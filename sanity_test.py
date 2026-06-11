"""Sanity test — run a single scenario through the full framework."""
import time
from data.scenarios.scenarios import SCENARIOS
from evaluation.evaluator import run_our_framework

scenario = next(s for s in SCENARIOS if s["scenario_id"] == "CP-S06")
print(f"Scenario:     {scenario['scenario_id']} ({scenario['complexity']})")
print(f"Ground truth: compliance={scenario['ground_truth_compliance']}  decision={scenario['ground_truth_decision']}")
print("Running...", flush=True)

t0 = time.time()
result = run_our_framework(scenario)
elapsed = time.time() - t0

mark = "✓" if result.compliance_correct else "✗"
print(f"\nResult:   {mark}")
print(f"Compliance: {result.predicted_compliance}")
print(f"Decision:   {result.predicted_decision}")
print(f"Latency:    {elapsed:.1f}s")
print(f"Error:      {result.error or 'none'}")
