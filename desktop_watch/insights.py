"""DeskTrace 2.7.0, batch 2 ("data put together"): space playback over the kept scans (S1.1), the "drive full in
N–M days" forecast (S1.3), plain-language search turned into filters (S2.1) and structured change summaries for
Word / Markdown / PowerPoint / Excel (S2.2). Read-only: nothing here changes a file. ``N`` is server.py's namespace."""
import datetime as dt
import json
import math
import os
import re
import time
import zlib

N = None

# ---------------------------------------------------------------------------------------------- S1.1 scan history
DAY = 86400
KEEP_DAYS = 90


def thin_history(store, drive):
    """S1.1: keep every full scan of the last 2 days, then one per calendar day up to 90 days (the newest of each
    day), nothing older. 2.6.0 kept the last 30 scans (~15 days at one pre-scan per 12 h)."""
    rows = store.q('SELECT finished FROM scan_history WHERE drive=? ORDER BY finished DESC', (drive,))
    now, seen, drop = time.time(), set(), []
    for r in rows:
        f = r['finished']
        if now - f > KEEP_DAYS * DAY:
            drop.append(f)
            continue
        if now - f <= 2 * DAY:
            continue
        day = time.strftime('%Y-%m-%d', time.localtime(f))
        if day in seen:
            drop.append(f)
        seen.add(day)
    for f in drop:
        store.x('DELETE FROM scan_history WHERE drive=? AND finished=?', (drive, f))
    return len(drop)


def history_rows(drive):
    App, cl = N['App'], N['cleaner']
    serial = cl.volume_serial(drive)
    return [r for r in App.store.q('SELECT finished, serial, sizes FROM scan_history WHERE drive=? ORDER BY finished DESC', (drive,))
            if r['serial'] == serial]


def space_at(drive, days):
    """S1.1: the folder sizes (50 MB or more) of the kept full scan nearest to ``days`` days ago, and how far back the
    kept scans reach. ``days`` 0 = the newest."""
    rows = history_rows(drive)
    if not rows:
        return {'ok': True, 'ready': False, 'scans': 0}
    want = rows[0]['finished'] - days * DAY
    pick = min(rows, key=lambda r: abs(r['finished'] - want))
    oldest = rows[-1]['finished']
    exact = abs(pick['finished'] - want) <= 1.5 * DAY
    return {'ok': True, 'ready': True, 'exact': exact or days == 0, 'at': pick['finished'], 'oldest': oldest, 'scans': len(rows),
            'days_back': round((rows[0]['finished'] - oldest) / DAY, 1), 'sizes': json.loads(zlib.decompress(pick['sizes']))}


# ---------------------------------------------------------------------------------------------- S1.3 forecast
def sample_drives():
    """Once a day per drive: used and total bytes (meta 'disk_samples'), for the forecast. Kept 90 days."""
    App, cl = N['App'], N['cleaner']
    samples = App.store.meta('disk_samples', {}) or {}
    day = time.strftime('%Y-%m-%d')
    for d in cl.drives():
        s = samples.setdefault(d['drive'], {})
        s[day] = [d['used'], d['total']]
        for k in sorted(s)[:-KEEP_DAYS]:
            del s[k]
    App.store.set_meta('disk_samples', samples)


def forecast(drive, samples=None):
    """S1.3: "full in about N–M days", only with 7 or more days of samples over at least 7 days and a steady
    rise (linear fit, R² ≥ 0.6, rising). The range is the 80 % band of the slope. Otherwise nothing is promised."""
    if samples is None:
        samples = (N['App'].store.meta('disk_samples', {}) or {}).get(drive, {})
    pts = sorted((dt.date.fromisoformat(k).toordinal(), v[0], v[1]) for k, v in samples.items())
    if len(pts) < 7 or pts[-1][0] - pts[0][0] < 7:
        return {'ok': True, 'show': False, 'why': 'few', 'days': len(pts)}
    xs, ys = [p[0] - pts[0][0] for p in pts], [p[1] for p in pts]
    n, mx, my = len(xs), sum(xs) / len(xs), sum(ys) / len(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    res = [y - (my + slope * (x - mx)) for x, y in zip(xs, ys)]
    sst = sum((y - my) ** 2 for y in ys) or 1
    r2 = 1 - sum(r * r for r in res) / sst
    if slope <= 0 or r2 < 0.6:
        return {'ok': True, 'show': False, 'why': 'unsteady' if slope > 0 else 'notGrowing', 'days': n, 'r2': round(r2, 2)}
    se = math.sqrt(sum(r * r for r in res) / max(1, n - 2) / sxx)
    free = pts[-1][2] - pts[-1][1]
    hi_slope, lo_slope = slope + 1.3 * se, max(slope - 1.3 * se, slope * 0.25)
    lo, hi = free / hi_slope, free / lo_slope
    if lo > 730:
        return {'ok': True, 'show': False, 'why': 'far', 'days': n}
    return {'ok': True, 'show': True, 'lo': max(1, math.floor(lo)), 'hi': math.ceil(min(hi, 3650)), 'per_day': slope, 'days': n, 'r2': round(r2, 2)}


# ---------------------------------------------------------------------------------------------- S2.1 plain-language search
KINDS = [('deleted', r'\b(deleted|removed|gone)\b|删除的?|删掉的?|被删的?'), ('modified', r'\b(changed|modified|edited)\b|改过的?|修改(过)?的?|编辑过的?'),
         ('created', r'\b(new|created|added)\b|新建的?|新增的?'), ('renamed', r'\b(renamed|moved)\b|重命名的?|改名的?|移动过?的?')]
CATS = [('excel', r'\b(excel|spreadsheets?|xlsx?|sheets?)\b|表格|电子表格'), ('word', r'\b(?:word|docx?)(?:\s+documents?)?\b|\bdocuments?\b|文档|word'),
        ('ppt', r'\b(powerpoint|pptx?|slides?|presentations?)\b|幻灯片|演示文稿|ppt'), ('pdf', r'\bpdfs?\b|pdf'),
        ('image', r'\b(pictures?|images?|photos?|screenshots?)\b|图片|照片|截图'), ('markdown', r'\b(markdown|md)\b'),
        ('text', r'\b(text|txt)\s*files?\b|文本'), ('code', r'\b(code|scripts?)\b|代码')]
TIMES = [('today', r'\btoday\b|今天|今日'), ('yesterday', r"\byesterday('s)?\b|昨天|昨日"), ('thisweek', r'\bthis week\b|本周|这周|这星期'),
         ('lastweek', r'\blast week\b|上周|上星期|上个星期'), ('thismonth', r'\bthis month\b|本月|这个月'), ('lastmonth', r'\blast month\b|上个?月'),
         ('days', r'\b(?:last|past) (\d{1,3}) days\b|最近\s*(\d{1,3})\s*天|(\d{1,3})\s*天内|\b(\d{1,3}) days ago\b')]
FILLER = r"\b(files?|the|on|in|from|my|that|were|was|which|i|of|all|show|me|find|s)\b|的|里|中|上|在|文件|所有|哪些|找|给我|看看|一下"


def time_span(key, n=None, now=None):
    now = dt.datetime.fromtimestamp(now or time.time())
    d0 = dt.datetime(now.year, now.month, now.day)
    ts = lambda d: d.timestamp()  # noqa: E731
    if key == 'today':
        return ts(d0), None
    if key == 'yesterday':
        return ts(d0 - dt.timedelta(days=1)), ts(d0)
    if key == 'thisweek':
        return ts(d0 - dt.timedelta(days=d0.weekday())), None
    if key == 'lastweek':
        start = d0 - dt.timedelta(days=d0.weekday() + 7)
        return ts(start), ts(start + dt.timedelta(days=7))
    if key == 'thismonth':
        return ts(d0.replace(day=1)), None
    if key == 'lastmonth':
        first = d0.replace(day=1)
        prev = (first - dt.timedelta(days=1)).replace(day=1)
        return ts(prev), ts(first)
    return ts(d0 - dt.timedelta(days=int(n))), None


def folder_words(roots):
    """Words that name a watched folder or a known place: "Desktop", "桌面", "Downloads", "下载", the folder's own name."""
    out = []
    known = {'desktop': r'\bdesktop\b|桌面', 'downloads': r'\bdownloads?\b|下载', 'documents': r'\bdocuments folder\b|我的文档|文档文件夹',
             'pictures': r'\bpictures folder\b|图片文件夹'}
    for r in roots:
        name = os.path.basename(r.rstrip('\\')).lower()
        pat = known.get(name, r'\b' + re.escape(name) + r'\b' if re.match(r'^[\w .-]+$', name) else re.escape(name))
        out.append((r, pat))
    return out


def parse_query(q, roots=(), now=None):
    """S2.1: a plain-language query as chips (kind, file type, time span, folder) plus what is left of the words,
    which is searched as a name (and offered as content search when nothing matches). Nothing is guessed when no
    word is recognised: the query is then searched exactly as typed."""
    text, chips = ' ' + q.strip() + ' ', []

    def take(pattern):
        nonlocal text
        m = re.search(pattern, text, re.I)
        if m:
            text = text[:m.start()] + ' ' + text[m.end():]
        return m
    for key, pat in TIMES:
        m = take(pat)
        if m:
            n = next((g for g in m.groups() if g), None) if key == 'days' else None
            since, until = time_span(key, n, now)
            chips.append({'type': 'time', 'value': key, 'n': int(n) if n else None, 'since': since, 'until': until})
            break
    for key, pat in KINDS:
        if take(pat):
            chips.append({'type': 'kind', 'value': key})
    for key, pat in CATS:
        if take(pat):
            chips.append({'type': 'cat', 'value': key})
    for root, pat in folder_words(roots):
        if take(pat):
            chips.append({'type': 'folder', 'value': root, 'name': os.path.basename(root.rstrip('\\'))})
            break
    rest = re.sub(FILLER, ' ', text, flags=re.I) if chips else text
    rest = re.sub(r"[\s,，。.'’]+", ' ', rest).strip()
    return {'ok': True, 'chips': chips, 'rest': rest if chips else q.strip()}


# ---------------------------------------------------------------------------------------------- S2.2 change summaries
NUM = re.compile(r'-?\d[\d,]*(?:\.\d+)?')


def structured_summary(old, new, kind):
    """S2.2: what changed in a document's structure, from the same line comparison the diff shows: headings
    (Word / Markdown), slides (PowerPoint), table rows, cells (Excel) and numbers that changed in an otherwise same
    line. Only facts that are certain are listed; an empty list when there is nothing to say."""
    import difflib
    if kind not in ('docx', 'markdown', 'pptx', 'xlsx'):
        return []
    a, b = old or [], new or []
    sm = difflib.SequenceMatcher(None, a, b, autojunk=len(a) + len(b) > 4000)
    added, removed, pairs = [], [], []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ('delete', 'replace'):
            removed += a[i1:i2]
        if tag in ('insert', 'replace'):
            added += b[j1:j2]
        if tag == 'replace':
            pairs += list(zip(a[i1:i2], b[j1:j2]))
    out = []
    if kind in ('docx', 'markdown'):
        head = re.compile(r'^(#{1,6})\s+(.+)')
        ha = [m.group(2).strip() for m in map(head.match, added) if m]
        hr = [m.group(2).strip() for m in map(head.match, removed) if m]
        for x in ha:
            if x not in hr:
                out.append({'k': 'heading+', 'v': x})
        for x in hr:
            if x not in ha:
                out.append({'k': 'heading-', 'v': x})
    if kind == 'pptx':
        sl = re.compile(r'^\[Slide (\d+)\]\s*(.*)')
        ta, tr = [m.group(2) or m.group(1) for m in map(sl.match, added) if m], [m.group(2) or m.group(1) for m in map(sl.match, removed) if m]
        na, nr = sum(1 for x in a if sl.match(x)), sum(1 for x in b if sl.match(x))
        if nr != na:
            out.append({'k': 'slides', 'from': na, 'to': nr})
        for x in ta:
            if x not in tr:
                out.append({'k': 'slide+', 'v': x})
        for x in tr:
            if x not in ta:
                out.append({'k': 'slide-', 'v': x})
    if kind in ('docx', 'markdown', 'pptx'):
        rows = lambda ls: sum(1 for x in ls if x.startswith('| '))  # noqa: E731
        ra, rr = rows(added), rows(removed)
        if ra or rr:
            out.append({'k': 'rows', 'add': ra, 'del': rr})
    if kind == 'xlsx':
        cell = re.compile(r'^(.{1,80}?)!([A-Z]+)(\d+): ?(.*?)(?:   ƒ =.*)?$')
        old_c = {m.group(1) + '!' + m.group(2) + m.group(3): m.group(4) for m in map(cell.match, removed) if m}
        new_c = {m.group(1) + '!' + m.group(2) + m.group(3): m.group(4) for m in map(cell.match, added) if m}
        changed = [k for k in new_c if k in old_c]
        plus = [k for k in new_c if k not in old_c]
        minus = [k for k in old_c if k not in new_c]
        if changed or plus or minus:
            out.append({'k': 'cells', 'changed': len(changed), 'add': len(plus), 'del': len(minus)})
        rows_touched = {k.split('!')[0] + '!' + re.sub(r'^[A-Z]+', '', k.split('!')[1]) for k in changed + plus + minus}
        if rows_touched:
            out.append({'k': 'xrows', 'n': len(rows_touched)})
        pairs = [(old_c[k], new_c[k]) for k in changed]
    nums = []
    for x, y in pairs:
        if kind == 'xlsx':
            if NUM.fullmatch(x.strip() or 'x') and NUM.fullmatch(y.strip() or 'x'):
                nums.append((x.strip(), y.strip()))
            continue
        nx, ny = NUM.findall(x), NUM.findall(y)
        if nx and len(nx) == len(ny) and NUM.sub('#', x) == NUM.sub('#', y):  # the same line, only numbers differ
            nums += [(p, q) for p, q in zip(nx, ny) if p != q]
    for p, q in nums[:8]:
        out.append({'k': 'num', 'from': p, 'to': q})
    if len(nums) > 8:
        out.append({'k': 'numMore', 'n': len(nums) - 8})
    merged = []  # the same heading / slide added or removed twice: one line with ×2
    for x in out:
        same = next((m for m in merged if m['k'] == x['k'] and m.get('v') is not None and m.get('v') == x.get('v')), None)
        if same:
            same['times'] = same.get('times', 1) + 1
        else:
            merged.append(dict(x))
    return merged


def diff_summary(eid):
    App = N['App']
    r = App.store.q('SELECT * FROM events WHERE id=?', (eid,))
    if not r or r[0]['kind'] != 'modified':
        return {'ok': True, 'items': []}
    r = r[0]
    new, old = App.store.content(r['hash'], r['ext']), App.store.content(r['prev_hash'], r['ext'])
    if not new or not old:
        return {'ok': True, 'items': []}
    kind = new.get('type') or old.get('type')
    if r['ext'] in ('.md', '.markdown'):
        kind = 'markdown'
    return {'ok': True, 'type': kind, 'items': structured_summary(old.get('lines'), new.get('lines'), kind)}
