from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db import init_db
from app.routes import upload
from app.schemas import ErrorResponse
from app.services.pdf_reader import PDFReadError
from app.utils.file_validation import FileValidationError

app = FastAPI(
    title=settings.app_name,
    description="Trust-based AI procurement verification (backend)",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Error handlers: every error uses {"error": ..., "message": ...}
# -------------------------------

@app.exception_handler(FileValidationError)
async def file_validation_error_handler(request: Request, exc: FileValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


@app.exception_handler(PDFReadError)
async def pdf_read_error_handler(request: Request, exc: PDFReadError):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error=exc.error, message=exc.message).model_dump(),
    )


# -------------------------------
# Routes
# -------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


init_db()
app.include_router(upload.router, prefix="/api", tags=["upload"])

# Uncomment each router as you write it:
# from app.routes import extraction, reports
# app.include_router(extraction.router, prefix="/api", tags=["extraction"])
# app.include_router(reports.router, prefix="/api", tags=["reports"])