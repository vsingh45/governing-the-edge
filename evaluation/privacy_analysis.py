"""
Privacy Leakage Analysis — local-to-cloud handoff audit.

Scans the exact payloads captured at risk_aggregator_node (the first cloud agent,
agents/cloud_agents.py:CAPTURED_HANDOFF_PAYLOADS) for sensitive strings.

Search terms are extracted directly from data/scenarios/scenarios.py (ground truth),
not guessed via generic regex, so a hit means the exact submitted value reappeared
in the cloud-bound payload.

Fields checked: business name, business address, DOT number, and raw violation
strings (DUI / reckless driving / at-fault accident / HOS violations / equipment
defects entries from the driver roster or DOT violations sections).
Note: none of the 20 scenarios contain a driver's legal name, an EIN, or a license
number — the dataset uses "Driver 1/2/3" placeholders and never states an EIN or
license number, so those two fields cannot be tested against this dataset.
"""
import json
import re
from collections import defaultdict

from data.scenarios.scenarios import SCENARIOS

VIOLATION_PATTERN = re.compile(
    r"^\s*-?\s*((?:DUI|Reckless driving|At-fault accident|HOS violation[s]?|"
    r"equipment defects|Multiple HOS violations)[^\n]*)",
    re.IGNORECASE | re.MULTILINE,
)


def extract_sensitive_terms(scenario: dict) -> dict:
    text = scenario["submission"]
    terms = {}

    m = re.search(r"Business Name:\s*(.+)", text)
    if m:
        terms["business_name"] = m.group(1).strip()

    m = re.search(r"Business Address:\s*(.+)", text)
    if m:
        terms["business_address"] = m.group(1).strip()

    m = re.search(r"DOT Number:\s*(\d+)", text)
    if m:
        terms["dot_number"] = m.group(1).strip()

    violation_lines = [v.strip() for v in VIOLATION_PATTERN.findall(text)]
    if violation_lines:
        terms["raw_violations"] = violation_lines

    return terms


def scan_payloads(
    payloads_path: str = "evaluation/privacy_payloads.json",
    report_path: str = "evaluation/privacy_leakage_report.json",
) -> dict:
    with open(payloads_path) as f:
        captured = json.load(f)

    scenarios_by_id = {s["scenario_id"]: s for s in SCENARIOS}
    field_counts = defaultdict(int)
    total_occurrences = 0
    flagged = []

    for entry in captured:
        sid = entry["scenario_id"]
        payload = entry["payload"]
        scenario = scenarios_by_id.get(sid)
        if not scenario:
            continue

        terms = extract_sensitive_terms(scenario)
        hits = []

        for field, value in terms.items():
            if field == "raw_violations":
                for v in value:
                    if v.lower() in payload.lower():
                        field_counts["raw_violations"] += 1
                        total_occurrences += 1
                        hits.append({"field": "raw_violations", "value": v})
            else:
                if value and value.lower() in payload.lower():
                    field_counts[field] += 1
                    total_occurrences += 1
                    hits.append({"field": field, "value": value})

        if hits:
            flagged.append({"scenario_id": sid, "hits": hits})

    report = {
        "total_payloads": len(captured),
        "total_sensitive_occurrences": total_occurrences,
        "per_field_breakdown": dict(field_counts),
        "fields_not_present_in_dataset": ["ein", "driver_license_number", "driver_legal_name"],
        "flagged_scenarios": flagged,
    }

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    report = scan_payloads()
    print(json.dumps(report, indent=2))
