"""
Demo runner for Member 3's verification engine.

    python demo.py          readable report for both sample vendors
    python demo.py --json   the same reports as JSON (like the API response)

build_report() shows how the findings merge into Member 2's VerificationReport.
In the real system Member 2 does this merge; it is here to prove the formats fit.
"""

import json
import sys

from schemas import (
    ExtractedField, ReportField, VerificationInput, VerificationReport,
)
from tests.sample_inputs import CLEAN, INCONSISTENT
from verify import verify_with_status


def build_report(data: VerificationInput) -> VerificationReport:
    summary = verify_with_status(data)

    # first field per name wins, the same rule verify() uses
    extracted: dict[str, ExtractedField] = {}
    for f in data.fields:
        extracted.setdefault(f.name, f)

    fields = []
    for finding in summary.output.findings:
        ex = extracted.get(finding.name)
        fields.append(ReportField(
            name=finding.name,
            document_value=ex.document_value if ex else None,
            raw_text=ex.raw_text if ex else None,
            document_source=ex.document_source if ex else None,
            extraction_status=ex.extraction_status if ex else "NOT_FOUND",
            reference_value=finding.reference_value,
            reference_source=finding.reference_source,
            is_demo_reference=finding.is_demo_reference,
            match_status=finding.match_status,
            risk_level=finding.risk_level,
            explanation=finding.explanation,
        ))

    files = sorted({
        f.document_source.file
        for f in data.fields
        if f.document_source and f.document_source.file
    })

    return VerificationReport(
        vendor_id=data.vendor_id,
        files=files,
        verification_status=summary.verification_status,
        highest_risk=summary.highest_risk,
        fields=fields,
        pending_checks=summary.output.pending_checks,
    )


def print_report(report: VerificationReport) -> None:
    print("=" * 72)
    print(f"Vendor {report.vendor_id} | status: {report.verification_status} "
          f"| highest risk: {report.highest_risk}")
    print("Files:", ", ".join(report.files) or "none")
    print("-" * 72)
    for f in report.fields:
        print(f"{f.name:16} {f.match_status:9} risk={f.risk_level}")
        print(f"    document: {f.document_value}   reference: {f.reference_value}")
        print(f"    {f.explanation}")
    print("-" * 72)
    print("Pending checks:", report.pending_checks)
    print("Human decision required:", report.human_decision_required)
    print()


def main() -> None:
    as_json = "--json" in sys.argv
    for sample in (CLEAN, INCONSISTENT):
        report = build_report(sample)
        if as_json:
            print(json.dumps(report.model_dump(mode="json"), indent=2))
        else:
            print_report(report)


if __name__ == "__main__":
    main()