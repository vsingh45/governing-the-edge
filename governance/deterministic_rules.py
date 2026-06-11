"""
Deterministic rule evaluator for HARD_STOP P&C compliance rules.
No LLM involved — pure Python predicates against extracted ACORD fields.
This is the structural governance enforcement layer.
"""
from typing import Dict, List, Optional


def check_cp01_frame_height(fields: Dict) -> Optional[Dict]:
    """CP-01: Frame construction >3 stories → DECLINE"""
    construction = fields.get("construction_class", "").upper()
    stories = fields.get("stories")
    if construction == "FRAME" and stories is not None and stories > 3:
        return {
            "rule_id": "CP-01",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"Frame construction with {stories} stories exceeds 3-story limit",
            "action": "DECLINE",
        }
    return None


def check_cp02_tiv(fields: Dict) -> Optional[Dict]:
    """CP-02: Single location TIV > $10M → REFER"""
    tiv = fields.get("total_insured_value")
    if tiv is not None and tiv > 10_000_000:
        return {
            "rule_id": "CP-02",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"TIV ${tiv:,.0f} exceeds $10M specialty market threshold",
            "action": "REFER",
        }
    return None


def check_cp03_habitational(fields: Dict) -> Optional[Dict]:
    """CP-03: Habitational > 4 units → NOT ELIGIBLE"""
    occupancy = fields.get("occupancy_type", "").upper()
    units = fields.get("unit_count")
    if occupancy == "HABITATIONAL" and units is not None and units > 4:
        return {
            "rule_id": "CP-03",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"Habitational risk with {units} units exceeds 4-unit limit",
            "action": "DECLINE",
        }
    return None


def check_ca01_fleet_size(fields: Dict) -> Optional[Dict]:
    """CA-01: Fleet > 20 vehicles → FLEET SPECIALIST"""
    fleet_size = fields.get("fleet_size")
    if fleet_size is not None and fleet_size > 20:
        return {
            "rule_id": "CA-01",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"Fleet size {fleet_size} requires fleet specialist underwriter",
            "action": "REFER",
        }
    return None


def check_ca02_driver_violations(fields: Dict) -> Optional[Dict]:
    """CA-02: Driver with 2+ major violations (3 yrs) → DECLINE DRIVER"""
    violations = fields.get("driver_mvr_violations")
    if violations is not None and violations >= 2:
        return {
            "rule_id": "CA-02",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"Driver with {violations} major violations in 3 yrs exceeds limit",
            "action": "DECLINE",
        }
    return None


def check_ca05_dot_rating(fields: Dict) -> Optional[Dict]:
    """CA-05: DOT Conditional/Unsatisfactory → DECLINE"""
    rating = fields.get("dot_safety_rating", "").upper()
    if rating in ("CONDITIONAL", "UNSATISFACTORY"):
        return {
            "rule_id": "CA-05",
            "status": "VIOLATION",
            "severity": "HARD_STOP",
            "detail": f"DOT safety rating '{rating}' fails minimum threshold",
            "action": "DECLINE",
        }
    return None


HARD_STOP_CHECKS = {
    "COMMERCIAL_PROPERTY": [
        check_cp01_frame_height,
        check_cp02_tiv,
        check_cp03_habitational,
    ],
    "COMMERCIAL_AUTO": [
        check_ca01_fleet_size,
        check_ca02_driver_violations,
        check_ca05_dot_rating,
    ],
}


def evaluate_hard_stops(line: str, fields: Dict) -> List[Dict]:
    """Run all HARD_STOP checks for a given line. Return list of violations."""
    checks = HARD_STOP_CHECKS.get(line, [])
    violations = []
    for check_fn in checks:
        result = check_fn(fields)
        if result is not None:
            violations.append(result)
    return violations
