"""
Demo runner for Member 3's verification engine.

    python demo.py          readable report for both sample vendors
    python demo.py --json   the same reports as JSON (like the API response)
"""

import json
import sys

from report import build_report
from schemas import VerificationReport
from tests.sample_inputs import CLEAN, INCONSISTENT


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