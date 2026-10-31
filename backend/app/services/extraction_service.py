"""
Rule-based field extraction from PDF text (Member 2 -> Member 3 handoff).

Reads a PDFContent (page-by-page text from pdf_reader.py) and returns one
ExtractedField per field name, each with the exact snippet and page it came from.

Rules:
- Never guess. Not found -> NOT_FOUND. Conflicting values -> UNCERTAIN, no value.
- If some pages had no text (scans), a missing field is UNCERTAIN, not NOT_FOUND,
  because the value may be on a page we could not read.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable

from app.schemas import DocumentSource, ExtractedField
from app.services.pdf_reader import PageText, PDFContent

MAX_SNIPPET_CHARS = 250

# Rough rule-based scores, NOT probabilities. Fixed-format IDs are the most reliable.
CONF_ID_FORMAT = 0.95
CONF_TURNOVER_STRONG = 0.85   # keyword + currency symbol or lakh/crore unit
CONF_TURNOVER_BARE = 0.6      # keyword + plain number only
CONF_COMPANY = 0.7


@dataclass
class Candidate:
    value: str
    raw_text: str
    page: int
    confidence: float


# -------------------------------
# Helpers
# -------------------------------

def _line_end(text: str, pos: int) -> int:
    idx = text.find("\n", pos)
    return len(text) if idx == -1 else idx


def _snippet(text: str, start: int, end: int) -> str:
    """The line(s) around a match, whitespace collapsed, capped in length."""
    line_start = text.rfind("\n", 0, start) + 1
    line_end = _line_end(text, end)
    if line_end - line_start > MAX_SNIPPET_CHARS:
        line_start = max(line_start, start - 100)
        line_end = min(line_end, end + 100)
    return re.sub(r"\s+", " ", text[line_start:line_end]).strip()


# -------------------------------
# PAN, GSTIN, Udyam (fixed formats)
# -------------------------------

# The look-arounds stop a PAN being matched inside a GSTIN (which contains one).
PAN_RE = re.compile(r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])", re.IGNORECASE)
GSTIN_RE = re.compile(
    r"(?<![A-Z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Z0-9])",
    re.IGNORECASE,
)
UDYAM_RE = re.compile(
    r"(?<![A-Z0-9])UDYAM[-\s]?[A-Z]{2}[-\s]?\d{2}[-\s]?\d{7}(?![A-Z0-9])",
    re.IGNORECASE,
)


def _normalize_udyam(raw: str) -> str:
    s = re.sub(r"[\s-]", "", raw).upper()          # UDYAMXX000000 0000
    return f"UDYAM-{s[5:7]}-{s[7:9]}-{s[9:]}"      # UDYAM-XX-00-0000000


def _regex_finder(
    pattern: re.Pattern, normalize: Callable[[str], str]
) -> Callable[[PageText], list[Candidate]]:
    def finder(page: PageText) -> list[Candidate]:
        return [
            Candidate(
                value=normalize(m.group()),
                raw_text=_snippet(page.text, m.start(), m.end()),
                page=page.page,
                confidence=CONF_ID_FORMAT,
            )
            for m in pattern.finditer(page.text)
        ]
    return finder


# -------------------------------
# Annual turnover
# -------------------------------

TURNOVER_RE = re.compile(r"turnover", re.IGNORECASE)

# Number (Indian or western commas), optional unit. The look-arounds reject digits
# glued to letters, e.g. the "1234" inside a PAN like ABCDE1234F.
AMOUNT_RE = re.compile(
    r"(?P<cur>₹|\brs\.?|\binr)?\s*"
    r"(?<![A-Za-z0-9])"
    r"(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s*(?P<unit>lakhs?|lacs?|crores?|cr)\b|(?![A-Za-z0-9]))",
    re.IGNORECASE,
)

# Financial years like 2023-24 or 2023/2024 must not be read as amounts.
FY_RE = re.compile(r"(?:19|20)\d{2}\s*[-–/]\s*(?:\d{4}|\d{2})\b")
YEAR_RE = re.compile(r"(?:19|20)\d{2}")

UNIT_MULTIPLIER = {
    "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000,
    "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000,
}


def _find_amounts(segment: str) -> list[tuple[Decimal, bool, int]]:
    """Returns (rupees, strong, end_offset) for each plausible amount in a text segment."""
    fy_spans = [m.span() for m in FY_RE.finditer(segment)]
    found = []

    for m in AMOUNT_RE.finditer(segment):
        if any(m.start() < fy_end and fy_start < m.end() for fy_start, fy_end in fy_spans):
            continue

        number = m.group("num").replace(",", "")
        unit = (m.group("unit") or "").lower()
        strong = bool(m.group("cur") or unit)

        if not strong:
            whole = number.split(".")[0]
            if len(whole) < 4 or YEAR_RE.fullmatch(whole):
                continue    # too small to be a turnover, or just a year

        try:
            rupees = Decimal(number) * UNIT_MULTIPLIER.get(unit, 1)
        except InvalidOperation:
            continue
        found.append((rupees, strong, m.end()))

    # If any amount has a currency symbol or unit, ignore the bare numbers.
    if any(strong for _, strong, _ in found):
        found = [f for f in found if f[1]]
    return found


def _format_rupees(value: Decimal) -> str:
    return format(value.normalize(), "f")      # 5000000, never 5E+6


def _find_turnover(page: PageText) -> list[Candidate]:
    text = page.text
    candidates = []

    for kw in TURNOVER_RE.finditer(text):
        line_end = _line_end(text, kw.end())
        next_start = line_end + 1
        segments = [
            (kw.end(), line_end),                              # rest of the same line
            (next_start, _line_end(text, next_start)),         # else the next line
        ]
        for seg_start, seg_end in segments:
            amounts = _find_amounts(text[seg_start:seg_end])
            if not amounts:
                continue
            for rupees, strong, end in amounts:
                candidates.append(Candidate(
                    value=_format_rupees(rupees),
                    raw_text=_snippet(text, kw.start(), seg_start + end),
                    page=page.page,
                    confidence=CONF_TURNOVER_STRONG if strong else CONF_TURNOVER_BARE,
                ))
            break
    return candidates


# -------------------------------
# Company name
# -------------------------------

COMPANY_LABEL_RE = re.compile(
    r"(?:legal\s+name(?:\s+of\s+business)?"
    r"|name\s+of\s+(?:the\s+)?(?:company|firm|vendor|supplier|seller|bidder|enterprise"
    r"|entity|applicant|business|organi[sz]ation)"
    r"|(?:company|firm|business|registered|enterprise)\s+name)"
    r"(?:[ \t]*[:\-–][ \t]*\n?[ \t]*|[ \t]*\n[ \t]*)"       # "Label: value" or "Label\nvalue"
    r"(?P<name>[^\n\r]{2,100})",
    re.IGNORECASE,
)


def _looks_like_company_name(name: str) -> bool:
    if ":" in name:                                  # probably the next label, e.g. "PAN: ..."
        return False
    if sum(ch.isalpha() for ch in name) < 3:
        return False
    if PAN_RE.fullmatch(name) or GSTIN_RE.fullmatch(name):
        return False
    return True


def _find_company_names(page: PageText) -> list[Candidate]:
    candidates = []
    for m in COMPANY_LABEL_RE.finditer(page.text):
        name = re.sub(r"\s+", " ", m.group("name")).strip(" \t:-–,;")
        if _looks_like_company_name(name):
            candidates.append(Candidate(
                value=name,
                raw_text=_snippet(page.text, m.start(), m.end()),
                page=page.page,
                confidence=CONF_COMPANY,
            ))
    return candidates


# -------------------------------
# Building the result
# -------------------------------

FIELD_FINDERS: dict[str, Callable[[PageText], list[Candidate]]] = {
    "company_name": _find_company_names,
    "pan": _regex_finder(PAN_RE, str.upper),
    "gstin": _regex_finder(GSTIN_RE, str.upper),
    "annual_turnover": _find_turnover,
    "udyam_number": _regex_finder(UDYAM_RE, _normalize_udyam),
}


def _build_field(
    name: str, candidates: list[Candidate], file_name: str, unreadable: bool
) -> ExtractedField:
    # Same value found twice (e.g. on two pages) is not a conflict: keep the first.
    unique: dict[str, Candidate] = {}
    for c in candidates:
        unique.setdefault(c.value.casefold(), c)
    distinct = list(unique.values())

    if not distinct:
        return ExtractedField(
            name=name,
            extraction_status="UNCERTAIN" if unreadable else "NOT_FOUND",
        )

    if len(distinct) == 1:
        c = distinct[0]
        return ExtractedField(
            name=name,
            document_value=c.value,
            raw_text=c.raw_text,
            document_source=DocumentSource(file=file_name, page=c.page),
            confidence=c.confidence,
            extraction_status="EXTRACTED",
        )

    # Conflicting values: do not pick one. Keep all snippets as evidence for the officer.
    return ExtractedField(
        name=name,
        document_value=None,
        raw_text=" || ".join(f"(p.{c.page}) {c.raw_text}" for c in distinct),
        document_source=DocumentSource(file=file_name, page=distinct[0].page),
        extraction_status="UNCERTAIN",
    )


def extract_fields(content: PDFContent) -> list[ExtractedField]:
    """Returns one ExtractedField per field name for a single PDF."""
    unreadable = bool(content.pages_without_text)
    fields = []

    for name, finder in FIELD_FINDERS.items():
        candidates: list[Candidate] = []
        for page in content.pages:
            if page.has_text:
                candidates.extend(finder(page))
        fields.append(_build_field(name, candidates, content.file, unreadable))

    return fields