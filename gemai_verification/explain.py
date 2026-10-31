"""
Explanation builder. Grounded text only.

Every sentence is built from stored values: document_value, reference_value,
reference_source, the document source (file, page), or a reason string that
validators.py / evidence.py already produced from stored values.
Nothing is invented, guessed or paraphrased by a model.

explain_crosscheck(result, source)  -> text for a cross-check result
explain_review(name, reason, ...)   -> text for format / evidence / uncertainty problems
"""

from constants import TURNOVER_TOLERANCE
from crosscheck import (
    CrossCheckResult,
    EXACT, TURNOVER_WITHIN_TOLERANCE, MINOR_SPELLING, NAME_MISMATCH,
    VALUE_MISMATCH, TURNOVER_MINOR_MISMATCH, TURNOVER_MAJOR_MISMATCH,
    NO_DOCUMENT_VALUE, REFERENCE_UNAVAILABLE, UNCLEAR_VALUE,
)
from risk import (
    FORMAT_INVALID, UNSUPPORTED_EVIDENCE, UNCERTAIN_EXTRACTION, GSTIN_PAN_CONFLICT,
)
from schemas import DocumentSource

LABELS = {
    "company_name": "Company name",
    "pan": "PAN",
    "gstin": "GSTIN",
    "annual_turnover": "Annual turnover",
    "udyam_number": "Udyam number",
}


def _where(source: DocumentSource | None) -> str:
    """' (from file.pdf, page 3)' or an empty string."""
    if source is None or not source.file:
        return ""
    if source.page:
        return f" (from {source.file}, page {source.page})"
    return f" (from {source.file})"


def _ref_label(result: CrossCheckResult) -> str:
    """Reference source, always flagged as simulated when it is demo data."""
    if result.is_demo_reference:
        return f"{result.reference_source}, simulated demo data"
    return result.reference_source or "unknown source"


def explain_crosscheck(result: CrossCheckResult, source: DocumentSource | None = None) -> str:
    label = LABELS[result.name]
    doc, ref = result.document_value, result.reference_value
    where = _where(source)
    kind = result.kind

    if kind == EXACT:
        return f"{label} '{doc}'{where} matches the reference value '{ref}' ({_ref_label(result)})."

    if kind == TURNOVER_WITHIN_TOLERANCE:
        pct = round(TURNOVER_TOLERANCE * 100)
        return (
            f"{label} '{doc}'{where} differs slightly from the reference value '{ref}' "
            f"({_ref_label(result)}) but is within the {pct}% tolerance, so it is treated as matching."
        )

    if kind == MINOR_SPELLING:
        return (
            f"{label} '{doc}'{where} differs slightly from the reference value '{ref}' "
            f"({_ref_label(result)}). This looks like a minor spelling difference; "
            "officer review is recommended."
        )

    if kind == NAME_MISMATCH:
        return (
            f"{label} '{doc}'{where} is different from the reference value '{ref}' "
            f"({_ref_label(result)}). Officer review is required."
        )

    if kind == VALUE_MISMATCH:
        return (
            f"{label} '{doc}'{where} does not match the reference value '{ref}' "
            f"({_ref_label(result)}). Officer review is required."
        )

    if kind == TURNOVER_MINOR_MISMATCH:
        return (
            f"{label} '{doc}'{where} differs from the reference value '{ref}' "
            f"({_ref_label(result)}). The values differ; officer review is required."
        )

    if kind == TURNOVER_MAJOR_MISMATCH:
        return (
            f"{label} '{doc}'{where} differs substantially from the reference value '{ref}' "
            f"({_ref_label(result)}). Officer review is required."
        )

    if kind == NO_DOCUMENT_VALUE:
        text = f"No {label} was extracted from the uploaded documents."
        if ref is not None:
            text += f" The reference value is '{ref}' ({_ref_label(result)})."
        return text + " The document may be missing or unclear; officer review is required."

    if kind == REFERENCE_UNAVAILABLE:
        return (
            f"Verification Pending: no reference record is available for {label}, "
            f"so '{doc}'{where} could not be cross-checked. This is not a failure."
        )

    if kind == UNCLEAR_VALUE:
        return (
            f"{label} '{doc}'{where} could not be read as a number, so it was not compared "
            f"with the reference value '{ref}'. Officer review is required."
        )

    raise ValueError(f"Unknown cross-check kind: {kind}")


def explain_review(
    name: str,
    reason: str,
    detail: str | None = None,
    document_value: str | None = None,
    raw_text: str | None = None,
    source: DocumentSource | None = None,
) -> str:
    """
    Explanation for values that need human review before any comparison.
    `detail` is the reason string already produced by validators.py or evidence.py.
    """
    label = LABELS[name]
    where = _where(source)

    if reason == FORMAT_INVALID:
        base = detail or f"{label} '{document_value}'{where} does not have a valid format."
        return f"{base} It was not compared with the reference and is marked for human review."

    if reason == UNSUPPORTED_EVIDENCE:
        base = detail or f"{label} '{document_value}'{where} is not supported by its raw text."
        return f"{base} It is not trusted automatically and is marked for human review."

    if reason == UNCERTAIN_EXTRACTION:
        if document_value is None:
            return (
                f"The extraction of {label} was marked uncertain and no value was kept. "
                "Human review is required."
            )
        return (
            f"The extraction of {label} was marked uncertain "
            f"(document value '{document_value}'{where}, raw text '{raw_text}'). "
            "It is not trusted automatically; human review is required."
        )

    if reason == GSTIN_PAN_CONFLICT:
        base = detail or "The PAN contained in the GSTIN does not agree with the extracted PAN."
        return f"{base} Human review is required."

    raise ValueError(f"Unknown review reason: {reason}")