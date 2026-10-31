

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.routes import upload
from app.utils.file_validation import FileValidationError


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Use a temporary upload directory for every test
    monkeypatch.setattr(upload.settings, "upload_dir", tmp_path)

    app = FastAPI()
    app.include_router(upload.router, prefix="/api")

    # Handle file-validation errors
    @app.exception_handler(FileValidationError)
    async def handle_file_validation_error(
        request: Request, exc: FileValidationError
    ):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error,
                "message": exc.message,
            },
        )

    return TestClient(app, raise_server_exceptions=False), tmp_path


def test_successful_upload(client, monkeypatch):
    test_client, upload_dir = client
    saved_records = []

    monkeypatch.setattr(
        upload,
        "insert_document",
        lambda *args: saved_records.append(args),
    )

    response = test_client.post(
        "/api/upload",
        files={
            "file": (
                "pan.pdf",
                b"%PDF-1.4 test content",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["filename"] == "pan.pdf"
    assert data["status"] == "UPLOADED"
    assert data["vendor_id"].startswith("V")
    assert len(saved_records) == 1
    assert len(list(upload_dir.iterdir())) == 1


def test_upload_with_existing_vendor_id(client, monkeypatch):
    test_client, _ = client

    monkeypatch.setattr(upload, "insert_document", lambda *args: None)

    response = test_client.post(
        "/api/upload",
        data={"vendor_id": "VENDOR_123"},
        files={
            "file": (
                "gst.pdf",
                b"%PDF-1.4 test",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["vendor_id"] == "VENDOR_123"


def test_invalid_vendor_id(client):
    test_client, upload_dir = client

    response = test_client.post(
        "/api/upload",
        data={"vendor_id": "../invalid"},
        files={
            "file": (
                "pan.pdf",
                b"%PDF-1.4 test",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "INVALID_VENDOR_ID"
    assert list(upload_dir.iterdir()) == []


def test_reject_non_pdf_file(client):
    test_client, upload_dir = client

    response = test_client.post(
        "/api/upload",
        files={
            "file": (
                "document.txt",
                b"Some text",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []


def test_reject_empty_file(client):
    test_client, upload_dir = client

    response = test_client.post(
        "/api/upload",
        files={
            "file": (
                "empty.pdf",
                b"",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert list(upload_dir.iterdir()) == []


def test_cleanup_when_database_insert_fails(client, monkeypatch):
    test_client, upload_dir = client

    def fail_insert(*args):
        raise RuntimeError("Database unavailable")

    monkeypatch.setattr(upload, "insert_document", fail_insert)

    response = test_client.post(
        "/api/upload",
        files={
            "file": (
                "pan.pdf",
                b"%PDF-1.4 test",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 500
    assert list(upload_dir.iterdir()) == []
