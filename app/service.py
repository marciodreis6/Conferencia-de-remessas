from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from . import db
from .config import BASE_TYPES, UPLOAD_DIR
from .parsers import parse_number, read_tabular, read_txt_scans, require_columns
from .validation import validate
from .xlsx_writer import workbook


def initialize() -> None:
    db.init_db()


def import_base(base_type: str, filename: str, source: Path) -> dict:
    if base_type not in BASE_TYPES:
        raise ValueError("Tipo de base desconhecido.")
    stored = _store(source, base_type, filename)
    rows = read_tabular(stored)
    require_columns(rows, BASE_TYPES[base_type]["required"])
    if base_type == "shelf":
        for row in rows:
            try:
                shelf_minimo = parse_number(row["shelf_minimo"])
            except ValueError:
                continue
            db.upsert_shelf(
                row["cliente"],
                shelf_minimo,
                row.get("cliente_nome", ""),
            )
    import_id = db.save_import(base_type, filename, stored, rows)
    return {"id": import_id, "base_type": base_type, "filename": filename, "row_count": len(rows)}


def process_txt(filename: str, source: Path) -> dict:
    stored = _store(source, "txt", filename)
    rows = read_txt_scans(stored)
    required = ("fabrica", "detalhamento", "bloqueados")
    bases = {base: db.latest_rows(base) for base in required}
    missing = [base for base in required if not bases[base]]
    if missing:
        raise ValueError("Importe primeiro as bases: " + ", ".join(missing))
    results = validate(rows, bases["fabrica"], bases["detalhamento"], bases["bloqueados"], db.shelf_rules())
    run_id = db.save_run(filename, results)
    return {"id": run_id, "filename": filename, "items": len(results),
            "approved": sum(item["status"] == "APROVADO" for item in results)}


def dashboard() -> dict:
    runs = db.runs()
    validations = db.validation_rows()
    approved = sum(row["status"] == "APROVADO" for row in validations)
    errors = {}
    for row in validations:
        for error in filter(None, (row.get("errors") or "").split(", ")):
            errors[error] = errors.get(error, 0) + 1
    return {
        "runs": len(runs), "items": len(validations), "approved": approved,
        "accuracy": round(approved * 100 / len(validations), 1) if validations else 0,
        "errors": [{"name": key, "count": value} for key, value in sorted(errors.items(), key=lambda item: -item[1])],
    }


def export_history() -> bytes:
    summary = [dashboard()]
    return workbook([
        ("Resumo", summary),
        ("Processamentos", db.runs()),
        ("Validacoes", db.validation_rows()),
        ("Importacoes", db.imports()),
        ("Shelf life", db.shelf_rules()),
    ])


def _store(source: Path, category: str, filename: str) -> Path:
    safe_name = Path(filename).name
    folder = UPLOAD_DIR / category / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / safe_name
    shutil.copyfile(source, target)
    return target
