"""Analyst-facing scenario catalog: list, CRUD user scenarios, clone, YAML export, LLM fill."""

from __future__ import annotations

import json
import logging
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator

from mirofish_backend.config import get_settings
from mirofish_backend.db.repo import (
    get_user_scenario_row,
    list_user_scenario_rows,
    upsert_user_scenario,
    user_scenario_exists,
)
from mirofish_backend.llm.router import llm_complete
from mirofish_backend.scenarios.loader import load_scenario_for_run
from mirofish_backend.scenarios.registry import get_scenario, list_builtin_scenario_catalog
from mirofish_backend.scenarios.serialize import scenario_config_to_document
from mirofish_backend.scenarios.validate import (
    SCENARIO_ID_RE,
    list_allowed_corpus_paths,
    validate_scenario_document,
)

logger = logging.getLogger("mirofish_backend.api.scenario_catalog")

router = APIRouter(tags=["scenarios"])


class ScenarioUpsertBody(BaseModel):
    document: dict[str, Any]
    display_name: str | None = Field(
        default=None,
        description="Optional label for catalog; defaults to document['name']",
    )


class ScenarioCloneBody(BaseModel):
    template_id: str = Field(..., min_length=2, max_length=64)
    new_scenario_id: str = Field(..., min_length=2, max_length=64)
    display_name: str | None = None

    @field_validator("new_scenario_id")
    @classmethod
    def _slug_new(cls, v: str) -> str:
        if not SCENARIO_ID_RE.match(v):
            raise ValueError("new_scenario_id must match ^[a-z][a-z0-9_]{1,63}$")
        return v


class ScenarioCreateResponse(BaseModel):
    id: str
    warnings: list[str] = Field(default_factory=list)


@router.post("/scenarios/clone", response_model=ScenarioCreateResponse)
async def clone_scenario(body: ScenarioCloneBody) -> ScenarioCreateResponse:
    settings = get_settings()
    allowed = frozenset(list_allowed_corpus_paths())
    try:
        cfg, _src = await load_scenario_for_run(settings.sqlite_path, body.template_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"Unknown template_id: {body.template_id}") from e
    doc = scenario_config_to_document(cfg)
    doc["scenario_id"] = body.new_scenario_id
    if body.display_name:
        doc["name"] = body.display_name
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=allowed)
    if errs:
        raise HTTPException(status_code=422, detail={"errors": errs, "warnings": warns})
    if await user_scenario_exists(settings.sqlite_path, scenario_id=body.new_scenario_id):
        raise HTTPException(status_code=409, detail=f"scenario_id already exists: {body.new_scenario_id}")
    dn = body.display_name or str(doc.get("name") or body.new_scenario_id)
    await upsert_user_scenario(
        settings.sqlite_path,
        scenario_id=body.new_scenario_id,
        display_name=dn,
        document_json=json.dumps(doc, sort_keys=True),
    )
    return ScenarioCreateResponse(id=body.new_scenario_id, warnings=warns)


@router.get("/scenarios/bundled-rag-paths")
async def bundled_rag_paths() -> dict[str, list[str]]:
    return {"paths": list_allowed_corpus_paths()}


@router.get("/scenarios")
async def list_scenario_catalog() -> list[dict[str, Any]]:
    settings = get_settings()
    builtin = list_builtin_scenario_catalog()
    by_id: dict[str, dict[str, Any]] = {b["id"]: dict(b) for b in builtin}
    for row in await list_user_scenario_rows(settings.sqlite_path):
        try:
            doc = json.loads(row["document_json"])
        except json.JSONDecodeError:
            logger.warning("Skipping corrupt user_scenario row %s", row["scenario_id"])
            continue
        sid = row["scenario_id"]
        by_id[sid] = {
            "id": sid,
            "name": row["display_name"],
            "rag_enabled": bool(doc.get("rag_enabled")),
            "source": "user",
        }
    return sorted(by_id.values(), key=lambda x: x["id"])


@router.post("/scenarios", response_model=ScenarioCreateResponse)
async def create_user_scenario(body: ScenarioUpsertBody) -> ScenarioCreateResponse:
    settings = get_settings()
    doc = dict(body.document)
    allowed = frozenset(list_allowed_corpus_paths())
    errs, warns = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=allowed)
    if errs:
        raise HTTPException(status_code=422, detail={"errors": errs, "warnings": warns})
    sid = str(doc["scenario_id"])
    if await user_scenario_exists(settings.sqlite_path, scenario_id=sid):
        raise HTTPException(status_code=409, detail=f"scenario_id already exists: {sid}")
    dn = (body.display_name or "").strip() or str(doc.get("name") or sid)
    await upsert_user_scenario(
        settings.sqlite_path,
        scenario_id=sid,
        display_name=dn,
        document_json=json.dumps(doc, sort_keys=True),
    )
    return ScenarioCreateResponse(id=sid, warnings=warns)


@router.put("/scenarios/{scenario_id}", response_model=ScenarioCreateResponse)
async def update_user_scenario(scenario_id: str, body: ScenarioUpsertBody) -> ScenarioCreateResponse:
    settings = get_settings()
    if not await user_scenario_exists(settings.sqlite_path, scenario_id=scenario_id):
        raise HTTPException(status_code=404, detail="User scenario not found (cannot PUT built-ins)")
    doc = dict(body.document)
    if str(doc.get("scenario_id", "")) != scenario_id:
        raise HTTPException(
            status_code=422,
            detail="document.scenario_id must match URL path for PUT",
        )
    allowed = frozenset(list_allowed_corpus_paths())
    errs, warns = validate_scenario_document(doc, is_update=True, allowed_corpus_paths=allowed)
    if errs:
        raise HTTPException(status_code=422, detail={"errors": errs, "warnings": warns})
    dn = (body.display_name or "").strip() or str(doc.get("name") or scenario_id)
    await upsert_user_scenario(
        settings.sqlite_path,
        scenario_id=scenario_id,
        display_name=dn,
        document_json=json.dumps(doc, sort_keys=True),
    )
    return ScenarioCreateResponse(id=scenario_id, warnings=warns)


@router.get("/scenarios/{scenario_id}/export.yaml", response_class=PlainTextResponse)
async def export_scenario_yaml(scenario_id: str) -> PlainTextResponse:
    settings = get_settings()
    try:
        cfg, _src = await load_scenario_for_run(settings.sqlite_path, scenario_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    doc = scenario_config_to_document(cfg)
    text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return PlainTextResponse(text, media_type="text/yaml; charset=utf-8")


@router.get("/scenarios/{scenario_id}/document")
async def get_scenario_document(scenario_id: str) -> dict[str, Any]:
    """Return raw document for wizard edit (user row or materialized builtin)."""
    settings = get_settings()
    row = await get_user_scenario_row(settings.sqlite_path, scenario_id=scenario_id)
    if row:
        return json.loads(row["document_json"])
    try:
        cfg = get_scenario(scenario_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return scenario_config_to_document(cfg)


class LlmFillRequest(BaseModel):
    """Persona stub used to prompt LLM for structured attribute section suggestions (Iteration 14)."""

    persona_id: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=64)
    name: str = Field(default="", max_length=128)
    style_cues: str = Field(default="", max_length=2000)
    beliefs_summary: str = Field(
        default="",
        max_length=2000,
        description="Optional plain-text summary of the agent's beliefs for extra context.",
    )
    sections: list[str] = Field(
        default_factory=lambda: ["identity", "attitudes", "personal_history"],
        description="Which sections to fill. Valid values: identity, attitudes, personal_history.",
    )


class LlmFillResponse(BaseModel):
    identity: dict[str, Any] = Field(default_factory=dict)
    attitudes: dict[str, Any] = Field(default_factory=dict)
    personal_history: dict[str, Any] = Field(default_factory=dict)
    raw_llm_text: str = ""


_LLM_FILL_SYSTEM = """\
You are a simulation assistant. Given a persona stub, generate realistic structured attribute
sections for a policy simulation agent. Return ONLY valid JSON — no prose, no code fences.

The JSON must be a single object with up to three keys: "identity", "attitudes", "personal_history".
Each value is a flat JSON object (string → string or number). Keep each section to 3-6 key-value pairs.

Relevant domain: public sector / school policy simulation.

Examples of useful keys:
- identity: nationality, gender_identity, language_background, religion_or_values
- attitudes: policy_stance, change_readiness, trust_in_leadership, workload_sensitivity
- personal_history: years_in_role, prior_posting, highest_qualification, notable_experience
"""


@router.post("/scenarios/{scenario_id}/llm-fill", response_model=LlmFillResponse)
async def llm_fill_persona_sections(
    scenario_id: str,
    body: LlmFillRequest,
) -> LlmFillResponse:
    """
    Call the configured LLM to suggest identity/attitudes/personal_history attribute sections
    for a persona stub. Returns suggested dicts; the caller decides whether to save them.

    When server ``llm_provider`` is ``hybrid``, calls use LM Studio (consistent with bulk simulation
    turns). Set provider to ``anthropic`` for frontier-only fill.
    """
    settings = get_settings()
    sections_str = ", ".join(sorted(set(body.sections) & {"identity", "attitudes", "personal_history"}))
    if not sections_str:
        raise HTTPException(status_code=422, detail="sections must contain at least one valid section name")

    user_prompt = (
        f"Scenario: {scenario_id}\n"
        f"Persona: {body.name or body.persona_id}, role={body.role}\n"
        f"Style cues: {body.style_cues or '(none provided)'}\n"
        f"Beliefs summary: {body.beliefs_summary or '(none provided)'}\n"
        f"Sections to generate: {sections_str}\n\n"
        f"Return a JSON object with only the requested sections as top-level keys."
    )

    provider = settings.llm_provider
    try:
        raw = (
            await llm_complete(
                provider=provider if provider in ("lmstudio", "anthropic") else "lmstudio",
                messages=[
                    {"role": "system", "content": _LLM_FILL_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=512,
                lmstudio_base_url=settings.lmstudio_base_url,
                lmstudio_model=settings.lmstudio_model,
                anthropic_api_key=settings.anthropic_api_key,
                anthropic_model=settings.anthropic_model,
            )
        ).text
    except Exception as e:
        logger.warning("llm_fill LLM call failed for %s: %s", body.persona_id, e)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}") from e

    # Parse the JSON response — be lenient about wrapping fences
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first {...} block
        import re
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

    if not isinstance(parsed, dict):
        parsed = {}

    def _safe_dict(key: str) -> dict[str, Any]:
        v = parsed.get(key, {})
        return dict(v) if isinstance(v, dict) else {}

    return LlmFillResponse(
        identity=_safe_dict("identity"),
        attitudes=_safe_dict("attitudes"),
        personal_history=_safe_dict("personal_history"),
        raw_llm_text=raw[:2000],
    )
