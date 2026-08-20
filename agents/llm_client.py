"""
Provider-agnostic LLM client via LiteLLM.
Every agent calls llm_call() — the model string is the only thing that changes.
Supports: Anthropic Claude, OpenAI GPT-4o, Ollama/Gemma (local)
"""
from __future__ import annotations
import json
import re
from typing import Type, TypeVar
from pydantic import BaseModel
import litellm

litellm.set_verbose = False

T = TypeVar("T", bound=BaseModel)


def _extract_json(raw: str) -> dict:
    """
    Parse a JSON object out of a raw LLM response, robust to two local-model
    quirks observed with Gemma 2:
      1. The full JSON *schema* echoed back instead of (or before) the data.
      2. The schema echoed first, followed by the real answer in a separate
         ```json fenced block — i.e. two concatenated JSON objects.
    Prefers the last fenced ```json block if present, else the last valid
    top-level JSON object found in the text.
    """
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
    if fenced:
        return json.loads(fenced[-1])

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    text = raw.strip()
    objects = []
    idx = 0
    while idx < len(text):
        chunk = text[idx:].lstrip()
        if not chunk:
            break
        skip = len(text[idx:]) - len(chunk)
        try:
            obj, end = decoder.raw_decode(chunk)
            objects.append(obj)
            idx += skip + end
        except json.JSONDecodeError:
            break

    if objects:
        return objects[-1]

    raise ValueError(f"Could not extract JSON from LLM response: {raw[:200]!r}")


def llm_call(
    model: str,
    system_prompt: str,
    user_prompt: str,
    response_schema: Type[T],
    temperature: float = 0.0,
    max_tokens: int = 4000,
    max_retries: int = 3,
) -> T:
    """
    Make a provider-agnostic LLM call and return a validated Pydantic object.

    Args:
        model: LiteLLM model string, e.g. 'claude-sonnet-4-6' or 'ollama/gemma2'
        system_prompt: System instruction for the agent
        user_prompt: The actual input to process
        response_schema: Pydantic model class to validate and parse the response
        temperature: Sampling temperature (low = more deterministic)
        max_tokens: Max output tokens
        max_retries: Number of retry attempts on parse failure

    Returns:
        Validated instance of response_schema

    Raises:
        ValueError: If response cannot be parsed after max_retries
    """
    schema_str = json.dumps(response_schema.model_json_schema(), indent=2)

    full_system = (
        f"{system_prompt}\n\n"
        f"You MUST respond with valid JSON matching this exact schema:\n"
        f"{schema_str}\n\n"
        f"Return ONLY the JSON object. No markdown, no explanation, no preamble."
    )

    messages = [
        {"role": "system", "content": full_system},
        {"role": "user", "content": user_prompt},
    ]

    last_error = None
    for attempt in range(max_retries):
        try:
            response = litellm.completion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            raw = response.choices[0].message.content.strip()

            parsed = _extract_json(raw)
            # Gemma sometimes returns the full JSON Schema structure {"title":..,"properties":{..}}
            # instead of the flat data object — unwrap the "properties" level.
            # Safe because none of our Pydantic schemas have a field named "properties".
            if "properties" in parsed and isinstance(parsed["properties"], dict):
                parsed = parsed["properties"]
            return response_schema.model_validate(parsed)

        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                messages.append({"role": "assistant", "content": raw if 'raw' in dir() else ""})
                messages.append({
                    "role": "user",
                    "content": f"Your response was invalid. Error: {str(e)}. Please return valid JSON only."
                })

    raise ValueError(f"LLM call failed after {max_retries} retries. Last error: {last_error}")


def llm_call_raw(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
    max_tokens: int = 4000,
) -> str:
    """Simple raw text LLM call — returns string. Used for prompts that don't need schema."""
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()
