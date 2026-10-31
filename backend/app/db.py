import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings

DB_PATH = Path(settings.database_url.removeprefix("sqlite:///"))


@contextmanager
def get_connection():
    """Opens a connection, commits on success, rolls back on error, always closes."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Creates the database folder and tables if they don't exist yet."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id       TEXT PRIMARY KEY,
                vendor_id         TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                stored_filename   TEXT NOT NULL,
                status            TEXT NOT NULL,
                uploaded_at       TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_vendor "
            "ON documents (vendor_id)"
        )


def insert_document(
    document_id: str,
    vendor_id: str,
    original_filename: str,
    stored_filename: str,
    status: str = "UPLOADED",
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO documents (
                document_id, vendor_id, original_filename,
                stored_filename, status, uploaded_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                vendor_id,
                original_filename,
                stored_filename,
                status,
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_document(document_id: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM documents WHERE document_id = ?", (document_id,)
        ).fetchone()
    return dict(row) if row else None


def list_documents_for_vendor(vendor_id: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE vendor_id = ? ORDER BY uploaded_at",
            (vendor_id,),
        ).fetchall()
    return [dict(r) for r in rows]