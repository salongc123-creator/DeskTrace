"""Apply a small fix to already-built (not yet published) version licenses and the base installer,
keeping each version's own program files otherwise unchanged.

    python installer\\patch_release.py <patch file> <published path> [--installer 1.6]

The patch file's text is appended to that published path (e.g. a CSS fix to static/app.css) in every
license in dist\\licenses; each is re-signed. With --installer, the base installer of that version is
rebuilt from the first license's files (its version number put back)."""
import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_installer as bi  # noqa: E402
import make_license as ml  # noqa: E402


def unpack(lic, dest):
    with zipfile.ZipFile(lic) as z:
        meta = json.loads(z.read('license.json'))
        files = {}
        for rel in meta['files']:
            p = dest / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(z.read('app/' + rel))
            files[rel] = p
    return meta, files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('patch')
    ap.add_argument('target')
    ap.add_argument('--installer')
    a = ap.parse_args()
    extra = Path(a.patch).read_text('utf-8')
    key = ml.load_key()
    lics = sorted((HERE.parent / 'dist' / 'licenses').glob('*' + ml.updates.EXT), key=lambda p: ml.updates.vtuple(p.stem.split()[-1]))
    for lic in lics:
        with tempfile.TemporaryDirectory() as tmp:
            meta, files = unpack(lic, Path(tmp))
            t = files[a.target]
            t.write_text(t.read_text('utf-8').rstrip('\n') + '\n' + extra, 'utf-8')
            ml.make_license(meta['version'], meta.get('min_version', '1.6'), meta.get('notes') or {}, key, lic, files=files,
                            changelog=meta.get('changelog'))
            print('re-signed', lic.name)
    if a.installer:
        tmp = Path(tempfile.mkdtemp())
        meta, files = unpack(lics[0], tmp)
        s = files['server.py']
        s.write_text(re.sub(r"^APP_VERSION = '[^']*'", f"APP_VERSION = '{a.installer}'", s.read_text('utf-8'), flags=re.M), 'utf-8')
        bi.app_files = lambda: files
        for test in (False, True):
            bi.stage()
            bi.compile_installer(a.installer, test=test)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
