from pathlib import Path

import fitz  # PyMuPDF
from pydantic import BaseModel

from app.config import settings


class PDFReadError(Exception):
    """Raised when a PDF cannot be read. Handled in main.py."""

    def __init__(
        self,
        message: str,
        status_code: int = 422,
        error: str = "PDF_READ_ERROR",
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error = error


class PageText(BaseModel):
    page: int            # 1-based, matches DocumentSource.page in schemas.py
    text: str
    has_text: bool       # False for blank or scanned pages
    char_count: int


class PDFContent(BaseModel):
    file: str            # name to show the officer (original filename if given)
    total_pages: int
    pages: list[PageText]
    has_extractable_text: bool       # False means the whole PDF needs OCR
    pages_without_text: list[int]    # page numbers that may need OCR


def extract_text_from_pdf(
    file_path: str | Path,
    display_name: str | None = None,
) -> PDFContent:
    """
    Extracts text from a PDF, page by page, keeping page numbers.

    file_path:    the stored file on disk (settings.upload_dir / stored_filename)
    display_name: the original filename from the database, used as the
                  evidence source shown to the officer. Falls back to the
                  name on disk if not given.

    Raises PDFReadError for missing, corrupt, encrypted, empty or oversized PDFs.
    """
    path = Path(file_path)

    if not path.is_file():
        raise PDFReadError(
            "PDF file not found.", status_code=404, error="PDF_NOT_FOUND"
        )

    try:
        with fitz.open(str(path)) as pdf:
            # needs_pass is True only when a password is actually required.
            # (is_encrypted is also True for PDFs that open without one.)
            if pdf.needs_pass:
                raise PDFReadError(
                    "Password-protected PDFs are not supported.",
                    error="PDF_ENCRYPTED",
                )

            if pdf.page_count == 0:
                raise PDFReadError("The PDF has no pages.", error="PDF_EMPTY")

            if pdf.page_count > settings.max_pdf_pages:
                raise PDFReadError(
                    f"The PDF has {pdf.page_count} pages; "
                    f"the limit is {settings.max_pdf_pages}.",
                    status_code=413,
                    error="PDF_TOO_MANY_PAGES",
                )

            pages: list[PageText] = []
            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text("text").strip()
                pages.append(
                    PageText(
                        page=page_number,
                        text=text,
                        has_text=bool(text),
                        char_count=len(text),
                    )
                )

    except PDFReadError:
        raise
    except Exception as exc:
        raise PDFReadError(
            "Unable to read this PDF. It may be corrupt.",
            error="PDF_CORRUPT",
        ) from exc

    pages_without_text = [p.page for p in pages if not p.has_text]

    return PDFContent(
        file=display_name or path.name,
        total_pages=len(pages),
        pages=pages,
        has_extractable_text=len(pages_without_text) < len(pages),
        pages_without_text=pages_without_text,
    )