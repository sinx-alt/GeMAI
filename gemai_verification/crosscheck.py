"""
Cross-check: compare document_value with the reference record.

This only decides MATCHED / MISMATCH / PENDING and labels WHY with a `kind`.
It does not assign risk (Work 6) or write explanations (Work 7).
It never fixes or guesses a value.

PENDING means the check could not be completed. It is never a failure.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from rapidfuzz import fuzz

from constants import NAME_SIMILARITY_LOW, TURNOVER_TOLERANCE, TURNOVER_MAJOR_RATIO
from reference_data import get_reference
from schemas import ExtractedField

# match_status values
MATCHED = "MATCHED"
MISMATCH = "MISMATCH"
PENDING = "PENDING"

# kinds (Work 6 maps these to risk levels)
EXACT = "exact"
TURNOVER_WITHIN_TOLERANCE = "turnover_within_tolerance"
MINOR_SPELLING = "minor_spelling"
NAME_MISMATCH = "name_mismatch"
VALUE_MISMATCH = "value_mismatch"                      # pan, gstin, udyam_number
TURNOVER_MINOR_MISMATCH = "turnover_minor_mismatch"
TURNOVER_MAJOR_MISMATCH = "turnover_major_mismatch"
NO_DOCUMENT_VALUE = "no_document_value"                # nothing extracted
REFERENCE_UNAVAILABLE = "reference_unavailable"        # no reference to compare with
UNCLEAR_VALUE = "unclear_value"                        # value could not be read as a number


@dataclass
class CrossCheckResult:
    name: str
    match_status: str
    kind: str
    document_value: str | None
    reference_value: str | None
    reference_source: str | None
    is_demo_reference: bool


def _normalize_name(text: str) -> str:
    """Casefold, drop punctuation, collapse spaces: 'Pvt. Ltd.' == 'pvt ltd'."""
    text = re.sub(r"[^\w\s]", " ", text.casefold())
    return re.sub(r"\s+", " ", text).strip()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text).upper()


def _compare_name(doc: str, ref: str) -> tuple[str, str]:
    a, b = _normalize_name(doc), _normalize_name(ref)
    if a == b:
        return MATCHED, EXACT
    if fuzz.ratio(a, b) >= NAME_SIMILARITY_LOW:
        return MISMATCH, MINOR_SPELLING
    return MISMATCH, NAME_MISMATCH


def _compare_code(doc: str, ref: str) -> tuple[str, str]:
    if _compact(doc) == _compact(ref):
        return MATCHED, EXACT
    return MISMATCH, VALUE_MISMATCH


def _compare_turnover(doc: str, ref: str) -> tuple[str, str]:
    try:
        d, r = Decimal(doc), Decimal(ref)
    except InvalidOperation:
        return PENDING, UNCLEAR_VALUE
    if d == r:
        return MATCHED, EXACT
    if r > 0 and abs(d - r) / r <= Decimal(str(TURNOVER_TOLERANCE)):
        return MATCHED, TURNOVER_WITHIN_TOLERANCE
    if min(d, r) <= 0:
        return MISMATCH, TURNOVER_MAJOR_MISMATCH
    if max(d, r) / min(d, r) >= Decimal(str(TURNOVER_MAJOR_RATIO)):
        return MISMATCH, TURNOVER_MAJOR_MISMATCH
    return MISMATCH, TURNOVER_MINOR_MISMATCH


def crosscheck_field(field: ExtractedField, vendor_id: str) -> CrossCheckResult:
    """Cross-check one extracted field against the reference record."""
    ref = get_reference(vendor_id, field.name)
    ref_value = ref["value"] if ref else None
    ref_source = ref["source"] if ref else None
    is_demo = bool(ref["is_demo"]) if ref else False

    def result(status: str, kind: str) -> CrossCheckResult:
        return CrossCheckResult(
            name=field.name,
            match_status=status,
            kind=kind,
            document_value=field.document_value,
            reference_value=ref_value,
            reference_source=ref_source,
            is_demo_reference=is_demo,
        )

    # nothing was extracted from the document
    if field.document_value is None:
        return result(PENDING, NO_DOCUMENT_VALUE)

    # nothing to compare with
    if ref is None:
        return result(PENDING, REFERENCE_UNAVAILABLE)

    if field.name == "company_name":
        status, kind = _compare_name(field.document_value, ref_value)
    elif field.name == "annual_turnover":
        status, kind = _compare_turnover(field.document_value, ref_value)
    else:  # pan, gstin, udyam_number
        status, kind = _compare_code(field.document_value, ref_value)
    return result(status, kind)


def crosscheck_all(fields: list[ExtractedField], vendor_id: str) -> list[CrossCheckResult]:
    """One result per field, in the same order as the input."""
    return [crosscheck_field(f, vendor_id) for f in fields]