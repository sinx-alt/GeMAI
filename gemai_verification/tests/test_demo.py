import json

from demo import build_report
from schemas import ExtractedField, VerificationInput, VerificationReport
from tests.sample_inputs import CLEAN, INCONSISTENT


def _by_name(report):
    return {f.name: f for f in report.fields}


def test_clean_report():
    report = build_report(CLEAN)
    assert isinstance(report, VerificationReport)
    assert report.verification_status == "REVIEW_REQUIRED"
    assert report.highest_risk == "MEDIUM"
    assert report.pending_checks == ["udyam_number"]


def test_inconsistent_report():
    report = build_report(INCONSISTENT)
    assert report.verification_status == "REVIEW_REQUIRED"
    assert report.highest_risk == "HIGH"
    assert report.pending_checks == ["pan", "udyam_number"]


def test_human_decision_always_required():
    for sample in (CLEAN, INCONSISTENT):
        assert build_report(sample).human_decision_required is True


def test_report_is_json_serialisable():
    data = json.loads(json.dumps(build_report(INCONSISTENT).model_dump(mode="json")))
    assert data["vendor_id"] == "V002"
    assert data["human_decision_required"] is True


def test_extracted_values_are_never_changed():
    for sample in (CLEAN, INCONSISTENT):
        extracted = {f.name: f for f in sample.fields}
        for rf in build_report(sample).fields:
            assert rf.document_value == extracted[rf.name].document_value
            assert rf.raw_text == extracted[rf.name].raw_text


def test_report_lists_source_files():
    assert build_report(CLEAN).files == ["fin.pdf", "gst.pdf", "pan.pdf"]


def test_demo_checklist_from_project_doc():
    clean = _by_name(build_report(CLEAN))
    bad = _by_name(build_report(INCONSISTENT))
    # one correct match
    assert bad["company_name"].match_status == "MATCHED"
    # one extraction uncertainty
    assert "uncertain" in bad["udyam_number"].explanation.lower()
    # one high-risk mismatch
    assert bad["annual_turnover"].match_status == "MISMATCH"
    assert bad["annual_turnover"].risk_level == "HIGH"
    # unavailable reference data becomes Pending, not Failed
    assert clean["udyam_number"].match_status == "PENDING"


def test_empty_input_does_not_crash():
    report = build_report(VerificationInput(vendor_id="V001", fields=[]))
    assert len(report.fields) == 5
    assert all(f.match_status == "PENDING" for f in report.fields)
    assert all(f.extraction_status == "NOT_FOUND" for f in report.fields)
    assert report.human_decision_required is True


def test_duplicate_field_first_one_wins():
    extra = ExtractedField(
        name="pan", document_value="ZZZZZ9999Z", raw_text="PAN: ZZZZZ9999Z",
    )
    data = VerificationInput(vendor_id="V001", fields=list(CLEAN.fields) + [extra])
    report = build_report(data)
    assert len(report.fields) == 5
    assert _by_name(report)["pan"].document_value == "ABCDE1234F"
    assert _by_name(report)["pan"].match_status == "MATCHED"


def test_turnover_field_has_the_shape_from_project_doc_section_8():
    dump = _by_name(build_report(INCONSISTENT))["annual_turnover"].model_dump()
    required = {
        "name", "document_value", "document_source", "reference_value",
        "reference_source", "match_status", "risk_level", "explanation",
    }
    assert required <= set(dump.keys())
    assert dump["document_source"] == {"file": "fin.pdf", "page": 3}


def test_no_explanation_calls_a_vendor_fraudulent():
    for sample in (CLEAN, INCONSISTENT):
        for f in build_report(sample).fields:
            assert "fraud" not in f.explanation.lower()


def test_every_mismatch_has_a_risk_level():
    for sample in (CLEAN, INCONSISTENT):
        for f in build_report(sample).fields:
            if f.match_status == "MISMATCH":
                assert f.risk_level is not None


def test_every_reference_value_is_labelled_demo():
    for sample in (CLEAN, INCONSISTENT):
        for f in build_report(sample).fields:
            if f.reference_value is not None:
                assert f.is_demo_reference is True
                assert f.reference_source == "DEMO_REFERENCE_RECORD"