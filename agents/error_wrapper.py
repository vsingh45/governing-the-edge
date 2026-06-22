"""
Error categorization and wrapping for agent LLM calls.
Translates exceptions into the 8 failure categories for error tracking.
"""
import json
import time
from typing import Callable, Any, Optional, List
from functools import wraps
from evaluation.error_tracking import error_tracker


def categorize_error(error: Exception, last_error_msg: str = "") -> tuple:
    """
    Categorize an exception into one of 8 failure categories.

    Returns: (category_string, detailed_message)
    """
    error_str = str(error).lower()
    error_msg = last_error_msg.lower()

    # Check for specific patterns in order of specificity
    if "timeout" in error_str or "timeout" in error_msg:
        return ("TIMEOUT", f"LLM call exceeded timeout: {error}")

    if "authentication" in error_str or "api key" in error_str or "401" in error_str:
        return ("LLM_API_ERROR", f"Authentication/API error: {error}")

    if "rate limit" in error_str or "quota" in error_str or "429" in error_str:
        return ("LLM_API_ERROR", f"Rate limit/quota error: {error}")

    if "json" in error_str or "parsing" in error_msg:
        return ("LLM_PARSE_ERROR", f"JSON parsing failed: {error}")

    if "validation" in error_str or "validate" in error_msg:
        return ("SCHEMA_VALIDATION", f"Pydantic schema validation failed: {error}")

    if "tool" in error_str or "function call" in error_str:
        return ("TOOL_FAILURE", f"Tool invocation failed: {error}")

    if "inconsistent" in error_str or "contradict" in error_msg:
        return ("INCONSISTENCY", f"Output inconsistency detected: {error}")

    if "null" in error_str or "required" in error_msg:
        return ("NULL_REQUIRED", f"Required field is null/missing: {error}")

    if "governance" in error_str or "rule" in error_str or "compliance" in error_str:
        return ("GOVERNANCE_CONFLICT", f"Governance rule violation: {error}")

    # Fallback
    return ("LLM_PARSE_ERROR", f"Unclassified error (defaulting to PARSE_ERROR): {error}")


def wrap_agent_with_tracking(
    agent_name: str,
    tool_names: Optional[List[str]] = None
) -> Callable:
    """
    Decorator to wrap an agent function with error tracking.

    Args:
        agent_name: Name of the agent (e.g., "document_parser", "risk_aggregator")
        tool_names: List of tools this agent may invoke (for documentation)

    Usage:
        @wrap_agent_with_tracking("document_parser", tool_names=["ocr_document"])
        def document_parser_node(state: UnderwritingState) -> UnderwritingState:
            ...
    """
    if tool_names is None:
        tool_names = []

    def decorator(agent_func: Callable) -> Callable:
        @wraps(agent_func)
        def wrapper(state, *args, **kwargs):
            scenario_id = state.scenario_id
            start_time = time.time()
            retry_count = 0

            try:
                # Execute the agent
                result = agent_func(state, *args, **kwargs)

                # Record success
                latency_ms = (time.time() - start_time) * 1000
                confidence = getattr(result, 'agent_explanations', {}).get(agent_name, {}).get('confidence', 0.8)

                # [TOOL_GROUNDING_PATCH]
                # Log the tools that ACTUALLY ran with their real payloads,
                # not the static documentation list.
                _tr = getattr(result, '_tool_results', {}) or {}
                _ran = _tr.get(agent_name, {})
                _real_tool_calls = list(_ran.keys()) if _ran else []
                error_tracker.record_success(
                    scenario_id=scenario_id,
                    agent_name=agent_name,
                    latency_ms=latency_ms,
                    confidence=confidence,
                    tool_calls=_real_tool_calls,
                    retry_count=retry_count
                )

                return result

            except Exception as e:
                # Categorize and record failure
                latency_ms = (time.time() - start_time) * 1000
                category, detail = categorize_error(e, str(e))

                error_tracker.record_failure(
                    scenario_id=scenario_id,
                    agent_name=agent_name,
                    category=category,
                    detail=detail,
                    retry_count=retry_count,
                    final_output=str(e)[:500]  # Truncate long errors
                )

                # Re-raise so the workflow can handle it
                raise

        return wrapper
    return decorator


def extract_tool_calls_from_state(state) -> List[str]:
    """
    Extract which tools were called in the last agent execution.
    This is a placeholder — actual implementation depends on your audit trail.
    """
    # Check audit trail for tool invocations (if implemented)
    tools_called = []
    if hasattr(state, 'audit_trail') and state.audit_trail:
        last_entry = state.audit_trail[-1]
        # Your audit entries should record tool calls here
        if hasattr(last_entry, 'tool_calls'):
            tools_called = last_entry.tool_calls
    return tools_called
