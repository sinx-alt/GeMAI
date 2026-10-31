from evidence import check_evidence, has_source, SUPPORTED, UNSUPPORTED, NO_VALUE
from schemas import ExtractedField
from tests.sample_inputs import CLEAN, INCONSISTENT


def _f(name, value, raw):
    return ExtractedField(name=name, document_value=value, raw_text=raw)


def test_pan_supported_with_spaces_in_raw_text():
    assert check_evidence(_f("pan", "ABCDE1234F", "PAN: ABCDE 1234 F")) == (SUPPORTED, None)


def test_pan_unsupported_and_truncated():
    status, reason = check_evidence(_f("pan", "ABCDE1234F", "PAN: XYZAB9876K"))
    assert status == UNSUPPORTED and "ABCDE1234F" in reason
    # a truncated value must not count as supported by the full number
    assert check_evidence(_f("pan", "ABCDE1234", "PAN: ABCDE1234F"))[0] == UNSUPPORTED


def test_gstin_supported_and_unsupported():
    assert check_evidence(_f("gstin", "06ABCDE1234F1Z5", "GSTIN: 06ABCDE1234F1Z5"))[0] == SUPPORTED
    assert check_evidence(_f("gstin", "06ABCDE1234F1Z5", "GSTIN: 06ABCDE1234F1Z9"))[0] == UNSUPPORTED


def test_company_supported_ignoring_case_and_spacing():
    raw = "Name of Firm:  ACME  traders pvt ltd"
    assert check_evidence(_f("company_name", "Acme Traders Pvt Ltd", raw))[0] == SUPPORTED


def test_company_unsupported():
    raw = "Name of Firm: Beta Supplies"
    assert check_evidence(_f("company_name", "Acme Traders Pvt Ltd", raw))[0] == UNSUPPORTED


def test_turnover_lakh():
    assert check_evidence(_f("annual_turnover", "5000000", "Annual turnover: Rs. 50 lakh"))[0] == SUPPORTED


def test_turnover_with_commas():
    assert check_evidence(_f("annual_turnover", "500000", "Turnover Rs. 5,00,000"))[0] == SUPPORTED


def test_turnover_crore():
    assert check_evidence(_f("annual_turnover", "20000000", "Turnover: 2 crore"))[0] == SUPPORTED


def test_turnover_unsupported():
    status, reason = check_evidence(_f("annual_turnover", "5000000", "Annual turnover: Rs. 5 lakh"))
    assert status == UNSUPPORTED and "5000000" in reason


def test_udyam_supported():
    raw = "Udyam No: UDYAM-HR-01-0000001"
    assert check_evidence(_f("udyam_number", "UDYAM-HR-01-0000001", raw))[0] == SUPPORTED


def test_no_value_is_not_checked():
    assert check_evidence(ExtractedField(name="udyam_number", extraction_status="NOT_FOUND"))[0] == NO_VALUE


def test_missing_raw_text_is_unsupported():
    field = ExtractedField(name="pan", document_value="ABCDE1234F", extraction_status="UNCERTAIN")
    assert check_evidence(field)[0] == UNSUPPORTED


def test_sample_inputs():
    clean = {f.name: check_evidence(f)[0] for f in CLEAN.fields}
    assert clean["udyam_number"] == NO_VALUE
    assert all(v == SUPPORTED for k, v in clean.items() if k != "udyam_number")
    assert all(check_evidence(f)[0] == SUPPORTED for f in INCONSISTENT.fields)


def test_has_source():
    assert has_source(CLEAN.fields[0]) is True
    assert has_source(CLEAN.fields[4]) is False