"""
Format and consistency checks. These only look at the SHAPE of a value.
They never fix, guess or fill in anything.

Every function returns (ok, reason):
  ok = True   -> format is valid, reason is None
  ok = False  -> format is invalid, reason explains why using only the stored value
"""

import re

from constants import PAN_REGEX, GSTIN_REGEX, UDYAM_REGEX


def validate_pan(value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return False, "No PAN value was extracted."
    if re.fullmatch(PAN_REGEX, value):
        return True, None
    return False, (
        f"PAN '{value}' does not match the expected format "
        "(5 letters, 4 digits, 1 letter)."
    )


def validate_gstin(value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return False, "No GSTIN value was extracted."
    if re.fullmatch(GSTIN_REGEX, value):
        return True, None
    return False, (
        f"GSTIN '{value}' does not match the expected 15-character GSTIN format."
    )


def validate_udyam(value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return False, "No Udyam number was extracted."
    if re.fullmatch(UDYAM_REGEX, value):
        return True, None
    return False, (
        f"Udyam number '{value}' does not match the expected format "
        "(UDYAM-XX-00-0000000)."
    )


def validate_turnover(value: str | None) -> tuple[bool, str | None]:
    if value is None:
        return False, "No annual turnover value was extracted."
    if not re.fullmatch(r"\d+", value):
        return False, (
            f"Annual turnover '{value}' is not a plain rupee number "
            "(digits only, no commas or symbols)."
        )
    if int(value) <= 0:
        return False, f"Annual turnover '{value}' must be greater than zero."
    return True, None


def validate_company_name(value: str | None) -> tuple[bool, str | None]:
    if value is None or not value.strip():
        return False, "No company name was extracted."
    return True, None


_VALIDATORS = {
    "company_name": validate_company_name,
    "pan": validate_pan,
    "gstin": validate_gstin,
    "annual_turnover": validate_turnover,
    "udyam_number": validate_udyam,
}


def validate_field(name: str, value: str | None) -> tuple[bool, str | None]:
    """Run the right format check for a field name."""
    return _VALIDATORS[name](value)


def gstin_pan_consistent(gstin: str | None, pan: str | None) -> bool | None:
    """
    A GSTIN contains the holder's PAN in characters 3 to 12.
    Returns True if they agree, False if they conflict, and None when it
    cannot be assessed (either value missing or in an invalid format).
    """
    if not validate_gstin(gstin)[0] or not validate_pan(pan)[0]:
        return None
    return gstin[2:12] == pan