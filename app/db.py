from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR, DB_PATH, UPLOAD_DIR


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


@contextmanager
def connection():
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with connection() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS imports (
          id INTEGER PRIMARY KEY, base_type TEXT NOT NULL, filename TEXT NOT NULL,
          imported_at TEXT NOT NULL, row_count INTEGER NOT NULL, stored_path TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS base_rows (
          id INTEGER PRIMARY KEY, import_id INTEGER NOT NULL, base_type TEXT NOT NULL,
          payload TEXT NOT NULL, FOREIGN KEY(import_id) REFERENCES imports(id)
        );
        CREATE TABLE IF NOT EXISTS shelf_rules (
          cliente TEXT PRIMARY KEY, cliente_nome TEXT, shelf_minimo REAL NOT NULL,
          active INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS shelf_history (
          id INTEGER PRIMARY KEY, cliente TEXT NOT NULL, cliente_nome TEXT,
          shelf_minimo REAL NOT NULL, active INTEGER NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
          id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, filename TEXT NOT NULL,
          remessa TEXT, status TEXT NOT NULL, total_items INTEGER NOT NULL,
          approved_items INTEGER NOT NULL, unidentified_items INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS validations (
          id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL, data_embarque TEXT, remessa TEXT,
          cliente TEXT, palete TEXT, produto TEXT, lote TEXT, validade TEXT, producao TEXT,
          quantidade_txt REAL, quantidade_detalhe REAL, shelf_percentual REAL,
          shelf_minimo REAL, bloqueio_status TEXT, status TEXT, errors TEXT,
          FOREIGN KEY(run_id) REFERENCES runs(id)
        );
        """)


def save_import(base_type: str, filename: str, stored_path: Path, rows: list[dict]) -> int:
    with connection() as con:
        cur = con.execute(
            "INSERT INTO imports(base_type, filename, imported_at, row_count, stored_path) VALUES(?,?,?,?,?)",
            (base_type, filename, now(), len(rows), str(stored_path)),
        )
        import_id = cur.lastrowid
        con.executemany(
            "INSERT INTO base_rows(import_id, base_type, payload) VALUES(?,?,?)",
            [(import_id, base_type, json.dumps(row, ensure_ascii=True)) for row in rows],
        )
    return import_id


def latest_rows(base_type: str) -> list[dict]:
    with connection() as con:
        row = con.execute("SELECT MAX(id) id FROM imports WHERE base_type=?", (base_type,)).fetchone()
        if not row["id"]:
            return []
        rows = con.execute("SELECT payload FROM base_rows WHERE import_id=?", (row["id"],)).fetchall()
        return [json.loads(item["payload"]) for item in rows]


def imports() -> list[dict]:
    with connection() as con:
        return [dict(row) for row in con.execute("SELECT * FROM imports ORDER BY id DESC").fetchall()]


def clear_latest_import(base_type: str) -> bool:
    with connection() as con:
        row = con.execute(
            "SELECT MAX(id) id FROM imports WHERE base_type=?",
            (base_type,),
        ).fetchone()
        if not row["id"]:
            return False
        con.execute("DELETE FROM base_rows WHERE import_id=?", (row["id"],))
        con.execute("DELETE FROM imports WHERE id=?", (row["id"],))
    return True


def upsert_shelf(cliente: str, shelf_minimo: float, cliente_nome: str = "", active: bool = True) -> None:
    stamp = now()
    with connection() as con:
        con.execute(
            """INSERT INTO shelf_rules(cliente,cliente_nome,shelf_minimo,active,updated_at) VALUES(?,?,?,?,?)
               ON CONFLICT(cliente) DO UPDATE SET cliente_nome=excluded.cliente_nome,
               shelf_minimo=excluded.shelf_minimo, active=excluded.active, updated_at=excluded.updated_at""",
            (cliente, cliente_nome, shelf_minimo, int(active), stamp),
        )
        con.execute(
            "INSERT INTO shelf_history(cliente,cliente_nome,shelf_minimo,active,updated_at) VALUES(?,?,?,?,?)",
            (cliente, cliente_nome, shelf_minimo, int(active), stamp),
        )


def clear_shelf_rules() -> None:
    with connection() as con:
        con.execute("DELETE FROM shelf_rules")


def shelf_rules() -> list[dict]:
    with connection() as con:
        return [dict(row) for row in con.execute("SELECT * FROM shelf_rules ORDER BY cliente").fetchall()]


def save_run(filename: str, results: list[dict]) -> int:
    approved = sum(item["status"] == "APROVADO" for item in results)
    unidentified = sum(not item.get("produto") for item in results)
    shipment = next((item.get("remessa", "") for item in results if item.get("remessa")), "")
    status = "APROVADO" if approved == len(results) else "COM_DIVERGENCIAS"
    with connection() as con:
        cur = con.execute(
            "INSERT INTO runs(created_at,filename,remessa,status,total_items,approved_items,unidentified_items) VALUES(?,?,?,?,?,?,?)",
            (now(), filename, shipment, status, len(results), approved, unidentified),
        )
        run_id = cur.lastrowid
        columns = ("data_embarque", "remessa", "cliente", "palete", "produto", "lote",
                   "validade", "producao", "quantidade_txt", "quantidade_detalhe",
                   "shelf_percentual", "shelf_minimo", "bloqueio_status", "status", "errors")
        con.executemany(
            f"INSERT INTO validations(run_id,{','.join(columns)}) VALUES(?," + ",".join("?" * len(columns)) + ")",
            [(run_id, *[item.get(col) for col in columns]) for item in results],
        )
    return run_id


def runs() -> list[dict]:
    with connection() as con:
        return [dict(row) for row in con.execute("SELECT * FROM runs ORDER BY id DESC").fetchall()]


def validation_rows(run_id: int | None = None) -> list[dict]:
    with connection() as con:
        sql = "SELECT * FROM validations"
        params = ()
        if run_id:
            sql += " WHERE run_id=?"
            params = (run_id,)
        sql += " ORDER BY id DESC"
        return [dict(row) for row in con.execute(sql, params).fetchall()]
