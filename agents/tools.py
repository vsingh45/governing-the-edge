"""
Tool stubs for external data sources.
All tools return realistic mock data — no real API calls.
Used by local_agents.py and cloud_agents.py for risk dimension scoring.
"""
from typing import Optional, Dict, List
import json


# ── Document Processing ───────────────────────────────────────────────────────

def ocr_document(raw_document: str) -> Dict:
    """
    Parse unstructured document (ACORD form, email, image, etc).
    Returns extracted fields with confidence scores.
    """
    return {
        "extracted_fields": {
            "business_name": "Unknown Business",
            "address": "Unknown Address",
            "sic_code": "0000",
            "occupancy_type": "OFFICE",
            "year_built": 2000,
            "construction_class": "MASONRY"
        },
        "confidence": 0.85,
        "warnings": []
    }


# ── Address & Business Validation ─────────────────────────────────────────────

def validate_address(address: str) -> Dict:
    """
    Validate address format and basic sanity checks.
    Returns normalized address and geocoding confidence.
    """
    return {
        "address_valid": True,
        "normalized_address": address,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "confidence": 0.95,
        "warnings": []
    }


def lookup_sic_code(business_name: str, business_type: str) -> Dict:
    """
    Look up SIC code by business name and type.
    Returns primary and secondary SIC codes.
    """
    sic_map = {
        "RETAIL": "5411",
        "RESTAURANT": "5812",
        "WAREHOUSE": "4225",
        "OFFICE": "8111",
        "CONTRACTOR": "1622",
        "HABITATIONAL": "6513"
    }
    sic = sic_map.get(business_type, "9999")
    return {
        "sic_code": sic,
        "sic_description": f"Business Type {business_type}",
        "confidence": 0.90
    }


# ── Property Risk Data ────────────────────────────────────────────────────────

def lookup_fema_flood_zone(latitude: float, longitude: float, address: str) -> Dict:
    """
    Check FEMA flood risk zone for a property location.
    Returns FEMA flood zone (X, A, AE, VE, etc) and flood risk level.
    """
    # Mock: 70% of locations are Zone X (low risk)
    import random
    zones = ["X", "X", "X", "X", "X", "A", "A", "AE", "VE"]
    zone = random.choice(zones)

    risk_map = {
        "X": "LOW",
        "A": "MEDIUM",
        "AE": "MEDIUM_HIGH",
        "VE": "HIGH"
    }

    return {
        "fema_flood_zone": zone,
        "flood_risk_level": risk_map.get(zone, "UNKNOWN"),
        "100yr_flood_probability": 0.01 if zone == "X" else 0.10,
        "confidence": 0.95,
        "data_source": "FEMA National Flood Hazard Layer (2024)"
    }


def lookup_wildfire_risk(latitude: float, longitude: float, state: str) -> Dict:
    """
    Check wildfire risk score for a property (WUI — Wildland-Urban Interface).
    Returns wildfire risk tier and historical incident count in 5-mile radius.
    """
    import random
    risk_tier = random.choice(["LOW", "LOW", "MEDIUM", "MEDIUM", "HIGH", "VERY_HIGH"])

    return {
        "wildfire_risk_tier": risk_tier,
        "wui_distance_km": round(random.uniform(0.5, 20), 1),
        "incidents_5yr_5mi_radius": random.randint(0, 8),
        "confidence": 0.85,
        "data_source": "USDA Wildfire Risk to Communities"
    }


# ── Geographic Risk Data (Motor Vehicle Records, Driver Risk) ─────────────────

def lookup_mvr(driver_name: str, driver_license: str, state: str) -> Dict:
    """
    Motor Vehicle Record (MVR) lookup.
    Returns violations, accidents, license status for a driver.
    """
    import random
    violation_types = [
        "SPEEDING",
        "UNSAFE_LANE_CHANGE",
        "FOLLOWING_TOO_CLOSE",
        "RECKLESS_DRIVING",
        "VIOLATION_OF_TRAFFIC_SIGNAL"
    ]

    violations = [random.choice(violation_types) for _ in range(random.randint(0, 3))]

    return {
        "driver_license_status": "VALID",
        "violations_3yr": violations,
        "accidents_3yr": random.randint(0, 2),
        "at_fault_accidents": random.randint(0, 1),
        "confidence": 0.90,
        "data_source": "State Motor Vehicle Records"
    }


# ── Business Risk Data (D&B, DOT Safety) ──────────────────────────────────────

def lookup_dnb_business(business_name: str, ein: str, state: str) -> Dict:
    """
    Dun & Bradstreet (D&B) business credit and risk lookup.
    Returns payment history, failure risk, business stability score.
    """
    import random

    return {
        "company_name": business_name,
        "years_in_business": random.randint(2, 50),
        "payment_history": random.choice(["EXCELLENT", "GOOD", "FAIR", "POOR"]),
        "business_failure_score": round(random.uniform(0, 100), 1),  # 0=lowest risk, 100=highest
        "employee_count": random.choice([1, 5, 10, 25, 50, 100, 250]),
        "confidence": 0.85,
        "data_source": "Dun & Bradstreet"
    }


def lookup_dot_safety_rating(carrier_name: str, mc_number: str) -> Dict:
    """
    DOT (Department of Transportation) safety rating for a commercial carrier.
    Returns SAFER database safety rating: SATISFACTORY | CONDITIONAL | UNSATISFACTORY | NOT_RATED.
    """
    import random
    rating = random.choice(["SATISFACTORY", "SATISFACTORY", "SATISFACTORY", "CONDITIONAL", "UNSATISFACTORY"])

    return {
        "dot_safety_rating": rating,
        "inspections_24mo": random.randint(0, 20),
        "violations_24mo": random.randint(0, 15),
        "crashes_24mo": random.randint(0, 5),
        "confidence": 0.95,
        "data_source": "FMCSA SAFER Database"
    }


# ── Compliance & Rules Engine ─────────────────────────────────────────────────

def query_rules_engine(submission_type: str, state: str, risk_profile: Dict,
                       parsed_fields: Dict) -> Dict:
    """
    Query the governance rules engine for compliance violations.
    Returns list of rule IDs violated, severity levels, remediation steps.
    """
    # Rules engine is called within the compliance agent; this is a direct query
    # that can be used for debugging or explicit rule checking
    return {
        "rules_checked": [
            "RULE_001_MIN_INSURED_VALUE",
            "RULE_002_LOSS_RATIO_THRESHOLD",
            "RULE_003_CONSTRUCTION_RESTRICTION",
            "RULE_004_OCCUPANCY_RESTRICTION"
        ],
        "violations": [],
        "severity": "NONE",
        "confidence": 0.95
    }


# ── Pricing & Rate Data ───────────────────────────────────────────────────────

def lookup_base_rate(submission_type: str, sic_code: str, state: str,
                     construction_class: Optional[str] = None) -> Dict:
    """
    Lookup base rate and tier for a given submission type and SIC code.
    Returns base rate per $100 of coverage, adjustment factor ranges.
    """
    import random

    base_rates = {
        "COMMERCIAL_PROPERTY": round(random.uniform(0.5, 3.0), 2),
        "COMMERCIAL_AUTO": round(random.uniform(1.0, 5.0), 2)
    }

    return {
        "base_rate_per_100": base_rates.get(submission_type, 2.0),
        "rate_tier": random.choice(["PREFERRED", "STANDARD", "SUBSTANDARD"]),
        "adjustment_factor_ranges": {
            "construction_class": (0.85, 1.25) if construction_class else None,
            "loss_history": (0.80, 1.50),
            "occupancy": (0.90, 1.40),
            "management_quality": (0.95, 1.20)
        },
        "confidence": 0.90,
        "effective_date": "2026-06-01"
    }


# ── Batch Tool Call Handler ───────────────────────────────────────────────────

class ToolCallRecorder:
    """
    Records tool calls invoked by agents for audit trail and error tracking.
    Each call is timestamped and linked to an agent and scenario.
    """

    def __init__(self):
        self.calls: List[Dict] = []

    def record_call(self, scenario_id: str, agent_name: str, tool_name: str,
                    input_args: Dict, output: Dict, latency_ms: float,
                    success: bool, error: str = ""):
        """Record a single tool call."""
        self.calls.append({
            "scenario_id": scenario_id,
            "agent_name": agent_name,
            "tool_name": tool_name,
            "input_args": input_args,
            "output": output,
            "latency_ms": latency_ms,
            "success": success,
            "error": error
        })

    def get_tool_calls_for_scenario(self, scenario_id: str) -> List[Dict]:
        """Retrieve all tool calls for a scenario."""
        return [c for c in self.calls if c["scenario_id"] == scenario_id]

    def get_failure_tools(self) -> List[Dict]:
        """Retrieve all failed tool calls."""
        return [c for c in self.calls if not c["success"]]

    def clear(self):
        """Clear all recorded calls."""
        self.calls = []


# Global recorder instance
tool_recorder = ToolCallRecorder()
