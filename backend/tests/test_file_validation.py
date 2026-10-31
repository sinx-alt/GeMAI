
from io import BytesIO

import pytest
from fastapi import UploadFile

from app.utils.file_validation import (
    validate_pdf_upload,
    FileValidationError,
)


def create_upload(filename, content):
    return UploadFile(
        filename=filename,
        file=BytesIO(content)
    )


def test_valid_pdf():
    file = create_upload(
        "vendor.pdf",
        b"%PDF-1.7 sample document content"
    )

    result = validate_pdf_upload(file)

    assert result == "vendor.pdf"


def test_invalid_extension():
    file = create_upload(
        "vendor.txt",
        b"%PDF-1.7 sample content"
    )

    with pytest.raises(FileValidationError):
        validate_pdf_upload(file)


def test_invalid_pdf_signature():
    file = create_upload(
        "vendor.pdf",
        b"This is not a PDF file"
    )

    with pytest.raises(FileValidationError):
        validate_pdf_upload(file)


def test_empty_file():
    file = create_upload("vendor.pdf", b"")

    with pytest.raises(FileValidationError):
        validate_pdf_upload(file)


def test_filename_sanitization():
    file = create_upload(
        "../../vendor.pdf",
        b"%PDF-1.7 sample content"
    )

    result = validate_pdf_upload(file)

    assert result == "vendor.pdf"
