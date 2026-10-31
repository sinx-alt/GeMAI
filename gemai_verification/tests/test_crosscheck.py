from crosscheck import (
    crosscheck_field, crosscheck_all,
    MATCHED, MISMATCH, PENDING,
    EXACT, MINOR_SPELLING, NAME_MISMATCH, VALUE_MISMATCH,
    TURNOVER_WITHIN_TOLERANCE, TURNOVER_MINOR_MISMATCH, TURNOVER_MAJOR_MISMATCH,
    NO_DOCUMENT_VALUE, REFERENCE_UNAVAILABLE,
)
from schemas import ExtractedField
from tests.sample_inputs import CLEAN, INCONSISTENT


def _f(name, value):
    return ExtractedField(name=name, document_value=value, raw_text="evidence")


def _by_name(results):
    return {r.name: r for r in results}


def test_clean_vendor_matches():
    res = _by_name(crosscheck_all(CLEAN.fields, "V001"))
    for name in ["company_name", "pan", "gstin", "annual_turnover"]:
        assert res[name].match_status == MATCHED and res[name].kind == EXACT
        assert res[name].is_demo_reference is True


def test_clean_udyam_is_pending_no_document():
    r = _by_name(crosscheck_all(CLEAN.fields, "V001"))["udyam_number"]
    assert r.match_status == PENDING and r.kind == NO_DOCUMENT_VALUE
    assert r.reference_value is None


def test_inconsistent_gstin_mismatch():
    r = _by_name(crosscheck_all(INCONSISTENT.fields, "V002"))["gstin"]
    assert r.match_status == MISMATCH and r.kind == VALUE_MISMATCH
    assert r.reference_value == "06ABCDE1234F1Z5"
    assert r.reference_source == "DEMO_REFERENCE_RECORD"


def test_inconsistent_pan_value_mismatch():
    r = _by_name(crosscheck_all(INCONSISTENT.fields, "V002"))["pan"]
    assert r.match_status == MISMATCH and r.kind == VALUE_MISMATCH


def test_inconsistent_turnover_major():
    r = _by_name(crosscheck_all(INCONSISTENT.fields, "V002"))["annual_turnover"]
    assert r.match_status == MISMATCH and r.kind == TURNOVER_MAJOR_MISMATCH
    assert r.document_value == "5000000" and r.reference_value == "500000"


def test_inconsistent_udyam_reference_unavailable():
    r = _by_name(crosscheck_all(INCONSISTENT.fields, "V002"))["udyam_number"]
    assert r.match_status == PENDING and r.kind == REFERENCE_UNAVAILABLE


def test_name_minor_spelling():
    r = crosscheck_field(_f("company_name", "Acme Trader Pvt Ltd"), "V001")
    assert r.match_status == MISMATCH and r.kind == MINOR_SPELLING


def test_name_completely_different():
    r = crosscheck_field(_f("company_name", "Beta Supplies LLP"), "V001")
    assert r.match_status == MISMATCH and r.kind == NAME_MISMATCH


def test_name_case_and_punctuation_ignored():
    r = crosscheck_field(_f("company_name", "ACME TRADERS PVT. LTD."), "V001")
    assert r.match_status == MATCHED and r.kind == EXACT


def test_turnover_within_tolerance():
    r = crosscheck_field(_f("annual_turnover", "5100000"), "V001")  # 2% off
    assert r.match_status == MATCHED and r.kind == TURNOVER_WITHIN_TOLERANCE


def test_turnover_minor_mismatch():
    r = crosscheck_field(_f("annual_turnover", "3000000"), "V001")  # 40% off, under 2x
    assert r.match_status == MISMATCH and r.kind == TURNOVER_MINOR_MISMATCH


def test_unknown_vendor_is_pending():
    r = crosscheck_field(_f("pan", "ABCDE1234F"), "V999")
    assert r.match_status == PENDING and r.kind == REFERENCE_UNAVAILABLE
    assert r.reference_value is None and r.is_demo_reference is False


def test_missing_document_value_keeps_reference():
    field = ExtractedField(name="pan", extraction_status="NOT_FOUND")
    r = crosscheck_field(field, "V001")
    assert r.match_status == PENDING and r.kind == NO_DOCUMENT_VALUE
    assert r.reference_value == "ABCDE1234F"


def test_crosscheck_all_one_result_per_field_in_order():
    results = crosscheck_all(CLEAN.fields, "V001")
    assert [r.name for r in results] == [f.name for f in CLEAN.fields]


def test_code_comparison_ignores_case_and_spaces():
    r = crosscheck_field(_f("pan", "abcde 1234 f"), "V001")
    assert r.match_status == MATCHED