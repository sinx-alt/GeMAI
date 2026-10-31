"""
Risk rules. Pure rules, no guessing.

risk_for_crosscheck(name, match_status, kind) -> "LOW" | "MEDIUM" | "HIGH" | None
risk_for_review(reason)                       -> risk for format/evidence/uncertainty problems
max_risk / highest_risk                       -> highest level among several

None means "no risk to flag" (for example MATCHED, or reference unavailable,
which is shown as Verification Pending and is never a failure).
"""

from constants import RISK_RULES
from crosscheck import (
    MATCHED, MISMATCH, PENDING,
    MINOR_SPELLING, TURNOVER_MAJOR_MISMATCH, TURNOVER_MINOR_MISMATCH,
    NO_DOCUMENT_VALUE, UNCLEAR_VALUE,
)

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

RISK_ORDER = {LOW: 1, MEDIUM: 2, HIGH: 3}

# Reasons used when a value needs human review before any comparison (Work 8)
FORMAT_INVALID = "format_invalid"
UNSUPPORTED_EVIDENCE = "unsupported_evidence"
UNCERTAIN_EXTRACTION = "uncertain_extraction"
GSTIN_PAN_CONFLICT = "gstin_pan_conflict"

_REVIEW_RISK = {
    FORMAT_INVALID: MEDIUM,
    UNSUPPORTED_EVIDENCE: MEDIUM,
    UNCERTAIN_EXTRACTION: MEDIUM,
    GSTIN_PAN_CONFLICT: RISK_RULES["gstin_mismatch"],   # HIGH
}


def risk_for_crosscheck(name: str, match_status: str, kind: str) -> str | None:
    """Risk for one cross-check result."""
    if match_status == MATCHED:
        return None

    if match_status == PENDING:
        if kind == NO_DOCUMENT_VALUE:
            return RISK_RULES["missing_document"]       # MEDIUM
        if kind == UNCLEAR_VALUE:
            return MEDIUM
        return None                                     # reference unavailable -> Pending

    # MISMATCH
    if kind == MINOR_SPELLING:
        return RISK_RULES["minor_spelling"]             # LOW
    if kind == TURNOVER_MAJOR_MISMATCH:
        return RISK_RULES["major_turnover_mismatch"]    # HIGH
    if kind == TURNOVER_MINOR_MISMATCH:
        return MEDIUM
    if name == "gstin":
        return RISK_RULES["gstin_mismatch"]             # HIGH
    if name == "pan":
        return HIGH
    return MEDIUM                                       # different company name, udyam mismatch


def risk_for_review(reason: str) -> str:
    """Risk when a value is unclear, unsupported or conflicting."""
    if reason not in _REVIEW_RISK:
        raise ValueError(f"Unknown review reason: {reason}")
    return _REVIEW_RISK[reason]


def max_risk(a: str | None, b: str | None) -> str | None:
    """The higher of two risk levels. None counts as lowest."""
    if a is None:
        return b
    if b is None:
        return a
    return a if RISK_ORDER[a] >= RISK_ORDER[b] else b


def highest_risk(levels) -> str | None:
    """The highest level in a list, or None when the list has no risk."""
    result = None
    for level in levels:
        result = max_risk(result, level)
    return result