"""Content extractors.

Turn raw file bytes into a structured, previewable form (what the UI renders) plus a
flat list of ``lines`` (what the diff engine compares between versions).

Only the standard library is required. PyMuPDF (``fitz``) or ``pypdf`` is used for PDF
text when available, and Pillow for image dimensions.
"""
import base64
import csv
import datetime as dt
import io
import posixpath
import re
import struct
import zipfile
import xml.etree.ElementTree as ET

VERSION = 2  # bump when extraction output changes, so cached results are rebuilt
MAX_LINES = 60000
MAX_TEXT = 3_000_000
MAX_ROWS = 1000
MAX_COLS = 60
MAX_SHEETS = 30
MAX_PAGES = 500

CATS = {
    'word': {'.docx', '.docm', '.dotx', '.doc', '.wps', '.rtf', '.odt'},
    'excel': {'.xlsx', '.xlsm', '.xltx', '.xls', '.et', '.csv', '.tsv', '.ods'},
    'ppt': {'.pptx', '.pptm', '.potx', '.ppt', '.dps', '.odp'},
    'pdf': {'.pdf'},
    'markdown': {'.md', '.markdown', '.mdx'},
    'text': {'.txt', '.log', '.ini', '.cfg', '.conf', '.toml', '.yaml', '.yml', '.env', '.properties', '.status', '.srt'},
    'code': {'.py', '.js', '.ts', '.tsx', '.jsx', '.json', '.html', '.htm', '.css', '.scss', '.java', '.c', '.h',
             '.cpp', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.sh', '.bat', '.cmd', '.ps1', '.sql', '.xml',
             '.vue', '.kt', '.swift', '.m', '.r', '.lua', '.tex', '.bib', '.ipynb'},
    'image': {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg', '.ico', '.avif'},
    'archive': {'.zip', '.rar', '.7z', '.tar', '.gz'},
    'media': {'.mp3', '.mp4', '.wav', '.mov', '.avi', '.mkv', '.flac', '.m4a'},
}
EXT_CAT = {e: c for c, exts in CATS.items() for e in exts}
TEXTUAL = CATS['text'] | CATS['code'] | CATS['markdown'] | {'.csv', '.tsv'}
# Types worth extracting at baseline so the first change already has a "before".
EXTRACTABLE = (CATS['word'] | CATS['excel'] | CATS['ppt'] | CATS['pdf'] | TEXTUAL) - {'.rtf', '.odt', '.ods', '.odp'}


def category_of(ext):
    return EXT_CAT.get((ext or '').lower(), 'other')


# ---------------------------------------------------------------- entry point

def extract(data, ext):
    ext = (ext or '').lower()
    try:
        kind = _sniff(data, ext)
        res = HANDLERS[kind](data, ext)
    except Exception as e:  # a corrupt/odd file must never break monitoring
        res = {'type': 'error', 'error': f'{type(e).__name__}: {e}'}
    lines = res.get('lines') or []
    if len(lines) > MAX_LINES:
        lines = lines[:MAX_LINES]
        res['truncated'] = True
    res['lines'] = lines
    res.setdefault('meta', {})
    res['v'] = VERSION
    return res


def _sniff(data, ext):
    head = data[:8]
    if head.startswith(b'PK\x03\x04'):
        try:
            names = set(zipfile.ZipFile(io.BytesIO(data)).namelist())
        except zipfile.BadZipFile:
            names = set()
        if 'word/document.xml' in names:
            return 'docx'
        if 'ppt/presentation.xml' in names:
            return 'pptx'
        if 'xl/workbook.xml' in names:
            return 'xlsx'
        if ext not in TEXTUAL:
            return 'zip'
    if head == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return 'ole'
    if data[:5] == b'%PDF-':
        return 'pdf'
    if ext in CATS['image']:
        return 'image'
    if ext in CATS['markdown']:
        return 'markdown'
    if ext in ('.csv', '.tsv'):
        return 'csv'
    if ext in TEXTUAL:
        return 'text'
    if b'\x00' not in data[:8192] and data:
        return 'text'
    return 'binary'


def decode_text(data):
    if data.startswith(b'\xef\xbb\xbf'):
        return data[3:].decode('utf-8', 'replace')
    if data[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return data.decode('utf-16', 'replace')
    try:
        return data.decode('utf-8')
    except UnicodeDecodeError:
        pass
    try:
        return data.decode('gb18030')  # common for Chinese Windows files
    except UnicodeDecodeError:
        return data.decode('utf-8', 'replace')


# ---------------------------------------------------------------- plain text

def _text(data, ext):
    text = decode_text(data[:MAX_TEXT])
    kind = 'code' if ext in CATS['code'] else 'text'
    return {'type': kind, 'lang': ext.lstrip('.'), 'text': text, 'lines': text.splitlines(),
            'meta': {'Lines': text.count('\n') + 1, 'Characters': len(text)}}


def _markdown(data, ext):
    res = _text(data, ext)
    res['type'] = 'markdown'
    return res


def _csv(data, ext):
    text = decode_text(data[:MAX_TEXT])
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=',;\t|')
    except csv.Error:
        dialect = csv.excel_tab if ext == '.tsv' else csv.excel
    rows = []
    for i, row in enumerate(csv.reader(io.StringIO(text), dialect)):
        if i >= MAX_ROWS:
            break
        rows.append(row[:MAX_COLS])
    return {'type': 'xlsx', 'sheets': [{'name': 'CSV', 'rows': rows, 'r0': 1, 'c0': 1}],
            'lines': text.splitlines(), 'meta': {'Rows': text.count('\n') + 1}}


# ---------------------------------------------------------------- OOXML shared

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
PML = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
SML = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'
VML = '{urn:schemas-microsoft-com:vml}'


def _xml(z, name):
    try:
        return ET.fromstring(z.read(name))
    except KeyError:
        return None


def _rels(z, path):
    """Relationship id -> absolute part name for the part at ``path``."""
    d, base = posixpath.split(path)
    root = _xml(z, posixpath.join(d, '_rels', base + '.rels'))
    out = {}
    if root is None:
        return out
    for r in root.iter(PKG + 'Relationship'):
        t = r.get('Target', '')
        if r.get('TargetMode') == 'External':
            continue
        out[r.get('Id')] = t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(d, t))
    return out


def _ooxml_meta(z):
    meta = {}
    core = _xml(z, 'docProps/core.xml')
    if core is not None:
        labels = {'title': 'Title', 'creator': 'Author', 'lastModifiedBy': 'Last modified by',
                  'created': 'Created', 'modified': 'Saved', 'revision': 'Revision'}
        for el in core:
            tag = el.tag.split('}')[-1]
            if tag in labels and (el.text or '').strip():
                meta[labels[tag]] = el.text.strip()
    app = _xml(z, 'docProps/app.xml')
    if app is not None:
        for el in app:
            tag = el.tag.split('}')[-1]
            if tag in ('Pages', 'Words', 'Slides', 'Application') and (el.text or '').strip():
                meta[tag] = el.text.strip()
    return meta


def _thumbnail(z):
    for name in z.namelist():
        low = name.lower()
        if low.startswith('docprops/thumbnail') and low.endswith(('.jpeg', '.jpg', '.png')):
            raw = z.read(name)
            if len(raw) < 400_000:
                mime = 'image/png' if low.endswith('.png') else 'image/jpeg'
                return f'data:{mime};base64,' + base64.b64encode(raw).decode()
    return None


def _on(el, ns=W):
    return el is not None and el.get(ns + 'val', 'true') not in ('0', 'false', 'none')


# ---------------------------------------------------------------- Word

def _docx(data, ext):
    z = zipfile.ZipFile(io.BytesIO(data))
    styles = {}
    st = _xml(z, 'word/styles.xml')
    if st is not None:
        for s in st.iter(W + 'style'):
            name = s.find(W + 'name')
            if name is not None:
                styles[s.get(W + 'styleId')] = (name.get(W + 'val') or '').lower()
    body = _xml(z, 'word/document.xml').find(W + 'body')
    rels = _rels(z, 'word/document.xml')
    blocks, lines = [], []

    def walk(container):
        for el in container:
            if el.tag == W + 'p':
                b = _docx_para(el, styles, rels)
                blocks.append(b)
                text = ''.join(r['t'] for r in b['runs'])
                if text.strip():
                    lines.append(('#' * b['lv'] + ' ' if b['t'] == 'h' else '• ' if b.get('list') else '') + text)
            elif el.tag == W + 'tbl':
                rows = []
                for tr in el.iter(W + 'tr'):
                    cells = []
                    for tc in tr.findall(W + 'tc'):
                        cells.append('\n'.join(''.join(r['t'] for r in _docx_para(p, styles)['runs'])
                                               for p in tc.iter(W + 'p')).strip())
                    rows.append(cells)
                    if len(rows) >= MAX_ROWS:
                        break
                blocks.append({'t': 'table', 'rows': rows})
                lines.extend('| ' + ' | '.join(c.replace('\n', ' ') for c in r) + ' |' for r in rows)
            elif el.tag == W + 'sdt':
                c = el.find(W + 'sdtContent')
                if c is not None:
                    walk(c)

    walk(body)
    # Drop runs of empty paragraphs so the preview doesn't show huge gaps.
    compact, empty = [], 0
    for b in blocks:
        is_empty = b['t'] != 'table' and not any(r['t'].strip() or r.get('img') for r in b['runs'])
        empty = empty + 1 if is_empty else 0
        if empty <= 1:
            compact.append(b)
    meta = _ooxml_meta(z)
    meta['Paragraphs'] = len(lines)
    return {'type': 'docx', 'blocks': compact, 'lines': lines, 'meta': meta, 'thumb': _thumbnail(z)}


def _image_part(el, rels):
    """Package part of the picture inside a w:drawing / w:pict element, if any."""
    blip = next(el.iter(A + 'blip'), None)
    rid = blip.get(REL + 'embed') if blip is not None else None
    if rid is None:
        imd = next(el.iter(VML + 'imagedata'), None)
        rid = imd.get(REL + 'id') if imd is not None else None
    return rels.get(rid) if rels and rid else None


def _docx_para(p, styles, rels=None):
    ppr = p.find(W + 'pPr')
    style, is_list, align = '', False, None
    if ppr is not None:
        ps = ppr.find(W + 'pStyle')
        if ps is not None:
            sid = ps.get(W + 'val', '')
            style = styles.get(sid, sid.lower())
        is_list = ppr.find(W + 'numPr') is not None or 'list' in style
        jc = ppr.find(W + 'jc')
        if jc is not None:
            align = jc.get(W + 'val')
    runs = []
    for r in p.iter(W + 'r'):
        rpr = r.find(W + 'rPr')
        b = i = u = False
        if rpr is not None:
            b, i = _on(rpr.find(W + 'b')), _on(rpr.find(W + 'i'))
            u = rpr.find(W + 'u') is not None and rpr.find(W + 'u').get(W + 'val') != 'none'
        parts, img = [], False
        for c in r:
            if c.tag == W + 't':
                parts.append(c.text or '')
            elif c.tag == W + 'tab':
                parts.append('\t')
            elif c.tag in (W + 'br', W + 'cr'):
                parts.append('\n')
            elif c.tag in (W + 'drawing', W + 'pict', W + 'object'):
                img = _image_part(c, rels) or True
        text = ''.join(parts)
        if img:
            runs.append({'t': '', 'img': img})
        if not text:
            continue
        if runs and not runs[-1].get('img') and (runs[-1]['b'], runs[-1]['i'], runs[-1]['u']) == (b, i, u):
            runs[-1]['t'] += text
        else:
            runs.append({'t': text, 'b': b, 'i': i, 'u': u})
    m = re.search(r'heading\s*(\d)', style)
    if m or style in ('title', 'subtitle'):
        lv = int(m.group(1)) if m else (1 if style == 'title' else 2)
        return {'t': 'h', 'lv': min(lv, 6), 'runs': runs, 'align': align}
    return {'t': 'p', 'runs': runs, 'list': is_list, 'align': align}


# ---------------------------------------------------------------- PowerPoint

def _pptx(data, ext):
    z = zipfile.ZipFile(io.BytesIO(data))
    pres = _xml(z, 'ppt/presentation.xml')
    rels = _rels(z, 'ppt/presentation.xml')
    order = [rels.get(s.get(REL + 'id')) for s in pres.iter(PML + 'sldId')]
    slides, lines = [], []
    for n, path in enumerate([p for p in order if p], 1):
        x = _xml(z, path)
        if x is None:
            continue
        title, paras, pics = '', [], 0
        for sp in x.iter(PML + 'sp'):
            ph = sp.find(f'{PML}nvSpPr/{PML}nvPr/{PML}ph')
            is_title = ph is not None and ph.get('type') in ('title', 'ctrTitle')
            texts = []
            for ap in sp.iter(A + 'p'):
                t = ''.join(t.text or '' for t in ap.iter(A + 't')).strip()
                if t:
                    ppr = ap.find(A + 'pPr')
                    texts.append({'t': t, 'lv': int(ppr.get('lvl', 0)) if ppr is not None else 0})
            if is_title and texts and not title:
                title = ' '.join(t['t'] for t in texts)
            else:
                paras.extend(texts)
        tables = []
        for tbl in x.iter(A + 'tbl'):
            tables.append([[''.join(t.text or '' for t in tc.iter(A + 't')) for tc in tr.iter(A + 'tc')]
                           for tr in tbl.iter(A + 'tr')])
        srels = _rels(z, path)
        pic_parts = [_image_part(pic, srels) for pic in x.iter(PML + 'pic')]
        pics = len(pic_parts)
        imgs = [p for p in pic_parts if p][:6]
        notes = ''
        for target in srels.values():
            if 'notesSlide' in target:
                nx = _xml(z, target)
                if nx is not None:
                    chunks = []
                    for sp in nx.iter(PML + 'sp'):
                        ph = sp.find(f'{PML}nvSpPr/{PML}nvPr/{PML}ph')
                        if ph is not None and ph.get('type') == 'body':
                            chunks += [''.join(t.text or '' for t in ap.iter(A + 't')) for ap in sp.iter(A + 'p')]
                    notes = '\n'.join(c for c in chunks if c.strip())
        slides.append({'n': n, 'title': title, 'paras': paras, 'tables': tables, 'pics': pics, 'imgs': imgs, 'notes': notes})
        lines.append(f'[Slide {n}] {title}'.rstrip())
        lines += ['  ' * p['lv'] + '• ' + p['t'] for p in paras]
        for t in tables:
            lines += ['| ' + ' | '.join(r) + ' |' for r in t]
        if notes:
            lines += ['[Notes] ' + l for l in notes.splitlines()]
    meta = _ooxml_meta(z)
    meta['Slides'] = len(slides)
    return {'type': 'pptx', 'slides': slides, 'lines': lines, 'meta': meta, 'thumb': _thumbnail(z)}


# ---------------------------------------------------------------- Excel

_BUILTIN_DATE = set(range(14, 23)) | {45, 46, 47}


def _col_letters(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _ref(ref):
    m = re.match(r'([A-Z]+)(\d+)', ref or '')
    if not m:
        return None
    col = 0
    for ch in m.group(1):
        col = col * 26 + ord(ch) - 64
    return int(m.group(2)), col


def _fmt_num(v, date_kind=None):
    try:
        f = float(v)
    except ValueError:
        return v
    if date_kind and 0 < f < 2958466:
        d = dt.datetime(1899, 12, 30) + dt.timedelta(days=f)
        if date_kind == 'time' and f < 1:
            return d.strftime('%H:%M:%S')
        return d.strftime('%Y-%m-%d') if f == int(f) else d.strftime('%Y-%m-%d %H:%M')
    if f == int(f) and abs(f) < 1e15:
        return str(int(f))
    return f'{f:.10g}'


def _xlsx(data, ext):
    z = zipfile.ZipFile(io.BytesIO(data))
    wb = _xml(z, 'xl/workbook.xml')
    rels = _rels(z, 'xl/workbook.xml')
    sst = []
    sx = _xml(z, 'xl/sharedStrings.xml')
    if sx is not None:
        for si in sx.iter(SML + 'si'):
            parts = [si.find(SML + 't')] + [r.find(SML + 't') for r in si.findall(SML + 'r')]
            sst.append(''.join((p.text or '') for p in parts if p is not None))
    # Which cell styles are dates, so serial numbers display as dates.
    xf_date = []
    sty = _xml(z, 'xl/styles.xml')
    if sty is not None:
        custom = {}
        nf = sty.find(SML + 'numFmts')
        if nf is not None:
            for f in nf.findall(SML + 'numFmt'):
                code = re.sub(r'"[^"]*"|\[[^\]]*\]|\\.', '', f.get('formatCode', ''))
                custom[int(f.get('numFmtId'))] = 'date' if re.search(r'[yYdD]', code) else \
                    'time' if re.search(r'[hH]|[sS]', code) else None
        xfs = sty.find(SML + 'cellXfs')
        for xf in (xfs.findall(SML + 'xf') if xfs is not None else []):
            fid = int(xf.get('numFmtId', 0))
            xf_date.append('date' if fid in _BUILTIN_DATE else custom.get(fid))
    sheets, lines = [], []
    for s in list(wb.iter(SML + 'sheet'))[:MAX_SHEETS]:
        name = s.get('name')
        path = rels.get(s.get(REL + 'id'))
        if not path or path not in z.namelist():
            continue
        cells = {}
        with z.open(path) as fh:
            for _, el in ET.iterparse(fh):
                if el.tag != SML + 'c':
                    continue
                pos = _ref(el.get('r'))
                t = el.get('t')
                v = el.find(SML + 'v')
                f = el.find(SML + 'f')
                val = v.text if v is not None else None
                if t == 's' and val is not None:
                    val = sst[int(val)] if int(val) < len(sst) else ''
                elif t == 'inlineStr':
                    val = ''.join(x.text or '' for x in el.iter(SML + 't'))
                elif t == 'b' and val is not None:
                    val = 'TRUE' if val == '1' else 'FALSE'
                elif t in (None, 'n') and val is not None:
                    si = int(el.get('s', 0))
                    val = _fmt_num(val, xf_date[si] if si < len(xf_date) else None)
                formula = f.text if f is not None and f.text else None
                if pos and (val not in (None, '') or formula):
                    cells[pos] = (val or '', formula)
                    if len(lines) < MAX_LINES:
                        ref = _col_letters(pos[1]) + str(pos[0])
                        lines.append(f'{name}!{ref}: {val or ""}' + (f'   ƒ ={formula}' if formula else ''))
                el.clear()
        if cells:
            r0 = min(r for r, _ in cells)
            c0 = min(c for _, c in cells)
            r1 = min(max(r for r, _ in cells), r0 + MAX_ROWS - 1)
            c1 = min(max(c for _, c in cells), c0 + MAX_COLS - 1)
            rows = [[cells.get((r, c), ('', None))[0] for c in range(c0, c1 + 1)] for r in range(r0, r1 + 1)]
            formulas = {f'{r - r0},{c - c0}': cells[(r, c)][1] for (r, c) in cells
                        if cells[(r, c)][1] and r <= r1 and c <= c1}
        else:
            r0 = c0 = 1
            rows, formulas = [], {}
        sheets.append({'name': name, 'rows': rows, 'r0': r0, 'c0': c0, 'formulas': formulas, 'cells': len(cells)})
    meta = _ooxml_meta(z)
    meta['Sheets'] = len(sheets)
    meta['Non-empty cells'] = sum(s['cells'] for s in sheets)
    return {'type': 'xlsx', 'sheets': sheets, 'lines': lines, 'meta': meta}


# ---------------------------------------------------------------- PDF

def _pdf(data, ext):
    pages, meta = [], {}
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open(stream=data, filetype='pdf')
        meta = {k.title(): v for k, v in (doc.metadata or {}).items() if v and k in ('title', 'author', 'creator', 'producer', 'modDate')}
        meta['Pages'] = doc.page_count
        for i in range(min(doc.page_count, MAX_PAGES)):
            pages.append(doc[i].get_text('text'))
    except ImportError:
        from pypdf import PdfReader
        rd = PdfReader(io.BytesIO(data))
        meta['Pages'] = len(rd.pages)
        for p in rd.pages[:MAX_PAGES]:
            pages.append(p.extract_text() or '')
    lines = []
    for i, t in enumerate(pages, 1):
        lines.append(f'──── Page {i} ────')
        lines += [l for l in t.splitlines() if l.strip()]
    return {'type': 'pdf', 'pages': pages, 'lines': lines, 'meta': meta}


# ---------------------------------------------------------------- images / zip / binary

def _image(data, ext):
    meta = {}
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(data))
        meta = {'Dimensions': f'{im.width} × {im.height}', 'Mode': im.mode, 'Format': im.format}
    except Exception:
        pass
    return {'type': 'image', 'meta': meta}


def _zip(data, ext):
    z = zipfile.ZipFile(io.BytesIO(data))
    entries = [(i.filename, i.file_size) for i in z.infolist()[:5000]]
    return {'type': 'archive', 'entries': entries, 'lines': [f'{n}  ({s} B)' for n, s in entries],
            'meta': {'Entries': len(z.infolist())}}


def _binary(data, ext):
    return {'type': 'binary'}


# ---------------------------------------------------------------- legacy Office (OLE / CFB)

def _cfb_streams(data):
    """Minimal Compound File Binary reader: stream name -> bytes."""
    ssz = 1 << struct.unpack_from('<H', data, 0x1E)[0]
    msz = 1 << struct.unpack_from('<H', data, 0x20)[0]
    dir_start, = struct.unpack_from('<I', data, 0x30)
    cutoff, minifat_start, n_minifat, difat_start, n_difat = struct.unpack_from('<IIIII', data, 0x38)

    def sector(sid):
        off = (sid + 1) * ssz
        return data[off:off + ssz]

    difat = list(struct.unpack_from('<109I', data, 0x4C))
    sid = difat_start
    for _ in range(n_difat):
        if sid >= 0xFFFFFFFA:
            break
        vals = struct.unpack(f'<{ssz // 4}I', sector(sid))
        difat += vals[:-1]
        sid = vals[-1]
    fat = []
    for s in difat:
        if s < 0xFFFFFFFA:
            fat += struct.unpack(f'<{ssz // 4}I', sector(s))

    def chain(start, table, getter, limit=1 << 20):
        out, s, n = [], start, 0
        while s < 0xFFFFFFFA and s < len(table) and n < limit:
            out.append(getter(s))
            s, n = table[s], n + 1
        return b''.join(out)

    dirs = chain(dir_start, fat, sector)
    entries = []
    for off in range(0, len(dirs) - 127, 128):
        nlen, = struct.unpack_from('<H', dirs, off + 64)
        name = dirs[off:off + max(nlen - 2, 0)].decode('utf-16-le', 'replace')
        typ = dirs[off + 66]
        start, size = struct.unpack_from('<II', dirs, off + 116)
        entries.append((name, typ, start, size))
    if not entries:
        return {}
    root = entries[0]
    ministream = chain(root[2], fat, sector)
    minifat_raw = chain(minifat_start, fat, sector)
    minifat = list(struct.unpack(f'<{len(minifat_raw) // 4}I', minifat_raw[:len(minifat_raw) // 4 * 4]))
    streams = {}
    for name, typ, start, size in entries[1:]:
        if typ != 2:
            continue
        if size < cutoff:
            raw = chain(start, minifat, lambda s: ministream[s * msz:(s + 1) * msz])
        else:
            raw = chain(start, fat, sector)
        streams[name] = raw[:size]
    return streams


def _doc_text(streams):
    wd = streams['WordDocument']
    flags, = struct.unpack_from('<H', wd, 0x0A)
    table = streams['1Table' if flags & 0x0200 else '0Table']
    ccp_text, = struct.unpack_from('<I', wd, 0x4C)
    fc_clx, lcb_clx = struct.unpack_from('<II', wd, 0x1A2)
    clx = table[fc_clx:fc_clx + lcb_clx]
    i = 0
    while i < len(clx) and clx[i] == 0x01:  # skip Prc entries
        i += 3 + struct.unpack_from('<H', clx, i + 1)[0]
    lcb, = struct.unpack_from('<I', clx, i + 1)
    plc = clx[i + 5:i + 5 + lcb]
    n = (lcb - 4) // 12
    cps = struct.unpack_from(f'<{n + 1}I', plc, 0)
    out = []
    for k in range(n):
        fc, = struct.unpack_from('<I', plc, 4 * (n + 1) + 8 * k + 2)
        count = cps[k + 1] - cps[k]
        if fc & 0x40000000:
            off = (fc & 0x3FFFFFFF) // 2
            out.append(wd[off:off + count].decode('cp1252', 'replace'))
        else:
            out.append(wd[fc:fc + 2 * count].decode('utf-16-le', 'replace'))
    text = ''.join(out)[:ccp_text]
    text = re.sub(r'\x13[^\x13\x14\x15]*\x14?', '', text).replace('\x15', '')  # field codes
    text = text.replace('\r', '\n').replace('\x0b', '\n').replace('\x07', '\t').replace('\x0c', '\n')
    return re.sub(r'[\x00-\x08\x0e-\x1f]', '', text)


def _ppt_text(stream):
    out, i = [], 0
    while i + 8 <= len(stream):
        ver, typ, ln = struct.unpack_from('<HHI', stream, i)
        if ver & 0x0F == 0x0F:  # container: descend
            i += 8
            continue
        body = stream[i + 8:i + 8 + ln]
        if typ == 0x0FA0:
            out.append(body.decode('utf-16-le', 'replace'))
        elif typ == 0x0FA8:
            out.append(body.decode('cp1252', 'replace'))
        i += 8 + ln
    return '\n'.join(t.replace('\r', '\n') for t in out)


def _xls_strings(stream):
    """Shared strings (SST) of a BIFF8 workbook, honouring CONTINUE boundaries."""
    chunks, i, collecting = [], 0, False
    while i + 4 <= len(stream):
        typ, ln = struct.unpack_from('<HH', stream, i)
        if typ == 0x00FC:
            chunks, collecting = [stream[i + 4:i + 4 + ln]], True
        elif typ == 0x003C and collecting:
            chunks.append(stream[i + 4:i + 4 + ln])
        elif collecting:
            break
        i += 4 + ln
    if not chunks:
        return []
    ci, pos = 0, 8
    out = []

    def take(n):
        nonlocal ci, pos
        buf = b''
        while n > 0 and ci < len(chunks):
            part = chunks[ci][pos:pos + n]
            buf += part
            pos += len(part)
            n -= len(part)
            if pos >= len(chunks[ci]):
                ci, pos = ci + 1, 0
        return buf

    total, = struct.unpack_from('<I', chunks[0], 4)
    for _ in range(min(total, 200000)):
        if ci >= len(chunks):
            break
        hdr = take(3)
        if len(hdr) < 3:
            break
        cch, flags = struct.unpack('<HB', hdr)
        runs = struct.unpack('<H', take(2))[0] if flags & 0x08 else 0
        ext_len = struct.unpack('<I', take(4))[0] if flags & 0x04 else 0
        chars, wide = [], flags & 0x01
        while cch > 0 and ci < len(chunks):
            avail = len(chunks[ci]) - pos
            n = min(cch, avail // 2 if wide else avail) or 1
            raw = take(n * 2 if wide else n)
            chars.append(raw.decode('utf-16-le' if wide else 'latin-1', 'replace'))
            cch -= n
            if cch > 0 and pos == 0 and ci < len(chunks):  # continued: new option byte
                wide = take(1)[0] & 0x01
        take(4 * runs + ext_len)
        out.append(''.join(chars))
    return out


def _ole(data, ext):
    streams = _cfb_streams(data)
    if 'WordDocument' in streams:
        text = _doc_text(streams)
        lines = [l for l in text.splitlines() if l.strip()]
        return {'type': 'docx', 'legacy': True, 'blocks': [{'t': 'p', 'runs': [{'t': l}]} for l in lines],
                'lines': lines, 'meta': {'Format': 'Word 97-2003', 'Paragraphs': len(lines)}}
    if 'PowerPoint Document' in streams:
        text = _ppt_text(streams['PowerPoint Document'])
        lines = [l for l in text.splitlines() if l.strip()]
        return {'type': 'text', 'legacy': True, 'text': '\n'.join(lines), 'lines': lines,
                'meta': {'Format': 'PowerPoint 97-2003'}}
    wb = streams.get('Workbook') or streams.get('Book')
    if wb:
        strings = [s for s in _xls_strings(wb) if s.strip()]
        return {'type': 'text', 'legacy': True, 'text': '\n'.join(strings), 'lines': strings,
                'meta': {'Format': 'Excel 97-2003', 'Text cells': len(strings)}}
    return {'type': 'binary', 'meta': {'Format': 'OLE compound file'}}


HANDLERS = {'docx': _docx, 'pptx': _pptx, 'xlsx': _xlsx, 'pdf': _pdf, 'ole': _ole, 'zip': _zip,
            'image': _image, 'markdown': _markdown, 'csv': _csv, 'text': _text, 'binary': _binary}
