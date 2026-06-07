# Governing the Edge
## A Hybrid Local-Cloud Multi-Agent Framework for Commercial P&C Insurance Underwriting

**Paper:** "Governing the Edge: A Hybrid Local-Cloud Multi-Agent Framework for Commercial P&C Insurance Underwriting"  
**Authors:** Vivek Kumar Singh (Cisco) · Gautam Bhowmick (Deloitte Consulting)  
**Conference:** IEEE AIBThings 2026, Central Michigan University

---

## Overview

This repository contains the reference implementation of the Governing the Edge framework — a governance-aware, privacy-preserving multi-agent system for commercial P&C insurance underwriting.

### Key Features
- **11-node LangGraph workflow** with governance-aware conditional routing
- **Hybrid local-cloud deployment** — sensitive data processed locally via Gemma 4, complex reasoning via Claude Sonnet
- **10 validated P&C compliance rules** across commercial property and commercial auto
- **Confidence-aware escalation** to human underwriters
- **Audit-grade explainability** assembled from per-agent explanation snippets
- **Provider-agnostic** via LiteLLM — swap models without changing agent code

---

## Architecture

```
Document Parser (Local/Gemma 4)
        ↓
Intake Agent (Local/Gemma 4)
        ↓
┌─────────────────────────────┐
│ Property/Fleet Risk (Local) │
│ Geographic/Driver (Local)   │  ← parallel
│ Business/Ops Risk (Local)   │
└─────────────────────────────┘
        ↓
Risk Aggregator (Cloud/Sonnet)   ← first cloud agent, receives scores only
        ↓
Compliance Agent (Local/Gemma 4)
        ↓
PASS ─────────────────────────────────────────────────┐
FAIL → Human Escalation                               │
CONFLICT → Retry → PASS ─────────────────────────────┤
               FAIL/CONFLICT → Human Escalation       │
                                                       ↓
                              ┌─────────────────────────────┐
                              │ Coverage Gap (Cloud/Sonnet)  │
                              │ Pricing (Cloud/Sonnet)       │  ← parallel
                              └─────────────────────────────┘
                                              ↓
                        confidence >= 0.80 → Explainability → Final Decision
                        confidence <  0.80 → Human Escalation
```

**Privacy boundary:** Raw submission data never leaves the local tier. Cloud agents receive only anonymized scores and structured flags.

---

## Quick Start

### Option A — Cloud Only (No Local Setup Required)
Run everything on cloud models. Fastest way to get started.

```bash
# 1. Clone and install
git clone https://github.com/vsingh45/governing-the-edge
cd governing-the-edge
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and OPENAI_API_KEY
# Set FALLBACK_ALL_CLOUD=true

# 3. Run evaluation
python -m evaluation.evaluator
```

### Option B — Hybrid (Local Gemma 4 + Cloud Sonnet)
Full privacy-preserving configuration as described in the paper.

```bash
# 1. Install Ollama
# https://ollama.ai/download

# 2. Pull Gemma model
ollama pull gemma2   # Use gemma2 until gemma4 is available in Ollama

# 3. Start Ollama server
ollama serve

# 4. Clone and install
git clone https://github.com/vsingh45/governing-the-edge
cd governing-the-edge
pip install -r requirements.txt

# 5. Configure
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY
# Set FALLBACK_ALL_CLOUD=false (default)
# Set LOCAL_MODEL=ollama/gemma2

# 6. Run evaluation
python -m evaluation.evaluator
```

---

## Running a Single Submission

```python
from graph.workflow import run_submission

# Commercial property example
result = run_submission(
    raw_document="""
    Business Name: Main Street Retail LLC
    Construction Class: MASONRY
    Stories: 2
    Total Insured Value: $850,000
    Occupancy Type: RETAIL
    3-Year Loss Ratio: 12%
    """,
    scenario_id="my-test-01",
)

print(f"Decision:    {result.final_decision}")
print(f"Compliance:  {result.compliance_result.status}")
print(f"Risk Tier:   {result.risk_profile.aggregate_tier}")
print(f"Confidence:  {result.confidence_score:.2f}")
print(f"Audit Trail: {len(result.audit_trail)} entries")
```

---

## Running the Full Evaluation

```bash
# Run all 3 systems against all 20 scenarios
python -m evaluation.evaluator

# Run only our framework
python -c "
from evaluation.evaluator import run_full_evaluation, print_comparison_table
summaries = run_full_evaluation(run_monolithic_flag=False, run_linear_flag=False)
print_comparison_table(summaries)
"
```

---

## Project Structure

```
governing-the-edge/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py          # All configuration — models, weights, thresholds
├── agents/
│   ├── llm_client.py        # Provider-agnostic LiteLLM wrapper
│   ├── local_agents.py      # Gemma 4 agents (parser, intake, risk, compliance)
│   └── cloud_agents.py      # Claude Sonnet agents (aggregator, gap, pricing, explainability)
├── graph/
│   ├── state.py             # UnderwritingState — shared state schema
│   ├── workflow.py          # LangGraph StateGraph definition
│   └── routing.py           # Routing functions and confidence scoring
├── governance/
│   └── rules_engine.py      # 10 validated P&C compliance rules
├── data/
│   └── scenarios/
│       └── scenarios.py     # 20 synthetic P&C scenarios
└── evaluation/
    ├── evaluator.py         # Evaluation harness — 3 systems × 20 scenarios
    └── results.json         # Generated after running evaluation
```

---

## Compliance Rules

The framework enforces 10 validated P&C underwriting rules:

| Rule ID | Line | Rule | Severity |
|---------|------|------|----------|
| CP-01 | Commercial Property | Frame construction > 3 stories → Decline | HARD STOP |
| CP-02 | Commercial Property | Single location TIV > $10M → Refer to specialty | HARD STOP |
| CP-03 | Commercial Property | Habitational > 4 units → Not eligible | HARD STOP |
| CP-04 | Commercial Property | 3-year loss ratio > 70% → Decline or surcharge | WARNING |
| CP-05 | Commercial Property | Building age > 40yr, no renovation → Inspection required | WARNING |
| CA-01 | Commercial Auto | Fleet > 20 vehicles → Fleet specialist | HARD STOP |
| CA-02 | Commercial Auto | Driver with 2+ major violations → Decline driver | HARD STOP |
| CA-03 | Commercial Auto | Radius > 500 miles → Interstate filing | WARNING |
| CA-04 | Commercial Auto | Average fleet age > 10yr → Surcharge | WARNING |
| CA-05 | Commercial Auto | DOT rating Conditional/Unsatisfactory → Decline | HARD STOP |

Rules validated by Gautam Bhowmick (Deloitte Consulting) from active insurance engagement experience.

---

## Citation

```bibtex
@inproceedings{singh2026governing,
  title={Governing the Edge: A Hybrid Local-Cloud Multi-Agent Framework for Commercial P\&C Insurance Underwriting},
  author={Singh, Vivek Kumar and Bhowmick, Gautam},
  booktitle={Proceedings of the IEEE 4th International Conference on Artificial Intelligence, Blockchain and Internet of Things (AIBThings)},
  year={2026},
  organization={IEEE}
}
```

---

## License

MIT License — see LICENSE file.

## Contact

- Vivek Kumar Singh — LinkedIn: linkedin.com/in/vivek-kumar-singh
- Gautam Bhowmick — LinkedIn: linkedin.com/in/gautam-bhowmick
