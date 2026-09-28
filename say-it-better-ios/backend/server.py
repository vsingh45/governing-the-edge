"""Personal Deep-dive backend for the Say It Better iOS app.

Runs on a machine you control (your Mac) and answers with Claude through the Claude Agent SDK,
authenticated with your own Claude Code login, so calls draw on your Claude subscription rather
than separately billed API usage. Personal use on your own devices only.

    GET  /health                  -> {"ok": true}
    GET  /deepdive?word=cadence   -> deep-dive JSON (same shape as the app's bundled deepdive.json)
    POST /checkSentence           -> {"verdict", "feedback", "improved"}  body: {"word", "sentence"}

Run:  uvicorn server:app --host 0.0.0.0 --port 8765
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

COACH = (
    "You are a vocabulary coach for a lead software engineer who wants to sound clear and "
    "confident when presenting and explaining technical work to teams and stakeholders."
)

SETTINGS = ["Standup", "Design review", "Incident call", "Stakeholder update", "1:1", "Email"]

DEEPDIVE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "word": {"type": "string"},
        "pronunciation": {"type": "string"},
        "partOfSpeech": {"type": "string", "description": "One short label, e.g. noun, verb, adjective"},
        "meaning": {"type": "string"},
        "origin": {"type": "string"},
        "family": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"word": {"type": "string"}, "meaning": {"type": "string"}},
                "required": ["word", "meaning"],
            },
        },
        "collocations": {"type": "array", "items": {"type": "string"}},
        "compare": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"word": {"type": "string"}, "difference": {"type": "string"}},
                "required": ["word", "difference"],
            },
        },
        "mistake": {"type": "string"},
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"setting": {"type": "string"}, "sentence": {"type": "string"}},
                "required": ["setting", "sentence"],
            },
        },
        "tip": {"type": "string"},
    },
    "required": [
        "word", "pronunciation", "partOfSpeech", "meaning", "origin", "family",
        "collocations", "compare", "mistake", "examples", "tip",
    ],
}

FEEDBACK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["good", "almost", "off"]},
        "feedback": {"type": "string"},
        "improved": {"type": "string"},
    },
    "required": ["verdict", "feedback", "improved"],
}

app = FastAPI(title="Say It Better backend")
_cache: dict[str, dict[str, Any]] = {}


async def ask_claude(prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
    """One stateless Agent SDK call with no tools, returning parsed JSON."""
    options = ClaudeAgentOptions(
        tools=[],  # a pure writing task: no file, shell or web access
        max_turns=3,
        setting_sources=[],  # ignore any CLAUDE.md / settings in the directory it runs from
        output_format={"type": "json_schema", "schema": schema},
        model=os.environ.get("SAYITBETTER_MODEL") or None,
    )
    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message

    if result is None or result.is_error:
        detail = (result.errors or result.result) if result else "no result"
        raise HTTPException(status_code=502, detail=f"Claude call failed: {detail}")
    if isinstance(result.structured_output, dict):
        return result.structured_output
    return _parse_json(result.result or "")


def _parse_json(text: str) -> dict[str, Any]:
    """Fallback for a plain-text reply: take the outermost {...} block."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise HTTPException(status_code=502, detail="Claude did not return JSON")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Claude returned malformed JSON: {exc}") from exc


@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/deepdive")
async def deepdive(word: str = Query(..., min_length=1, max_length=60)) -> dict[str, Any]:
    key = word.strip().lower()
    if key in _cache:
        return _cache[key]

    prompt = (
        f'{COACH} Explain the English word or phrase "{word.strip()}" in depth. '
        "Reply with only one JSON object: {word, pronunciation, partOfSpeech, meaning, origin, "
        "family: [{word, meaning}], collocations: [string], compare: [{word, difference}], "
        "mistake, examples: [{setting, sentence}], tip}. "
        f"Give exactly one example for each of these settings, in order: {', '.join(SETTINGS)}. "
        "Use a simple respelled pronunciation with the stressed syllable in capitals "
        "(e.g. rek-uhn-sil-ee-AY-shun) and a one-word partOfSpeech (noun, verb, adjective). Keep the etymology accurate; say so if it is uncertain."
    )
    data = await ask_claude(prompt, DEEPDIVE_SCHEMA)
    _cache[key] = data
    return data


class SentenceIn(BaseModel):
    word: str = Field(min_length=1, max_length=60)
    sentence: str = Field(min_length=1, max_length=600)


@app.post("/checkSentence")
async def check_sentence(body: SentenceIn) -> dict[str, Any]:
    prompt = (
        f'{COACH} They wrote this sentence to practise the word "{body.word}":\n\n'
        f"{body.sentence}\n\n"
        "Judge whether the word is used correctly and naturally for a workplace setting. "
        'Reply with only one JSON object: {verdict: "good" | "almost" | "off", '
        "feedback: one or two encouraging, specific sentences, "
        "improved: a polished version of their sentence that keeps their meaning}."
    )
    return await ask_claude(prompt, FEEDBACK_SCHEMA)
