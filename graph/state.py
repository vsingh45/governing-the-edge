"""
Shared UnderwritingState — flows through every node in the LangGraph workflow.
This is the single source of truth for a submission's progress.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
import uuid


# ── Sub-schemas ───────────────────────────────────────────────────────────────

class RiskProfile(BaseModel):
    dimension_a_score:  float = 0.0    # property/fleet risk score
    dimension_b_score:  float = 0.0    # geographic/driver risk score
    dimension_c_score:  float = 0.0    # business/operations risk score
    aggregate_score:    float = 0.0
    aggregate_tier:     str   = "UNKNOWN"   # LOW | MEDIUM | HIGH | DECLINE
    inconsistency_flag: bool  = False
    inconsistency_detail: str = ""

class ComplianceResult(BaseModel):
    status:       str         = "PENDING"   # PASS | FAIL | CONFLICT
    rules_checked: List[str]  = Field(default_factory=list)
    violations:   List[Dict]  = Field(default_factory=list)
    conflicts:    List[Dict]  = Field(default_factory=list)
    severity:     str         = "NONE"      # HARD_STOP | WARNING | NONE
    retry_count:  int         = 0

class CoverageGap(BaseModel):
    gap_type:       str    # COVERAGE_TYPE | LIMIT_ADEQUACY | EXCLUSION | ENDORSEMENT
    description:    str
    severity:       str    # HIGH | MEDIUM | LOW
    recommendation: str

class PricingRecommendation(BaseModel):
    premium_low:        float = 0.0
    premium_high:       float = 0.0
    base_rate_tier:     str   = ""
    placement_type:     str   = "ADMITTED"   # ADMITTED | SURPLUS_LINES
    adjustment_factors: List[Dict] = Field(default_factory=list)

class AuditEntry(BaseModel):
    timestamp:          str
    event_type:         str    # AGENT_START | AGENT_COMPLETE | GOVERNANCE_CHECK | ROUTING_DECISION | HUMAN_ESCALATION | HUMAN_DECISION | WORKFLOW_COMPLETE
    agent:              str
    input_summary:      str    = ""
    output_summary:     str    = ""
    governance_result:  str    = "N/A"
    rule_ids_checked:   List[str] = Field(default_factory=list)
    routing_outcome:    str    = ""
    confidence_at_event: Optional[float] = None


# ── Main State ────────────────────────────────────────────────────────────────

class UnderwritingState(BaseModel):
    # Identity
    submission_id:      str   = Field(default_factory=lambda: str(uuid.uuid4()))
    submission_type:    str   = ""   # COMMERCIAL_PROPERTY | COMMERCIAL_AUTO

    # Input — raw_document is NEVER sent to cloud agents
    raw_document:       str   = ""
    parsed_fields:      Dict  = Field(default_factory=dict)

    # Agent outputs
    risk_profile:       RiskProfile            = Field(default_factory=RiskProfile)
    compliance_result:  ComplianceResult       = Field(default_factory=ComplianceResult)
    coverage_gaps:      List[CoverageGap]      = Field(default_factory=list)
    pricing:            PricingRecommendation  = Field(default_factory=PricingRecommendation)

    # Routing
    confidence_score:   float  = 0.0
    escalation_reason:  str    = ""
    final_decision:     str    = ""   # APPROVE | DECLINE | REFER | REQUEST_INFO

    # Agent explanation snippets — keyed by agent name
    # Each agent writes its own snippet here immediately after executing
    agent_explanations: Dict[str, Dict] = Field(default_factory=dict)

    # Audit trail — append-only
    audit_trail:        List[AuditEntry] = Field(default_factory=list)

    # Internal routing flags
    compliance_retry_count: int = 0
    human_decision:         str = ""   # set by human escalation resume

    # Evaluation metadata (used by eval harness)
    ground_truth_decision:    str = ""
    ground_truth_compliance:  str = ""
    scenario_id:              str = ""
    scenario_complexity:      str = ""


def make_audit_entry(
    event_type: str,
    agent: str,
    input_summary: str = "",
    output_summary: str = "",
    governance_result: str = "N/A",
    rule_ids_checked: List[str] = None,
    routing_outcome: str = "",
    confidence_at_event: float = None,
) -> AuditEntry:
    """Helper to create a timestamped audit entry."""
    return AuditEntry(
        timestamp=datetime.utcnow().isoformat() + "Z",
        event_type=event_type,
        agent=agent,
        input_summary=input_summary,
        output_summary=output_summary,
        governance_result=governance_result,
        rule_ids_checked=rule_ids_checked or [],
        routing_outcome=routing_outcome,
        confidence_at_event=confidence_at_event,
    )
