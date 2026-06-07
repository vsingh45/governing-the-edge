"""
Configuration — all settings in one place.
Load from environment or .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── Model Config ──────────────────────────────────────────────────────────────
LOCAL_MODEL  = os.getenv("LOCAL_MODEL",  "ollama/gemma2")
CLOUD_MODEL  = os.getenv("CLOUD_MODEL",  "claude-sonnet-4-6")
FALLBACK_ALL_CLOUD = os.getenv("FALLBACK_ALL_CLOUD", "false").lower() == "true"

def get_model(tier: str) -> str:
    """
    Return the model string for a given tier.
    If FALLBACK_ALL_CLOUD=true, all agents use the cloud model.
    This lets you run the full system without a local Ollama setup.
    """
    if FALLBACK_ALL_CLOUD:
        return CLOUD_MODEL
    return LOCAL_MODEL if tier == "local" else CLOUD_MODEL

# ── Routing Config ────────────────────────────────────────────────────────────
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.80"))

# ── Weights for confidence scoring ───────────────────────────────────────────
WEIGHT_INTRA_AGENT    = 0.40   # average self-reported agent confidence
WEIGHT_INTER_AGENT    = 0.35   # inter-agent consistency
WEIGHT_GOVERNANCE     = 0.25   # governance resolution score

# ── Risk aggregation weights by line ─────────────────────────────────────────
RISK_WEIGHTS = {
    "COMMERCIAL_PROPERTY": {
        "dimension_a": 0.40,   # property risk
        "dimension_b": 0.35,   # geographic risk
        "dimension_c": 0.25,   # business risk
    },
    "COMMERCIAL_AUTO": {
        "dimension_a": 0.30,   # fleet risk
        "dimension_b": 0.45,   # driver risk
        "dimension_c": 0.25,   # operations risk
    }
}

# ── Compliance ────────────────────────────────────────────────────────────────
MAX_COMPLIANCE_RETRIES = 1     # one retry on CONFLICT before escalating
