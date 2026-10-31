from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, model_validator

FieldName = Literal["company_name", "pan", "gstin", "annual_turnover", "udyam_number"]
DocumentType = Literal["PAN", "GST", "UDYAM", "FINANCIAL", "OTHER"]
ExtractionStatus = Literal["EXTRACTED", "UNCERTAIN", "NOT_FOUND"]
MatchStatus = Literal["MATCHED", "MISMATCH", "PENDING"]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
VerificationStatus = Literal["REVIEW_REQUIRED", "PENDING", "NO_ISSUES_FOUND"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DocumentUploadResponse(BaseModel):
    vendor_id: str
    document_id: str
    filename: str
    status: Literal["UPLOADED", "PROCESSING", "FAILED"]


class DocumentSource(BaseModel):
    file: str
    page: int | None = Field(default=None, ge=1)


class ExtractedField(BaseModel):
    name: FieldName
    document_value: str | None = None      # normalized value, None if not found/unclear
    raw_text: str | None = None            # exact snippet the value came from
    document_source: DocumentSource | None = None
    document_type: DocumentType | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    extraction_status: ExtractionStatus = "EXTRACTED"

    @model_validator(mode="after")
    def check_consistency(self):
        if self.extraction_status == "EXTRACTED":
            if self.document_value is None:
                raise ValueError("EXTRACTED field must have a document_value")
            if not self.raw_text:
                raise ValueError("EXTRACTED field must have raw_text as evidence")
        if self.extraction_status == "NOT_FOUND":
            if self.document_value is not None or self.raw_text is not None:
                raise ValueError("NOT_FOUND field must not have a value or raw_text")
        return self


class ExtractionResponse(BaseModel):
    vendor_id: str
    document_id: str
    fields: list[ExtractedField]
    status: Literal["SUCCESS", "PARTIAL", "FAILED"]


class Finding(BaseModel):
    name: FieldName
    reference_value: str | None = None
    reference_source: str | None = None    # e.g. "DEMO_REFERENCE_RECORD"
    is_demo_reference: bool = False        # True when reference data is simulated
    match_status: MatchStatus
    risk_level: RiskLevel | None = None
    explanation: str

    @model_validator(mode="after")
    def check_consistency(self):
        if self.match_status == "MISMATCH" and self.risk_level is None:
            raise ValueError("MISMATCH finding must have a risk_level")
        if self.match_status == "MATCHED" and self.reference_value is None:
            raise ValueError("MATCHED finding must have a reference_value")
        if self.reference_value is not None and not self.reference_source:
            raise ValueError("reference_value requires a reference_source")
        return self


class VerificationInput(BaseModel):
    """What gets passed to Member 3's verify()."""
    vendor_id: str
    fields: list[ExtractedField]


class VerificationOutput(BaseModel):
    """What Member 3's verify() returns."""
    findings: list[Finding]
    pending_checks: list[str] = Field(default_factory=list)


class ReportField(BaseModel):
    """One extracted field merged with its finding."""
    name: FieldName
    document_value: str | None = None
    raw_text: str | None = None
    document_source: DocumentSource | None = None
    extraction_status: ExtractionStatus
    reference_value: str | None = None
    reference_source: str | None = None
    is_demo_reference: bool = False
    match_status: MatchStatus
    risk_level: RiskLevel | None = None
    explanation: str


class VerificationReport(BaseModel):
    vendor_id: str
    files: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus
    highest_risk: RiskLevel | None = None
    fields: list[ReportField]
    pending_checks: list[str] = Field(default_factory=list)
    human_decision_required: Literal[True] = True
    generated_at: datetime = Field(default_factory=utc_now)


class ErrorResponse(BaseModel):
    error: str
    message: str