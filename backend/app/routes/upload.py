import re
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.config import settings
from app.db import insert_document
from app.schemas import DocumentUploadResponse
from app.utils.file_validation import (
    FileValidationError,
    generate_stored_filename,
    validate_pdf_upload,
)

router = APIRouter()

VENDOR_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,50}$")


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
def upload_document(
    file: UploadFile = File(...),
    vendor_id: str | None = Form(default=None),
):
    # 1. Validate the file (raises FileValidationError if rejected)
    original_name = validate_pdf_upload(file)

    # 2. Use the given vendor_id (for a vendor's 2nd, 3rd... document) or make a new one
    if vendor_id is None:
        vendor_id = f"V{uuid.uuid4().hex[:8].upper()}"
    elif not VENDOR_ID_PATTERN.match(vendor_id):
        raise FileValidationError(
            "vendor_id may only contain letters, digits, '-' and '_'.",
            error="INVALID_VENDOR_ID",
        )

    # 3. Save under a generated name, never the user's filename
    stored_filename = generate_stored_filename()
    document_id = Path(stored_filename).stem
    destination = settings.upload_dir / stored_filename

    # 4. Save the file and record it in the database.
    #    Clean up the file if either step fails.
    try:
        with open(destination, "wb") as out:
            shutil.copyfileobj(file.file, out)

        insert_document(
            document_id,
            vendor_id,
            original_name,
            stored_filename,
        )
    except Exception:
        destination.unlink(missing_ok=True)
        raise

    return DocumentUploadResponse(
        vendor_id=vendor_id,
        document_id=document_id,
        filename=original_name,
        status="UPLOADED",
    )