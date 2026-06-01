from __future__ import annotations

import html
import zipfile
from io import BytesIO


def workbook(sheets: list[tuple[str, list[dict]]]) -> bytes:
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types(len(sheets)))
        archive.writestr("_rels/.rels", _root_rels())
        archive.writestr("xl/workbook.xml", _workbook(sheets))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels(len(sheets)))
        archive.writestr("xl/styles.xml", _styles())
        for index, (_, rows) in enumerate(sheets, 1):
            archive.writestr(f"xl/worksheets/sheet{index}.xml", _sheet(rows))
    return output.getvalue()


def _sheet(rows: list[dict]) -> str:
    columns = list(rows[0]) if rows else ["sem_dados"]
    table = [columns] + [[row.get(column, "") for column in columns] for row in rows]
    xml_rows = []
    for r_index, values in enumerate(table, 1):
        cells = []
        for c_index, value in enumerate(values, 1):
            ref = f"{_col(c_index)}{r_index}"
            text = html.escape("" if value is None else str(value))
            style = ' s="1"' if r_index == 1 else ""
            cells.append(f'<c r="{ref}" t="inlineStr"{style}><is><t>{text}</t></is></c>')
        xml_rows.append(f'<row r="{r_index}">{"".join(cells)}</row>')
    return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' \
           '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' \
           f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'


def _col(number: int) -> str:
    result = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _content_types(count: int) -> str:
    sheets = "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                     'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                     for i in range(1, count + 1))
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' \
           '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' \
           '<Default Extension="xml" ContentType="application/xml"/>' \
           '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' \
           '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' \
           f'{sheets}</Types>'


def _root_rels() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
           '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' \
           '</Relationships>'


def _workbook(sheets: list[tuple[str, list[dict]]]) -> str:
    tags = "".join(f'<sheet name="{html.escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
                   for i, (name, _) in enumerate(sheets, 1))
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' \
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' \
           f'<sheets>{tags}</sheets></workbook>'


def _workbook_rels(count: int) -> str:
    sheets = "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
                     for i in range(1, count + 1))
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' \
           f'{sheets}<Relationship Id="rId{count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' \
           '</Relationships>'


def _styles() -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>' \
           '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' \
           '<fonts count="2"><font/><font><b/></font></fonts><fills count="1"><fill><patternFill patternType="none"/></fill></fills>' \
           '<borders count="1"><border/></borders><cellStyleXfs count="1"><xf/></cellStyleXfs>' \
           '<cellXfs count="2"><xf/><xf fontId="1" applyFont="1"/></cellXfs></styleSheet>'

