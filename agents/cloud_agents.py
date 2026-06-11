"""
Cloud Agents — run on Claude Sonnet via LiteLLM.
These agents receive ONLY anonymized scores and structured flags.
Raw submission data (raw_document, parsed_fields) is NEVER passed here.

Agents:
  3d. risk_aggregator_node
  5.  coverage_gap_node
  6.  pricing_node
  7.  explainability_node
"""
from __future__ import annotations
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

from config.settings import get_model, RISK_WEIGHTS
from agents.llm_client import llm_call
from agents.error_wrapper import wrap_agent_with_tracking
from graph.state import UnderwritingState, CoverageGap, PricingRecommendation, make_audit_entry


# ── Output Schemas ────────────────────────────────────────────────────────────

class RiskAggregatorOutput(BaseModel):
    aggregate_score:      float
    aggregate_tier:       str           # LOW | MEDIUM | HIGH | DECLINE
    inconsistency_flag:   bool          = False
    inconsistency_detail: str           = ""
    confidence:           float         = 0.85
    explanation:          Dict          = Field(default_factory=dict)

class CoverageGapOutput(BaseModel):
    gaps:         List[Dict]            = Field(default_factory=list)
    gap_count:    int                   = 0
    max_severity: str                   = "NONE"    # HIGH | MEDIUM | LOW | NONE
    confidence:   float                 = 0.85
    explanation:  Dict                  = Field(default_factory=dict)

class PricingOutput(BaseModel):
    premium_low:        float           = 0.0
    premium_high:       float           = 0.0
    base_rate_tier:     str             = ""
    placement_type:     str             = "ADMITTED"
    adjustment_factors: List[Dict]      = Field(default_factory=list)
    confidence:         float           = 0.85
    explanation:        Dict            = Field(default_factory=dict)

class ExplainabilityOutput(BaseModel):
    submission_summary:   str
    risk_narrative:       str
    compliance_narrative: str
    coverage_narrative:   str
    decision_rationale:   str
    policy_references:    List[str]     = Field(default_factory=list)
    final_decision:       str           # APPROVE | DECLINE | REFER | REQUEST_INFO
    confidence:           float         = 0.9
    explanation:          Dict          = Field(default_factory=dict)


# ── Node 3d: Risk Aggregator ──────────────────────────────────────────────────

@wrap_agent_with_tracking("risk_aggregator")
def risk_aggregator_node(state: UnderwritingState) -> UnderwritingState:
    """
    Combine three sub-agent scores into unified risk profile.
    PRIVACY: receives only numeric scores — no raw submission data.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "risk_aggregator"))

    weights = RISK_WEIGHTS.get(state.submission_type, RISK_WEIGHTS["COMMERCIAL_PROPERTY"])

    score_summary = (
        f"Dimension A (Property/Fleet) score: {state.risk_profile.dimension_a_score:.2f}\n"
        f"Dimension B (Geographic/Driver) score: {state.risk_profile.dimension_b_score:.2f}\n"
        f"Dimension C (Business/Operations) score: {state.risk_profile.dimension_c_score:.2f}\n"
        f"Weights: A={weights['dimension_a']}, B={weights['dimension_b']}, C={weights['dimension_c']}\n"
        f"Submission type: {state.submission_type}\n"
        f"Sub-agent explanations: {state.agent_explanations.get('property_risk', {})}, "
        f"{state.agent_explanations.get('geographic_risk', {})}, "
        f"{state.agent_explanations.get('business_risk', {})}"
    )

    result = llm_call(
        model=get_model("cloud"),
        system_prompt=(
            "You are a risk aggregation specialist. "
            "Compute a weighted aggregate risk score from three independent sub-agent scores. "
            "Flag inconsistency if any two sub-agents disagree by more than one band "
            "(e.g., one scores HIGH while another scores LOW). "
            "Score bands: 0.0-0.3=LOW, 0.3-0.6=MEDIUM, 0.6-0.8=HIGH, 0.8-1.0=DECLINE."
        ),
        user_prompt=score_summary,
        response_schema=RiskAggregatorOutput,
    )

    state.risk_profile.aggregate_score    = result.aggregate_score
    state.risk_profile.aggregate_tier     = result.aggregate_tier
    state.risk_profile.inconsistency_flag = result.inconsistency_flag
    state.risk_profile.inconsistency_detail = result.inconsistency_detail

    state.agent_explanations["risk_aggregator"] = {
        "agent": "risk_aggregator",
        "aggregate_score": result.aggregate_score,
        "aggregate_tier": result.aggregate_tier,
        "inconsistency": result.inconsistency_flag,
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "risk_aggregator",
        output_summary=f"Tier={result.aggregate_tier}, Score={result.aggregate_score:.2f}, Inconsistency={result.inconsistency_flag}"
    ))
    return state


# ── Node 5: Coverage Gap Agent ────────────────────────────────────────────────

@wrap_agent_with_tracking("coverage_gap")
def coverage_gap_node(state: UnderwritingState) -> UnderwritingState:
    """
    Identify missing or insufficient coverage.
    PRIVACY: receives only risk_profile and compliance_result — no raw fields.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "coverage_gap"))

    gap_context = (
        f"Submission type: {state.submission_type}\n"
        f"Risk tier: {state.risk_profile.aggregate_tier}\n"
        f"Risk score: {state.risk_profile.aggregate_score:.2f}\n"
        f"Compliance status: {state.compliance_result.status}\n"
        f"Coverage requested: {state.parsed_fields.get('coverage_requested', {})}\n"
        f"Occupancy/operations: {state.parsed_fields.get('occupancy_type', state.parsed_fields.get('radius_of_operations', 'unknown'))}"
    )

    result = llm_call(
        model=get_model("cloud"),
        system_prompt=(
            "You are a commercial insurance coverage specialist. "
            "Identify coverage gaps based on the risk profile and requested coverage. "
            "Check four gap types: "
            "1. COVERAGE_TYPE: lines of coverage missing given the risk profile; "
            "2. LIMIT_ADEQUACY: requested limits below industry benchmarks for this risk tier; "
            "3. EXCLUSION: policy exclusions creating uninsured exposure; "
            "4. ENDORSEMENT: endorsements recommended but not requested. "
            "For commercial auto, also check: hired/non-owned auto, motor truck cargo for freight, excess liability adequacy. "
            "Each gap needs: gap_type, description, severity (HIGH/MEDIUM/LOW), recommendation."
        ),
        user_prompt=gap_context,
        response_schema=CoverageGapOutput,
    )

    state.coverage_gaps = [
        CoverageGap(
            gap_type=g.get("gap_type", "UNKNOWN"),
            description=g.get("description", ""),
            severity=g.get("severity", "LOW"),
            recommendation=g.get("recommendation", ""),
        )
        for g in result.gaps
    ]

    state.agent_explanations["coverage_gap"] = {
        "agent": "coverage_gap",
        "gap_count": result.gap_count,
        "max_severity": result.max_severity,
        "gaps": result.gaps,
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "coverage_gap",
        output_summary=f"Gaps={result.gap_count}, MaxSeverity={result.max_severity}"
    ))
    return state


# ── Node 6: Pricing Agent ─────────────────────────────────────────────────────

@wrap_agent_with_tracking("pricing", tool_names=["lookup_base_rate"])
def pricing_node(state: UnderwritingState) -> UnderwritingState:
    """
    Recommend premium range.
    PRIVACY: receives only anonymized risk scores and compliance result.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "pricing"))

    pricing_context = (
        f"Submission type: {state.submission_type}\n"
        f"Risk tier: {state.risk_profile.aggregate_tier}\n"
        f"Risk score: {state.risk_profile.aggregate_score:.2f}\n"
        f"Compliance status: {state.compliance_result.status}\n"
        f"Compliance severity: {state.compliance_result.severity}\n"
        f"SIC code: {state.parsed_fields.get('sic_code', 'unknown')}\n"
        f"Loss ratio: {state.parsed_fields.get('three_year_loss_ratio', 'unknown')}"
    )

    result = llm_call(
        model=get_model("cloud"),
        system_prompt=(
            "You are a commercial lines pricing specialist. "
            "Recommend a premium range based on the risk tier and compliance result. "
            "Use standard commercial lines rate relativities: "
            "LOW risk: base rate; MEDIUM: 1.25x base; HIGH: 1.75x base; DECLINE: not eligible. "
            "Base rate ranges: commercial property $2,500-$5,000; commercial auto $3,500-$7,000. "
            "Apply adjustment factors for: loss history, compliance issues (WARNING = +10%), "
            "surplus lines placement (+20% loading). "
            "Express as a premium range (low/high), not a point estimate."
        ),
        user_prompt=pricing_context,
        response_schema=PricingOutput,
    )

    state.pricing = PricingRecommendation(
        premium_low=result.premium_low,
        premium_high=result.premium_high,
        base_rate_tier=result.base_rate_tier,
        placement_type=result.placement_type,
        adjustment_factors=result.adjustment_factors,
    )

    state.agent_explanations["pricing"] = {
        "agent": "pricing",
        "premium_range": f"${result.premium_low:,.0f} - ${result.premium_high:,.0f}",
        "placement": result.placement_type,
        "adjustments": result.adjustment_factors,
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "pricing",
        output_summary=f"Range=${result.premium_low:,.0f}-${result.premium_high:,.0f}, Placement={result.placement_type}"
    ))
    return state


# ── Node 7: Explainability Agent ──────────────────────────────────────────────

@wrap_agent_with_tracking("explainability")
def explainability_node(state: UnderwritingState) -> UnderwritingState:
    """
    Assemble agent explanation snippets into audit-grade justification trace.
    This agent is an ASSEMBLER — it does not re-reason, it organizes and narrates.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "explainability"))

    assembly_input = (
        f"Submission type: {state.submission_type}\n"
        f"Agent explanations collected:\n{state.agent_explanations}\n\n"
        f"Risk profile: tier={state.risk_profile.aggregate_tier}, score={state.risk_profile.aggregate_score:.2f}\n"
        f"Compliance: {state.compliance_result.status}, violations={state.compliance_result.violations}\n"
        f"Coverage gaps: {len(state.coverage_gaps)}\n"
        f"Pricing: ${state.pricing.premium_low:,.0f} - ${state.pricing.premium_high:,.0f}\n"
        f"Confidence score: {state.confidence_score:.2f}"
    )

    result = llm_call(
        model=get_model("cloud"),
        system_prompt=(
            "You are an insurance decision documentation specialist. "
            "Assemble the agent explanation snippets into a coherent audit-grade justification. "
            "CRITICAL: Every claim you make must be traceable to a specific agent explanation snippet. "
            "Do NOT introduce new reasoning — only organize and narrate what the agents already documented. "
            "Structure your output in four sections: "
            "1. submission_summary: 2-3 sentence overview of what was submitted; "
            "2. risk_narrative: what the risk assessment found and the aggregate conclusion; "
            "3. compliance_narrative: which rules were checked and the outcome; "
            "4. coverage_narrative: gaps identified and recommendations; "
            "5. decision_rationale: how the findings together support the final decision. "
            "Final decision must be one of: APPROVE | DECLINE | REFER | REQUEST_INFO"
        ),
        user_prompt=assembly_input,
        response_schema=ExplainabilityOutput,
    )

    state.final_decision = result.final_decision

    state.agent_explanations["explainability"] = {
        "agent": "explainability",
        "final_decision": result.final_decision,
        "policy_references": result.policy_references,
        "confidence": result.confidence,
    }

    # Store full narrative in audit trail
    state.audit_trail.append(make_audit_entry(
        "WORKFLOW_COMPLETE", "explainability",
        output_summary=f"Final decision: {result.final_decision}",
        confidence_at_event=state.confidence_score,
        routing_outcome=f"explainability -> {result.final_decision}",
    ))

    # Attach full explanation to state for retrieval
    state.parsed_fields["_final_explanation"] = {
        "submission_summary":   result.submission_summary,
        "risk_narrative":       result.risk_narrative,
        "compliance_narrative": result.compliance_narrative,
        "coverage_narrative":   result.coverage_narrative,
        "decision_rationale":   result.decision_rationale,
        "policy_references":    result.policy_references,
    }

    return state
