import pytest

from crosscheck import (
    crosscheck_all, MATCHED, MISMATCH, PENDING,
    EXACT, MINOR_SPELLING, NAME_MISMATCH, VALUE_MISMATCH,
    TURNOVER_MINOR_MISMATCH, TURNOVER_MAJOR_MISMATCH,
    NO_DOCUMENT_VALUE, REFERENCE_UNAVAILABLE, UNCLEAR_VALUE,
)
from risk import (
    risk_for_crosscheck, risk_for_review, max_risk, highest_risk,
    FORMAT_INVALID, UNSUPPORTED_EVIDENCE, UNCERTAIN_EXTRACTION, GSTIN_PAN_CONFLICT,
)
from tests.sample_inputs import CLEAN, INCONSISTENT


def test_matched_has_no_risk():
    assert risk_for_crosscheck("pan", MATCHED, EXACT) is None


def test_minor_spelling_is_low():
    assert risk_for_crosscheck("company_name", MISMATCH, MINOR_SPELLING) == "LOW"


def test_gstin_mismatch_is_high():
    assert risk_for_crosscheck("gstin", MISMATCH, VALUE_MISMATCH) == "HIGH"


def test_pan_mismatch_is_high():
    assert risk_for_crosscheck("pan", MISMATCH, VALUE_MISMATCH) == "HIGH"


def test_major_turnover_is_high():
    assert risk_for_crosscheck("annual_turnover", MISMATCH, TURNOVER_MAJOR_MISMATCH) == "HIGH"


def test_minor_turnover_is_medium():
    assert risk_for_crosscheck("annual_turnover", MISMATCH, TURNOVER_MINOR_MISMATCH) == "MEDIUM"


def test_different_company_name_is_medium():
    assert risk_for_crosscheck("company_name", MISMATCH, NAME_MISMATCH) == "MEDIUM"


def test_udyam_mismatch_is_medium():
    assert risk_for_crosscheck("udyam_number", MISMATCH, VALUE_MISMATCH) == "MEDIUM"


def test_missing_document_is_medium():
    assert risk_for_crosscheck("udyam_number", PENDING, NO_DOCUMENT_VALUE) == "MEDIUM"


def test_reference_unavailable_has_no_risk():
    assert risk_for_crosscheck("udyam_number", PENDING, REFERENCE_UNAVAILABLE) is None


def test_unclear_value_is_medium():
    assert risk_for_crosscheck("annual_turnover", PENDING, UNCLEAR_VALUE) == "MEDIUM"


def test_review_reasons_are_medium():
    for reason in [FORMAT_INVALID, UNSUPPORTED_EVIDENCE, UNCERTAIN_EXTRACTION]:
        assert risk_for_review(reason) == "MEDIUM"


def test_gstin_pan_conflict_is_high():
    assert risk_for_review(GSTIN_PAN_CONFLICT) == "HIGH"


def test_unknown_review_reason_raises():
    with pytest.raises(ValueError):
        risk_for_review("made_up_reason")


def test_max_risk():
    assert max_risk(None, None) is None
    assert max_risk(None, "LOW") == "LOW"
    assert max_risk("HIGH", "MEDIUM") == "HIGH"
    assert max_risk("LOW", "MEDIUM") == "MEDIUM"


def test_highest_risk_of_list():
    assert highest_risk([]) is None
    assert highest_risk([None, "LOW", "HIGH", "MEDIUM"]) == "HIGH"


def test_clean_sample_risks():
    results = crosscheck_all(CLEAN.fields, "V001")
    risks = {r.name: risk_for_crosscheck(r.name, r.match_status, r.kind) for r in results}
    assert risks == {
        "company_name": None, "pan": None, "gstin": None,
        "annual_turnover": None, "udyam_number": "MEDIUM",
    }


def test_inconsistent_sample_risks():
    results = crosscheck_all(INCONSISTENT.fields, "V002")
    risks = {r.name: risk_for_crosscheck(r.name, r.match_status, r.kind) for r in results}
    assert risks["company_name"] is None
    assert risks["gstin"] == "HIGH"
    assert risks["annual_turnover"] == "HIGH"
    assert risks["udyam_number"] is None
    assert highest_risk(risks.values()) == "HIGH"