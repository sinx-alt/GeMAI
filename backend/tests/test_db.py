
import sqlite3
import pytest

from app import db


@pytest.fixture
def test_database(tmp_path, monkeypatch):
    test_db_path = tmp_path / "test_gemai.db"
    monkeypatch.setattr(db, "DB_PATH", test_db_path)
    db.init_db()


# 1. Database initialization

def test_database_initialization(test_database):
    with db.get_connection() as conn:
        result = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name='documents'"
        ).fetchone()

    assert result is not None


def test_init_db_twice(test_database):
    db.insert_document("D001", "V001", "pan.pdf", "abc.pdf")

    db.init_db()

    assert db.get_document("D001") is not None


# 2. Document insertion and retrieval

def test_insert_and_get_document(test_database):
    db.insert_document(
        document_id="D001",
        vendor_id="V001",
        original_filename="pan.pdf",
        stored_filename="abc123.pdf",
    )

    document = db.get_document("D001")

    assert document is not None
    assert document["vendor_id"] == "V001"
    assert document["original_filename"] == "pan.pdf"
    assert document["status"] == "UPLOADED"


def test_custom_document_status(test_database):
    db.insert_document(
        "D001", "V001", "pan.pdf", "abc.pdf",
        status="PROCESSING"
    )

    document = db.get_document("D001")

    assert document["status"] == "PROCESSING"


# 3. Missing records

def test_get_missing_document(test_database):
    result = db.get_document("DOES_NOT_EXIST")

    assert result is None


def test_list_documents_for_unknown_vendor(test_database):
    result = db.list_documents_for_vendor("V999")

    assert result == []


# 4. Duplicate document IDs

def test_duplicate_document_id(test_database):
    db.insert_document("D001", "V001", "pan.pdf", "abc.pdf")

    with pytest.raises(sqlite3.IntegrityError):
        db.insert_document("D001", "V001", "gst.pdf", "xyz.pdf")


# 5. Transaction rollback

def test_transaction_rollback(test_database):
    with pytest.raises(RuntimeError):
        with db.get_connection() as conn:
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?)",
                (
                    "D001",
                    "V001",
                    "pan.pdf",
                    "abc.pdf",
                    "UPLOADED",
                    "2026-10-31T10:00:00+00:00",
                ),
            )

            raise RuntimeError("Simulated database failure")

    assert db.get_document("D001") is None


# 6. Listing documents for a vendor

def test_list_documents_for_vendor(test_database):
    db.insert_document("D001", "V001", "pan.pdf", "abc.pdf")
    db.insert_document("D002", "V001", "gst.pdf", "xyz.pdf")
    db.insert_document("D003", "V002", "udyam.pdf", "123.pdf")

    documents = db.list_documents_for_vendor("V001")

    assert len(documents) == 2

    filenames = {doc["original_filename"] for doc in documents}

    assert filenames == {"pan.pdf", "gst.pdf"}
    assert all(doc["vendor_id"] == "V001" for doc in documents)
