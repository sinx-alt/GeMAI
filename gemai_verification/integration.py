"""
Integration layer for Member 2's pipeline.

    from integration import verify_vendor, verify_extraction, verify_payload

verify_vendor(list[ExtractionResponse])  -> VerificationReport   (several documents, one vendor)
verify_extraction(ExtractionResponse)    -> VerificationReport   (one document)
verify_payload(dict)                     -> dict                 (JSON in, JSON out)

Nothing here edits an extracted value.
"""

from constants import ALL_FIELDS
from report import build_report
from schemas import (
    ExtractedField, ExtractionResponse, VerificationInput, VerificationReport,
)

# When the same field appears in several documents, keep the most reliable one.
_PRIORITY = {"EXTRACTED": 0, "UNCERTAIN": 1, "NOT_FOUND": 2}


def merge_fields(extractions: list[ExtractionResponse]) -> list[ExtractedField]:
    """One field per name across all documents. Better status wins, then first seen."""
    best: dict[str, ExtractedField] = {}
    for extraction in extractions:
        for f in extraction.fields:
            current = best.get(f.name)
            if current is None or _PRIORITY[f.extraction_status] < _PRIORITY[current.extraction_status]:
                best[f.name] = f
    return [best[name] for name in ALL_FIELDS if name in best]


def verify_vendor(extractions: list[ExtractionResponse]) -> VerificationReport:
    """Verify one vendor whose documents were extracted separately."""
    if not extractions:
        raise ValueError("verify_vendor needs at least one ExtractionResponse.")
    vendor_ids = {e.vendor_id for e in extractions}
    if len(vendor_ids) != 1:
        raise ValueError(f"All extractions must belong to one vendor, got: {sorted(vendor_ids)}")

    data = VerificationInput(vendor_id=extractions[0].vendor_id, fields=merge_fields(extractions))
    return build_report(data)


def verify_extraction(extraction: ExtractionResponse) -> VerificationReport:
    """Verify a single extraction result."""
    return verify_vendor([extraction])


def verify_payload(payload: dict) -> dict:
    """JSON-style dict in (an ExtractionResponse), JSON-style dict out (a VerificationReport)."""
    extraction = ExtractionResponse.model_validate(payload)
    return verify_extraction(extraction).model_dump(mode="json")