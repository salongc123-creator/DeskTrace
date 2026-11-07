"""Updates through version licenses.

A version license (``DeskTrace <version>.dtlicense``) is one signed file that carries a newer
version of the program. Put it into any monitored folder (the Desktop, by default): DeskTrace notices
it, checks its signature and offers the update — every time the window is opened, until it is installed —
and in the tray menu. Updating is never forced. The history and settings are kept; the new version
converts them on its first start if needed (server.py: migrate()).

File format (a zip archive):
    license.json   {"product", "version", "min_version", "released", "notes": {lang: text},
                    "changelog": [{"version", "date", "changes": [{"level": 1-5, "en", "zh", "de"}]}],
                    "files": {relative path: sha256}}

Change levels (installer/changelog.json, enforced by installer/release.py): 5 = an entirely new feature
(raises the second version digit, the third goes back to 0; after x.9 the first digit goes up), 4 = major
improvement, 3 = improvement, 2 = polish, 1 = fix (levels 1-4 raise the third digit).
    license.sig    hex RSA signature (PKCS#1 v1.5, SHA-256) of license.json, made with the release key
    app/<path>     the program files listed in "files" (they replace the installed program folder)

Licenses are made with installer/make_license.py, which holds the private half of the release key.

This file also is the updater: ``pythonw updates.py --apply ...`` (started by the running version with the
copy of this file taken from the NEW license, so each version installs itself). It waits for the old
version to exit, swaps the program folder (keeping a portable copy's data), records the result and
starts the new version. Keep its command line compatible with older versions.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

PRODUCT = 'desktop-watch'
EXT = '.dtlicense'
# Public half of the release key. Only licenses signed with the matching private key are accepted.
PUBLIC_KEY = {'e': 65537, 'n': int(
    'ba5d07fe959e9a32b573911920a85b540103e8ef57c156daf06ef1f61d439906640d68b2a9eed869680ab9bc2f69d8f743ef7bbe053304084e84810187e038d2453fde2af694e0982d8ab79b2db52f46fff22bb1916ca0f396689099027eaad799440245a3fe86b9d62fe0aaa1a26ea203dbf1f09dab9b34da15aa371dc7cf611eb53986cdb5a3fe82f825e02b759b83699a3ae505a052f98876089c0049f5a9c428d7abcad17fc4120b633498456e5104645036689f5dfceca7c64edb745a66e4aa29e2af8380f36e57fb8683e6a361555637a5aa2f07636f9413e7cb850fc2c0245d63a5d138fbb77827be5713b0a58ac0114641d0bae74143f11e1c86ed898c5d289509ae532e79c7225ab0bc107e058fcde953446294d0515e9fc1c9e6dfad880f716042684fb638fcbf340e2bc9ea4f1e29b625709a7dd36bfee31d04e4186da86be14c3cf101d126e9364dcf148e9a8a442f15344612384f76eb68fd8bad540afb30971ca4995dc76cf706b968e6c6693ae96aed3d5b526441f79f4bfb', 16)}
DIGEST_INFO_SHA256 = bytes.fromhex('3031300d060960864801650304020105000420')
KEEP_IN_APP = ('data', 'portable.txt')  # a portable / test copy keeps its history inside the program folder
NO_WINDOW = 0x08000000


class LicenseError(Exception):
    """Why a license file can't be used: signature, product, contents, damaged, not-newer, too-old."""

    def __init__(self, code, detail=''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code


def net_changes(changelog, current, removed=None):
    """The changes a jump from ``current`` really brings (2.6.0): changes to a feature that is removed again
    before the newest version are left out, and a "… was removed" line only stays if the user had one of the
    features it removes. ``removed`` maps feature -> version it was removed in (from the license); entries
    carry "feature" or "removes" ({feature: version it came in}) tags. Untagged entries are kept as they are."""
    cur = vtuple(current)
    newest = max((vtuple(r['version']) for r in changelog), default=cur)
    removed = {f: vtuple(v) for f, v in (removed or {}).items() if vtuple(v) <= newest}
    out = []
    for rel in changelog:
        v = vtuple(rel['version'])
        if v <= cur:
            continue
        keep = []
        for c in rel.get('changes', []):
            f = c.get('feature')
            if f and f in removed and removed[f] > v:
                continue  # added or changed in this jump, removed again later in it
            if c.get('removal_only') and not any(vtuple(since) <= cur for since in (c.get('removes') or {}).values()):
                continue  # removes only things this user never had
            keep.append(c)
        if rel.get('changes') and not keep:
            continue  # everything this release did was undone later in the jump
        out.append({**rel, 'changes': keep})
    return out


def vtuple(v):
    return tuple(int(x) for x in re.findall(r'\d+', str(v))[:4]) or (0,)


def verify_signature(data, sig_hex, key=None):
    key = key or PUBLIC_KEY
    n, e = key['n'], key['e']
    size = (n.bit_length() + 7) // 8
    try:
        s = int(sig_hex, 16)
    except ValueError:
        return False
    if not 0 < s < n:
        return False
    em = pow(s, e, n).to_bytes(size, 'big')
    t = DIGEST_INFO_SHA256 + hashlib.sha256(data).digest()
    return hmac.compare_digest(em, b'\x00\x01' + b'\xff' * (size - len(t) - 3) + b'\x00' + t)


def safe_rel(p):
    parts = Path(p).parts
    return bool(parts) and not Path(p).is_absolute() and '..' not in parts and ':' not in p and not p.startswith(('/', '\\'))


def read_license(path, current=None, key=None):
    """The checked contents of a license file (its license.json). Raises LicenseError if the file is not a
    genuine, intact license for this product, or (with ``current``) not an upgrade from that version."""
    try:
        with zipfile.ZipFile(path) as z:
            raw = z.read('license.json')
            if not verify_signature(raw, z.read('license.sig').decode('ascii', 'replace').strip(), key):
                raise LicenseError('signature')
            meta = json.loads(raw)
            if meta.get('product') != PRODUCT or not meta.get('version') or not isinstance(meta.get('files'), dict):
                raise LicenseError('product')
            files = meta['files']
            if not all(safe_rel(p) for p in files) or 'server.py' not in files:
                raise LicenseError('contents')
            if set(z.namelist()) - {'license.json', 'license.sig'} != {'app/' + p for p in files}:
                raise LicenseError('contents')
            for p, h in files.items():
                if hashlib.sha256(z.read('app/' + p)).hexdigest() != h:
                    raise LicenseError('contents', p)
    except LicenseError:
        raise
    except (OSError, KeyError, ValueError, zipfile.BadZipFile, UnicodeDecodeError) as e:
        raise LicenseError('damaged', repr(e))
    if current is not None:
        if vtuple(meta['version']) <= vtuple(current):
            raise LicenseError('not-newer', meta['version'])
        if vtuple(current) < vtuple(meta.get('min_version') or '0'):
            raise LicenseError('too-old', meta.get('min_version'))
    return meta


def installed_layout(app_dir):
    """True for an installed copy: <install>/app (this program) next to <install>/runtime (its Python)."""
    app_dir = Path(app_dir)
    return app_dir.name.lower() == 'app' and (app_dir.parent / 'runtime' / 'pythonw.exe').exists()


class Updates:
    """Finds, keeps and applies version licenses for the running program (used by server.py)."""

    def __init__(self, data_dir, app_dir, current, on_found=None):
        self.dir = Path(data_dir) / 'updates'
        self.app_dir, self.current = Path(app_dir), current
        self.on_found = on_found or (lambda meta: None)
        self.available = {}   # version -> license.json of a usable newer license, plus 'file' and 'source'
        self.rejected = {}    # path -> reason, for licenses found but not usable
        self.result = None    # outcome of the last update (shown once by the window)
        self.load()

    @property
    def pending(self):
        """The newest update waiting (or None)."""
        return self.available[max(self.available, key=vtuple)] if self.available else None

    def load(self):
        """Licenses kept from earlier runs (the prompt comes back until an update is installed)."""
        try:
            self.result = json.loads((self.dir / 'result.json').read_text('utf-8'))
        except (OSError, ValueError):
            self.result = None
        for f in sorted(self.dir.glob('*' + EXT)) if self.dir.is_dir() else []:
            try:
                meta = read_license(f, self.current)
            except LicenseError:
                for x in (f, f.with_suffix('.source')):  # installed already (or older than what is installed)
                    try:
                        x.unlink()
                    except OSError:
                        pass
                continue
            src = f.with_suffix('.source')
            self.available[meta['version']] = {**meta, 'file': str(f), 'source': src.read_text('utf-8') if src.exists() else ''}

    def consider(self, path):
        """A license file appeared in a monitored folder. Returns True if it offers a new update.
        Every newer version found is kept, so the user can choose which one to install; a version that
        was already found is skipped."""
        path = str(path)
        if not path.lower().endswith(EXT):
            return False
        try:
            meta = read_license(path, self.current)
        except LicenseError as e:
            self.rejected[path] = e.code
            print(f'license {path}: {e}')
            return False
        self.rejected.pop(path, None)
        if meta['version'] in self.available:
            return False  # already detected: skip it
        self.dir.mkdir(parents=True, exist_ok=True)
        kept = self.dir / f"{meta['version']}{EXT}"
        shutil.copyfile(path, kept)
        kept.with_suffix('.source').write_text(path, 'utf-8')
        self.available[meta['version']] = {**meta, 'file': str(kept), 'source': path}
        print(f"update {meta['version']} found: {path}")
        self.on_found(self.available[meta['version']])
        return True

    def changes(self, meta, lang):
        """What installing ``meta`` brings, version by version (newest first), from after the current one.
        Licenses carry the whole changelog up to their own version, each change with its level (1-5)."""
        out = []
        for rel in net_changes(meta.get('changelog') or [], self.current, meta.get('removed_features')):  # 2.6.0: net of removals
            items = [{'level': c['level'], 'text': c.get(lang) or c.get('en', '')} for c in rel.get('changes', [])]
            notes = rel.get('notes') or {}
            out.append({'version': rel['version'], 'released': rel.get('date'), 'items': items,
                        'notes': notes.get(lang) or notes.get('en') or ''})
        if not out:  # an older license without a changelog
            notes = meta.get('notes') or {}
            out.append({'version': meta['version'], 'released': meta.get('released'), 'items': [],
                        'notes': notes.get(lang) or notes.get('en') or ''})
        return sorted(out, key=lambda r: vtuple(r['version']), reverse=True)

    def status(self, lang='en'):
        versions = [{'version': v, 'released': m.get('released'), 'source': m.get('source'),
                     'top': max([c['level'] for r in self.changes(m, lang) for c in r['items']] or [0]),
                     'changes': self.changes(m, lang)}
                    for v, m in sorted(self.available.items(), key=lambda x: vtuple(x[0]), reverse=True)]
        p = self.pending
        notes = (p.get('notes') or {}) if p else {}
        return {'current': self.current, 'available': bool(p), 'version': p and p['version'],
                'released': p and p.get('released'), 'notes': notes.get(lang) or notes.get('en') or '',
                'source': p and p.get('source'), 'can_apply': installed_layout(self.app_dir),
                'versions': versions,
                'rejected': [{'path': k, 'reason': v} for k, v in self.rejected.items()
                             if v != 'not-newer' and os.path.exists(k)],
                'result': self.result}

    def seen_result(self):
        self.result = None
        try:
            (self.dir / 'result.json').unlink()
        except OSError:
            pass

    def apply(self, server_pid, open_window=True, version=None):
        """Start the updater (the chosen version's own copy of this file) and return; the caller must then
        exit so the program files can be replaced. ``version`` defaults to the newest one found."""
        meta = self.available.get(version) if version else self.pending
        if not meta:
            raise LicenseError('none')
        if not installed_layout(self.app_dir):
            raise LicenseError('not-installed')
        lic = Path(meta['file'])
        read_license(lic, self.current)  # still intact?
        updater = self.dir / 'updater.py'
        with zipfile.ZipFile(lic) as z:
            names = z.namelist()
            updater.write_bytes(z.read('app/updates.py') if 'app/updates.py' in names else Path(__file__).read_bytes())
        install = self.app_dir.parent
        pyw = install / 'runtime' / 'pythonw.exe'
        args = [str(pyw), '-I', str(updater), '--apply', str(lic), '--install', str(install), '--pid', str(server_pid),
                '--current', self.current, '--data', str(self.dir.parent)]
        if open_window:
            args.append('--open')
        subprocess.Popen(args, cwd=str(install), creationflags=NO_WINDOW, close_fds=True)
        return meta['version']


# -- the updater (runs on its own, after the running version has exited) -------------------------------------------
def _log(msg):
    try:
        with open(Path(os.environ.get('TEMP', '.')) / 'DeskTrace-update.log', 'a', encoding='utf-8') as f:
            f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S")}  {msg}\n')
    except OSError:
        pass


def _wait_for_exit(pid, timeout=60):
    if not pid or os.name != 'nt':
        return
    import ctypes
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.restype = ctypes.c_void_p
    h = k32.OpenProcess(0x00100000, False, pid)  # SYNCHRONIZE
    if not h:
        return  # already gone
    try:
        if k32.WaitForSingleObject(ctypes.c_void_p(h), int(timeout * 1000)) != 0:
            _log(f'old version (pid {pid}) did not exit; ending it')
            subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, creationflags=NO_WINDOW)
            time.sleep(1)
    finally:
        k32.CloseHandle(ctypes.c_void_p(h))


def _retry(fn, tries=40, delay=0.25):
    """Renames can fail for a moment while antivirus or the indexer still looks at a file."""
    for i in range(tries):
        try:
            return fn()
        except OSError:
            if i == tries - 1:
                raise
            time.sleep(delay)


def _set_registered_version(install, version):
    """Keep "Installed apps" (the installer's uninstall entry) showing the version actually installed."""
    if os.name != 'nt':
        return
    import winreg
    base = r'Software\Microsoft\Windows\CurrentVersion\Uninstall'
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, base) as root:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(root, i)
                except OSError:
                    break
                i += 1
                try:
                    with winreg.OpenKey(root, name, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as k:
                        loc = winreg.QueryValueEx(k, 'Inno Setup: App Path')[0]
                        if os.path.normcase(os.path.normpath(loc)) == os.path.normcase(os.path.normpath(str(install))):
                            winreg.SetValueEx(k, 'DisplayVersion', 0, winreg.REG_SZ, version)
                            dn = winreg.QueryValueEx(k, 'DisplayName')[0]
                            if re.search(r'\d+\.\d+', dn):
                                winreg.SetValueEx(k, 'DisplayName', 0, winreg.REG_SZ, re.sub(r'\d+(\.\d+)+', version, dn))
                except OSError:
                    continue
    except OSError:
        pass


def run_updater(args):
    install = Path(args.install)
    app, new, old = install / 'app', install / 'app.new', install / 'app.old'
    data = Path(args.data)
    result = {'ok': False, 'from': args.current, 'to': None, 'ts': time.time()}
    _log(f'updating {install} from {args.current} with {args.apply}')
    _wait_for_exit(args.pid)
    swapped = False
    try:
        meta = read_license(args.apply, args.current)
        result['to'] = meta['version']
        # what this update brought, so the window can show "What's new" afterwards (2.0.1)
        result['changelog'] = net_changes(meta.get('changelog') or [], args.current, meta.get('removed_features'))  # 2.6.0
        for d in (new, old):
            if d.exists():
                shutil.rmtree(d)
        with zipfile.ZipFile(args.apply) as z:
            for p in meta['files']:
                dest = new / p
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read('app/' + p))
        _retry(lambda: app.rename(old))
        try:
            _retry(lambda: new.rename(app))
        except OSError:
            _retry(lambda: old.rename(app))  # put the old version back
            raise
        swapped = True
        for name in KEEP_IN_APP:  # a portable copy's history and marker move into the new program folder
            if (old / name).exists():
                _retry(lambda: (old / name).rename(app / name))
        swapped = False
        shutil.rmtree(old, ignore_errors=True)
        _set_registered_version(install, meta['version'])
        result['ok'] = True
        _log(f"updated to {meta['version']}")
    except Exception as e:
        result['error'] = f'{type(e).__name__}: {e}'
        _log('update failed: ' + result['error'])
        if swapped:  # roll back completely: the old program folder, with everything that belongs in it
            try:
                for name in KEEP_IN_APP:
                    if (app / name).exists() and not (old / name).exists():
                        _retry(lambda: (app / name).rename(old / name))
                _retry(lambda: app.rename(new))
                _retry(lambda: old.rename(app))
            except OSError as e2:
                _log(f'ROLLBACK FAILED: {e2!r} (old version is in {old})')
        if new.exists() and app.exists():
            shutil.rmtree(new, ignore_errors=True)
    if result['ok']:  # the installed license is done with; other (newer) ones stay on offer
        for f in (Path(args.apply), Path(args.apply).with_suffix('.source')):
            try:
                f.unlink()
            except OSError:
                pass
    try:
        # the data folder of a portable copy has just moved along with the program
        data = data if data.exists() else app / 'data'
        (data / 'updates').mkdir(parents=True, exist_ok=True)
        (data / 'updates' / 'result.json').write_text(json.dumps(result), 'utf-8')
    except OSError:
        pass
    start = [str(install / 'runtime' / 'pythonw.exe'), str(app / 'server.py')] + ([] if args.open else ['--no-browser'])
    subprocess.Popen(start, cwd=str(app), creationflags=NO_WINDOW, close_fds=True)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='DeskTrace updater')
    ap.add_argument('--apply', required=True, help='the license file to install')
    ap.add_argument('--install', required=True, help='installation folder (holds app and runtime)')
    ap.add_argument('--pid', type=int, help='process of the running version to wait for')
    ap.add_argument('--current', required=True, help='version being replaced')
    ap.add_argument('--data', required=True, help='data folder of the running version')
    ap.add_argument('--open', action='store_true', help='open the window after updating')
    run_updater(ap.parse_args())
