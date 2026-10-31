"""
Mock reference records for the hackathon demo.

IMPORTANT: this is SIMULATED data. It is NOT a live response from GSTN,
Income Tax, Udyam or any government system. Every value returned from here
must be labelled with DEMO_SOURCE and is_demo_reference=True.

A field set to None means "reference unavailable" -> the check must become
PENDING ("Verification Pending"), never a failure.
"""

from constants import DEMO_SOURCE

DEMO_REFERENCE_RECORDS = {
    # V001: clean vendor. Reference agrees with the document.
    "V001": {
        "company_name": "Acme Traders Pvt Ltd",
        "pan": "ABCDE1234F",
        "gstin": "06ABCDE1234F1Z5",
        "annual_turnover": "5000000",
        "udyam_number": None,          # unavailable -> PENDING
    },
    # V002: deliberately inconsistent vendor.
    "V002": {
        "company_name": "Acme Traders Pvt Ltd",
        "pan": "ABCDE1234F",
        "gstin": "06ABCDE1234F1Z5",    # document says 06XXXXX9999X1Z5
        "annual_turnover": "500000",   # document says 5000000 (10x higher)
        "udyam_number": None,          # unavailable -> PENDING
    },
}


def get_reference(vendor_id: str, field_name: str) -> dict | None:
    """
    Return {"value", "source", "is_demo"} for one field of one vendor,
    or None when the reference is unavailable (unknown vendor, or the
    field has no reference value).
    """
    record = DEMO_REFERENCE_RECORDS.get(vendor_id)
    if record is None:
        return None
    value = record.get(field_name)
    if value is None:
        return None
    return {"value": value, "source": DEMO_SOURCE, "is_demo": True}