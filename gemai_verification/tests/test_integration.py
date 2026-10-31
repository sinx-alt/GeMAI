import pytest
from pydantic import ValidationError

from integration import merge_fields, verify_extraction, verify_payload, verify_vendor
from report import build_report
from schemas import ExtractedField, ExtractionResponse
from tests.sample_inputs import CLEAN, INCONSISTENT


def _resp(vendor, doc, fields, status="PARTIAL"):
    return ExtractionResponse(vendor_id=vendor, document_id=doc, fields=fields, status=status)


def test_single_extraction_equals_direct_build_report():
    report = verify_extraction(_resp("V002", "D1", INCONSISTENT.fields))
    direct = build_report(INCONSISTENT)
    assert report.verification_status == direct.verification_status
    assert report.highest_risk == direct.highest_risk
    assert report.pending_checks == direct.pending_checks


def test_payload_round_trip_is_json():
    payload = _resp("V001", "D1", CLEAN.fields).model_dump(mode="json")
    result = verify_payload(payload)
    assert isinstance(result, dict)
    assert result["vendor_id"] == "V001"
    assert result["human_decision_required"] is True
    assert result["pending_checks"] == ["udyam_number"]


def test_merge_combines_documents():
    pan_doc = _resp("V001", "D1", [
        ExtractedField(name="pan", document_value="ABCDE1234F", raw_text="PAN: ABCDE1234F"),
        ExtractedField(name="gstin", extraction_status="NOT_FOUND"),
    ])
    gst_doc = _resp("V001", "D2", [
        ExtractedField(name="gstin", document_value="06ABCDE1234F1Z5",
                       raw_text="GSTIN: 06ABCDE1234F1Z5"),
        ExtractedField(name="pan", extraction_status="NOT_FOUND"),
    ])
    merged = {f.name: f for f in merge_fields([pan_doc, gst_doc])}
    assert merged["pan"].document_value == "ABCDE1234F"
    assert merged["gstin"].document_value == "06ABCDE1234F1Z5"


def test_merge_prefers_extracted_over_uncertain():
    uncertain = _resp("V001", "D1", [
        ExtractedField(name="udyam_number", document_value="UDYAM-HR-01-0000001",
                       raw_text="Udyam No: UDYAM-HR-01-0000001", extraction_status="UNCERTAIN"),
    ])
    clear = _resp("V001", "D2", [
        ExtractedField(name="udyam_number", document_value="UDYAM-HR-01-0000001",
                       raw_text="Udyam No: UDYAM-HR-01-0000001"),
    ])
    merged = merge_fields([uncertain, clear])
    assert merged[0].extraction_status == "EXTRACTED"


def test_multi_document_vendor_verifies():
    docs = [
        _resp("V001", "D1", [f for f in CLEAN.fields if f.name in ("pan", "company_name")]),
        _resp("V001", "D2", [f for f in CLEAN.fields if f.name in ("gstin", "annual_turnover")]),
    ]
    report = verify_vendor(docs)
    by_name = {f.name: f for f in report.fields}
    assert by_name["pan"].match_status == "MATCHED"
    assert by_name["gstin"].match_status == "MATCHED"
    assert by_name["udyam_number"].match_status == "PENDING"


def test_failed_extraction_does_not_crash():
    report = verify_extraction(_resp("V001", "D1", [], status="FAILED"))
    assert len(report.fields) == 5
    assert all(f.match_status == "PENDING" for f in report.fields)
    assert report.human_decision_required is True


def test_invalid_payload_is_rejected():
    bad = {"vendor_id": "V001", "document_id": "D1", "status": "SUCCESS",
           "fields": [{"name": "not_a_field", "document_value": "x", "raw_text": "x"}]}
    with pytest.raises(ValidationError):
        verify_payload(bad)


def test_empty_list_is_rejected():
    with pytest.raises(ValueError):
        verify_vendor([])


def test_mixed_vendors_are_rejected():
    with pytest.raises(ValueError):
        verify_vendor([_resp("V001", "D1", []), _resp("V002", "D2", [])])