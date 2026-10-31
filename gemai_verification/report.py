"""
Merges extracted fields with Member 3's findings into Member 2's VerificationReport.
Extracted values are copied exactly and never changed.
"""

from schemas import (
    ExtractedField, ReportField, VerificationInput, VerificationReport,
)
from verify import verify_with_status


def build_report(data: VerificationInput) -> VerificationReport:
    summary = verify_with_status(data)

    # first field per name wins, the same rule verify() uses
    extracted: dict[str, ExtractedField] = {}
    for f in data.fields:
        extracted.setdefault(f.name, f)

    fields = []
    for finding in summary.output.findings:
        ex = extracted.get(finding.name)
        fields.append(ReportField(
            name=finding.name,
            document_value=ex.document_value if ex else None,
            raw_text=ex.raw_text if ex else None,
            document_source=ex.document_source if ex else None,
            extraction_status=ex.extraction_status if ex else "NOT_FOUND",
            reference_value=finding.reference_value,
            reference_source=finding.reference_source,
            is_demo_reference=finding.is_demo_reference,
            match_status=finding.match_status,
            risk_level=finding.risk_level,
            explanation=finding.explanation,
        ))

    files = sorted({
        f.document_source.file
        for f in data.fields
        if f.document_source and f.document_source.file
    })

    return VerificationReport(
        vendor_id=data.vendor_id,
        files=files,
        verification_status=summary.verification_status,
        highest_risk=summary.highest_risk,
        fields=fields,
        pending_checks=summary.output.pending_checks,
    )