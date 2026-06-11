"""
LangGraph Workflow — the governance-aware orchestration graph.
Defines all nodes, edges, and conditional routing functions.
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import UnderwritingState, make_audit_entry
from agents.local_agents import (
    document_parser_node,
    intake_node,
    property_risk_node,
    geographic_risk_node,
    business_risk_node,
    compliance_node,
    compliance_retry_node,
)
from agents.cloud_agents import (
    risk_aggregator_node,
    coverage_gap_node,
    pricing_node,
    explainability_node,
)
from graph.routing import (
    route_compliance,
    route_compliance_retry,
    route_confidence,
    compute_confidence_score,
    human_escalation_node,
    merge_parallel_node,
)
from config.settings import MAX_COMPLIANCE_RETRIES


def build_workflow() -> StateGraph:
    """
    Build and return the compiled LangGraph workflow.

    Graph topology:
        document_parser → intake → [property_risk || geographic_risk || business_risk]
        → risk_aggregator → compliance → (PASS) → [coverage_gap || pricing]
                                        (FAIL) → human_escalation
                                        (CONFLICT) → compliance_retry → (PASS/FAIL) → ...
        → merge_parallel → (confidence >= threshold) → explainability → END
                           (confidence < threshold)  → human_escalation → END
    """
    graph = StateGraph(UnderwritingState)

    # ── Register all nodes ────────────────────────────────────────────────────
    graph.add_node("document_parser",   document_parser_node)
    graph.add_node("intake",            intake_node)

    # Risk sub-graph (parallel execution via fan-out)
    graph.add_node("property_risk",     property_risk_node)
    graph.add_node("geographic_risk",   geographic_risk_node)
    graph.add_node("business_risk",     business_risk_node)
    graph.add_node("risk_aggregator",   risk_aggregator_node)

    # Compliance with retry
    graph.add_node("compliance",        compliance_node)
    graph.add_node("compliance_retry",  compliance_retry_node)

    # Parallel cloud agents
    graph.add_node("coverage_gap",      coverage_gap_node)
    graph.add_node("pricing",           pricing_node)
    graph.add_node("merge_parallel",    merge_parallel_node)

    # Final nodes
    graph.add_node("explainability",    explainability_node)
    graph.add_node("human_escalation",  human_escalation_node)

    # ── Sequential edges ──────────────────────────────────────────────────────
    graph.set_entry_point("document_parser")
    graph.add_edge("document_parser", "intake")

    # Fan-out: intake → three parallel risk sub-agents
    graph.add_edge("intake",           "property_risk")
    graph.add_edge("intake",           "geographic_risk")
    graph.add_edge("intake",           "business_risk")

    # Fan-in: all three sub-agents → risk_aggregator
    graph.add_edge("property_risk",    "risk_aggregator")
    graph.add_edge("geographic_risk",  "risk_aggregator")
    graph.add_edge("business_risk",    "risk_aggregator")

    graph.add_edge("risk_aggregator",  "compliance")

    # ── Compliance conditional routing ────────────────────────────────────────
    graph.add_conditional_edges(
        "compliance",
        route_compliance,
        {
            "coverage_gap":       "coverage_gap",
            "human_escalation":   "human_escalation",
            "compliance_retry":   "compliance_retry",
        }
    )

    graph.add_conditional_edges(
        "compliance_retry",
        route_compliance_retry,
        {
            "coverage_gap":       "coverage_gap",
            "human_escalation":   "human_escalation",
        }
    )

    # Fan-out: both cloud parallel agents run after compliance PASS
    graph.add_edge("coverage_gap",     "merge_parallel")
    graph.add_edge("pricing",          "merge_parallel")

    # ── Confidence routing after parallel merge ───────────────────────────────
    graph.add_conditional_edges(
        "merge_parallel",
        route_confidence,
        {
            "explainability":     "explainability",
            "human_escalation":   "human_escalation",
        }
    )

    graph.add_edge("explainability",   END)
    graph.add_edge("human_escalation", END)

    return graph.compile()


# Module-level compiled workflow for import
workflow = build_workflow()


def run_submission(
    raw_document: str,
    scenario_id: str = "",
    ground_truth_decision: str = "",
    ground_truth_compliance: str = "",
    scenario_complexity: str = "",
) -> UnderwritingState:
    """
    Run a single submission through the full workflow.

    Args:
        raw_document: Raw submission text (PDF content, email, or structured JSON string)
        scenario_id: Optional ID for evaluation tracking
        ground_truth_decision: Expected decision for evaluation
        ground_truth_compliance: Expected compliance outcome for evaluation
        scenario_complexity: Complexity label for evaluation

    Returns:
        Final UnderwritingState with all results and audit trail
    """
    initial_state = UnderwritingState(
        raw_document=raw_document,
        scenario_id=scenario_id,
        ground_truth_decision=ground_truth_decision,
        ground_truth_compliance=ground_truth_compliance,
        scenario_complexity=scenario_complexity,
    )

    result = workflow.invoke(initial_state)
    # LangGraph returns a dict (not the Pydantic model) when Annotated reducers are active
    if isinstance(result, dict):
        return UnderwritingState.model_validate(result)
    return result
