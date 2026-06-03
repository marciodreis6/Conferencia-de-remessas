from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from .config import ALIASES


def normalize(value: object) -> str:
    text = "" if value is None else str(value).strip()
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def parse_date(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+(\.\d+)?", text):
        serial = int(float(text))
        return date.fromordinal(date(1899, 12, 30).toordinal() + serial).isoformat()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def parse_number(value: object) -> float:
    text = str(value or "0").strip().replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text or 0)


def canonicalize(row: dict[str, object]) -> dict[str, str]:
    normalized = {normalize(k): v for k, v in row.items()}
    result = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            key = normalize(alias)
            if key in normalized:
                result[canonical] = str(normalized[key] or "").strip()
                break
    if "cliente" in result:
        result["cliente"] = normalize_customer_id(result["cliente"])
    for key in ("palete", "produto", "lote"):
        if key in result:
            result[key] = normalize_identifier(result[key])
    return result


def normalize_customer_id(value: object) -> str:
    identifier = normalize_identifier(value)
    if not identifier.isdigit():
        return identifier
    candidate = identifier.zfill(14)
    return candidate if is_valid_cnpj(candidate) else identifier


def normalize_identifier(value: object) -> str:
    text = str(value or "").strip().removeprefix("'")
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text.upper()


def is_valid_cnpj(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if len(digits) != 14 or len(set(digits)) == 1:
        return False
    numbers = [int(digit) for digit in digits]
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        remainder = sum(number * weight for number, weight in zip(numbers[:size], weights)) % 11
        check_digit = 0 if remainder < 2 else 11 - remainder
        if numbers[size] != check_digit:
            return False
    return True


def read_tabular(path: Path) -> list[dict[str, str]]:
    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        rows = _read_xlsx(path)
    elif suffix in {".csv", ".txt"}:
        rows = _read_delimited(path)
    else:
        raise ValueError("Formato nao suportado. Use XLSX, CSV ou TXT.")
    return [canonicalize(row) for row in rows if any(str(v).strip() for v in row.values())]


def read_txt_scans(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        fields = [field.strip() for field in line.split(";")]
        if len(fields) < 4:
            raise ValueError(f"Linha {number} do TXT possui menos de quatro campos.")
        rows.append({
            "data_embarque": parse_date(fields[0]),
            "hora_leitura": fields[1],
            "palete": fields[2],
            "quantidade": fields[3],
        })
    if not rows:
        raise ValueError("O TXT nao possui leituras.")
    return rows


def _read_delimited(path: Path) -> list[dict[str, str]]:
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=";,\t|")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    return list(csv.DictReader(io.StringIO(text), dialect=dialect))


def _read_xlsx(path: Path) -> list[dict[str, str]]:
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    with zipfile.ZipFile(path) as archive:
        shared = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//x:t", ns))
                      for item in root.findall("x:si", ns)]
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheet = workbook.find("x:sheets/x:sheet", ns)
        target = relationships[sheet.attrib[f"{{{ns['r']}}}id"]]
        sheet_path = target.lstrip("/")
        if not sheet_path.startswith("xl/"):
            sheet_path = "xl/" + sheet_path
        root = ET.fromstring(archive.read(sheet_path))

    table = []
    for row in root.findall(".//x:sheetData/x:row", ns):
        values = {}
        for cell in row.findall("x:c", ns):
            ref = cell.attrib.get("r", "")
            col = re.match(r"[A-Z]+", ref).group()
            node = cell.find("x:v", ns)
            value = "" if node is None else node.text or ""
            if cell.attrib.get("t") == "s" and value:
                value = shared[int(value)]
            inline = cell.find("x:is/x:t", ns)
            if inline is not None:
                value = inline.text or ""
            values[col] = value
        table.append(values)
    if not table:
        return []
    columns = sorted(table[0], key=_column_number)
    headers = [table[0].get(col, "") for col in columns]
    return [{headers[i]: row.get(col, "") for i, col in enumerate(columns)}
            for row in table[1:]]


def _column_number(col: str) -> int:
    total = 0
    for char in col:
        total = total * 26 + ord(char) - 64
    return total


def require_columns(rows: list[dict[str, str]], required: list[str]) -> None:
    if not rows:
        raise ValueError("O arquivo nao possui linhas de dados.")
    missing = [column for column in required if column not in rows[0]]
    if missing:
        raise ValueError("Colunas obrigatorias ausentes: " + ", ".join(missing))
