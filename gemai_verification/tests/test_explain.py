import pytest

from crosscheck import CrossCheckResult, crosscheck_all, crosscheck_field
from explain import explain_crosscheck, explain_review
from risk import (
    FORMAT_INVALID, UNSUPPORTED_EVIDENCE, UNCERTAIN_EXTRACTION, GSTIN_PAN_CONFLICT,
)
from schemas import ExtractedField, DocumentSource
from tests.sample_inputs import CLEAN, INCONSISTENT


def _f(name, value):
    return ExtractedField(name=name, document_value=value, raw_text="evidence")


def _res(sample, vendor, name):
    results = {r.name: r for r in crosscheck_all(sample.fields, vendor)}
    return results[name]


def _src(sample, name):
    return {f.name: f for f in sample.fields}[name].document_source


def test_match_is_grounded_and_labelled_demo():
    text = explain_crosscheck(_res(CLEAN, "V001", "pan"), _src(CLEAN, "pan"))
    assert "ABCDE1234F" in text and "matches" in text
    assert "DEMO_REFERENCE_RECORD" in text and "simulated demo data" in text
    assert "pan.pdf, page 1" in text


def test_within_tolerance():
    text = explain_crosscheck(crosscheck_field(_f("annual_turnover", "5100000"), "V001"))
    assert "5100000" in text and "5%" in text and "matching" in text


def test_minor_spelling():
    text = explain_crosscheck(crosscheck_field(_f("company_name", "Acme Trader Pvt Ltd"), "V001"))
    assert "minor spelling" in text and "Acme Trader Pvt Ltd" in text


def test_turnover_major_mismatch_shows_both_values():
    text = explain_crosscheck(
        _res(INCONSISTENT, "V002", "annual_turnover"), _src(INCONSISTENT, "annual_turnover")
    )
    assert "5000000" in text and "500000" in text
    assert "fin.pdf, page 3" in text and "review" in text.lower()


def test_gstin_mismatch_shows_both_values():
    text = explain_crosscheck(_res(INCONSISTENT, "V002", "gstin"), _src(INCONSISTENT, "gstin"))
    assert "06XXXXX9999X1Z5" in text and "06ABCDE1234F1Z5" in text
    assert "does not match" in text


def test_reference_unavailable_is_pending_not_failure():
    text = explain_crosscheck(
        _res(INCONSISTENT, "V002", "udyam_number"), _src(INCONSISTENT, "udyam_number")
    )
    assert "Verification Pending" in text and "not a failure" in text
    assert "UDYAM-HR-01-0000001" in text


def test_no_document_value_and_no_reference():
    text = explain_crosscheck(_res(CLEAN, "V001", "udyam_number"))
    assert "No Udyam number was extracted" in text
    assert "reference value" not in text


def test_no_document_value_with_reference():
    text = explain_crosscheck(crosscheck_field(ExtractedField(name="pan", extraction_status="NOT_FOUND"), "V001"))
    assert "No PAN was extracted" in text and "ABCDE1234F" in text


def test_unclear_value():
    text = explain_crosscheck(crosscheck_field(_f("annual_turnover", "abc"), "V001"))
    assert "could not be read as a number" in text and "abc" in text


def test_unknown_kind_raises():
    bad = CrossCheckResult(
        name="pan", match_status="MISMATCH", kind="weird",
        document_value="a", reference_value="b",
        reference_source="S", is_demo_reference=True,
    )
    with pytest.raises(ValueError):
        explain_crosscheck(bad)


def test_review_format_invalid_uses_detail():
    detail = "PAN 'ABCDE1234' does not match the expected format (5 letters, 4 digits, 1 letter)."
    text = explain_review("pan", FORMAT_INVALID, detail=detail)
    assert detail in text and "human review" in text and "not compared" in text


def test_review_unsupported_evidence():
    detail = "GSTIN '06ABCDE1234F1Z5' was not found in the raw text 'GSTIN: 06ABCDE1234F1Z9'."
    text = explain_review("gstin", UNSUPPORTED_EVIDENCE, detail=detail)
    assert detail in text and "human review" in text


def test_review_uncertain_with_value():
    text = explain_review(
        "udyam_number", UNCERTAIN_EXTRACTION,
        document_value="UDYAM-HR-01-0000001",
        raw_text="Udyam No: UDYAM-HR-01-0000001",
        source=DocumentSource(file="udyam.pdf", page=1),
    )
    assert "uncertain" in text and "UDYAM-HR-01-0000001" in text
    assert "udyam.pdf, page 1" in text


def test_review_uncertain_without_value():
    text = explain_review("pan", UNCERTAIN_EXTRACTION)
    assert "uncertain" in text and "no value was kept" in text


def test_review_gstin_pan_conflict():
    text = explain_review("gstin", GSTIN_PAN_CONFLICT)
    assert "PAN" in text and "Human review" in text


def test_unknown_review_reason_raises():
    with pytest.raises(ValueError):
        explain_review("pan", "made_up_reason")


def test_every_sample_explanation_contains_its_stored_values():
    for sample, vendor in [(CLEAN, "V001"), (INCONSISTENT, "V002")]:
        for r in crosscheck_all(sample.fields, vendor):
            text = explain_crosscheck(r)
            assert text
            if r.document_value is not None:
                assert r.document_value in text
            if r.reference_value is not None:
                assert r.reference_value in text


def test_no_source_means_no_where_text():
    text = explain_crosscheck(_res(CLEAN, "V001", "pan"))
    assert "(from" not in text