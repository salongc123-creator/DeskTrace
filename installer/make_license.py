"""Make a version license: one signed file that updates installed copies of DeskTrace.

    python installer\\make_license.py [--min-version 1.6] [--notes-en "..."] [--notes-zh "..."] [--notes-de "..."]
        -> dist\\DeskTrace <version>.dtlicense   (version = APP_VERSION in server.py)

Users put the file into a monitored folder (the Desktop, by default); DeskTrace then offers the update.
The license is signed with the release key in installer\\keys\\release-key.json. That file is the only
thing that can make licenses the app accepts: keep it private and back it up. If it is lost, later
versions can only be shipped with the installer (which can also bring a new public key).

    python installer\\make_license.py --new-key     # once: create the key and put its public half in updates.py
"""
import argparse
import hashlib
import json
import re
import secrets
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'installer'))
sys.path.insert(0, str(ROOT / 'desktop_watch'))
from build_installer import APP_SRC, DIST, app_files, app_version  # noqa: E402
import updates  # noqa: E402

KEY_FILE = ROOT / 'installer' / 'keys' / 'release-key.json'
SMALL_PRIMES = [p for p in range(3, 2000) if all(p % d for d in range(2, int(p ** 0.5) + 1))]


def probable_prime(n, rounds=48):
    if any(n % p == 0 for p in SMALL_PRIMES):
        return n in SMALL_PRIMES
    d, r = n - 1, 0
    while d % 2 == 0:
        d, r = d // 2, r + 1
    for _ in range(rounds):
        x = pow(secrets.randbelow(n - 3) + 2, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def new_prime(bits):
    while True:
        c = secrets.randbits(bits) | (3 << (bits - 2)) | 1
        if probable_prime(c):
            return c


def new_key(bits=3072):
    e = 65537
    while True:
        p, q = new_prime(bits // 2), new_prime(bits // 2)
        phi = (p - 1) * (q - 1)
        if p != q and phi % e:
            n = p * q
            if n.bit_length() == bits:
                return {'n': n, 'e': e, 'd': pow(e, -1, phi)}


def sign(data, key):
    size = (key['n'].bit_length() + 7) // 8
    t = updates.DIGEST_INFO_SHA256 + hashlib.sha256(data).digest()
    em = b'\x00\x01' + b'\xff' * (size - len(t) - 3) + b'\x00' + t
    return format(pow(int.from_bytes(em, 'big'), key['d'], key['n']), 'x')


def load_key():
    k = json.loads(KEY_FILE.read_text('ascii'))
    return {'n': int(k['n'], 16), 'e': k['e'], 'd': int(k['d'], 16)}


def install_public_key(key):
    src = APP_SRC / 'updates.py'
    text = src.read_text('utf-8')
    text, n = re.subn(r"(PUBLIC_KEY = \{'e': 65537, 'n': int\(\s*')[^']*(', 16\)\})", lambda m: m.group(1) + format(key['n'], 'x') + m.group(2), text)
    if n != 1:
        sys.exit('could not find PUBLIC_KEY in updates.py')
    src.write_text(text, 'utf-8')


def make_license(version, min_version, notes, key, out=None, files=None, changelog=None, removed=None):
    files = {rel: Path(src).read_bytes() for rel, src in (files or app_files()).items()}
    # The packaged program must call itself by the license's version, or it would keep offering itself.
    files['server.py'], n = re.subn(rb"^APP_VERSION = '[^']*'", f"APP_VERSION = '{version}'".encode(), files['server.py'], flags=re.M)
    if n != 1:
        sys.exit('APP_VERSION not found in server.py')
    manifest = {rel: hashlib.sha256(data).hexdigest() for rel, data in files.items()}
    meta = {'product': updates.PRODUCT, 'version': version, 'min_version': min_version,
            'released': time.strftime('%Y-%m-%d'), 'notes': {k: v for k, v in notes.items() if v}, 'files': manifest}
    if changelog:
        meta['changelog'] = changelog
    if removed:
        meta['removed_features'] = removed  # feature -> version it was removed in (2.6.0)
    raw = json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True).encode('utf-8')
    out = Path(out or DIST / f'DeskTrace {version}{updates.EXT}')
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr('license.json', raw)
        z.writestr('license.sig', sign(raw, key))
        for rel, data in sorted(files.items()):
            z.writestr('app/' + rel, data)
    pub = {'n': key['n'], 'e': key['e']}
    updates.read_license(out, key=pub)  # self-check: the app will accept it
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--new-key', action='store_true', help='create the release key (once) and put it in updates.py')
    ap.add_argument('--min-version', default='1.6', help='oldest installed version this license can update')
    ap.add_argument('--version', help='default: APP_VERSION in server.py')
    for lang in ('en', 'zh', 'de'):
        ap.add_argument(f'--notes-{lang}', default='', help=f'release notes ({lang})')
    ap.add_argument('--notes-file', help='JSON file {"en": "...", "zh": "...", "de": "..."} with the release notes')
    ap.add_argument('--out')
    a = ap.parse_args()
    if a.notes_file:
        nf = json.loads(Path(a.notes_file).read_text('utf-8'))
        a.notes_en, a.notes_zh, a.notes_de = nf.get('en', ''), nf.get('zh', ''), nf.get('de', '')
    if a.new_key:
        if KEY_FILE.exists():
            sys.exit(f'{KEY_FILE} already exists — refusing to replace the release key.')
        key = new_key()
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(json.dumps({'n': format(key['n'], 'x'), 'e': key['e'], 'd': format(key['d'], 'x')}), 'ascii')
        install_public_key(key)
        print(f'created {KEY_FILE} and put its public half into updates.py — keep the key file private and backed up')
        sys.exit()
    key = load_key()
    if key['n'] != updates.PUBLIC_KEY['n']:
        sys.exit('updates.py holds a different public key than installer\\keys\\release-key.json')
    out = make_license(a.version or app_version(), a.min_version,
                       {'en': a.notes_en, 'zh': a.notes_zh, 'de': a.notes_de}, key, a.out)
    print(f'built {out}  ({out.stat().st_size / 1024:.0f} KB)')
