"""
Routing functions and confidence scoring.
These are the governance enforcement points — they determine which edge to take.
"""
from __future__ import annotations
from graph.state import UnderwritingState, make_audit_entry
from config.settings import (
    CONFIDENCE_THRESHOLD,
    WEIGHT_INTRA_AGENT,
    WEIGHT_INTER_AGENT,
    WEIGHT_GOVERNANCE,
)


# ── Compliance Routing ────────────────────────────────────────────────────────

def route_compliance(state: UnderwritingState) -> str:
    """
    Branch Point 1 — after Compliance Agent.
    PASS    → proceed to parallel Coverage Gap + Pricing
    FAIL    → route to Human Escalation (blocked)
    CONFLICT → trigger self-correcting retry
    """
    status = state.compliance_result.status

    state.audit_trail.append(make_audit_entry(
        "ROUTING_DECISION", "router",
        input_summary=f"Compliance status: {status}",
        routing_outcome=f"compliance -> {'coverage_gap' if status == 'PASS' else 'human_escalation' if status == 'FAIL' else 'compliance_retry'}",
        governance_result=status,
        rule_ids_checked=state.compliance_result.rules_checked,
    ))

    if status == "PASS":
        return "coverage_gap"
    elif status == "FAIL":
        return "human_escalation"
    else:  # CONFLICT
        return "compliance_retry"


def route_compliance_retry(state: UnderwritingState) -> str:
    """
    Branch Point 1b — after Compliance Retry.
    PASS → proceed
    FAIL or CONFLICT → escalate (max retries reached)
    """
    status = state.compliance_result.status

    state.audit_trail.append(make_audit_entry(
        "ROUTING_DECISION", "router",
        input_summary=f"Compliance retry status: {status}",
        routing_outcome=f"compliance_retry -> {'coverage_gap' if status == 'PASS' else 'human_escalation'}",
        governance_result=status,
    ))

    return "coverage_gap" if status == "PASS" else "human_escalation"


# ── Confidence Scoring ────────────────────────────────────────────────────────

def compute_confidence_score(state: UnderwritingState) -> float:
    """
    Compute composite confidence score from three components.

    Component 1 — Intra-agent certainty (weight 0.40):
        Average self-reported confidence across all agents that ran.

    Component 2 — Inter-agent consistency (weight 0.35):
        - Risk tier agreement across sub-agents (0.0 if inconsistency flagged, 1.0 otherwise)
        - Gap-price alignment (0.5 penalty if HIGH severity gaps but no pricing adjustment)

    Component 3 — Governance resolution (weight 0.25):
        1.0 = clean PASS
        0.5 = PASS on retry
        0.0 = FAIL (should not reach here, but handled defensively)
    """

    # ── Component 1: Intra-agent certainty ───────────────────────────────────
    agent_confidences = []
    for agent_name, explanation in state.agent_explanations.items():
        conf = explanation.get("confidence", None)
        if conf is not None:
            agent_confidences.append(float(conf))
    intra_certainty = sum(agent_confidences) / len(agent_confidences) if agent_confidences else 0.7

    # ── Component 2: Inter-agent consistency ─────────────────────────────────
    # Risk tier agreement
    risk_consistency = 0.0 if state.risk_profile.inconsistency_flag else 1.0

    # Gap-price alignment: HIGH gaps should drive pricing adjustment
    gap_severity = state.agent_explanations.get("coverage_gap", {}).get("max_severity", "NONE")
    pricing_adjustments = state.pricing.adjustment_factors

    has_upward_adjustment = any(
        adj.get("direction", "").upper() in ("UP", "INCREASE", "SURCHARGE")
        for adj in pricing_adjustments
    )

    if gap_severity == "HIGH" and not has_upward_adjustment:
        gap_price_alignment = 0.5   # penalty: high gaps not reflected in pricing
    else:
        gap_price_alignment = 1.0

    inter_consistency = (risk_consistency + gap_price_alignment) / 2.0

    # ── Component 3: Governance resolution ───────────────────────────────────
    compliance_status = state.compliance_result.status
    retry_count       = state.compliance_result.retry_count

    if compliance_status == "PASS" and retry_count == 0:
        governance_resolution = 1.0
    elif compliance_status == "PASS" and retry_count > 0:
        governance_resolution = 0.5
    else:
        governance_resolution = 0.0

    # ── Weighted combination ──────────────────────────────────────────────────
    score = (
        WEIGHT_INTRA_AGENT  * intra_certainty    +
        WEIGHT_INTER_AGENT  * inter_consistency  +
        WEIGHT_GOVERNANCE   * governance_resolution
    )

    return round(min(max(score, 0.0), 1.0), 3)


# ── Merge Parallel Node ───────────────────────────────────────────────────────

def merge_parallel_node(state: UnderwritingState) -> UnderwritingState:
    """
    Merge point after parallel Coverage Gap and Pricing agents.
    Computes the composite confidence score for routing.
    Called by both coverage_gap and pricing before routing to explainability or escalation.
    """
    # Only compute once (when both agents have completed)
    if state.agent_explanations.get("coverage_gap") and state.agent_explanations.get("pricing"):
        state.confidence_score = compute_confidence_score(state)

        state.audit_trail.append(make_audit_entry(
            "ROUTING_DECISION", "router",
            input_summary="Parallel agents complete — computing confidence",
            output_summary=f"Confidence score: {state.confidence_score:.3f} (threshold: {CONFIDENCE_THRESHOLD})",
            confidence_at_event=state.confidence_score,
        ))

    return state


# ── Confidence Routing ────────────────────────────────────────────────────────

def route_confidence(state: UnderwritingState) -> str:
    """
    Branch Point 2 — after parallel merge.
    confidence >= threshold → explainability → final decision
    confidence <  threshold → human escalation
    """
    score     = state.confidence_score
    threshold = CONFIDENCE_THRESHOLD

    if score >= threshold:
        route = "explainability"
    else:
        state.escalation_reason = (
            f"Confidence score {score:.3f} below threshold {threshold}. "
            f"Intra-agent certainty, inter-agent consistency, or governance resolution "
            f"insufficient for automated decision."
        )
        route = "human_escalation"

    state.audit_trail.append(make_audit_entry(
        "ROUTING_DECISION", "router",
        input_summary=f"Confidence={score:.3f}, Threshold={threshold}",
        routing_outcome=f"merge -> {route}",
        confidence_at_event=score,
    ))

    return route


# ── Human Escalation Node ─────────────────────────────────────────────────────

def human_escalation_node(state: UnderwritingState) -> UnderwritingState:
    """
    Node 8 — Deterministic interrupt.
    No LLM call. Serializes escalation package with fixed schema.
    In production: triggers LangGraph interrupt() and surfaces to FastAPI endpoint.
    In evaluation: records escalation and sets final_decision = REFER.
    """
    escalation_package = {
        "submission_id":      state.submission_id,
        "escalation_reason":  state.escalation_reason or "Compliance violation — human review required",
        "risk_profile": {
            "tier":  state.risk_profile.aggregate_tier,
            "score": state.risk_profile.aggregate_score,
        },
        "compliance_result": {
            "status":     state.compliance_result.status,
            "violations": state.compliance_result.violations,
            "severity":   state.compliance_result.severity,
        },
        "coverage_gaps":      [g.model_dump() for g in state.coverage_gaps],
        "confidence_score":   state.confidence_score,
        "recommended_action": _recommend_action(state),
        "agent_explanations": state.agent_explanations,
        "audit_trail_length": len(state.audit_trail),
    }

    state.final_decision = "REFER"
    state.parsed_fields["_escalation_package"] = escalation_package

    state.audit_trail.append(make_audit_entry(
        "HUMAN_ESCALATION", "human_escalation_node",
        output_summary=f"Escalated. Reason: {escalation_package['escalation_reason'][:100]}",
        governance_result=state.compliance_result.status,
        routing_outcome="human_escalation -> END (awaiting human decision)",
        confidence_at_event=state.confidence_score,
    ))

    return state


def _recommend_action(state: UnderwritingState) -> str:
    """
    Derive a system recommendation for the human underwriter
    based on compliance severity and risk tier.
    """
    if state.compliance_result.severity == "HARD_STOP":
        return "DECLINE"
    if state.risk_profile.aggregate_tier == "DECLINE":
        return "DECLINE"
    if state.risk_profile.aggregate_tier == "HIGH":
        return "REFER"
    return "REQUEST_INFO"
