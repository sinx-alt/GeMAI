# Reference source label (mock data must always be labelled as simulated)
DEMO_SOURCE = "DEMO_REFERENCE_RECORD"

# Fields we verify
ALL_FIELDS = ["company_name", "pan", "gstin", "annual_turnover", "udyam_number"]

# Regex formats
PAN_REGEX = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
GSTIN_REGEX = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$"
UDYAM_REGEX = r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$"

# Thresholds (tune later)
NAME_SIMILARITY_LOW = 85      # >=85 and not exact -> minor spelling difference (LOW)
TURNOVER_TOLERANCE = 0.05     # within 5% treated as matching
TURNOVER_MAJOR_RATIO = 2.0    # >=2x difference -> major (HIGH)

# Risk rule table (project doc, Section 3C)
RISK_RULES = {
    "minor_spelling": "LOW",
    "missing_document": "MEDIUM",
    "gstin_mismatch": "HIGH",
    "major_turnover_mismatch": "HIGH",
}