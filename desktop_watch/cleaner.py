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
            self.files, self.bytes = self.dirs[self.root][1], self.dirs[self.root][0]
            self.state = 'stopped' if self.stop else 'done'
        except Exception as e:  # a scan must never take the service down
            self.state, self.error = 'failed', repr(e)
        self.finished = time.time()
        if self.state == 'done' and self.on_done:
            try:
                self.on_done(self)
            except Exception:
                pass

    def _walk_top(self, top):
        """``top`` and everything below it. The folders two levels down are read in parallel when the user
        waits for the result on an SSD; in the background or on a spinning disk one at a time."""
        own_s, own_n, subdirs = self._list(top)
        units = []
        child_own = {}
        for c in subdirs:
            s, n, sub = self._list(c)
            child_own[c] = (s, n, sub)
            units.extend(sub)
        workers = 1 if (self.background or self.hdd or not self.priority) else min(4, max(2, (os.cpu_count() or 4) // 2))  # 2.4.1: at most 4
        results = {}
        if workers > 1 and len(units) > 8:
            results = self._in_processes(units, workers)
        if not results:
            for u in units:
                if self.stop:
                    break
                results[u] = self._walk_safe(u)
        total_s, total_n, kept_top = own_s, own_n, []
        for c, (s, n, sub) in child_own.items():
            cs, cn, kept = s, n, []
            for u in sub:
                us, un = results.get(u, (0, 0))
                cs, cn = cs + us, cn + un
                if us >= KEEP_MIN:
                    kept.append(u)
            self._keep(c, cs, cn, kept)
            total_s, total_n = total_s + cs, total_n + cn
            if cs >= KEEP_MIN:
                kept_top.append(c)
        self._keep(top, total_s, total_n, kept_top, force=True)
        return total_s, total_n

    def _in_processes(self, units, workers):
        """Read ``units`` in ``workers`` separate Python processes (2.4.0): Python itself runs one thread at a
        time, so real parallel reading needs processes. Each reports its progress and returns its totals;
        anything going wrong falls back to reading here."""
        import json
        import subprocess
        import sys
        groups = [units[i::workers] for i in range(workers)]
        procs, outs = [], {}
        try:
            for g in groups:
                pr = subprocess.Popen([sys.executable, os.path.abspath(__file__), '--scan-worker'], stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == 'nt' else 0)
                pr.stdin.write(json.dumps({'units': g, 'cluster': self.cluster, 'floor': 0}).encode('utf-8'))
                pr.stdin.close()
                procs.append(pr)

            def read(pr, k):
                base_f = base_b = 0
                for line in pr.stdout:
                    if line.startswith(b'P '):
                        f, b = map(int, line.split()[1:3])
                        with self._lock:
                            self.files, self.bytes = self.files + f - base_f, self.bytes + b - base_b
                        base_f, base_b = f, b
                    elif line.startswith(b'R '):
                        outs[k] = json.loads(line[2:])
            readers = [threading.Thread(target=read, args=(pr, k), daemon=True) for k, pr in enumerate(procs)]
            for r in readers:
                r.start()
            while any(r.is_alive() for r in readers):
                if self.stop:
                    for pr in procs:
                        pr.kill()
                    return {}
                time.sleep(0.2)
            if len(outs) != len(procs):
                return {}
        except OSError:
            for pr in procs:
                pr.kill()
            return {}
        results = {}
        with self._lock:
            self.files = self.bytes = 0
            for o in outs.values():
                results.update({u: tuple(v) for u, v in o['results'].items()})
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
        return results

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

    def _walk(self, d):
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
        self._keep(d, total_s, total_n, kept)
        return total_s, total_n

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
        return [{'path': d, 'name': os.path.basename(d) or d, 'size': s, 'files': n,
                 'shared': self.shared if os.path.normcase(d) == os.path.normcase(win) else 0} for s, n, d in sorted(out, reverse=True)]

    def own_files(self, folder, n=60):
        """The biggest files directly in ``folder`` (read now: the scan only keeps the drive's biggest)."""
        out = []
        try:
            with os.scandir(folder) as it:
                for e in it:
                    try:
                        st = e.stat(follow_symlinks=False)
                        if e.is_file(follow_symlinks=False) and not getattr(st, 'st_file_attributes', 0) & (REPARSE | ONLINE_ONLY):
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
        big = sorted(self.big, reverse=True)[:150]
        return {'folder': folder, 'size': whole[0], 'count': whole[1], 'folders': self.children(folder)[:40],
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


def _scan_worker():
    """A worker process of a fast scan: reads the folders it is given and prints its totals as JSON."""
    import json
    import sys
    job = json.loads(sys.stdin.buffer.read())
    sc = DriveScan('', start=False)
    sc.cluster = job['cluster']
    results, last = {}, 0
    for u in job['units']:
        results[u] = sc._walk_safe(u)
        if time.time() - last > 0.5:
            sys.stdout.write(f'P {sc.files} {sc.bytes}\n')
            sys.stdout.flush()
            last = time.time()
    out = {'results': results, 'dirs': [[d, list(v)] for d, v in sc.dirs.items()], 'kids': sc.kids, 'types': sc.types,
           'big': [list(b) for b in sc.big], 'online': sc.online, 'skipped': sc.skipped, 'tiny': sc.tiny}
    sys.stdout.write('R ' + json.dumps(out) + '\n')
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


def consequence(path):
    """What deleting this file means: (level, reason key, can delete). Levels: system (never), cloud
    (synced: deleting removes it online too), program (uninstall instead), inapp (clean up inside the app),
    caution (an app's own data), personal (yours: to the Recycle Bin), safe."""
    k = known_dirs()
    name, ext = os.path.basename(path).lower(), os.path.splitext(path)[1].lower()
    low = os.path.normcase(os.path.normpath(path)) + '\\'
    root_file = os.path.dirname(os.path.normpath(path)).rstrip('\\').endswith(':')
    if cloud_root_of(path):
        return 'cloud', 'cloud', False
    if inside(path, os.path.join(drive_of(path), 'Windows.old')):
        return 'system', 'winold', False
    if root_file and name in ('pagefile.sys', 'swapfile.sys'):
        return 'system', 'pagefile', False
    if root_file and name == 'hiberfil.sys':
        return 'system', 'hiberfil', False
    if inside(path, k['windows']) or name.endswith('.sys') or '\\system volume information' in path.lower():
        return 'system', 'windows', False
    if any(g in low for g in GAME_DIRS):
        return 'program', 'game', False
    if any(c in low for c in CHAT_DIRS):
        return 'inapp', 'chat', False
    if ext == '.pst':
        return 'inapp', 'pst', False
    if any(inside(path, p) for p in k['programs']):
        return 'program', 'program', False
    if inside(path, k['programdata']):
        return 'program', 'programdata', False
    if '\\.git\\' in low:
        return 'caution', 'git', True
    if ext == '.ost':
        return 'caution', 'ost', True
    if any(inside(path, a) for a in k['appdata']):
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
        {'id': 'crash', 'icon': 'warn', 'how': 'delete', 'level': 'safe',
         'paths': [os.path.join(la, 'CrashDumps'), os.path.join(la, 'Microsoft', 'Windows', 'WER'),
                   os.path.join(env('ProgramData', r'C:\ProgramData'), 'Microsoft', 'Windows', 'WER', 'ReportArchive')]},
        {'id': 'thumbs', 'icon': 'image', 'how': 'delete', 'level': 'safe', 'files': True,
         'paths': [os.path.join(la, 'Microsoft', 'Windows', 'Explorer')], 'match': ('thumbcache_', 'iconcache_')},
        {'id': 'devcache', 'icon': 'code', 'how': 'delete', 'level': 'safe',
         'paths': [os.path.join(la, 'pip', 'cache'), os.path.join(la, 'npm-cache'), os.path.join(la, 'Yarn', 'Cache'),
                   os.path.join(home, '.cache', 'pip')]},
        {'id': 'installers', 'icon': 'download', 'how': 'recycle', 'level': 'safe', 'files': True, 'old_days': 30,
         'paths': [os.path.join(home, 'Downloads')], 'exts': INSTALLERS},
        {'id': 'winupdate', 'icon': 'shield', 'how': 'admin', 'level': 'safe',
         'paths': [os.path.join(win, 'SoftwareDistribution', 'Download')]},
        {'id': 'memdump', 'icon': 'warn', 'how': 'admin', 'level': 'safe', 'files': True,
         'paths': [win, os.path.join(win, 'Minidump')], 'exts': {'.dmp'}},
        {'id': 'winold', 'icon': 'shield', 'how': 'admin', 'level': 'safe', 'paths': [os.path.join(system_drive(), 'Windows.old')]},
        {'id': 'recycle', 'icon': 'trash', 'how': 'empty', 'level': 'caution', 'paths': []},
    ]


def _place_files(pl):
    """(path, size, mtime) of every file a place would clean (skipping links, junctions and fresh files)."""
    now, out = time.time(), []
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
            return {'ok': False, 'code': 'inUse'}
    else:
        problem = recycle_problem(path)
        if problem:
            return {'ok': False, 'code': problem, 'size': size}
        if not (recycle and recycle(path)):
            return {'ok': False, 'code': 'inUse'}
    if scan:
        scan.big = [b for b in scan.big if b[1] != path]
        heapq.heapify(scan.big)
    return {'ok': True, 'size': size, 'recycled': not permanent}
