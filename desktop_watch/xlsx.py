"""A minimal .xlsx writer (standard library only): one sheet, a bold frozen header row with
filters, column widths, and real date/number cells. Enough for exporting the change history."""
import datetime as dt
import io
import zipfile
from xml.sax.saxutils import escape

_EPOCH = dt.datetime(1899, 12, 30)


def _col(n):
    s = ''
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


def _cell(ref, v):
    if v is None or v == '':
        return ''
    if isinstance(v, dt.datetime):
        return f'<c r="{ref}" s="2"><v>{(v - _EPOCH).total_seconds() / 86400:.8f}</v></c>'
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return f'<c r="{ref}"><v>{v}</v></c>'
    text = escape(''.join(ch for ch in str(v) if ch in '\t\n' or ord(ch) >= 32))  # XML-safe characters only
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def write_xlsx(headers, rows, widths=None, sheet='Sheet1'):
    """Return the bytes of a workbook. Cells may be str, int/float or datetime (local time)."""
    ncol = len(headers)
    last = f'{_col(ncol)}{len(rows) + 1}'
    head = ''.join(f'<c r="{_col(i + 1)}1" t="inlineStr" s="1"><is><t>{escape(h)}</t></is></c>' for i, h in enumerate(headers))
    body = ''.join(f'<row r="{r + 2}">' + ''.join(_cell(f'{_col(i + 1)}{r + 2}', v) for i, v in enumerate(row)) + '</row>'
                   for r, row in enumerate(rows))
    cols = ''.join(f'<col min="{i + 1}" max="{i + 1}" width="{w}" customWidth="1"/>' for i, w in enumerate(widths or []))
    sheet_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
                 f'<dimension ref="A1:{last}"/>'
                 '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
                 '</sheetView></sheetViews>'
                 + (f'<cols>{cols}</cols>' if cols else '') +
                 f'<sheetData><row r="1">{head}</row>{body}</sheetData>'
                 f'<autoFilter ref="A1:{last}"/></worksheet>')
    styles = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<numFmts count="1"><numFmt numFmtId="164" formatCode="yyyy-mm-dd hh:mm:ss"/></numFmts>'
              '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
              '<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>'
              '<fill><patternFill patternType="solid"><fgColor rgb="FFE8EAF6"/><bgColor indexed="64"/></patternFill></fill></fills>'
              '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
              '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
              '<cellXfs count="3"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
              '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1"/>'
              '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>'
              '</styleSheet>')
    parts = {
        '[Content_Types].xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>',
        '_rels/.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>',
        'xl/workbook.xml': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<sheets><sheet name="{escape(sheet[:31])}" sheetId="1" r:id="rId1"/></sheets>'
        f'<definedNames><definedName name="_xlnm._FilterDatabase" localSheetId="0" hidden="1">\'{escape(sheet[:31])}\'!$A$1:${_col(ncol)}${len(rows) + 1}</definedName></definedNames>'
        '</workbook>',
        'xl/_rels/workbook.xml.rels': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
        '</Relationships>',
        'xl/worksheets/sheet1.xml': sheet_xml,
        'xl/styles.xml': styles,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return buf.getvalue()
