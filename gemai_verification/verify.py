"""
Public entry point for Member 3's verification engine.

    from verify import verify, verify_with_status

verify(VerificationInput) -> VerificationOutput          (the agreed contract)
verify_with_status(VerificationInput) -> VerificationSummary
    same output plus verification_status and highest_risk, so schemas.py
    (Member 2's file) does not have to change.

Nothing here edits the extracted values. human_decision_required is always True.
"""

from dataclasses import dataclass

from constants import ALL_FIELDS
from crosscheck import crosscheck_field, CrossCheckResult, MISMATCH, PENDING
from evidence import check_evidence, UNSUPPORTED, SUPPORTED
from explain import explain_crosscheck, explain_review
from reference_data import get_reference
from risk import (
    risk_for_crosscheck, risk_for_review, highest_risk, max_risk,
    FORMAT_INVALID, UNSUPPORTED_EVIDENCE, UNCERTAIN_EXTRACTION, GSTIN_PAN_CONFLICT,
)
from schemas import ExtractedField, Finding, VerificationInput, VerificationOutput
from validators import validate_field, gstin_pan_consistent


@dataclass
class VerificationSummary:
    output: VerificationOutput
    verification_status: str        # REVIEW_REQUIRED | PENDING | NO_ISSUES_FOUND
    highest_risk: str | None        # LOW | MEDIUM | HIGH | None
    human_decision_required: bool = True


def _finding_from_crosscheck(r: CrossCheckResult, field: ExtractedField) -> Finding:
    return Finding(
        name=r.name,
        reference_value=r.reference_value,
        reference_source=r.reference_source,
        is_demo_reference=r.is_demo_reference,
        match_status=r.match_status,
        risk_level=risk_for_crosscheck(r.name, r.match_status, r.kind),
        explanation=explain_crosscheck(r, field.document_source),
    )


def _review_finding(field: ExtractedField, vendor_id: str, reason: str,
                    detail: str | None = None) -> Finding:
    """Value is unclear, unsupported or invalid: PENDING + human review, no comparison."""
    ref = get_reference(vendor_id, field.name)
    return Finding(
        name=field.name,
        reference_value=ref["value"] if ref else None,
        reference_source=ref["source"] if ref else None,
        is_demo_reference=bool(ref["is_demo"]) if ref else False,
        match_status="PENDING",
        risk_level=risk_for_review(reason),
        explanation=explain_review(
            field.name, reason, detail=detail,
            document_value=field.document_value,
            raw_text=field.raw_text,
            source=field.document_source,
        ),
    )


def _finding_for_field(field: ExtractedField, vendor_id: str) -> Finding:
    if field.document_value is None:
        if field.extraction_status == "UNCERTAIN":
            return _review_finding(field, vendor_id, UNCERTAIN_EXTRACTION)
        return _finding_from_crosscheck(crosscheck_field(field, vendor_id), field)

    status, detail = check_evidence(field)
    if status == UNSUPPORTED:
        return _review_finding(field, vendor_id, UNSUPPORTED_EVIDENCE, detail)

    ok, detail = validate_field(field.name, field.document_value)
    if not ok:
        return _review_finding(field, vendor_id, FORMAT_INVALID, detail)

    if field.extraction_status == "UNCERTAIN":
        return _review_finding(field, vendor_id, UNCERTAIN_EXTRACTION)

    return _finding_from_crosscheck(crosscheck_field(field, vendor_id), field)


def _apply_gstin_pan_conflict(findings: list[Finding], fields: dict[str, ExtractedField]) -> None:
    """If the GSTIN contains a different PAN than the extracted PAN, flag it HIGH."""
    gstin, pan = fields["gstin"], fields["pan"]
    if check_evidence(gstin)[0] != SUPPORTED or check_evidence(pan)[0] != SUPPORTED:
        return  # do not build a conflict on values that are not trusted
    if gstin_pan_consistent(gstin.document_value, pan.document_value) is not False:
        return

    g, p = gstin.document_value, pan.document_value
    detail = f"GSTIN '{g}' contains the PAN '{g[2:12]}', but the extracted PAN is '{p}'."
    for i, old in enumerate(findings):
        if old.name == "gstin":
            findings[i] = Finding(
                name=old.name,
                reference_value=old.reference_value,
                reference_source=old.reference_source,
                is_demo_reference=old.is_demo_reference,
                match_status="MISMATCH" if old.match_status == MISMATCH else PENDING,
                risk_level=max_risk(old.risk_level, risk_for_review(GSTIN_PAN_CONFLICT)),
                explanation=old.explanation + " " + explain_review(
                    "gstin", GSTIN_PAN_CONFLICT, detail=detail),
            )
            return


def overall_status(findings: list[Finding]) -> str:
    if any(f.match_status == MISMATCH or f.risk_level is not None for f in findings):
        return "REVIEW_REQUIRED"
    if any(f.match_status == PENDING for f in findings):
        return "PENDING"
    return "NO_ISSUES_FOUND"


def verify_with_status(data: VerificationInput) -> VerificationSummary:
    # one entry per field name; a field missing from the input is treated as not found
    fields: dict[str, ExtractedField] = {}
    for f in data.fields:
        fields.setdefault(f.name, f)
    for name in ALL_FIELDS:
        if name not in fields:
            fields[name] = ExtractedField(name=name, extraction_status="NOT_FOUND")

    findings = [_finding_for_field(f, data.vendor_id) for f in fields.values()]
    _apply_gstin_pan_conflict(findings, fields)

    pending_checks = [f.name for f in findings if f.match_status == PENDING]
    output = VerificationOutput(findings=findings, pending_checks=pending_checks)
    return VerificationSummary(
        output=output,
        verification_status=overall_status(findings),
        highest_risk=highest_risk(f.risk_level for f in findings),
    )


def verify(data: VerificationInput) -> VerificationOutput:
    """The function Member 2 imports."""
    return verify_with_status(data).output