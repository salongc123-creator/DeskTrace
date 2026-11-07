"""Drive space cleaner (2.2.0): what takes up a drive, what can go, and what deleting it means.

Nothing here deletes on its own. A scan only reads; cleaning happens when the user clicks one item,
and only inside that item's own folders (never through links or junctions). Personal files are moved to
the Recycle Bin, caches and temporary files are deleted for good — each item says which, up front."""
import heapq
import os
import shutil
import threading
import time

from extractors import category_of

if os.name == 'nt':
    import ctypes
    from ctypes import wintypes

REPARSE = 0x400          # FILE_ATTRIBUTE_REPARSE_POINT: links and junctions are never followed
ONLINE_ONLY = 0x400000 | 0x40000 | 0x1000  # RECALL_ON_DATA_ACCESS | RECALL_ON_OPEN | OFFLINE: a cloud placeholder
FRESH = 2 * 86400        # temporary files changed within the last two days are left alone (2.4.2: was 1 hour):
                         # a program that crashed last night may keep its unsaved work there
# Recovery copies and unsaved drafts of Office, WPS and other editors: never cleaned, however old (2.4.2)
DRAFT_EXTS = {'.asd', '.wbk', '.xar', '.~vsd', '.autosave', '.bak', '.bkp', '.$$$', '.sav', '.recover'}
DRAFT_NAMES = ('~wrd', '~wrl', '~wrc', '~wrf', '~$', 'autorecover', 'autosave', 'unsaved')
DRAFT_DIRS = ('unsavedfiles', 'autorecover', 'autosave', 'backup', 'recovery', 'unsaved', 'draft', 'wps')


def is_draft(name, is_dir=False):
    """A recovery copy or unsaved draft (or a folder of them) that a temp cleanup must never remove."""
    low = name.lower()
    if is_dir:
        return any(w in low for w in DRAFT_DIRS)
    return os.path.splitext(low)[1] in DRAFT_EXTS or low.startswith(DRAFT_NAMES)
TOP_FILES = 300
MAX_WORKERS = 4         # worker processes for a scan the user waits for (2.5.0: measured, 8 is no faster)
SLICE = 0.2             # a worker reads a folder this many seconds, then hands back what is left (2.5.0)
KEEP_MIN = 1 << 20       # after a scan, folders under 1 MB are not kept (they would never make the lists)


def env(name, default=''):
    return os.environ.get(name) or default


def drive_of(p):
    return os.path.splitdrive(os.path.abspath(p))[0].upper() + '\\'


def system_drive():
    return (env('SystemDrive', 'C:') + '\\').upper()


# ----------------------------------------------------------------------------------------------- cloud folders
_cloud = {'at': 0.0, 'roots': []}


def cloud_roots():
    """Folders a cloud service keeps in sync (OneDrive, Dropbox, iCloud, Box, Google Drive, ... — every
    provider that registers with Windows' cloud files system, plus the classic spots). Deleting a file here
    deletes it in the cloud too, so the cleaner never offers it (2.2.0 review, P0-1)."""
    if time.time() - _cloud['at'] < 300:
        return _cloud['roots']
    roots = set()
    for k in ('OneDrive', 'OneDriveConsumer', 'OneDriveCommercial'):
        if env(k):
            roots.add(env(k))
    home = env('USERPROFILE')
    for name in ('iCloudDrive', 'iCloud Drive', 'Dropbox', 'Box', 'BaiduSyncdisk', '百度网盘同步空间', 'Nutstore', '我的坚果云'):
        roots.add(os.path.join(home, name))
    for base in (env('LOCALAPPDATA'), env('APPDATA')):  # Dropbox writes where its folders are
        try:
            import json
            info = json.loads(open(os.path.join(base, 'Dropbox', 'info.json'), encoding='utf-8').read())
            roots.update(v.get('path') for v in info.values() if isinstance(v, dict) and v.get('path'))
        except (OSError, ValueError):
            pass
    if os.name == 'nt':
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\SyncRootManager'),):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            with winreg.OpenKey(k, winreg.EnumKey(k, i) + r'\UserSyncRoots') as u:
                                for j in range(winreg.QueryInfoKey(u)[1]):
                                    v = winreg.EnumValue(u, j)[1]
                                    if isinstance(v, str):
                                        roots.add(v)
                        except OSError:
                            pass
            except OSError:
                pass
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\OneDrive\Accounts') as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        with winreg.OpenKey(k, winreg.EnumKey(k, i)) as a:
                            roots.add(winreg.QueryValueEx(a, 'UserFolder')[0])
                    except OSError:
                        pass
        except OSError:
            pass
    _cloud.update(at=time.time(), roots=sorted(r for r in roots if r and os.path.isdir(r)))
    return _cloud['roots']


def cloud_root_of(path):
    return next((r for r in cloud_roots() if inside(path, r)), None)


def online_only(path):
    """True for a cloud placeholder: listed with its size, but nothing of it is on this disk."""
    try:
        return bool(os.stat(path, follow_symlinks=False).st_file_attributes & ONLINE_ONLY)
    except (OSError, AttributeError):
        return False


def cloud_overview():
    """Each cloud-synced folder with the space its files take on this PC and how many are online-only
    (2.6.0 #30). Reading attributes never downloads anything."""
    out = []
    for root in cloud_roots():
        local = local_n = online = 0
        for d, dirs, files in os.walk(root):
            for f in files:
                try:
                    st = os.stat(os.path.join(d, f), follow_symlinks=False)
                except OSError:
                    continue
                if getattr(st, 'st_file_attributes', 0) & ONLINE_ONLY:
                    online += 1
                else:
                    local, local_n = local + st.st_size, local_n + 1
        out.append({'path': root, 'name': os.path.basename(root), 'local': local, 'local_n': local_n, 'online_n': online})
    return out


def free_cloud_folder(root):
    """Ask the cloud service to keep every file of ``root`` online only (attrib -P +U, recursive): the local
    copies are freed, the files stay in the cloud and in the folder (2.6.0 #30)."""
    if root not in cloud_roots() or not os.path.isdir(root):
        return {'ok': False, 'code': 'notAllowed'}
    import subprocess
    r = subprocess.run(['attrib', '-P', '+U', os.path.join(root, '*'), '/S', '/D'], capture_output=True, creationflags=0x08000000)
    return {'ok': r.returncode == 0}


def keep_online_only(path):
    """Ask the cloud service to free the local copy (it stays in the cloud and in the folder)."""
    if not cloud_root_of(path) or not os.path.isfile(path):
        return {'ok': False, 'code': 'notAllowed'}
    import subprocess
    r = subprocess.run(['attrib', '-P', '+U', path], capture_output=True, creationflags=0x08000000)
    return {'ok': r.returncode == 0, 'size': os.path.getsize(path) if r.returncode == 0 else 0}


# ----------------------------------------------------------------------------------------------- Recycle Bin
def bin_status(drive):
    """(has a Recycle Bin, its size limit in bytes or None when unknown). Network and most removable
    drives have none, and a user or policy can switch it off: there "to the Recycle Bin" would really
    mean "gone for good" (2.2.0 review, P0-2)."""
    if os.name != 'nt':
        return False, None
    drive = drive_of(drive)
    if ctypes.windll.kernel32.GetDriveTypeW(drive) != 3:  # only fixed drives get a Recycle Bin
        return False, None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Policies\Explorer') as k:
            if winreg.QueryValueEx(k, 'NoRecycleFiles')[0]:
                return False, None
    except OSError:
        pass
    vol = ctypes.create_unicode_buffer(64)
    if not ctypes.windll.kernel32.GetVolumeNameForVolumeMountPointW(drive, vol, 64):
        return True, None
    guid = vol.value[vol.value.find('{'):vol.value.find('}') + 1]
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\BitBucket\Volume' + '\\' + guid) as k:
            try:
                if winreg.QueryValueEx(k, 'NukeOnDelete')[0]:
                    return False, None
            except OSError:
                pass
            try:
                return True, int(winreg.QueryValueEx(k, 'MaxCapacity')[0]) * 2 ** 20
            except OSError:
                return True, None
    except OSError:
        return True, None


def _bin_records(drive):
    """(original path, deleted at, $I file, $R file) of what this user has in the Recycle Bin of a drive,
    read from Windows' own $I records (never by guessing names)."""
    out = []
    base = os.path.join(drive_of(drive), '$Recycle.Bin')
    try:
        sids = [e.path for e in os.scandir(base) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return out
    for sid in sids:
        try:
            entries = list(os.scandir(sid))
        except OSError:
            continue  # other users' bins are not ours to read
        for e in entries:
            if not e.name.startswith('$I'):
                continue
            try:
                raw = open(e.path, 'rb').read()
                version = int.from_bytes(raw[0:8], 'little')
                when = (int.from_bytes(raw[16:24], 'little') - 116444736000000000) / 1e7
                if version >= 2:
                    n = int.from_bytes(raw[24:28], 'little')
                    orig = raw[28:28 + 2 * n].decode('utf-16-le').rstrip('\0')
                else:
                    orig = raw[24:24 + 520].decode('utf-16-le').split('\0')[0]
            except (OSError, ValueError, UnicodeDecodeError):
                continue
            out.append((orig, when, e.path, os.path.join(sid, '$R' + e.name[2:])))
    return out


def recycle_restore(paths, since):
    """Undo (2.4.0 §4): put files this app just moved to the Recycle Bin back where they were. Only the
    newest bin entry of each path deleted after ``since`` is used; an occupied original place is never
    overwritten (that file stays in the Recycle Bin and is reported)."""
    want = {os.path.normcase(os.path.normpath(p)): p for p in paths}
    found = {}
    for attempt in range(4):  # a just-written record can still be held by Windows for a moment
        for drive in {drive_of(p) for p in paths}:
            for orig, when, i_file, r_file in _bin_records(drive):
                k = os.path.normcase(os.path.normpath(orig))
                if k in want and when >= since - 120 and (k not in found or when > found[k][0]):
                    found[k] = (when, i_file, r_file)
        if len(found) == len(want):
            break
        time.sleep(0.5)
    restored, failed = [], []
    for k, p in want.items():
        if k not in found:
            failed.append({'path': p, 'code': 'notInBin'})
            continue
        _, i_file, r_file = found[k]
        if os.path.exists(p):
            failed.append({'path': p, 'code': 'occupied'})
            continue
        try:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            os.replace(r_file, p)
            try:
                os.remove(i_file)
            except OSError:
                pass
            restored.append(p)
        except OSError:
            failed.append({'path': p, 'code': 'inUse'})
    return {'ok': not failed, 'restored': restored, 'failed': failed}


# ----------------------------------------------------------------------------------------------- chat apps, hibernation
def _first(*paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def chat_apps():
    """Chat apps whose data is on this PC (2.4.0 §5): their data folder and, if found, the program to open.
    DeskTrace never deletes chat data — chat history and received files cannot be downloaded again."""
    home, docs, ad, la = env('USERPROFILE'), os.path.join(env('USERPROFILE'), 'Documents'), env('APPDATA'), env('LOCALAPPDATA')
    pf, pf86 = env('ProgramFiles', r'C:\Program Files'), env('ProgramFiles(x86)', r'C:\Program Files (x86)')
    apps = [
        ('wechat', [os.path.join(docs, 'WeChat Files'), os.path.join(docs, 'xwechat_files'), os.path.join(home, 'xwechat_files')],
         [os.path.join(pf, 'Tencent', 'Weixin', 'Weixin.exe'), os.path.join(pf86, 'Tencent', 'WeChat', 'WeChat.exe'), os.path.join(pf, 'Tencent', 'WeChat', 'WeChat.exe')]),
        ('qq', [os.path.join(docs, 'Tencent Files')],
         [os.path.join(pf, 'Tencent', 'QQNT', 'QQ.exe'), os.path.join(pf86, 'Tencent', 'QQNT', 'QQ.exe'), os.path.join(pf86, 'Tencent', 'QQ', 'Bin', 'QQScLauncher.exe')]),
        ('wecom', [os.path.join(docs, 'WXWork')], [os.path.join(pf86, 'WXWork', 'WXWork.exe'), os.path.join(pf, 'WXWork', 'WXWork.exe')]),
        ('dingtalk', [os.path.join(ad, 'DingTalk')], [os.path.join(pf86, 'DingDing', 'DingtalkLauncher.exe'), os.path.join(pf, 'DingDing', 'DingtalkLauncher.exe')]),
        ('telegram', [os.path.join(ad, 'Telegram Desktop', 'tdata')], [os.path.join(ad, 'Telegram Desktop', 'Telegram.exe')]),
    ]
    names = {'wechat': ('微信', 'wechat', 'weixin'), 'qq': ('qq',), 'wecom': ('企业微信', 'wxwork', 'wecom'),
             'dingtalk': ('钉钉', 'dingtalk'), 'telegram': ('telegram',)}
    installed = _installed_programs()
    out = []
    for app, datas, exes in apps:
        data = _first(*datas)
        if data:
            exe = _first(*exes) or next((x for n, x in installed if any(k == n or (len(k) > 2 and k in n) for k in names[app])
                                         and not (app == 'qq' and 'music' in n)), None)
            out.append({'id': 'app_' + app, 'app': app, 'data': data, 'exe': exe})
    return out


CHAT_KIND = {'image': 'picture', 'images': 'picture', 'pic': 'picture', 'imagefiles': 'picture', 'img': 'picture', 'thumb': 'picture',
             'video': 'video', 'videos': 'video', 'file': 'file', 'files': 'file', 'filerecv': 'file', 'attach': 'file',
             'msgattach': 'file', 'cache': 'cache', 'temp': 'cache', 'tmp': 'cache', 'sns': 'cache', 'resource_cache': 'cache'}
CHAT_NEVER = {'db_storage', 'database', 'nt_db', 'config', 'backup', 'msgbackup', 'msg_db', 'favorite', 'favorites'}


def chat_media(data, days=90):
    """Received pictures, videos, files and caches in a chat app's folder, older than ``days`` days, by kind
    (2.6.0 #7): {kind: [(path, size), ...]}. Databases, configuration and backups are never included."""
    limit, out = time.time() - days * 86400, {'picture': [], 'video': [], 'file': [], 'cache': []}
    for d, dirs, files in os.walk(data):
        parts = [x.lower() for x in os.path.relpath(d, data).split(os.sep)]
        if any(p in CHAT_NEVER for p in parts):
            dirs[:] = []
            continue
        kind = next((CHAT_KIND[p] for p in reversed(parts) if p in CHAT_KIND), None)
        if not kind:
            continue
        for f in files:
            if os.path.splitext(f)[1].lower() in DATABASES:
                continue  # a database, wherever it is: never
            p = os.path.join(d, f)
            try:
                st = os.stat(p)
            except OSError:
                continue
            if st.st_mtime < limit:
                out[kind].append((p, st.st_size))
    return out


def _installed_programs():
    """(lower-case name, program file) of installed programs, from the same list Settings › Apps uses."""
    out = []
    if os.name != 'nt':
        return out
    import winreg
    for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
                      (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
                      (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall')):
        try:
            with winreg.OpenKey(hive, key) as k:
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        with winreg.OpenKey(k, winreg.EnumKey(k, i)) as a:
                            name = str(winreg.QueryValueEx(a, 'DisplayName')[0]).lower()
                            icon = ''
                            try:
                                icon = str(winreg.QueryValueEx(a, 'DisplayIcon')[0]).split(',')[0].strip('"')
                            except OSError:
                                pass
                            if icon.lower().endswith('.exe') and os.path.isfile(icon) and 'uninst' not in os.path.basename(icon).lower():
                                out.append((name, icon))
                    except OSError:
                        pass
        except OSError:
            pass
    return out


def hibernation():
    """Hibernation on the system drive (2.4.0 §5): on/off and what hiberfil.sys takes. Switching it is
    left to Windows (powercfg needs administrator rights; DeskTrace only asks Windows to show its prompt)."""
    root = system_drive()
    size = 0
    try:
        with os.scandir(root) as it:
            for e in it:
                if e.name.lower() == 'hiberfil.sys':
                    size = e.stat(follow_symlinks=False).st_size
    except OSError:
        pass
    on = size > 0
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Power') as k:
                on = bool(winreg.QueryValueEx(k, 'HibernateEnabled')[0]) and size > 0
        except OSError:
            pass
    return {'on': on, 'size': size}


def recycle_problem(path):
    """Why ``path`` cannot go to the Recycle Bin ('noBin' / 'tooBigForBin'), or None when it can."""
    has, cap = bin_status(path)
    if not has:
        return 'noBin'
    try:
        if cap and os.path.getsize(path) > cap:
            return 'tooBigForBin'
    except OSError:
        pass
    return None


# ----------------------------------------------------------------------------------------------- drives
def drives():
    """Fixed and removable drives with their size and free space."""
    out = []
    if os.name != 'nt':
        return out
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if not mask & (1 << i):
            continue
        root = f'{chr(65 + i)}:\\'
        kind = ctypes.windll.kernel32.GetDriveTypeW(root)
        if kind not in (2, 3):  # DRIVE_REMOVABLE, DRIVE_FIXED
            continue
        try:
            u = shutil.disk_usage(root)
        except OSError:
            continue  # e.g. an empty card reader
        label = ctypes.create_unicode_buffer(261)
        ctypes.windll.kernel32.GetVolumeInformationW(root, label, 261, None, None, None, None, 0)
        out.append({'drive': root, 'label': label.value, 'total': u.total, 'free': u.free, 'used': u.total - u.free,
                    'system': root == system_drive(), 'removable': kind == 2})
    return out


# ----------------------------------------------------------------------------------------------- scan
SPARSE, COMPRESSED = 0x200, 0x800


def cluster_size(drive):
    if os.name != 'nt':
        return 4096
    spc, bps, a, b = wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD(), wintypes.DWORD()
    if ctypes.windll.kernel32.GetDiskFreeSpaceW(drive, ctypes.byref(spc), ctypes.byref(bps), ctypes.byref(a), ctypes.byref(b)):
        return spc.value * bps.value or 4096
    return 4096


def volume_serial(drive):
    if os.name != 'nt':
        return 0
    serial = wintypes.DWORD()
    ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, ctypes.byref(serial), None, None, None, 0)
    return serial.value


def is_hdd(drive):
    """True for a spinning disk (seek penalty): read gently, one folder at a time, and quick-scan by default."""
    if os.name != 'nt':
        return False
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    h = k32.CreateFileW('\\\\.\\' + drive[:2], 0, 3, None, 3, 0, None)
    if not h or h == wintypes.HANDLE(-1).value:
        return False
    try:
        query = (ctypes.c_uint32 * 3)(7, 0, 0)  # StorageDeviceSeekPenaltyProperty, PropertyStandardQuery
        out = (ctypes.c_uint8 * 12)()
        got = wintypes.DWORD()
        if not k32.DeviceIoControl(wintypes.HANDLE(h), 0x2D1400, query, 12, out, 12, ctypes.byref(got), None):
            return False
        return bool(out[8])
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))


class _FSI(ctypes.Structure if os.name == 'nt' else object):
    _fields_ = [('alloc', ctypes.c_longlong), ('eof', ctypes.c_longlong), ('links', ctypes.c_ulong),
                ('delete', ctypes.c_byte), ('dir', ctypes.c_byte)] if os.name == 'nt' else []


def file_disk_info(path):
    """(bytes the file really takes on disk, number of hard links) — or None. One handle per file, so it
    is only asked for the files that are shown, never for a whole drive (2.4.0 §6)."""
    if os.name != 'nt':
        return None
    k32 = ctypes.windll.kernel32
    k32.CreateFileW.restype = wintypes.HANDLE
    h = k32.CreateFileW(path, 0x80, 7, None, 3, 0x02000000 | 0x00200000, None)
    if not h or h == wintypes.HANDLE(-1).value:
        return None
    try:
        f = _FSI()
        if not k32.GetFileInformationByHandleEx(wintypes.HANDLE(h), 1, ctypes.byref(f), ctypes.sizeof(f)):
            return None
        return f.alloc, f.links
    finally:
        k32.CloseHandle(wintypes.HANDLE(h))


def compressed_size(path):
    if os.name != 'nt':
        return None
    hi = wintypes.DWORD()
    lo = ctypes.windll.kernel32.GetCompressedFileSizeW(path, ctypes.byref(hi))
    return None if lo == 0xFFFFFFFF and ctypes.GetLastError() else (hi.value << 32) + lo


class DriveScan:
    """One read-only walk of a drive (or, quick, of your own folders on it): what every folder takes on
    the disk, the biggest files and the space by type. 2.4.0: sizes are disk usage (whole clusters; real
    usage for compressed and sparse files), several folders are read at once when you wait for it, the
    result is kept on disk, and a quick scan reads only your folders."""

    def __init__(self, root, background=None, mode='full', folders=None, priority=False, on_done=None, start=True):
        self.root, self.background, self.mode = root, background, mode
        self.folders = [f for f in (folders or []) if f and os.path.isdir(f)]
        if mode == 'quick' and not self.folders:
            self.mode = 'full'  # nothing of yours on this drive: read all of it
        self.priority, self.on_done = priority, on_done
        self.state, self.started, self.finished = 'scanning', time.time(), None
        self.files = self.bytes = self.skipped = self.online = self.tiny = 0
        self.sharing = False
        self.dirs, self.kids = {}, {}   # folder (1 MB or more) -> (bytes on disk, files); folder -> its listed subfolders
        self.big, self.types = [], {}
        self.shared = 0                 # WinSxS hard links counted at their other place too (worked out afterwards)
        self.cluster = cluster_size(root)
        self.serial = volume_serial(root)
        self.hdd = is_hdd(root)
        self.cached_at = None
        self.stop = False
        self._lock = threading.Lock()
        if start:
            threading.Thread(target=self.run, daemon=True, name='drive-scan').start()

    # -- reading
    def run(self):
        if self.background:
            self.background()  # Windows background mode: other programs come first
        try:
            if self.mode == 'quick':
                parts = [(f, self._walk_top(f)) for f in self.folders]
                total_s = sum(x[0] for _, x in parts)
                total_n = sum(x[1] for _, x in parts)
                self.dirs[self.root] = (total_s, total_n)
                self.kids[self.root] = [f for f, x in parts if x[0] >= KEEP_MIN]
            else:
                self._walk_top(self.root)
            whole = self.dirs.get(self.root, (self.bytes, self.files))  # stopped early: what was read so far
            self.files, self.bytes = whole[1], whole[0]
            self.state = 'stopped' if self.stop else 'done'
        except Exception as e:  # a scan must never take the service down
            self.state, self.error = 'failed', repr(e)
        self.finished = time.time()
        if self.state == 'done' and self.on_done:
            try:
                self.on_done(self)
            except Exception:
                pass

    def workers(self):
        """Worker processes for a scan the user waits for on an SSD: up to MAX_WORKERS, half the logical processors
        ; one in the background or on a spinning disk."""
        if self.background or self.hdd or not self.priority:
            return 1
        return min(MAX_WORKERS, max(2, (os.cpu_count() or 4) // 2))

    def _walk_top(self, top):
        """``top`` and everything below it: in parallel when the user waits for it, otherwise one folder
        at a time."""
        if self.workers() > 1:
            r = self._parallel(top, self.workers())
            if r is not None:
                return r
            self._reset()  # the workers failed: read it here instead, from the start
        total_s, total_n, kept = self._walk(top, force=True)
        return total_s, total_n

    def _reset(self):
        with self._lock:
            self.files = self.bytes = self.skipped = self.online = self.tiny = 0
            self.dirs, self.kids, self.big, self.types = {}, {}, [], {}

    def _parallel(self, top, workers):
        """Read ``top`` with ``workers`` separate Python processes sharing one queue of folders (2.5.0).
        A worker reads a folder for at most SLICE seconds, then hands the subfolders it has not started
        back to the queue (what it listed and finished is reported); small folders are read whole. A worker takes the next folder as
        soon as it is free, so one huge folder (a user profile, MATLAB, WinSxS) is spread over all of them.
        Python runs one thread at a time, so real parallel reading needs processes. Returns None if the
        workers cannot do it (then the caller reads in-process)."""
        import collections
        import json
        import queue
        import subprocess
        import sys
        procs, out = [], queue.Queue()
        try:
            for _ in range(workers):
                procs.append(subprocess.Popen([sys.executable, os.path.abspath(__file__), '--scan-worker'],
                                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                              creationflags=0x08000000 if os.name == 'nt' else 0))
        except OSError:
            for pr in procs:
                pr.kill()
            return None

        def read(k, pr):
            for line in pr.stdout:
                out.put((k, line))
            out.put((k, None))
        for k, pr in enumerate(procs):
            threading.Thread(target=read, args=(k, pr), daemon=True).start()
        todo, busy = collections.deque([top]), [0] * workers
        listed, walked, finals, counts = {}, {}, {}, [(0, 0)] * workers
        cl = self.cluster
        try:
            while True:
                for k, pr in enumerate(procs):
                    while todo and busy[k] < 2:  # two folders in hand: never idle while the next is sent
                        d = todo.popleft()
                        pr.stdin.write((json.dumps({'d': d, 'budget': SLICE, 'cluster': cl}) + '\n').encode('utf-8'))
                        pr.stdin.flush()
                        busy[k] += 1
                if not todo and not any(busy):
                    break
                if self.stop:
                    raise InterruptedError
                try:
                    k, line = out.get(timeout=0.2)
                except queue.Empty:
                    continue
                if line is None:
                    return self._abort(procs)  # a worker ended early
                m = json.loads(line)
                busy[k] -= 1
                counts[k] = (m['files'], m['bytes'])
                with self._lock:
                    self.files, self.bytes = sum(c[0] for c in counts), sum(c[1] for c in counts)
                for d, s_, n_, sub in m['listed']:
                    listed[d] = (s_, n_, sub)
                for d, s_, n_ in m['walked']:
                    walked[d] = (s_, n_)
                todo.extend(m['todo'])
            for pr in procs:
                pr.stdin.write(b'{"end": true}\n')
                pr.stdin.close()
            ended = 0
            while ended < workers:
                k, line = out.get(timeout=60)
                if line is None:
                    ended += 1
                elif line.startswith(b'{"t": "R"'):
                    finals[k] = json.loads(line)
            if len(finals) != workers:
                return self._abort(procs)
        except InterruptedError:
            self._abort(procs)
            return 0, 0
        except (OSError, ValueError, queue.Empty):
            return self._abort(procs)
        with self._lock:
            for o in finals.values():
                self.dirs.update({d: tuple(v) for d, v in o['dirs']})
                self.kids.update(o['kids'])
                for k, v in o['types'].items():
                    self.types[k] = self.types.get(k, 0) + v
                for b in o['big']:
                    b = tuple(b)
                    if len(self.big) < TOP_FILES:
                        heapq.heappush(self.big, b)
                    elif b[0] > self.big[0][0]:
                        heapq.heapreplace(self.big, b)
                self.online += o['online']
                self.skipped += o['skipped']
                self.tiny += o.get('tiny', 0)
        # the listed folders add up from the bottom: deepest first
        total = dict(walked)
        for d in sorted(listed, key=lambda p: -os.path.normpath(p).rstrip('\\').count('\\')):
            s_, n_, sub = listed[d]
            kept = []
            for c in sub:
                cs, cn = total.get(c, (0, 0))
                s_, n_ = s_ + cs, n_ + cn
                if cs >= KEEP_MIN:
                    kept.append(c)
            total[d] = (s_, n_)
            self._keep(d, s_, n_, kept, force=(d == top))
        if top not in listed and top in total:  # read whole by one worker (a small folder): keep it anyway
            with self._lock:
                self.dirs[top] = total[top]
        return total.get(top, (0, 0))

    def _abort(self, procs):
        for pr in procs:
            try:
                pr.kill()
            except OSError:
                pass
        return None

    def _keep(self, d, size, n, kept, force=False):
        if size >= KEEP_MIN or force:
            with self._lock:
                self.dirs[d] = (size, n)
                if kept:
                    self.kids[d] = kept

    def _walk_safe(self, d):
        try:
            return self._walk(d)
        except RecursionError:
            self.skipped += 1
            return 0, 0

    def _list(self, d):
        """The files directly in ``d`` (counted now) and its subfolders (to read)."""
        own_s = own_n = 0
        subdirs, big, types = [], [], {}
        try:
            it = os.scandir(d)
        except OSError:
            self.skipped += 1
            return 0, 0, []
        cl = self.cluster
        floor = self.big[0][0] if len(self.big) >= TOP_FILES else -1  # only files that can make the list
        with it:
            for e in it:
                try:
                    st = e.stat(follow_symlinks=False)  # from the folder listing: no extra call on Windows
                except OSError:
                    continue
                attrs = st.st_file_attributes
                if attrs & 0x10:  # a folder
                    if not attrs & REPARSE:
                        subdirs.append(e.path)
                    continue
                if attrs & REPARSE and not attrs & ONLINE_ONLY:
                    continue  # links and junctions are never followed
                if attrs & ONLINE_ONLY:
                    self.online += 1  # a cloud placeholder: nothing of it is on this disk
                    continue
                size = st.st_size
                if attrs & (SPARSE | COMPRESSED):  # only these are asked: the rest is whole clusters
                    used = compressed_size(e.path)
                    used = size if used is None else used
                else:
                    used = (size + cl - 1) // cl * cl
                if size < 700:
                    self.tiny += 1  # may be stored inside the file table itself: then it takes no cluster
                own_s += used
                own_n += 1
                name = e.name
                dot = name.rfind('.')
                ext = name[dot:].lower() if dot > 0 else '(none)'
                types[ext] = types.get(ext, 0) + used
                if used > floor:
                    big.append((used, e.path, st.st_mtime, size))
        with self._lock:
            for k, v in types.items():
                self.types[k] = self.types.get(k, 0) + v
            for b in big:
                if len(self.big) < TOP_FILES:
                    heapq.heappush(self.big, b)
                elif b[0] > self.big[0][0]:
                    heapq.heapreplace(self.big, b)
            self.files += own_n
            self.bytes += own_s
        return own_s, own_n, subdirs

    def _walk(self, d, force=False):
        """Whole size of ``d``, adding up on the way back out, so only folders of 1 MB or more are held."""
        own_s, own_n, subdirs = self._list(d)
        total_s, total_n, kept = own_s, own_n, []
        for sd in subdirs:
            if self.stop:
                break
            s, n = self._walk(sd)
            total_s, total_n = total_s + s, total_n + n
            if s >= KEEP_MIN:
                kept.append(sd)
        self._keep(d, total_s, total_n, kept, force=force)
        return (total_s, total_n, kept) if force else (total_s, total_n)

    def count_shared(self):
        """WinSxS: files hard-linked from elsewhere in Windows take their space only once. Worked out after
        the scan, in the background (a handle per file is too slow for the scan itself), and subtracted."""
        want = os.path.normcase(os.path.join(env('WINDIR', r'C:\Windows'), 'WinSxS'))
        win = next((k for k in self.dirs if os.path.normcase(k) == want), None)  # Windows may say C:\WINDOWS
        if self.mode != 'full' or not win:
            return
        if self.background:
            self.background()
        self.sharing = True
        shared, stack = 0, [win]
        while stack and not self.stop:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                            continue
                    except OSError:
                        continue
                    info = file_disk_info(e.path)
                    if info and info[1] > 1:
                        shared += info[0]
        self.sharing = False
        if self.stop:
            return
        self.shared = shared
        d = win
        while True:  # WinSxS and every folder above it
            if d in self.dirs:
                s, n = self.dirs[d]
                self.dirs[d] = (max(0, s - shared), n)
            parent = os.path.dirname(d)
            if parent == d or len(d) <= 3:
                break
            d = parent if len(parent) > 3 else self.root

    # -- results
    def progress(self):
        return {'state': self.state, 'files': self.files, 'bytes': self.bytes, 'skipped': self.skipped, 'online': self.online,
                'seconds': round((self.finished or time.time()) - self.started, 1), 'mode': self.mode, 'hdd': self.hdd,
                'cached_at': self.cached_at, 'shared': self.shared, 'sharing': self.sharing,
                'tiny': self.tiny, 'tiny_bytes': self.tiny * self.cluster}

    def children(self, folder):
        """The folders directly inside ``folder`` with what they take, biggest first."""
        out = [(self.dirs[d][0], self.dirs[d][1], d) for d in self.kids.get(self.key(folder), []) if d in self.dirs]
        win = os.path.join(env('WINDIR', r'C:\Windows'), 'WinSxS')
        return [{'path': d, 'name': os.path.basename(d) or d, 'size': s, 'files': n, 'movable': movable(d, s),
                 'shared': self.shared if os.path.normcase(d) == os.path.normcase(win) else 0} for s, n, d in sorted(out, reverse=True)]

    def own_files(self, folder, n=60):
        """The biggest files directly in ``folder`` (read now: the scan only keeps the drive's biggest)."""
        out = []
        try:
            with os.scandir(folder) as it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                        if (e.is_file(follow_symlinks=False) and not getattr(st, 'st_file_attributes', 0) & (REPARSE | ONLINE_ONLY)
                                and not is_core(e.path)):
                            out.append((st.st_size, e.path, st.st_mtime))
                    except OSError:
                        pass
        except OSError:
            pass
        return [file_row(p, s, m, exact=True) for s, p, m in heapq.nlargest(n, out)]

    def key(self, folder):
        """How a folder is spelled in ``dirs``: the drive root with its backslash, others without."""
        folder = os.path.normpath(folder)
        if os.path.normcase(folder.rstrip('\\')) == os.path.normcase(self.root.rstrip('\\')):
            return self.root
        return folder.rstrip('\\')

    def summary(self, folder=None):
        folder = self.key(folder or self.root)
        whole = self.dirs.get(folder, [0, 0])
        types = sorted(self.types.items(), key=lambda x: -x[1])
        if not getattr(self, '_exact', False) and self.state != 'scanning':  # real usage of the listed files, once
            self.big = [(r['used'], r['path'], r['mtime'], r['size']) for r in
                        (file_row(p, sz, m, exact=True) for _, p, m, sz in sorted(self.big, reverse=True)[:TOP_FILES])]
            self._exact = True
        big = [b for b in sorted(self.big, reverse=True) if not is_core(b[1])][:150]
        folders = self.children(folder)[:40]
        for f in folders[:16]:  # the space grid's second level (2.5.0)
            f['sub'] = [{'path': c['path'], 'name': c['name'], 'size': c['size']} for c in self.children(f['path'])[:12]]
        return {'folder': folder, 'size': whole[0], 'count': whole[1], 'folders': folders,
                'here': self.own_files(folder) if folder != self.root else [],
                'big': [file_row(p, sz, m, used=u) for u, p, m, sz in big],
                'types': [{'ext': e, 'size': s} for e, s in types[:12]],
                'other_types': sum(s for _, s in types[12:]), 'quick_folders': self.folders if self.mode == 'quick' else [],
                **self.progress()}

    # -- kept on disk between visits (2.4.0 §3)
    def to_dict(self):
        return {'root': self.root, 'mode': self.mode, 'folders': self.folders, 'serial': self.serial, 'finished': self.finished,
                'files': self.files, 'bytes': self.bytes, 'skipped': self.skipped, 'online': self.online, 'shared': self.shared,
                'tiny': self.tiny, 'cluster': self.cluster,
                'dirs': [[d, s, n] for d, (s, n) in self.dirs.items()], 'kids': self.kids, 'big': self.big,
                'types': self.types, 'seconds': round((self.finished or time.time()) - self.started, 1)}

    @classmethod
    def from_dict(cls, d):
        sc = cls(d['root'], mode=d['mode'], folders=d.get('folders'), start=False)
        sc.mode = d['mode']
        sc.state, sc.finished, sc.cached_at = 'done', d['finished'], d['finished']
        sc.started = d['finished'] - d.get('seconds', 0)
        sc.files, sc.bytes, sc.skipped, sc.online, sc.shared = d['files'], d['bytes'], d['skipped'], d['online'], d.get('shared', 0)
        sc.tiny, sc.cluster = d.get('tiny', 0), d.get('cluster', 4096)
        sc.dirs = {x[0]: (x[1], x[2]) for x in d['dirs']}
        sc.kids, sc.types = d['kids'], d['types']
        sc.big = [tuple(b) for b in d['big']]
        heapq.heapify(sc.big)
        sc._exact = True
        return sc


def _walk_slice(sc, d, deadline, listed, walked, todo):
    """Read ``d`` until ``deadline``: returns its (bytes, files) if the whole folder was read in time.
    Otherwise ``d`` goes into ``listed`` (its own files and subfolders), finished subfolders into
    ``walked`` and the subfolders not started yet into ``todo``, for any free worker (2.5.0)."""
    own_s, own_n, subs = sc._list(d)
    total_s, total_n, kept, done, complete = own_s, own_n, [], [], True
    for i, c in enumerate(subs):
        if time.perf_counter() > deadline:
            todo.extend(subs[i:])
            complete = False
            break
        r = _walk_slice(sc, c, deadline, listed, walked, todo)
        if r is None:
            complete = False
            continue
        done.append((c, r[0], r[1]))
        total_s, total_n = total_s + r[0], total_n + r[1]
        if r[0] >= KEEP_MIN:
            kept.append(c)
    if complete:
        sc._keep(d, total_s, total_n, kept)
        return total_s, total_n
    listed.append([d, own_s, own_n, subs])
    walked.extend([c, s_, n_] for c, s_, n_ in done)
    return None


def _scan_worker():
    """A worker process of a fast scan (2.5.0): takes one folder at a time from the shared queue (a JSON
    line), reads it for at most ``budget`` seconds, and answers with one line: what it finished, what it
    only listed and the subfolders it hands back. At the end it sends everything it collected."""
    import json
    import sys
    sc = DriveScan('', start=False)
    for raw in sys.stdin.buffer:
        job = json.loads(raw)
        if job.get('end'):
            break
        sc.cluster = job['cluster']
        listed, walked, todo = [], [], []
        try:
            r = _walk_slice(sc, job['d'], time.perf_counter() + job['budget'], listed, walked, todo)
        except RecursionError:
            sc.skipped += 1
            r = (0, 0)
        if r is not None:
            walked.append([job['d'], r[0], r[1]])
        m = {'t': 'b', 'listed': listed, 'walked': walked, 'todo': todo}
        m.update(files=sc.files, bytes=sc.bytes)
        sys.stdout.write(json.dumps(m) + '\n')
        sys.stdout.flush()
    out = {'t': 'R', 'dirs': [[d, list(v)] for d, v in sc.dirs.items()], 'kids': sc.kids, 'types': sc.types,
           'big': [list(b) for b in sc.big], 'online': sc.online, 'skipped': sc.skipped, 'tiny': sc.tiny}
    sys.stdout.write(json.dumps(out) + '\n')
    sys.stdout.flush()


if __name__ == '__main__' and '--scan-worker' in __import__('sys').argv:
    _scan_worker()


# ----------------------------------------------------------------------------------------------- consequences
def known_dirs():
    w = env('WINDIR', r'C:\Windows')
    pf = [env('ProgramFiles', r'C:\Program Files'), env('ProgramFiles(x86)', r'C:\Program Files (x86)')]
    return {'windows': w, 'programs': pf, 'programdata': env('ProgramData', r'C:\ProgramData'),
            'appdata': [env('APPDATA'), env('LOCALAPPDATA')], 'downloads': os.path.join(env('USERPROFILE'), 'Downloads'),
            'home': env('USERPROFILE')}


def inside(p, base):
    if not base:
        return False
    p, base = os.path.normcase(os.path.normpath(p)), os.path.normcase(os.path.normpath(base))
    return p == base or p.startswith(base.rstrip('\\') + '\\')


GAME_DIRS = ('\\steamapps\\', '\\steamlibrary\\', '\\epic games\\', '\\battle.net\\', '\\xboxgames\\', '\\riot games\\',
             '\\ubisoft game launcher\\', '\\ea games\\', '\\gog galaxy\\games\\', '\\wegameapps\\', '\\tencent games\\')
CHAT_DIRS = ('\\wechat files\\', '\\xwechat_files\\', '\\tencent files\\', '\\wxwork\\', '\\dingtalk\\', '\\telegram desktop\\')
INSTALLERS = {'.exe', '.msi', '.msix', '.appx', '.msixbundle'}
ARCHIVES = {'.zip', '.rar', '.7z', '.iso', '.img', '.tar', '.gz', '.cab'}
VMS = {'.vmdk', '.vhd', '.vhdx', '.vdi', '.qcow2', '.avhdx'}
MEDIA = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.mp3', '.flac', '.wav', '.m4a', '.jpg', '.jpeg', '.png', '.heic', '.raw', '.psd'}
DOCS = {'.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.pdf', '.txt', '.md', '.csv'}


BROWSER_DIRS = ('\\google\\chrome\\user data\\', '\\microsoft\\edge\\user data\\', '\\mozilla\\firefox\\profiles\\',
                '\\bravesoftware\\', '\\opera software\\', '\\vivaldi\\user data\\', '\\360chrome\\', '\\qqbrowser\\')
BROWSER_CACHE = ('\\cache\\', '\\cache2\\', '\\code cache\\', '\\gpucache\\', '\\shadercache\\', '\\cachestorage\\',
                 '\\grshadercache\\', '\\dawncache\\')
PACKAGE_CACHES = ('\\npm-cache\\', '\\pip\\cache\\', '\\yarn\\cache\\', '\\.cache\\', '\\.gradle\\caches\\', '\\.m2\\repository\\',
                  '\\.nuget\\packages\\', '\\anaconda3\\pkgs\\', '\\miniconda3\\pkgs\\', '\\go\\pkg\\mod\\', '\\.cargo\\registry\\')
DATABASES = {'.db', '.sqlite', '.sqlite3', '.mdb', '.accdb', '.mdf', '.ldf', '.edb', '.realm', '.kdbx',
             '.db-wal', '.db-shm', '.db-journal', '.sqlite-wal', '.sqlite-shm', '.sqlite-journal'}  # a database's journal is part of it
CORE_ROOT_FILES = {'pagefile.sys', 'swapfile.sys', 'hiberfil.sys', 'bootmgr', 'bootnxt', 'dumpstack.log', 'dumpstack.log.tmp',
                   'bootsect.bak', 'boottel.dat'}
CORE_ROOT_DIRS = {'system volume information', 'recovery', 'boot', 'efi', 'msocache'}
# Windows' own data under ProgramData: machine keys, activation, the credential vault, Defender (Gemini 2.5.0 P1-1)
CORE_PROGRAMDATA = ('\\microsoft\\crypto\\', '\\microsoft\\windows\\clipsvc\\', '\\microsoft\\vault\\',
                    '\\microsoft\\windows defender\\', '\\microsoft\\windows\\systemdata\\', '\\microsoft\\protect\\')


def is_core(path):
    """A file Windows itself needs to start and run: never listed and never deleted (2.5.0). Its space
    still counts in the folder totals."""
    parts = os.path.normpath(path).split('\\')
    top = parts[1].lower() if len(parts) > 1 else ''
    if len(parts) == 2 and top in CORE_ROOT_FILES:
        return True
    k = known_dirs()
    if inside(path, k['programdata']):
        low = os.path.normcase(path)
        if any(c in low for c in CORE_PROGRAMDATA):
            return True
    return inside(path, k['windows']) or top.startswith('$') or top in CORE_ROOT_DIRS


def consequence(path):
    """What deleting this file means: (level, reason key, can delete). 2.5.0: everything but core system
    files can be deleted — the level says what the file is, the reason what deleting it does. Levels:
    system (core: not listed), cloud (synced: deleting removes it online too), program (part of an
    installed program or game), inapp (an app's own data such as chat history), caution (settings or
    caches of an app), personal (yours), safe."""
    k = known_dirs()
    name, ext = os.path.basename(path).lower(), os.path.splitext(path)[1].lower()
    low = os.path.normcase(os.path.normpath(path)) + '\\'
    root_file = os.path.dirname(os.path.normpath(path)).rstrip('\\').endswith(':')
    if is_core(path):
        return 'system', 'windows', False
    if is_draft(name) or any(is_draft(part, True) and part.lower() in ('unsavedfiles', 'autorecover', 'autosave')
                             for part in os.path.normpath(path).split('\\')[1:-1]):
        return 'inapp', 'draft', True  # a recovery copy or unsaved draft (2.4.2 promise, Gemini 2.5.0 P0-1)
    if cloud_root_of(path):
        return 'cloud', 'cloud', True
    if inside(path, os.path.join(drive_of(path), 'Windows.old')):
        return 'program', 'winold', True
    if any(g in low for g in GAME_DIRS):
        return 'program', 'game', True
    if any(c in low for c in CHAT_DIRS):
        return 'inapp', 'chat', True
    if ext == '.pst':
        return 'inapp', 'pst', True
    # 2.5.0: kinds that are easy to delete by mistake, each with its own warning
    if 'docker' in low and ext in ('.vhdx', '.vhd', '.raw', '.img'):
        return 'inapp', 'docker', True
    if name == 'ext4.vhdx' or (ext in ('.vhdx', '.vhd') and ('\\wsl\\' in low or 'canonicalgroup' in low or 'linux' in low)):
        return 'inapp', 'wsl', True
    if '\\mobilesync\\backup\\' in low:
        return 'inapp', 'phonebackup', True
    if '\\saved games\\' in low or '\\my games\\' in low:
        return 'inapp', 'gamesave', True
    if ext in DATABASES:
        return 'inapp', 'database', True  # wherever it is: a database and its journal are data, never cache (P0-2, P1-2)
    if any(b in low for b in BROWSER_DIRS):
        if any(c in low for c in BROWSER_CACHE):
            return 'safe', 'browsercache', True
        return 'inapp', 'browser', True
    if ext in ('.dmp', '.mdmp', '.hdmp'):
        return 'safe', 'dump', True
    if ext in ('.log', '.etl') or name.endswith('.log.old'):
        return 'safe', 'log', True
    if any(c in low for c in PACKAGE_CACHES):
        return 'safe', 'pkgcache', True
    if any(inside(path, p) for p in k['programs']):
        return 'program', 'program', True
    if inside(path, k['programdata']):
        return 'program', 'programdata', True
    if '\\.git\\' in low:
        return 'caution', 'git', True
    if ext == '.ost':
        return 'caution', 'ost', True
    if any(inside(path, a) for a in k['appdata']):
        if '\\cache\\' in low or '\\caches\\' in low or '\\temp\\' in low:
            return 'safe', 'appcache', True
        return 'caution', 'appdata', True
    if inside(path, k['downloads']) and ext in INSTALLERS:
        return 'safe', 'installer', True
    if ext in VMS:
        return 'caution', 'vm', True
    if ext in ARCHIVES:
        return 'personal', 'archive', True
    if ext in MEDIA:
        return 'personal', 'media', True
    if ext in DOCS:
        return 'personal', 'document', True
    if ext in INSTALLERS:
        return 'personal', 'program_file', True
    return 'personal', 'other', True


def file_row(path, size, mtime, used=None, exact=False):
    """A file as the cleaner lists it: its size, what it takes on the disk ("used": whole clusters, less
    when compressed, much less when sparse, shared when hard-linked) and what deleting it would mean."""
    level, why, ok = consequence(path)
    links, approx = 1, used is None and not exact
    if exact:
        info = file_disk_info(path)
        if info:
            used, links = info
        else:
            approx = True
    if used is None:
        used = size
    try:
        attrs = os.stat(path, follow_symlinks=False).st_file_attributes if exact else 0
    except (OSError, AttributeError):
        attrs = 0
    return {'path': path, 'name': os.path.basename(path), 'dir': os.path.dirname(path), 'size': size, 'mtime': mtime,
            'used': used, 'links': links, 'sparse': bool(attrs & SPARSE), 'compressed': bool(attrs & COMPRESSED), 'approx': approx,
            'ext': os.path.splitext(path)[1].lower(), 'cat': category_of(os.path.splitext(path)[1].lower()),
            'level': level, 'why': why, 'can_delete': ok}


# ----------------------------------------------------------------------------------------------- cleanable places
def _globs(base, pattern_parts):
    """Folders matching base\\*\\part (one wildcard level, for browser profiles)."""
    out = []
    if not os.path.isdir(base):
        return out
    for prof in os.listdir(base):
        for part in pattern_parts:
            p = os.path.join(base, prof, part)
            if os.path.isdir(p):
                out.append(p)
    return out


DEV_DEPS = {'node_modules': ('package.json',), 'target': ('Cargo.toml',), '.venv': None, 'venv': None, 'env': None}
_dev = {'at': 0, 'dirs': []}


def dev_dirs(home=None, days=30, max_depth=6):
    """Dependency folders that a build tool makes again (2.6.0 #8): node_modules next to package.json, a Rust
    target next to Cargo.toml, a Python virtual environment (it has pyvenv.cfg) — only in projects whose own
    files have not changed for ``days`` days. AppData and hidden folders are not searched. Cached 10 minutes."""
    if home is None and time.time() - _dev['at'] < 600:
        return list(_dev['dirs'])
    root = home or env('USERPROFILE')
    limit, out = time.time() - days * 86400, []
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        names = {e.name for e in entries}
        newest = 0
        for e in entries:
            try:
                if e.is_file(follow_symlinks=False):
                    newest = max(newest, e.stat(follow_symlinks=False).st_mtime)
            except OSError:
                pass
        for e in entries:
            try:
                if not e.is_dir(follow_symlinks=False) or e.stat(follow_symlinks=False).st_file_attributes & REPARSE:
                    continue
            except (OSError, AttributeError):
                continue
            n = e.name
            if n in DEV_DEPS:
                need = DEV_DEPS[n]
                ok = (any(x in names for x in need) if need else os.path.isfile(os.path.join(e.path, 'pyvenv.cfg')))
                if ok:
                    if newest and newest < limit:
                        out.append(e.path)
                    continue  # never look inside a dependency folder
            if depth >= max_depth or n.startswith('.') or (depth == 0 and n.lower() in ('appdata', 'onedrive')):
                continue
            stack.append((e.path, depth + 1))
    if home is None:
        _dev.update(at=time.time(), dirs=out)
    return out


_health = {'at': 0, 'disks': []}


def disk_health():
    """Each physical disk's health as Windows itself reports it (Get-PhysicalDisk; no administrator rights,
    so no detailed SMART counters) — cached for an hour (2.6.0 #34)."""
    if time.time() - _health['at'] < 3600:
        return _health['disks']
    import json
    import subprocess
    disks = []
    try:
        r = subprocess.run(['powershell', '-NoProfile', '-Command',
                            'Get-PhysicalDisk | Select-Object FriendlyName,MediaType,HealthStatus,OperationalStatus,Size | ConvertTo-Json -Compress'],
                           capture_output=True, text=True, timeout=20, creationflags=0x08000000)
        data = json.loads(r.stdout or '[]')
        for d in data if isinstance(data, list) else [data]:
            disks.append({'name': d.get('FriendlyName') or '', 'media': d.get('MediaType') or '', 'size': d.get('Size') or 0,
                          'health': str(d.get('HealthStatus') or ''), 'status': str(d.get('OperationalStatus') or '')})
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    _health.update(at=time.time(), disks=disks)
    return disks


def places():
    """Every known place that only holds things that can be thrown away, with how and what it means."""
    la, home, win = env('LOCALAPPDATA'), env('USERPROFILE'), env('WINDIR', r'C:\Windows')
    cache_parts = ['Cache', 'Code Cache', 'GPUCache', os.path.join('Service Worker', 'CacheStorage')]
    return [
        {'id': 'temp', 'icon': 'clock', 'how': 'delete', 'level': 'safe', 'paths': [env('TEMP'), env('TMP')], 'fresh': True},
        {'id': 'wintemp', 'icon': 'clock', 'how': 'delete', 'level': 'safe', 'paths': [os.path.join(win, 'Temp')], 'fresh': True},
        {'id': 'edge', 'icon': 'globe', 'how': 'delete', 'level': 'safe',
         'paths': _globs(os.path.join(la, 'Microsoft', 'Edge', 'User Data'), cache_parts)},
        {'id': 'chrome', 'icon': 'globe', 'how': 'delete', 'level': 'safe',
         'paths': _globs(os.path.join(la, 'Google', 'Chrome', 'User Data'), cache_parts)},
        {'id': 'firefox', 'icon': 'globe', 'how': 'delete', 'level': 'safe',
         'paths': _globs(os.path.join(la, 'Mozilla', 'Firefox', 'Profiles'), ['cache2'])},
        # 2.6.0 #18: other browsers — only their caches; bookmarks, passwords and history are never touched
        {'id': 'otherbrowsers', 'icon': 'globe', 'how': 'delete', 'level': 'safe',
         'paths': [p for base in (os.path.join(la, 'BraveSoftware', 'Brave-Browser', 'User Data'), os.path.join(la, 'Vivaldi', 'User Data'),
                                  os.path.join(la, '360Chrome', 'Chrome', 'User Data'), os.path.join(la, 'Tencent', 'QQBrowser', 'User Data'))
                   for p in _globs(base, cache_parts)]
                  + [os.path.join(la, 'Opera Software', 'Opera Stable', 'Cache'), os.path.join(env('APPDATA'), 'Opera Software', 'Opera Stable', 'Cache')]},
        # 2.6.0 #36: shader caches of the graphics drivers and DirectX — rebuilt when a game or app needs them
        {'id': 'shaders', 'icon': 'image', 'how': 'delete', 'level': 'safe', 'fresh': True,
         'paths': [os.path.join(la, 'NVIDIA', 'DXCache'), os.path.join(la, 'NVIDIA', 'GLCache'), os.path.join(la, 'NVIDIA Corporation', 'NV_Cache'),
                   os.path.join(la, 'AMD', 'DxCache'), os.path.join(la, 'AMD', 'DxcCache'), os.path.join(la, 'AMD', 'GLCache'),
                   os.path.join(la, 'AMD', 'VkCache'), os.path.join(env('USERPROFILE'), 'AppData', 'LocalLow', 'Intel', 'ShaderCache'),
                   os.path.join(la, 'D3DSCache')]},
        {'id': 'crash', 'icon': 'warn', 'how': 'delete', 'level': 'safe',
         'paths': [os.path.join(la, 'CrashDumps'), os.path.join(la, 'Microsoft', 'Windows', 'WER'),
                   os.path.join(env('ProgramData', r'C:\ProgramData'), 'Microsoft', 'Windows', 'WER', 'ReportArchive')]},
        {'id': 'thumbs', 'icon': 'image', 'how': 'delete', 'level': 'safe', 'files': True,
         'paths': [os.path.join(la, 'Microsoft', 'Windows', 'Explorer')], 'match': ('thumbcache_', 'iconcache_')},
        {'id': 'devcache', 'icon': 'code', 'how': 'delete', 'level': 'safe',
         'paths': [os.path.join(la, 'pip', 'cache'), os.path.join(la, 'npm-cache'), os.path.join(la, 'Yarn', 'Cache'),
                   os.path.join(home, '.cache', 'pip')]},
        {'id': 'devprojects', 'icon': 'code', 'how': 'delete', 'level': 'safe', 'paths': dev_dirs()},  # 2.6.0 #8
        {'id': 'compress', 'icon': 'archive', 'how': 'compress', 'level': 'safe', 'files': True,  # 2.6.0 #15
         'paths': [home], 'only': compressible_files()},
        {'id': 'brokenlinks', 'icon': 'open', 'how': 'recycle', 'level': 'safe', 'files': True,  # 2.6.0 #12
         'paths': [os.path.join(home, 'Desktop'), os.path.join(env('APPDATA'), 'Microsoft', 'Windows', 'Start Menu'),
                   os.path.join(home, 'Downloads')], 'only': broken_shortcuts() + empty_folders()},
        {'id': 'oldinstallers', 'icon': 'download', 'how': 'recycle', 'level': 'safe', 'files': True,  # 2.6.0 #33
         'paths': [os.path.join(home, 'Downloads')], 'only': old_installer_versions()},
        {'id': 'installers', 'icon': 'download', 'how': 'recycle', 'level': 'safe', 'files': True, 'old_days': 30,
         'paths': [os.path.join(home, 'Downloads')], 'exts': INSTALLERS},
        {'id': 'winupdate', 'icon': 'shield', 'how': 'admin', 'level': 'safe',
         'paths': [os.path.join(win, 'SoftwareDistribution', 'Download')]},
        {'id': 'memdump', 'icon': 'warn', 'how': 'admin', 'level': 'safe', 'files': True,
         'paths': [win, os.path.join(win, 'Minidump')], 'exts': {'.dmp'}},
        {'id': 'winold', 'icon': 'shield', 'how': 'admin', 'level': 'safe', 'paths': [os.path.join(system_drive(), 'Windows.old')]},
        {'id': 'winupgrade', 'icon': 'shield', 'how': 'admin', 'level': 'safe',  # 2.6.0 #9
         'paths': [os.path.join(system_drive(), n) for n in ('$Windows.~BT', '$Windows.~WS', '$SysReset', '$GetCurrent')]},
        {'id': 'recycle', 'icon': 'trash', 'how': 'empty', 'level': 'caution', 'paths': []},
    ]


_links = {'at': 0, 'items': []}


def broken_shortcuts(folders=None):
    """Shortcuts (.lnk) on the Desktop and in the Start menu whose target no longer exists — left behind by
    uninstalled programs (2.6.0 #12). Targets are read by Windows itself (one PowerShell call); shortcuts to
    network places, URLs or without a file target are never counted as broken. Cached 10 minutes."""
    if folders is None and time.time() - _links['at'] < 600:
        return list(_links['items'])
    import json
    import subprocess
    folders = folders or [os.path.join(env('USERPROFILE'), 'Desktop'), os.path.join(env('APPDATA'), 'Microsoft', 'Windows', 'Start Menu')]
    lnks = []
    for f in folders:
        for d, _, files in os.walk(f):
            lnks += [os.path.join(d, n) for n in files if n.lower().endswith('.lnk')]
    out = []
    if lnks:
        script = ('[Console]::InputEncoding = [Text.Encoding]::UTF8; [Console]::OutputEncoding = [Text.Encoding]::UTF8; '  # Chinese paths
                  '$s = New-Object -ComObject WScript.Shell; $in = [Console]::In.ReadToEnd() | ConvertFrom-Json; '
                  '$in | ForEach-Object { try { $s.CreateShortcut($_).TargetPath } catch { "" } } | ConvertTo-Json -Compress')
        try:
            r = subprocess.run(['powershell', '-NoProfile', '-Command', script], input=json.dumps(lnks), capture_output=True,
                               text=True, encoding='utf-8', timeout=60, creationflags=0x08000000)
            targets = json.loads(r.stdout or '[]')
            targets = targets if isinstance(targets, list) else [targets]
            for lnk, tgt in zip(lnks, targets):
                tgt = tgt or ''
                if len(tgt) > 3 and tgt[1:3] == ':\\' and os.path.isdir(tgt[:3]) and not os.path.exists(tgt):
                    out.append(lnk)  # a local drive that is there, and the target is not
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    if folders is None or folders == [os.path.join(env('USERPROFILE'), 'Desktop'), os.path.join(env('APPDATA'), 'Microsoft', 'Windows', 'Start Menu')]:
        _links.update(at=time.time(), items=out)
    return out


def empty_folders(folder=None):
    """Folders in Downloads with nothing at all inside (also no hidden files) (2.6.0 #12)."""
    folder = folder or os.path.join(env('USERPROFILE'), 'Downloads')
    out = []
    for d, dirs, files in os.walk(folder, topdown=False):
        if d != folder and not files and not any(os.path.join(d, x) not in out for x in dirs):
            try:
                if not os.stat(d).st_file_attributes & REPARSE:
                    out.append(d)
            except (OSError, AttributeError):
                pass
    return [d for d in out if not any(d != o and d.startswith(o + os.sep) for o in out)]  # the outermost empty folder


LEFTOVER_SAFE = {'microsoft', 'windows', 'packages', 'temp', 'tmp', 'comms', 'connecteddevicesplatform', 'd3dscache', 'crashdumps',
                 'programs', 'publishers', 'virtualstore', 'nvidia', 'nvidiacorporation', 'intel', 'amd', 'apple', 'applecomputer',
                 'history', 'packagecache', 'packagecachesettings', 'ssh', 'npmcache', 'pip', 'yarn', 'desktoptrace', 'desktopwatch',
                 'regid19910811commicrosoft', 'usoshared', 'usoprivate', 'softwaredistribution', 'ssoxsoft', 'mozilla', 'google',
                 'package cache', 'paquetes', 'identities', 'peerdistrepub', 'oem', 'dell', 'lenovo', 'hp', 'asus', 'acer', 'realtek'}


# never suggested: game saves, software licences and activation, Windows accessibility (2.6.0 #2)
LEFTOVER_KEEP = ('save', 'licens', 'sentinel', 'flexnet', 'activation', 'narrator', 'voiceaccess', 'magnifier', 'backup', 'profile',
                 # vendors and game platforms that register under other names (Gemini 2.6.0 Q-3)
                 'dingtalk', 'alipay', 'taobao', 'aliworkbench', 'wechat', 'weixin', 'tencent', 'qq', 'wegame', 'steam', 'epicgames',
                 'hypergryph', 'mihoyo', 'hoyoverse', 'gog', 'blizzard', 'battle.net', 'riot', 'ubisoft', 'electronicarts', 'origin',
                 'netease', 'bytedance', 'douyin', 'baidu', 'kingsoft', 'wps', 'xunlei', 'thunder', 'huawei', 'xiaomi')
SAVE_EXTS = {'.sav', '.save', '.sl2', '.savegame', '.ess', '.rvdata2', '.profile'}


def _norm(x):
    return ''.join(ch for ch in x.lower() if ch.isalnum())


def installed_words():
    """Names that tell an installed program: display names, publishers and install folders from the
    uninstall list, Program Files folders and Start-menu folders (2.6.0 #2)."""
    words = set()
    if os.name == 'nt':
        import winreg
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall'),
                          (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'),
                          (winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Uninstall')):
            try:
                with winreg.OpenKey(hive, key) as k:
                    for i in range(winreg.QueryInfoKey(k)[0]):
                        try:
                            with winreg.OpenKey(k, winreg.EnumKey(k, i)) as a:
                                for v in ('DisplayName', 'Publisher', 'InstallLocation'):
                                    try:
                                        val = str(winreg.QueryValueEx(a, v)[0])
                                    except OSError:
                                        continue
                                    if v == 'InstallLocation':
                                        parts = [p for p in val.strip('"\\').split('\\') if p][-2:]
                                        words.update(_norm(p) for p in parts)
                                    else:
                                        words.add(_norm(val))
                                        words.update(_norm(w) for w in val.split() if len(w) >= 4)
                        except OSError:
                            pass
            except OSError:
                pass
    k = known_dirs()
    for base in k['programs'] + [os.path.join(env('LOCALAPPDATA'), 'Programs'),
                                 os.path.join(env('APPDATA'), 'Microsoft', 'Windows', 'Start Menu', 'Programs'),
                                 os.path.join(env('ProgramData', r'C:\ProgramData'), 'Microsoft', 'Windows', 'Start Menu', 'Programs')]:
        try:
            words.update(_norm(e.name) for e in os.scandir(base) if e.is_dir())
        except OSError:
            pass
    return {w for w in words if len(w) >= 3}


def _still_used(folder, days=90):
    """True if ``folder`` holds a program (.exe) or anything in its first two levels changed in ``days`` days."""
    limit = time.time() - days * 86400
    stack = [(folder, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if 'save' in e.name.lower():
                                return True  # a folder of game saves
                            if depth < 2:
                                stack.append((e.path, depth + 1))
                            continue
                        low = e.name.lower()
                        if (low.endswith('.exe') or os.path.splitext(low)[1] in SAVE_EXTS
                                or e.stat(follow_symlinks=False).st_mtime > limit):
                            return True  # a program, a game save, or still in use
                    except OSError:
                        pass
        except OSError:
            return True  # cannot look inside: never suggest it
    return False


def leftovers(sizes, words=None, min_size=300 * 2 ** 20):
    """Folders directly in AppData (Roaming, Local) or ProgramData, of ``min_size`` or more, whose name matches
    no installed program, publisher or install folder: possibly left behind by an uninstalled program
    (2.6.0 #2). ``sizes`` is folder -> bytes from the last scan. Only a hint: shown one by one, never ticked."""
    words = installed_words() if words is None else words
    bases = [env('APPDATA'), env('LOCALAPPDATA'), env('ProgramData', r'C:\ProgramData')]
    out = []
    for base in bases:
        try:
            entries = [e for e in os.scandir(base) if e.is_dir(follow_symlinks=False)]
        except OSError:
            continue
        for e in entries:
            n = _norm(e.name)
            size = sizes.get(e.path) or sizes.get(os.path.normpath(e.path)) or 0
            if size < min_size or not n or n in LEFTOVER_SAFE or e.name.startswith(('.', '{', '$')) or is_core(e.path):
                continue
            if any(len(w) >= 4 and (n in w or w in n) for w in words) or n in words:
                continue
            if any(k in n for k in LEFTOVER_KEEP) or _still_used(e.path):
                continue  # a program lives here (an .exe) or still writes here: not a leftover
            out.append({'path': e.path, 'name': e.name, 'size': size, 'where': os.path.basename(base)})
    return sorted(out, key=lambda x: -x['size'])


def lockers_many(paths, limit=20000):
    """Programs that have any of ``paths`` open (Restart Manager, in batches); [] when none (Gemini 2.6.0 Q-2)."""
    found = set()
    for i in range(0, min(len(paths), limit), 500):
        found.update(lockers(paths[i:i + 500]))
    return sorted(found)


def lockers(path):
    """Names of the programs that have ``path`` open, as Windows' Restart Manager reports them (2.6.0 #19);
    [] when none or when Windows cannot tell. Read-only: nothing is closed."""
    if os.name != 'nt':
        return []
    try:
        rm = ctypes.WinDLL('rstrtmgr')

        class RM_UNIQUE_PROCESS(ctypes.Structure):
            _fields_ = [('pid', wintypes.DWORD), ('start', wintypes.FILETIME)]

        class RM_PROCESS_INFO(ctypes.Structure):
            _fields_ = [('proc', RM_UNIQUE_PROCESS), ('app', ctypes.c_wchar * 256), ('svc', ctypes.c_wchar * 64),
                        ('type', ctypes.c_int), ('status', wintypes.DWORD), ('session', wintypes.DWORD), ('restartable', wintypes.BOOL)]
        session, key = wintypes.DWORD(), ctypes.create_unicode_buffer(64)
        if rm.RmStartSession(ctypes.byref(session), 0, key):
            return []
        try:
            items = [path] if isinstance(path, str) else list(path)
            files = (ctypes.c_wchar_p * len(items))(*items)
            if rm.RmRegisterResources(session, len(items), files, 0, None, 0, None):
                return []
            need, have, reasons = wintypes.UINT(), wintypes.UINT(0), wintypes.DWORD()
            rm.RmGetList(session, ctypes.byref(need), ctypes.byref(have), None, ctypes.byref(reasons))
            if not need.value:
                return []
            info = (RM_PROCESS_INFO * need.value)()
            have = wintypes.UINT(need.value)
            if rm.RmGetList(session, ctypes.byref(need), ctypes.byref(have), info, ctypes.byref(reasons)):
                return []
            return sorted({info[i].app for i in range(have.value) if info[i].app})
        finally:
            rm.RmEndSession(session)
    except (OSError, AttributeError):
        return []


COMPRESSIBLE = {'.log', '.txt', '.csv', '.tsv', '.json', '.xml', '.sql', '.md', '.html', '.htm', '.svg', '.bmp', '.wav',
                '.tif', '.tiff', '.psd', '.dump', '.trace', '.out', '.ldf', '.vmdk-log'}
_compressible = {'at': 0, 'files': []}


def compressible_files(home=None, min_size=20 * 2 ** 20, days=90):
    """Large files of kinds that compress well (text, logs, uncompressed images and sound) not changed for
    ``days`` days and not compressed yet — in your user folder, AppData and hidden folders left out (2.6.0 #15).
    Cached 10 minutes."""
    if home is None and time.time() - _compressible['at'] < 600:
        return list(_compressible['files'])
    root, limit, out = home or env('USERPROFILE'), time.time() - days * 86400, []
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        try:
            it = list(os.scandir(d))
        except OSError:
            continue
        for e in it:
            try:
                st = e.stat(follow_symlinks=False)
                attrs = getattr(st, 'st_file_attributes', 0)
                if attrs & REPARSE:
                    continue
                if e.is_dir(follow_symlinks=False):
                    if depth < 8 and not e.name.startswith('.') and not (depth == 0 and e.name.lower() in ('appdata', 'onedrive')):
                        stack.append((e.path, depth + 1))
                elif (st.st_size >= min_size and st.st_mtime < limit and os.path.splitext(e.name)[1].lower() in COMPRESSIBLE
                      and not attrs & (COMPRESSED | SPARSE | ONLINE_ONLY)):
                    out.append(e.path)
            except OSError:
                pass
    if home is None:
        _compressible.update(at=time.time(), files=out)
    return out


def _tree_size(d):
    total, stack = 0, [d]
    while stack:
        x = stack.pop()
        try:
            for e in os.scandir(x):
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    else:
                        total += e.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
        except OSError:
            pass
    return total


def git_repos(home=None, min_size=300 * 2 ** 20, max_depth=6):
    """Git repositories in your user folder whose history (.git) takes ``min_size`` or more (2.6.0 #29)."""
    root, out, stack = home or env('USERPROFILE'), [], [(home or env('USERPROFILE'), 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(os.scandir(d))
        except OSError:
            continue
        if any(e.name == '.git' and e.is_dir(follow_symlinks=False) for e in entries):
            size = _tree_size(os.path.join(d, '.git'))
            if size >= min_size:
                out.append({'path': d, 'name': os.path.basename(d), 'size': size})
            continue  # a repository's own folders are not searched for more
        for e in entries:
            try:
                if (e.is_dir(follow_symlinks=False) and depth < max_depth and not e.name.startswith('.')
                        and e.name not in DEV_DEPS and not (depth == 0 and e.name.lower() in ('appdata', 'onedrive'))):
                    stack.append((e.path, depth + 1))
            except OSError:
                pass
    return sorted(out, key=lambda x: -x['size'])


def _files_under(d):
    out = []
    for root, dirs, files in os.walk(d):
        dirs[:] = [x for x in dirs if not os.path.islink(os.path.join(root, x))
                   and not getattr(os.path, 'isjunction', lambda _: False)(os.path.join(root, x))]
        out += [os.path.join(root, f) for f in files]
    return out


def _sha256_file(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for block in iter(lambda: fh.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def movable(d, size):
    """Can be offered "Move to another drive" (2.6.0 #3): 1 GB or more, inside your user folder, not the user
    folder itself, not AppData or its three main folders, not a junction."""
    home = env('USERPROFILE')
    if size < 2 ** 30 or not home or not inside(d, home):
        return False
    n = os.path.normcase(os.path.normpath(d))
    fixed = {os.path.normcase(os.path.join(home, *p)) for p in ((), ('AppData',), ('AppData', 'Local'), ('AppData', 'Roaming'), ('AppData', 'LocalLow'))}
    return n not in fixed and not getattr(os.path, 'isjunction', lambda _: False)(d)


def move_folder(src, dest, progress=None):
    """Move folder ``src`` to ``dest`` (on another drive) and leave a junction at ``src`` pointing there, so
    programs find it as before (2.6.0 #3). Steps, each checked: rename ``src`` aside (fails at once if a
    file in it is open — nothing has happened then); copy; compare every file's content (SHA-256); make the
    junction; only then delete the set-aside original. On any failure the original is put back."""
    import shutil
    import subprocess
    progress = progress or (lambda **k: None)
    # A program may hold a file open with "share delete" (Chrome, Electron apps, VS Code…): Windows then allows
    # the rename below, and the program would go on writing to the old copy. Ask who has files open first.
    progress(step='check', done=0, total=0)
    busy = lockers_many(_files_under(src))
    if busy:
        return {'ok': False, 'code': 'inUse', 'by': busy}
    aside = src.rstrip('\\') + '.dtmove'
    try:
        os.rename(src, aside)
    except OSError:
        return {'ok': False, 'code': 'inUse', 'by': []}
    try:
        files = _files_under(aside)
        progress(step='copy', done=0, total=len(files))
        shutil.copytree(aside, dest, symlinks=True, dirs_exist_ok=False)
        for i, f in enumerate(files):  # every file's content, compared
            g = os.path.join(dest, os.path.relpath(f, aside))
            if os.path.getsize(f) != os.path.getsize(g) or _sha256_file(f) != _sha256_file(g):
                raise OSError('verify')
            progress(step='verify', done=i + 1, total=len(files))
        r = subprocess.run(['cmd', '/c', 'mklink', '/J', src, dest], capture_output=True, creationflags=0x08000000)
        if r.returncode != 0 or not os.path.isdir(src):
            raise OSError('junction')
    except (OSError, shutil.Error) as e:
        if os.path.isdir(src) and getattr(os.path, 'isjunction', lambda _: False)(src):
            os.rmdir(src)
        os.rename(aside, src)  # back as it was
        shutil.rmtree(dest, ignore_errors=True)
        return {'ok': False, 'code': 'moveFailed', 'why': str(e)[:200]}
    shutil.rmtree(aside, ignore_errors=True)
    if os.path.exists(aside):  # something could not be deleted after all: say where it is, never ignore it
        return {'ok': True, 'src': src, 'dest': dest, 'files': len(files), 'leftover': aside}
    return {'ok': True, 'src': src, 'dest': dest, 'files': len(files)}


def move_back(src, dest, progress=None):
    """Undo ``move_folder``: copy ``dest`` back, verify, replace the junction at ``src`` with the real folder,
    then delete ``dest`` (2.6.0 #3)."""
    import shutil
    progress = progress or (lambda **k: None)
    if not getattr(os.path, 'isjunction', lambda _: False)(src):
        return {'ok': False, 'code': 'notMoved'}
    tmp = src.rstrip('\\') + '.dtback'
    try:
        files = _files_under(dest)
        progress(step='copy', done=0, total=len(files))
        shutil.copytree(dest, tmp, symlinks=True)
        for i, f in enumerate(files):
            g = os.path.join(tmp, os.path.relpath(f, dest))
            if _sha256_file(f) != _sha256_file(g):
                raise OSError('verify')
            progress(step='verify', done=i + 1, total=len(files))
        os.rmdir(src)  # the junction only
        os.rename(tmp, src)
    except (OSError, shutil.Error) as e:
        shutil.rmtree(tmp, ignore_errors=True)
        return {'ok': False, 'code': 'moveFailed', 'why': str(e)[:200]}
    shutil.rmtree(dest, ignore_errors=True)
    return {'ok': True}


def recent_drafts(days=7, places_=None):
    """Recovery copies and unsaved drafts Office and WPS keep after a crash or a close without saving, changed
    in the last ``days`` days, newest first (2.6.0 #24). Only read; nothing is moved."""
    ad, la = env('APPDATA'), env('LOCALAPPDATA')
    places_ = places_ or [os.path.join(la, 'Microsoft', 'Office', 'UnsavedFiles'), os.path.join(ad, 'Microsoft', 'Word'),
                          os.path.join(ad, 'Microsoft', 'Excel'), os.path.join(ad, 'Microsoft', 'PowerPoint'),
                          os.path.join(ad, 'kingsoft', 'office6', 'backup'), os.path.join(ad, 'Kingsoft', 'office6', 'backup'),
                          env('TEMP')]
    limit, out, seen = time.time() - days * 86400, [], set()
    for base in places_:
        if not base or not os.path.isdir(base) or os.path.normcase(base) in seen:
            continue
        seen.add(os.path.normcase(base))
        for d, dirs, files in os.walk(base):
            if os.path.normcase(d).count(os.sep) - os.path.normcase(base).count(os.sep) >= 2:
                dirs[:] = []
            for f in files:
                p = os.path.join(d, f)
                low = f.lower()
                ext = os.path.splitext(low)[1]
                draft = is_draft(f) or 'unsavedfiles' in os.path.normcase(d) or 'backup' in os.path.normcase(d)
                if not draft or ext in ('.tmp',) and not low.startswith(('~wr', '~$')) or low.startswith('~$'):
                    continue  # "~$" files are only Office's lock files
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                if st.st_mtime >= limit and st.st_size > 0:
                    out.append({'path': p, 'name': f, 'size': st.st_size, 'mtime': st.st_mtime, 'app': os.path.basename(base)})
    return sorted(out, key=lambda x: -x['mtime'])


KEEP_LOCALES = ('en', 'zh')  # the languages DeskTrace speaks; a program's own other languages are listed


def language_packs(bases=None, min_size=20 * 2 ** 20):
    """Programs (Electron, Chromium, CEF and the like) that carry a "locales" folder of language packs: the
    space the packs other than English and Chinese take (2.6.0 #27). Listed only — deleting them breaks some
    programs' updates, so DeskTrace offers no delete."""
    k = known_dirs()
    bases = bases or k['programs'] + [os.path.join(env('LOCALAPPDATA'), 'Programs')]
    out = []
    for base in bases:
        for d, dirs, files in os.walk(base):
            depth = os.path.relpath(d, base).count(os.sep)
            if depth >= 4:
                dirs[:] = []
            if os.path.basename(d).lower() != 'locales':
                continue
            dirs[:] = []
            other = 0
            for f in files:
                low = f.lower()
                if low.endswith('.pak') and not low.startswith(KEEP_LOCALES):
                    try:
                        other += os.path.getsize(os.path.join(d, f))
                    except OSError:
                        pass
            if other >= min_size:
                out.append({'path': d, 'program': ' / '.join(os.path.relpath(d, base).split(os.sep)[:2]), 'size': other})
    return sorted(out, key=lambda x: -x['size'])


def _lp(p):
    return p if p.startswith('\\\\?\\') or len(p) < 240 else '\\\\?\\' + p


def bad_names(home=None, max_depth=12):
    """Files and folders in your user folder that Explorer cannot open, rename or delete: names ending in a
    space or a dot, and paths over 260 characters (2.6.0 #35). AppData and hidden folders are not searched."""
    root, out, stack = home or env('USERPROFILE'), [], [(home or env('USERPROFILE'), 0)]
    while stack:
        d, depth = stack.pop()
        try:
            entries = list(os.scandir(_lp(d)))
        except OSError:
            continue
        for e in entries:
            p = os.path.join(d, e.name)
            why = 'trailing' if e.name != e.name.rstrip(' .') else 'long' if len(p) >= 260 else None
            if why:
                out.append({'path': p, 'name': e.name, 'why': why, 'dir': e.is_dir(follow_symlinks=False)})
            try:
                if (e.is_dir(follow_symlinks=False) and depth < max_depth and not e.name.startswith('.')
                        and not (depth == 0 and e.name.lower() in ('appdata', 'onedrive')) and not why == 'long'):
                    stack.append((p, depth + 1))
            except OSError:
                pass
    return out


def fix_name(path):
    """Rename a file or folder so Windows can handle it: trailing spaces and dots removed; a path that is too
    long gets a shorter name (the start of the name and its extension). Never overwrites (2.6.0 #35)."""
    folder, name = os.path.dirname(path), os.path.basename(path)
    stem, ext = os.path.splitext(name.rstrip(' .'))
    new = (stem or 'renamed') + ext
    if len(os.path.join(folder, new)) >= 260:
        room = max(8, 259 - len(folder) - 1 - len(ext))
        new = stem[:room].rstrip(' .') + ext
    target, n = os.path.join(folder, new), 2
    raw = '\\\\?\\'  # always: without it Windows drops a trailing space or dot and cannot find the file
    while os.path.exists(raw + target):
        target, n = os.path.join(folder, f'{os.path.splitext(new)[0]} ({n}){os.path.splitext(new)[1]}'), n + 1
    try:
        os.rename(raw + path, raw + target)  # not abspath(): it would drop the trailing dot too
    except OSError:
        return {'ok': False, 'code': 'inUse'}
    return {'ok': True, 'path': target}


def old_installer_versions(folder=None):
    """Setup files in Downloads that have a newer version of the same program next to them: the name with its
    numbers taken out is the program ("app-setup-1.2.3.exe" ~ "app-setup-1.5.0.exe"); the newest stays (2.6.0 #33)."""
    import re
    folder = folder or os.path.join(env('USERPROFILE'), 'Downloads')
    groups = {}
    try:
        with os.scandir(folder) as it:
            for e in it:
                ext = os.path.splitext(e.name)[1].lower()
                if ext in INSTALLERS and e.is_file(follow_symlinks=False):
                    key = re.sub(r'[\s._()-]*\d+', '#', os.path.splitext(e.name)[0].lower()) + ext
                    groups.setdefault(key, []).append((e.stat().st_mtime, e.path))
    except OSError:
        return []
    return [p for g in groups.values() if len(g) > 1 for _, p in sorted(g)[:-1]]


def _place_files(pl):
    """(path, size, mtime) of every file a place would clean (skipping links, junctions and fresh files)."""
    now, out = time.time(), []
    if 'only' in pl:  # an explicit list of files (2.6.0)
        for p in pl['only']:
            try:
                st = os.stat(p, follow_symlinks=False)
                out.append((p, st.st_size, st.st_mtime))
            except OSError:
                pass
        return out
    seen = set()
    for base in pl['paths']:
        if not base or not os.path.isdir(base) or os.path.normcase(base) in seen:
            continue
        seen.add(os.path.normcase(base))
        stack = [base]
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except OSError:
                continue
            with it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                        if getattr(st, 'st_file_attributes', 0) & REPARSE:
                            continue
                        if e.is_dir(follow_symlinks=False):
                            if not pl.get('files') and not (pl.get('fresh') and is_draft(e.name, True)):
                                stack.append(e.path)
                            continue
                    except OSError:
                        continue
                    if pl.get('match') and not e.name.lower().startswith(pl['match']):
                        continue
                    if pl.get('exts') and os.path.splitext(e.name)[1].lower() not in pl['exts']:
                        continue
                    if pl.get('fresh') and (now - st.st_mtime < FRESH or is_draft(e.name)):
                        continue
                    if pl.get('old_days') and now - st.st_mtime < pl['old_days'] * 86400:
                        continue
                    out.append((e.path, st.st_size, st.st_mtime))
    return out


def recycle_bin(drive):
    """(bytes, items) in the Recycle Bin of one drive."""
    if os.name != 'nt':
        return 0, 0

    class Info(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.DWORD), ('size', ctypes.c_longlong), ('items', ctypes.c_longlong)]
    info = Info(cbSize=ctypes.sizeof(Info))
    if ctypes.windll.shell32.SHQueryRecycleBinW(drive, ctypes.byref(info)) != 0:
        return 0, 0
    return info.size, info.items


def cleanable(drive):
    """The cleanable places on ``drive`` with what they hold now."""
    drive = drive.upper()
    out = []
    for pl in places():
        if pl['id'] == 'recycle':
            size, n = recycle_bin(drive)
            if size:
                out.append({**{k: pl[k] for k in ('id', 'icon', 'how', 'level')}, 'size': size, 'count': n})
            continue
        pl['paths'] = [p for p in pl['paths'] if p and drive_of(p) == drive]
        if not pl['paths']:
            continue
        files = _place_files(pl)
        cl = cluster_size(drive)
        size = sum((f[1] + cl - 1) // cl * cl for f in files)  # disk usage, whole clusters (2.4.0 §6)
        if size:
            out.append({**{k: pl[k] for k in ('id', 'icon', 'how', 'level')}, 'size': size, 'count': len(files),
                        'where': pl['paths'][0] if len(pl['paths']) == 1 else os.path.commonpath(pl['paths']) if len({drive_of(p) for p in pl['paths']}) == 1 else ''})
    for a in chat_apps():
        if drive_of(a['data']) == drive:
            files = _place_files({'paths': [a['data']]})
            out.append({'id': a['id'], 'app': a['app'], 'icon': 'note', 'how': 'inapp', 'level': 'inapp', 'data': a['data'],
                        'exe': bool(a['exe']), 'size': sum(f[1] for f in files), 'count': len(files)})
    if drive == system_drive():
        h = hibernation()
        if h['size'] or h['on']:
            out.append({'id': 'hiber', 'icon': 'power', 'how': 'switch', 'level': 'safe', 'on': h['on'], 'size': h['size'], 'count': 1})
    out.sort(key=lambda x: -x['size'])
    return out


def clean(drive, place_id, recycle=None):
    """Clean one place on ``drive``: returns {freed, cleaned, failed}. Files in use are skipped."""
    drive = drive.upper()
    if place_id == 'recycle':
        before = recycle_bin(drive)[0]
        if os.name == 'nt':
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, drive, 0x1 | 0x2 | 0x4)  # no confirmation, progress or sound
        after = recycle_bin(drive)[0]
        return {'freed': max(0, before - after), 'cleaned': 1 if before > after else 0, 'failed': 1 if after else 0}
    pl = next((p for p in places() if p['id'] == place_id), None)
    if not pl or pl['how'] == 'admin':
        return {'freed': 0, 'cleaned': 0, 'failed': 0, 'code': 'notAllowed'}
    bases = [p for p in pl['paths'] if p and drive_of(p) == drive]
    pl['paths'] = bases
    freed = cleaned = failed = 0
    recycled = []
    for path, size, _ in _place_files(pl):
        if not any(inside(path, b) for b in bases):  # belt and braces: never outside the place itself
            continue
        try:
            if pl['how'] == 'compress':  # Windows' transparent NTFS compression: the file stays as it is (2.6.0 #15)
                import subprocess
                r = subprocess.run(['compact', '/c', '/q', '/i', path], capture_output=True, creationflags=0x08000000)
                after = compressed_size(path)
                if r.returncode != 0 or after is None or after >= size:
                    raise OSError
                freed += max(0, (size + 4095) // 4096 * 4096 - after)  # what the disk gives back
                cleaned += 1
                continue
            if pl['how'] == 'recycle':
                if recycle_problem(path) or not (recycle and recycle(path)):
                    raise OSError  # never "to the Recycle Bin" that would really be gone for good
                recycled.append(path)
            else:
                os.remove(path)
            freed += size
            cleaned += 1
        except OSError:
            failed += 1  # in use or not ours to delete: left alone
    if pl['how'] == 'delete' and not pl.get('files'):
        for b in bases:  # empty folders left behind (the place's own folder stays)
            _prune(b)
    return {'freed': freed, 'cleaned': cleaned, 'failed': failed, 'recycled': recycled[:5000]}


def _prune(d):
    """Remove the empty folders inside ``d``; True if ``d`` itself is empty now. Links and junctions are
    left as they are and never entered (os.walk would walk into junctions)."""
    empty = True
    try:
        entries = list(os.scandir(d))
    except OSError:
        return False
    for e in entries:
        try:
            st = e.stat(follow_symlinks=False)
            if not getattr(st, 'st_file_attributes', 0) & REPARSE and e.is_dir(follow_symlinks=False) and _prune(e.path):
                os.rmdir(e.path)
                continue
        except OSError:
            pass
        empty = False
    return empty


def delete_file(path, scan=None, recycle=None, permanent=False):
    """One file from the biggest-files list, to the Recycle Bin — only if its consequence allows it. When
    the Recycle Bin cannot take it, nothing happens unless the user chose ``permanent`` deletion."""
    level, why, ok = consequence(path)
    if not ok or not os.path.isfile(path):
        return {'ok': False, 'code': 'notAllowed' if not ok else 'gone'}
    size = os.path.getsize(path)
    if permanent:
        try:
            os.remove(path)
        except OSError:
            return {'ok': False, 'code': 'inUse', 'by': lockers(path)}
    else:
        problem = recycle_problem(path)
        if problem:
            return {'ok': False, 'code': problem, 'size': size}
        if not (recycle and recycle(path)):
            return {'ok': False, 'code': 'inUse', 'by': lockers(path)}
    if scan:
        scan.big = [b for b in scan.big if b[1] != path]
        heapq.heapify(scan.big)
    return {'ok': True, 'size': size, 'recycled': not permanent}
