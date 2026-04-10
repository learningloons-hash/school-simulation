"""LLM-assisted scenario authoring (Iteration 16)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mirofish_backend.config import get_settings
from mirofish_backend.llm.router import llm_complete
from mirofish_backend.scenarios.validate import list_allowed_corpus_paths, validate_scenario_document

logger = logging.getLogger("mirofish_backend.api.scenarios_generate")

router = APIRouter(tags=["scenarios"])


class GenerateFromBriefRequest(BaseModel):
    brief: str = Field(..., min_length=20, max_length=16000)
    max_tokens: int | None = Field(default=None, ge=512, le=8192)


class GenerateFromBriefResponse(BaseModel):
    document: dict[str, Any]
    warnings: list[str] = Field(default_factory=list)


# This template is passed to str.format(allowed_paths=...). Literal `{`/`}` in the instructions must be
# doubled as `{{`/`}}` so they are not treated as format placeholders (not an f-string).
_GENERATE_SYSTEM_TEMPLATE = """You are a simulation scenario author for MiroFish — a domain-agnostic policy tabletop engine.
The user describes a scenario in plain language. You must output ONE JSON object — valid JSON only, no markdown fences, no commentary.

Required top-level keys:
- scenario_id: string matching ^[a-z][a-z0-9_]{{1,63}}$ (lowercase slug, unique suggestion)
- name: human-readable title
- policy_events: object mapping round number strings to policy text, e.g. {{"1": "...", "2": "..."}} — at least one round
- personas: non-empty array. Each persona MUST have:
  persona_id, role (string — any organisational role relevant to the scenario domain), name,
  role_level (integer — 1 = highest authority in this scenario, larger integers = lower authority),
  style_cues (string), beliefs (object with string keys — numeric beliefs 0-1 are fine)

Optional:
- groups: array of {{group_id, name, description}}
- identity, attitudes, personal_history on each persona: flat objects (string values preferred)
- initial_state on each persona: object with optional support_level, resistance_level, workload_stress (0-1 floats), belief_posture (string)
- rag_enabled: boolean; if true, rag_corpus_paths must be a non-empty array of paths from the allowed list below only

Allowed bundled RAG paths (use only these if enabling RAG):
{allowed_paths}

If the brief is vague, still produce a minimal coherent 3-persona policy scenario matching the brief's domain.
"""


def _parse_llm_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}
    return parsed if isinstance(parsed, dict) else {}


@router.post("/scenarios/generate-from-brief", response_model=GenerateFromBriefResponse)
async def generate_scenario_from_brief(body: GenerateFromBriefRequest) -> GenerateFromBriefResponse:
    """
    When server ``llm_provider`` is ``hybrid``, calls use LM Studio (consistent with bulk simulation
    turns). Set provider to ``anthropic`` in settings for frontier-only scenario drafting.
    """
    settings = get_settings()
    allowed_paths = list_allowed_corpus_paths()
    paths_block = "\n".join(f"- {p}" for p in allowed_paths) if allowed_paths else "(none — leave rag_enabled false or omit RAG)"
    system_prompt = _GENERATE_SYSTEM_TEMPLATE.format(allowed_paths=paths_block)

    user_prompt = f"Scenario brief:\n{body.brief.strip()}\n"

    max_tok = body.max_tokens if body.max_tokens is not None else 4096
    provider = settings.llm_provider
    try:
        raw = (
            await llm_complete(
                provider=provider if provider in ("lmstudio", "anthropic") else "lmstudio",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.55,
                max_tokens=max_tok,
                lmstudio_base_url=settings.lmstudio_base_url,
                lmstudio_model=settings.lmstudio_model,
                anthropic_api_key=settings.anthropic_api_key,
                anthropic_model=settings.anthropic_model,
            )
        ).text
    except Exception as e:
        logger.warning("generate-from-brief LLM failed: %s", e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e

    doc = _parse_llm_json_object(raw)
    if not doc:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": ["LLM returned no parseable JSON object"],
                "warnings": [],
                "raw_llm_text": raw[:4000],
            },
        )

    allowed = frozenset(allowed_paths)
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=allowed)
    if errs:
        raise HTTPException(
            status_code=422,
            detail={
                "errors": errs,
                "warnings": warns,
                "raw_llm_text": raw[:4000],
            },
        )

    return GenerateFromBriefResponse(document=doc, warnings=warns)
