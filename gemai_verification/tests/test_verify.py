from schemas import ExtractedField, Finding, VerificationInput, VerificationOutput
from tests.sample_inputs import CLEAN, INCONSISTENT
from verify import verify, verify_with_status, overall_status


def _f(name, value, raw):
    return ExtractedField(name=name, document_value=value, raw_text=raw)


def _with(sample, vendor=None, **replacements):
    fields = [replacements.get(f.name, f) for f in sample.fields]
    return VerificationInput(vendor_id=vendor or sample.vendor_id, fields=fields)


def _by_name(output):
    return {f.name: f for f in output.findings}


def test_returns_verification_output():
    assert isinstance(verify(CLEAN), VerificationOutput)


def test_one_finding_per_field_in_order():
    out = verify(CLEAN)
    assert [f.name for f in out.findings] == [f.name for f in CLEAN.fields]


def test_clean_findings():
    res = _by_name(verify(CLEAN))
    for name in ["company_name", "pan", "gstin", "annual_turnover"]:
        assert res[name].match_status == "MATCHED" and res[name].risk_level is None
    assert res["udyam_number"].match_status == "PENDING"
    assert res["udyam_number"].risk_level == "MEDIUM"


def test_clean_pending_checks():
    assert verify(CLEAN).pending_checks == ["udyam_number"]


def test_clean_overall_status():
    s = verify_with_status(CLEAN)
    assert s.verification_status == "REVIEW_REQUIRED"
    assert s.highest_risk == "MEDIUM"


def test_inconsistent_pan_bad_format_goes_to_review():
    f = _by_name(verify(INCONSISTENT))["pan"]
    assert f.match_status == "PENDING" and f.risk_level == "MEDIUM"
    assert "expected format" in f.explanation and "human review" in f.explanation


def test_inconsistent_gstin_is_high_mismatch():
    f = _by_name(verify(INCONSISTENT))["gstin"]
    assert f.match_status == "MISMATCH" and f.risk_level == "HIGH"
    assert "06XXXXX9999X1Z5" in f.explanation and "06ABCDE1234F1Z5" in f.explanation


def test_inconsistent_turnover_is_high_mismatch():
    f = _by_name(verify(INCONSISTENT))["annual_turnover"]
    assert f.match_status == "MISMATCH" and f.risk_level == "HIGH"
    assert f.reference_value == "500000"


def test_inconsistent_udyam_uncertain_goes_to_review():
    f = _by_name(verify(INCONSISTENT))["udyam_number"]
    assert f.match_status == "PENDING" and f.risk_level == "MEDIUM"
    assert "uncertain" in f.explanation


def test_inconsistent_pending_checks():
    assert verify(INCONSISTENT).pending_checks == ["pan", "udyam_number"]


def test_inconsistent_overall_status():
    s = verify_with_status(INCONSISTENT)
    assert s.verification_status == "REVIEW_REQUIRED"
    assert s.highest_risk == "HIGH"
    assert s.human_decision_required is True


def test_demo_reference_always_labelled():
    for sample in (CLEAN, INCONSISTENT):
        for f in verify(sample).findings:
            if f.reference_value is not None:
                assert f.is_demo_reference is True
                assert f.reference_source == "DEMO_REFERENCE_RECORD"


def test_missing_fields_are_added_as_not_found():
    data = VerificationInput(vendor_id="V001", fields=[
        _f("pan", "ABCDE1234F", "PAN: ABCDE1234F"),
    ])
    out = verify(data)
    assert len(out.findings) == 5
    assert _by_name(out)["gstin"].match_status == "PENDING"


def test_unsupported_evidence_goes_to_review():
    bad = _f("gstin", "06ABCDE1234F1Z5", "GSTIN: 06ABCDE1234F1Z9")
    f = _by_name(verify(_with(CLEAN, gstin=bad)))["gstin"]
    assert f.match_status == "PENDING" and f.risk_level == "MEDIUM"
    assert "not found in the raw text" in f.explanation


def test_gstin_pan_conflict_is_high():
    bad = _f("gstin", "06XXXXX9999X1Z5", "GSTIN: 06XXXXX9999X1Z5")
    f = _by_name(verify(_with(CLEAN, gstin=bad)))["gstin"]
    assert f.risk_level == "HIGH"
    assert "'XXXXX9999X'" in f.explanation and "'ABCDE1234F'" in f.explanation


def test_all_references_unavailable_is_pending_not_failure():
    udyam = _f("udyam_number", "UDYAM-HR-01-0000001", "Udyam No: UDYAM-HR-01-0000001")
    s = verify_with_status(_with(CLEAN, vendor="V999", udyam_number=udyam))
    assert s.verification_status == "PENDING"
    assert s.highest_risk is None
    assert len(s.output.pending_checks) == 5


def test_overall_status_no_issues():
    findings = [
        Finding(name="pan", reference_value="X", reference_source="S",
                match_status="MATCHED", explanation="ok"),
    ]
    assert overall_status(findings) == "NO_ISSUES_FOUND"


def test_input_is_never_modified():
    before = INCONSISTENT.model_dump()
    verify(INCONSISTENT)
    assert INCONSISTENT.model_dump() == before