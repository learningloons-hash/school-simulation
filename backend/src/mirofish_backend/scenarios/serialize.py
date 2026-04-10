"""ScenarioConfig ↔ YAML-shaped dict for export and clone."""

from __future__ import annotations

from typing import Any

from mirofish_backend.scenarios.registry import ScenarioConfig


def scenario_config_to_document(cfg: ScenarioConfig) -> dict[str, Any]:
    pe = {str(k): v for k, v in sorted(cfg.policy_events.items())}
    personas: list[dict[str, Any]] = []
    for p in cfg.personas:
        d: dict[str, Any] = {
            "persona_id": p.persona_id,
            "role": p.role,
            "name": p.name,
            "role_level": p.role_level,
            "style_cues": p.style_cues,
            "beliefs": dict(p.beliefs),
        }
        if p.psychological_profile:
            d["psychological_profile"] = dict(p.psychological_profile)
        if p.implementation_profile:
            d["implementation_profile"] = dict(p.implementation_profile)
        if p.groups:
            d["groups"] = list(p.groups)
        if p.identity:
            d["identity"] = dict(p.identity)
        if p.attitudes:
            d["attitudes"] = dict(p.attitudes)
        if p.personal_history:
            d["personal_history"] = dict(p.personal_history)
        personas.append(d)
    out: dict[str, Any] = {
        "scenario_id": cfg.scenario_id,
        "name": cfg.name,
        "policy_events": pe,
        "personas": personas,
    }
    if cfg.groups:
        out["groups"] = [
            {"group_id": g.group_id, "name": g.name, "description": g.description} for g in cfg.groups
        ]
    if cfg.rag_enabled:
        out["rag_enabled"] = True
    if cfg.rag_corpus_paths:
        out["rag_corpus_paths"] = list(cfg.rag_corpus_paths)
    if cfg.interaction_overlay and cfg.interaction_overlay != "none":
        out["interaction_overlay"] = cfg.interaction_overlay
    return out
