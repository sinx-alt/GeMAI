
from app.schemas import (
    DocumentSource,
    ExtractedField,
    ExtractionResponse,
)


def test_extracted_field():
    field = ExtractedField(
        name="pan",
        document_value="ABCDE1234F",
        raw_text="PAN: ABCDE1234F",
        document_source=DocumentSource(
            file="pan_card.pdf",
            page=1
        ),
        document_type="PAN",
        confidence=0.98,
        extraction_status="EXTRACTED"
    )

    assert field.name == "pan"
    assert field.document_value == "ABCDE1234F"


def test_extraction_response():
    response = ExtractionResponse(
        vendor_id="V001",
        document_id="D001",
        fields=[],
        status="SUCCESS"
    )

    assert response.vendor_id == "V001"
    assert response.status == "SUCCESS"
