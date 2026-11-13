"""DeskTrace 2.7.0 — DeepSeek's 2.8.0 proposal ("can I still trust it after half a year?"), built into 2.7.0:
F2 protection overview, F3 retention preview, F4 restore from a backup folder (merge or replace, both reversible),
F5 weekly report, F6 adjustable mass-change alert, F7 a copy of the current content before any replace, F8 folder
time slice, F9 saved searches, F10 per-folder retention, F11 scheduled cleanup of safe items (off unless chosen),
F12 export of a file's versions with a manifest. F1 (the activity record) lives in features.py.
Nothing here deletes a user's file. ``N`` is server.py's namespace."""
import csv
import hashlib
import io
import json
import os
import shutil
import sqlite3
import threading
import time
from pathlib import Path

N = None
DAY = 86400


def F():
    return N['features']


def settings():
    return N['App'].mon.settings


# ---------------------------------------------------------------------------------------------- F10 + F3: retention
def folder_rules():
    """F10: per watched folder {'keep_days': d, 'max_gb': g}; a missing value inherits the global one."""
    rules = settings().get('folder_rules') or {}
    return {r: v for r, v in rules.items() if r in settings()['roots'] and isinstance(v, dict)}


def effective_days(root):
    r = folder_rules().get(root, {})
    return float(r['keep_days']) if r.get('keep_days') is not None else float(settings().get('keep_days') or 0)


def _range(root):
    lo = root.rstrip('\\') + '\\'
    return lo, lo[:-1] + chr(ord('\\') + 1)


def expiry_sql(at):
    """F3/F10: the condition "this change is older than its folder's limit at time ``at``" — the one condition both the
    preview and the real cleanup use, so the preview lists exactly what the cleanup removes. Noted versions and
    pinned files never match."""
    parts, args, out_cond, out_args = [], [], [], []
    for root in folder_rules():
        lo, hi = _range(root)
        d = effective_days(root)
        if d > 0:  # this folder's own limit (0 = keep forever)
            parts.append('(path >= ? AND path < ? AND ts < ?)')
            args += [lo, hi, at - d * DAY]
        out_cond.append('NOT (path >= ? AND path < ?)')
        out_args += [lo, hi]
    g = float(settings().get('keep_days') or 0)
    if g > 0:  # everything else: the global limit
        parts.append('(ts < ?' + ''.join(' AND ' + c for c in out_cond) + ')')
        args += [at - g * DAY] + out_args
    if not parts:
        return None, []
    return ('(' + ' OR '.join(parts) + ') AND id NOT IN (SELECT event_id FROM notes) AND path NOT IN (SELECT path FROM pins)'), args


def expire_old(store):
    """Called by Monitor.cleanup instead of its own age rule (F10: per-folder limits)."""
    where, args = expiry_sql(time.time())
    if not where:
        return 0
    return store.count('DELETE FROM events WHERE ' + where, args)


def retention_preview(days=7, limit=500):
    """F3: what the age limits will forget in the next ``days`` days: changes, kept copies that then go, space."""
    App = N['App']
    where, args = expiry_sql(time.time() + days * DAY)
    if not where:
        return {'ok': True, 'n': 0, 'items': [], 'bytes': 0, 'days': days, 'forever': True}
    rows = App.store.q(f'SELECT id, ts, kind, path, hash, prev_hash FROM events WHERE {where} ORDER BY ts', args)
    ids = {r['id'] for r in rows}
    # a copy goes only if no change that stays (or a current file) still needs it
    keep = {c[2] for c in App.mon.confirmed.values() if c[2]}
    for r in App.store.q('SELECT id, hash, prev_hash FROM events'):
        if r['id'] not in ids:
            keep |= {r['hash'], r['prev_hash']}
    freed = {}
    for r in rows:
        for h in (r['hash'], r['prev_hash']):
            if h and h not in keep and h not in freed:
                try:
                    freed[h] = App.store.blob_path(h).stat().st_size
                except OSError:
                    pass
    items = [{'id': r['id'], 'ts': r['ts'], 'kind': r['kind'], 'path': r['path'], 'name': os.path.basename(r['path']),
              'goes_on': r['ts'] + effective_days(App.mon.root_of(r['path']) or '') * DAY,
              'size': sum(freed.get(h, 0) for h in (r['hash'], r['prev_hash']) if h)} for r in rows[:limit]]
    protected = App.store.q('SELECT COUNT(*) n FROM events WHERE id IN (SELECT event_id FROM notes) OR path IN (SELECT path FROM pins)')[0]['n']
    return {'ok': True, 'n': len(rows), 'items': items, 'bytes': sum(freed.values()), 'days': days, 'protected': protected,
            'policy': policy_text()}


def policy_text():
    return {'keep_days': settings().get('keep_days') or 0, 'max_gb': settings().get('max_storage_gb') or 0,
            'folders': {r: {'keep_days': effective_days(r), 'max_gb': v.get('max_gb'), 'own': True} for r, v in folder_rules().items()}}


def folder_caps(store, blobs, keep):
    """F10: a folder's own space cap: the copies of its oldest versions go first until it fits (texts stay)."""
    App, freed = N['App'], 0
    for root, rule in folder_rules().items():
        cap = float(rule.get('max_gb') or 0) * 1024 ** 3
        if cap <= 0:
            continue
        lo, hi = _range(root)
        newest = {}
        for r in store.q('SELECT hash h, prev_hash p, ts FROM events WHERE path >= ? AND path < ?', (lo, hi)):
            for h in (r['h'], r['p']):
                if h:
                    newest[h] = max(newest.get(h, 0), r['ts'])
        sizes = {h: s for h, s, _, _ in blobs if h in newest}
        total = sum(sizes.values())
        for t, h in sorted((newest[h], h) for h in sizes):
            if total <= cap:
                break
            if h in keep:
                continue
            try:
                store.blob_path(h).unlink()
            except OSError:
                continue
            total -= sizes[h]
            freed += sizes[h]
    return freed


# ---------------------------------------------------------------------------------------------- F2: protection overview
_overview = {'key': None, 'res': None}


def overview():
    """F2, cached until the watched files or their versions change, or a minute passes (2.7.1 G4: every open looked at
    the disk once per watched file)."""
    App = N['App']
    key = (App.mon.gen, int(time.time() // 60))
    if _overview['key'] != key:
        _overview.update(key=key, res={**_overview_now(), 'at': time.time()})
    return _overview['res']


def _overview_now():
    """F2: how complete the history is: files watched, with a kept version, and why the others have none."""
    App = N['App']
    with App.mon.lock:
        items = list(App.mon.confirmed.items())
    by = {'kept': 0, 'big': 0, 'cloud': 0, 'text': 0, 'pending': 0}
    for p, c in items:
        by[N['protection'](p, c[0], c[2])] += 1
    week = time.time() - 7 * DAY
    flags = {f: App.store.q(f"SELECT COUNT(*) n FROM events WHERE ts >= ? AND (',' || flags || ',') LIKE '%,{f},%'", (week,))[0]['n']
             for f in ('lowdisk', 'nosnap', 'cloud')}
    locked = App.store.q("SELECT COUNT(*) n FROM events WHERE ts >= ? AND summary LIKE '%\"locked\"%'", (week,))[0]['n']
    last_clean = App.store.q("SELECT ts, size FROM action_log WHERE action IN ('clean', 'retention-cleanup', 'auto-clean') ORDER BY id DESC LIMIT 1")
    last_backup = App.store.q("SELECT ts, target FROM action_log WHERE action IN ('backup', 'export-history') AND result = 'ok' ORDER BY id DESC LIMIT 1")
    mass = App.store.q("SELECT COUNT(*) n FROM action_log WHERE action = 'mass-alert' AND ts >= ?", (week,))[0]['n']
    return {'ok': True, 'files': len(items), 'kept': by['kept'], 'why': {k: v for k, v in by.items() if k != 'kept'},
            'excluded_rules': len(settings().get('exclude_exts', [])) + len(settings().get('exclude_dirs', [])) + len(settings().get('exclude_paths', [])),
            'week': {'lowdisk': flags['lowdisk'], 'nocopy': flags['nosnap'], 'cloud': flags['cloud'], 'locked': locked, 'mass': mass},
            'warn': App.mon.warnings(), 'integrity': App.integrity,
            'last_clean': dict(last_clean[0]) if last_clean else None, 'last_backup': dict(last_backup[0]) if last_backup else None}


def files_by_protection(kind, offset=0, limit=200):
    """F2 click-through: the watched files in one "why no version" group (Files view)."""
    App = N['App']
    with App.mon.lock:
        items = [(p, c[0], c[1], c[2]) for p, c in App.mon.confirmed.items()]
    hit = sorted((x for x in items if N['protection'](x[0], x[1], x[3]) == kind), key=lambda x: -x[2])
    counts = N['change_counts']()
    return {'files': [N['file_row'](p, s, m, h, counts.get(p, 0)) for p, s, m, h in hit[offset:offset + limit]], 'total': len(hit)}


# ---------------------------------------------------------------------------------------------- F5: weekly report
def week_report(lang='en', end=None):
    """F5: the last 7 days, from the history and the activity record; nothing leaves the PC."""
    App = N['App']
    end = end or time.time()
    since = end - 7 * DAY
    q = lambda sql, a=(): App.store.q(sql, a)  # noqa: E731
    versions = q('SELECT COUNT(*) n FROM events WHERE ts >= ? AND ts < ? AND hash IS NOT NULL', (since, end))[0]['n']
    changes = q('SELECT COUNT(*) n FROM events WHERE ts >= ? AND ts < ?', (since, end))[0]['n']
    restores = q("SELECT COUNT(*) n FROM action_log WHERE ts >= ? AND ts < ? AND action IN ('restore', 'replace', 'restore-many', 'mass-restore', 'backup-restore') AND result = 'ok'", (since, end))[0]['n']
    freed = q("SELECT COALESCE(SUM(size), 0) s FROM action_log WHERE ts >= ? AND ts < ? AND action IN ('clean', 'auto-clean', 'retention-cleanup', 'delete-file', 'chat-clean') AND result = 'ok'", (since, end))[0]['s']
    unusual = q("SELECT COUNT(*) n FROM action_log WHERE ts >= ? AND ts < ? AND action IN ('mass-alert', 'integrity')", (since, end))[0]['n']
    deleted = q("SELECT COUNT(*) n FROM events WHERE ts >= ? AND ts < ? AND kind = 'deleted'", (since, end))[0]['n']
    per = {}
    for r in q('SELECT path FROM events WHERE ts >= ? AND ts < ?', (since, end)):
        d = os.path.dirname(r['path'])
        per[d] = per.get(d, 0) + 1
    top = sorted(per.items(), key=lambda x: -x[1])[:5]
    data = {'ok': True, 'from': since, 'to': end, 'versions': versions, 'changes': changes, 'deleted': deleted, 'restores': restores,
            'freed': freed, 'unusual': unusual, 'top': [{'folder': f, 'n': n} for f, n in top]}
    data['markdown'] = report_md(data, lang)
    return data


def report_md(d, lang):
    zh = lang == 'zh'
    T = lambda en, cn: cn if zh else en  # noqa: E731
    day = lambda ts: time.strftime('%Y-%m-%d', time.localtime(ts))  # noqa: E731
    lines = [f"# {T('DeskTrace weekly report', '桌迹保护周报')} · {day(d['from'])} – {day(d['to'])}", '',
             f"- {T('Changes recorded', '记录的变化')}: **{d['changes']}** ({T('deleted', '其中删除')} {d['deleted']})",
             f"- {T('Versions kept', '保存的版本')}: **{d['versions']}**",
             f"- {T('Restores', '恢复次数')}: **{d['restores']}**",
             f"- {T('Space freed by cleanups', '清理释放的空间')}: **{N['fmt_size'](d['freed'])}**",
             f"- {T('Unusual events (mass changes, damaged copies)', '异常事件（大量变化、损坏的副本）')}: **{d['unusual']}**", '',
             f"## {T('Folders that changed most', '变化最多的文件夹')}", '']
    lines += [f"{i + 1}. `{t['folder']}` — {t['n']}" for i, t in enumerate(d['top'])] or [T('No changes this week.', '本周没有变化。')]
    lines += ['', f"_{T('Made on this PC by DeskTrace', '由桌迹在本机生成')} {N['APP_VERSION']}; {T('nothing was uploaded.', '没有上传任何数据。')}_", '']
    return '\n'.join(lines)


def weekly_loop():
    """F5: Monday (or the first start after it), one quiet notification with the week's numbers — if switched on."""
    time.sleep(120)
    while True:
        try:
            App = N['App']
            if F().pref('weekly_report'):
                last = App.store.meta('week_report_at', 0)
                now = time.localtime()
                if time.time() - last > 6.5 * DAY and now.tm_wday == 0 and now.tm_hour >= 9:
                    App.store.set_meta('week_report_at', time.time())
                    d = week_report(N['ui_lang']())
                    if App.tray:
                        App.tray.notify(N['tr']('wk_title'), N['tr']('wk_text', v=d['versions'], r=d['restores'], f=N['fmt_size'](d['freed'])))
                    App.notify_hash = '#week'
        except Exception as e:
            print('weekly report:', repr(e))
        time.sleep(1800)


# ---------------------------------------------------------------------------------------------- F6: mass changes
def mass_limits():
    return F().pref('mass_n'), F().pref('mass_window')


def mass_quiet_seconds():
    return F().pref('mass_quiet')


# ---------------------------------------------------------------------------------------------- F7: a copy before replacing
def keep_current_first(target, force=False):
    """F7: before a file is replaced by an older version, make sure its current content is kept. Returns None when
    it is kept (now or already), else a refusal code: the replace then does not happen unless ``force``."""
    App = N['App']
    mon = App.mon
    with mon.lock:
        c = mon.confirmed.get(target)
    if c and c[2] and App.store.has_blob(c[2]):
        return None
    try:
        size = os.path.getsize(target)
    except OSError:
        return 'gone'
    if size > settings()['snapshot_max_mb'] * 2 ** 20:
        return None if force else 'tooBigToKeep'
    if N['disk_low']():
        return None if force else 'noSpaceToKeep'
    try:
        with open(target, 'rb') as fh:
            data = fh.read()
    except OSError:
        return None if force else 'cannotRead'
    h = N['content_hash'](data)
    try:
        App.store.put_blob(h, data)
    except OSError:
        return None if force else 'noSpaceToKeep'
    st = os.stat(target)
    with mon.lock:  # the current version is now the one kept: the replace records it as "before"
        mon.confirmed[target] = [st.st_size, st.st_mtime_ns, h]
        App.store.x('INSERT OR REPLACE INTO files VALUES(?,?,?,?)', (target, st.st_size, st.st_mtime_ns, h))
    F().log_action('keep-before-replace', target, size=size, source='auto')
    return None


# ---------------------------------------------------------------------------------------------- F8: folder time slice
def folder_slice(folder, since, until):
    """F8: what happened in ``folder`` (and below) between two times: per kind, net size, and per direct subfolder."""
    App = N['App']
    lo, hi = _range(folder)
    rows = App.store.q('SELECT kind, path, old_path, size, old_size FROM events WHERE ((path >= ? AND path < ?) OR (old_path >= ? AND old_path < ?))'
                       ' AND ts >= ? AND ts < ?', (lo, hi, lo, hi, since, until))
    kinds = {'created': 0, 'modified': 0, 'deleted': 0, 'renamed': 0}
    net, subs = 0, {}
    for r in rows:
        kinds[r['kind']] += 1
        if r['kind'] == 'created':
            net += r['size'] or 0
        elif r['kind'] == 'deleted':
            net -= r['old_size'] or 0
        elif r['kind'] == 'modified':
            net += (r['size'] or 0) - (r['old_size'] or 0)
        rel = os.path.relpath(r['path'], folder).split(os.sep)
        key = os.path.join(folder, rel[0]) if len(rel) > 1 and not rel[0].startswith('..') else folder
        subs[key] = subs.get(key, 0) + 1
    return {'ok': True, 'folder': folder, 'since': since, 'until': until, 'total': len(rows), 'kinds': kinds, 'net': net,
            'subfolders': [{'path': k, 'name': os.path.basename(k) if k != folder else '.', 'n': v} for k, v in sorted(subs.items(), key=lambda x: -x[1])[:12]]}


# ---------------------------------------------------------------------------------------------- F9 / F10 / F11 settings
SAFE_AUTO = ('temp', 'wintemp', 'edge', 'chrome', 'firefox', 'otherbrowsers', 'thumbs', 'crash', 'shaders')  # F11: never user files


def clean_structured(b, new):
    """Validate the structured 2.7.0 settings: saved searches (F9), folder rules (F10), scheduled cleanup (F11)."""
    if 'saved_searches' in b:
        out = []
        for s in (b['saved_searches'] or [])[:50]:
            if isinstance(s, dict) and str(s.get('name') or '').strip() and isinstance(s.get('filters'), dict):
                out.append({'name': str(s['name']).strip()[:80], 'v': 1, 'filters': {k: v for k, v in s['filters'].items()
                            if k in SEARCH_KEYS and isinstance(v, (str, int, float, bool, list))}})
        new['saved_searches'] = out
    if 'folder_rules' in b:
        rules = {}
        for root, v in (b['folder_rules'] or {}).items():
            if root in new['roots'] and isinstance(v, dict):
                r = {}
                if v.get('keep_days') not in (None, ''):
                    r['keep_days'] = max(0, min(3650, float(v['keep_days'])))
                if v.get('max_gb') not in (None, ''):
                    r['max_gb'] = max(0, min(1000, float(v['max_gb'])))
                if r:
                    rules[root] = r
        new['folder_rules'] = rules
    if 'auto_clean' in b:
        a = b['auto_clean'] or {}
        on = bool(a.get('on')) and bool(a.get('confirmed'))  # switched on only with the explicit confirmation step
        items = [i for i in (a.get('items') or []) if i in SAFE_AUTO]
        new['auto_clean'] = {'on': on and bool(items), 'every': a.get('every') if a.get('every') in ('week', 'month') else 'week',
                             'items': items, 'last': (new.get('auto_clean') or {}).get('last', 0)}


SEARCH_KEYS = {'kinds', 'cats', 'q', 'range', 'day', 'folder', 'starred', 'noted', 'gone', 'sort', 'big', 'where', 'since', 'until'}


def auto_clean_due(now=None):
    a = settings().get('auto_clean') or {}
    if not a.get('on') or not a.get('items'):
        return False
    every = 7 if a.get('every') == 'week' else 30
    return (now or time.time()) - float(a.get('last') or 0) >= every * DAY


def auto_clean_once(drive=None):
    """F11: clean the chosen safe items of the system drive once; every item is logged (source auto) and one
    notification sums it up. Personal files are never part of it (SAFE_AUTO only, deleted-for-good kinds)."""
    App, cl = N['App'], N['cleaner']
    a = settings().get('auto_clean') or {}
    drive = drive or cl.system_drive()
    total, done = 0, []
    for pid in a.get('items') or []:
        if pid not in SAFE_AUTO:
            continue
        r = cl.clean(drive, pid, None)
        F().log_action('auto-clean', f'{pid} ({drive})', 'ok' if 'code' not in r else r['code'], r.get('freed') or 0, source='auto')
        total += r.get('freed') or 0
        done.append(pid)
    a['last'] = time.time()
    settings()['auto_clean'] = a
    N['save_settings'](settings())
    N['find_cleanable'](drive, set(done))
    if App.tray and done:
        App.tray.notify(N['tr']('ac_title'), N['tr']('ac_text', f=N['fmt_size'](total), n=len(done)))
    return {'ok': True, 'freed': total, 'items': done}


def auto_clean_loop():
    time.sleep(300)
    while True:
        try:
            if auto_clean_due() and not N['on_battery']() and not N['user_busy_fullscreen']() and time.time() - N['App'].last_request > 300:
                auto_clean_once()
            F().rotate_actions(N['App'].store)
        except Exception as e:
            print('scheduled cleanup:', repr(e))
        time.sleep(3600)


# ---------------------------------------------------------------------------------------------- F4: restore from a backup folder
def _backup_root(path):
    p = Path(path)
    if (p / 'watch.db').exists():
        return p
    if (p / 'DeskTrace backup' / 'watch.db').exists():
        return p / 'DeskTrace backup'
    return None


def check_backup(path, sample=50):
    """F4 step 1: what a backup folder holds, and whether it can be used: format, database check, counts, a sample
    of kept copies read back against their names. A backup in a format this version cannot read is refused."""
    root = _backup_root(path)
    if not root:
        return {'ok': False, 'code': 'notBackup'}
    fmt = (root / 'FORMAT.txt').read_text('utf-8', 'replace') if (root / 'FORMAT.txt').exists() else ''
    try:
        con = sqlite3.connect(f'file:{root / "watch.db"}?mode=ro', uri=True)
        quick = con.execute('PRAGMA quick_check').fetchone()[0]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'events', 'files'} <= tables:
            con.close()
            return {'ok': False, 'code': 'wrongFormat'}
        events = con.execute('SELECT COUNT(*) FROM events').fetchone()[0]
        first_last = con.execute('SELECT MIN(ts), MAX(ts) FROM events').fetchone()
        try:
            schema = json.loads(con.execute("SELECT v FROM meta WHERE k='schema'").fetchone()[0])
            made_by = json.loads(con.execute("SELECT v FROM meta WHERE k='app_version'").fetchone()[0])
        except (TypeError, sqlite3.Error, ValueError):
            schema, made_by = 1, None
        con.close()
    except sqlite3.Error:
        return {'ok': False, 'code': 'damaged'}
    if quick != 'ok':
        return {'ok': False, 'code': 'damaged', 'detail': quick}
    if schema > N['SCHEMA_VERSION']:
        return {'ok': False, 'code': 'newerFormat', 'needs': made_by}
    names = [(e.name, e.path) for d in os.scandir(root / 'blobs') if d.is_dir() for e in os.scandir(d.path) if len(e.name) in (40, 64)] if (root / 'blobs').is_dir() else []
    bad, checked = [], 0
    step = max(1, len(names) // max(1, sample))
    for name, p in names[::step][:sample]:
        try:
            data = N['unpack_snapshot'](Path(p).read_bytes())
            ok = (hashlib.sha1 if len(name) == 40 else hashlib.sha256)(data).hexdigest() == name
        except (OSError, N['SnapshotError']):
            ok = False
        checked += 1
        if not ok:
            bad.append(name)
    if names and len(bad) == checked:
        return {'ok': False, 'code': 'wrongFormat'}
    return {'ok': True, 'root': str(root), 'format': fmt.strip(), 'events': events, 'snapshots': len(names), 'checked': checked, 'bad': len(bad),
            'db_bytes': (root / 'watch.db').stat().st_size, 'made': (root / 'watch.db').stat().st_mtime, 'made_by': made_by,
            'first': first_last[0], 'last': first_last[1], 'settings': (root / 'settings.json').exists()}


def merge_backup(path):
    """F4 "merge into the current history": the backup's changes that are not here yet are added (same time, kind,
    path and version = the same change), with their notes, pins and stars, and the kept copies that are missing.
    The current database is copied aside first; everything is one transaction (rolled back on any error)."""
    App = N['App']
    chk = check_backup(path)
    if not chk.get('ok'):
        return chk
    root = Path(chk['root'])
    aside = N['DATA'] / f'watch before merge {time.strftime("%Y-%m-%d %H-%M-%S")}.db'
    target = sqlite3.connect(str(aside))
    with App.store.lock:
        App.store.conn.backup(target)
    target.close()
    st = App.store
    added = notes = copied = 0
    with st.lock:
        con = st.conn
        try:
            con.execute('ATTACH DATABASE ? AS bk', (f'file:{root / "watch.db"}?mode=ro',))
        except sqlite3.OperationalError:
            con.execute('ATTACH DATABASE ? AS bk', (str(root / 'watch.db'),))
        try:
            con.execute('BEGIN')
            rows = con.execute('SELECT b.* FROM bk.events b WHERE NOT EXISTS (SELECT 1 FROM main.events e WHERE e.ts = b.ts AND e.kind = b.kind'
                               ' AND e.path = b.path AND COALESCE(e.hash, "") = COALESCE(b.hash, ""))').fetchall()
            cols = [c for c in rows[0].keys() if c != 'id'] if rows else []
            ids = {}
            for r in rows:
                cur = con.execute(f'INSERT INTO main.events({",".join(cols)}) VALUES({",".join("?" * len(cols))})', [r[c] for c in cols])
                ids[r['id']] = cur.lastrowid
                added += 1
            bk_notes = {r[0]: r for r in con.execute('SELECT event_id, text, ts FROM bk.notes').fetchall()}
            for old, new in ids.items():
                if old in bk_notes:
                    con.execute('INSERT OR REPLACE INTO main.notes(event_id, text, ts) VALUES(?,?,?)', (new, bk_notes[old][1], bk_notes[old][2]))
                    notes += 1
            for t in ('pins', 'stars'):
                con.execute(f'INSERT OR IGNORE INTO main.{t}(path) SELECT path FROM bk.{t}')
            con.execute('COMMIT')
        except Exception:
            con.execute('ROLLBACK')
            con.execute('DETACH DATABASE bk')
            raise
        con.execute('DETACH DATABASE bk')
    for d in (root / 'blobs').iterdir() if (root / 'blobs').is_dir() else []:
        for f in d.iterdir():
            dest = N['BLOBS'] / f.name[:2] / f.name
            if len(f.name) in (40, 64) and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dest)
                copied += 1
    App.mon.notes = {r['event_id']: r['text'] for r in st.q('SELECT event_id, text FROM notes')}
    App.mon.stars = {r['path'] for r in st.q('SELECT path FROM stars')}
    N['_pins']['at'] = 0
    App.mon.gen += 1
    App.hub.publish({'type': 'cleared'})
    report = verify_after(added)
    return {'ok': True, 'mode': 'merge', 'added': added, 'notes': notes, 'copied': copied, 'aside': str(aside), 'report': report}


def verify_after(added):
    App = N['App']
    q = App.store.q('PRAGMA quick_check')[0][0]
    hs = [r['h'] for r in App.store.q('SELECT hash h FROM events WHERE hash IS NOT NULL ORDER BY id DESC LIMIT 30')]
    ok = sum(1 for h in hs if App.store.has_blob(h) and (hashlib.sha1 if len(h) == 40 else hashlib.sha256)(App.store.read_blob(h)).hexdigest() == h)
    return {'database': q, 'events': App.store.q('SELECT COUNT(*) n FROM events')[0]['n'], 'added': added,
            'sample': len(hs), 'sample_ok': ok}


def stage_replace(path):
    """F4 "replace the current history": the backup is copied next to the data folder and takes its place at the next
    start; the current history is kept aside as "<data> before import <time>" (as 2.6.0's import), so it can be
    brought back. Settings come with the backup."""
    chk = check_backup(path)
    if not chk.get('ok'):
        return chk
    root = Path(chk['root'])
    pend = N['pending_dir']()
    shutil.rmtree(pend, ignore_errors=True)
    shutil.copytree(root, pend, ignore=shutil.ignore_patterns('README.txt', 'FORMAT.txt'))
    if not (pend / 'settings.json').exists():
        shutil.copy2(N['SETTINGS_FILE'], pend / 'settings.json')
    return {'ok': True, 'mode': 'replace', 'staged': True, 'events': chk['events'], 'snapshots': chk['snapshots']}


# ---------------------------------------------------------------------------------------------- F12: versions with a manifest
def bundle_plan(paths, since=0, until=None):
    """F12: every kept version of ``paths`` (files, or folders: every file in them), in a time range; with sizes."""
    App = N['App']
    until = until or time.time() + 1
    out = {}
    for p in paths:
        p = os.path.normpath(p)
        lo, hi = _range(p)
        rows = App.store.q("SELECT id, ts, kind, path, hash, prev_hash FROM events WHERE (path = ? OR (path >= ? AND path < ?)) AND ts >= ? AND ts < ? ORDER BY ts",
                           (p, lo, hi, since, until))
        for r in rows:
            h = r['prev_hash'] if r['kind'] == 'deleted' else r['hash']
            if h and App.store.has_blob(h):
                versions = out.setdefault(r['path'], [])
                if not versions or versions[-1]['hash'] != h:
                    versions.append({'id': r['id'], 'ts': r['ts'], 'hash': h, 'kind': r['kind'], 'note': App.mon.notes.get(r['id'], '')})
    total = 0
    for vs in out.values():
        for v in vs:
            try:
                raw = App.store.blob_path(v['hash']).read_bytes()
                v['size'] = len(N['unpack_snapshot'](raw)) if raw[:4] == N['SNAP_MAGIC'] else len(raw)
            except (OSError, N['SnapshotError']):
                v['size'] = 0
            total += v['size']
    return out, total


def bundle_estimate(paths, since=0, until=None):
    plan, total = bundle_plan(paths, since, until)
    dest = None
    return {'ok': True, 'files': len(plan), 'versions': sum(len(v) for v in plan.values()), 'bytes': total}


def run_bundle(paths, dest, since=0, until=None, progress=None):
    """F12: dest\\<file name>\\v1 <time>.ext … plus manifest.csv (version, time, note, algorithm, hash, size, original path).
    Resumable: a version already written with the right size is not written again; the manifest is written last."""
    App = N['App']
    plan, total = bundle_plan(paths, since, until)
    progress = progress or (lambda **k: None)
    done_b = written = skipped = 0
    rows = []
    names = {}
    for path, versions in sorted(plan.items()):
        stem, ext = os.path.splitext(os.path.basename(path))
        folder_name = stem + ext
        if folder_name.lower() in names and names[folder_name.lower()] != path:  # two files with one name: keep both
            folder_name = f'{stem}{ext} ({hashlib.sha1(path.encode()).hexdigest()[:6]})'
        names[folder_name.lower()] = path
        for i, v in enumerate(versions, 1):
            when = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime(v['ts']))
            out = Path(dest) / folder_name / f'v{i} {when}{ext}'
            if out.exists() and out.stat().st_size == v['size']:
                skipped += 1
            else:
                out.parent.mkdir(parents=True, exist_ok=True)
                App.store.copy_blob(v['hash'], str(out))
                written += 1
            done_b += v['size']
            progress(done=done_b, total=total, files=written + skipped)
            rows.append([os.path.relpath(out, dest), f'v{i}', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(v['ts'])), v['kind'], v['note'],
                         'SHA-1' if len(v['hash']) == 40 else 'SHA-256', v['hash'], v['size'], path])
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['file', 'version', 'time', 'change', 'note', 'algorithm', 'hash', 'size', 'original path'])
    w.writerows(rows)
    (Path(dest) / 'manifest.csv').write_text('﻿' + buf.getvalue(), 'utf-8', newline='')  # csv already ends lines with CRLF
    return {'ok': True, 'dest': dest, 'versions': len(rows), 'written': written, 'skipped': skipped, 'bytes': total}


# ---------------------------------------------------------------------------------------------- routes
def get_route(h, route, qs):
    App = N['App']
    if route == '/api/overview':  # F2
        return h.send_json(overview())
    if route == '/api/files-by-protection':  # F2 click-through
        return h.send_json(files_by_protection(qs.get('kind', ''), int(qs.get('offset', 0)), min(500, int(qs.get('limit', 200)))))
    if route == '/api/retention-preview':  # F3
        return h.send_json(retention_preview(max(1, min(90, int(qs.get('days', 7))))))
    if route == '/api/report/week':  # F5
        return h.send_json(week_report(qs.get('lang') or N['ui_lang']()))
    if route == '/api/folder-slice':  # F8
        f = os.path.normpath(qs.get('folder', ''))
        if not h.allowed_path(f):
            return h.send_json({'ok': False, 'code': 'notAllowed'})
        return h.send_json(folder_slice(f, float(qs.get('since') or 0), float(qs.get('until') or time.time() + 1)))
    if route == '/api/bundle':  # F12 progress
        return h.send_json(getattr(App, 'bundle', {}) or {})
    if route == '/api/actions.csv':  # F1 export
        import urllib.parse
        data = F().actions_csv([dict(r) for r in App.store.q('SELECT * FROM action_log ORDER BY id DESC LIMIT 100000')]).encode('utf-8')
        name = f'DeskTrace activity {time.strftime("%Y-%m-%d")}.csv'
        return h.send_bytes(data, 'text/csv; charset=utf-8', {'Content-Disposition': "attachment; filename*=UTF-8''" + urllib.parse.quote(name)})
    return False


def post_route(h, route, b):
    App = N['App']
    if route == '/api/backup-check':  # F4 step 1 (also picks the folder)
        p = str(b.get('path') or '') or N['pick_folder']()
        if not p:
            return h.send_json({'ok': False, 'code': 'cancelled'})
        return h.send_json({**check_backup(p), 'path': p})
    if route == '/api/backup-restore':  # F4 step 2: merge now, or replace at the next start
        p = str(b.get('path') or '')
        if not p:
            return h.send_json({'ok': False, 'code': 'notAllowed'})
        if b.get('mode') == 'merge':
            try:
                return h.send_json(merge_backup(p))
            except Exception as e:
                return h.send_json({'ok': False, 'code': 'mergeFailed', 'why': repr(e)[:200]})
        if b.get('mode') == 'replace':
            return h.send_json(stage_replace(p))
        return h.send_json({'ok': False, 'code': 'notAllowed'})
    if route == '/api/restart':  # F4: finish a replace now (the window comes back by itself)
        import subprocess
        import sys
        args = [N['pythonw'](), str(N['APP_DIR'] / 'server.py'), '--port', str(App.port), '--data', str(N['DATA'])]
        subprocess.Popen([N['pythonw'](), '-c', 'import subprocess, sys, time; time.sleep(3); subprocess.Popen(sys.argv[1:])', *args],
                         creationflags=N['NO_WINDOW'])
        h.send_json({'ok': True})
        threading.Thread(target=App.server.shutdown, daemon=True).start()
        return True
    if route == '/api/restore-bundle':  # F12
        paths = [os.path.normpath(str(p)) for p in (b.get('paths') or [])][:500]
        if not paths or not all(h.allowed_path(p) for p in paths):
            return h.send_json({'ok': False, 'code': 'notAllowed'})
        since, until = float(b.get('since') or 0), float(b.get('until') or 0) or None
        if b.get('estimate'):
            return h.send_json(bundle_estimate(paths, since, until))
        dest = str(b.get('dest') or '') or N['pick_folder']()
        if not dest:
            return h.send_json({'ok': False, 'code': 'cancelled'})
        if getattr(App, 'bundle', {}).get('state') == 'running':
            return h.send_json({'ok': False, 'code': 'busy'})
        App.bundle = {'state': 'running', 'done': 0, 'total': 0, 'dest': dest}

        def go():
            try:
                r = run_bundle(paths, dest, since, until, progress=lambda **k: App.bundle.update(k))
                App.bundle.update(state='done', result=r)
            except Exception as e:
                App.bundle.update(state='failed', error=repr(e)[:300])
        if b.get('wait'):
            go()
            return h.send_json({'ok': App.bundle['state'] == 'done', **App.bundle})
        threading.Thread(target=go, daemon=True, name='bundle').start()
        return h.send_json({'ok': True, 'dest': dest})
    if route == '/api/autoclean-now':  # F11: run the chosen items once now (the user's click)
        if not (settings().get('auto_clean') or {}).get('on'):
            return h.send_json({'ok': False, 'code': 'notAllowed'})
        return h.send_json(auto_clean_once())
    return False


def install(ns):
    global N
    N = ns
    threading.Thread(target=weekly_loop, daemon=True, name='weekly').start()
    threading.Thread(target=auto_clean_loop, daemon=True, name='autoclean').start()
