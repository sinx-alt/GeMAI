from tests.sample_inputs import CLEAN, INCONSISTENT
from schemas import Finding
import pytest


def test_samples_load():
    assert len(CLEAN.fields) == 5
    assert len(INCONSISTENT.fields) == 5


def test_not_found_has_no_value():
    udyam = [f for f in CLEAN.fields if f.name == "udyam_number"][0]
    assert udyam.document_value is None and udyam.raw_text is None


def test_finding_rules_enforced():
    with pytest.raises(ValueError):
        Finding(name="gstin", match_status="MISMATCH", explanation="x")  # no risk_level
    with pytest.raises(ValueError):
        Finding(name="gstin", match_status="MATCHED", explanation="x")   # no reference_value