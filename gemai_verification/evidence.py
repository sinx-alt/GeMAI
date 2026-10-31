"""
Evidence checks (hallucination / extraction-error safeguard).

Question answered: is document_value actually supported by raw_text?
This never fixes or guesses a value. It only reports SUPPORTED / UNSUPPORTED.

check_evidence returns (status, reason):
  SUPPORTED   -> the value can be found in raw_text
  UNSUPPORTED -> the value cannot be found in raw_text (or raw_text is missing)
  NO_VALUE    -> nothing was extracted, so there is nothing to check
Reasons use only stored values (document_value, raw_text).
"""

import re
from decimal import Decimal, InvalidOperation

from schemas import ExtractedField

SUPPORTED = "SUPPORTED"
UNSUPPORTED = "UNSUPPORTED"
NO_VALUE = "NO_VALUE"

_MULTIPLIERS = {
    "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000,
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "thousand": 1_000,
}

# a number, optionally followed by a unit word such as "lakh" or "crore"
_AMOUNT_RE = re.compile(
    r"(\d[\d,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|thousand)?\b",
    re.IGNORECASE,
)


def _compact(text: str) -> str:
    """Remove all whitespace and uppercase (for PAN / GSTIN / Udyam)."""
    return re.sub(r"\s+", "", text).upper()


def _collapse(text: str) -> str:
    """Collapse whitespace and casefold (for company names)."""
    return re.sub(r"\s+", " ", text).strip().casefold()


def _code_in_text(value: str, raw_text: str) -> bool:
    """
    True if value appears in raw_text as a whole token (ignoring spaces and case).
    The boundary check stops 'ABCDE1234' from being 'supported' by 'ABCDE1234F'.
    """
    pattern = r"(?<![A-Z0-9])" + re.escape(_compact(value)) + r"(?![A-Z0-9])"
    return re.search(pattern, _compact(raw_text)) is not None


def _amounts_in_text(raw_text: str) -> list[Decimal]:
    """Every rupee amount that can be read from raw_text, in plain rupees."""
    amounts = []
    for number, unit in _AMOUNT_RE.findall(raw_text):
        try:
            amount = Decimal(number.replace(",", ""))
        except InvalidOperation:
            continue
        multiplier = _MULTIPLIERS.get(unit.lower(), 1) if unit else 1
        amounts.append(amount * multiplier)
    return amounts


def _turnover_in_text(value: str, raw_text: str) -> bool:
    try:
        target = Decimal(value)
    except InvalidOperation:
        return False
    return any(amount == target for amount in _amounts_in_text(raw_text))


_LABELS = {
    "company_name": "Company name",
    "pan": "PAN",
    "gstin": "GSTIN",
    "annual_turnover": "Annual turnover",
    "udyam_number": "Udyam number",
}


def check_evidence(field: ExtractedField) -> tuple[str, str | None]:
    """Check one extracted field against its own raw_text."""
    if field.document_value is None:
        return NO_VALUE, "No value was extracted, so there is nothing to check against the evidence."

    label = _LABELS[field.name]
    value, raw = field.document_value, field.raw_text

    if not raw or not raw.strip():
        return UNSUPPORTED, f"{label} '{value}' has no raw_text evidence to support it."

    if field.name == "company_name":
        found = _collapse(value) in _collapse(raw)
    elif field.name == "annual_turnover":
        found = _turnover_in_text(value, raw)
    else:  # pan, gstin, udyam_number
        found = _code_in_text(value, raw)

    if found:
        return SUPPORTED, None
    return UNSUPPORTED, f"{label} '{value}' was not found in the raw text '{raw}'."


def has_source(field: ExtractedField) -> bool:
    """True if the field says which file it came from (page is optional)."""
    return bool(field.document_source and field.document_source.file)