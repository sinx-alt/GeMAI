from reference_data import get_reference, DEMO_REFERENCE_RECORDS
from constants import DEMO_SOURCE, ALL_FIELDS


def test_known_value_is_labelled_demo():
    ref = get_reference("V001", "pan")
    assert ref["value"] == "ABCDE1234F"
    assert ref["source"] == DEMO_SOURCE
    assert ref["is_demo"] is True


def test_unavailable_field_returns_none():
    assert get_reference("V001", "udyam_number") is None


def test_unknown_vendor_returns_none():
    assert get_reference("V999", "pan") is None


def test_every_vendor_covers_all_fields():
    for record in DEMO_REFERENCE_RECORDS.values():
        assert set(record.keys()) == set(ALL_FIELDS)


def test_inconsistent_vendor_differs_where_expected():
    assert get_reference("V002", "gstin")["value"] == "06ABCDE1234F1Z5"
    assert get_reference("V002", "annual_turnover")["value"] == "500000"