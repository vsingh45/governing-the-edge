"""
Evaluation Harness
Runs all 20 scenarios against 3 systems and produces results for the paper.

Systems compared:
  1. Monolithic GPT-4o — single prompt, no agents
  2. Linear Pipeline   — same agents, sequential, post-hoc compliance only
  3. Our Framework     — governance-aware hybrid local-cloud system

Metrics:
  - Compliance Accuracy: % scenarios where compliance determination matches ground truth
  - Workflow Completion Rate: % scenarios that reach final decision without error
  - Average Latency: seconds per submission
"""
from __future__ import annotations
import time
import json
from typing import Dict, List, Any
from dataclasses import dataclass, field

from data.scenarios.scenarios import SCENARIOS
from evaluation.error_tracking import error_tracker


@dataclass
class EvalResult:
    scenario_id:          str
    line:                 str
    complexity:           str
    ground_truth_decision: str
    ground_truth_compliance: str
    system_name:          str
    predicted_decision:   str    = ""
    predicted_compliance: str    = ""
    compliance_correct:   bool   = False
    workflow_completed:   bool   = False
    latency_seconds:      float  = 0.0
    error:                str    = ""
    audit_trail_length:   int    = 0


@dataclass
class EvalSummary:
    system_name:           str
    total_scenarios:       int   = 0
    compliance_correct:    int   = 0
    workflow_completed:    int   = 0
    total_latency:         float = 0.0
    results:               List[EvalResult] = field(default_factory=list)

    @property
    def compliance_accuracy(self) -> float:
        return self.compliance_correct / self.total_scenarios if self.total_scenarios > 0 else 0.0

    @property
    def completion_rate(self) -> float:
        return self.workflow_completed / self.total_scenarios if self.total_scenarios > 0 else 0.0

    @property
    def avg_latency(self) -> float:
        return self.total_latency / self.total_scenarios if self.total_scenarios > 0 else 0.0


# ── System 1: Monolithic GPT-4o ───────────────────────────────────────────────

def run_monolithic(scenario: Dict) -> EvalResult:
    """
    Baseline 1: Single GPT-4o prompt.
    Full submission in, decision out. No governance, no agents.
    """
    from agents.llm_client import llm_call
    from pydantic import BaseModel
    from config.settings import CLOUD_MODEL

    class MonolithicOutput(BaseModel):
        compliance_status: str   # PASS | FAIL
        decision:          str   # APPROVE | DECLINE | REFER | REQUEST_INFO
        reasoning:         str

    result = EvalResult(
        scenario_id=scenario["scenario_id"],
        line=scenario["line"],
        complexity=scenario["complexity"],
        ground_truth_decision=scenario["ground_truth_decision"],
        ground_truth_compliance=scenario["ground_truth_compliance"],
        system_name="monolithic_sonnet",
    )

    start = time.time()
    try:
        output = llm_call(
            model=CLOUD_MODEL,
            system_prompt=(
                "You are a commercial P&C insurance underwriter. "
                "Review this submission and determine: "
                "1. compliance_status: PASS if no underwriting rule violations, FAIL if violations found; "
                "2. decision: APPROVE | DECLINE | REFER | REQUEST_INFO; "
                "3. reasoning: brief explanation. "
                "Common rules to check: frame construction >3 stories=decline, "
                "TIV >$10M=refer, habitational >4 units=not eligible, "
                "loss ratio >70%=decline/surcharge, building age >40yr no reno=inspection, "
                "fleet >20 vehicles=fleet specialist, driver with 2+ major violations=decline driver, "
                "radius >500mi=interstate filing, fleet age >10yr=surcharge, "
                "DOT conditional/unsatisfactory=decline."
            ),
            user_prompt=f"Review this submission:\n{scenario['submission']}",
            response_schema=MonolithicOutput,
        )
        result.predicted_compliance = output.compliance_status
        result.predicted_decision   = output.decision
        result.compliance_correct   = (output.compliance_status == scenario["ground_truth_compliance"])
        result.workflow_completed   = True

    except Exception as e:
        result.error = str(e)
        result.workflow_completed = False

    result.latency_seconds = time.time() - start
    return result


# ── System 2: Linear Pipeline ─────────────────────────────────────────────────

def run_linear_pipeline(scenario: Dict) -> EvalResult:
    """
    Baseline 2: Linear sequential agents, no conditional routing.
    Post-hoc compliance validation at the end.
    Inspired by Sajid et al. (2025) CrewAI approach.
    """
    from agents.llm_client import llm_call
    from pydantic import BaseModel
    from config.settings import CLOUD_MODEL

    class LinearOutput(BaseModel):
        risk_tier:         str
        compliance_status: str
        decision:          str
        reasoning:         str

    result = EvalResult(
        scenario_id=scenario["scenario_id"],
        line=scenario["line"],
        complexity=scenario["complexity"],
        ground_truth_decision=scenario["ground_truth_decision"],
        ground_truth_compliance=scenario["ground_truth_compliance"],
        system_name="linear_pipeline",
    )

    start = time.time()
    try:
        # Step 1: Risk assessment
        risk_result = llm_call(
            model=CLOUD_MODEL,
            system_prompt="You are a risk assessor. Evaluate the overall risk tier: LOW | MEDIUM | HIGH | DECLINE.",
            user_prompt=f"Assess risk for:\n{scenario['submission']}",
            response_schema=type("RiskOut", (BaseModel,), {"__annotations__": {"risk_tier": str, "reasoning": str}}),
        )

        # Step 2: Coverage analysis
        coverage_result = llm_call(
            model=CLOUD_MODEL,
            system_prompt="You are a coverage specialist. Identify any coverage gaps in this submission.",
            user_prompt=f"Risk tier: {risk_result.risk_tier}\nSubmission:\n{scenario['submission']}",
            response_schema=type("CovOut", (BaseModel,), {"__annotations__": {"gaps": str, "count": int}}),
        )

        # Step 3: Post-hoc compliance check (linear pipeline — runs AFTER other agents)
        final_result = llm_call(
            model=CLOUD_MODEL,
            system_prompt=(
                "You are a compliance validator. Check for rule violations AND make a final decision. "
                "compliance_status: PASS or FAIL. decision: APPROVE | DECLINE | REFER | REQUEST_INFO."
            ),
            user_prompt=(
                f"Risk tier: {risk_result.risk_tier}\n"
                f"Coverage gaps: {coverage_result.gaps}\n"
                f"Submission:\n{scenario['submission']}"
            ),
            response_schema=LinearOutput,
        )

        result.predicted_compliance = final_result.compliance_status
        result.predicted_decision   = final_result.decision
        result.compliance_correct   = (final_result.compliance_status == scenario["ground_truth_compliance"])
        result.workflow_completed   = True

    except Exception as e:
        result.error = str(e)
        result.workflow_completed = False

    result.latency_seconds = time.time() - start
    return result


# ── System 3: Our Framework ───────────────────────────────────────────────────

def run_our_framework(scenario: Dict) -> EvalResult:
    """
    Our governance-aware hybrid local-cloud framework.
    """
    from graph.workflow import run_submission

    result = EvalResult(
        scenario_id=scenario["scenario_id"],
        line=scenario["line"],
        complexity=scenario["complexity"],
        ground_truth_decision=scenario["ground_truth_decision"],
        ground_truth_compliance=scenario["ground_truth_compliance"],
        system_name="governing_the_edge",
    )

    start = time.time()
    try:
        state = run_submission(
            raw_document=scenario["submission"],
            scenario_id=scenario["scenario_id"],
            ground_truth_decision=scenario["ground_truth_decision"],
            ground_truth_compliance=scenario["ground_truth_compliance"],
            scenario_complexity=scenario["complexity"],
        )

        result.predicted_compliance = state.compliance_result.status
        result.predicted_decision   = state.final_decision
        result.compliance_correct   = (state.compliance_result.status == scenario["ground_truth_compliance"])
        result.workflow_completed   = bool(state.final_decision)
        result.audit_trail_length   = len(state.audit_trail)

    except Exception as e:
        result.error = str(e)
        result.workflow_completed = False

    result.latency_seconds = time.time() - start
    return result


# ── Main Evaluation Runner ────────────────────────────────────────────────────

def run_full_evaluation(
    run_monolithic_flag: bool = True,
    run_linear_flag: bool = True,
    run_framework_flag: bool = True,
    verbose: bool = True,
) -> Dict[str, EvalSummary]:
    """
    Run all 20 scenarios against selected systems.
    Returns a dict of system_name -> EvalSummary.
    """
    summaries: Dict[str, EvalSummary] = {}

    systems = []
    if run_monolithic_flag: systems.append(("monolithic_sonnet",      run_monolithic))
    if run_linear_flag:      systems.append(("linear_pipeline",        run_linear_pipeline))
    if run_framework_flag:   systems.append(("governing_the_edge",     run_our_framework))

    for system_name, runner in systems:
        summary = EvalSummary(system_name=system_name, total_scenarios=len(SCENARIOS))
        summaries[system_name] = summary

        if verbose:
            print(f"\n{'='*60}")
            print(f"Running: {system_name}")
            print(f"{'='*60}")

        for i, scenario in enumerate(SCENARIOS):
            if verbose:
                print(f"  [{i+1:02d}/{len(SCENARIOS)}] {scenario['scenario_id']} ({scenario['complexity']})...", end=" ", flush=True)

            result = runner(scenario)
            summary.results.append(result)

            if result.compliance_correct: summary.compliance_correct += 1
            if result.workflow_completed: summary.workflow_completed += 1
            summary.total_latency += result.latency_seconds

            if verbose:
                status = "✓" if result.compliance_correct else "✗"
                print(f"{status} compliance={result.predicted_compliance} decision={result.predicted_decision} ({result.latency_seconds:.1f}s)")

        if verbose:
            print(f"\n  RESULTS — {system_name}:")
            print(f"    Compliance Accuracy:    {summary.compliance_accuracy:.1%}")
            print(f"    Workflow Completion:     {summary.completion_rate:.1%}")
            print(f"    Avg Latency:             {summary.avg_latency:.1f}s")

        # Persist after each system so data survives interruptions
        error_tracker.to_file("evaluation/error_report.json")

    return summaries


def print_comparison_table(summaries: Dict[str, EvalSummary]) -> None:
    """Print a formatted comparison table for the paper."""
    print("\n" + "="*70)
    print("RESULTS TABLE — For Paper Section V")
    print("="*70)
    print(f"{'System':<30} {'Compliance Acc.':<18} {'Completion Rate':<18} {'Avg Latency'}")
    print("-"*70)
    for name, s in summaries.items():
        print(f"{name:<30} {s.compliance_accuracy:<18.1%} {s.completion_rate:<18.1%} {s.avg_latency:.1f}s")
    print("="*70)

    # Per-complexity breakdown
    print("\nPer-Complexity Compliance Accuracy:")
    complexities = ["STRAIGHTFORWARD_APPROVAL", "WARNING_COMPLIANCE", "HARD_STOP_VIOLATION", "LOW_CONFIDENCE_ESCALATION"]
    for complexity in complexities:
        print(f"\n  {complexity}:")
        for name, s in summaries.items():
            subset = [r for r in s.results if r.complexity == complexity]
            if subset:
                acc = sum(1 for r in subset if r.compliance_correct) / len(subset)
                print(f"    {name:<30} {acc:.1%} ({sum(1 for r in subset if r.compliance_correct)}/{len(subset)})")


def save_results(summaries: Dict[str, EvalSummary], output_path: str = "results.json") -> None:
    """Save full results to JSON for analysis."""
    output = {}
    for name, summary in summaries.items():
        output[name] = {
            "compliance_accuracy": summary.compliance_accuracy,
            "completion_rate":     summary.completion_rate,
            "avg_latency":         summary.avg_latency,
            "results": [
                {
                    "scenario_id":           r.scenario_id,
                    "complexity":            r.complexity,
                    "ground_truth_compliance": r.ground_truth_compliance,
                    "predicted_compliance":  r.predicted_compliance,
                    "compliance_correct":    r.compliance_correct,
                    "workflow_completed":    r.workflow_completed,
                    "latency":               r.latency_seconds,
                    "error":                 r.error,
                }
                for r in summary.results
            ]
        }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    summaries = run_full_evaluation(verbose=True)
    print_comparison_table(summaries)
    save_results(summaries, "evaluation/results.json")
    error_tracker.to_file("evaluation/error_report.json")
    print("Error report saved to evaluation/error_report.json")
