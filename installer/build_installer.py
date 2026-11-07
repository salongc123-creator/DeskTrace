"""Build the DeskTrace installer for Windows 10/11 (64-bit).

    python installer\\build_installer.py            # stage + compile  ->  dist\\DeskTrace-Setup-<version>.exe
    python installer\\build_installer.py --stage    # only assemble build\\stage (no Inno Setup needed)

The installed program is self-contained: a trimmed copy of the Python that runs this script (no
Python needed on the target PC) plus the app. It installs per user, without admin rights, into
%LOCALAPPDATA%\\Programs\\DeskTrace; history lives separately in %LOCALAPPDATA%\\DeskTrace,
so a newer installer replaces the program and keeps the data (see DesktopWatch.iss).
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_SRC = ROOT / 'desktop_watch'
STAGE = ROOT / 'build' / 'stage'
DIST = ROOT / 'dist'
ISS = Path(__file__).resolve().parent / 'DesktopWatch.iss'

APP_FILES = ['cleaner.py', 'server.py', 'window.py', 'updates.py', 'extractors.py', 'tray.py', 'winwatch.py', 'xlsx.py', 'README.md']
SITE_PACKAGES = ['pypdf']  # pure-Python PDF text; PyMuPDF would be faster but adds ~100 MB
STDLIB_SKIP = {'test', 'tests', 'idle_test', 'idlelib', 'ensurepip', 'lib2to3', 'turtledemo', 'venv',
               'pydoc_data', 'site-packages', '__pycache__', 'distutils', 'unittest'}
DLL_SKIP = re.compile(r'^(_test|_ctypes_test|xxlimited|_xxtestfuzz|_testbuffer|_testcapi|_testclinic|'
                      r'_testconsole|_testimportmultiple|_testinternalcapi|_testmultiphase|_testsinglephase)', re.I)


def app_version():
    m = re.search(r"^APP_VERSION = '([^']+)'", (APP_SRC / 'server.py').read_text('utf-8'), re.M)
    return m.group(1)


def app_files():
    """The program files, as {path inside the program folder: source file} (installer and licenses)."""
    out = {name: APP_SRC / name for name in APP_FILES}
    for f in sorted((APP_SRC / 'static').rglob('*')):
        if f.is_file() and '__pycache__' not in f.parts:
            out[f.relative_to(APP_SRC).as_posix()] = f
    return out


def stage_runtime(dst):
    """A private Python: interpreter, DLLs, the standard library zipped, Tk for the folder picker."""
    py = Path(sys.base_prefix)
    ver = f'{sys.version_info.major}{sys.version_info.minor}'
    dst.mkdir(parents=True)
    for name in ['python.exe', 'pythonw.exe', 'python3.dll', f'python{ver}.dll', 'vcruntime140.dll',
                 'vcruntime140_1.dll', 'LICENSE.txt']:
        if (py / name).exists():
            shutil.copy2(py / name, dst / name)
    (dst / 'DLLs').mkdir()
    for f in (py / 'DLLs').iterdir():
        if f.is_file() and not DLL_SKIP.match(f.name):
            shutil.copy2(f, dst / 'DLLs' / f.name)
    if (py / 'tcl').is_dir():
        shutil.copytree(py / 'tcl', dst / 'tcl', ignore=shutil.ignore_patterns('*demos*', '*.chm'))

    lib = py / 'Lib'
    with zipfile.PyZipFile(dst / f'python{ver}.zip', 'w', zipfile.ZIP_DEFLATED, optimize=0) as z:
        keep = lambda p: not (set(Path(p).parts) & STDLIB_SKIP)  # noqa: E731
        z.writepy(str(lib), filterfunc=keep)   # top-level modules (writepy does not descend here)
        for pkg in sorted(p for p in lib.iterdir() if p.is_dir() and p.name not in STDLIB_SKIP
                          and (p / '__init__.py').exists()):
            z.writepy(str(pkg), filterfunc=keep)  # each package, with its subpackages
    site = dst / 'site-packages'
    for name in SITE_PACKAGES:
        shutil.copytree(lib / 'site-packages' / name, site / name, ignore=shutil.ignore_patterns('__pycache__'))
    # A ._pth file makes this interpreter ignore any Python installed on the PC: only these paths count.
    (dst / f'python{ver}._pth').write_text(f'python{ver}.zip\n.\nDLLs\nsite-packages\n..\\app\n', 'ascii')


def stage():
    if STAGE.exists():
        shutil.rmtree(STAGE)
    app = STAGE / 'app'
    for rel, src in app_files().items():
        (app / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, app / rel)
    stage_runtime(STAGE / 'runtime')
    size = sum(f.stat().st_size for f in STAGE.rglob('*') if f.is_file())
    print(f'staged {STAGE}  ({size / 1024 / 1024:.1f} MB)')


def find_iscc():
    for base in (os.environ.get('ProgramFiles(x86)'), os.environ.get('ProgramFiles'),
                 str(Path(os.environ.get('LOCALAPPDATA', '')) / 'Programs')):
        if base and (Path(base) / 'Inno Setup 6' / 'ISCC.exe').exists():
            return Path(base) / 'Inno Setup 6' / 'ISCC.exe'
    return shutil.which('iscc')


def compile_installer(version, test=False):
    iscc = find_iscc()
    if not iscc:
        sys.exit('Inno Setup 6 was not found (winget install JRSoftware.InnoSetup).')
    DIST.mkdir(exist_ok=True)
    defines = [f'/DAppVersion={version}']
    if test:  # side-by-side test build: other name, own data folder, leaves the real install alone
        (ROOT / 'build' / 'portable.txt').write_text('Data is kept in the "data" folder next to this file.\n')
        defines.append('/DTestBuild')
    subprocess.run([str(iscc), *defines, '/Q', str(ISS)], check=True)
    out = DIST / f"DeskTrace-{'TEST-' if test else ''}Setup-{version}.exe"
    print(f'built {out}  ({out.stat().st_size / 1024 / 1024:.1f} MB)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', action='store_true', help='only assemble the files, do not compile')
    ap.add_argument('--test', action='store_true', help='build a side-by-side test installer instead')
    args = ap.parse_args()
    stage()
    if not args.stage:
        compile_installer(app_version(), test=args.test)
