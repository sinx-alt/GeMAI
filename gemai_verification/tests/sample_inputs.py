from schemas import ExtractedField, DocumentSource, VerificationInput


def _src(f, p):
    return DocumentSource(file=f, page=p)


CLEAN = VerificationInput(vendor_id="V001", fields=[
    ExtractedField(name="company_name", document_value="Acme Traders Pvt Ltd",
        raw_text="Name of Firm: Acme Traders Pvt Ltd", document_source=_src("gst.pdf", 1)),
    ExtractedField(name="pan", document_value="ABCDE1234F",
        raw_text="PAN: ABCDE 1234 F", document_source=_src("pan.pdf", 1)),
    ExtractedField(name="gstin", document_value="06ABCDE1234F1Z5",
        raw_text="GSTIN: 06ABCDE1234F1Z5", document_source=_src("gst.pdf", 1)),
    ExtractedField(name="annual_turnover", document_value="5000000",
        raw_text="Annual turnover: Rs. 50 lakh", document_source=_src("fin.pdf", 3)),
    ExtractedField(name="udyam_number", extraction_status="NOT_FOUND"),
])

INCONSISTENT = VerificationInput(vendor_id="V002", fields=[
    ExtractedField(name="company_name", document_value="Acme Traders Pvt Ltd",
        raw_text="Name of Firm: Acme Traders Pvt Ltd", document_source=_src("gst.pdf", 1)),
    ExtractedField(name="pan", document_value="ABCDE1234",
        raw_text="PAN: ABCDE1234", document_source=_src("pan.pdf", 1)),
    ExtractedField(name="gstin", document_value="06XXXXX9999X1Z5",
        raw_text="GSTIN: 06XXXXX9999X1Z5", document_source=_src("gst.pdf", 1)),
    ExtractedField(name="annual_turnover", document_value="5000000",
        raw_text="Annual turnover: Rs. 50 lakh", document_source=_src("fin.pdf", 3)),
    ExtractedField(name="udyam_number", document_value="UDYAM-HR-01-0000001",
        raw_text="Udyam No: UDYAM-HR-01-0000001", extraction_status="UNCERTAIN",
        document_source=_src("udyam.pdf", 1)),
])