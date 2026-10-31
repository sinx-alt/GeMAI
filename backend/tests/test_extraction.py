from app.services.extraction_service import extract_fields
from app.services.pdf_reader import PageText, PDFContent


def make_content(*page_texts, file="financials.pdf"):
    pages = [
        PageText(page=i, text=t, has_text=bool(t.strip()), char_count=len(t))
        for i, t in enumerate(page_texts, start=1)
    ]
    without = [p.page for p in pages if not p.has_text]
    return PDFContent(
        file=file,
        total_pages=len(pages),
        pages=pages,
        has_extractable_text=len(without) < len(pages),
        pages_without_text=without,
    )


def get(fields, name):
    return next(f for f in fields if f.name == name)


def test_returns_all_five_fields():
    fields = extract_fields(make_content("nothing useful here"))
    assert [f.name for f in fields] == [
        "company_name", "pan", "gstin", "annual_turnover", "udyam_number"
    ]


def test_missing_fields_are_not_found_without_value():
    f = get(extract_fields(make_content("nothing useful here")), "pan")
    assert f.extraction_status == "NOT_FOUND"
    assert f.document_value is None and f.raw_text is None


def test_pan_with_page_and_snippet():
    fields = extract_fields(make_content("cover page", "PAN: abcde1234f\nother"))
    f = get(fields, "pan")
    assert f.extraction_status == "EXTRACTED"
    assert f.document_value == "ABCDE1234F"
    assert f.document_source.page == 2
    assert f.document_source.file == "financials.pdf"
    assert "abcde1234f" in f.raw_text.lower()


def test_gstin_found_and_pan_not_taken_from_inside_it():
    fields = extract_fields(make_content("GSTIN: 07ABCDE1234F1Z5"))
    assert get(fields, "gstin").document_value == "07ABCDE1234F1Z5"
    assert get(fields, "pan").extraction_status == "NOT_FOUND"


def test_udyam_is_normalized():
    f1 = get(extract_fields(make_content("UDYAM-DL-12-3456789")), "udyam_number")
    assert f1.document_value == "UDYAM-DL-12-3456789"
    f2 = get(extract_fields(make_content("UDYAMDL123456789")), "udyam_number")
    assert f2.document_value == "UDYAM-DL-12-3456789"
    f3 = get(extract_fields(make_content("udyam dl 12 3456789")), "udyam_number")
    assert f3.document_value == "UDYAM-DL-12-3456789"


def test_turnover_lakh_is_converted_to_rupees():
    f = get(extract_fields(make_content("Annual Turnover: ₹50 lakh")), "annual_turnover")
    assert f.document_value == "5000000"
    assert "50 lakh" in f.raw_text


def test_turnover_indian_commas_and_rs():
    f = get(extract_fields(make_content("Total Turnover Rs. 5,00,00,000/-")), "annual_turnover")
    assert f.document_value == "50000000"


def test_turnover_crore():
    f = get(extract_fields(make_content("Annual turnover: Rs 2.5 crore")), "annual_turnover")
    assert f.document_value == "25000000"


def test_turnover_ignores_financial_year():
    f = get(extract_fields(make_content("Turnover for FY 2023-24: ₹50 lakh")), "annual_turnover")
    assert f.document_value == "5000000"


def test_turnover_bare_number_has_lower_confidence():
    f = get(extract_fields(make_content("Annual Turnover: 5000000")), "annual_turnover")
    assert f.document_value == "5000000"
    assert f.confidence < 0.85


def test_turnover_value_on_next_line():
    f = get(extract_fields(make_content("Annual Turnover\n₹ 50 lakh")), "annual_turnover")
    assert f.document_value == "5000000"


def test_turnover_does_not_take_digits_from_a_pan_on_next_line():
    f = get(extract_fields(make_content("Annual Turnover\nPAN: ABCDE1234F")), "annual_turnover")
    assert f.extraction_status == "NOT_FOUND"


def test_conflicting_turnover_is_uncertain_with_no_value():
    text = "Turnover FY 2022-23: ₹40 lakh\nTurnover FY 2023-24: ₹50 lakh"
    f = get(extract_fields(make_content(text)), "annual_turnover")
    assert f.extraction_status == "UNCERTAIN"
    assert f.document_value is None
    assert "40 lakh" in f.raw_text and "50 lakh" in f.raw_text


def test_same_value_on_two_pages_is_not_a_conflict():
    f = get(extract_fields(make_content("PAN: ABCDE1234F", "PAN No ABCDE1234F")), "pan")
    assert f.extraction_status == "EXTRACTED"
    assert f.document_source.page == 1


def test_company_name_same_line():
    text = "Name of the Company: Sharma Traders Pvt. Ltd.\nPAN: ABCDE1234F"
    f = get(extract_fields(make_content(text)), "company_name")
    assert f.document_value == "Sharma Traders Pvt. Ltd."


def test_company_name_on_next_line():
    f = get(extract_fields(make_content("Name of Enterprise\nSHARMA TRADERS\nType: Micro")), "company_name")
    assert f.document_value == "SHARMA TRADERS"


def test_company_name_rejects_next_label():
    f = get(extract_fields(make_content("Company Name\nPAN: ABCDE1234F")), "company_name")
    assert f.extraction_status == "NOT_FOUND"


def test_unreadable_page_makes_missing_fields_uncertain_not_not_found():
    f = get(extract_fields(make_content("PAN: ABCDE1234F", "")), "gstin")
    assert f.extraction_status == "UNCERTAIN"
    assert f.document_value is None


def test_fully_scanned_pdf_is_all_uncertain():
    fields = extract_fields(make_content("", ""))
    assert all(f.extraction_status == "UNCERTAIN" for f in fields)