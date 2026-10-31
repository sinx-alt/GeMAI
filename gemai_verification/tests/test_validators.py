from validators import (
    validate_pan, validate_gstin, validate_udyam, validate_turnover,
    validate_company_name, validate_field, gstin_pan_consistent,
)


def test_pan_valid():
    assert validate_pan("ABCDE1234F") == (True, None)


def test_pan_invalid():
    for bad in ["ABCDE1234", "abcde1234f", "ABCDE12345", "ABCDE 1234 F", None]:
        ok, reason = validate_pan(bad)
        assert ok is False and reason


def test_gstin_valid():
    assert validate_gstin("06ABCDE1234F1Z5") == (True, None)


def test_gstin_invalid():
    for bad in ["06ABCDE1234F1Z", "ABCDE1234F1Z5", "06abcde1234f1z5", None]:
        ok, reason = validate_gstin(bad)
        assert ok is False and reason


def test_inconsistent_sample_gstin_passes_format():
    # Right shape but wrong value: this must be caught later by the cross-check.
    assert validate_gstin("06XXXXX9999X1Z5")[0] is True


def test_gstin_pan_consistent():
    assert gstin_pan_consistent("06ABCDE1234F1Z5", "ABCDE1234F") is True


def test_gstin_pan_conflict():
    assert gstin_pan_consistent("06XXXXX9999X1Z5", "ABCDE1234F") is False


def test_gstin_pan_not_assessable():
    assert gstin_pan_consistent("06ABCDE1234F1Z5", "ABCDE1234") is None
    assert gstin_pan_consistent(None, "ABCDE1234F") is None


def test_udyam():
    assert validate_udyam("UDYAM-HR-01-0000001") == (True, None)
    assert validate_udyam("UDYAM-HR-1-1")[0] is False
    assert validate_udyam(None)[0] is False


def test_turnover():
    assert validate_turnover("5000000") == (True, None)
    for bad in ["50 lakh", "0", "-5", "5,000,000", None]:
        assert validate_turnover(bad)[0] is False


def test_company_name():
    assert validate_company_name("Acme Traders Pvt Ltd") == (True, None)
    assert validate_company_name("   ")[0] is False
    assert validate_company_name(None)[0] is False


def test_validate_field_dispatch():
    assert validate_field("pan", "ABCDE1234F")[0] is True
    assert validate_field("gstin", "bad")[0] is False
    assert validate_field("annual_turnover", "5000000")[0] is True