"""
Error Tracking & Categorization
Tracks per-agent failures across 8 failure categories for detailed ablation analysis.

Failure Categories:
  1. LLM_PARSE_ERROR — LLM output cannot be parsed as valid JSON/structured output
  2. SCHEMA_VALIDATION — LLM output parses but fails Pydantic schema validation
  3. TOOL_FAILURE — Tool call fails (network error, data not found, etc)
  4. TIMEOUT — LLM call or tool call exceeds configured timeout
  5. HALLUCINATION — LLM produces internally inconsistent or false claims
  6. INCONSISTENCY — Agent output contradicts another agent's output
  7. NULL_REQUIRED — Required field is null/missing in agent output
  8. GOVERNANCE_CONFLICT — Agent output violates compliance rules (not a hard stop)
  9. LLM_API_ERROR — Authentication, rate limit, quota exceeded
"""
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json


class ErrorRecord(BaseModel):
    """Single error event."""
    scenario_id: str
    agent_name: str
    error_category: str  # One of the 8 categories above
    error_detail: str    # Human-readable error message
    timestamp: str       # ISO 8601
    retry_count: int     # Number of retries attempted
    final_output: Optional[str] = ""  # Last output before failure


class SuccessRecord(BaseModel):
    """Single success event."""
    scenario_id: str
    agent_name: str
    latency_ms: float
    confidence: float    # Agent confidence score [0, 1]
    tool_calls: List[str] = Field(default_factory=list)  # List of tool names called
    retry_count: int = 0
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class ErrorTracker:
    """
    Centralized error tracking for the evaluation harness.
    Aggregates errors per agent, per category, per scenario.
    """

    def __init__(self):
        self.errors: List[ErrorRecord] = []
        self.successes: List[SuccessRecord] = []

        # Aggregation buckets
        self.errors_by_agent: Dict[str, List[ErrorRecord]] = {}
        self.errors_by_category: Dict[str, List[ErrorRecord]] = {}
        self.errors_by_scenario: Dict[str, List[ErrorRecord]] = {}

        self.successes_by_agent: Dict[str, List[SuccessRecord]] = {}

    def record_failure(self, scenario_id: str, agent_name: str, category: str,
                       detail: str, retry_count: int = 0, final_output: str = ""):
        """
        Record an agent failure.

        Args:
            scenario_id: Test case ID (e.g., "CP-S01")
            agent_name: Name of the agent that failed
            category: One of 8 failure categories
            detail: Human-readable error message
            retry_count: Number of retries attempted
            final_output: The output that failed validation (if applicable)
        """
        error = ErrorRecord(
            scenario_id=scenario_id,
            agent_name=agent_name,
            error_category=category,
            error_detail=detail,
            timestamp=datetime.utcnow().isoformat(),
            retry_count=retry_count,
            final_output=final_output
        )

        self.errors.append(error)

        # Aggregate by agent
        if agent_name not in self.errors_by_agent:
            self.errors_by_agent[agent_name] = []
        self.errors_by_agent[agent_name].append(error)

        # Aggregate by category
        if category not in self.errors_by_category:
            self.errors_by_category[category] = []
        self.errors_by_category[category].append(error)

        # Aggregate by scenario
        if scenario_id not in self.errors_by_scenario:
            self.errors_by_scenario[scenario_id] = []
        self.errors_by_scenario[scenario_id].append(error)

    def record_success(self, scenario_id: str, agent_name: str, latency_ms: float,
                       confidence: float, tool_calls: List[str] = None, retry_count: int = 0):
        """
        Record an agent success.

        Args:
            scenario_id: Test case ID
            agent_name: Name of the agent
            latency_ms: Execution time in milliseconds
            confidence: Agent confidence score [0, 1]
            tool_calls: List of tools invoked (optional)
            retry_count: Number of retries before success
        """
        if tool_calls is None:
            tool_calls = []

        success = SuccessRecord(
            scenario_id=scenario_id,
            agent_name=agent_name,
            latency_ms=latency_ms,
            confidence=confidence,
            tool_calls=tool_calls,
            retry_count=retry_count
        )

        self.successes.append(success)

        # Aggregate by agent
        if agent_name not in self.successes_by_agent:
            self.successes_by_agent[agent_name] = []
        self.successes_by_agent[agent_name].append(success)

    def get_agent_error_rate(self, agent_name: str) -> float:
        """
        Get error rate for a single agent.
        Returns: (errors / (errors + successes))
        """
        errors = len(self.errors_by_agent.get(agent_name, []))
        successes = len(self.successes_by_agent.get(agent_name, []))
        total = errors + successes
        return errors / total if total > 0 else 0.0

    def get_category_error_count(self, category: str) -> int:
        """Get count of errors in a specific category."""
        return len(self.errors_by_category.get(category, []))

    def get_top_error_categories(self, top_n: int = 5) -> List[tuple]:
        """
        Return top N error categories by frequency.
        Returns: [(category, count), ...]
        """
        counts = {cat: len(errs) for cat, errs in self.errors_by_category.items()}
        return sorted(counts.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def get_top_error_agents(self, top_n: int = 5) -> List[tuple]:
        """
        Return top N agents by error rate.
        Returns: [(agent_name, error_rate), ...]
        """
        rates = {agent: self.get_agent_error_rate(agent)
                 for agent in self.errors_by_agent.keys()}
        return sorted(rates.items(), key=lambda x: x[1], reverse=True)[:top_n]

    def get_scenario_errors(self, scenario_id: str) -> List[ErrorRecord]:
        """Get all errors for a specific scenario."""
        return self.errors_by_scenario.get(scenario_id, [])

    def get_scenario_success_count(self, scenario_id: str) -> int:
        """Get count of successful agents for a scenario."""
        return len([s for s in self.successes if s.scenario_id == scenario_id])

    def summarize(self) -> Dict:
        """
        Generate a summary report.
        """
        total_errors = len(self.errors)
        total_successes = len(self.successes)
        total = total_errors + total_successes

        return {
            "total_errors": total_errors,
            "total_successes": total_successes,
            "total_agent_calls": total,
            "overall_error_rate": total_errors / total if total > 0 else 0.0,
            "top_error_categories": self.get_top_error_categories(top_n=5),
            "top_error_agents": self.get_top_error_agents(top_n=5),
            "avg_latency_ms": sum(s.latency_ms for s in self.successes) / total_successes if total_successes > 0 else 0.0,
            "avg_confidence": sum(s.confidence for s in self.successes) / total_successes if total_successes > 0 else 0.0
        }

    def to_json(self) -> Dict:
        """
        Export all records as JSON-serializable dict.
        """
        return {
            "error_records": [e.dict() for e in self.errors],
            "success_records": [s.dict() for s in self.successes],
            "summary": self.summarize()
        }

    def to_file(self, filepath: str):
        """Export tracking data to a JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_json(), f, indent=2, default=str)

    def clear(self):
        """Clear all tracking data."""
        self.errors = []
        self.successes = []
        self.errors_by_agent = {}
        self.errors_by_category = {}
        self.errors_by_scenario = {}
        self.successes_by_agent = {}


# Global tracker instance
error_tracker = ErrorTracker()
