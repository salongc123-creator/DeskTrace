"""DeskTrace 2.7.0: the features of the 2.7.0 list and of the 2.8.0 proposal that the service side needs.

server.py calls ``install(globals())`` once at import; this module then extends the settings, wraps a few
of server.py's functions (by name, in its namespace, so server.py's own calls reach the new versions) and
answers the new routes through ``get_route`` / ``post_route``. Nothing here runs a destructive step on its own.
"""
import json
import os
import re
import threading
import time
from pathlib import Path

N = None   # server.py's namespace (a dict), set by install()

# ---------------------------------------------------------------------------------------------- settings
# One table for the 2.7.0 preferences: key -> (default, allowed values | (low, high) | bool)
PREFS = {
    'restore_suffix': ('time', ('time', 'n', 'tag')),       # M1-13: "name (restored <time>)" / "name (2)" / "name_DeskTrace"
    'notify_deleted': (True, bool),                          # M1-18: three independent switches
    'notify_lowdisk': (True, bool),
    'notify_changes': (False, bool),
    'sound': (True, bool),                                   # M1-19: system sound when a cleanup or restore is done
    'time_mode': ('rel', ('rel', 'abs')),                     # M2-10
    'search_history': (True, bool),                          # M1-5 (kept in this window only, never in the log)
    'hotkey': ('ctrl+alt+z', ('ctrl+alt+z', 'ctrl+shift+alt+z', 'off')),  # M2-22
    'dblclick': ('open', ('open', 'reveal', 'details')),     # M2-23
    'clipboard_hint': (False, bool),                         # M2-27 (default off)
    'zoom': (100, (100, 110, 125, 150)),                     # M1-4
    'topmost': (False, bool),                                # M1-2
    'compact': (False, bool),
    'split': ('auto', ('auto', 'side', 'stack')),            # M2-19
    'weekly_report': (True, bool),                           # F5
    'mass_n': (100, (20, 5000)),                             # F6: this many changes ...
    'mass_window': (10, (5, 600)),                           # ... within this many seconds
    'mass_quiet': (3600, (600, 3600, 86400)),                # "that was normal": quiet for 10 min / 1 h / 24 h
    'animations': (True, bool),                              # M2-12 (the system's "reduce motion" always wins)
    'seen_upto': (0, (0, 10 ** 15)),                         # M2-29: changes up to this id were seen ("Mark all read")
}


def pref(k):
    v = N['App'].mon.settings.get(k)
    return PREFS[k][0] if v is None else v


def clean_pref(k, v):
    default, rule = PREFS[k]
    if rule is bool:
        return bool(v)
    if k in ('mass_n', 'mass_window', 'seen_upto'):  # a range
        try:
            return max(rule[0], min(rule[1], int(v)))
        except (TypeError, ValueError):
            return default
    if isinstance(default, int):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return default
    return v if v in rule else default


def migrate_notify(s, saved):
    """2.6.0 had one notification choice (off / deleted / all); 2.7.0 has three switches (M1-18)."""
    if 'notify_deleted' not in saved:
        n = saved.get('notify', s.get('notify', 'deleted'))
        s['notify_deleted'] = n in ('deleted', 'all')
        s['notify_changes'] = n == 'all'
        s['notify_lowdisk'] = n != 'off'
    return s


def old_notify(s):
    """The 2.6.0 value kept in step, for older tools that read it."""
    return 'all' if s.get('notify_changes') else 'deleted' if s.get('notify_deleted') else 'off'


# ---------------------------------------------------------------------------------------------- M1-13 restore names
def restore_copy_name(target, lang):
    """The name a restored copy gets when the original name is taken; never an existing file (M1-13)."""
    style = pref('restore_suffix')
    if style == 'time':
        return _orig['restore_copy_name'](target, lang)
    stem, ext = os.path.splitext(target)
    lp = N['long_path']
    if style == 'n':
        n = 2
        while os.path.exists(lp(f'{stem} ({n}){ext}')):
            n += 1
        return f'{stem} ({n}){ext}'
    tag = '_桌迹找回' if lang == 'zh' else '_DeskTrace'
    out, n = f'{stem}{tag}{ext}', 2
    while os.path.exists(lp(out)):
        out, n = f'{stem}{tag} ({n}){ext}', n + 1
    return out


# ---------------------------------------------------------------------------------------------- notifications
def notifier_add(self, ev):
    """M1-18: deleted (and overwritten by a much smaller file) / ordinary changes, each its own switch;
    starred files always notify. A single deletion's notification opens its Restore dialog (S5.2)."""
    App, s = N['App'], N['App'].mon.settings
    if time.time() < float(s.get('mute_until') or 0) or N['user_busy_fullscreen']():
        return
    starred = ev.get('path') in App.mon.stars or ev.get('old_path') in App.mon.stars
    overwritten = ev['kind'] == 'modified' and (ev.get('old_size') or 0) > 4096 and (ev.get('size') or 0) < (ev.get('old_size') or 0) * 0.5
    wanted = (pref('notify_deleted') and (ev['kind'] == 'deleted' or overwritten)) or pref('notify_changes')
    if not (starred or wanted):
        return
    with self.lock:
        now = time.time()
        if not self.pending:
            self.first = now
        self.pending.append(ev)
        self.due = min(now + self.QUIET, self.first + self.MAX_WAIT)
        if not self.timer:
            self._start(self.due - now)


def notifier_flush(self):
    with self.lock:
        evs = list(self.pending)
    _orig['Notifier.flush'](self)
    if len(evs) == 1 and evs[0]['kind'] == 'deleted' and evs[0].get('has_prev_blob'):
        N['App'].notify_hash = f"#restore={evs[0]['id']}"   # S5.2: the click opens Restore for that file
    if evs:
        log_action('notify', len(evs), source='auto')


_disk_note = {'low': False, 'at': 0.0, 'free': None, 'free_at': 0.0}


def system_free():
    """Free space of the Windows drive, asked at most once a minute (M1-16)."""
    if time.time() - _disk_note['free_at'] > 60:
        try:
            import shutil
            _disk_note['free'] = shutil.disk_usage(N['cleaner'].system_drive()).free
        except OSError:
            _disk_note['free'] = None
        _disk_note['free_at'] = time.time()
    return _disk_note['free']


def lowdisk_watch():
    """M1-18: one notification when the drive with the history gets below 1 GB free (again after 6 hours)."""
    while True:
        time.sleep(30)
        try:
            App = N['App']
            if not getattr(App, 'mon', None):
                continue
            low = N['disk_low']()
            if low and not _disk_note['low'] and pref('notify_lowdisk') and time.time() - _disk_note['at'] > 6 * 3600:
                _disk_note['at'] = time.time()
                if App.tray:
                    App.tray.notify(N['tr']('low_title'), N['tr']('low_text', free=N['fmt_size'](N['_disk']['free'] or 0)))
                App.notify_hash = '#clean'
                App.hub.publish({'type': 'lowdisk', 'free': N['_disk']['free']})
            _disk_note['low'] = low
        except Exception as e:
            print('low disk watch:', repr(e))


def tray_status(status):
    """The tray tip (M1-16): files watched, changes today and free space on C:, kept short."""
    App, tr = N['App'], N['tr']
    day0 = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    today = App.store.q('SELECT COUNT(*) n FROM events WHERE ts >= ?', (day0,))[0]['n']
    if status['paused']:
        tip = (tr('tip_paused_until', t=time.strftime('%H:%M', time.localtime(status['pause_until'])))
               if status.get('pause_until') else tr('tip_paused'))
    else:
        tip = tr('tip', n=f"{status['files']:,}", c=today)
    free = system_free()
    if free is not None:
        tip += '\n' + tr('tip_free', d=N['cleaner'].system_drive()[:2], free=N['fmt_size'](free))
    if status.get('warn'):
        tip = tr('tip_warn') + '\n' + tip
    burst = sum(n for t0, n in getattr(App.mon, '_burst', []) if time.time() - t0 < 15)
    state = 'alert' if 'mass' in (status.get('warn') or []) else 'busy' if burst >= 20 else None
    App.tray.update(tooltip=tip, paused=status['paused'], state=state)


def tray_menu():
    """The Notifications submenu as three switches (M1-18) instead of one choice."""
    items, tr = _orig['tray_menu'](), N['tr']
    for i, it in enumerate(items):
        if it[0] == '>' and it[1] == tr('notify'):
            rest = [x for x in it[2] if not str(x[0]).startswith('notify-')]
            sw = [('notify-deleted', tr('n_sw_deleted'), pref('notify_deleted')), ('notify-lowdisk', tr('n_sw_lowdisk'), pref('notify_lowdisk')),
                  ('notify-all', tr('n_sw_changes'), pref('notify_changes'))]
            items[i] = ('>', it[1], sw + rest)
    return items


def tray_command(name):
    s = N['App'].mon.settings
    key = {'notify-deleted': 'notify_deleted', 'notify-lowdisk': 'notify_lowdisk', 'notify-all': 'notify_changes'}.get(name)
    if key:
        s[key] = not pref(key)
        s['notify'] = old_notify(s)
        N['save_settings'](s)
        log_action('setting', key, result='on' if s[key] else 'off')
        return
    if name == 'notify-off':
        s.update(notify_deleted=False, notify_lowdisk=False, notify_changes=False, notify='off')
        N['save_settings'](s)
        return
    return _orig['tray_command'](name)


# ---------------------------------------------------------------------------------------------- F1 action log
ACTION_KEEP_DAYS = 365      # F1: rotation — 12 months ...
ACTION_KEEP_ROWS = 100_000  # ... or 100,000 rows, whichever is less


def log_action(action, target='', result='ok', size=None, source='user', detail=None):
    """F1: one row per thing the user (or DeskTrace on its own) did. Never the text of a note."""
    try:
        App = N['App']
        App.store.x('INSERT INTO action_log(ts, action, target, result, size, source, detail) VALUES(?,?,?,?,?,?,?)',
                    (time.time(), action, str(target)[:1000], str(result)[:200], size, source,
                     json.dumps(detail, ensure_ascii=False)[:2000] if detail is not None else None))
    except Exception as e:
        print('action log:', repr(e))


LOGGED = {  # F1: the requests that change something, and the name they get in the activity record
    '/api/restore': 'restore', '/api/restore-many': 'restore-many', '/api/restore-as': 'save-version', '/api/clean/run': 'clean',
    '/api/clean/delete': 'delete-file', '/api/clean/undo': 'undo-clean', '/api/clean/last-undo': 'undo-clean', '/api/backup': 'backup',
    '/api/export': 'export-history', '/api/import': 'import-history', '/api/settings': 'settings', '/api/note': 'note', '/api/pin': 'pin',
    '/api/star': 'star', '/api/forget': 'forget-versions', '/api/cleanup': 'retention-cleanup', '/api/mass-restore': 'mass-restore',
    '/api/mass-dismiss': 'mass-dismiss', '/api/rename-back': 'rename-back', '/api/folder-at': 'folder-at', '/api/clear': 'clear-history',
    '/api/ignore-folder': 'ignore-folder', '/api/dup-link': 'hardlink', '/api/relocate': 'move-folder', '/api/relocate-back': 'move-back',
    '/api/clean/leftover-delete': 'delete-leftover', '/api/chat-media-clean': 'chat-clean', '/api/clean/fix-name': 'fix-name',
    '/api/clean/git-gc': 'git-gc', '/api/clean/cloud-free': 'cloud-free', '/api/clean/online': 'cloud-free', '/api/recycle': 'recycle-duplicate',
    '/api/shell-menu': 'setting', '/api/autostart': 'setting', '/api/pause': 'pause', '/api/root-gone': 'root-gone', '/api/update/apply': 'update',
    '/api/restore-bundle': 'export-versions', '/api/backup-restore': 'backup-restore', '/api/autoclean-now': 'auto-clean',
    '/api/actions/clear': 'clear-activity',
}


def after_post(h, route, b):
    """F1: after a request that changed something, one row: what, on what, how it went. Note text is never kept."""
    action = LOGGED.get(route)
    r = getattr(h, '_resp', None)
    if not action or not isinstance(r, dict) or r.get('cancelled') or r.get('code') == 'cancelled' or b.get('estimate'):
        return
    try:
        target = b.get('path') or b.get('dest') or b.get('folder') or b.get('drive') or ''
        if not target and b.get('id') is not None and str(b.get('id')).isdigit():
            row = N['App'].store.q('SELECT path FROM events WHERE id=?', (int(b['id']),))
            target = row[0]['path'] if row else ''
        if route == '/api/clean/run':
            target = f"{b.get('id')} ({b.get('drive')})"
        if action == 'restore' and b.get('replace'):
            action = 'replace'
        if route == '/api/note':
            action = 'note-add' if b.get('text') else 'note-remove'
        detail = None
        if route == '/api/settings':
            detail = sorted(k for k in b if k not in ('lang',))
            target = ', '.join(detail)[:300]
        elif route in ('/api/restore-many', '/api/rename-back'):
            detail = {'n': len(b.get('ids') or [])}
        result = 'ok' if r.get('ok', True) and not r.get('error') else (r.get('code') or 'failed')
        size = r.get('freed') or r.get('size') if isinstance(r.get('freed') or r.get('size'), (int, float)) else None
        log_action(action, target, result, size, 'user', detail)
    except Exception as e:
        print('action log:', repr(e))


def rotate_actions(store):
    store.x('DELETE FROM action_log WHERE ts < ?', (time.time() - ACTION_KEEP_DAYS * 86400,))
    store.x('DELETE FROM action_log WHERE id <= (SELECT MAX(id) FROM action_log) - ?', (ACTION_KEEP_ROWS,))


# ---------------------------------------------------------------------------------------------- M1-20 diagnostics bundle
def redact(text):
    """Every spelling of this Windows user's name in paths becomes <User> (M1-20)."""
    names = {os.environ.get('USERNAME', ''), os.path.basename(os.environ.get('USERPROFILE', '').rstrip('\\'))}
    for n in sorted((x for x in names if len(x) >= 2), key=len, reverse=True):
        text = re.sub(r'(?i)(?<=[\\/])' + re.escape(n) + r'(?=[\\/]|$|["\s])', '<User>', text)
    return text


def diag_bundle(handler):
    """What a support bundle holds: the last 300 log lines, the check-up and the settings — names taken out."""
    App, DATA = N['App'], N['DATA']
    try:
        lines = (DATA / 'desktop_watch.log').read_text('utf-8', 'replace').splitlines()[-300:]
    except OSError:
        lines = []
    d = handler.diagnostics()
    s = {k: v for k, v in App.mon.settings.items() if k not in ('dup_hidden', 'saved_searches')}
    parts = {'diagnostics.json': json.dumps(d, ensure_ascii=False, indent=1, default=str),
             'settings.json': json.dumps(s, ensure_ascii=False, indent=1),
             'log-last-300.txt': '\n'.join(lines)}
    return {k: redact(v) for k, v in parts.items()}


# ---------------------------------------------------------------------------------------------- M2-14 Recycle Bin look
WORK_EXTS = {'.psd', '.ai', '.dwg', '.sketch', '.fig', '.sln', '.csproj', '.py', '.js', '.ts', '.java', '.cpp', '.prproj', '.aep', '.blend'}


def bin_peek(drive, days=7):
    """What a look at the Recycle Bin of ``drive`` shows before emptying it (M2-14): total, and documents and
    folders deleted in the last ``days`` days (names only; nothing is opened or changed)."""
    cl = N['cleaner']
    size, n = cl.recycle_bin(drive)
    recent = []
    try:
        recs = cl._bin_records(drive)
    except Exception:
        recs = []
    since = time.time() - days * 86400
    for p, when, info, data in recs or []:
        ext = os.path.splitext(p)[1].lower()
        is_dir = os.path.isdir(data)
        if when >= since and (ext in cl.DOCS or ext in WORK_EXTS or is_dir):
            try:
                with open(info, 'rb') as fh:
                    item_size = int.from_bytes(fh.read(16)[8:16], 'little')
            except OSError:
                item_size = 0
            recent.append({'path': p, 'name': os.path.basename(p), 'deleted': when, 'size': item_size, 'dir': is_dir})
    recent.sort(key=lambda x: -x['deleted'])
    return {'ok': True, 'size': size, 'count': n, 'recent': recent[:20], 'recent_n': len(recent)}


# ---------------------------------------------------------------------------------------------- S1.2 heat
def space_heat(d, days):
    """S1.2: per folder of the space map, how it changed between the newest full scan and one about ``days``
    older: grew / shrank / stable, with the numbers (folders of 50 MB or more are in the scan history)."""
    App, cl = N['App'], N['cleaner']
    rows = [r for r in App.store.q('SELECT finished, serial, sizes FROM scan_history WHERE drive=? ORDER BY finished DESC', (d,))
            if r['serial'] == cl.volume_serial(d)]
    if len(rows) < 2:
        return {'ok': True, 'ready': False, 'scans': len(rows)}
    import zlib
    new = rows[0]
    old = next((r for r in rows[1:] if r['finished'] <= new['finished'] - days * 86400 + 3 * 3600), rows[-1])
    a, b = json.loads(zlib.decompress(old['sizes'])), json.loads(zlib.decompress(new['sizes']))
    out = {}
    for f in set(a) | set(b):
        was, now = a.get(f, 0), b.get(f, 0)
        delta = now - was
        stable = abs(delta) < max(20 * 2 ** 20, was * 0.02)
        out[f] = {'was': was, 'now': now, 'delta': delta, 'trend': 'stable' if stable else 'grew' if delta > 0 else 'shrank'}
    return {'ok': True, 'ready': True, 'from': old['finished'], 'to': new['finished'], 'folders': out}


# ---------------------------------------------------------------------------------------------- routes
def get_route(h, route, qs):
    """New GET routes: True when ``route`` was one of them (and answered)."""
    if N['trust'].get_route(h, route, qs) is not False:
        return True
    r = _get(h, route, qs)
    return r is not False


def post_route(h, route, b):
    if N['trust'].post_route(h, route, b) is not False:
        return True
    r = _post(h, route, b)
    return r is not False


def _get(h, route, qs):
    App = N['App']
    if route == '/api/diag-bundle':  # M1-20: what would go out, to read first
        return h.send_json({'ok': True, 'files': diag_bundle(h)})
    if route == '/api/clean/bin-peek':  # M2-14
        d = N['clean_drive'](qs.get('drive'))
        return h.send_json(bin_peek(d) if d else {'ok': False, 'code': 'notAllowed'})
    if route == '/api/clean/heat':  # S1.2
        d = N['clean_drive'](qs.get('drive'))
        return h.send_json(space_heat(d, max(1, min(90, int(qs.get('days', 7))))) if d else {'ok': False, 'code': 'notAllowed'})
    if route == '/api/actions':  # F1
        return h.send_json(actions_list(qs))
    ins = N['insights']
    if route in ('/api/clean/space-at', '/api/clean/forecast'):  # S1.1, S1.3
        d = N['clean_drive'](qs.get('drive'))
        if not d:
            return h.send_json({'ok': False, 'code': 'notAllowed'})
        return h.send_json(ins.space_at(d, max(0, min(90, int(qs.get('days', 0))))) if route.endswith('space-at') else ins.forecast(d))
    if route == '/api/nl':  # S2.1
        return h.send_json(ins.parse_query(qs.get('q', ''), App.mon.settings['roots']))
    if route == '/api/clipboard-path':  # M2-27
        return h.send_json({'path': clipboard_path()})
    if route == '/api/patch':  # M2-17
        text, code = make_patch(int(qs.get('id', 0)))
        if text is None:
            return h.send_json({'ok': False, 'code': code})
        r = App.store.q('SELECT path FROM events WHERE id=?', (int(qs['id']),))
        import urllib.parse
        name = os.path.splitext(os.path.basename(r[0]['path']))[0] + '.patch'
        return h.send_bytes(text.encode('utf-8'), 'text/x-diff; charset=utf-8', {'Content-Disposition': "attachment; filename*=UTF-8''" + urllib.parse.quote(name)})
    if route == '/api/diff-summary':  # S2.2
        return h.send_json(ins.diff_summary(int(qs.get('id', 0))))
    return False


def _post(h, route, b):
    App = N['App']
    if route == '/api/diag-bundle':  # M1-20: saved as a .zip where the user says (or ``dest`` in tests)
        import zipfile
        dest = str(b.get('dest') or '') or N['pick_save'](f'DeskTrace diagnostics {time.strftime("%Y-%m-%d %H-%M")}.zip')
        if not dest:
            return h.send_json({'ok': False, 'code': 'cancelled'})
        with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
            for name, text in diag_bundle(h).items():
                z.writestr(name, text)
        log_action('diagnostics', redact(dest))
        return h.send_json({'ok': True, 'path': dest})
    if route == '/api/note-many':  # M2-8: one note on several versions
        text = str(b.get('text') or '').strip()[:500]
        label = b.get('label') if b.get('label') in NOTE_LABELS else None
        ids = [int(i) for i in (b.get('ids') or [])][:2000]
        for eid in ids:
            set_note(eid, text, label)
        log_action('note', f'{len(ids)} versions', detail={'label': label})
        return h.send_json({'ok': True, 'n': len(ids)})
    if route == '/api/desktop-shortcut':  # M2-28: never a second one
        lnk = Path(os.environ.get('DESKTOP_WATCH_DESKTOP') or N['desktop_path']()) / f"{N['APP_NAME']}.lnk"
        if lnk.exists():
            return h.send_json({'ok': True, 'existed': True, 'path': str(lnk)})
        try:
            N['make_shortcut'](lnk, '', N['APP_NAME'])
        except Exception as e:
            return h.send_json({'ok': False, 'error': repr(e)[:200]})
        return h.send_json({'ok': lnk.exists(), 'existed': False, 'path': str(lnk)})
    if route == '/api/actions/clear':  # F1: the user empties the activity record
        App.store.x('DELETE FROM action_log')
        return h.send_json({'ok': True})
    return False


# ---------------------------------------------------------------------------------------------- M1-15 note labels
NOTE_LABELS = ('final', 'draft', 'important', 'sent')


def set_note(eid, text, label=None):
    App = N['App']
    if text or label:
        App.store.x('INSERT OR REPLACE INTO notes(event_id, text, ts, label) VALUES(?,?,?,?)', (eid, text, time.time(), label))
        App.mon.notes[eid] = text
        _labels[eid] = label
    else:
        App.store.x('DELETE FROM notes WHERE event_id=?', (eid,))
        App.mon.notes.pop(eid, None)
        _labels.pop(eid, None)
    try:
        App.hub.publish({'type': 'update', 'event': App.mon.event_dict(eid)})
    except Exception:
        pass


_labels = {}


def event_dict(self, eid=None, row=None, memo=None):
    d = _orig['Monitor.event_dict'](self, eid, row, memo)
    d['label'] = _labels.get(d['id'])
    return d


def actions_list(qs):
    App = N['App']
    where, args = [], []
    if qs.get('action'):
        where.append('action = ?')
        args.append(qs['action'])
    if qs.get('source'):
        where.append('source = ?')
        args.append(qs['source'])
    if qs.get('since'):
        where.append('ts >= ?')
        args.append(float(qs['since']))
    sql = 'SELECT * FROM action_log' + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY id DESC LIMIT ?'
    rows = [dict(r) for r in App.store.q(sql, args + [min(int(qs.get('limit', 300)), 100000)])]
    if qs.get('format') == 'csv':
        return {'csv': actions_csv(rows)}
    return {'ok': True, 'items': rows, 'total': App.store.q('SELECT COUNT(*) n FROM action_log')[0]['n']}


def actions_csv(rows):
    import csv
    import io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(['time', 'action', 'target', 'result', 'size', 'source'])
    for r in rows:
        w.writerow([time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r['ts'])), r['action'], r['target'], r['result'], r['size'] or '', r['source']])
    return '﻿' + buf.getvalue()   # with a BOM: Excel reads Chinese paths right


# ---------------------------------------------------------------------------------------------- batch 3 helpers
def save_target(b):
    """M2-18: the folder a "Save a copy to" choice means (Desktop / next to the original / Downloads), or None."""
    tg = b.get('target')
    if tg == 'desktop':
        return os.environ.get('DESKTOP_WATCH_DESKTOP') or N['desktop_path']()
    if tg == 'downloads':
        try:
            return N['known_folder'](N['KNOWN_FOLDERS']['downloads'])
        except Exception:
            return os.path.join(os.environ.get('USERPROFILE', ''), 'Downloads')
    if tg == 'beside':
        p = str(b.get('path') or '')
        if p and N['Handler'].allowed_path(None, p) and os.path.isdir(os.path.dirname(p)):
            return os.path.dirname(p)
    return None


def eco_qos_thread():
    """M2-26: mark the calling (background) thread for Windows' efficiency mode — EcoQoS, Windows 11; elsewhere a
    no-op. Only scan / hash / index threads call this; the threads that answer the window never do."""
    import ctypes

    class TPT(ctypes.Structure):  # THREAD_POWER_THROTTLING_STATE
        _fields_ = [('Version', ctypes.c_ulong), ('ControlMask', ctypes.c_ulong), ('StateMask', ctypes.c_ulong)]
    try:
        k32 = ctypes.windll.kernel32
        k32.GetCurrentThread.restype = ctypes.c_void_p
        st = TPT(1, 1, 1)  # THREAD_POWER_THROTTLING_EXECUTION_SPEED on
        ok = k32.SetThreadInformation(ctypes.c_void_p(k32.GetCurrentThread()), 3, ctypes.byref(st), ctypes.sizeof(st))  # ThreadPowerThrottling
        _eco['ok' if ok else 'no'] += 1
        return bool(ok)
    except Exception:
        _eco['no'] += 1
        return False


_eco = {'ok': 0, 'no': 0}


def clipboard_path():
    """M2-27: a file path on the clipboard right now, if it is one DeskTrace knows. Read only when the user switched
    it on and the window asks; never stored or logged."""
    if not pref('clipboard_hint'):
        return None
    import ctypes
    u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
    u32.GetClipboardData.restype = ctypes.c_void_p
    k32.GlobalLock.restype = ctypes.c_void_p
    text = None
    if u32.IsClipboardFormatAvailable(13) and u32.OpenClipboard(None):  # CF_UNICODETEXT
        try:
            h = u32.GetClipboardData(13)
            p = k32.GlobalLock(ctypes.c_void_p(h)) if h else None
            if p:
                text = ctypes.wstring_at(p)[:600]
                k32.GlobalUnlock(ctypes.c_void_p(h))
        finally:
            u32.CloseClipboard()
    if not text:
        return None
    cand = text.strip().strip('"').strip()
    if '\n' in cand or len(cand) > 520 or not re.match(r'^[A-Za-z]:\\', cand):
        return None
    cand = os.path.normpath(cand)
    return cand if os.path.isfile(cand) and N['Handler'].allowed_path(None, cand) else None


def make_patch(eid):
    """M2-17: one change of a text file as a unified diff that `git apply` accepts (from the kept copies, byte-exact)."""
    App = N['App']
    r = App.store.q('SELECT * FROM events WHERE id=?', (eid,))
    if not r or r[0]['kind'] != 'modified':
        return None, 'noDiff'
    r = r[0]
    if not (App.store.has_blob(r['hash']) and App.store.has_blob(r['prev_hash'])):
        return None, 'noSnapshot'
    try:
        a, b = App.store.read_blob(r['prev_hash']).decode('utf-8'), App.store.read_blob(r['hash']).decode('utf-8')
    except UnicodeDecodeError:
        return None, 'notText'
    import difflib
    name = os.path.basename(r['path'])
    al, bl = a.splitlines(keepends=True), b.splitlines(keepends=True)
    out = []
    for line in difflib.unified_diff(al, bl, 'a/' + name, 'b/' + name):
        out.append(line)
        if not line.endswith('\n'):
            out.append('\n\\ No newline at end of file\n')
    return ''.join(out), None


def bin_paths():
    """Original paths of what is in the Recycle Bins of the drives with watched folders (M2-11)."""
    cl, out = N['cleaner'], set()
    if os.environ.get('DESKTOP_WATCH_TEST_BIN'):  # tests: a scratch list instead of the real Recycle Bin
        return {os.path.normcase(p) for p in json.loads(os.environ['DESKTOP_WATCH_TEST_BIN'])}
    for d in {cl.drive_of(r) for r in N['App'].mon.settings['roots']}:
        try:
            out |= {os.path.normcase(p) for p, *_ in cl._bin_records(d)}
        except Exception:
            pass
    return out


def event_filter(qs):
    where, args = _orig['event_filter'](qs)
    if qs.get('big'):  # M2-9: only changes of 1 KB or more
        where.append('ABS(COALESCE(size, 0) - COALESCE(old_size, 0)) >= 1024')
    if qs.get('inbin') or qs.get('snaponly'):  # M2-11: deleted files still in the Recycle Bin / that only DeskTrace has
        bins = sorted(bin_paths())[:5000]
        where.append("kind = 'deleted'")
        if qs.get('inbin'):
            where.append(f"LOWER(path) IN ({','.join('?' * len(bins)) or 'NULL'})")
            args += bins
        else:
            where.append('prev_hash IS NOT NULL AND path NOT IN (SELECT path FROM files)')
            if bins:
                where.append(f"LOWER(path) NOT IN ({','.join('?' * len(bins))})")
                args += bins
    return where, args


def events(self, qs):
    """M2-7: the change list by size of the change or by how often the file changed (pages by offset)."""
    sort = qs.get('sort')
    if sort not in ('size', 'freq'):
        return _orig['events'](self, qs)
    App = N['App']
    where, args = event_filter({k: v for k, v in qs.items() if k != 'before'})
    w = (' WHERE ' + ' AND '.join(where)) if where else ''
    limit, offset = min(int(qs.get('limit', 150)), 500), int(qs.get('offset', 0))
    if sort == 'size':
        sql = f'SELECT * FROM events{w} ORDER BY ABS(COALESCE(size, 0) - COALESCE(old_size, 0)) DESC, id DESC LIMIT ? OFFSET ?'
    else:
        sql = (f'SELECT events.*, c.n FROM events JOIN (SELECT path p, COUNT(*) n FROM events GROUP BY path) c ON c.p = events.path{w}'
               ' ORDER BY c.n DESC, events.path, id DESC LIMIT ? OFFSET ?')
    rows = App.store.q(sql, args + [limit, offset])
    memo = {}
    out = []
    for r in rows:
        d = App.mon.event_dict(row={k: r[k] for k in r.keys() if k != 'n'}, memo=memo)
        if sort == 'freq':
            d['freq'] = r['n']
        out.append(d)
    return {'events': out, 'more': len(rows) == limit}


# ---------------------------------------------------------------------------------------------- install
_orig = {}
SCHEMA_270 = """
CREATE TABLE IF NOT EXISTS action_log(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, action TEXT, target TEXT, result TEXT,
  size INTEGER, source TEXT, detail TEXT);
CREATE INDEX IF NOT EXISTS al_ts ON action_log(ts);
"""


def migrate(store):
    """2.7.0 data: the action log (F1) and a colour label on notes (M1-15). Older data stays readable."""
    store.conn.executescript(SCHEMA_270)
    cols = {r[1] for r in store.q('PRAGMA table_info(notes)')}
    if 'label' not in cols:
        with store.lock:
            store.conn.execute('ALTER TABLE notes ADD COLUMN label TEXT')
            store.conn.commit()
    _labels.update({r['event_id']: r['label'] for r in store.q('SELECT event_id, label FROM notes WHERE label IS NOT NULL')})
    rotate_actions(store)


def install(ns):
    global N
    N = ns
    for k, (default, _) in PREFS.items():
        ns['DEFAULTS'].setdefault(k, default)
    for name in ('restore_copy_name', 'tray_menu', 'tray_command', 'load_settings', 'migrate'):
        _orig[name] = ns[name]
    _orig['Notifier.flush'] = ns['Notifier'].flush
    _orig['Monitor.event_dict'] = ns['Monitor'].event_dict
    ns['restore_copy_name'] = restore_copy_name
    ns['tray_menu'] = tray_menu
    ns['tray_command'] = tray_command
    ns['tray_status'] = tray_status
    ns['Notifier'].add = notifier_add
    ns['Notifier'].flush = notifier_flush
    ns['Monitor'].event_dict = event_dict
    ns['TRAY_COMMANDS'].append('notify-lowdisk')
    _orig['event_filter'] = ns['Handler'].event_filter
    ns['Handler'].event_filter = staticmethod(event_filter)
    _orig['events'] = ns['Handler'].events
    ns['Handler'].events = events

    def load_settings():
        s = _orig['load_settings']()
        try:
            saved = json.loads(ns['SETTINGS_FILE'].read_text('utf-8'))
        except (OSError, ValueError):
            saved = {}
        return migrate_notify(s, saved)
    ns['load_settings'] = load_settings

    def migrate_all(store):
        _orig['migrate'](store)
        migrate(store)
    ns['migrate'] = migrate_all
    threading.Thread(target=lowdisk_watch, daemon=True, name='lowdisk').start()
    ns['insights'].N = ns
    threading.Thread(target=sample_loop, daemon=True, name='disk-samples').start()


def sample_loop():
    """S1.3: the used space of each drive, once a day (checked hourly; a few calls, no disk reading)."""
    time.sleep(60)
    while True:
        try:
            if getattr(N['App'], 'store', None) is not None:
                N['insights'].sample_drives()
        except Exception as e:
            print('disk samples:', repr(e))
        time.sleep(3600)


def update_settings_extra(b, new):
    """The 2.7.0 preferences in a settings change (validated); returns the keys that changed."""
    changed = []
    N['trust'].clean_structured(b, new)  # F9 saved searches, F10 folder rules, F11 scheduled cleanup
    for k in PREFS:
        if k in b:
            v = clean_pref(k, b[k])
            if new.get(k) != v:
                changed.append(k)
            new[k] = v
    if any(k.startswith('notify_') for k in changed):
        new['notify'] = old_notify(new)
    if 'hotkey' in changed and getattr(N['App'], 'tray', None):  # M2-22
        N['App'].tray.set_hotkey(new['hotkey'])
    if b.get('notify') in ('off', 'deleted', 'all') and not any(k.startswith('notify_') for k in b):  # the 2.6.0 way, still understood
        migrate_notify(new, {'notify': b['notify']})
    return changed
