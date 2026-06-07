"""
P&C Compliance Rules Engine
10 validated underwriting rules across commercial property and commercial auto.
Rules validated by Gautam Bhowmick (Deloitte Consulting) from active engagement experience.
"""
from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel
import json


# ── Rule Schema ───────────────────────────────────────────────────────────────

class ComplianceRule(BaseModel):
    rule_id:           str
    line:              str         # COMMERCIAL_PROPERTY | COMMERCIAL_AUTO
    rule_type:         str         # CONSTRUCTION | TIV | OCCUPANCY | LOSS_RATIO | AGE | FLEET | DRIVER | RADIUS | FLEET_AGE | DOT
    description:       str
    check_field:       str
    condition:         str         # human-readable condition for LLM prompt
    violation_message: str
    severity:          str         # HARD_STOP | WARNING
    remediation_hint:  Optional[str] = None
    effective_date:    Optional[str] = None


# ── The 10 Validated P&C Rules ────────────────────────────────────────────────

RULES: List[ComplianceRule] = [

    # ── Commercial Property ───────────────────────────────────────────────────

    ComplianceRule(
        rule_id="CP-01",
        line="COMMERCIAL_PROPERTY",
        rule_type="CONSTRUCTION",
        description="Frame construction buildings over 3 stories are not eligible for standard market placement.",
        check_field="construction_class,stories",
        condition="If construction_class = 'FRAME' AND stories > 3, then DECLINE.",
        violation_message="Frame construction over 3 stories — not eligible for standard market.",
        severity="HARD_STOP",
        remediation_hint="Refer to surplus lines market or require masonry/fire-resistive construction upgrade."
    ),

    ComplianceRule(
        rule_id="CP-02",
        line="COMMERCIAL_PROPERTY",
        rule_type="TIV",
        description="Single location Total Insured Value over $10M requires specialty market referral.",
        check_field="total_insured_value",
        condition="If total_insured_value > 10000000, then REFER to specialty market.",
        violation_message="Single location TIV exceeds $10M — refer to specialty market.",
        severity="HARD_STOP",
        remediation_hint="Route to E&S market or wholesale broker with capacity for high-value property."
    ),

    ComplianceRule(
        rule_id="CP-03",
        line="COMMERCIAL_PROPERTY",
        rule_type="OCCUPANCY",
        description="Habitational risks with more than 4 units are not eligible.",
        check_field="occupancy_type,unit_count",
        condition="If occupancy_type = 'HABITATIONAL' AND unit_count > 4, then NOT ELIGIBLE.",
        violation_message="Habitational risk exceeds 4 units — not eligible.",
        severity="HARD_STOP",
        remediation_hint="Refer to specialty habitational markets or residential package program."
    ),

    ComplianceRule(
        rule_id="CP-04",
        line="COMMERCIAL_PROPERTY",
        rule_type="LOSS_RATIO",
        description="Three-year loss ratio over 70% requires declination or significant surcharge.",
        check_field="three_year_loss_ratio",
        condition="If three_year_loss_ratio > 0.70, then DECLINE or apply surcharge.",
        violation_message="3-year loss ratio exceeds 70% — decline or surcharge required.",
        severity="WARNING",
        remediation_hint="Apply minimum 25% surcharge or require loss control inspection before binding."
    ),

    ComplianceRule(
        rule_id="CP-05",
        line="COMMERCIAL_PROPERTY",
        rule_type="AGE",
        description="Buildings over 40 years old without documented renovation require inspection.",
        check_field="year_built,last_renovation_year",
        condition="If building_age > 40 AND last_renovation_year is null, then REQUIRE INSPECTION.",
        violation_message="Building over 40 years without documented renovation — inspection required.",
        severity="WARNING",
        remediation_hint="Obtain building inspection report before binding. Renovation documentation acceptable in lieu."
    ),

    # ── Commercial Auto ───────────────────────────────────────────────────────

    ComplianceRule(
        rule_id="CA-01",
        line="COMMERCIAL_AUTO",
        rule_type="FLEET",
        description="Fleets with more than 20 vehicles require specialist fleet underwriter review.",
        check_field="fleet_size",
        condition="If fleet_size > 20, then REFER to fleet specialist.",
        violation_message="Fleet exceeds 20 vehicles — refer to fleet specialist.",
        severity="HARD_STOP",
        remediation_hint="Route to commercial fleet unit with experience modification rating capability."
    ),

    ComplianceRule(
        rule_id="CA-02",
        line="COMMERCIAL_AUTO",
        rule_type="DRIVER",
        description="Any driver with 2 or more major violations in the past 3 years must be excluded.",
        check_field="driver_mvr_violations",
        condition="If any driver has >= 2 major violations in past 3 years, then DECLINE that driver.",
        violation_message="One or more drivers exceed violation threshold — driver exclusion required.",
        severity="HARD_STOP",
        remediation_hint="Exclude violating driver(s) from policy or decline if principal operator."
    ),

    ComplianceRule(
        rule_id="CA-03",
        line="COMMERCIAL_AUTO",
        rule_type="RADIUS",
        description="Operations exceeding 500 mile radius require interstate filing.",
        check_field="radius_of_operations",
        condition="If radius_of_operations > 500, then REQUIRE interstate filing.",
        violation_message="Radius over 500 miles — interstate filing required.",
        severity="WARNING",
        remediation_hint="File MCS-90 endorsement and verify FMCSA operating authority."
    ),

    ComplianceRule(
        rule_id="CA-04",
        line="COMMERCIAL_AUTO",
        rule_type="FLEET_AGE",
        description="Average fleet age over 10 years requires mandatory surcharge.",
        check_field="average_fleet_age",
        condition="If average_fleet_age > 10, then APPLY surcharge.",
        violation_message="Average fleet age exceeds 10 years — surcharge required.",
        severity="WARNING",
        remediation_hint="Apply minimum 15% surcharge. Require maintenance records for vehicles over 15 years."
    ),

    ComplianceRule(
        rule_id="CA-05",
        line="COMMERCIAL_AUTO",
        rule_type="DOT",
        description="DOT safety rating of Conditional or Unsatisfactory results in declination.",
        check_field="dot_safety_rating",
        condition="If dot_safety_rating IN ['CONDITIONAL', 'UNSATISFACTORY'], then DECLINE.",
        violation_message="DOT safety rating is Conditional or Unsatisfactory — decline.",
        severity="HARD_STOP",
        remediation_hint="Not eligible until carrier achieves Satisfactory DOT rating."
    ),
]


# ── Rules Engine ──────────────────────────────────────────────────────────────

class RulesEngine:
    """
    Provides rule lookup by line of business.
    Used by the Compliance Agent to get the applicable rule set for a submission.
    """

    def __init__(self):
        self._rules = {r.rule_id: r for r in RULES}

    def get_rules_for_line(self, line: str) -> List[ComplianceRule]:
        """Return all rules applicable to a given line of business."""
        return [r for r in RULES if r.line == line]

    def get_rule(self, rule_id: str) -> Optional[ComplianceRule]:
        """Look up a specific rule by ID."""
        return self._rules.get(rule_id)

    def format_rules_for_prompt(self, line: str) -> str:
        """
        Format rules as a structured string for the compliance agent prompt.
        Returns a numbered list of rules with condition and severity.
        """
        rules = self.get_rules_for_line(line)
        lines = [f"COMPLIANCE RULES FOR {line}:\n"]
        for r in rules:
            lines.append(
                f"Rule {r.rule_id} [{r.severity}]\n"
                f"  Description: {r.description}\n"
                f"  Condition: {r.condition}\n"
                f"  Violation Message: {r.violation_message}\n"
            )
        return "\n".join(lines)

    def to_json(self) -> str:
        """Export all rules as JSON (for documentation/audit purposes)."""
        return json.dumps([r.model_dump() for r in RULES], indent=2)


# Singleton instance
rules_engine = RulesEngine()
