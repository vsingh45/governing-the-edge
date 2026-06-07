"""
Local Agents — run on Gemma 4 (on-premise).
These agents process raw sensitive submission data.
Raw document and parsed fields NEVER leave this layer.

Agents:
  1. document_parser_node
  2. intake_node
  3a. property_risk_node / fleet_risk_node
  3b. geographic_risk_node / driver_risk_node
  3c. business_risk_node / operations_risk_node
  4. compliance_node / compliance_retry_node
"""
from __future__ import annotations
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

from config.settings import get_model
from agents.llm_client import llm_call
from governance.rules_engine import rules_engine
from graph.state import UnderwritingState, make_audit_entry


# ── Output Schemas ────────────────────────────────────────────────────────────

class DocumentParserOutput(BaseModel):
    document_type:    str           # ACORD_125 | ACORD_126 | LOSS_RUN | EMAIL | JSON | UNKNOWN
    normalized_text:  str
    flagged_sections: List[str]     = Field(default_factory=list)
    confidence:       float         = 0.8
    explanation:      Dict          = Field(default_factory=dict)

class IntakeOutput(BaseModel):
    submission_type:        str     # COMMERCIAL_PROPERTY | COMMERCIAL_AUTO
    business_name:          str     = ""
    sic_code:               str     = ""
    # Commercial Property fields
    construction_class:     Optional[str]   = None   # FRAME | MASONRY | JOISTED_MASONRY | FIRE_RESISTIVE
    stories:                Optional[int]   = None
    total_insured_value:    Optional[float] = None
    occupancy_type:         Optional[str]   = None   # OFFICE | RETAIL | RESTAURANT | HABITATIONAL | WAREHOUSE | CONTRACTOR
    unit_count:             Optional[int]   = None
    year_built:             Optional[int]   = None
    last_renovation_year:   Optional[int]   = None
    three_year_loss_ratio:  Optional[float] = None
    # Commercial Auto fields
    fleet_size:             Optional[int]   = None
    average_fleet_age:      Optional[float] = None
    radius_of_operations:   Optional[int]   = None
    dot_safety_rating:      Optional[str]   = None   # SATISFACTORY | CONDITIONAL | UNSATISFACTORY | NOT_RATED
    driver_mvr_violations:  Optional[int]   = None   # max violations across driver roster
    # Common
    coverage_requested:     Dict    = Field(default_factory=dict)
    loss_history:           List    = Field(default_factory=list)
    missing_fields:         List[str] = Field(default_factory=list)
    confidence:             float   = 0.8
    explanation:            Dict    = Field(default_factory=dict)

class RiskSubAgentOutput(BaseModel):
    dimension:      str             # identifies which dimension this agent scored
    score:          float           # [0,1] — higher = higher risk
    band:           str             # LOW | MEDIUM | HIGH | DECLINE
    top_factors:    List[str]       = Field(default_factory=list)
    missing_inputs: List[str]       = Field(default_factory=list)
    confidence:     float           = 0.8
    explanation:    Dict            = Field(default_factory=dict)

class ComplianceAgentOutput(BaseModel):
    status:         str             # PASS | FAIL | CONFLICT
    rules_checked:  List[str]       = Field(default_factory=list)
    violations:     List[Dict]      = Field(default_factory=list)
    conflicts:      List[Dict]      = Field(default_factory=list)
    severity:       str             = "NONE"    # HARD_STOP | WARNING | NONE
    confidence:     float           = 0.9
    explanation:    Dict            = Field(default_factory=dict)


# ── Node 1: Document Parser ───────────────────────────────────────────────────

def document_parser_node(state: UnderwritingState) -> UnderwritingState:
    """
    Normalize raw PDF/email to clean structured text.
    Raw data stays local — never sent to cloud.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "document_parser"))

    result = llm_call(
        model=get_model("local"),
        system_prompt=(
            "You are a document parser for insurance submissions. "
            "Your only job is to normalize the input into clean, structured text. "
            "Do NOT interpret the content or make underwriting decisions. "
            "Identify the document type, extract all readable text preserving section structure, "
            "and flag any sections that appear corrupted, missing, or illegible. "
            "Do not guess at missing information — leave it blank."
        ),
        user_prompt=(
            f"Parse this insurance submission document:\n\n{state.raw_document}\n\n"
            "Extract and normalize the content. Identify the document type."
        ),
        response_schema=DocumentParserOutput,
    )

    state.agent_explanations["document_parser"] = {
        "agent": "document_parser",
        "action": f"Parsed {result.document_type} submission",
        "quality": result.confidence,
        "flags": result.flagged_sections,
    }
    state.parsed_fields["_normalized_text"] = result.normalized_text
    state.parsed_fields["_document_type"]   = result.document_type

    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "document_parser",
        output_summary=f"Parsed as {result.document_type}, confidence={result.confidence:.2f}"
    ))
    return state


# ── Node 2: Intake Agent ──────────────────────────────────────────────────────

def intake_node(state: UnderwritingState) -> UnderwritingState:
    """
    Extract typed underwriting fields from normalized text.
    Uses ACORD 125 schema as extraction template.
    Returns null for missing fields rather than guessing.
    """
    state.audit_trail.append(make_audit_entry("AGENT_START", "intake"))

    normalized = state.parsed_fields.get("_normalized_text", state.raw_document)

    result = llm_call(
        model=get_model("local"),
        system_prompt=(
            "You are an insurance intake specialist. Extract structured underwriting fields "
            "from the submission text following the ACORD 125 commercial lines schema. "
            "CRITICAL: Return null for any field you cannot confidently extract. "
            "Never guess or hallucinate values. A null value is always preferable to a wrong value. "
            "Flag any internal inconsistencies you notice in the data."
        ),
        user_prompt=(
            f"Extract all underwriting fields from this submission:\n\n{normalized}"
        ),
        response_schema=IntakeOutput,
    )

    # Write structured fields to state
    state.submission_type = result.submission_type
    for field, value in result.model_dump().items():
        if field not in ("confidence", "explanation", "missing_fields") and value is not None:
            state.parsed_fields[field] = value

    state.agent_explanations["intake"] = {
        "agent": "intake",
        "action": f"Extracted {result.submission_type} submission fields",
        "business": result.business_name,
        "missing_fields": result.missing_fields,
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "intake",
        output_summary=f"Line: {result.submission_type}, Business: {result.business_name}, Missing: {result.missing_fields}"
    ))
    return state


# ── Nodes 3a/3b/3c: Risk Sub-Agents ──────────────────────────────────────────

def _run_risk_subagent(
    state: UnderwritingState,
    dimension_label: str,
    agent_name: str,
    scoring_criteria: str,
) -> RiskSubAgentOutput:
    """Shared runner for all three risk sub-agents."""
    fields_json = str({k: v for k, v in state.parsed_fields.items() if not k.startswith("_")})

    return llm_call(
        model=get_model("local"),
        system_prompt=(
            f"You are a specialized insurance risk assessor evaluating the {dimension_label} dimension only. "
            f"Score ONLY this dimension — do not consider other risk dimensions. "
            f"Use this scoring rubric:\n{scoring_criteria}\n\n"
            "Score bands: 0.0-0.3=LOW, 0.3-0.6=MEDIUM, 0.6-0.8=HIGH, 0.8-1.0=DECLINE. "
            "Reduce your confidence score if relevant input fields are null or inconsistent. "
            "Report your top 3 factors driving the score."
        ),
        user_prompt=(
            f"Submission type: {state.submission_type}\n"
            f"Submission fields:\n{fields_json}\n\n"
            f"Score the {dimension_label} risk dimension."
        ),
        response_schema=RiskSubAgentOutput,
    )


def property_risk_node(state: UnderwritingState) -> UnderwritingState:
    """3a — Property risk: construction, occupancy, TIV."""
    state.audit_trail.append(make_audit_entry("AGENT_START", "property_risk"))

    if state.submission_type == "COMMERCIAL_PROPERTY":
        criteria = (
            "Score based on: construction class (FRAME=high risk, FIRE_RESISTIVE=low risk), "
            "occupancy type (HABITATIONAL=high, WAREHOUSE=medium, OFFICE=low), "
            "total insured value (>$5M=high, $1-5M=medium, <$1M=low), "
            "building age (>40yr=high, 20-40yr=medium, <20yr=low)."
        )
    else:  # COMMERCIAL_AUTO
        criteria = (
            "Score based on: fleet size (>15=high, 8-15=medium, <8=low), "
            "vehicle types (heavy trucks=high, mixed=medium, light vehicles=low), "
            "average fleet age (>10yr=high, 5-10yr=medium, <5yr=low)."
        )

    result = _run_risk_subagent(state, "Property/Fleet", "property_risk", criteria)
    state.risk_profile.dimension_a_score = result.score

    state.agent_explanations["property_risk"] = {
        "agent": "property_risk",
        "dimension": result.dimension,
        "score": result.score,
        "band": result.band,
        "top_factors": result.top_factors,
        "confidence": result.confidence,
    }
    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "property_risk",
        output_summary=f"Score={result.score:.2f}, Band={result.band}"
    ))
    return state


def geographic_risk_node(state: UnderwritingState) -> UnderwritingState:
    """3b — Geographic/Driver risk."""
    state.audit_trail.append(make_audit_entry("AGENT_START", "geographic_risk"))

    if state.submission_type == "COMMERCIAL_PROPERTY":
        criteria = (
            "Score based on: flood zone (VE=0.85, AE=0.5, X=0.1), "
            "wildfire risk (HIGH=0.75, MEDIUM=0.45, LOW=0.15), "
            "CAT exposure (hurricane/earthquake zone=high), "
            "distance to fire station (>5mi=high, 2-5mi=medium, <2mi=low)."
        )
    else:  # COMMERCIAL_AUTO
        criteria = (
            "Score based on: driver MVR violations (any driver >=2 major=high, 1 major=medium, clean=low), "
            "average driver age (<25 or >70=high, 25-65=low), "
            "driving experience (<2yr=high, 2-5yr=medium, >5yr=low)."
        )

    result = _run_risk_subagent(state, "Geographic/Driver", "geographic_risk", criteria)
    state.risk_profile.dimension_b_score = result.score

    state.agent_explanations["geographic_risk"] = {
        "agent": "geographic_risk",
        "score": result.score,
        "band": result.band,
        "top_factors": result.top_factors,
        "confidence": result.confidence,
    }
    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "geographic_risk",
        output_summary=f"Score={result.score:.2f}, Band={result.band}"
    ))
    return state


def business_risk_node(state: UnderwritingState) -> UnderwritingState:
    """3c — Business/Operations risk."""
    state.audit_trail.append(make_audit_entry("AGENT_START", "business_risk"))

    if state.submission_type == "COMMERCIAL_PROPERTY":
        criteria = (
            "Score based on: SIC code risk class (contractors/restaurants=high, retail=medium, office=low), "
            "years in business (<2yr=high, 2-5yr=medium, >5yr=low), "
            "prior loss frequency (>2 losses in 3yr=high, 1-2=medium, 0=low), "
            "loss severity relative to TIV (>20%=high, 10-20%=medium, <10%=low)."
        )
    else:  # COMMERCIAL_AUTO
        criteria = (
            "Score based on: radius of operations (>500mi=high, 200-500mi=medium, <200mi=low), "
            "cargo type (hazmat/explosives=high, general freight=medium, light cargo=low), "
            "DOT safety rating (CONDITIONAL/UNSATISFACTORY=high, SATISFACTORY=low), "
            "prior auto losses (>2 in 3yr=high, 1=medium, 0=low)."
        )

    result = _run_risk_subagent(state, "Business/Operations", "business_risk", criteria)
    state.risk_profile.dimension_c_score = result.score

    state.agent_explanations["business_risk"] = {
        "agent": "business_risk",
        "score": result.score,
        "band": result.band,
        "top_factors": result.top_factors,
        "confidence": result.confidence,
    }
    state.audit_trail.append(make_audit_entry(
        "AGENT_COMPLETE", "business_risk",
        output_summary=f"Score={result.score:.2f}, Band={result.band}"
    ))
    return state


# ── Node 4: Compliance Agent ──────────────────────────────────────────────────

def _run_compliance(
    state: UnderwritingState,
    retry_context: str = "",
) -> ComplianceAgentOutput:
    """Shared compliance runner used by both compliance_node and compliance_retry_node."""
    rule_prompt = rules_engine.format_rules_for_prompt(state.submission_type)
    fields_json = str({k: v for k, v in state.parsed_fields.items() if not k.startswith("_")})

    retry_instruction = ""
    if retry_context:
        retry_instruction = (
            f"\n\nPREVIOUS COMPLIANCE RESULT HAD CONFLICTS:\n{retry_context}\n"
            "For each conflicting rule pair, apply the MORE RESTRICTIVE rule. "
            "Document your resolution. Return PASS or FAIL — do not return CONFLICT again unless the conflict is genuinely unresolvable."
        )

    return llm_call(
        model=get_model("local"),
        system_prompt=(
            "You are a P&C insurance compliance officer. "
            "Check the submission against ALL applicable underwriting rules. "
            "For each rule, evaluate whether the submission fields satisfy the condition. "
            "Return PASS only if ALL rules are satisfied. "
            "Return FAIL if any HARD_STOP rule is violated. "
            "Return CONFLICT only if two rules genuinely contradict each other. "
            "IMPORTANT: Always cite the specific rule_id for any violation or conflict. "
            + retry_instruction
        ),
        user_prompt=(
            f"Submission type: {state.submission_type}\n"
            f"Submission fields:\n{fields_json}\n\n"
            f"{rule_prompt}\n\n"
            "Evaluate all rules and return your compliance determination."
        ),
        response_schema=ComplianceAgentOutput,
    )


def compliance_node(state: UnderwritingState) -> UnderwritingState:
    """Node 4 — First compliance check."""
    state.audit_trail.append(make_audit_entry("AGENT_START", "compliance"))

    result = _run_compliance(state)

    state.compliance_result.status        = result.status
    state.compliance_result.rules_checked = result.rules_checked
    state.compliance_result.violations    = result.violations
    state.compliance_result.conflicts     = result.conflicts
    state.compliance_result.severity      = result.severity

    state.agent_explanations["compliance"] = {
        "agent": "compliance",
        "status": result.status,
        "rules_checked": result.rules_checked,
        "violations": result.violations,
        "severity": result.severity,
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "GOVERNANCE_CHECK", "compliance",
        output_summary=f"Status={result.status}, Severity={result.severity}",
        governance_result=result.status,
        rule_ids_checked=result.rules_checked,
        routing_outcome=f"compliance -> {result.status.lower()}_path",
    ))
    return state


def compliance_retry_node(state: UnderwritingState) -> UnderwritingState:
    """Compliance retry — called only on CONFLICT. Applies more-restrictive-rule heuristic."""
    state.compliance_result.retry_count += 1
    state.audit_trail.append(make_audit_entry("AGENT_START", "compliance_retry"))

    conflict_context = str(state.compliance_result.conflicts)
    result = _run_compliance(state, retry_context=conflict_context)

    state.compliance_result.status    = result.status
    state.compliance_result.violations = result.violations
    state.compliance_result.conflicts  = result.conflicts
    state.compliance_result.severity   = result.severity

    state.agent_explanations["compliance_retry"] = {
        "agent": "compliance_retry",
        "status": result.status,
        "resolution": "Applied more-restrictive-rule heuristic",
        "confidence": result.confidence,
    }

    state.audit_trail.append(make_audit_entry(
        "GOVERNANCE_CHECK", "compliance_retry",
        output_summary=f"Retry result: {result.status}",
        governance_result=result.status,
        rule_ids_checked=result.rules_checked,
    ))
    return state
