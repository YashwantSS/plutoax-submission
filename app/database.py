from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.extract import RawRow
from app.models import EnvReading
from app.settings import settings


def _conn() -> sqlite3.Connection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(settings.db_path)
    c.row_factory = sqlite3.Row
    return c


def init_db() -> None:
    with _conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                stored_path TEXT NOT NULL,
                original_name TEXT
            );
            CREATE TABLE IF NOT EXISTS env_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                page INTEGER,
                month TEXT NOT NULL,
                area TEXT NOT NULL,
                reference_document TEXT NOT NULL,
                temp_min REAL NOT NULL,
                temp_max REAL NOT NULL,
                rh_min REAL NOT NULL,
                rh_max REAL NOT NULL,
                dp_min REAL NOT NULL,
                dp_max REAL NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id),
                UNIQUE(document_id, month, area, reference_document)
            );
            CREATE INDEX IF NOT EXISTS idx_readings_doc_month_area
            ON env_readings(document_id, month, area);
            CREATE TABLE IF NOT EXISTS pipeline_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                extract_row_count INTEGER NOT NULL,
                validation_json TEXT NOT NULL,
                analysis_json TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );
            CREATE INDEX IF NOT EXISTS idx_pipeline_doc ON pipeline_runs(document_id);
            """
        )


@contextmanager
def get_connection():
    conn = _conn()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_document(doc_id: str, stored_path: Path, original_name: str | None) -> str:
    with get_connection() as c:
        c.execute(
            "INSERT INTO documents (id, stored_path, original_name) VALUES (?, ?, ?)",
            (doc_id, str(stored_path), original_name),
        )
    return doc_id


def replace_readings(document_id: str, rows: list[RawRow]) -> int:
    with get_connection() as c:
        c.execute("DELETE FROM env_readings WHERE document_id = ?", (document_id,))
        for r in rows:
            c.execute(
                """
                INSERT INTO env_readings (
                    document_id, page, month, area, reference_document,
                    temp_min, temp_max, rh_min, rh_max, dp_min, dp_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    document_id,
                    r.page,
                    r.month,
                    r.area,
                    r.reference_document,
                    r.temp_min,
                    r.temp_max,
                    r.rh_min,
                    r.rh_max,
                    r.dp_min,
                    r.dp_max,
                ),
            )
    return len(rows)


def fetch_reading(
    document_id: str,
    month: str,
    area: str,
    reference_document: str = "Executed BMRs",
) -> EnvReading | None:
    from app.normalize import normalize_area, normalize_month, normalize_reference

    m = normalize_month(month)
    a = normalize_area(area)
    ref = normalize_reference(reference_document)
    with get_connection() as c:
        row = c.execute(
            """
            SELECT month, area, reference_document, temp_min, temp_max,
                   rh_min, rh_max, dp_min, dp_max, page
            FROM env_readings
            WHERE document_id = ? AND month = ? AND area = ? AND reference_document = ?
            """,
            (document_id, m, a, ref),
        ).fetchone()
        if row is None:
            row = c.execute(
                """
                SELECT month, area, reference_document, temp_min, temp_max,
                       rh_min, rh_max, dp_min, dp_max, page
                FROM env_readings
                WHERE document_id = ? AND month = ? AND reference_document = ?
                  AND lower(area) = lower(?)
                """,
                (document_id, m, ref, a),
            ).fetchone()
    if row is None:
        return None
    return EnvReading(
        month=row["month"],
        area=row["area"],
        reference_document=row["reference_document"],
        temperature_c={"min": row["temp_min"], "max": row["temp_max"]},
        relative_humidity_pct={"min": row["rh_min"], "max": row["rh_max"]},
        differential_pressure_mm_wc={"min": row["dp_min"], "max": row["dp_max"]},
        page=row["page"],
    )


def get_document_stored_path(document_id: str) -> str | None:
    with get_connection() as c:
        row = c.execute("SELECT stored_path FROM documents WHERE id = ?", (document_id,)).fetchone()
    return str(row["stored_path"]) if row else None


def insert_pipeline_run(
    document_id: str,
    stored_path: str,
    extract_row_count: int,
    validation_json: str,
    analysis_json: str,
) -> None:
    with get_connection() as c:
        c.execute(
            """
            INSERT INTO pipeline_runs (
                document_id, stored_path, extract_row_count, validation_json, analysis_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, stored_path, extract_row_count, validation_json, analysis_json),
        )


def fetch_latest_pipeline_run(document_id: str):
    with get_connection() as c:
        return c.execute(
            """
            SELECT stored_path, extract_row_count, validation_json, analysis_json
            FROM pipeline_runs
            WHERE document_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (document_id,),
        ).fetchone()


def count_readings(document_id: str) -> int:
    with get_connection() as c:
        row = c.execute(
            "SELECT COUNT(*) AS n FROM env_readings WHERE document_id = ?",
            (document_id,),
        ).fetchone()
    return int(row["n"]) if row else 0


def list_readings(document_id: str, limit: int = 500) -> list[EnvReading]:
    with get_connection() as c:
        rows = c.execute(
            """
            SELECT month, area, reference_document, temp_min, temp_max,
                   rh_min, rh_max, dp_min, dp_max, page
            FROM env_readings
            WHERE document_id = ?
            ORDER BY page, month, area
            LIMIT ?
            """,
            (document_id, limit),
        ).fetchall()
    return [
        EnvReading(
            month=r["month"],
            area=r["area"],
            reference_document=r["reference_document"],
            temperature_c={"min": r["temp_min"], "max": r["temp_max"]},
            relative_humidity_pct={"min": r["rh_min"], "max": r["rh_max"]},
            differential_pressure_mm_wc={"min": r["dp_min"], "max": r["dp_max"]},
            page=r["page"],
        )
        for r in rows
    ]


def fetch_reading_fuzzy_area(
    document_id: str,
    month: str,
    area_substring: str,
    reference_document: str = "Executed BMRs",
) -> EnvReading | None:
    from app.normalize import normalize_month, normalize_reference

    m = normalize_month(month)
    ref = normalize_reference(reference_document)
    like = f"%{area_substring.strip()}%"
    with get_connection() as c:
        row = c.execute(
            """
            SELECT month, area, reference_document, temp_min, temp_max,
                   rh_min, rh_max, dp_min, dp_max, page
            FROM env_readings
            WHERE document_id = ? AND month = ? AND reference_document = ?
              AND lower(area) LIKE lower(?)
            LIMIT 1
            """,
            (document_id, m, ref, like),
        ).fetchone()
    if row is None:
        return None
    return EnvReading(
        month=row["month"],
        area=row["area"],
        reference_document=row["reference_document"],
        temperature_c={"min": row["temp_min"], "max": row["temp_max"]},
        relative_humidity_pct={"min": row["rh_min"], "max": row["rh_max"]},
        differential_pressure_mm_wc={"min": row["dp_min"], "max": row["dp_max"]},
        page=row["page"],
    )
