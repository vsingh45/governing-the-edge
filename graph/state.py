"""
Shared UnderwritingState — flows through every node in the LangGraph workflow.
This is the single source of truth for a submission's progress.
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any, Annotated
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from operator import add


def keep_first(a, b):
    """Return a if truthy, else b. Handles concurrent updates where all agents pass the same value."""
    return a if a else b


def keep_first_num(a, b):
    """Keep whichever is non-zero; used for numeric fields that only one node writes."""
    return a if a != 0.0 and a != 0 else b


def merge_dicts(a: Dict, b: Dict) -> Dict:
    """Merge two dicts; later writes win on key conflicts."""
    return {**a, **b}


def merge_compliance_result(a: "ComplianceResult", b: "ComplianceResult") -> "ComplianceResult":
    """Take b if it has been set by an agent (status != PENDING), else keep a."""
    return b if b.status != "PENDING" else a


def merge_pricing(a: "PricingRecommendation", b: "PricingRecommendation") -> "PricingRecommendation":
    """Take b if an agent has filled it in, else keep a."""
    return b if (b.premium_low or b.premium_high or b.base_rate_tier) else a


def merge_risk_profiles(a: "RiskProfile", b: "RiskProfile") -> "RiskProfile":
    """Merge two RiskProfile updates — each parallel sub-agent writes exactly one dimension."""
    return RiskProfile(
        dimension_a_score=b.dimension_a_score if b.dimension_a_score != 0.0 else a.dimension_a_score,
        dimension_b_score=b.dimension_b_score if b.dimension_b_score != 0.0 else a.dimension_b_score,
        dimension_c_score=b.dimension_c_score if b.dimension_c_score != 0.0 else a.dimension_c_score,
        aggregate_score=b.aggregate_score if b.aggregate_score != 0.0 else a.aggregate_score,
        aggregate_tier=b.aggregate_tier if b.aggregate_tier not in ("UNKNOWN", "") else a.aggregate_tier,
        inconsistency_flag=a.inconsistency_flag or b.inconsistency_flag,
        inconsistency_detail=b.inconsistency_detail or a.inconsistency_detail,
    )


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
    # Identity — keep_first so parallel agents don't conflict on the ID set at init
    submission_id:      Annotated[str, keep_first] = Field(default_factory=lambda: str(uuid.uuid4()))
    submission_type:    Annotated[str, keep_first] = ""   # COMMERCIAL_PROPERTY | COMMERCIAL_AUTO

    # Input — raw_document is NEVER sent to cloud agents
    raw_document:       Annotated[str, keep_first] = ""
    parsed_fields:      Annotated[Dict, merge_dicts] = Field(default_factory=dict)

    # Agent outputs — risk_profile needs custom merge (parallel agents each write one dimension)
    risk_profile:       Annotated[RiskProfile, merge_risk_profiles]           = Field(default_factory=RiskProfile)
    compliance_result:  Annotated[ComplianceResult, merge_compliance_result]    = Field(default_factory=ComplianceResult)
    coverage_gaps:      Annotated[List[CoverageGap], keep_first]              = Field(default_factory=list)
    pricing:            Annotated[PricingRecommendation, merge_pricing]        = Field(default_factory=PricingRecommendation)

    # Routing — only written by sequential nodes; keep_first handles pass-through from parallel nodes
    confidence_score:   Annotated[float, keep_first_num] = 0.0
    escalation_reason:  Annotated[str, keep_first] = ""
    final_decision:     Annotated[str, keep_first] = ""   # APPROVE | DECLINE | REFER | REQUEST_INFO

    # Agent explanation snippets — keyed by agent name
    agent_explanations: Annotated[Dict[str, Dict], merge_dicts] = Field(default_factory=dict)

    # Audit trail — append-only (concurrent updates via add operator)
    audit_trail:        Annotated[List[AuditEntry], add] = Field(default_factory=list)

    # Internal routing flags
    compliance_retry_count: Annotated[int, keep_first_num] = 0
    human_decision:         Annotated[str, keep_first] = ""   # set by human escalation resume

    # Evaluation metadata (used by eval harness)
    ground_truth_decision:    Annotated[str, keep_first] = ""
    ground_truth_compliance:  Annotated[str, keep_first] = ""
    scenario_id:              Annotated[str, keep_first] = ""
    scenario_complexity:      Annotated[str, keep_first] = ""


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
