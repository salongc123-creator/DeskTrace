"""DeskTrace (桌迹, formerly Desktop Watch) — real-time file change monitor with versioned content previews.

Run:  pythonw server.py [--port 8765] [--no-browser]
The interface opens in its own app window (window.py). The local HTTP server behind it only answers
that window (a per-start key, handed over as a cookie), not a web browser.

How it works
  * Windows change notifications wake the scanner the moment something changes; a full
    rescan also runs periodically as a safety net (and is the only mechanism elsewhere).
    A change is recorded once the file has been stable across two scans, which filters
    out half-written files and the temp-file shuffle Office does on save.
  * Every created/modified file (up to the snapshot size limit) is copied into a
    content-addressed store, so each event can be previewed exactly as it was.
  * On first run the existing documents are indexed in the background (text only, plus
    a copy of small files) so the very first edit/delete already has a "before".
"""
import argparse
import contextlib
import re
import difflib
import fnmatch
import hashlib
import io
import heapq
import json
import mimetypes
import os
import queue
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import http.cookies
import urllib.parse
import webbrowser
import zipfile
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import datetime as dt

import tray as traymod
import updates as updmod
import winwatch
import cleaner
import xlsx
from extractors import EXTRACTABLE, VERSION as EXTRACT_VERSION, category_of, extract

APP_DIR = Path(__file__).resolve().parent
APP_ID = 'desktop-watch/1'   # internal id (kept from the old name: older copies answer to it)
APP_NAME = 'DeskTrace'
APP_VERSION = '2.6.0'      # the installer and update licenses take their version number from here
SCHEMA_VERSION = 2       # bump with a step in migrate() whenever stored data changes shape
TOKEN = secrets.token_hex(16)


def default_data_dir():
    """Where history lives. An installed copy keeps it in the user's profile, apart from the program
    files, so installing a newer version (or reinstalling) never touches it. A copy run from a folder
    that already has a ``data`` folder next to it (development / portable) keeps using that."""
    if os.environ.get('DESKTOP_WATCH_DATA'):
        return Path(os.environ['DESKTOP_WATCH_DATA'])
    if (APP_DIR / 'data').is_dir() or (APP_DIR / 'portable.txt').exists():
        return APP_DIR / 'data'
    return PROFILE_DIR / 'DeskTrace' / 'data'


PROFILE_DIR = Path(os.environ.get('LOCALAPPDATA') or Path.home())
OLD_DATA_ROOT = PROFILE_DIR / 'Desktop Watch'  # where versions before the rename to DeskTrace kept it


DATA = default_data_dir()
BLOBS = DATA / 'blobs'
STATIC = APP_DIR / 'static'
SETTINGS_FILE = DATA / 'settings.json'


def desktop_path():
    if os.name == 'nt':
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(1024)
            if ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:
            pass
    return str(Path.home() / 'Desktop')


DEFAULTS = {
    'roots': [desktop_path()],
    'interval': 60.0,  # full-rescan safety net; changes themselves are picked up instantly
    'exclude_exts': ['.lnk', '.url', '.appref-ms', '.website', '.tmp', '.crdownload', '.part', '.partial', '.download'],
    'exclude_names': ['~$*', '~*.tmp', '.~lock.*', '~WRL*.tmp', 'Thumbs.db', 'desktop.ini', '.DS_Store', '*.swp'],
    'exclude_dirs': ['.git', 'node_modules', '__pycache__', '.venv', 'venv', '.idea', '.vs', '$RECYCLE.BIN'],
    'snapshot_max_mb': 50,
    'baseline_text_max_mb': 30,
    'baseline_copy_mb': 1,
    'lang': '',  # '' = follow the browser; or en / zh / de
    'notify': 'deleted',  # Windows notifications: off / deleted / all (new installs: deletions, 2.0.1)
    'keep_days': 90,  # forget changes older than this (0 = keep forever)
    'max_storage_gb': 5,  # above this, full copies of the oldest versions are dropped (0 = no limit)
    'exclude_paths': [],  # specific folders to ignore ("Ignore this folder")
    'mute_until': 0,  # desktop notifications are silent until this time
    'prescan': True,  # read drives for Clean up in the background while the PC is idle (2.4.0)
    'onboarded': False,  # the first-run guide was shown (2.4.0); set for existing users when they update
}


def load_settings():
    s = dict(DEFAULTS)
    try:
        saved = json.loads(SETTINGS_FILE.read_text('utf-8'))
        s.update(saved)
        s.setdefault('onboarded', True)
        if 'onboarded' not in saved:  # someone updating, not a new install: no first-run guide (2.4.0)
            s['onboarded'] = True
    except (OSError, ValueError):
        pass
    return s


def save_settings(s):
    SETTINGS_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2), 'utf-8')


# ---------------------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, size INTEGER, mtime INTEGER, hash TEXT);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, path TEXT, old_path TEXT, ext TEXT, cat TEXT,
  size INTEGER, old_size INTEGER, mtime INTEGER, hash TEXT, prev_hash TEXT,
  added INTEGER, removed INTEGER, summary TEXT, flags TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS ev_path ON events(path);
CREATE INDEX IF NOT EXISTS ev_ts ON events(ts);
CREATE INDEX IF NOT EXISTS ev_old ON events(old_path);
CREATE TABLE IF NOT EXISTS stars(path TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS pins(path TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS notes(event_id INTEGER PRIMARY KEY, text TEXT, ts REAL);
CREATE TABLE IF NOT EXISTS contents(hash TEXT PRIMARY KEY, ext TEXT, data BLOB);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS drive_scans(drive TEXT PRIMARY KEY, serial INTEGER, mode TEXT, finished REAL, data BLOB);
CREATE TABLE IF NOT EXISTS scan_history(drive TEXT, serial INTEGER, finished REAL, sizes BLOB, PRIMARY KEY(drive, finished));
"""


SEARCH_CATS = {'word', 'excel', 'ppt', 'pdf', 'markdown', 'text'}  # what content search covers


SNAP_MAGIC = b'DTS1'   # compressed snapshot (2.4.0): magic, format version, algorithm, original size, data


class SnapshotError(ValueError):
    pass


def compressible(data):
    """Worth compressing? Files under 4 KB are not; for the rest the first 4 KB tell (Office files, PDFs,
    pictures, videos and archives are compressed already and would only cost time)."""
    if len(data) < 4096:
        return False
    sample = data[:4096]
    return len(zlib.compress(sample, 1)) < len(sample) * 0.9


def pack_snapshot(data):
    """What is written to disk for ``data``: zlib (level 6) behind a small header when that saves space,
    otherwise the bytes as they are. Content addressing (the SHA-1 of the original) is unchanged."""
    if compressible(data):
        body = zlib.compress(data, 6)
        if len(body) < len(data) * 0.98:
            return SNAP_MAGIC + bytes((1, 1)) + len(data).to_bytes(8, 'little') + body
    if data[:4] == SNAP_MAGIC:  # an original that happens to start like a header is stored with one
        return SNAP_MAGIC + bytes((1, 0)) + len(data).to_bytes(8, 'little') + data
    return data


def unpack_snapshot(raw):
    if raw[:4] != SNAP_MAGIC:
        return raw  # stored before 2.4.0, or not worth compressing
    if len(raw) < 14 or raw[4] != 1 or raw[5] not in (0, 1):
        raise SnapshotError('unknown snapshot format')
    size = int.from_bytes(raw[6:14], 'little')
    try:
        data = zlib.decompress(raw[14:]) if raw[5] == 1 else raw[14:]
    except zlib.error as e:
        raise SnapshotError('damaged snapshot') from e
    if len(data) != size:
        raise SnapshotError('damaged snapshot')
    return data


class Store:
    def __init__(self, path):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA journal_mode=WAL')
        self.conn.execute('PRAGMA synchronous=NORMAL')
        self.conn.execute('PRAGMA busy_timeout=5000')  # wait instead of failing if the file is briefly busy
        self.conn.executescript(SCHEMA)
        self.lock = threading.RLock()
        self._tl = threading.local()  # per-thread write batching, see batch() (2.1.0)
        try:  # full-text index of document text; the trigram tokenizer also matches Chinese
            self.conn.executescript("CREATE TABLE IF NOT EXISTS ftsdoc(id INTEGER PRIMARY KEY, hash TEXT UNIQUE);"
                                    "CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(body, tokenize='trigram');")
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False

    def index_text(self, h, ext, res):
        """Add one version's text to the search index (documents only, once per version)."""
        if not self.fts or not h or not res or category_of(ext) not in SEARCH_CATS:
            return
        body = '\n'.join(res.get('lines') or [])[:1_000_000]
        if not body.strip():
            return
        with self.lock:
            if self.conn.execute('SELECT 1 FROM ftsdoc WHERE hash=?', (h,)).fetchone():
                return
            rid = self.conn.execute('INSERT INTO ftsdoc(hash) VALUES(?)', (h,)).lastrowid
            self.conn.execute('INSERT INTO fts(rowid, body) VALUES(?, ?)', (rid, body))
            self._commit()

    def q(self, sql, args=()):
        with self.lock:
            return self.conn.execute(sql, args).fetchall()

    def _commit(self):
        """Commit now, or, inside batch() on this thread, once per 250 writes or 2 seconds."""
        tl = self._tl
        if getattr(tl, 'depth', 0):
            if not tl.n:
                tl.first = time.time()
            tl.n += 1
            if tl.n < 250 and time.time() - tl.first < 2.0:
                return
            tl.n = 0
        self.conn.commit()

    @contextlib.contextmanager
    def batch(self):
        """Collect this thread's writes into a few commits instead of one per row (2.1.0). Recording a
        folder of thousands of files copied in, deleted or excluded writes far less to disk this way."""
        tl = self._tl
        if not getattr(tl, 'depth', 0):
            tl.depth, tl.n = 0, 0
        tl.depth += 1
        try:
            yield
        finally:
            tl.depth -= 1
            if not tl.depth:
                self.flush()

    def flush(self):
        """Commit what this thread's batch has collected so far (before a long wait)."""
        tl = self._tl
        if getattr(tl, 'n', 0):
            tl.n = 0
            with self.lock:
                self.conn.commit()

    def x(self, sql, args=()):
        with self.lock:
            cur = self.conn.execute(sql, args)
            self._commit()
            return cur.lastrowid

    def count(self, sql, args=()):
        """Run a write and return how many rows it touched."""
        with self.lock:
            cur = self.conn.execute(sql, args)
            self._commit()
            return cur.rowcount

    def tidy(self):
        """Keep the database quick and small: refresh the query planner's statistics and fold the
        write-ahead log back into the database file (2.1.0)."""
        with self.lock:
            self.conn.execute('PRAGMA optimize')
            self.conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')

    def many(self, sql, rows):
        with self.lock:
            self.conn.executemany(sql, rows)
            self._commit()

    def meta(self, k, default=None):
        r = self.q('SELECT v FROM meta WHERE k=?', (k,))
        return json.loads(r[0]['v']) if r else default

    def set_meta(self, k, v):
        self.x('INSERT OR REPLACE INTO meta(k, v) VALUES(?, ?)', (k, json.dumps(v)))

    # content-addressed snapshots ------------------------------------------------
    @staticmethod
    def blob_path(h):
        return BLOBS / h[:2] / h

    def has_blob(self, h):
        return bool(h) and self.blob_path(h).exists()

    def put_blob(self, h, data):
        p = self.blob_path(h)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix('.tmp')
            tmp.write_bytes(pack_snapshot(data))
            os.replace(tmp, p)

    def read_blob(self, h):
        """The content of a kept version, whether stored compressed (2.4.0) or as it was (older)."""
        return unpack_snapshot(self.blob_path(h).read_bytes())

    def copy_blob(self, h, dest):
        """Write a kept version to ``dest`` as the original file: first in full to a temporary file next to
        it, then put in place in one step, so a full disk, a crash or a file open in another program never
        leaves a half-written or damaged file (2.4.2)."""
        data = self.read_blob(h)
        dest = long_path(dest)
        tmp = long_path(os.path.join(os.path.dirname(dest), f'.~dt-restore-{os.getpid()}-{threading.get_ident()}.tmp'))
        try:
            with open(tmp, 'wb') as fh:
                fh.write(data)
                fh.flush()
                os.fsync(fh.fileno())
            replace_file(tmp, dest)
        except OSError as e:
            try:
                os.remove(tmp)
            except OSError:
                pass
            if isinstance(e, RestoreError):
                raise
            raise RestoreError('inUse' if getattr(e, 'winerror', 0) in (5, 32, 33) else 'writeFailed') from e

    def sha1_of(self, h):
        """SHA-1 of a kept version's content, to match it with a version kept before 2.4.2."""
        cache = self.__dict__.setdefault('_sha1', {})
        if h not in cache:
            try:
                cache[h] = hashlib.sha1(self.read_blob(h)).hexdigest() if self.has_blob(h) else None
            except (OSError, SnapshotError):
                cache[h] = None
        return cache[h]

    def sha256_of(self, h):
        """The 2.4.2 name of a version kept under its SHA-1 name (so Duplicates can compare old and new)."""
        if not h or len(h) != 40:
            return h
        cache = self.__dict__.setdefault('_sha256', {})
        if h not in cache:
            try:
                cache[h] = content_hash(self.read_blob(h)) if self.has_blob(h) else h
            except (OSError, SnapshotError):
                cache[h] = h
        return cache[h]

    def has_content(self, h):
        return bool(h) and bool(self.q('SELECT 1 FROM contents WHERE hash=?', (h,)))

    def put_content(self, h, ext, res):
        self.x('INSERT OR REPLACE INTO contents(hash, ext, data) VALUES(?,?,?)',
               (h, ext, zlib.compress(json.dumps(res, ensure_ascii=False).encode('utf-8'), 6)))
        self.index_text(h, ext, res)

    def content(self, h, ext):
        """Extracted content for a snapshot hash; extracts lazily from the blob if needed."""
        if not h:
            return None
        r = self.q('SELECT data FROM contents WHERE hash=?', (h,))
        if r:
            res = json.loads(zlib.decompress(r[0]['data']))
            if res.get('v') == EXTRACT_VERSION or not self.has_blob(h):
                return res
        if self.has_blob(h):  # not extracted yet, or extracted by an older version
            try:
                res = extract(self.read_blob(h), ext)
            except (OSError, SnapshotError):
                return None  # a damaged snapshot: shown as "not available", never a crash
            self.put_content(h, ext, res)
            return res
        return None


# ---------------------------------------------------------------------------- live updates

class Hub:
    def __init__(self):
        self.clients = set()
        self.lock = threading.Lock()

    def subscribe(self):
        q = queue.Queue(maxsize=1000)
        with self.lock:
            self.clients.add(q)
        return q

    def unsubscribe(self, q):
        with self.lock:
            self.clients.discard(q)

    def publish(self, msg):
        data = json.dumps(msg, ensure_ascii=False)
        with self.lock:
            for q in list(self.clients):
                try:
                    q.put_nowait(data)
                except queue.Full:
                    pass


# ---------------------------------------------------------------------------- monitor

class Rules:
    def __init__(self, s):
        self.exts = {(e if e.startswith('.') else '.' + e).lower() for e in s['exclude_exts']}
        self.names = [n.lower() for n in s['exclude_names']]
        self.dirs = [d.lower() for d in s['exclude_dirs']]
        # Specific folders the user chose to ignore (whole paths, unlike the folder-name patterns above).
        self.paths = [os.path.normcase(os.path.normpath(p)) for p in s.get('exclude_paths', []) if p]

    def dir_path_excluded(self, path):
        if not self.paths:
            return False
        n = os.path.normcase(os.path.normpath(path))
        return any(n == p or n.startswith(p.rstrip(os.sep) + os.sep) for p in self.paths)

    def file_excluded(self, name):
        n = name.lower()
        return os.path.splitext(n)[1] in self.exts or any(fnmatch.fnmatchcase(n, p) for p in self.names)

    def dir_excluded(self, name):
        n = name.lower()
        return any(fnmatch.fnmatchcase(n, p) for p in self.dirs)

    def path_excluded(self, path, root):
        rel = os.path.relpath(path, root).split(os.sep)
        return (self.file_excluded(rel[-1]) or any(self.dir_excluded(d) for d in rel[:-1])
                or self.dir_path_excluded(os.path.dirname(path)))


def under(path, root):
    root = os.path.normcase(os.path.normpath(root))
    p = os.path.normcase(os.path.normpath(path))
    return p == root or p.startswith(root.rstrip(os.sep) + os.sep)


SETTLE = 1.0          # seconds between the two scans that confirm a change has finished
BURST = 0.4           # after a change notification, wait this long so a burst of operations lands in one scan
MAX_UNSTABLE = 30.0   # a file that never stops changing (e.g. a growing log) is recorded after this long anyway
SAFETY_MIN = 300.0    # while Windows reports changes instantly, the safety rescan runs at most this often (2.1.0)
MASS_N = 100         # this many changes, deletions or renames ...
MASS_WINDOW = 10.0   # ... within this many seconds: a mass change (2.6.0 #6)
WAKE_DELAY = 45.0     # after the PC wakes up, the catch-up rescan waits this long: the user comes first (2.4.2)


def content_hash(data):
    """Name of a kept version: SHA-256 of its content (2.4.2). Versions kept earlier are named by SHA-1
    (40 characters) and stay readable; nothing is renamed."""
    return hashlib.sha256(data).hexdigest()


def long_path(p):
    """``p`` usable beyond 260 characters, also where Windows long paths are not switched on (2.4.2)."""
    p = str(p)
    if os.name != 'nt' or len(p) < 240 or p.startswith('\\\\?\\'):
        return p
    p = os.path.abspath(p)
    return '\\\\?\\UNC\\' + p[2:] if p.startswith('\\\\') else '\\\\?\\' + p


class RestoreError(OSError):
    """A restore that could not be written; the file that was there is untouched (2.4.2)."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def replace_file(tmp, dest):
    """Put ``tmp`` in the place of ``dest`` in one step (ReplaceFileW keeps the file's creation date and
    permissions); if another program has ``dest`` open, nothing changes and RestoreError('inUse') is raised."""
    if os.name == 'nt' and os.path.exists(dest):
        import ctypes
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        k32.ReplaceFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32,
                                     ctypes.c_void_p, ctypes.c_void_p]
        if k32.ReplaceFileW(dest, tmp, None, 0x2, None, None):  # REPLACEFILE_IGNORE_MERGE_ERRORS
            return
        err = ctypes.get_last_error()
        if err in (5, 32, 33, 1175):  # access denied, sharing or lock violation, could not remove the old file
            raise RestoreError('inUse')
    os.replace(tmp, dest)


class Monitor:
    def __init__(self, store, hub, settings):
        self.store, self.hub, self.settings = store, hub, settings
        self.rules = Rules(settings)
        self.lock = threading.RLock()
        self.confirmed = {r['path']: [r['size'], r['mtime'], r['hash']]
                          for r in store.q('SELECT path, size, mtime, hash FROM files')}
        self.known_roots = set(store.meta('known_roots', []))
        self.stars = {r['path'] for r in store.q('SELECT path FROM stars')}  # files the user starred
        self.notes = {r['event_id']: r['text'] for r in store.q('SELECT event_id, text FROM notes')}  # labelled versions
        self.pause_until = 0.0      # timed pause: resume automatically at this time
        self.last = None            # previous scan result: path -> (size, mtime)
        self.retries = {}
        self.paused = False
        self.prev_scope = None      # (rules, roots) before a settings change, to absorb newly visible files
        self.wake = threading.Event()
        self.on_status = None       # optional callback(status) after every scan (updates the tray)
        self.on_event = None        # optional callback(event) for each recorded change (notifications)
        self.watchers = {}          # root -> winwatch.Watcher
        self.unsettled = False      # changes seen but not yet confirmed stable: rescan soon
        self.unstable_since = {}    # path -> when it was first seen changing
        self.dirty = set()          # paths Windows reported as changed since the last scan
        self.dirty_lock = threading.Lock()
        self.full_needed = True     # next scan must cover everything (first scan, overflow, settings…)
        self.pending = set()        # paths still settling: looked at again by the next targeted scan
        self.last_full = 0.0
        self.jobs = queue.Queue()
        self.stats = {'scan_ms': 0, 'files': len(self.confirmed), 'last_scan': 0, 'scans': 0,
                      'baseline_total': 0, 'baseline_done': 0}
        self.started = time.time()
        self.gen = 0                # goes up whenever the set of files or their versions change (2.1.0)

    # -- helpers ---------------------------------------------------------------
    def root_of(self, path):
        for r in self.settings['roots']:
            if under(path, r):
                return r
        return None

    def root_available(self, r):
        """A monitored folder can be read now (False: drive unplugged, network or cloud drive away,
        folder moved or deleted)."""
        try:
            with os.scandir(r) as it:
                next(it, None)
            return True
        except OSError:
            return False

    def check_roots(self):
        """In the monitor loop: act on folders that went away or came back. A drive that goes away does not
        always stop its change watcher (it just goes quiet): drop it, and when the folder is back watch it
        afresh and look at everything once (2.4.2)."""
        away = set(self.stats.get('offline_roots') or [])
        seen = getattr(self, '_away_seen', set())
        if away == seen:
            return
        self._away_seen = away
        for r in away ^ seen:
            w = self.watchers.pop(r, None)
            if w:
                threading.Thread(target=w.stop, daemon=True).start()  # never wait on a vanished drive
        if seen - away:
            with self.dirty_lock:
                self.full_needed = True

    def roots_loop(self):
        """Every 10 s, see whether each monitored folder can be reached; wake the monitor only when that
        changes (a few directory opens: no measurable cost at idle) (2.4.2)."""
        last, drives = None, None
        while True:
            time.sleep(10)
            if getattr(App, 'mon', self) is not self:
                return  # replaced by a new monitor
            try:
                now = tuple(self.offline_roots())
            except Exception:
                continue
            if last is not None and now != last:
                self.wake.set()
            last = now
            try:  # a removable drive plugged in: say so once, with its space (2.6.0 #21)
                rem = {d['drive']: d for d in cleaner.drives() if d['removable']}
                if drives is not None:
                    for d in set(rem) - drives:
                        App.hub.publish({'type': 'drive', 'drive': rem[d]})
                drives = set(rem)
            except Exception:
                pass

    def offline_roots(self):
        out = [r for r in self.settings['roots'] if not self.root_available(r)]
        self.stats['offline_roots'] = out
        return out

    def scan(self):
        """Every file under every monitored folder: path -> (size, mtime_ns). Folders that cannot be read
        right now keep what was known about them: their files are not taken for deleted (2.4.2)."""
        self.walk_failed = []
        out = self._walk([r for r in self.settings['roots'] if r not in self.offline_roots()])
        if self.walk_failed and self.last:
            prefixes = tuple(d.rstrip(os.sep) + os.sep for d in self.walk_failed)
            out.update({k: v for k, v in self.last.items() if k.startswith(prefixes) and k not in out})
        return out

    def partial_scan(self, base, paths):
        """``base`` with just the places in ``paths`` looked at again (files: their folder; folders: their
        whole subtree; vanished paths: forgotten). Much cheaper than a full scan after a few changes."""
        cur = dict(base)
        flat, deep, gone = set(), set(), set()
        for p in paths:
            root = self.root_of(p)
            if root is None or under(p, str(DATA)):
                continue
            if os.path.isdir(p):
                if not getattr(os.path, 'isjunction', lambda _: False)(p) and self._dir_watched(p, root):
                    deep.add(p)
            else:
                if not os.path.lexists(p):
                    gone.add(p)
                if self._dir_watched(os.path.dirname(p), root):
                    flat.add(os.path.dirname(p))
        # Windows reports names with the same spelling as directory listings, so plain string
        # matching is enough; anything missed is caught by the periodic full scan.
        for g in gone:
            cur.pop(g, None)
        prefixes = tuple(d.rstrip(os.sep) + os.sep for d in deep | gone)
        if prefixes:  # a folder appeared or vanished: forget everything we knew below it
            for k in [k for k in cur if k.startswith(prefixes)]:
                del cur[k]
        for d in flat:
            cur.update(self._list_files(d))
        cur.update(self._walk(sorted(deep)))
        return cur

    def _dir_watched(self, d, root):
        """False if ``d`` lies inside an excluded folder (or is not under ``root``)."""
        rel = os.path.relpath(d, root)
        if rel.startswith('..') or self.rules.dir_path_excluded(d):
            return False
        return rel == '.' or not any(self.rules.dir_excluded(part) for part in rel.split(os.sep))

    def _list_files(self, d):
        """The files directly inside ``d`` (not its subfolders)."""
        out = {}
        try:
            it = os.scandir(d)
        except OSError:
            return out
        with it:
            for e in it:
                try:
                    if e.is_file(follow_symlinks=False) and not self.rules.file_excluded(e.name):
                        st = e.stat(follow_symlinks=False)
                        out[e.path] = (st.st_size, st.st_mtime_ns)
                except OSError:
                    pass
        return out

    def collect(self):
        """Decide between a full scan and a targeted one, and run it."""
        with self.dirty_lock:
            dirty, self.dirty = self.dirty, set()
            full, self.full_needed = self.full_needed, False
        paths = dirty | self.pending
        due = time.time() - self.last_full >= self.full_interval() - 0.5
        if full or due or self.last is None or not self.instant or len(paths) > 400:
            self.last_full = time.time()
            return self.scan(), 'full'
        return self.partial_scan(self.last, paths), 'partial'

    def request_full(self):
        with self.dirty_lock:
            self.full_needed = True
        self.wake.set()

    def _walk(self, dirs):
        out = {}
        data_dir = os.path.normcase(str(DATA))
        rules = self.rules
        stack = list(dirs)
        failed = getattr(self, 'walk_failed', None)
        while stack:
            d = stack.pop()
            try:
                it = os.scandir(d)
            except FileNotFoundError:
                continue
            except OSError:
                if failed is not None:
                    failed.append(d)  # there but unreadable now: not "everything in it was deleted"
                continue
            with it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            if (getattr(e, 'is_junction', lambda: False)() or rules.dir_excluded(e.name)
                                    or rules.dir_path_excluded(e.path)):
                                continue
                            if os.path.normcase(e.path) != data_dir:
                                stack.append(e.path)
                        elif e.is_file(follow_symlinks=False) and not rules.file_excluded(e.name):
                            st = e.stat(follow_symlinks=False)
                            out[e.path] = (st.st_size, st.st_mtime_ns)
                    except OSError:
                        pass
        return out

    def capture(self, path, size, force=False, prev=None):
        """Snapshot a file. Returns (hash|None, ok). ok=False means retry next scan.

        ``force`` accepts whatever is on disk right now, for files that never stop changing. ``prev`` is the
        hash kept so far: when it is an SHA-1 one (before 2.4.2) and the content is the same, it is reused.
        """
        if size > self.settings['snapshot_max_mb'] * 1024 * 1024 or disk_low() or cleaner.online_only(path):
            return None, True
        try:
            with open(path, 'rb') as fh:
                data = fh.read()
        except OSError:
            n = self.retries.get(path, 0) + 1
            self.retries[path] = n
            return None, n >= 3       # give up snapshotting after 3 locked attempts
        if len(data) != size and not force:
            return None, False        # still being written
        self.retries.pop(path, None)
        if prev and len(prev) == 40 and hashlib.sha1(data).hexdigest() == prev and self.store.has_blob(prev):
            return prev, True         # unchanged since a version kept before 2.4.2: no second copy
        h = content_hash(data)
        self.store.put_blob(h, data)
        return h, True

    # -- change notifications --------------------------------------------------
    def sync_watchers(self):
        """One Windows change watcher per monitored folder (restarted if a folder comes back)."""
        if not winwatch.available:
            return
        roots = set(self.settings['roots'])
        for r, w in list(self.watchers.items()):
            if r not in roots or not w.alive:
                w.stop()
                del self.watchers[r]
        for r in roots:
            if r not in self.watchers and os.path.isdir(r):
                self.watchers[r] = winwatch.Watcher(r, lambda changes, r=r: self.on_fs_change(r, changes))

    def on_fs_change(self, root, changes):
        if changes is None:           # Windows dropped the details: look at everything, and say so (2.3.0)
            self.last_overflow = time.time()
            return self.request_full()
        paths = {os.path.join(root, rel) for a, rel in changes if self._relevant(root, a, rel)}
        if not paths:
            return
        with self.dirty_lock:
            self.dirty |= paths
        self.wake.set()

    def _relevant(self, root, action, rel):
        p = os.path.join(root, rel)
        if under(p, str(DATA)):
            return False              # our own snapshots and database
        if action == winwatch.MODIFIED and os.path.isdir(p):
            return False              # a folder's timestamp; the files inside report themselves
        return not self.rules.path_excluded(p, root)

    def full_interval(self):
        """Seconds between full safety rescans: the setting — but while Windows change notifications work
        (they already report every change at once) no more often than every SAFETY_MIN seconds (2.1.0)."""
        iv = float(self.settings['interval'])
        if self.instant:
            return max(iv, SAFETY_MIN * (6 if battery_low() else 3 if on_battery() else 1))  # battery: every 15 min, under 20 %: 30 min (2.6.0 #41)
        return iv

    def after_wake(self, now):
        """The PC just woke up: look at everything again, but only WAKE_DELAY seconds later — the user,
        the network and other programs come first. Change notifications keep working meanwhile (2.4.2)."""
        self.last_full = now - self.full_interval() + WAKE_DELAY
        self.woke_at = now
        with self.dirty_lock:
            self.full_needed = False

    @property
    def instant(self):
        return bool(self.watchers) and all(w.alive for w in self.watchers.values())

    # -- main loop -------------------------------------------------------------
    def run(self):
        background_thread()
        threading.Thread(target=self.roots_loop, daemon=True, name='roots').start()
        wall, mono = time.time(), time.monotonic()
        while True:
            t0 = time.time()
            if (t0 - wall) - (time.monotonic() - mono) > 30:  # the PC slept: changes may have been missed (2.3.0)
                self.after_wake(t0)
            wall, mono = t0, time.monotonic()
            try:  # nothing may stop the monitoring loop
                self.check_roots()
                self.sync_watchers()
                if self.paused and self.pause_until and time.time() >= self.pause_until:
                    self.paused, self.pause_until = False, 0.0  # a timed pause is over
                if self.paused:
                    self.full_needed = True   # after a pause, look at everything once
                else:
                    with self.lock:           # settings changes wait for a whole scan to finish
                        self.tick()
                status = self.status()
                sig = {k: v for k, v in status.items() if k not in ('last_scan', 'uptime', 'scan_ms', 'partial_ms', 'scans', 'scan_kind')}
                if sig != getattr(self, '_last_sig', None) or time.time() - getattr(self, '_last_pub', 0) > 60:
                    self._last_sig, self._last_pub = sig, time.time()  # nothing new: no redraw (2.1.0)
                    self.hub.publish({'type': 'status', 'status': status})
                    if self.on_status:
                        self.on_status(status)
            except Exception as e:
                print('scan error:', repr(e), file=sys.stderr)
                self.full_needed = True
            # Sleep until the next safety rescan or a change notification — or, while changes are
            # still settling, just until the confirming scan.
            wait = self.full_interval() - (time.time() - self.last_full)
            if self.unsettled and not self.paused:
                wait = min(wait, SETTLE)
            trim_when_idle()
            if App.mon is self:
                maybe_prescan()
            if self.wake.wait(max(0.3, min(wait, 600))):
                time.sleep(BURST)
                self.wake.clear()
                time.sleep(max(0.0, SETTLE - (time.time() - t0)))  # at most about one scan per second

    def tick(self):
        t0 = time.perf_counter()
        cur, kind = self.collect()
        ms = round((time.perf_counter() - t0) * 1000)
        self.stats.update({'scan_ms' if kind == 'full' else 'partial_ms': ms, 'scan_kind': kind})
        roots = self.settings['roots']
        new_roots = [r for r in roots if r not in self.known_roots]
        first = self.last is None
        stable = cur if first else self.last
        prev_scope, self.prev_scope = self.prev_scope, None

        def newly_visible(p):
            if prev_scope is None:
                return False
            rules, old_roots = prev_scope
            r = next((r for r in old_roots if under(p, r)), None)
            return r is None or rules.path_excluded(p, r)
        offline = first and bool(self.confirmed)
        away = self.stats.get('offline_roots') if kind == 'full' else self.offline_roots()
        now = time.time()
        unsettled, unstable, force = set(), {}, set()   # unsettled: paths to look at again soon

        created, modified, deleted = [], [], []
        with self.lock, self.store.batch():
            silent_rows = []
            for p, st in cur.items():
                c = self.confirmed.get(p)
                if c is not None and (c[0], c[1]) == st:
                    continue
                root = self.root_of(p)
                if c is None and (root in new_roots or newly_visible(p)):
                    self.confirmed[p] = [st[0], st[1], None]
                    silent_rows.append((p, st[0], st[1], None))
                    continue
                if stable.get(p) != st:
                    since = unstable[p] = self.unstable_since.get(p, now)
                    if now - since < MAX_UNSTABLE:
                        unsettled.add(p)
                        continue      # wait until it stops changing
                    force.add(p)      # it keeps changing: record what is there now
                (created if c is None else modified).append((p, st))
            for p in list(self.confirmed):
                if p in cur:
                    continue
                root = self.root_of(p)
                if root is not None and root in away:
                    continue          # its folder is not there right now: wait, it is not "deleted" (2.4.2)
                if root is None or self.rules.path_excluded(p, root):
                    self.confirmed.pop(p)
                    self.gen += 1
                    self.store.x('DELETE FROM files WHERE path=?', (p,))
                elif p not in stable:
                    deleted.append(p)
                else:
                    unsettled.add(p)  # gone now: confirm on the next scan
            if silent_rows:
                self.gen += 1
                self.store.many('INSERT OR REPLACE INTO files(path,size,mtime,hash) VALUES(?,?,?,?)', silent_rows)

            # Pair deletes+creates with identical size and mtime into renames/moves.
            by_key = {}
            for p, st in created:
                by_key.setdefault(st, []).append(p)
            renames = []
            del_keys = {}
            for p in deleted:
                k = (self.confirmed[p][0], self.confirmed[p][1])
                del_keys[k] = del_keys.get(k, 0) + 1
            for p in list(deleted):
                c = self.confirmed[p]
                cands = by_key.get((c[0], c[1]))
                if cands:
                    same_name = [n for n in cands if os.path.basename(n).lower() == os.path.basename(p).lower()]
                    if not same_name and (len(cands) > 1 or del_keys[(c[0], c[1])] > 1):
                        continue  # several files share size and time (Windows' clock is coarse): content decides below (2.6.0)
                    same_ext = [n for n in cands if os.path.splitext(n)[1].lower() == os.path.splitext(p)[1].lower()]
                    pick = (same_name or same_ext or cands)[0]
                    cands.remove(pick)
                    deleted.remove(p)
                    created = [(n, s) for n, s in created if n != pick]
                    renames.append((p, pick, (c[0], c[1])))

            # Some tools give a moved file a new timestamp: pair what is left by identical content.
            captured = {p: self.capture(p, st[0], force=p in force) for p, st in created}
            by_hash = {}
            for p, st in created:
                h, ok = captured[p]
                if ok and h:
                    by_hash.setdefault(h, []).append((p, st))
            for p in list(deleted):
                h = self.confirmed[p][2]
                if h and len(h) == 40 and not by_hash.get(h):  # kept before 2.4.2: compare by SHA-1
                    size = self.confirmed[p][0]
                    for nh, lst in by_hash.items():
                        if lst and lst[0][1][0] == size and self.store.sha1_of(nh) == h:
                            h = nh
                            break
                if h and by_hash.get(h):
                    new, nst = by_hash[h].pop(0)
                    deleted.remove(p)
                    created = [(n, s) for n, s in created if n != new]
                    renames.append((p, new, nst))

            flags = 'offline' if offline else ''
            for old, new, nst in renames:
                c = self.confirmed.pop(old)
                self.confirmed[new] = [nst[0], nst[1], c[2]]
                self.store.x('DELETE FROM files WHERE path=?', (old,))
                if old in self.stars:  # a starred file stays starred under its new name
                    self.stars = (self.stars - {old}) | {new}
                    self.store.x('UPDATE OR REPLACE stars SET path=? WHERE path=?', (new, old))
                self.store.x('INSERT OR REPLACE INTO files VALUES(?,?,?,?)', (new, nst[0], nst[1], c[2]))
                same_dir = os.path.dirname(old).lower() == os.path.dirname(new).lower()
                self.emit('renamed', new, old_path=old, size=nst[0], old_size=c[0], mtime=nst[1], h=c[2], prev=c[2],
                          summary=json.dumps({'t': 'renamed' if same_dir else 'moved'}), flags=flags)
            for p in deleted:
                c = self.confirmed.pop(p)
                self.store.x('DELETE FROM files WHERE path=?', (p,))
                self.emit('deleted', p, size=0, old_size=c[0], mtime=c[1], h=None, prev=c[2], flags=flags)
            for kind, items in (('created', created), ('modified', modified)):
                for p, st in items:
                    h, ok = captured[p] if p in captured else self.capture(
                        p, st[0], force=p in force, prev=(self.confirmed.get(p) or (None, None, None))[2])
                    if not ok:
                        unsettled.add(p)
                        continue
                    unstable.pop(p, None)
                    prev = self.confirmed.get(p)
                    self.confirmed[p] = [st[0], st[1], h]
                    self.store.x('INSERT OR REPLACE INTO files VALUES(?,?,?,?)', (p, st[0], st[1], h))
                    f = [flags] if flags else []
                    if h is None:
                        f.append('nosnap')
                        if disk_low():
                            f.append('lowdisk')
                        elif cleaner.online_only(p):
                            f.append('cloud')  # online-only: recorded, not downloaded (2.3.0)
                    if kind == 'modified' and h and prev and prev[2] == h:
                        f.append('same')
                    self.emit(kind, p, size=st[0], old_size=prev[0] if prev else None, mtime=st[1], h=h,
                              prev=prev[2] if prev else None, flags=','.join(f))

        # mass change guard (2.6.0 #6): a batch job gone wrong or ransomware touches many files at once
        hits = len(modified) + len(deleted) + len(renames)
        if hits and not first and now > getattr(self, 'mass_quiet', 0):
            win = [x for x in getattr(self, '_burst', []) if now - x[0] <= MASS_WINDOW] + [(now, hits)]
            self._burst = win
            total = sum(n for _, n in win)
            if total >= MASS_N:
                m = getattr(self, 'mass', None)
                if m and now - m['until'] < 120:
                    m.update(until=now, n=m['n'] + hits)
                else:
                    self.mass = {'since': win[0][0] - SETTLE - 2, 'until': now, 'n': total}
        if new_roots:
            self.known_roots |= set(new_roots)
            self.store.set_meta('known_roots', sorted(self.known_roots))
            self.wake_baseline()
        if prev_scope:
            self.wake_baseline()
        self.last = cur
        self.unsettled, self.pending, self.unstable_since = bool(unsettled), unsettled, unstable
        self.stats.update(files=len(cur), last_scan=time.time(), scans=self.stats['scans'] + 1)

    def emit(self, kind, path, *, old_path=None, size=None, old_size=None, mtime=None, h=None, prev=None,
             summary=None, flags=''):
        ext = os.path.splitext(path)[1].lower()
        self.gen += 1
        eid = self.store.x(
            'INSERT INTO events(ts,kind,path,old_path,ext,cat,size,old_size,mtime,hash,prev_hash,summary,flags)'
            ' VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (time.time(), kind, path, old_path, ext, category_of(ext), size, old_size, mtime, h, prev, summary, flags))
        ev = self.event_dict(eid)
        self.hub.publish({'type': 'event', 'event': ev})
        if self.on_event:
            self.on_event(ev)
        if kind != 'renamed':
            self.jobs.put(eid)

    # -- background workers ----------------------------------------------------
    def worker(self):
        """Extract content for new events and compute their change summary."""
        background_thread()
        while True:
            todo = [self.jobs.get()]
            while len(todo) < 500:  # many changes at once (a folder copied in): few commits for all (2.1.0)
                try:
                    todo.append(self.jobs.get_nowait())
                except queue.Empty:
                    break
            with self.store.batch():
                for eid in todo:
                    try:
                        self.summarize(eid)
                    except Exception as e:
                        print('summary error:', repr(e), file=sys.stderr)

    def summarize(self, eid):
        r = self.store.q('SELECT * FROM events WHERE id=?', (eid,))[0]
        ext, flags = r['ext'], r['flags'] or ''
        new = self.store.content(r['hash'], ext) if r['kind'] != 'deleted' else None
        old = self.store.content(r['prev_hash'], ext) if r['kind'] != 'created' else None
        unit = {'docx': 'paragraph', 'xlsx': 'cell'}.get((new or old or {}).get('type'), 'line')
        added = removed = None
        if 'lowdisk' in flags and r['kind'] != 'deleted':
            s = {'t': 'lowdisk'}
        elif 'cloud' in flags and r['kind'] != 'deleted':
            s = {'t': 'cloud'}
        elif 'nosnap' in flags and r['kind'] != 'deleted':
            too_big = (r['size'] or 0) > self.settings['snapshot_max_mb'] * 1024 * 1024
            s = {'t': 'big', 'size': r['size']} if too_big else {'t': 'locked'}
        elif 'same' in flags:
            s, added, removed = {'t': 'same'}, 0, 0
        elif r['kind'] == 'created':
            added = len(new['lines']) if new else None
            s = {'t': 'new', 'n': added, 'u': unit}
        elif r['kind'] == 'deleted':
            removed = len(old['lines']) if old else None
            s = {'t': 'del', 'n': removed, 'u': unit}
        elif new is not None and old is not None and (new['lines'] or old['lines']):
            added, removed = diff_counts(old['lines'], new['lines'])
            s = {'t': 'diff', 'u': unit} if (added or removed) else {'t': 'fmt'}
        else:
            s = {'t': 'size', 'd': (r['size'] or 0) - (r['old_size'] or 0)}
        self.store.x('UPDATE events SET added=?, removed=?, summary=? WHERE id=?', (added, removed, json.dumps(s), eid))
        self.hub.publish({'type': 'update', 'event': self.event_dict(eid)})

    def wake_baseline(self):
        self._baseline_wake.set()

    def baseline(self):
        """Index existing documents so their first change/delete has a 'before'."""
        self._baseline_wake = getattr(self, '_baseline_wake', threading.Event())
        background_thread()
        while True:
            try:  # an unreadable file or a database hiccup must not end indexing for good
                self.baseline_pass()
                self.index_backlog()
            except Exception as e:
                print('index error:', repr(e), file=sys.stderr)
            self.stats.update(baseline_total=0, baseline_done=0)
            self._baseline_wake.wait(600)
            self._baseline_wake.clear()

    def baseline_pass(self):
        text_max = self.settings['baseline_text_max_mb'] * 1024 * 1024
        copy_max = self.settings['baseline_copy_mb'] * 1024 * 1024
        with self.lock:
            todo = [(p, c[0], c[1]) for p, c in self.confirmed.items()
                    if c[2] is None and os.path.splitext(p)[1].lower() in EXTRACTABLE and c[0] <= text_max]
        todo.sort(key=lambda t: t[1])
        self.stats.update(baseline_total=len(todo), baseline_done=0)
        pending = []
        with self.store.batch():
            self._baseline_files(todo, pending, copy_max)
        if pending:
            self.store.many('UPDATE files SET hash=? WHERE path=?', pending)

    def _baseline_files(self, todo, pending, copy_max):
        for i, (p, size, mtime) in enumerate(todo):
            self.stats['baseline_done'] = i
            wait_for_power(self.store)
            with self.lock:
                c = self.confirmed.get(p)
                if not c or c[2] is not None or (c[0], c[1]) != (size, mtime):
                    continue
            if cleaner.online_only(p):
                continue  # a cloud placeholder: reading it would download it
            try:
                with open(p, 'rb') as fh:
                    data = fh.read()
            except OSError:
                continue
            h = content_hash(data)
            ext = os.path.splitext(p)[1].lower()
            if size <= copy_max and not disk_low():
                self.store.put_blob(h, data)
            if not self.store.has_content(h):
                self.store.put_content(h, ext, extract(data, ext))
            with self.lock:
                c = self.confirmed.get(p)
                if c and (c[0], c[1]) == (size, mtime) and c[2] is None:
                    c[2] = h
                    self.gen += 1
                    pending.append((h, p))
            if len(pending) >= 100:  # one database write per hundred files instead of one per file (2.1.0)
                self.store.many('UPDATE files SET hash=? WHERE path=?', pending)
                pending.clear()
            time.sleep(0.002)

    def index_backlog(self):
        """Put every current document version into the search index (e.g. text indexed before search existed)."""
        if not self.store.fts:
            return
        with self.lock:
            todo = {c[2]: os.path.splitext(p)[1].lower() for p, c in self.confirmed.items()
                    if c[2] and category_of(os.path.splitext(p)[1]) in SEARCH_CATS}
        done = {r['hash'] for r in self.store.q('SELECT hash FROM ftsdoc')}
        for h, ext in todo.items():
            if h not in done:
                try:
                    self.store.index_text(h, ext, self.store.content(h, ext))
                except Exception as e:
                    print('index error:', repr(e), file=sys.stderr)
                time.sleep(0.001)

    # -- retention -----------------------------------------------------------------
    def housekeeping(self):
        """Apply the retention settings a few minutes after start, every 6 hours, and after a change."""
        self.housekeeping_wake = getattr(self, 'housekeeping_wake', threading.Event())
        background_thread()
        self.housekeeping_wake.wait(180)
        while True:
            self.housekeeping_wake.clear()
            try:
                check_integrity()
                self.cleanup()
                recompress_old(self.store)
                verify_blobs(self.store)
                self.store.tidy()
            except Exception as e:
                print('cleanup error:', repr(e), file=sys.stderr)
            self.housekeeping_wake.wait(6 * 3600)

    def cleanup(self):
        """Forget changes older than ``keep_days``, delete snapshots nothing refers to, and drop full
        copies of the oldest versions while storage is above ``max_storage_gb`` (their text stays)."""
        st = self.store
        days = float(self.settings.get('keep_days') or 0)
        cap = float(self.settings.get('max_storage_gb') or 0) * 1024 ** 3
        # Versions the user labelled with a note are kept no matter how old.
        removed = st.count('DELETE FROM events WHERE ts < ? AND id NOT IN (SELECT event_id FROM notes)'
                           ' AND path NOT IN (SELECT path FROM pins)',  # pinned: kept forever (2.6.0 #20)
                           (time.time() - days * 86400,)) if days > 0 else 0
        freed = 0
        with self.lock:  # no new snapshots while deciding what is unused
            keep = {c[2] for c in self.confirmed.values() if c[2]}
            keep |= {r['h'] for r in st.q('SELECT hash h FROM events WHERE id IN (SELECT event_id FROM notes)'
                                          ' UNION SELECT prev_hash FROM events WHERE id IN (SELECT event_id FROM notes)'
                                          ' UNION SELECT hash FROM events WHERE path IN (SELECT path FROM pins)'
                                          ' UNION SELECT prev_hash FROM events WHERE path IN (SELECT path FROM pins)') if r['h']}
            newest = {r['h']: r['t'] for r in st.q(
                'SELECT h, MAX(t) t FROM (SELECT hash h, ts t FROM events UNION ALL SELECT prev_hash, ts FROM events)'
                ' WHERE h IS NOT NULL GROUP BY h')}
            blobs, recent = list(iter_blobs()), time.time() - 3600
            total = sum(b[1] for b in blobs)
            dropped = set()

            def drop(h, size, f):
                nonlocal total, freed
                try:
                    f.unlink()
                except OSError:
                    return
                total, freed = total - size, freed + size
                dropped.add(h)

            for h, size, mtime, f in blobs:   # 1) snapshots no change or file refers to any more
                if h not in keep and h not in newest and mtime < recent:
                    drop(h, size, f)
            if cap > 0 and total > cap:       # 2) still too big: oldest versions first
                for t, h, size, f in sorted((newest[h], h, size, f) for h, size, _, f in blobs
                                            if h in newest and h not in keep and h not in dropped):
                    if total <= cap:
                        break
                    drop(h, size, f)
            st.x('DELETE FROM contents WHERE hash NOT IN (SELECT hash FROM files WHERE hash IS NOT NULL)'
                 ' AND hash NOT IN (SELECT hash FROM events WHERE hash IS NOT NULL)'
                 ' AND hash NOT IN (SELECT prev_hash FROM events WHERE prev_hash IS NOT NULL)')
            if st.fts:  # the search index only needs the versions that are on disk now
                stale = 'SELECT id FROM ftsdoc WHERE hash NOT IN (SELECT hash FROM files WHERE hash IS NOT NULL)'
                st.x(f'DELETE FROM fts WHERE rowid IN ({stale})')
                st.x(f'DELETE FROM ftsdoc WHERE id IN ({stale})')
        if removed or freed:
            print(f'cleanup: {removed} old changes forgotten, {fmt_size(freed)} of snapshots freed')
            self.hub.publish({'type': 'cleared'})
        # Give unused database space back to the disk once it is a sizeable share of the file.
        pages, free, size = (st.q(f'PRAGMA {p}')[0][0] for p in ('page_count', 'freelist_count', 'page_size'))
        if free > pages * 0.25 and free * size > 50 * 1024 * 1024:
            with st.lock:
                st.conn.execute('VACUUM')
            print(f'database compacted: {fmt_size(free * size)} returned to the disk')
        return {'events': removed, 'freed': freed}

    # -- views -------------------------------------------------------------------
    def warnings(self):
        """Why the history may be incomplete right now, for a banner, the tray and Diagnostics (2.3.0)."""
        w = []
        if disk_low():
            w.append('lowdisk')
        if time.time() - getattr(self, 'last_overflow', 0) < 1800:
            w.append('overflow')
        if winwatch.available and self.settings['roots'] and not self.instant:
            w.append('noinstant')
        if App.integrity not in ('ok', None):
            w.append('integrity')
        if self.stats.get('offline_roots'):
            w.append('rootgone')
        if getattr(self, 'mass', None) and time.time() - self.mass['until'] < 6 * 3600:
            w.append('mass')
        return w

    def forget_root_files(self, root):
        """The user confirmed that a monitored folder that is away was deleted, not just unplugged:
        record its files as deleted (each can be restored from its kept version) (2.4.2)."""
        if root not in self.settings['roots'] or self.root_available(root):
            return 0
        n = 0
        with self.lock, self.store.batch():
            for p in [p for p in self.confirmed if under(p, root)]:
                c = self.confirmed.pop(p)
                self.store.x('DELETE FROM files WHERE path=?', (p,))
                self.emit('deleted', p, size=0, old_size=c[0], mtime=c[1], h=None, prev=c[2], flags='')
                n += 1
            if self.last:
                self.last = {k: v for k, v in self.last.items() if not under(k, root)}
        return n

    def status(self):
        return {**self.stats, 'offline_roots': self.stats.get('offline_roots') or [], 'mass': getattr(self, 'mass', None), 'warn': self.warnings(), 'paused': self.paused, 'pause_until': self.pause_until if self.paused else 0,
                'mute_until': float(self.settings.get('mute_until') or 0), 'roots': self.settings['roots'], 'instant': self.instant,
                'interval': self.settings['interval'], 'uptime': time.time() - self.started}

    def event_dict(self, eid=None, row=None):
        r = row if row is not None else self.store.q('SELECT * FROM events WHERE id=?', (eid,))[0]
        d = dict(r)
        root = self.root_of(d['path'])
        d['name'] = os.path.basename(d['path'])
        d['dir'] = os.path.dirname(d['path'])
        d['root'] = root
        d['rel_dir'] = os.path.relpath(d['dir'], root) if root else d['dir']
        if d['rel_dir'] == '.':
            d['rel_dir'] = ''
        d['root_name'] = os.path.basename(root.rstrip(os.sep)) if root else ''
        d['has_blob'] = self.store.has_blob(d['hash'])
        d['has_prev_blob'] = self.store.has_blob(d['prev_hash'])
        d['exists'] = os.path.exists(d['path'])
        d['flags'] = [f for f in (d['flags'] or '').split(',') if f]
        d['starred'] = d['path'] in self.stars
        d['pinned'] = is_pinned(d['path'])
        d['note'] = self.notes.get(d['id'])
        return d


def diff_counts(a, b):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=len(a) + len(b) > 4000)
    added = removed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('replace', 'delete'):
            removed += i2 - i1
        if tag in ('replace', 'insert'):
            added += j2 - j1
    return added, removed


def diff_report_html(ev, d, lang='en'):
    """One change as a self-contained HTML page: removed lines red, added green, changed words marked
    (2.6.0 #26). Opens in any browser; nothing is loaded from the internet."""
    import html as H
    zh = lang == 'zh'
    T = (lambda en, cn: cn if zh else en)

    def seg(row):
        if not row.get('s'):
            return H.escape(row['t'])
        return ''.join(f'<mark>{H.escape(x)}</mark>' if ch else H.escape(x) for ch, x in row['s'])
    body = []
    for h in d.get('hunks', []):
        body.append(f'<tr class="hunk"><td colspan="3">@@ {h["a"]} → {h["b"]}</td></tr>')
        for r in h['rows']:
            cls = {'-': 'del', '+': 'add'}.get(r['k'], 'ctx')
            body.append(f'<tr class="{cls}"><td class="n">{r.get("a", "")}</td><td class="n">{r.get("b", "")}</td>'
                        f'<td class="t"><span class="k">{r["k"]}</span>{seg(r)}</td></tr>')
    when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ev['ts']))
    return f"""<!doctype html><html lang="{'zh-CN' if zh else 'en'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{H.escape(ev['name'])} — {T('changes', '修改对比')}</title>
<style>
:root {{ --bg:#fff; --fg:#1b1f2a; --mute:#6b7280; --add:#e6f6ec; --addk:#137a3d; --del:#fdecec; --delk:#b42318; --hunk:#f1f3f8; --mark:#ffe08a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#14161c; --fg:#e7e9ee; --mute:#9aa1ae; --add:#163524; --addk:#5fd38d; --del:#3a1a1a; --delk:#ff8a80; --hunk:#1f2330; --mark:#6b5a12; }} }}
body {{ margin:0; background:var(--bg); color:var(--fg); font:14px/1.5 system-ui, "Microsoft YaHei", sans-serif; }}
header {{ padding:20px 24px 12px; }} h1 {{ font-size:20px; margin:0 0 4px; }} .meta {{ color:var(--mute); font-size:13px; }}
.sum b.p {{ color:var(--addk); }} .sum b.m {{ color:var(--delk); }}
table {{ border-collapse:collapse; width:100%; font:13px/1.45 Consolas, "Cascadia Mono", monospace; }}
td {{ padding:1px 8px; vertical-align:top; }} td.n {{ color:var(--mute); text-align:right; width:1%; white-space:nowrap; user-select:none; }}
td.t {{ white-space:pre-wrap; word-break:break-word; }} .k {{ display:inline-block; width:1.2em; color:var(--mute); }}
tr.add {{ background:var(--add); }} tr.add .k {{ color:var(--addk); }} tr.del {{ background:var(--del); }} tr.del .k {{ color:var(--delk); }}
tr.hunk td {{ background:var(--hunk); color:var(--mute); padding:4px 8px; }} mark {{ background:var(--mark); color:inherit; border-radius:2px; }}
footer {{ color:var(--mute); font-size:12px; padding:16px 24px; }}
</style></head><body><header><h1>{H.escape(ev['name'])}</h1>
<div class="meta">{H.escape(ev['path'])}<br>{T('Changed', '修改于')} {when}</div>
<div class="sum">{T('Added', '新增')} <b class="p">+{d.get('added', 0)}</b> · {T('removed', '删除')} <b class="m">−{d.get('removed', 0)}</b>
{T(' (shortened)', '（已截断）') if d.get('truncated') else ''}</div></header>
<table>{''.join(body)}</table><footer>{T('Made with DeskTrace', '由桌迹生成')} {APP_VERSION}</footer></body></html>"""


def build_diff(a, b, context=3, max_lines=6000):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=len(a) + len(b) > 4000)
    hunks, shown, truncated = [], 0, False
    for group in sm.get_grouped_opcodes(context):
        rows = []
        for tag, i1, i2, j1, j2 in group:
            if tag == 'equal':
                rows += [{'k': ' ', 'a': i + 1, 'b': j1 + (i - i1) + 1, 't': a[i]} for i in range(i1, i2)]
                continue
            dels = [{'k': '-', 'a': i + 1, 't': a[i]} for i in range(i1, i2)]
            adds = [{'k': '+', 'b': j + 1, 't': b[j]} for j in range(j1, j2)]
            if tag == 'replace':  # word-level highlights for paired lines
                for d, n in zip(dels, adds):
                    if len(d['t']) + len(n['t']) < 4000:
                        d['s'], n['s'] = inline_segments(d['t'], n['t'])
            rows += dels + adds
        hunks.append({'a': group[0][1] + 1, 'b': group[0][3] + 1, 'rows': rows})
        shown += len(rows)
        if shown > max_lines:
            truncated = True
            break
    added, removed = diff_counts(a, b)
    return {'hunks': hunks, 'added': added, 'removed': removed, 'truncated': truncated,
            'a_len': len(a), 'b_len': len(b)}


def inline_segments(x, y):
    sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
    if sm.ratio() < 0.3:
        return None, None
    sx, sy = [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if i2 > i1:
            sx.append([0 if tag == 'equal' else 1, x[i1:i2]])
        if j2 > j1:
            sy.append([0 if tag == 'equal' else 1, y[j1:j2]])
    return sx, sy


_scans = {}    # drive -> cleaner.DriveScan (2.2.0)
_cleanable = {}  # drive -> {'state', 'items'}: the cleanable places, worked out next to the scan


def save_scan(sc):
    """Keep a finished drive scan on disk, so Clean up opens on it at once next time (2.4.0 §3)."""
    data = zlib.compress(json.dumps(sc.to_dict()).encode('utf-8'), 6)
    App.store.x('INSERT OR REPLACE INTO drive_scans(drive, serial, mode, finished, data) VALUES(?,?,?,?,?)',
                (sc.root, sc.serial, sc.mode, sc.finished, data))
    App.store.x('DELETE FROM drive_scans WHERE drive NOT IN (SELECT drive FROM drive_scans ORDER BY finished DESC LIMIT 8)')
    if sc.mode == 'full' and sc.finished:  # the radar compares full scans over time (2.6.0 #1)
        sizes = {d: v[0] for d, v in sc.dirs.items() if v[0] >= GROWTH_KEEP}
        App.store.x('INSERT OR REPLACE INTO scan_history(drive, serial, finished, sizes) VALUES(?,?,?,?)',
                    (sc.root, sc.serial, sc.finished, zlib.compress(json.dumps(sizes).encode('utf-8'), 6)))
        App.store.x('DELETE FROM scan_history WHERE drive=? AND finished NOT IN '
                    '(SELECT finished FROM scan_history WHERE drive=? ORDER BY finished DESC LIMIT 30)', (sc.root, sc.root))


GROWTH_KEEP = 50 * 2 ** 20   # folders of 50 MB or more are remembered per full scan for the radar
GROWTH_MIN = 100 * 2 ** 20   # growth shown from 100 MB


def space_growth(d, days):
    """Space Spikes Radar (2.6.0 #1): the folders of drive ``d`` that grew most between the newest full scan
    and one about ``days`` days older (the oldest kept one if none is that old). Only the deepest folder that
    explains a growth is shown: if most of C:\\Users grew in one folder below it, that folder is the cause."""
    rows = App.store.q('SELECT finished, serial, sizes FROM scan_history WHERE drive=? ORDER BY finished DESC', (d,))
    rows = [r for r in rows if r['serial'] == cleaner.volume_serial(d)]
    if len(rows) < 2:
        return {'ok': True, 'ready': False, 'scans': len(rows)}
    new = rows[0]
    want = new['finished'] - days * 86400
    old = next((r for r in rows[1:] if r['finished'] <= want + 3 * 3600), rows[-1])
    a = json.loads(zlib.decompress(old['sizes']))
    b = json.loads(zlib.decompress(new['sizes']))
    delta = {f: b[f] - a.get(f, 0) for f in b if b[f] - a.get(f, 0) >= GROWTH_MIN}
    gone = sum(max(0, a[f] - b.get(f, 0)) for f in a if f not in b)
    picked = []
    for f in sorted(delta, key=lambda x: -delta[x]):
        pre = f.rstrip('\\') + '\\'
        # a deeper folder explains most of this growth: show that one instead
        if any(g.startswith(pre) and delta[g] >= delta[f] * 0.6 for g in delta if g != f):
            continue
        picked.append({'path': f, 'name': os.path.basename(f.rstrip('\\')) or f, 'grew': delta[f], 'was': a.get(f, 0), 'now': b[f],
                       'new': f not in a})
        if len(picked) >= 10:
            break
    total = b.get(d, 0) - a.get(d, 0)
    return {'ok': True, 'ready': True, 'from': old['finished'], 'to': new['finished'], 'total': total, 'items': picked,
            'shrunk': gone, 'scans': len(rows)}


def load_scan(d):
    """The kept scan of drive ``d``, or None; a scan of a different volume (another disk now has this
    letter, or it was formatted) is dropped and reported as such."""
    r = App.store.q('SELECT serial, data FROM drive_scans WHERE drive=?', (d,))
    if not r:
        return None
    if r[0]['serial'] != cleaner.volume_serial(d):
        App.store.x('DELETE FROM drive_scans WHERE drive=?', (d,))
        _scan_notes[d] = 'invalid'
        return None
    try:
        return cleaner.DriveScan.from_dict(json.loads(zlib.decompress(r[0]['data'])))
    except (ValueError, KeyError, zlib.error):
        return None


_scan_notes = {}  # drive -> 'invalid' when a kept scan no longer matched the disk


def quick_folders(d):
    """Your folders on drive ``d``: your user folder and the folders DeskTrace watches."""
    return [f for f in dict.fromkeys([os.environ.get('USERPROFILE', '')] + list(App.mon.settings['roots']))
            if f and cleaner.drive_of(f) == d and not any(under(f, g) and f != g for g in [os.environ.get('USERPROFILE', '')] + list(App.mon.settings['roots']))]


def scan_finished(sc):
    save_scan(sc)

    def shared():  # WinSxS hard links, afterwards and in the background, then kept too
        sc.background = background_thread
        sc.count_shared()
        if sc.shared:
            save_scan(sc)
    threading.Thread(target=shared, daemon=True, name='winsxs').start()


def start_scan(d, mode=None, priority=True):
    mode = mode if mode in ('quick', 'full') else ('quick' if cleaner.is_hdd(d) else 'full')
    _scans[d] = cleaner.DriveScan(d, None if priority else background_thread, mode=mode, folders=quick_folders(d),
                                  priority=priority, on_done=scan_finished)
    _scan_notes.pop(d, None)
    find_cleanable(d)


_prescan = {'checked': 0.0, 'running': False}


_pins = {'at': 0, 'set': set()}


def is_pinned(path):
    """The user chose "Keep forever" for this file (2.6.0 #20)."""
    if time.time() - _pins['at'] > 5:
        _pins.update(at=time.time(), set={os.path.normcase(r['path']) for r in App.store.q('SELECT path FROM pins')})
    return os.path.normcase(os.path.normpath(path)) in _pins['set']


MILESTONES = {'restored': (10, 100, 1000), 'freed': (10 * 2 ** 30, 100 * 2 ** 30, 2 ** 40)}


def milestone(kind, n):
    """Count ``n`` more restored files or freed bytes; the first time a step is passed, the window shows one
    quiet card (2.6.0 #50). Switched off in Settings with "milestones": false."""
    if not n or not App.mon.settings.get('milestones', True):
        return
    total = App.store.meta('count_' + kind, 0) + n
    App.store.set_meta('count_' + kind, total)
    shown = App.store.meta('milestones_shown', [])
    for step in MILESTONES[kind]:
        key = f'{kind}:{step}'
        if total >= step and key not in shown:
            App.store.set_meta('milestones_shown', shown + [key])
            App.hub.publish({'type': 'milestone', 'kind': kind, 'step': step, 'total': total})
            break


def lineage(path):
    """A file's kept versions in order, and the other files whose first version was one of them — copies,
    "Save as", attachments saved again (2.6.0 #38)."""
    rows = App.store.q("SELECT id, ts, kind, hash, prev_hash FROM events WHERE path=? AND hash IS NOT NULL AND kind != 'deleted' ORDER BY id", (path,))
    versions = [{'id': r['id'], 'ts': r['ts'], 'hash': r['hash']} for r in rows]
    if rows and rows[0]['prev_hash'] and rows[0]['kind'] != 'created':  # the version from before monitoring started
        versions.insert(0, {'id': None, 'ts': rows[0]['ts'], 'hash': rows[0]['prev_hash'], 'before': True})
    hashes = {v['hash'] for v in versions}
    branches = []
    if hashes:
        marks = ','.join('?' * len(hashes))
        for r in App.store.q(f"SELECT path, MIN(ts) ts, hash FROM events WHERE hash IN ({marks}) AND path != ? AND kind IN ('created', 'modified')"
                             ' GROUP BY path ORDER BY ts LIMIT 30', (*hashes, path)):
            first = App.store.q("SELECT hash FROM events WHERE path=? AND hash IS NOT NULL ORDER BY id LIMIT 1", (r['path'],))
            if first and first[0]['hash'] in hashes:  # it started as one of these versions
                branches.append({'path': r['path'], 'name': os.path.basename(r['path']), 'ts': r['ts'], 'from': first[0]['hash']})
    return {'versions': versions, 'branches': branches}


def note_last_clean(paths, size):
    """Remember what a cleanup moved to the Recycle Bin, so it can be put back later from Clean up — not
    only within a few seconds (2.4.2, review P2-1). Cleanups within two minutes count as one."""
    if not paths:
        return
    last, now = App.store.meta('last_clean') or {}, time.time()
    if last.get('paths') and now - last.get('at', 0) < 120:
        paths, size, since = (last['paths'] + list(paths))[:5000], last.get('size', 0) + size, last['since']
    else:
        since = now - 5
    App.store.set_meta('last_clean', {'paths': list(paths), 'size': size, 'since': since, 'at': now})


def maybe_prescan():
    """Called from the monitor loop, which wakes anyway: at most every 10 minutes, start one pre-scan when due."""
    if (_prescan['running'] or time.time() - _prescan['checked'] < 600 or time.time() - App.mon.started < 300
            or time.time() - getattr(App.mon, 'woke_at', 0) < 300):  # not in the first minutes after waking (2.4.2)
        return
    _prescan['checked'] = time.time()

    def go():
        _prescan['running'] = True
        try:
            prescan_once()
        finally:
            _prescan['running'] = False
    threading.Thread(target=go, daemon=True, name='prescan').start()


def prescan_loop():
    """Background pre-scan (2.4.0): while the PC is idle, plugged in and not running a full-screen app, the
    drives with your folders are read again when their kept scan is over 12 hours old — at background
    priority, one folder at a time — so Clean up opens on fresh results. Switch off in Settings."""
    while True:
        prescan_once()
        time.sleep(600)


def prescan_once():
    if True:
        try:
            idle = time.time() - App.last_request > 300
            if App.mon.settings.get('prescan', True) and idle and not on_battery() and not user_busy_fullscreen() and not disk_low():
                drives = dict.fromkeys([cleaner.system_drive()] + [cleaner.drive_of(r) for r in App.mon.settings['roots']])
                for d in drives:
                    if d not in [x['drive'] for x in cleaner.drives()]:
                        continue
                    r = App.store.q('SELECT finished FROM drive_scans WHERE drive=?', (d,))
                    sc = _scans.get(d)
                    if (r and time.time() - r[0]['finished'] < 12 * 3600) or (sc and sc.state == 'scanning'):
                        continue
                    pre = cleaner.DriveScan(d, background_thread, mode='quick' if cleaner.is_hdd(d) else 'full',
                                            folders=quick_folders(d), on_done=scan_finished, start=False)
                    pre.run()  # in this thread, at background priority
                    App.prescanned[d] = time.time()
                    break  # one drive per round
        except Exception as e:
            print('pre-scan error:', repr(e), file=sys.stderr)


def clean_drive(d):
    """A drive the user may look at: one of this PC's drives, spelled "X:\\"."""
    d = (str(d or '').strip()[:2].upper() + '\\') if d else cleaner.system_drive()
    return d if any(x['drive'] == d for x in cleaner.drives()) else None


def find_cleanable(drive):
    _cleanable[drive] = {'state': 'scanning', 'items': (_cleanable.get(drive) or {}).get('items')}

    def work():
        background_thread()
        try:
            _cleanable[drive] = {'state': 'done', 'items': cleaner.cleanable(drive)}
        except Exception as e:
            _cleanable[drive] = {'state': 'failed', 'items': [], 'error': repr(e)}
    threading.Thread(target=work, daemon=True, name='cleanable').start()


def restore_copy_name(target, lang):
    """The name a restored copy gets when the original name is taken: the original is never overwritten."""
    stem, ext = os.path.splitext(target)
    word = {'zh': '恢复于'}.get(lang, 'restored')
    return f'{stem} ({word} {time.strftime("%Y-%m-%d %H-%M-%S")}){ext}'  # half-width brackets, readable time (2.4.1)


def fmt_size(n):
    n = float(n or 0)
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB':
            return f'{n:.0f} {u}' if u == 'B' else f'{n:.1f} {u}'
        n /= 1024


_disk = {'at': 0.0, 'low': False, 'free': None}


def disk_low():
    """True while the drive that holds DeskTrace's history has less than 1 GB free: changes are still
    recorded, but no new copies of versions are kept, so DeskTrace never fills up the disk (2.1.0)."""
    now = time.time()
    if now - _disk['at'] > 30:
        try:
            _disk['free'] = shutil.disk_usage(DATA).free
            _disk['low'] = _disk['free'] < 1024 ** 3
        except OSError:
            _disk['low'] = False
        _disk['at'] = now
    return _disk['low']


def recompress_old(store, limit=3000):
    """Compress snapshots kept before 2.4.0, a batch per upkeep run, at background priority: each is
    replaced in one step (os.replace), and only when it really gets smaller and reads back the same."""
    done = 0
    for h, size, _, path in iter_blobs():
        if done >= limit:
            break
        if size < 4096 or size > 64 * 2 ** 20:
            continue
        try:
            with open(path, 'rb') as fh:
                if fh.read(4) == SNAP_MAGIC:
                    continue
            raw = path.read_bytes()
            packed = pack_snapshot(raw)
            if packed is raw or len(packed) >= len(raw) or unpack_snapshot(packed) != raw:
                continue
            wait_for_power(store)
            tmp = path.with_suffix('.tmp')
            tmp.write_bytes(packed)
            os.replace(tmp, path)
            done += 1
        except (OSError, SnapshotError):
            continue
    return done


def verify_blobs(store, limit=2000):
    """Read kept versions back, a batch per upkeep run at background priority, and check that each one's
    content still matches its name (SHA-1 or SHA-256) (2.6.0 #43). A damaged one is reported in Diagnostics
    and in the warning bar; it is never "repaired" by guessing. The next batch starts where this one ended."""
    names = sorted(h for h, _, _, _ in iter_blobs())
    if not names:
        return
    start = store.meta('verify_at', '')
    todo = [h for h in names if h > start][:limit] or names[:limit]
    bad = set(store.meta('blobs_bad', []))
    for h in todo:
        wait_for_power(store)
        try:
            data = store.read_blob(h)
            ok = (hashlib.sha1 if len(h) == 40 else hashlib.sha256)(data).hexdigest() == h
        except (OSError, SnapshotError):
            ok = False
        (bad.discard if ok else bad.add)(h)
    store.set_meta('verify_at', todo[-1] if todo[-1] != names[-1] else '')
    store.set_meta('blobs_bad', sorted(bad))
    store.set_meta('verify_last', time.time())
    if bad:
        App.integrity = f'{len(bad)} kept versions are damaged (their content no longer matches)'


def check_integrity():
    """SQLite's quick check of the history database (2.3.0, review P0-4): a damaged database is shown,
    not silently used."""
    try:
        r = App.store.q('PRAGMA quick_check(5)')
        App.integrity = 'ok' if r and r[0][0] == 'ok' else '; '.join(str(x[0]) for x in r)[:300]
    except Exception as e:
        App.integrity = repr(e)[:300]


SNAP_FORMAT = 'DTS1 (zlib), DeskTrace 2.4.0 or later'


def backup_history(dest, raw=False):
    """Copy the whole history (database, kept versions, settings) to ``dest``\\DeskTrace backup, e.g. on
    another drive (2.3.0, review P0-4 / P1-15). The database is copied with SQLite's backup API, so it is
    consistent while DeskTrace keeps running; versions already in the backup are not copied again."""
    b = App.backup
    try:
        background_thread()
        root = Path(dest) / 'DeskTrace backup'
        (root / 'blobs').mkdir(parents=True, exist_ok=True)
        import sqlite3 as sq
        target = sq.connect(str(root / 'watch.db'))
        with App.store.lock:
            App.store.conn.backup(target)
        target.close()
        shutil.copy2(SETTINGS_FILE, root / 'settings.json')
        blobs = list(iter_blobs())
        b.update(total=len(blobs), done=0, bytes=0)
        for h, size, _, src in blobs:
            out = root / 'blobs' / h[:2] / h
            if raw:  # for DeskTrace 2.3.0 or older: every version written out uncompressed (2.4.1)
                data = App.store.read_blob(h)
                if not out.exists() or out.stat().st_size != len(data):
                    out.parent.mkdir(exist_ok=True)
                    out.write_bytes(data)
                    b['bytes'] += len(data)
            elif not out.exists() or out.stat().st_size != size:
                out.parent.mkdir(exist_ok=True)
                shutil.copyfile(src, out)
                b['bytes'] += size
            b['done'] += 1
        (root / 'FORMAT.txt').write_text(  # which DeskTrace can read this backup (2.4.1)
            ('Snapshots: uncompressed — readable by every DeskTrace version.\n' if raw else
             'Snapshots: ' + SNAP_FORMAT + '. Older versions cannot read them; back up "for older versions" for those.\n') +
            'Made by DeskTrace ' + APP_VERSION + ', ' + time.strftime('%Y-%m-%d %H:%M') + '.\n', 'utf-8')
        (root / 'README.txt').write_text('DeskTrace history backup, ' + time.strftime('%Y-%m-%d %H:%M') +
                                         '.\nTo use it: quit DeskTrace and copy these files into its data folder '
                                         '(%LOCALAPPDATA%\\DeskTrace\\data).\n', 'utf-8')
        b.update(state='done', path=str(root), finished=time.time())
    except Exception as e:
        b.update(state='failed', error=repr(e)[:300], finished=time.time())


def ctypes_fs_name(drive):
    """The file system of ``drive`` ("NTFS", "exFAT", ...)."""
    import ctypes
    name = ctypes.create_unicode_buffer(32)
    ok = ctypes.windll.kernel32.GetVolumeInformationW(drive, None, 0, None, None, None, name, 32) if os.name == 'nt' else 0
    return name.value if ok else ''


def pick_backup_file():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        p = filedialog.askopenfilename(title=APP_NAME, filetypes=[(APP_NAME + ' history', '*.dtbackup')])
        root.destroy()
        return os.path.normpath(p) if p else ''
    except Exception:
        return ''


def pending_dir():
    return DATA.parent / (DATA.name + ' import pending')


def export_history(dest):
    """The whole history — database, every kept version, settings — as one file in ``dest``, to take to
    another PC (2.6.0 #44). Versions are already compressed, so the file is stored, not zipped again."""
    b = App.backup
    try:
        background_thread()
        out = Path(dest) / f'DeskTrace history {time.strftime("%Y-%m-%d %H-%M")}.dtbackup'
        tmp = DATA / 'export-tmp.db'
        target = sqlite3.connect(str(tmp))
        with App.store.lock:
            App.store.conn.backup(target)
        target.close()
        blobs = list(iter_blobs())
        b.update(total=len(blobs), done=0, bytes=0)
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_STORED, allowZip64=True) as z:
            z.write(tmp, 'watch.db')
            z.write(SETTINGS_FILE, 'settings.json')
            z.writestr('FORMAT.txt', 'DeskTrace history export. Snapshots: ' + SNAP_FORMAT + '.\nMade by DeskTrace '
                       + APP_VERSION + ', ' + time.strftime('%Y-%m-%d %H:%M') + '.\n')
            for h, size, _, src in blobs:
                z.write(src, f'blobs/{h[:2]}/{h}')
                b['done'] += 1
                b['bytes'] += size
        tmp.unlink()
        b.update(state='done', path=str(out), finished=time.time())
    except Exception as e:
        b.update(state='failed', error=repr(e)[:300], finished=time.time())


def stage_import(path):
    """Check a .dtbackup file and unpack it next to the data folder; the next start uses it (2.6.0 #44)."""
    try:
        with zipfile.ZipFile(path) as z:
            names = set(z.namelist())
            if 'watch.db' not in names or 'settings.json' not in names:
                return {'ok': False, 'code': 'notBackup'}
            if any(n.startswith(('/', '\\')) or '..' in n.split('/') for n in names):
                return {'ok': False, 'code': 'notBackup'}  # never write outside the folder
            pend = pending_dir()
            shutil.rmtree(pend, ignore_errors=True)
            z.extractall(pend)
        con = sqlite3.connect(str(pend / 'watch.db'))
        ok = con.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
        con.close()
        if not ok:
            shutil.rmtree(pend, ignore_errors=True)
            return {'ok': False, 'code': 'damaged'}
        return {'ok': True}
    except (OSError, zipfile.BadZipFile, sqlite3.Error):
        return {'ok': False, 'code': 'notBackup'}


def apply_pending_import():
    """At start, before the history is opened: an imported history takes the data folder's place; what was
    there is kept as "<data> before import <time>" (2.6.0 #44)."""
    pend = pending_dir()
    if not (pend / 'watch.db').exists():
        return
    keep = DATA.parent / f'{DATA.name} before import {time.strftime("%Y-%m-%d %H-%M-%S")}'
    if DATA.exists():
        DATA.rename(keep)
    pend.rename(DATA)
    print(f'imported history applied; the previous one is kept in {keep}')


def iter_blobs():
    """(hash, size, mtime, path) of every stored snapshot, read from the folder listings alone (2.1.0:
    housekeeping looked at each file separately while change detection waited)."""
    try:
        subs = [e.path for e in os.scandir(BLOBS) if e.is_dir(follow_symlinks=False)]
    except OSError:
        return
    for d in subs:
        try:
            with os.scandir(d) as it:
                for e in it:
                    if len(e.name) in (40, 64):
                        try:
                            st = e.stat(follow_symlinks=False)
                        except OSError:
                            continue
                        yield e.name, st.st_size, st.st_mtime, Path(e.path)
        except OSError:
            continue


def dir_size(p):
    """Total size of the files in a folder. On Windows the sizes come with the folder listing itself, so
    there is no extra call per file (2.1.0: was about one second per look at a data folder of thousands of
    snapshots, every 30 seconds while the window was open)."""
    total, stack = 0, [str(p)]
    while stack:
        try:
            it = os.scandir(stack.pop())
        except OSError:
            continue
        with it:
            for e in it:
                try:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    else:
                        total += e.stat(follow_symlinks=False).st_size
                except OSError:
                    pass
    return total


# ---------------------------------------------------------------------------- HTTP

class App:
    store: Store
    mon: Monitor
    hub: Hub
    port: int
    diff_cache = None     # SizedCache, set up below App (2.1.0)
    integrity = None     # 'ok', or what SQLite's quick check reported (2.3.0)
    prescanned = {}      # drive -> when the background pre-scan last read it (2.4.0)
    backup = {}          # the running or last history backup (2.3.0)
    move = {}            # the running or last folder move to another drive (2.6.0 #3)
    current_cache = None
    storage = {'bytes': 0, 'at': 0}
    tray = None
    notifier = None
    updates = None      # updmod.Updates: version licenses found in the monitored folders
    last_request = time.time()  # when the window last asked for something (idle memory trim, 2.1.0)
    trimmed = False
    notify_hash = ''    # what clicking the last desktop notification opens


def strip_lines(res):
    return {k: v for k, v in res.items() if k != 'lines'} if res else res


def file_row(p, size, mtime, h, changes):
    """A tracked file as the Files view shows it."""
    root = App.mon.root_of(p) or ''
    rel = os.path.relpath(os.path.dirname(p), root) if root else os.path.dirname(p)
    ext = os.path.splitext(p)[1].lower()
    return {'path': p, 'name': os.path.basename(p), 'dir': os.path.dirname(p), 'root': root,
            'root_name': os.path.basename(root.rstrip(os.sep)), 'rel_dir': '' if rel == '.' else rel,
            'ext': ext, 'cat': category_of(ext), 'size': size, 'mtime': mtime / 1e9, 'indexed': bool(h),
            'changes': changes, 'exists': True, 'starred': p in App.mon.stars, 'protect': protection(p, size, h)}


def protection(p, size, h):
    """How DeskTrace protects one file right now (2.3.0, review P0-3): 'kept' (a copy of the current
    version), 'big' (over the snapshot limit: changes are recorded, no copies), 'cloud' (online-only),
    'text' (only its text was indexed; the first copy is made at its next change) or 'pending'."""
    if size and size > App.mon.settings['snapshot_max_mb'] * 2 ** 20:
        return 'big'
    if h and App.store.has_blob(h):
        return 'kept'
    if cleaner.online_only(p):
        return 'cloud'
    return 'text' if h else 'pending'


_counts_cache = {'key': None, 'counts': {}}


def events_key():
    k = App.store.q('SELECT MAX(id) m, COUNT(*) n FROM events')[0]
    return k['m'], k['n']


def new_rows(cache, key, cols):
    """The changes recorded since ``cache`` was worked out, or None when it has to be worked out from the
    start (older changes were forgotten in the meantime). Changes are only ever added at the end (2.1.0)."""
    old = cache.get('key')
    if not old or old[0] is None or key[0] is None or key[0] < old[0]:
        return None
    rows = App.store.q(f'SELECT {cols} FROM events WHERE id > ? ORDER BY id', (old[0],))
    return rows if old[1] + len(rows) == key[1] else None


def change_counts():
    """Recorded changes per current path, carried across renames and moves. After a change only the new
    changes are added (2.1.0: counting all of a long history again took a quarter second each time)."""
    key = events_key()
    c = _counts_cache
    if c['key'] == key:
        return c['counts']
    rows = new_rows(c, key, 'kind, path, old_path')
    if rows is None:
        total, rows = {}, App.store.q('SELECT kind, path, old_path FROM events ORDER BY id')
    else:
        total = dict(c['counts'])  # a copy: a request may still be reading the previous one
    for r in rows:
        if r['kind'] == 'renamed' and r['old_path']:
            total[r['path']] = total.get(r['path'], 0) + total.pop(r['old_path'], 0) + 1
        else:
            total[r['path']] = total.get(r['path'], 0) + 1
    c.update(key=key, counts=total)
    return total


_totals_cache = {'key': None}


def event_totals():
    """All-time changes per kind and per file type, and saved versions, kept current the same way (2.1.0: about 150 ms on a
    long history at every refresh of the statistics, i.e. every 30 seconds while the window is open)."""
    key = events_key()
    c = _totals_cache
    if c['key'] != key:
        rows = new_rows(c, key, 'kind, cat, hash')
        if rows is None:
            kinds = {r['kind']: r['n'] for r in App.store.q('SELECT kind, COUNT(*) n FROM events GROUP BY kind')}
            cats = {r['cat']: r['n'] for r in App.store.q('SELECT cat, COUNT(*) n FROM events GROUP BY cat')}
            versions = 0
        else:
            kinds, cats, versions = dict(c['kinds']), dict(c['cats']), c['versions']
            for r in rows:
                kinds[r['kind']] = kinds.get(r['kind'], 0) + 1
                cats[r['cat']] = cats.get(r['cat'], 0) + 1
                versions += r['hash'] is not None
        c.update(key=key, kinds=kinds, cats=cats, versions=versions)
    return c['kinds'], c['cats'], c['versions']


def file_history(path, limit=300):
    """A file's changes, newest first, following renames back to its earlier names."""
    st, clauses, args = App.store, ['path = ?', 'old_path = ?'], [path, path]
    cur, until, seen = path, None, {path}
    for _ in range(50):
        r = st.q("SELECT old_path, ts FROM events WHERE kind = 'renamed' AND path = ? AND (? IS NULL OR ts <= ?)"
                 ' ORDER BY id DESC LIMIT 1', (cur, until, until))
        if not r or not r[0]['old_path'] or r[0]['old_path'] in seen:
            break
        cur, until = r[0]['old_path'], r[0]['ts']
        seen.add(cur)
        clauses.append('(path = ? AND ts < ?)')  # the old name's events from before the rename only
        args += [cur, until]
    return st.q(f"SELECT * FROM events WHERE {' OR '.join(clauses)} ORDER BY id DESC LIMIT ?", args + [limit])


_view_cache = {}  # name -> (key, result): Duplicates and Space are only worked out again after a change (2.1.0)


def approx_size(o):
    """Roughly how much memory a result takes (strings, lists and dicts of them)."""
    if isinstance(o, str):
        return 50 + len(o) * (1 if o.isascii() else 3)
    if isinstance(o, dict):
        return 64 + sum(approx_size(k) + approx_size(v) for k, v in o.items())
    if isinstance(o, (list, tuple)):
        return 56 + 8 * len(o) + sum(approx_size(x) for x in o)
    return 32


class SizedCache:
    """Recent results up to a total size, the least recently used dropped first (2.1.0: the caches of
    compared versions and current files were limited by count, so a few huge documents could keep
    hundreds of MB in memory)."""

    def __init__(self, limit):
        self.limit, self.d, self.size, self.lock = limit, {}, 0, threading.Lock()

    def get(self, k):
        with self.lock:
            v = self.d.pop(k, None)
            if v is None:
                return None
            self.d[k] = v  # now the most recently used
            return v[0]

    def __setitem__(self, k, v):
        w = approx_size(v)
        with self.lock:
            old = self.d.pop(k, None)
            if old:
                self.size -= old[1]
            if w > self.limit:
                return
            self.d[k] = (v, w)
            self.size += w
            while self.size > self.limit:
                self.size -= self.d.pop(next(iter(self.d)))[1]

    def clear(self):
        with self.lock:
            self.d.clear()
            self.size = 0

    def __len__(self):
        return len(self.d)


App.diff_cache, App.current_cache = SizedCache(64 * 2 ** 20), SizedCache(64 * 2 ** 20)


def view_cached(name, fn):
    key = (App.mon.gen, len(_big_hash), int(time.time() // 600), tuple(App.mon.settings['roots']))
    hit = _view_cache.get(name)
    if hit and hit[0] == key:
        return hit[1]
    res = fn()
    if len(_view_cache) > 40:
        _view_cache.clear()
    _view_cache[name] = (key, res)
    return res


_big_hash = {}        # (path, size, mtime) -> sha1 of large files without a snapshot (2.0.1)
_big_busy = threading.Event()


def same_content(a, b):
    """Two content keys name the same content, also when one was kept before 2.4.2 (SHA-1)."""
    if not a or not b:
        return False
    return a == b or (len(a) != len(b) and a[0] != 'L' and b[0] != 'L' and App.store.sha256_of(a) == App.store.sha256_of(b))


def content_key(p, c):
    """The content hash of a tracked file: its snapshot hash, or the hash worked out for a large file."""
    return c[2] or _big_hash.get((p, c[0], c[1]))


def hash_large(todo):
    """Hash large same-size files in the background (once per version), so Duplicates can compare them."""
    background_thread()  # very low disk priority: other programs come first (2.1.0)
    try:
        for p, size, mtime in todo:
            wait_for_power()
            if cleaner.online_only(p):
                continue  # comparing would download it from the cloud
            h = hashlib.sha256()
            try:
                with open(p, 'rb') as f:
                    for i, block in enumerate(iter(lambda: f.read(1 << 20), b'')):
                        h.update(block)
                        if i % 16 == 15:
                            time.sleep(0.01)  # leave the disk some air between 16 MB stretches
            except OSError:
                continue
            _big_hash[(p, size, mtime)] = 'L' + h.hexdigest()
    finally:
        _big_busy.clear()


def history_storage():
    """The files whose kept versions take the most of DeskTrace's own space (2.1.0). A snapshot shared by
    several files counts for each of them once."""
    per = {}
    for r in App.store.q('SELECT path, hash, prev_hash FROM events'):
        for h in (r['hash'], r['prev_hash']):
            if h:
                per.setdefault(r['path'], set()).add(h)
    on_disk = {h: size for h, size, _, _ in iter_blobs()}  # one listing instead of one look per snapshot (2.1.0)
    sizes = {h: on_disk.get(h, 0) for hs in per.values() for h in hs}
    rows = sorted(((sum(sizes[h] for h in hs), sum(1 for h in hs if sizes[h]), p) for p, hs in per.items()), reverse=True)
    total = sum(sizes.values())
    files = [{'path': p, 'name': os.path.basename(p), 'size': s, 'versions': n, 'exists': os.path.exists(p),
              'ext': os.path.splitext(p)[1].lower(), 'cat': category_of(os.path.splitext(p)[1].lower())}
             for s, n, p in rows[:40] if s]
    return {'total': total, 'files': files}


def top_folders(sizes, n):
    """The biggest folders without listing one inside another (a folder that is almost all one subfolder
    shows as that subfolder; 2.0.1)."""
    out = []
    for d, s in sorted(sizes.items(), key=lambda x: -x[1]):
        if any(under(d, o) or under(o, d) for o, _ in out):
            parent = next((i for i, (o, _) in enumerate(out) if under(d, o)), None)
            if parent is not None and s >= out[parent][1] * 0.9:
                out[parent] = (d, s)  # the parent is really just this subfolder
            continue
        out.append((d, s))
        if len(out) >= n:
            break
    return out


def valid_hash(h):
    return isinstance(h, str) and len(h) in (40, 64) and all(c in '0123456789abcdef' for c in h)


def make_snippet(body, q, width=48):
    """A short excerpt around the first match, with \\x02 / \\x03 around the match itself."""
    i = body.lower().find(q.lower())
    if i < 0:
        return body[:width * 2]
    start, end = max(0, i - width), min(len(body), i + len(q) + width)
    return ('…' if start else '') + body[start:i] + '\x02' + body[i:i + len(q)] + '\x03' + body[i + len(q):end] + ('…' if end < len(body) else '')


class Handler(BaseHTTPRequestHandler):
    server_version = 'DesktopWatch'
    protocol_version = 'HTTP/1.1'

    def log_message(self, *a):
        pass

    # -- plumbing ---------------------------------------------------------------
    def host_ok(self):
        host = (self.headers.get('Host') or '').split(':')[0]
        return host in ('127.0.0.1', 'localhost', '[::1]')

    def authorized(self):
        """The app window (cookie from /app?k=...) or a tool that read instance.json (X-Token header)."""
        if self.headers.get('X-Token') == TOKEN:
            return True
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get('Cookie') or '')
        except http.cookies.CookieError:
            return False
        return 'dw' in jar and secrets.compare_digest(jar['dw'].value, TOKEN)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(self, data, ctype, extra=None, code=200):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path, name, data=None):
        ctype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        if ctype.startswith('text/') or ctype in ('application/json', 'application/javascript'):
            ctype += '; charset=utf-8'
        headers = {'Content-Disposition': "inline; filename*=UTF-8''" + urllib.parse.quote(name),
                   'X-Content-Type-Options': 'nosniff'}
        if ctype.startswith(('text/html', 'image/svg')):  # never run scripts from watched files
            headers['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src data:; style-src 'unsafe-inline'"
        self.send_bytes(data if data is not None else Path(path).read_bytes(), ctype, headers)

    def body(self):
        n = int(self.headers.get('Content-Length') or 0)
        return json.loads(self.rfile.read(n) or b'{}') if n else {}

    def allowed_path(self, p):
        """Only paths inside the monitored folders, or ones we have history for."""
        if not p:
            return False
        if any(under(p, r) for r in App.mon.settings['roots']):
            return True
        return bool(App.store.q('SELECT 1 FROM events WHERE path=? OR old_path=? LIMIT 1', (p, p)))

    # -- routes -------------------------------------------------------------------
    def do_GET(self):
        App.last_request, App.trimmed = time.time(), False
        if not self.host_ok():
            return self.send_json({'error': 'bad host'}, 403)
        u = urllib.parse.urlparse(self.path)
        qs = {k: v[-1] for k, v in urllib.parse.parse_qs(u.query).items()}
        route = u.path
        try:
            if route == '/app':  # the app window's way in: swap the key in the URL for a session cookie
                if not secrets.compare_digest(qs.get('k', ''), TOKEN):
                    return self.send_bytes(locked_page(), 'text/html; charset=utf-8', {'Cache-Control': 'no-store'}, 403)
                return self.send_bytes(b'', 'text/plain', {'Location': '/', 'Cache-Control': 'no-store',
                                                           'Set-Cookie': f'dw={TOKEN}; Path=/; HttpOnly; SameSite=Strict'}, 302)
            if route == '/api/ping':
                return self.send_json({'app': APP_ID, 'data': str(DATA)})
            if not self.authorized():
                if route.startswith('/api/'):
                    return self.send_json({'error': 'forbidden'}, 403)
                return self.send_bytes(locked_page(), 'text/html; charset=utf-8', {'Cache-Control': 'no-store'}, 403)
            if route in ('/', '/index.html'):
                html = (STATIC / 'index.html').read_text('utf-8').replace('__TOKEN__', TOKEN).replace('__VERSION__', APP_VERSION)
                return self.send_bytes(html.encode('utf-8'), 'text/html; charset=utf-8', {'Cache-Control': 'no-store'})
            if route.startswith('/static/'):
                f = (STATIC / route[len('/static/'):]).resolve()
                if STATIC in f.parents and f.is_file():
                    ctype = mimetypes.guess_type(f.name)[0] or 'application/octet-stream'
                    return self.send_bytes(f.read_bytes(), ctype + ('; charset=utf-8' if ctype.startswith(('text', 'application/javascript')) else ''),
                                           {'Cache-Control': 'no-store'})
                return self.send_json({'error': 'not found'}, 404)
            if route == '/api/autostart':
                return self.send_json({'enabled': STARTUP_LNK.exists(), 'supported': os.name == 'nt'})
            if route == '/api/update':
                return self.send_json(App.updates.status(qs.get('lang') if qs.get('lang') in TEXT else ui_lang()))
            if route == '/api/stream':
                return self.stream()
            if route == '/api/events':
                return self.send_json(self.events(qs))
            if route == '/api/event':
                return self.send_json(App.mon.event_dict(int(qs['id'])))
            if route == '/api/files':
                return self.send_json(self.files(qs))
            if route == '/api/search':
                return self.send_json(self.search(qs))
            if route == '/api/media':
                return self.media(qs)
            if route == '/api/lineage':  # versions and the copies made from them (2.6.0 #38)
                return self.send_json(lineage(qs.get('path', '')))
            if route == '/api/history':
                return self.send_json([App.mon.event_dict(row=r) for r in file_history(qs['path'])])
            if route == '/api/file-info':
                return self.send_json(self.file_info(qs.get('path', '')))
            if route == '/api/duplicates':
                return self.send_json(view_cached('dups', self.duplicates))
            if route == '/api/space':
                f = qs.get('folder', '')
                if f and not any(under(f, r) for r in App.mon.settings['roots']):
                    return self.send_json({'error': 'not allowed'}, 403)
                f = os.path.normpath(f) if f else ''
                return self.send_json(view_cached('space:' + f, lambda: self.space(f)))
            if route == '/api/storage':  # which files' kept versions use DeskTrace's space (2.1.0)
                return self.send_json(view_cached('storage', history_storage))
            if route == '/api/clean/leftovers':  # possible leftovers of uninstalled programs (2.6.0 #2)
                d = cleaner.system_drive()
                sc = _scans.get(d) or load_scan(d)
                sizes = {k: v[0] for k, v in sc.dirs.items()} if sc and sc.state != 'scanning' else {}
                App.leftovers = cleaner.leftovers(sizes) if sizes else []
                return self.send_json({'ok': True, 'ready': bool(sizes), 'items': App.leftovers})
            if route == '/api/clean/git':  # large Git repositories (2.6.0 #29)
                App.git_repos = cleaner.git_repos()
                return self.send_json({'items': App.git_repos, 'git': bool(shutil.which('git'))})
            if route == '/api/relocate':  # progress of a folder move, and the folders moved so far (2.6.0 #3)
                return self.send_json({**App.move, 'moves': App.store.meta('moves', [])})
            if route == '/api/drafts':  # recent unsaved drafts of Office / WPS (2.6.0 #24)
                App.drafts = cleaner.recent_drafts()
                return self.send_json({'items': App.drafts})
            if route == '/api/chat-media':  # what a chat app keeps, by kind, older than N days (2.6.0 #7)
                a = next((x for x in cleaner.chat_apps() if x['app'] == qs.get('app')), None)
                if not a:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                m = cleaner.chat_media(a['data'], max(7, int(qs.get('days', 90))))
                return self.send_json({'ok': True, 'kinds': {k: {'n': len(v), 'size': sum(x[1] for x in v)} for k, v in m.items()}})
            if route == '/api/clean/locales':  # programs' language packs, listed only (2.6.0 #27)
                return self.send_json({'items': cleaner.language_packs()})
            if route == '/api/clean/badnames':  # names Windows cannot handle (2.6.0 #35)
                App.badnames = cleaner.bad_names()
                return self.send_json({'items': App.badnames})
            if route == '/api/clean/cloud':  # synced folders: on this PC vs online-only (2.6.0 #30)
                return self.send_json({'items': cleaner.cloud_overview()})
            if route == '/api/clean/health':  # disk health as Windows reports it (2.6.0 #34)
                return self.send_json({'disks': cleaner.disk_health()})
            if route == '/api/clean/growth':  # Space Spikes Radar (2.6.0 #1)
                d = clean_drive(qs.get('drive'))
                if not d:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                return self.send_json(space_growth(d, max(1, min(30, int(qs.get('days', 1))))))
            if route == '/api/clean/last':  # what the last cleanup moved to the Recycle Bin (2.4.2)
                last = App.store.meta('last_clean') or {}
                return self.send_json({'n': len(last.get('paths') or []), 'size': last.get('size', 0), 'at': last.get('at', 0)})
            if route == '/api/clean/drives':  # drives for the space cleaner (2.2.0)
                return self.send_json({'drives': cleaner.drives(), 'system': cleaner.system_drive()})
            if route == '/api/clean/scan':  # what the scan of a drive (or one folder of it) found so far
                d = clean_drive(qs.get('drive'))
                if not d:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if d not in _scans:
                    kept = load_scan(d)  # opens at once on the last scan (2.4.0 §3)
                    if kept:
                        _scans[d] = kept
                        if d not in _cleanable:
                            find_cleanable(d)
                sc, cl = _scans.get(d), _cleanable.get(d) or {}
                usage = next((x for x in cleaner.drives() if x['drive'] == d), {})
                out = {'ok': True, 'drive': d, 'usage': usage, 'items': cl.get('items'), 'items_state': cl.get('state'),
                       'note': _scan_notes.get(d), 'hdd': cleaner.is_hdd(d), 'quick_default': cleaner.is_hdd(d)}
                if sc:
                    out.update(sc.summary(qs.get('folder') or None) if sc.state != 'scanning' else sc.progress())
                return self.send_json(out)
            if route == '/api/restore-plan':  # where a restore would go, before it happens (2.3.0, review P0-2)
                r = App.store.q('SELECT * FROM events WHERE id=?', (int(qs.get('id', 0)),))
                if not r:
                    return self.send_json({'ok': False, 'code': 'gone'})
                r, version = r[0], qs.get('version', 'this')
                h = r['prev_hash'] if version == 'prev' else (r['hash'] or r['prev_hash'])
                target = r['old_path'] if r['kind'] == 'renamed' and version == 'prev' else r['path']
                exists = os.path.exists(target)
                with App.mon.lock:
                    c = App.mon.confirmed.get(target)
                return self.send_json({'ok': App.store.has_blob(h), 'target': target, 'exists': exists,
                                       'copy': restore_copy_name(target, qs.get('lang')) if exists else None,
                                       'can_replace': bool(exists and c and c[2] and App.store.has_blob(c[2])),
                                       'note': App.mon.notes.get(r['id']), 'ts': r['ts']})
            if route == '/api/backup':  # progress of a history backup
                return self.send_json(App.backup)
            if route == '/api/clean/history':  # does DeskTrace keep a copy of this file? (2.3.0, review P0-5)
                path = os.path.normpath(qs.get('path', ''))
                with App.mon.lock:
                    c = App.mon.confirmed.get(path)
                watched = any(under(path, r) for r in App.mon.settings['roots'])
                kept = bool(c and c[2] and App.store.has_blob(c[2]))
                versions = App.store.q("SELECT COUNT(*) n FROM events WHERE path = ? AND hash IS NOT NULL", (path,))[0]['n'] if watched else 0
                return self.send_json({'watched': watched, 'tracked': bool(c), 'kept': kept, 'versions': versions,
                                       'keep_days': App.mon.settings.get('keep_days') or 0,
                                       'too_big': bool(c and (c[0] or 0) > App.mon.settings['snapshot_max_mb'] * 2 ** 20)})
            if route == '/api/diagnostics':
                return self.send_json(self.diagnostics())
            if route == '/api/shell-menu':
                return self.send_json({'enabled': shell_menu_enabled(), 'supported': os.name == 'nt'})
            if route == '/api/stats':
                return self.send_json(self.stats())
            if route == '/api/settings':
                return self.send_json({**App.mon.settings, 'defaults': DEFAULTS, 'data_dir': str(DATA),
                                       'version': APP_VERSION, 'suggested': suggested_folders(App.mon.settings['roots'])})
            if route == '/api/content':
                res = App.store.content(qs.get('hash'), qs.get('ext', '')) if valid_hash(qs.get('hash')) else None
                return self.send_json({'ok': res is not None, 'content': strip_lines(res)})
            if route == '/api/compare':
                return self.send_json(self.compare(qs))
            if route == '/api/current':
                return self.send_json(self.current(qs['path']))
            if route == '/api/diff':
                return self.send_json(self.diff(int(qs['id']), min(max(int(qs.get('context', 3)), 0), 100000)))
            if route == '/api/export':
                return self.export(qs)
            if route == '/api/export-view':  # Duplicates or Space as an Excel list (2.0.1)
                return self.export_view(qs)
            if route == '/api/blob':
                h = qs.get('hash', '')
                if valid_hash(h) and App.store.has_blob(h):
                    return self.send_file(None, qs.get('name', 'file' + qs.get('ext', '')), data=App.store.read_blob(h))
                return self.send_json({'error': 'snapshot not available'}, 404)
            if route == '/api/file':
                p = qs.get('path', '')
                if self.allowed_path(p) and os.path.isfile(p):
                    return self.send_file(p, os.path.basename(p))
                return self.send_json({'error': 'not found'}, 404)
            return self.send_json({'error': 'not found'}, 404)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try:
                self.send_json({'error': f'{type(e).__name__}: {e}'}, 500)
            except OSError:
                pass

    def do_POST(self):
        if not self.host_ok() or self.headers.get('X-Token') != TOKEN:
            return self.send_json({'error': 'forbidden'}, 403)
        route = urllib.parse.urlparse(self.path).path
        try:
            b = self.body()
            if route == '/api/open':
                p = b['path']
                if not self.allowed_path(p) or not os.path.exists(p):
                    return self.send_json({'ok': False, 'code': 'gone'})
                os.startfile(p) if os.name == 'nt' else subprocess.Popen(['xdg-open', p])
                return self.send_json({'ok': True})
            if route == '/api/reveal':
                p = b['path']
                if not self.allowed_path(p):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if os.path.exists(p):
                    subprocess.Popen(f'explorer /select,"{p}"')
                else:
                    d = os.path.dirname(p)
                    while d and not os.path.isdir(d):
                        d = os.path.dirname(d)
                    if d:
                        os.startfile(d)
                return self.send_json({'ok': True})
            if route == '/api/restore':
                return self.send_json(self.restore(b))
            if route == '/api/restore-many':
                return self.send_json(self.restore_many(b))
            if route in ('/api/open-version', '/api/restore-as'):  # a snapshot: open it, or save it where the user says
                h, name = b.get('hash', ''), os.path.basename(str(b.get('name') or 'file'))
                if not (valid_hash(h) and App.store.has_blob(h)):
                    return self.send_json({'ok': False, 'code': 'noSnapshot'})
                stem, ext = os.path.splitext(name)
                label = time.strftime('%Y-%m-%d %H.%M', time.localtime(float(b.get('ts') or time.time())))
                if route == '/api/restore-as':
                    dest = pick_save(f'{stem} ({label}){ext}', b.get('dir') or '')
                    if not dest:
                        return self.send_json({'ok': False, 'cancelled': True})
                else:
                    folder = Path(os.environ.get('TEMP', str(DATA))) / 'DeskTrace versions'
                    folder.mkdir(parents=True, exist_ok=True)
                    dest = str(folder / f'{stem} ({label}){ext}')
                    if os.path.exists(dest):
                        os.chmod(dest, 0o666)
                App.store.copy_blob(h, dest)
                if route == '/api/open-version':
                    os.chmod(dest, 0o444)  # read-only: it is a look at the past, edits belong in the real file
                    os.startfile(dest) if os.name == 'nt' else subprocess.Popen(['xdg-open', dest])
                return self.send_json({'ok': True, 'path': dest})
            if route == '/api/export':  # the whole history as one file, for another PC (2.6.0 #44)
                dest = str(b.get('dest') or '') or pick_folder()
                if not dest or not os.path.isdir(dest) or under(os.path.normpath(dest), str(DATA)):
                    return self.send_json({'ok': False, 'code': 'notAllowed' if dest else 'cancelled'})
                if App.backup.get('state') == 'running':
                    return self.send_json({'ok': False, 'code': 'busy'})
                App.backup = {'state': 'running', 'started': time.time(), 'done': 0, 'total': 0, 'bytes': 0, 'dest': dest}
                threading.Thread(target=export_history, args=(dest,), daemon=True, name='export').start()
                return self.send_json({'ok': True})
            if route == '/api/import':  # a history from another PC: used from the next start (2.6.0 #44)
                src = str(b.get('path') or '') or pick_backup_file()
                if not src:
                    return self.send_json({'ok': False, 'code': 'cancelled'})
                return self.send_json(stage_import(src))
            if route == '/api/backup':  # back up the whole history into a folder the user picked (2.3.0)
                dest = str(b.get('dest') or '')
                if not os.path.isdir(dest) or under(dest, str(DATA)):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if App.backup.get('state') == 'running':
                    return self.send_json({'ok': True, 'running': True})
                App.backup = {'state': 'running', 'started': time.time(), 'done': 0, 'total': 0, 'bytes': 0, 'dest': dest}
                threading.Thread(target=backup_history, args=(dest, bool(b.get('raw'))), daemon=True, name='backup').start()
                return self.send_json({'ok': True})
            if route == '/api/clean/scan':  # start (or repeat) reading a drive (2.2.0)
                d = clean_drive(b.get('drive'))
                if not d:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                old = _scans.get(d)
                if old and old.state == 'scanning':
                    return self.send_json({'ok': True, 'drive': d})
                start_scan(d, b.get('mode'))  # the user waits: several folders at once, normal priority (2.4.0)
                return self.send_json({'ok': True, 'drive': d})
            if route == '/api/onboard':  # first-run guide finished or skipped (2.4.0 §7)
                App.mon.settings['onboarded'] = True
                save_settings(App.mon.settings)
                return self.send_json({'ok': True})
            if route == '/api/onboard/demo':  # the guide's own test file: made, deleted and cleaned up by DeskTrace
                roots = App.mon.settings['roots']
                if not roots:
                    return self.send_json({'ok': False, 'code': 'noRoots'})
                demo = os.path.join(roots[0], 'DeskTrace demo.txt' if b.get('lang') != 'zh' else '桌迹演示.txt')
                act = b.get('action')
                if act == 'create':
                    with open(demo, 'w', encoding='utf-8') as fh:
                        fh.write(('This is a test file made by DeskTrace\'s first-run guide. You can delete it.\n' if b.get('lang') != 'zh'
                                  else '这是桌迹入门向导创建的测试文件，可以删除。\n') * 3)
                elif act in ('delete', 'cleanup') and os.path.isfile(demo):
                    os.remove(demo)
                return self.send_json({'ok': True, 'path': demo})
            if route == '/api/clean/undo':  # put back what was just moved to the Recycle Bin (2.4.0 §4)
                paths = [os.path.normpath(str(x)) for x in (b.get('paths') or [])][:5000]
                r = cleaner.recycle_restore(paths, float(b.get('since') or 0))
                for d in {cleaner.drive_of(x) for x in r['restored']}:
                    find_cleanable(d)
                return self.send_json(r)
            if route == '/api/clean/app':  # open a chat app so its own storage cleanup can be used (2.4.0 §5)
                a = next((x for x in cleaner.chat_apps() if x['id'] == b.get('id')), None)
                if not a or not a['exe']:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                os.startfile(a['exe'])
                return self.send_json({'ok': True})
            if route == '/api/clean/hibernate':  # Windows asks the user (UAC); DeskTrace never elevates itself
                arg = '/h /type reduced' if b.get('reduced') else ('/h on' if b.get('on') else '/h off')  # 2.6.0 #17: reduced keeps fast startup
                subprocess.Popen(['powershell', '-NoProfile', '-WindowStyle', 'Hidden', '-Command',
                                  f"Start-Process powercfg -ArgumentList '{arg}' -Verb RunAs"], creationflags=NO_WINDOW)
                return self.send_json({'ok': True, 'asked': True})
            if route == '/api/clean/wintool':  # Windows' own tools (2.6.0 #25, #49): DeskTrace only opens them
                tool = {'optimize': ['dfrgui'], 'index': ['control', 'srchadmin.dll'], 'cleanmgr': ['cleanmgr']}.get(str(b.get('tool')))
                if not tool:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                subprocess.Popen(tool)
                return self.send_json({'ok': True})
            if route == '/api/clean/power':  # Power Options, to change it by hand
                subprocess.Popen(['control', 'powercfg.cpl'])
                return self.send_json({'ok': True})
            if route == '/api/clean/run':  # clean one place (temporary files, a browser cache, ...)
                d = clean_drive(b.get('drive'))
                if not d:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                r = cleaner.clean(d, str(b.get('id', '')), recycle)
                find_cleanable(d)
                note_last_clean(r.get('recycled') or [], r.get('freed') or 0)
                milestone('freed', r.get('freed') or 0)
                return self.send_json({'ok': 'code' not in r, **r})
            if route == '/api/clean/last-undo':  # put back the last cleanup, any time later (2.4.2: was a 10 s offer)
                last = App.store.meta('last_clean') or {}
                if not last.get('paths'):
                    return self.send_json({'ok': False, 'code': 'nothing'})
                r = cleaner.recycle_restore(last['paths'][:5000], float(last.get('since') or 0))
                left = [p for p in last['paths'] if p not in set(r['restored'])]
                App.store.set_meta('last_clean', {**last, 'paths': left} if left and len(left) < len(last['paths']) else None)
                for dr in {cleaner.drive_of(x) for x in r['restored']}:
                    find_cleanable(dr)
                return self.send_json(r)
            if route == '/api/mass-restore':  # put every file of a mass change back as it was before (2.6.0 #6)
                m = App.mon.mass or {}
                since, until = float(b.get('since') or m.get('since') or 0), float(b.get('until') or m.get('until') or 0) + 5
                rows = App.store.q('SELECT * FROM events WHERE ts >= ? AND ts <= ? ORDER BY id', (since, until))
                first = {}
                for r in rows:  # per file, its first change in the burst: what it was before
                    first.setdefault(r['old_path'] if r['kind'] == 'renamed' else r['path'], r)
                done = failed = 0
                renames = [r['id'] for r in first.values() if r['kind'] == 'renamed']
                for r in first.values():
                    if r['kind'] == 'created':
                        continue  # a new file (a ransom note, a copy): left for the user to judge
                    if r['kind'] == 'renamed':
                        continue
                    try:
                        res = self.restore({'id': r['id'], 'version': 'prev', 'replace': r['kind'] == 'modified' and os.path.isfile(r['path']),
                                            'lang': b.get('lang')})
                    except OSError:
                        res = {'ok': False}
                    done, failed = (done + 1, failed) if res.get('ok') else (done, failed + 1)
                if renames:
                    rb = self.rename_back(renames)
                    done, failed = done + rb['done'], failed + len(rb['skipped'])
                App.mon.mass, App.mon._burst = None, []
                App.mon.mass_quiet = time.time() + 60  # our own restore is not a new mass change
                App.mon.wake.set()
                return self.send_json({'ok': True, 'restored': done, 'failed': failed})
            if route == '/api/mass-dismiss':
                App.mon.mass, App.mon._burst = None, []
                App.mon.mass_quiet = time.time() + 600  # "that was me": no new alert for 10 minutes (Gemini 2.6.0 Q-1)
                return self.send_json({'ok': True})
            if route == '/api/folder-at':  # a folder as it was at a time, as a copy (2.6.0 #31)
                return self.send_json(self.folder_at(str(b.get('folder', '')), float(b.get('ts') or 0), b.get('lang')))
            if route == '/api/diff-report':  # one change as an HTML report the user saves (2.6.0 #26)
                ev = App.mon.event_dict(int(b['id']))
                d = self.diff(int(b['id']), 3)
                if not d.get('hunks'):
                    return self.send_json({'ok': False, 'code': 'noDiff'})
                dest = str(b.get('dest') or '') or pick_save(os.path.splitext(ev['name'])[0] + ' — ' + ('修改对比' if b.get('lang') == 'zh' else 'changes') + '.html')
                if not dest:
                    return self.send_json({'ok': False, 'code': 'cancelled'})
                Path(dest).write_text(diff_report_html(ev, d, b.get('lang') or 'en'), 'utf-8')
                return self.send_json({'ok': True, 'path': dest})
            if route == '/api/dup-link':  # identical copies share one file on disk (2.6.0 #13)
                paths = [os.path.normpath(str(x)) for x in (b.get('paths') or [])][:500]
                if len(paths) < 2 or not all(self.allowed_path(p) and os.path.isfile(p) for p in paths):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                keep, freed, done, skipped = paths[0], 0, 0, []
                drive = cleaner.drive_of(keep)
                fs = ctypes_fs_name(drive)
                if fs != 'NTFS':
                    return self.send_json({'ok': False, 'code': 'notNtfs'})
                with open(keep, 'rb') as fh:
                    want = hashlib.sha256(fh.read()).hexdigest()
                for p in paths[1:]:
                    try:
                        if cleaner.drive_of(p) != drive:
                            skipped.append({'path': p, 'code': 'otherDrive'})
                            continue
                        with open(p, 'rb') as fh:
                            if hashlib.sha256(fh.read()).hexdigest() != want:
                                skipped.append({'path': p, 'code': 'changed'})  # not identical (any more)
                                continue
                        if os.path.samefile(p, keep):
                            continue
                        size = os.path.getsize(p)
                        tmp = p + '.dt-link.tmp'
                        os.link(keep, tmp)
                        try:
                            os.replace(tmp, p)
                        except OSError:
                            os.remove(tmp)
                            raise
                        freed, done = freed + size, done + 1
                    except OSError:
                        skipped.append({'path': p, 'code': 'inUse', 'by': cleaner.lockers(p)})
                return self.send_json({'ok': True, 'linked': done, 'freed': freed, 'skipped': skipped})
            if route == '/api/relocate':  # move a big folder to another drive, verified, junction left (2.6.0 #3)
                src = os.path.normpath(str(b.get('path', '')))
                drive = str(b.get('drive', ''))[:2].upper() + '\\'
                if App.move.get('state') == 'running':
                    return self.send_json({'ok': False, 'code': 'busy'})
                roots = App.mon.settings['roots']
                if (not os.path.isdir(src) or cleaner.is_core(src) or len(src) <= 3 or getattr(os.path, 'isjunction', lambda _: False)(src)
                        or under(src, str(DATA)) or under(str(DATA), src) or any(under(r, src) or under(src, r) for r in roots)
                        or cleaner.drive_of(src) == drive or not os.path.isdir(drive) or ctypes_fs_name(drive) != 'NTFS'):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                dest = str(b.get('dest') or '') or os.path.join(drive, 'DeskTrace moved', src[3:])
                need = cleaner._tree_size(src)
                if shutil.disk_usage(drive).free < need * 1.1 + 2 ** 30:
                    return self.send_json({'ok': False, 'code': 'noSpace'})
                App.move = {'state': 'running', 'src': src, 'dest': dest, 'size': need, 'step': 'start', 'done': 0, 'total': 0}

                def go():
                    r = cleaner.move_folder(src, dest, progress=lambda **k: App.move.update(k))
                    if r.get('ok'):
                        moves = App.store.meta('moves', [])
                        App.store.set_meta('moves', moves + [{'src': src, 'dest': dest, 'size': need, 'at': time.time()}])
                    App.move.update(state='done' if r.get('ok') else 'failed', result=r)
                threading.Thread(target=go, daemon=True, name='relocate').start()
                return self.send_json({'ok': True})
            if route == '/api/relocate-back':  # bring a moved folder back (2.6.0 #3)
                src = os.path.normpath(str(b.get('path', '')))
                m = next((x for x in App.store.meta('moves', []) if x['src'] == src), None)
                if not m or App.move.get('state') == 'running':
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                App.move = {'state': 'running', 'src': src, 'dest': m['dest'], 'size': m['size'], 'step': 'start', 'done': 0, 'total': 0}

                def back():
                    r = cleaner.move_back(src, m['dest'], progress=lambda **k: App.move.update(k))
                    if r.get('ok'):
                        App.store.set_meta('moves', [x for x in App.store.meta('moves', []) if x['src'] != src])
                    App.move.update(state='done' if r.get('ok') else 'failed', result=r)
                threading.Thread(target=back, daemon=True, name='relocate-back').start()
                return self.send_json({'ok': True})
            if route == '/api/draft-save':  # a copy of a draft, in Documents\DeskTrace recovered (2.6.0 #24)
                p = os.path.normpath(str(b.get('path', '')))
                if not any(x['path'] == p for x in getattr(App, 'drafts', [])):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                folder = Path(os.environ.get('USERPROFILE', str(DATA))) / 'Documents' / 'DeskTrace recovered'
                folder.mkdir(parents=True, exist_ok=True)
                stem, ext = os.path.splitext(os.path.basename(p))
                dest, n = folder / (stem + ext), 2
                while dest.exists():
                    dest, n = folder / f'{stem} ({n}){ext}', n + 1
                shutil.copy2(p, dest)
                return self.send_json({'ok': True, 'path': str(dest)})
            if route == '/api/chat-media-clean':  # chosen kinds of old received media to the Recycle Bin (2.6.0 #7)
                a = next((x for x in cleaner.chat_apps() if x['app'] == b.get('app')), None)
                kinds = [k for k in (b.get('kinds') or []) if k in ('picture', 'video', 'file', 'cache')]
                if not a or not kinds:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                m = cleaner.chat_media(a['data'], max(7, int(b.get('days', 90))))
                todo = [x for k in kinds for x in m[k]]
                moved = set(recycle_many([p for p, _ in todo]))
                freed = sum(size for p, size in todo if p in moved)
                note_last_clean(sorted(moved)[:5000], freed)
                milestone('freed', freed)
                return self.send_json({'ok': True, 'moved': len(moved), 'freed': freed, 'left': len(todo) - len(moved)})
            if route == '/api/clean/fix-name':  # rename one of them so Windows can handle it (2.6.0 #35)
                p = str(b.get('path', ''))
                if not any(x['path'] == p for x in getattr(App, 'badnames', [])):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                r = cleaner.fix_name(p)
                if r.get('ok'):
                    App.badnames = [x for x in App.badnames if x['path'] != p]
                return self.send_json(r)
            if route == '/api/clean/cloud-free':  # every file of a synced folder online only (2.6.0 #30)
                return self.send_json(cleaner.free_cloud_folder(str(b.get('path', ''))))
            if route == '/api/rename-back':  # undo a group of renames or moves (2.6.0 #40)
                return self.send_json(self.rename_back(b.get('ids') or []))
            if route == '/api/root-gone':  # a monitored folder that is away was really deleted (2.4.2)
                root = os.path.normpath(str(b.get('root', '')))
                n = App.mon.forget_root_files(root)
                rest = [r for r in App.mon.settings['roots'] if r != root]
                if rest and root in App.mon.settings['roots'] and not App.mon.root_available(root):
                    self.update_settings({'roots': rest, 'drop_root': root})
                return self.send_json({'ok': True, 'deleted': n})
            if route == '/api/clean/git-gc':  # Git's own clean-up of one repository, on request (2.6.0 #29)
                path = os.path.normpath(str(b.get('path', '')))
                if not any(x['path'] == path for x in getattr(App, 'git_repos', [])) or not shutil.which('git'):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                before = cleaner._tree_size(os.path.join(path, '.git'))
                r = subprocess.run(['git', '-C', path, 'gc', '--prune=now', '--quiet'], capture_output=True, timeout=1800,
                                   creationflags=NO_WINDOW)
                after = cleaner._tree_size(os.path.join(path, '.git'))
                return self.send_json({'ok': r.returncode == 0, 'freed': max(0, before - after), 'size': after,
                                       'code': None if r.returncode == 0 else 'gitFailed'})
            if route == '/api/clean/leftover-delete':  # one leftover folder, to the Recycle Bin (2.6.0 #2)
                path = os.path.normpath(str(b.get('path', '')))
                if not any(x['path'] == path for x in getattr(App, 'leftovers', [])) or cleaner.is_core(path):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if not recycle(path):
                    return self.send_json({'ok': False, 'code': 'inUse'})
                note_last_clean([path], next(x['size'] for x in App.leftovers if x['path'] == path))
                App.leftovers = [x for x in App.leftovers if x['path'] != path]
                return self.send_json({'ok': True})
            if route == '/api/clean/delete':  # one file of the biggest-files list, to the Recycle Bin
                path = os.path.normpath(str(b.get('path', '')))
                if is_pinned(path):
                    return self.send_json({'ok': False, 'code': 'pinned'})  # kept forever (2.6.0 #20)
                sc = _scans.get(cleaner.drive_of(path))
                r = cleaner.delete_file(path, sc, recycle, permanent=bool(b.get('permanent')))
                if r.get('ok'):
                    find_cleanable(cleaner.drive_of(path))  # the Recycle Bin grew
                    if r.get('recycled'):
                        note_last_clean([path], r.get('size') or 0)
                return self.send_json(r)
            if route == '/api/clean/online':  # a synced file: free its local copy, it stays in the cloud
                return self.send_json(cleaner.keep_online_only(os.path.normpath(str(b.get('path', '')))))
            if route == '/api/clean/stop':  # stop reading a drive
                sc = _scans.get(clean_drive(b.get('drive')))
                if sc:
                    sc.stop = True
                return self.send_json({'ok': True})
            if route == '/api/clean/reveal':  # show a file or folder the scan listed in Explorer
                path = os.path.normpath(str(b.get('path', '')))
                if not os.path.exists(path):
                    return self.send_json({'ok': False, 'code': 'gone'})
                subprocess.Popen(['explorer', '/select,', path] if os.path.isfile(path) else ['explorer', path])
                return self.send_json({'ok': True})
            if route == '/api/clean/bin':  # the Recycle Bin, to look at or restore from
                subprocess.Popen(['explorer', 'shell:RecycleBinFolder'])
                return self.send_json({'ok': True})
            if route == '/api/clean/apps':  # Settings › Apps, to uninstall a program instead of deleting its files
                os.startfile('ms-settings:appsfeatures') if os.name == 'nt' else None
                return self.send_json({'ok': True})
            if route == '/api/clean/windows':  # Windows' own Disk Cleanup, for what needs administrator rights
                d = clean_drive(b.get('drive'))
                if not d:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                subprocess.Popen(['cleanmgr', '/d', d[:2]])
                return self.send_json({'ok': True})
            if route == '/api/recycle':  # Duplicates: move one extra copy to the Recycle Bin
                p = os.path.normpath(str(b.get('path', '')))
                with App.mon.lock:
                    c = App.mon.confirmed.get(p)
                    k = content_key(p, c) if c else None
                    twins = [q for q, d in App.mon.confirmed.items() if q != p and d[0] == c[0] and same_content(content_key(q, d), k)] if k else []
                if not c or not any(under(p, r) for r in App.mon.settings['roots']):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if not any(os.path.isfile(q) for q in twins):
                    return self.send_json({'ok': False, 'code': 'lastCopy'})  # never remove the last copy
                if not os.path.exists(p):
                    return self.send_json({'ok': False, 'code': 'gone'})
                problem = cleaner.recycle_problem(p)
                return self.send_json({'ok': False, 'code': problem} if problem else {'ok': recycle(p)})
            if route == '/api/hide':  # "Not duplicates": add or remove one set (2.1.0)
                key, item = b.get('list'), str(b.get('item', ''))
                if key != 'dup_hidden' or not item:
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                cur = [x for x in App.mon.settings.get(key) or [] if x != item]
                if b.get('on', True):
                    cur.append(item)
                App.mon.settings[key] = cur[-1000:] if not b.get('clear') else []
                App.mon.gen += 1
                save_settings(App.mon.settings)
                return self.send_json({'ok': True, 'count': len(App.mon.settings[key])})
            if route == '/api/forget':  # forget a file's old versions: keep the newest and noted ones (2.1.0)
                p = str(b.get('path', ''))
                if is_pinned(p):
                    return self.send_json({'ok': False, 'code': 'pinned'})
                rows = App.store.q('SELECT id FROM events WHERE path=? OR old_path=? ORDER BY id DESC', (p, p))
                keep = {rows[0]['id']} if rows else set()
                gone = [r['id'] for r in rows if r['id'] not in keep and r['id'] not in App.mon.notes]
                for i in range(0, len(gone), 500):
                    chunk = gone[i:i + 500]
                    App.store.x(f"DELETE FROM events WHERE id IN ({','.join('?' * len(chunk))})", chunk)
                App.mon.gen += 1
                res = App.mon.cleanup()
                return self.send_json({'ok': True, 'forgotten': len(gone), 'freed': res.get('freed', 0)})
            if route == '/api/cleanup':  # Settings → Clean up now
                return self.send_json({'ok': True, **App.mon.cleanup()})
            if route == '/api/pause':
                set_pause(bool(b.get('paused')), float(b.get('minutes') or 0))
                return self.send_json({'ok': True, 'paused': App.mon.paused, 'pause_until': App.mon.pause_until})
            if route == '/api/mute':
                set_mute(float(b.get('minutes') or 0), b.get('until'))
                return self.send_json({'ok': True, 'mute_until': App.mon.settings.get('mute_until', 0)})
            if route == '/api/note':
                eid, text = int(b['id']), str(b.get('text') or '').strip()[:500]
                if text:
                    App.store.x('INSERT OR REPLACE INTO notes(event_id, text, ts) VALUES(?,?,?)', (eid, text, time.time()))
                    App.mon.notes[eid] = text
                else:
                    App.store.x('DELETE FROM notes WHERE event_id=?', (eid,))
                    App.mon.notes.pop(eid, None)
                App.hub.publish({'type': 'update', 'event': App.mon.event_dict(eid)})
                return self.send_json({'ok': True, 'note': text})
            if route == '/api/ignore-folder':
                p = os.path.normpath(b.get('path', ''))
                if not any(under(p, r) for r in App.mon.settings['roots']):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                paths = list(App.mon.settings.get('exclude_paths', []))
                if p not in paths:
                    paths.append(p)
                return self.send_json(self.update_settings({'exclude_paths': paths}))
            if route == '/api/shell-menu':
                return self.send_json({'ok': True, 'enabled': set_shell_menu(bool(b.get('enabled')))})
            if route == '/api/settings':
                return self.send_json(self.update_settings(b))
            if route == '/api/pick-folder':
                return self.send_json({'path': pick_folder()})
            if route == '/api/pin':  # keep forever (2.6.0 #20)
                p, on = os.path.normpath(str(b.get('path', ''))), bool(b.get('on'))
                if not self.allowed_path(p):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                App.store.x('INSERT OR IGNORE INTO pins(path) VALUES(?)' if on else 'DELETE FROM pins WHERE path=?', (p,))
                _pins['at'] = 0
                return self.send_json({'ok': True, 'pinned': on})
            if route == '/api/star':
                p, on = b['path'], bool(b.get('on'))
                if not self.allowed_path(p):
                    return self.send_json({'ok': False, 'code': 'notAllowed'})
                if on:
                    App.store.x('INSERT OR IGNORE INTO stars(path) VALUES(?)', (p,))
                    App.mon.stars = App.mon.stars | {p}
                else:
                    App.store.x('DELETE FROM stars WHERE path=?', (p,))
                    App.mon.stars = App.mon.stars - {p}
                return self.send_json({'ok': True, 'starred': on})
            if route in ('/api/open-data', '/api/open-log'):
                target = DATA if route == '/api/open-data' else DATA / 'desktop_watch.log'
                if not target.exists():
                    return self.send_json({'ok': False, 'code': 'gone'})
                os.startfile(str(target)) if os.name == 'nt' else subprocess.Popen(['xdg-open', str(target)])
                return self.send_json({'ok': True})
            if route == '/api/autostart':
                return self.send_json({'ok': True, 'enabled': set_autostart(bool(b.get('enabled')))})
            if route == '/api/quit':
                self.send_json({'ok': True})
                threading.Thread(target=App.server.shutdown, daemon=True).start()
                return
            if route == '/api/update/apply':  # install the version license found earlier, then restart
                try:
                    v = App.updates.apply(os.getpid(), open_window=True, version=b.get('version'))
                except updmod.LicenseError as e:
                    return self.send_json({'ok': False, 'code': e.code})
                self.send_json({'ok': True, 'version': v})
                threading.Thread(target=App.server.shutdown, daemon=True).start()
                return
            if route == '/api/update/seen':
                App.updates.seen_result()
                return self.send_json({'ok': True})
            if route == '/api/update/check':  # a license file picked by hand (Settings → Updates)
                p = pick_license() if b.get('pick') else b.get('path', '')
                ok = App.updates.consider(p) if p.lower().endswith(updmod.EXT) else False
                return self.send_json({'ok': ok, 'picked': p, 'update': App.updates.status(b.get('lang') or ui_lang()),
                                       'reason': App.updates.rejected.get(p)})
            if route == '/api/clear':
                App.store.x('DELETE FROM events')
                App.diff_cache.clear()
                # keep snapshots still referenced as the current version of a tracked file
                keep = {r['hash'] for r in App.store.q('SELECT hash FROM files WHERE hash IS NOT NULL')}
                for sub in BLOBS.glob('*/*'):
                    if sub.name not in keep:
                        try:
                            sub.unlink()
                        except OSError:
                            pass
                App.store.x('DELETE FROM contents WHERE hash NOT IN (SELECT hash FROM files WHERE hash IS NOT NULL)')
                App.storage['at'] = 0
                App.hub.publish({'type': 'cleared'})
                return self.send_json({'ok': True})
            return self.send_json({'error': 'not found'}, 404)
        except Exception as e:
            return self.send_json({'ok': False, 'error': f'{type(e).__name__}: {e}'}, 500)

    # -- handlers -----------------------------------------------------------------
    def stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()
        q = App.hub.subscribe()
        try:
            self.wfile.write(f'data: {json.dumps({"type": "status", "status": App.mon.status()})}\n\n'.encode())
            self.wfile.flush()
            while True:
                try:
                    msg = q.get(timeout=15)
                    self.wfile.write(f'data: {msg}\n\n'.encode('utf-8'))
                except queue.Empty:
                    self.wfile.write(b': ping\n\n')
                self.wfile.flush()
        except OSError:
            pass
        finally:
            App.hub.unsubscribe(q)
            self.close_connection = True

    @staticmethod
    def event_filter(qs):
        """SQL conditions for the change-list filters (shared by the list and the Excel export)."""
        where, args = [], []
        if qs.get('kinds'):
            ks = qs['kinds'].split(',')
            where.append(f'kind IN ({",".join("?" * len(ks))})')
            args += ks
        if qs.get('cats'):
            cs = qs['cats'].split(',')
            where.append(f'cat IN ({",".join("?" * len(cs))})')
            args += cs
        if qs.get('q'):  # the name or path, or a note on the version
            where.append('(path LIKE ? OR old_path LIKE ? OR id IN (SELECT event_id FROM notes WHERE text LIKE ?))')
            args += [f'%{qs["q"]}%'] * 3
        if qs.get('before'):
            where.append('id < ?')
            args.append(int(qs['before']))
        if qs.get('since'):
            where.append('ts >= ?')
            args.append(float(qs['since']))
        if qs.get('until'):  # one day picked in the statistics
            where.append('ts < ?')
            args.append(float(qs['until']))
        if qs.get('gone'):  # deleted and still missing: the last thing that happened to the path (2.4.2)
            where.append("kind = 'deleted' AND prev_hash IS NOT NULL AND path NOT IN (SELECT path FROM files)"
                         ' AND id = (SELECT MAX(e2.id) FROM events e2 WHERE e2.path = events.path)')
        if qs.get('noted'):  # only versions with a note
            where.append('id IN (SELECT event_id FROM notes)')
        if qs.get('starred'):
            where.append('path IN (SELECT path FROM stars)')
        if qs.get('folder'):  # one folder and everything in it (2.1.0); as a range, so the path index is used
            lo = qs['folder'].rstrip('\\/') + os.sep
            hi = lo[:-1] + chr(ord(os.sep) + 1)
            where.append('((path >= ? AND path < ?) OR (old_path >= ? AND old_path < ?))')
            args += [lo, hi, lo, hi]
        return where, args

    def events(self, qs):
        where, args = self.event_filter(qs)
        sql = 'SELECT * FROM events' + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY id DESC LIMIT ?'
        limit = min(int(qs.get('limit', 150)), 500)
        rows = App.store.q(sql, args + [limit])
        return {'events': [App.mon.event_dict(row=r) for r in rows], 'more': len(rows) == limit}

    def stats(self):
        st = App.store
        day0 = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
        kinds_today = {r['kind']: r['n'] for r in st.q('SELECT kind, COUNT(*) n FROM events WHERE ts>=? GROUP BY kind', (day0,))}
        kinds_all, cats, _ = event_totals()
        bucket = 300
        now = time.time()
        start = (int(now) // bucket - 23) * bucket
        act = {r['b']: dict(n=r['n'], c=r['c'], m=r['m'], d=r['d'], r=r['r']) for r in st.q(
            "SELECT CAST(ts/? AS INTEGER)*? b, COUNT(*) n, SUM(kind='created') c, SUM(kind='modified') m,"
            " SUM(kind='deleted') d, SUM(kind='renamed') r FROM events WHERE ts>=? GROUP BY b",
            (bucket, bucket, start))}
        activity = [{'t': start + i * bucket, **act.get(start + i * bucket, dict(n=0, c=0, m=0, d=0, r=0))}
                    for i in range(24)]
        if now - App.storage['at'] > 30:
            App.storage.update(bytes=dir_size(DATA), at=now)
        tracked_cats = {}
        with App.mon.lock:
            for p in App.mon.confirmed:
                c = category_of(os.path.splitext(p)[1])
                tracked_cats[c] = tracked_cats.get(c, 0) + 1
        return {'today': kinds_today, 'all': kinds_all, 'cats': cats, 'tracked_cats': tracked_cats,
                'activity': activity, 'bucket': bucket, 'storage': App.storage['bytes'],
                'storage_cap_gb': App.mon.settings.get('max_storage_gb') or 0, 'status': App.mon.status(),
                'notes': len(App.mon.notes)}

    def files(self, qs):
        """Every tracked file (not only changed ones), for the Files browser."""
        q = qs.get('q', '').lower()
        cats = set(qs['cats'].split(',')) if qs.get('cats') else None
        with App.mon.lock:
            items = [(p, c[0], c[1], c[2]) for p, c in App.mon.confirmed.items()]
        counts = change_counts()
        stars = App.mon.stars
        only_starred = bool(qs.get('starred'))
        only_changed = bool(qs.get('changed'))  # files that have a history of changes (2.0.1)
        rows = []
        for p, size, mtime, h in items:
            ext = os.path.splitext(p)[1].lower()
            cat = category_of(ext)
            if (cats and cat not in cats) or (q and q not in p.lower()) or (only_starred and p not in stars) \
                    or (only_changed and not counts.get(p)):
                continue
            rows.append((p, size, mtime, h, ext, cat))
        if qs.get('sort') == 'name':
            rows.sort(key=lambda r: os.path.basename(r[0]).lower())
        elif qs.get('sort') == 'size':
            rows.sort(key=lambda r: -r[1])
        elif qs.get('sort') == 'changes':
            rows.sort(key=lambda r: (-counts.get(r[0], 0), -r[2]))
        else:
            rows.sort(key=lambda r: -r[2])
        offset, limit = int(qs.get('offset', 0)), min(int(qs.get('limit', 200)), 500)
        out = [file_row(p, size, mtime, h, counts.get(p, 0)) for p, size, mtime, h, ext, cat in rows[offset:offset + limit]]
        return {'files': out, 'total': len(rows)}

    def compare(self, qs):
        """Diff any two versions of a file: snapshot hashes, or 'current' for the file on disk now."""
        ext = qs.get('ext', '')

        def text_of(v):
            if v == 'current':
                p = qs.get('path', '')
                if (not self.allowed_path(p) or not os.path.isfile(p) or os.path.getsize(p) > 200 * 1024 * 1024
                        or cleaner.online_only(p)):
                    return None
                with open(p, 'rb') as fh:
                    return extract(fh.read(), ext or os.path.splitext(p)[1])
            return App.store.content(v, ext) if valid_hash(v) else None

        a, b = text_of(qs.get('a')), text_of(qs.get('b'))
        if a is None or b is None:
            return {'ok': False}
        context = min(max(int(qs.get('context', 3)), 0), 100000)
        return {'ok': True, 'type': b.get('type') or a.get('type'),
                **build_diff(a.get('lines') or [], b.get('lines') or [], context=context,
                             max_lines=20000 if context > 50 else 6000)}

    def file_info(self, p):
        """One tracked file as the Files view shows it (used by links that open a file directly)."""
        with App.mon.lock:
            c = App.mon.confirmed.get(p)
            if c is None:  # Explorer may spell the path with different capitals
                n = os.path.normcase(os.path.normpath(p))
                p = next((k for k in App.mon.confirmed if os.path.normcase(k) == n), p)
                c = App.mon.confirmed.get(p)
        if c is None:
            return {'ok': False, 'tracked': False, 'exists': os.path.isfile(p), 'path': p}
        return {'ok': True, **file_row(p, c[0], c[1], c[2], change_counts().get(p, 0))}

    def space(self, folder=''):
        """What takes up room in the monitored folders (or inside one ``folder`` of them, 2.0.1): biggest
        files and folders, size by type, and how much they grew in the last 30 days (1.8.0)."""
        with App.mon.lock:
            items = [(p, c[0] or 0, c[1]) for p, c in App.mon.confirmed.items() if not folder or under(p, folder)]
        # one pass over the files (2.1.0: each file's type was worked out once per type list, and every
        # parent folder was checked against its root again — together most of the time this view took)
        folders, cats, roots, by_cat = {}, {}, {}, {}
        for item in items:
            p, size = item[0], item[1]
            cat = category_of(os.path.splitext(p)[1].lower())
            cats[cat] = cats.get(cat, 0) + size
            by_cat.setdefault(cat, []).append(item)
            root = App.mon.root_of(p)
            if not root:
                continue
            r = roots.setdefault(root, [0, 0])
            r[0], r[1] = r[0] + size, r[1] + 1
            top = len(root.rstrip(os.sep))
            d = os.path.dirname(p)
            while len(d) > top:  # every parent folder up to the root (p is inside root)
                folders[d] = folders.get(d, 0) + size
                d = os.path.dirname(d)
        since = time.time() - 30 * 86400
        g = App.store.q("SELECT SUM(CASE kind WHEN 'created' THEN COALESCE(size,0) WHEN 'deleted' THEN -COALESCE(old_size,0)"
                        " WHEN 'modified' THEN COALESCE(size,0) - COALESCE(old_size,0) ELSE 0 END) g FROM events WHERE ts >= ?"
                        + (' AND path LIKE ?' if folder else ''), (since, folder.rstrip(os.sep) + os.sep + '%') if folder else (since,))[0]['g']

        year_ago = time.time() - 365 * 86400
        stale = [i for i in items if i[2] and (i[2] / 1e9 if i[2] > 1e12 else i[2]) < year_ago]

        def size_of(item):
            return item[1]

        def row(p, size, mtime=None):
            ext = os.path.splitext(p)[1].lower()
            return {'path': p, 'name': os.path.basename(p), 'dir': os.path.dirname(p), 'size': size, 'ext': ext,
                    'cat': category_of(ext), 'root': App.mon.root_of(p), 'mtime': (mtime / 1e9 if mtime and mtime > 1e12 else mtime)}
        return {'total': sum(s for _, s, _ in items), 'files': len(items), 'growth': g or 0,
                'roots': [{'path': r, 'size': v[0], 'files': v[1]} for r, v in roots.items()],
                'cats': sorted(([c, s] for c, s in cats.items() if s), key=lambda x: -x[1]),
                'folders': [row(d, s) for d, s in top_folders({d: s for d, s in folders.items()
                                                              if not folder or (under(d, folder) and os.path.normcase(d) != os.path.normcase(folder))}, 12)],
                'folder': folder,
                'big': [row(p, s, m) for p, s, m in heapq.nlargest(60, items, key=size_of)],
                # biggest files not changed for over a year: clean-up candidates (2.0.1)
                'stale': [row(p, s, m) for p, s, m in heapq.nlargest(60, stale, key=size_of)],
                'stale_total': sum(s for _, s, _ in stale),
                'stale_files': len(stale),
                'big_by_cat': {c: [row(p, s, m) for p, s, m in heapq.nlargest(40, by_cat[c], key=size_of)] for c in cats}}

    def duplicates(self):
        """Identical files (same content hash) in the monitored folders, biggest waste first (1.7.0)."""
        noise = {'desktop.ini', 'thumbs.db', '.ds_store', 'icon\r'}  # system files every folder has (2.0.1)
        with App.mon.lock:
            files = [(p, c[0] or 0, c[1], content_key(p, c)) for p, c in App.mon.confirmed.items()
                     if (c[0] or 0) >= 1024 and os.path.basename(p).lower() not in noise]
        kinds = {}  # sizes where versions named before and after 2.4.2 meet: compare them by one name
        for p, size, mtime, h in files:
            if h and h[0] != 'L':
                kinds.setdefault(size, set()).add(len(h))
        files = [(p, size, mtime, App.store.sha256_of(h) if h and len(h) == 40 and len(kinds.get(size, ())) > 1 else h)
                 for p, size, mtime, h in files]
        # large files have no snapshot hash: those sharing a size get hashed in the background (2.0.1)
        by_size = {}
        for p, size, mtime, h in files:
            if not h:
                by_size.setdefault(size, []).append((p, size, mtime))
        todo = [f for fs in by_size.values() if len(fs) > 1 for f in fs if (f[0], f[1], f[2]) not in _big_hash]
        if todo and not _big_busy.is_set():
            _big_busy.set()
            threading.Thread(target=hash_large, args=(todo,), daemon=True, name='dup-hash').start()
        items = [f for f in files if f[3]]
        groups = {}
        for p, size, mtime, h in items:
            groups.setdefault(h, []).append((p, size, mtime))
        out = []
        for h, fs in groups.items():
            if len(fs) < 2:  # a file with no twin needs no look on disk (2.1.0: was most of the time spent here)
                continue
            fs = [f for f in fs if os.path.isfile(f[0])]
            if len(fs) < 2:
                continue
            fs.sort(key=lambda f: -f[2])  # newest first
            size = fs[0][1]
            ext = os.path.splitext(fs[0][0])[1].lower()
            out.append({'hash': h, 'size': size, 'count': len(fs), 'wasted': size * (len(fs) - 1),
                        'name': os.path.basename(fs[0][0]), 'ext': ext, 'cat': category_of(ext),
                        'files': [{'path': p, 'name': os.path.basename(p), 'dir': os.path.dirname(p), 'mtime': m / 1e9 if m > 1e12 else m,
                                   'root': App.mon.root_of(p)} for p, _, m in fs]})
        hidden = set(App.mon.settings.get('dup_hidden') or [])  # "Not duplicates" (2.1.0)
        n_hidden = sum(1 for g in out if g['hash'] in hidden)
        out = [g for g in out if g['hash'] not in hidden]
        out.sort(key=lambda g: (-g['wasted'], g['name'].lower()))
        limit = float(App.mon.settings.get('snapshot_max_mb') or 0)
        return {'groups': out, 'wasted': sum(g['wasted'] for g in out), 'files': sum(g['count'] for g in out),
                'checked': len(items), 'limit_mb': limit, 'checking': len(todo), 'hidden': n_hidden}

    def diagnostics(self):
        """What the app is doing right now — for the Diagnostics section in Settings."""
        mon, st = App.mon, App.store
        errors = []
        try:
            lines = (DATA / 'desktop_watch.log').read_text('utf-8', 'replace').splitlines()
            errors = [ln for ln in lines if re.search(r'error|traceback', ln, re.I)][-8:]
        except OSError:
            pass
        use = process_use()
        return {'version': APP_VERSION, 'python': sys.version.split()[0], 'pid': os.getpid(), 'port': App.port,
                'cpu_s': use.get('cpu_s'), 'memory_mb': use.get('memory_mb'), 'io_mb': use.get('io_mb'),
                'next_full_s': max(0, round(mon.last_full + mon.full_interval() - time.time())) if mon.last_full else None,
                'on_battery': on_battery(), 'busy': user_busy_fullscreen(), 'disk_low': disk_low(), 'disk_free': _disk['free'],
                'uptime': time.time() - mon.started, 'instant': mon.instant,
                'watchers': [{'root': r, 'alive': w.alive} for r, w in mon.watchers.items()],
                'files': mon.stats.get('files'), 'scans': mon.stats.get('scans'),
                'full_ms': mon.stats.get('scan_ms'), 'partial_ms': mon.stats.get('partial_ms'),
                'baseline_pending': mon.stats.get('baseline_total'),
                'events': st.q('SELECT COUNT(*) n FROM events')[0]['n'], 'notes': len(mon.notes), 'stars': len(mon.stars),
                'indexed': st.q('SELECT COUNT(*) n FROM ftsdoc')[0]['n'] if st.fts else None,
                'db_bytes': sum(f.stat().st_size for f in DATA.glob('watch.db*')),
                'snapshots': sum(1 for _ in iter_blobs()), 'errors': errors, 'integrity': App.integrity, 'warn': mon.warnings(),
                'blobs_bad': len(App.store.meta('blobs_bad', [])), 'verify_last': App.store.meta('verify_last', 0),
                'snap_format': SNAP_FORMAT}

    def export(self, qs):
        """The (filtered) change history as an Excel workbook, in the UI language."""
        lang = qs.get('lang') if qs.get('lang') in TEXT else ui_lang()
        T = TEXT[lang]
        where, args = self.event_filter(qs)
        rows = App.store.q('SELECT * FROM events' + (' WHERE ' + ' AND '.join(where) if where else '')
                           + ' ORDER BY id DESC LIMIT 100000', args)
        table = [[dt.datetime.fromtimestamp(r['ts']), T[r['kind']], os.path.basename(r['path']), os.path.dirname(r['path']),
                  r['path'], r['old_path'] or '', r['old_size'], None if r['kind'] == 'deleted' else r['size'],
                  r['added'], r['removed'], summary_text(r, lang), App.mon.notes.get(r['id'], '')] for r in rows]
        cols = ('x_time', 'x_change', 'x_file', 'x_folder', 'x_path', 'x_old', 'x_before', 'x_after', 'x_added', 'x_removed', 'x_summary', 'x_note')
        data = xlsx.write_xlsx([T[c] for c in cols], table, widths=[20, 10, 34, 44, 64, 40, 15, 15, 9, 9, 30, 36], sheet=T['x_sheet'])
        name = f"{T['app']} {T['x_sheet']} {time.strftime('%Y-%m-%d')}.xlsx"
        self.send_bytes(data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        {'Content-Disposition': "attachment; filename*=UTF-8''" + urllib.parse.quote(name)})

    def export_view(self, qs):
        lang = qs.get('lang') if qs.get('lang') in TEXT else ui_lang()
        T = TEXT[lang]
        mb = lambda n: round((n or 0) / 1048576, 2)  # noqa: E731
        when = lambda m: dt.datetime.fromtimestamp(m) if m else None  # noqa: E731
        if qs.get('view') == 'dups':
            d = self.duplicates()
            cols = [T['xd_set'], T['x_file'], T['x_folder'], T['xd_mb'], T['xd_copies'], T['xd_extra'], T['xd_modified'], T['xd_newest']]
            rows = [[i + 1, f['name'], f['dir'], mb(g['size']), g['count'], mb(g['wasted']), when(f['mtime']), T['xd_yes'] if j == 0 else '']
                    for i, g in enumerate(d['groups']) for j, f in enumerate(g['files'])]
            widths, sheet = [8, 34, 60, 12, 10, 14, 20, 10], T['xd_sheet']
        else:
            d = self.space(os.path.normpath(qs['folder']) if qs.get('folder') else '')
            cols = [T['x_file'], T['x_folder'], T['xd_mb'], T['xd_modified']]
            rows = [[f['name'], f['dir'], mb(f['size']), when(f['mtime'])] for f in (d['stale'] if qs.get('stale') else d['big'])]
            widths, sheet = [40, 64, 12, 20], T['xs_sheet']
        data = xlsx.write_xlsx(cols, rows, widths=widths, sheet=sheet)
        name = f"{T['app']} {sheet} {time.strftime('%Y-%m-%d')}.xlsx"
        self.send_bytes(data, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        {'Content-Disposition': "attachment; filename*=UTF-8''" + urllib.parse.quote(name)})

    def search(self, qs):
        """Find current documents whose text contains ``q`` (ranked, with a highlighted snippet)."""
        st, q = App.store, (qs.get('q') or '').strip()
        if not st.fts:
            return {'files': [], 'total': 0, 'indexed': 0, 'available': False}
        indexed = st.q('SELECT COUNT(DISTINCT f.hash) n FROM files f JOIN ftsdoc d ON d.hash = f.hash')[0]['n']
        if not q:
            return {'files': [], 'total': 0, 'indexed': indexed, 'available': True}
        with st.lock:
            if len(q) >= 3:  # trigram index: fast, ranked
                rows = st.conn.execute(
                    "SELECT d.hash h, snippet(fts, 0, char(2), char(3), '…', 24) s FROM fts JOIN ftsdoc d ON d.id = fts.rowid"
                    ' WHERE fts MATCH ? ORDER BY rank LIMIT 1000', ('"' + q.replace('"', '""') + '"',)).fetchall()
                hits = {r['h']: r['s'] for r in rows}
            else:            # one or two characters (common in Chinese): plain substring scan
                like = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'
                rows = st.conn.execute("SELECT d.hash h, fts.body b FROM fts JOIN ftsdoc d ON d.id = fts.rowid"
                                       " WHERE fts.body LIKE ? ESCAPE '\\' LIMIT 1000", (like,)).fetchall()
                hits = {r['h']: make_snippet(r['b'], q) for r in rows}
        cats = set(qs['cats'].split(',')) if qs.get('cats') else None
        rank = {h: i for i, h in enumerate(hits)}
        found = []
        if hits:
            marks = ','.join('?' * len(hits))
            found = [r for r in st.q(f'SELECT path, size, mtime, hash FROM files WHERE hash IN ({marks})', list(hits))
                     if not cats or category_of(os.path.splitext(r['path'])[1]) in cats]
        found.sort(key=lambda r: rank[r['hash']])
        counts = change_counts()
        out = [{**file_row(r['path'], r['size'], r['mtime'], r['hash'], counts.get(r['path'], 0)), 'snippet': hits[r['hash']]}
               for r in found[:300]]
        return {'files': out, 'total': len(found), 'indexed': indexed, 'available': True}

    def media(self, qs):
        """An image embedded in a .docx/.pptx/.xlsx, from a snapshot or from the live file."""
        part = qs.get('part', '')
        if not re.match(r'^(word|ppt|xl)/media/[^/]+\.(png|jpe?g|gif|bmp|webp)$', part, re.I):
            return self.send_json({'error': 'unsupported'}, 404)
        h, p = qs.get('hash', ''), qs.get('path', '')
        if h:
            if not (valid_hash(h) and App.store.has_blob(h)):
                return self.send_json({'error': 'not found'}, 404)
            src = io.BytesIO(App.store.read_blob(h))
        elif self.allowed_path(p) and os.path.isfile(p):
            src = p
        else:
            return self.send_json({'error': 'not found'}, 404)
        try:
            with zipfile.ZipFile(src) as z:
                data = z.read(part)
        except (KeyError, zipfile.BadZipFile, OSError):
            return self.send_json({'error': 'not found'}, 404)
        return self.send_bytes(data, mimetypes.guess_type(part)[0] or 'image/png',
                               {'Cache-Control': 'max-age=86400' if h else 'no-store', 'X-Content-Type-Options': 'nosniff'})

    def current(self, p):
        if not self.allowed_path(p) or not os.path.isfile(p):
            return {'ok': False, 'code': 'gone'}
        st = os.stat(p)
        if st.st_size > 200 * 1024 * 1024:
            return {'ok': False, 'code': 'tooLarge', 'size': st.st_size}
        if cleaner.online_only(p):
            return {'ok': False, 'code': 'cloud'}  # opening it would download it (2.4.2)
        key = (p, st.st_size, st.st_mtime_ns)
        res = App.current_cache.get(key)
        if res is None:
            with open(p, 'rb') as fh:
                res = strip_lines(extract(fh.read(), os.path.splitext(p)[1]))
            App.current_cache[key] = res
        return {'ok': True, 'content': res, 'size': st.st_size, 'mtime': st.st_mtime}

    def diff(self, eid, context=3):
        key = (eid, context)
        hit = App.diff_cache.get(key)
        if hit is not None:
            return hit
        r = App.store.q('SELECT * FROM events WHERE id=?', (eid,))[0]
        ext = r['ext']
        new = App.store.content(r['hash'], ext) if r['kind'] != 'deleted' else None
        old = App.store.content(r['prev_hash'], ext) if r['kind'] != 'created' else None
        res = {'kind': r['kind'], 'has_new': new is not None, 'has_old': old is not None,
               'type': (new or old or {}).get('type')}
        if r['kind'] == 'renamed':
            res['note'] = 'rename'
        elif (r['kind'] == 'modified' and (new is None or old is None)) or (new is None and old is None):
            res['note'] = 'missing'
        else:
            res.update(build_diff(old['lines'] if old else [], new['lines'] if new else [], context=context,
                                  max_lines=20000 if context > 50 else 6000))
        App.diff_cache[key] = res
        return res

    def folder_at(self, folder, when, lang=None):
        """Write ``folder`` as it was at time ``when`` into a new folder next to it — every file that existed
        then, in the version it had then; nothing in the real folder is touched (2.6.0 #31)."""
        folder = os.path.normpath(folder)
        if not self.allowed_path(folder) or not os.path.isdir(folder):
            return {'ok': False, 'code': 'notAllowed'}
        lo = folder.rstrip('\\') + '\\'
        hi = lo[:-1] + chr(ord('\\') + 1)
        state = {}  # path -> hash at ``when`` (None: did not exist then)
        for p, c in list(App.mon.confirmed.items()):  # what is known now, in case nothing changed since
            if p.startswith(lo):
                state[p] = c[2]
        later = App.store.q('SELECT * FROM events WHERE ((path >= ? AND path < ?) OR (old_path >= ? AND old_path < ?)) AND ts > ?'
                            ' ORDER BY id DESC', (lo, hi, lo, hi, when))
        for r in later:  # walk back from now to ``when``: undo each later change
            if r['kind'] == 'created':
                state[r['path']] = None
            elif r['kind'] == 'deleted':
                state[r['path']] = r['prev_hash']
            elif r['kind'] == 'modified':
                state[r['path']] = r['prev_hash']
            elif r['kind'] == 'renamed':
                h = state.pop(r['path'], r['hash'])
                if r['old_path'] and r['old_path'].startswith(lo):
                    state[r['old_path']] = h
        word = 'as of' if lang != 'zh' else '截至'
        dest = f'{folder} ({word} {time.strftime("%Y-%m-%d %H-%M", time.localtime(when))})'
        n = 2
        while os.path.exists(long_path(dest)):
            dest, n = f'{folder} ({word} {time.strftime("%Y-%m-%d %H-%M", time.localtime(when))}) ({n})', n + 1
        done = missing = 0
        for p, h in state.items():
            if h is None:
                continue
            if not App.store.has_blob(h):
                missing += 1
                continue
            out = os.path.join(dest, os.path.relpath(p, folder))
            try:
                os.makedirs(long_path(os.path.dirname(out)), exist_ok=True)
                App.store.copy_blob(h, out)
                done += 1
            except OSError:
                missing += 1
        return {'ok': True, 'path': dest, 'files': done, 'missing': missing}

    def rename_back(self, ids):
        """Give renamed or moved files their old names back, newest first; never overwrites (2.6.0 #40)."""
        done, skipped = [], []
        rows = [r[0] for r in (App.store.q("SELECT * FROM events WHERE id=? AND kind='renamed'", (int(i),)) for i in ids[:5000]) if r]
        for r in sorted(rows, key=lambda r: -r['id']):
            cur, old = r['path'], r['old_path']
            if not (old and self.allowed_path(cur) and self.allowed_path(old)):
                skipped.append({'path': cur, 'code': 'notAllowed'})
            elif not os.path.exists(long_path(cur)):
                skipped.append({'path': cur, 'code': 'gone'})
            elif os.path.exists(long_path(old)):
                skipped.append({'path': cur, 'code': 'taken'})
            else:
                try:
                    os.makedirs(long_path(os.path.dirname(old)), exist_ok=True)
                    os.rename(long_path(cur), long_path(old))
                    done.append(old)
                except OSError:
                    skipped.append({'path': cur, 'code': 'inUse'})
        App.mon.wake.set()
        return {'ok': True, 'done': len(done), 'skipped': skipped}

    def restore(self, b):
        r = App.store.q('SELECT * FROM events WHERE id=?', (int(b['id']),))[0]
        h = r['prev_hash'] if b.get('version') == 'prev' else (r['hash'] or r['prev_hash'])
        if not App.store.has_blob(h):
            return {'ok': False, 'code': 'noSnapshot'}
        target = r['old_path'] if r['kind'] == 'renamed' and b.get('version') == 'prev' else r['path']
        if b.get('replace') and os.path.isfile(target):  # roll the file itself back (2.0.1) — only if its current
            with App.mon.lock:                          # content is kept, so this can be undone the same way
                c = App.mon.confirmed.get(target)
            if not (c and c[2] and App.store.has_blob(c[2])):
                return {'ok': False, 'code': 'noBackup'}
            try:
                App.store.copy_blob(h, target)
            except RestoreError as e:
                return {'ok': False, 'code': e.code, 'path': target, 'by': cleaner.lockers(target) if e.code == 'inUse' else []}
            milestone('restored', 1)
            return {'ok': True, 'path': target, 'replaced': True}
        if os.path.exists(long_path(target)):
            target = restore_copy_name(target, b.get('lang'))
        os.makedirs(long_path(os.path.dirname(target)), exist_ok=True)
        try:
            App.store.copy_blob(h, target)
        except RestoreError as e:
            return {'ok': False, 'code': e.code, 'path': target}
        milestone('restored', 1)
        m = r['mtime'] if b.get('version') != 'prev' else None  # keep the version's own date when known (2.0.1)
        if m:
            try:
                m = m / 1e9 if m > 1e12 else m
                os.utime(long_path(target), (m, m))
            except (OSError, ValueError):
                pass
        return {'ok': True, 'path': target}

    def restore_into(self, ids, to):
        """Copies of a group's versions in a folder the user chose, keeping the folders below their common
        folder; nothing at the original places is touched and nothing is overwritten (2.1.0)."""
        if not os.path.isdir(to):
            return {'ok': False, 'code': 'gone'}
        rows = [r[0] for r in (App.store.q('SELECT * FROM events WHERE id=?', (int(i),)) for i in ids) if r]
        try:
            base = os.path.commonpath([os.path.dirname(r['path']) for r in rows]) if rows else None
        except ValueError:  # on different drives
            base = None
        done = failed = 0
        for r in rows:
            h = r['prev_hash'] if r['kind'] == 'deleted' else r['hash']
            if not (h and App.store.has_blob(h)):
                failed += 1
                continue
            dest = os.path.join(to, os.path.relpath(r['path'], base) if base else os.path.basename(r['path']))
            stem, ext = os.path.splitext(dest)
            n = 2
            while os.path.exists(long_path(dest)):
                dest, n = f'{stem} ({n}){ext}', n + 1
            try:
                os.makedirs(long_path(os.path.dirname(dest)), exist_ok=True)
                App.store.copy_blob(h, dest)
                done += 1
            except OSError:
                failed += 1
        return {'ok': True, 'restored': done, 'failed': failed, 'path': to}

    def restore_many(self, b):
        """Restore a group of changes: deleted files come back as they were, others as this version."""
        if b.get('to'):  # into another folder instead (2.1.0)
            return self.restore_into(b.get('ids', [])[:5000], os.path.normpath(str(b['to'])))
        done, failed = [], 0
        for eid in b.get('ids', [])[:5000]:
            rows = App.store.q('SELECT kind FROM events WHERE id=?', (int(eid),))
            if not rows:
                continue
            version = 'prev' if rows[0]['kind'] == 'deleted' else 'this'
            try:
                r = self.restore({'id': eid, 'version': version, 'lang': b.get('lang')})
            except OSError:
                r = {'ok': False}
            if r.get('ok'):
                done.append(r['path'])
            else:
                failed += 1
        return {'ok': True, 'restored': len(done), 'failed': failed}

    def update_settings(self, b):
        s = App.mon.settings
        new = dict(s)
        if 'roots' in b:
            roots = []
            for r in b['roots']:
                r = os.path.normpath(os.path.expandvars(os.path.expanduser(str(r).strip().strip('"'))))
                if r and (os.path.isdir(r) or r in s['roots']) and r not in roots and r != b.get('drop_root'):  # an unplugged drive stays (2.4.2)
                    roots.append(r)
            if not roots:
                return {'ok': False, 'code': 'noRoots'}
            new['roots'] = roots
        for k, lo, hi in (('interval', 0.5, 600), ('snapshot_max_mb', 0, 2048),
                          ('baseline_text_max_mb', 0, 2048), ('baseline_copy_mb', 0, 2048),
                          ('keep_days', 0, 3650), ('max_storage_gb', 0, 1000)):
            if k in b:
                new[k] = max(lo, min(hi, float(b[k])))
        retention_changed = any(new.get(k) != s.get(k) for k in ('keep_days', 'max_storage_gb'))
        for k in ('exclude_exts', 'exclude_names', 'exclude_dirs', 'exclude_paths'):
            if k in b:
                new[k] = [str(x).strip() for x in b[k] if str(x).strip()]
        if b.get('lang') in ('', 'en', 'zh'):
            new['lang'] = b['lang']
        if b.get('notify') in ('off', 'deleted', 'all'):
            new['notify'] = b['notify']
        if 'prescan' in b:
            new['prescan'] = bool(b['prescan'])
        if 'milestones' in b:
            new['milestones'] = bool(b['milestones'])  # 2.6.0 #50
        scope_changed = any(new.get(k) != s.get(k) for k in ('roots', 'exclude_exts', 'exclude_names', 'exclude_dirs', 'exclude_paths'))
        with App.mon.lock:
            removed_roots = set(s['roots']) - set(new['roots'])
            App.mon.known_roots -= removed_roots
            App.store.set_meta('known_roots', sorted(App.mon.known_roots))
            if scope_changed:
                App.mon.prev_scope = (App.mon.rules, list(s['roots']))
            s.update(new)
            App.mon.rules = Rules(s)
        save_settings(s)
        if scope_changed:
            App.mon.request_full()
        App.mon.wake.set()
        if retention_changed and getattr(App.mon, 'housekeeping_wake', None):
            App.mon.housekeeping_wake.set()
        return {'ok': True, 'settings': s}


def pick_folder():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        p = filedialog.askdirectory(title='Choose a folder to monitor')
        root.destroy()
        return os.path.normpath(p) if p else ''
    except Exception:
        return ''


def recycle(path):
    """Move a file to the Recycle Bin (it can be put back from there, and DeskTrace keeps its snapshot).
    Refused where the Recycle Bin would not keep it (no bin on that drive, switched off, file bigger than
    the bin): with "no confirmation" Windows would delete such a file for good, silently (2.3.0)."""
    if os.name != 'nt' or cleaner.recycle_problem(path):
        return False
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT), ('pFrom', wintypes.LPCWSTR), ('pTo', wintypes.LPCWSTR),
                    ('fFlags', ctypes.c_ushort), ('fAnyOperationsAborted', wintypes.BOOL), ('hNameMappings', ctypes.c_void_p),
                    ('lpszProgressTitle', wintypes.LPCWSTR)]
    # FO_DELETE with FOF_ALLOWUNDO (to the Recycle Bin) | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    # FOF_WANTNUKEWARNING (0x4000): should Windows still want to delete for good, it asks first
    op = SHFILEOPSTRUCTW(None, 3, path + '\0', None, 0x40 | 0x10 | 0x4 | 0x400 | 0x4000, False, None, None)
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op)) == 0 and not op.fAnyOperationsAborted and not os.path.exists(path)


def recycle_many(paths):
    """Move many files to the Recycle Bin in one Windows call per batch (2.6.0 #7); returns those moved."""
    if os.name != 'nt' or not paths:
        return []
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [('hwnd', wintypes.HWND), ('wFunc', wintypes.UINT), ('pFrom', wintypes.LPCWSTR), ('pTo', wintypes.LPCWSTR),
                    ('fFlags', ctypes.c_ushort), ('fAnyOperationsAborted', wintypes.BOOL), ('hNameMappings', ctypes.c_void_p),
                    ('lpszProgressTitle', wintypes.LPCWSTR)]
    ok = [p for p in paths if not cleaner.recycle_problem(p)]  # never "to the Recycle Bin" that would really be gone
    for i in range(0, len(ok), 400):
        batch = ok[i:i + 400]
        op = SHFILEOPSTRUCTW(None, 3, '\0'.join(batch) + '\0\0', None, 0x40 | 0x10 | 0x4 | 0x400 | 0x4000, False, None, None)
        ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return [p for p in ok if not os.path.exists(p)]


def pick_save(name, folder=''):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        p = filedialog.asksaveasfilename(title=APP_NAME, initialfile=name, initialdir=folder or None,
                                         defaultextension=os.path.splitext(name)[1])
        root.destroy()
        return os.path.normpath(p) if p else ''
    except Exception:
        return ''


def pick_license():
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        p = filedialog.askopenfilename(title=APP_NAME, filetypes=[(APP_NAME + ' license', '*' + updmod.EXT)])
        root.destroy()
        return os.path.normpath(p) if p else ''
    except Exception:
        return ''


class QuietServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False  # on Windows "reuse" would let two copies share a port; we want "taken"

    def server_bind(self):
        if os.name == 'nt':  # claim the port exclusively so a second copy moves on to the next one
            import socket
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            return  # the browser dropped a connection; not worth logging
        super().handle_error(request, client_address)


# ---------------------------------------------------------------------------- tray & notifications

TEXT = {
    'en': {'open': 'Open DeskTrace', 'pause': 'Pause monitoring', 'resume': 'Resume monitoring',
           'notify': 'Notifications', 'notify-off': 'Off', 'notify-deleted': 'Deleted files only',
           'notify-all': 'All changes', 'autostart': 'Start with Windows', 'quit': 'Quit',
           'tip': 'DeskTrace — watching {n} files', 'tip_paused': 'DeskTrace — paused',
           'created': 'Created', 'modified': 'Modified', 'deleted': 'Deleted', 'renamed': 'Renamed',
           'n_created': '{n} files created', 'n_modified': '{n} files modified', 'n_deleted': '{n} files deleted',
           'n_renamed': '{n} files renamed', 'n_mixed': '{n} changes', 'sep': ', ',
           'hint_deleted': 'Click to see it — you can restore it from there.', 'hint': 'Click to see what changed.'},
    'zh': {'open': '打开 桌迹', 'pause': '暂停监控', 'resume': '继续监控',
           'notify': '桌面通知', 'notify-off': '关闭', 'notify-deleted': '仅删除文件时',
           'notify-all': '所有变更', 'autostart': '开机自动启动', 'quit': '退出',
           'tip': '桌迹 — 正在监控 {n} 个文件', 'tip_paused': '桌迹 — 已暂停',
           'created': '新建', 'modified': '修改', 'deleted': '删除', 'renamed': '重命名',
           'n_created': '新建了 {n} 个文件', 'n_modified': '修改了 {n} 个文件', 'n_deleted': '删除了 {n} 个文件',
           'n_renamed': '重命名了 {n} 个文件', 'n_mixed': '{n} 处变更', 'sep': '、',
           'hint_deleted': '点击查看——可以在那里恢复。', 'hint': '点击查看改动。'},
}
for _lang, _extra in {
    'en': {'tip_warn': '⚠ History may be incomplete — open DeskTrace for details', 'tip': 'DeskTrace — watching {n} files · {c} changes today', 'recent': 'Recent changes',
           'recent_none': 'No changes yet',
           'x_sheet': 'Changes', 'x_time': 'Time', 'x_change': 'Change', 'x_file': 'File', 'x_folder': 'Folder',
           'x_path': 'Full path', 'x_old': 'Previous path', 'x_before': 'Size before (bytes)', 'x_after': 'Size after (bytes)',
           'x_added': 'Added', 'x_removed': 'Removed', 'x_summary': 'Summary', 'x_note': 'Note',
           's_new': 'New file', 's_newN': 'New file · {n} {u}', 's_del': 'Deleted', 's_delN': 'Deleted · had {n} {u}',
           's_renamed': 'Renamed', 's_moved': 'Moved', 's_big': 'Too large to snapshot', 's_locked': 'File locked — no snapshot',
           's_same': 'Saved — content unchanged', 's_fmt': 'Formatting / binary change', 's_size': 'Size {d}'},
    'zh': {'tip_warn': '⚠ 历史记录可能不完整——打开桌迹查看详情', 'tip': '桌迹 — 正在监控 {n} 个文件 · 今天 {c} 处变更', 'recent': '最近的变更', 'recent_none': '暂无变更',
           'x_sheet': '变更记录', 'x_time': '时间', 'x_change': '变更', 'x_file': '文件', 'x_folder': '文件夹',
           'x_path': '完整路径', 'x_old': '原路径', 'x_before': '修改前大小（字节）', 'x_after': '修改后大小（字节）',
           'x_added': '新增', 'x_removed': '删除', 'x_summary': '摘要', 'x_note': '备注',
           's_new': '新文件', 's_newN': '新文件 · {n} {u}', 's_del': '已删除', 's_delN': '已删除 · 原有 {n} {u}',
           's_renamed': '已重命名', 's_moved': '已移动', 's_big': '文件过大，未保存快照', 's_locked': '文件被占用，未保存快照',
           's_same': '已保存，内容未变化', 's_fmt': '格式或二进制内容变化', 's_size': '大小 {d}'},
}.items():
    TEXT[_lang].update(_extra)
for _lang, _extra in {
    'en': {'pause_indef': 'Until I resume', 'pause_30': 'For 30 minutes', 'pause_120': 'For 2 hours',
           'tip_paused_until': 'DeskTrace — paused until {t}', 'mute_60': 'Mute for 1 hour',
           'mute_tomorrow': 'Mute until 8:00 tomorrow', 'unmute': 'Unmute (muted until {t})',
           'shell_label': 'DeskTrace: show history', 'shell_deleted': 'DeskTrace: deleted files here'},
    'zh': {'pause_indef': '直到手动继续', 'pause_30': '30 分钟', 'pause_120': '2 小时',
           'tip_paused_until': '桌迹 — 已暂停，{t} 自动继续', 'mute_60': '静音 1 小时',
           'mute_tomorrow': '静音到明早 8:00', 'unmute': '取消静音（原定静音到 {t}）',
           'shell_label': '桌迹：查看历史版本', 'shell_deleted': '桌迹：找回这里删除的文件'},
}.items():
    TEXT[_lang].update(_extra)
for _lang, _extra in {
    'en': {'app': 'DeskTrace', 'xd_sheet': 'Duplicates', 'xs_sheet': 'Biggest files', 'xd_set': 'Set', 'xd_mb': 'Size (MB)', 'xd_copies': 'Copies', 'xd_extra': 'Extra (MB)', 'xd_modified': 'Modified', 'xd_newest': 'Newest', 'xd_yes': 'yes', 'update_to': 'Update to version {v}…', 'update_title': 'DeskTrace {v} is available',
           'update_text': 'Click to see what is new and update.',
           'locked': 'DeskTrace now opens in its own window. Use the DeskTrace shortcut on your Desktop '
                     'or in the Start menu, or click its icon in the notification area.'},
    'zh': {'app': '桌迹', 'xd_sheet': '重复文件', 'xs_sheet': '最大的文件', 'xd_set': '组', 'xd_mb': '大小（MB）', 'xd_copies': '份数', 'xd_extra': '多占（MB）', 'xd_modified': '修改时间', 'xd_newest': '最新', 'xd_yes': '是', 'update_to': '更新到 {v} 版…', 'update_title': '桌迹 {v} 新版本可用',
           'update_text': '点击查看新内容并更新。',
           'locked': '桌迹 现在在自己的窗口中打开。请使用桌面或开始菜单中的 桌迹 快捷方式，'
                     '或点击通知区域中的桌迹图标。'},
}.items():
    TEXT[_lang].update(_extra)
UNITS = {'en': {'paragraph': ('paragraph', 'paragraphs'), 'cell': ('cell', 'cells'), 'line': ('line', 'lines')},
         'zh': {'paragraph': ('段', '段'), 'cell': ('个单元格', '个单元格'), 'line': ('行', '行')}}
TRAY_COMMANDS = ['open', 'toggle-pause', 'notify-off', 'notify-deleted', 'notify-all', 'autostart', 'quit', 'update']


def summary_text(r, lang):
    """A change's one-line summary as text (the UI builds the same from the structured form)."""
    T = TEXT[lang]
    try:
        s = json.loads(r['summary']) if r['summary'] else None
    except ValueError:
        return r['summary'] or ''
    if not isinstance(s, dict):
        return ''
    t = s.get('t')
    unit = UNITS[lang].get(s.get('u') or 'line', UNITS[lang]['line'])
    if t == 'diff':
        return f"+{r['added']} −{r['removed']} {unit[1]}"
    if t in ('new', 'del'):
        return T[f's_{t}N'].format(n=s['n'], u=unit[0 if s['n'] == 1 else 1]) if s.get('n') else T[f's_{t}']
    if t == 'size':
        d = s.get('d') or 0
        return T['s_size'].format(d=('+' if d >= 0 else '−') + fmt_size(abs(d)))
    return T.get(f's_{t}', '')


KNOWN_FOLDERS = {'documents': '{FDD39AD0-238F-46AF-ADB4-6C85480369C7}',
                 'downloads': '{374DE290-123F-4565-9164-39C4925E467B}',
                 'pictures': '{33E28130-4E1E-4676-835A-98395C3BC3BB}'}


def known_folder(guid):
    """Path of a Windows known folder (handles folders the user moved, e.g. to OneDrive or D:)."""
    import ctypes
    import uuid
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [('Data1', wintypes.DWORD), ('Data2', wintypes.WORD), ('Data3', wintypes.WORD), ('Data4', ctypes.c_ubyte * 8)]

    u = uuid.UUID(guid)
    g = GUID(u.time_low, u.time_mid, u.time_hi_version, (ctypes.c_ubyte * 8)(*u.bytes[8:]))
    f = ctypes.windll.shell32.SHGetKnownFolderPath
    f.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
    f.restype = ctypes.c_long
    out = ctypes.c_wchar_p()
    if f(ctypes.byref(g), 0, None, ctypes.byref(out)) != 0:
        return None
    path = out.value
    ctypes.windll.ole32.CoTaskMemFree(ctypes.cast(out, ctypes.c_void_p))
    return path


def suggested_folders(roots):
    """Common folders the user could add with one click (those not already covered)."""
    if os.name != 'nt':
        return []
    out = []
    for key, guid in KNOWN_FOLDERS.items():
        try:
            p = known_folder(guid)
        except Exception:
            p = None
        if p and os.path.isdir(p) and not any(under(p, r) for r in roots):
            out.append({'key': key, 'path': p})
    return out


def ui_lang():
    """The language chosen in Settings, else the Windows display language."""
    lang = App.mon.settings.get('lang') or ''
    if lang in TEXT:
        return lang
    if os.name == 'nt':
        try:
            import ctypes
            primary = ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF
            return {0x04: 'zh'}.get(primary, 'en')
        except Exception:
            pass
    return 'en'


def tr(key, **kw):
    return TEXT[ui_lang()][key].format(**kw)


def crumb(ev):
    return ' › '.join(p for p in [ev.get('root_name'), *ev.get('rel_dir', '').split(os.sep)] if p)


class Notifier:
    """Turns bursts of changes into a few Windows notifications instead of one per file."""
    QUIET, MAX_WAIT = 2.5, 8.0

    def __init__(self, show):
        self.show = show
        self.pending, self.first, self.timer = [], 0.0, None
        self.lock = threading.Lock()
        self.last_id = None

    def add(self, ev):
        if time.time() < float(App.mon.settings.get('mute_until') or 0):
            return  # "do not disturb"
        if user_busy_fullscreen():
            return  # a presentation, a meeting shared full screen, a game or a video: no pop-ups (2.6.0 #39)
        policy = App.mon.settings.get('notify', 'off')
        starred = ev.get('path') in App.mon.stars or ev.get('old_path') in App.mon.stars
        if not starred and (policy == 'off' or (policy == 'deleted' and ev['kind'] != 'deleted')):
            return  # starred files always notify
        with self.lock:
            now = time.time()
            if not self.pending:
                self.first = now
            self.pending.append(ev)
            self.due = min(now + self.QUIET, self.first + self.MAX_WAIT)
            if not self.timer:  # one timer per burst, not a new one per file (2.1.0)
                self._start(self.due - now)

    def _start(self, delay):
        self.timer = threading.Timer(max(0.1, delay), self._fire)
        self.timer.daemon = True
        self.timer.start()

    def _fire(self):
        with self.lock:
            wait = self.due - time.time()
            if wait > 0.05:  # more changes came in meanwhile: wait for the quiet moment
                self._start(wait)
                return
        self.flush()

    def flush(self):
        with self.lock:
            evs, self.pending, self.timer = self.pending, [], None
        if not evs:
            return
        self.last_id = evs[0]['id']
        App.notify_hash = f'#event={self.last_id}'
        kinds = {e['kind'] for e in evs}
        hint = tr('hint_deleted' if kinds == {'deleted'} else 'hint')
        if len(evs) == 1:
            e = evs[0]
            title = f"{tr(e['kind'])}: {e['name']}"
            text = f'{crumb(e)}\n{hint}'
        else:
            kind = kinds.pop() if len(kinds) == 1 else 'mixed'
            title = tr('n_' + kind, n=len(evs))
            names = tr('sep').join(e['name'] for e in evs[:3]) + ('…' if len(evs) > 3 else '')
            text = f'{names}\n{hint}'
        try:
            shown = self.show(title, text)
            print(f'notification {"shown" if shown else "NOT shown"}: {title}')
        except Exception as e:
            print('notify error:', repr(e))


def tray_menu():
    s, paused = App.mon.settings, App.mon.paused
    n = s.get('notify', 'off')
    recent = [(f"event:{r['id']}", f"{time.strftime('%H:%M', time.localtime(r['ts']))}   {tr(r['kind'])} · "
               + os.path.basename(r['path']).replace('&', '&&'))  # '&' would underline the next letter
              for r in App.store.q('SELECT id, kind, path, ts FROM events ORDER BY id DESC LIMIT 8')]
    mute_until = float(s.get('mute_until') or 0)
    muted = time.time() < mute_until
    pause = (('toggle-pause', tr('resume')) if paused else
             ('>', tr('pause'), [('toggle-pause', tr('pause_indef')), ('pause-30', tr('pause_30')), ('pause-120', tr('pause_120'))]))
    notify = [(c, tr(c), n == c.split('-')[1]) for c in ('notify-off', 'notify-deleted', 'notify-all')] + [('-',)] + (
        [('unmute', tr('unmute', t=time.strftime('%H:%M', time.localtime(mute_until))))] if muted
        else [('mute-60', tr('mute_60')), ('mute-tomorrow', tr('mute_tomorrow'))])
    upd = App.updates.pending if App.updates else None
    return [('open', tr('open'))] + ([('update', tr('update_to', v=upd['version']))] if upd else []) + [
            ('>', tr('recent'), recent or [('noop', tr('recent_none'))]), ('-',),
            pause, ('>', tr('notify'), notify), ('autostart', tr('autostart'), STARTUP_LNK.exists()),
            ('-',), ('quit', tr('quit'))]


def set_pause(paused, minutes=0):
    App.mon.paused = paused
    App.mon.pause_until = time.time() + minutes * 60 if paused and minutes else 0.0
    App.mon.wake.set()


def set_mute(minutes=0, until=None):
    """Silence desktop notifications for a while ('tomorrow' = until 8:00 next morning); 0 = unmute."""
    if until == 'tomorrow':
        t = time.localtime(time.time() + 86400)
        end = time.mktime((t.tm_year, t.tm_mon, t.tm_mday, 8, 0, 0, 0, 0, -1))
    else:
        end = time.time() + minutes * 60 if minutes > 0 else 0
    App.mon.settings['mute_until'] = end
    save_settings(App.mon.settings)


SHELL_KEY = r'Software\Classes\*\shell\DesktopWatch'  # per-user: no admin rights, nothing system-wide
# 2.6.0 #4: on a folder and on a folder's empty space: "DeskTrace: deleted files here" (%1 = the folder, %V = the open folder)
SHELL_DIR_KEYS = ((r'Software\Classes\Directory\shell\DeskTraceDeleted', '%1'),
                  (r'Software\Classes\Directory\Background\shell\DeskTraceDeleted', '%V'))


def shell_menu_enabled():
    if os.name != 'nt':
        return False
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, SHELL_KEY))
        return True
    except OSError:
        return False


def set_shell_menu(on):
    """Add or remove "DeskTrace: show history" in Explorer's right-click menu for files."""
    if os.name != 'nt':
        return False
    import winreg
    if on:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SHELL_KEY) as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, tr('shell_label'))
            winreg.SetValueEx(k, 'Icon', 0, winreg.REG_SZ, str(STATIC / 'icon.ico'))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SHELL_KEY + r'\command') as k:
            winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{pythonw()}" "{APP_DIR / "server.py"}" --show "%1"')
        for key, arg in SHELL_DIR_KEYS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as k:
                winreg.SetValueEx(k, '', 0, winreg.REG_SZ, tr('shell_deleted'))
                winreg.SetValueEx(k, 'Icon', 0, winreg.REG_SZ, str(STATIC / 'icon.ico'))
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key + r'\command') as k:
                winreg.SetValueEx(k, '', 0, winreg.REG_SZ, f'"{pythonw()}" "{APP_DIR / "server.py"}" --show-deleted "{arg}"')
    else:
        for sub in (SHELL_KEY + r'\command', SHELL_KEY) + tuple(x for k, _ in SHELL_DIR_KEYS for x in (k + r'\command', k)):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except OSError:
                pass
    return shell_menu_enabled()


def locked_page():
    """What a web browser gets: the interface is only served to the app's own window."""
    import html
    return ('<!doctype html><meta charset="utf-8"><title>DeskTrace</title><body style="font:15px/1.6 '
            'system-ui,sans-serif;max-width:560px;margin:80px auto;padding:0 20px;color:#334">'
            f'<h2>{html.escape(tr("app"))}</h2><p>{html.escape(tr("locked"))}</p>').encode('utf-8')


def allow_foreground():
    """Let the window we are about to start come to the front (we may have the right, it doesn't yet)."""
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
        except Exception:
            pass


def edge_path():
    import winreg
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(root, r'Software\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe') as k:
                p = winreg.QueryValueEx(k, '')[0]
                if os.path.exists(p):
                    return p
        except OSError:
            pass
    return None


def open_window(fragment='', port=None, token=None, pid=None):
    """Show the interface in the app's own window (window.py, Microsoft Edge WebView2). If WebView2 is
    missing, fall back to an Edge app window, and only then to the default browser."""
    port, token, pid = port or App.port, token or TOKEN, pid or os.getpid()
    url = f'http://127.0.0.1:{port}/app?k={token}'
    allow_foreground()
    try:
        import window as winmod
        if winmod.available():
            subprocess.Popen([pythonw(), str(APP_DIR / 'window.py'), '--url', url, '--data', str(DATA),
                              '--hash', fragment or '', '--pid', str(pid)], cwd=str(APP_DIR), creationflags=NO_WINDOW)
            return 'window'
        edge = edge_path()
        if edge:
            subprocess.Popen([edge, f'--app={url}{fragment}', f'--user-data-dir={DATA / "edge-app"}',
                              '--no-first-run'], creationflags=NO_WINDOW)
            return 'edge'
    except Exception as e:
        print('window:', repr(e))
    webbrowser.open(url + (fragment or ''))
    return 'browser'


def update_found(meta):
    """A version license was dropped into a monitored folder: tell the window and the tray."""
    App.hub.publish({'type': 'app-update', 'update': App.updates.status(ui_lang())})
    App.notify_hash = '#update'
    if App.tray:
        App.tray.notify(tr('update_title', v=meta['version']), tr('update_text'))


def check_license(path):
    if App.updates and str(path).lower().endswith(updmod.EXT):
        threading.Thread(target=App.updates.consider, args=(path,), daemon=True, name='license').start()


def on_change(ev):
    App.notifier.add(ev)
    if ev['kind'] in ('created', 'modified', 'renamed'):
        check_license(ev['path'])


def find_licenses():
    """At start (after the first scan) look for licenses already sitting in the monitored folders."""
    for _ in range(600):
        if App.mon.stats.get('scans'):
            break
        time.sleep(0.5)
    for p in list(App.mon.last or App.mon.confirmed):
        if p.lower().endswith(updmod.EXT):
            App.updates.consider(p)


def tray_command(name):
    if name == 'open':
        open_window()
    elif name == 'open-notification':
        open_window(App.notify_hash or '')
    elif name == 'update':
        open_window('#update')
    elif name == 'quick-restore':  # Ctrl+Alt+Z (2.6.0 #14)
        open_window('#recent')
    elif name.startswith('event:'):
        open_window('#event=' + name.split(':', 1)[1])
    elif name == 'toggle-pause':
        set_pause(not App.mon.paused)
    elif name.startswith('pause-'):
        set_pause(True, int(name.split('-')[1]))
    elif name == 'mute-60':
        set_mute(60)
    elif name == 'mute-tomorrow':
        set_mute(until='tomorrow')
    elif name == 'unmute':
        set_mute(0)
    elif name.startswith('notify-'):
        App.mon.settings['notify'] = name.split('-')[1]
        save_settings(App.mon.settings)
    elif name == 'autostart':
        set_autostart(not STARTUP_LNK.exists())
    elif name == 'quit':
        threading.Thread(target=App.server.shutdown, daemon=True).start()


def tray_status(status):
    day0 = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    today = App.store.q('SELECT COUNT(*) n FROM events WHERE ts >= ?', (day0,))[0]['n']
    if status['paused']:
        tip = (tr('tip_paused_until', t=time.strftime('%H:%M', time.localtime(status['pause_until'])))
               if status.get('pause_until') else tr('tip_paused'))
    else:
        tip = tr('tip', n=f"{status['files']:,}", c=today)
    if status.get('warn'):  # history may be incomplete: the tray says so too (2.3.0)
        tip = tr('tip_warn') + '\n' + tip
    burst = sum(n for t0, n in getattr(App.mon, '_burst', []) if time.time() - t0 < 15)
    state = 'alert' if 'mass' in (status.get('warn') or []) else 'busy' if burst >= 20 else None  # 2.6.0 #45
    App.tray.update(tooltip=tip, paused=status['paused'], state=state)


def background_thread():
    """Put the calling thread in Windows background mode: lowest CPU, disk and memory priority, so scanning,
    indexing and hashing never slow down what the user is doing (2.1.0). Request threads stay normal."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentThread.restype = ctypes.c_void_p
        k32.SetThreadPriority(ctypes.c_void_p(k32.GetCurrentThread()), 0x00010000)  # THREAD_MODE_BACKGROUND_BEGIN
    except Exception as e:
        print('background mode:', repr(e))


def process_use():
    """CPU seconds used since start, current memory (working set) and disk traffic of this service."""
    if os.name != 'nt':
        return {}
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        h = ctypes.c_void_p(k32.GetCurrentProcess())
        c, e, kt, ut = (wintypes.FILETIME() for _ in range(4))
        k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e), ctypes.byref(kt), ctypes.byref(ut))
        cpu = ((kt.dwHighDateTime << 32 | kt.dwLowDateTime) + (ut.dwHighDateTime << 32 | ut.dwLowDateTime)) / 1e7

        class PMC(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [(n, ctypes.c_size_t) for n in (
                'peak', 'ws', 'a', 'b', 'c', 'd', 'pf', 'peakpf')]
        pm = PMC(cb=ctypes.sizeof(PMC))
        ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pm), pm.cb)

        class IO(ctypes.Structure):
            _fields_ = [(n, ctypes.c_ulonglong) for n in ('r', 'w', 'o', 'rb', 'wb', 'ob')]
        io = IO()
        k32.GetProcessIoCounters(h, ctypes.byref(io))
        return {'cpu_s': round(cpu, 1), 'memory_mb': round(pm.ws / 2 ** 20), 'io_mb': round((io.rb + io.wb) / 2 ** 20)}
    except Exception:
        return {}


def on_battery():
    """True while a laptop runs on battery (Windows reports AC power as offline)."""
    if os.name != 'nt':
        return False
    try:
        import ctypes

        class SPS(ctypes.Structure):
            _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('saver', ctypes.c_ubyte),
                        ('life', ctypes.c_ulong), ('full', ctypes.c_ulong)]
        st = SPS()
        return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st))) and st.ac == 0
    except Exception:
        return False


def battery_low():
    """On battery with 20 % or less left (2.6.0 #41)."""
    if os.name != 'nt':
        return False
    try:
        import ctypes

        class SPS(ctypes.Structure):
            _fields_ = [('ac', ctypes.c_ubyte), ('flag', ctypes.c_ubyte), ('pct', ctypes.c_ubyte), ('saver', ctypes.c_ubyte),
                        ('life', ctypes.c_ulong), ('full', ctypes.c_ulong)]
        st = SPS()
        return bool(ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(st))) and st.ac == 0 and st.pct <= 20
    except Exception:
        return False


def user_busy_fullscreen():
    """True while a full-screen game or video, or a presentation, has the screen (Windows' own notion of
    "busy", the one that also holds back notifications)."""
    if os.name != 'nt':
        return False
    try:
        import ctypes
        state = ctypes.c_int(0)
        if ctypes.windll.shell32.SHQueryUserNotificationState(ctypes.byref(state)) != 0:
            return False
        # QUNS_RUNNING_D3D_FULL_SCREEN (a game) or QUNS_PRESENTATION_MODE; not QUNS_BUSY, which any borderless
        # full-screen window (a maximized browser, a launcher) already triggers
        return state.value in (3, 4)
    except Exception:
        return False


def wait_for_power(store=None):
    """Battery and presentation saver (2.1.0): heavy optional work (first-time indexing, comparing large
    files) waits while the PC runs on battery or a full-screen game, video or presentation is on.
    Change detection itself goes on as normal."""
    while on_battery() or user_busy_fullscreen():
        if store:
            store.flush()  # nothing stays uncommitted while waiting
        time.sleep(60)


def trim_when_idle():
    """After 10 minutes without the window asking for anything: drop the caches and give the memory back
    to Windows (2.1.0). Runs once per idle stretch."""
    if App.trimmed or time.time() - App.last_request < 600:
        return
    App.trimmed = True
    App.diff_cache.clear()
    App.current_cache.clear()
    _view_cache.clear()
    for d in [d for d, sc in _scans.items() if sc.state != 'scanning']:  # drive scans: made again on the next visit (2.2.0)
        del _scans[d]
    _cleanable.clear()
    import gc
    gc.collect()
    if os.name == 'nt':
        try:
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.SetProcessWorkingSetSize(ctypes.c_void_p(k32.GetCurrentProcess()), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
        except Exception:
            pass


def lower_priority():
    """Run below normal priority, so scanning never competes with what the user is doing."""
    if os.name != 'nt':
        return
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = wintypes.HANDLE
        k32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)  # BELOW_NORMAL_PRIORITY_CLASS
    except Exception as e:
        print('priority:', repr(e))


def start_tray():
    """Show the notification-area icon (Windows only). Returns the Tray, or None."""
    if not traymod.available:
        return None
    t = traymod.Tray(STATIC / 'icon.ico', STATIC / 'icon-paused.ico', tray_command, tray_menu, commands=TRAY_COMMANDS)
    t.state_icons = {'busy': STATIC / 'icon-busy.ico', 'alert': STATIC / 'icon-alert.ico'}  # 2.6.0 #45
    if not t.start():
        print('tray icon could not be added')
        return None
    return t


STARTUP_LNK = Path(os.environ.get('APPDATA', '')) / 'Microsoft' / 'Windows' / 'Start Menu' / 'Programs' / 'Startup' / f'{APP_NAME}.lnk'
OLD_STARTUP_LNK = STARTUP_LNK.with_name('Desktop Watch.lnk')  # before the rename to DeskTrace
INSTANCE_FILE = DATA / 'instance.json'
NO_WINDOW = 0x08000000 if os.name == 'nt' else 0  # CREATE_NO_WINDOW: no console flash for helper processes


def pythonw():
    """The windowless interpreter next to the running one (falls back to the current one)."""
    w = Path(sys.executable).with_name('pythonw.exe')
    return str(w if w.exists() else sys.executable)


def make_shortcut(lnk, args, description):
    """Create a Windows shortcut that runs this app silently. Paths go through env vars to avoid quoting issues."""
    ps = ('$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:DW_LNK);$s.TargetPath=$env:DW_EXE;'
          '$s.Arguments=$env:DW_ARGS;$s.WorkingDirectory=$env:DW_DIR;$s.IconLocation=$env:DW_ICON;'
          '$s.Description=$env:DW_DESC;$s.Save()')
    env = {**os.environ, 'DW_LNK': str(lnk), 'DW_EXE': pythonw(), 'DW_ARGS': f'"{APP_DIR / "server.py"}" {args}'.strip(),
           'DW_DIR': str(APP_DIR), 'DW_ICON': f'{STATIC / "icon.ico"},0', 'DW_DESC': description}
    subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], env=env, check=True,
                   capture_output=True, creationflags=NO_WINDOW)


def set_autostart(on):
    if on:
        STARTUP_LNK.parent.mkdir(parents=True, exist_ok=True)
        make_shortcut(STARTUP_LNK, '--no-browser', f'{APP_NAME} - starts file monitoring in the background')
    elif STARTUP_LNK.exists():
        STARTUP_LNK.unlink()
    return STARTUP_LNK.exists()


def already_running(port):
    """True if this same installation (same data folder) is already serving on ``port``."""
    import urllib.request
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/ping', timeout=1) as r:
            info = json.loads(r.read())
        return info.get('app') == APP_ID and info.get('data', str(DATA)) == str(DATA)
    except Exception:
        return False


def port_taken(port):
    """True if something holds ``port``. Trying to claim it is instant, while asking a port nobody listens
    on makes Windows wait about half a second before it gives up (2.1.0: start-up was a second slower)."""
    import socket
    s = socket.socket()
    try:
        s.bind(('127.0.0.1', port))
        return False
    except OSError:
        return True
    finally:
        s.close()


def running_port(default):
    ports = [default]
    try:
        ports.insert(0, int(json.loads(INSTANCE_FILE.read_text('utf-8'))['port']))
    except (OSError, ValueError, KeyError):
        pass
    return next((p for p in dict.fromkeys(ports) if port_taken(p) and already_running(p)), None)


def quit_running():
    """Ask the running instance (of this data folder) to shut down cleanly; force it if it won't.
    The installer calls this before replacing program files."""
    import urllib.request
    try:
        info = json.loads(INSTANCE_FILE.read_text('utf-8'))
    except (OSError, ValueError):
        return False
    port, pid = info.get('port'), info.get('pid')
    if port and info.get('token') and already_running(port):
        try:
            req = urllib.request.Request(f'http://127.0.0.1:{port}/api/quit', data=b'{}', method='POST',
                                         headers={'X-Token': info['token'], 'Content-Type': 'application/json'})
            urllib.request.urlopen(req, timeout=3).read()
        except Exception:
            pass
        for _ in range(30):
            if not already_running(port):
                return True
            time.sleep(0.2)
    if pid and os.name == 'nt':  # an older version without a quit token, or one that is stuck
        subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, creationflags=NO_WINDOW)
    return True


def legacy_data_dirs():
    """Data folders of copies that ran before the installer existed (kept next to the program)."""
    out = []
    try:
        docs = known_folder(KNOWN_FOLDERS['documents']) if os.name == 'nt' else None
    except Exception:
        docs = None
    for base in dict.fromkeys(filter(None, [docs, str(Path.home() / 'Documents')])):
        out.append(Path(base) / 'Desktop Watch' / 'desktop_watch' / 'data')
    return out


def adopt_legacy_data():
    """First start of an installed copy: carry over the history of an earlier, uninstalled copy."""
    if (DATA / 'watch.db').exists() or os.environ.get('DESKTOP_WATCH_DATA') or APP_DIR in DATA.parents:
        return  # already has history, or a portable/test copy that keeps its own
    global INSTANCE_FILE
    old = OLD_DATA_ROOT / 'data'
    if (old / 'watch.db').exists() and old.resolve() != DATA.resolve():
        # Renamed from "Desktop Watch" to DeskTrace: move the history over (a rename — instant, no copy).
        mine, INSTANCE_FILE = INSTANCE_FILE, old / 'instance.json'
        quit_running()
        INSTANCE_FILE = mine
        DATA.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(20):
            try:
                if DATA.exists():
                    DATA.rmdir()  # only if empty; anything in it means "copy instead"
                os.replace(old, DATA)
                break
            except OSError:
                time.sleep(0.5)
        else:
            shutil.copytree(old, DATA, dirs_exist_ok=True, ignore=shutil.ignore_patterns('instance.json', '*.log'))
        try:
            OLD_DATA_ROOT.rmdir()
        except OSError:
            pass
        print(f'moved history from {old}')
        return
    for old in legacy_data_dirs():
        if old.resolve() == DATA.resolve() or not (old / 'watch.db').exists():
            continue
        mine, INSTANCE_FILE = INSTANCE_FILE, old / 'instance.json'
        quit_running()  # the old copy must not keep writing while we copy
        INSTANCE_FILE = mine
        DATA.mkdir(parents=True, exist_ok=True)
        shutil.copytree(old, DATA, dirs_exist_ok=True, ignore=shutil.ignore_patterns('instance.json', '*.log'))
        print(f'took over history from {old}')
        return


def migrate(store):
    """Bring stored data up to this version's shape. Each step runs once, in order, on upgrade."""
    v = store.meta('schema', 1)
    if v < 2:
        pass  # 1 -> 2: stars and notes tables, created by SCHEMA above; nothing to convert
    if v != SCHEMA_VERSION:
        store.set_meta('schema', SCHEMA_VERSION)
        print(f'data upgraded from schema {v} to {SCHEMA_VERSION}')
    store.set_meta('app_version', APP_VERSION)


def setup_log():
    """Under pythonw there is no console, so send output to data/desktop_watch.log instead."""
    if sys.stdout is not None and sys.stderr is not None:
        return
    log = DATA / 'desktop_watch.log'
    try:
        if log.stat().st_size > 1_000_000:
            log.replace(log.with_name('desktop_watch.old.log'))
    except OSError:
        pass
    sys.stdout = sys.stderr = RotatingLog(log)
    print(f'--- {time.strftime("%Y-%m-%d %H:%M:%S")} started (pid {os.getpid()})')


class RotatingLog:
    """The log, kept under about 1 MB (plus one older file) also while DeskTrace runs for weeks — it was
    only trimmed at start, so a message repeating every scan could grow it without end (2.1.0)."""
    LIMIT = 1_000_000

    def __init__(self, path):
        self.path, self.lock, self.n = path, threading.Lock(), 0
        self.f = open(path, 'a', encoding='utf-8', buffering=1)

    def write(self, s):
        with self.lock:
            n = self.f.write(s)
            self.n += 1
            if self.n % 100 == 0 and self.f.tell() > self.LIMIT:
                try:
                    self.f.close()
                    self.path.replace(self.path.with_name('desktop_watch.old.log'))
                except OSError:
                    pass
                self.f = open(self.path, 'a', encoding='utf-8', buffering=1)
            return n

    def flush(self):
        with self.lock:
            self.f.flush()

    def isatty(self):
        return False


def main():
    global DATA, BLOBS, SETTINGS_FILE, INSTANCE_FILE
    ap = argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--no-browser', action='store_true')
    ap.add_argument('--no-tray', action='store_true', help='do not show a notification-area icon')
    ap.add_argument('--data', help='use another data folder (e.g. for a separate test instance)')
    ap.add_argument('--show', metavar='FILE', help="open the page at this file's history (Explorer's right-click entry)")
    ap.add_argument('--show-deleted', metavar='FOLDER', help='open the files deleted in this folder (Explorer, 2.6.0 #4)')
    ap.add_argument('--quit', action='store_true', help='stop the running instance cleanly (used by the installer)')
    args = ap.parse_args()
    if args.data:
        DATA = Path(args.data).resolve()
        BLOBS, SETTINGS_FILE, INSTANCE_FILE = DATA / 'blobs', DATA / 'settings.json', DATA / 'instance.json'
    if args.quit:
        quit_running()
        return
    fragment = '#file=' + urllib.parse.quote(os.path.abspath(args.show)) if args.show else ''
    if args.show_deleted:
        fragment = '#deleted=' + urllib.parse.quote(os.path.abspath(args.show_deleted))

    if not args.data:
        adopt_legacy_data()
    if not running_port(args.port):
        try:
            apply_pending_import()  # a history brought from another PC (2.6.0 #44)
        except OSError as e:
            print('import not applied:', repr(e))
    BLOBS.mkdir(parents=True, exist_ok=True)
    setup_log()
    port = running_port(args.port)
    if port:
        print(f'{APP_NAME} is already running on port {port} — opening its window')
        if not args.no_browser or fragment:
            try:
                info = json.loads(INSTANCE_FILE.read_text('utf-8'))
                open_window(fragment, port, info['token'], info.get('pid'))
            except (OSError, ValueError, KeyError) as e:
                print('cannot reach the running copy:', repr(e))
        return

    lower_priority()
    settings = load_settings()
    if not SETTINGS_FILE.exists():
        try:  # first start: speak the language that was picked in the installer
            lang = (APP_DIR / 'install-lang.txt').read_text('ascii').strip()
            if lang in ('en', 'zh'):
                settings['lang'] = lang
        except OSError:
            pass
        save_settings(settings)
    App.store = Store(DATA / 'watch.db')
    migrate(App.store)
    App.hub = Hub()
    App.mon = Monitor(App.store, App.hub, settings)
    threading.Thread(target=check_integrity, daemon=True, name='integrity').start()
    App.mon._baseline_wake = threading.Event()
    App.updates = updmod.Updates(DATA, APP_DIR, APP_VERSION, on_found=update_found)
    if updmod.installed_layout(APP_DIR) and APP_DIR not in DATA.parents:
        try:
            if OLD_STARTUP_LNK.exists():  # renamed to DeskTrace: keep "start with Windows" under the new name
                OLD_STARTUP_LNK.unlink()
                set_autostart(True)
            if shell_menu_enabled():
                set_shell_menu(True)  # the right-click entry's label carries the name too
        except Exception as e:
            print('rename tidy-up:', repr(e))
    if App.updates.result:
        print(f'last update: {App.updates.result}')

    server = None
    for port in range(args.port, args.port + 20):
        try:
            server = QuietServer(('127.0.0.1', port), Handler)
            break
        except OSError:
            continue
    if server is None:
        sys.exit('No free port found.')
    server.daemon_threads = True
    App.server = server
    App.port = server.server_address[1]
    INSTANCE_FILE.write_text(json.dumps({'port': App.port, 'pid': os.getpid(), 'token': TOKEN,
                                         'version': APP_VERSION}), 'utf-8')

    App.tray = None if args.no_tray else start_tray()
    App.notifier = Notifier(App.tray.notify if App.tray else lambda title, text: None)
    App.mon.on_event = on_change
    if App.tray:
        App.mon.on_status = tray_status

    threading.Thread(target=App.mon.run, daemon=True, name='scanner').start()
    threading.Thread(target=App.mon.worker, daemon=True, name='worker').start()
    threading.Thread(target=App.mon.baseline, daemon=True, name='baseline').start()
    App.mon.housekeeping_wake = threading.Event()
    threading.Thread(target=App.mon.housekeeping, daemon=True, name='housekeeping').start()
    threading.Thread(target=find_licenses, daemon=True, name='licenses').start()

    print(f'{APP_NAME} {APP_VERSION} is monitoring: {", ".join(settings["roots"])}')
    print(f'Serving the app window on port {App.port}  tray={"on" if App.tray else "off"}  instant={winwatch.available}')
    if not args.no_browser or fragment:
        threading.Timer(0.3, lambda: print('opened in', open_window(fragment))).start()
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    if App.tray:
        App.tray.stop()  # removes the icon right away instead of leaving a ghost behind
    try:
        INSTANCE_FILE.unlink()
    except OSError:
        pass
    print(f'--- {time.strftime("%Y-%m-%d %H:%M:%S")} stopped')


if __name__ == '__main__':
    main()
