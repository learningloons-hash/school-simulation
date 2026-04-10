"""Validate analyst-authored scenario documents; collect warnings for UI/API."""

from __future__ import annotations

import re
from typing import Any

from mirofish_backend.scenarios.registry import is_builtin_scenario_id, scenario_from_mapping

SCENARIO_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")


def list_allowed_corpus_paths() -> list[str]:
    """Relative paths under scenarios/data/ for RAG (no path traversal)."""
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent / "data"
    if not data_dir.is_dir():
        return []
    out: list[str] = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".txt", ".md"):
            rel = p.relative_to(data_dir).as_posix()
            if ".." not in rel and not rel.startswith("/"):
                out.append(rel)
    return out


def validate_scenario_document(
    doc: dict[str, Any],
    *,
    is_update: bool,
    allowed_corpus_paths: frozenset[str],
) -> tuple[list[str], list[str]]:
    """
    Returns (errors, warnings). Errors block persistence; warnings are returned to client.

    When ``is_update`` is True, ``scenario_id`` in body must match URL id (checked by caller).
    """
    errors: list[str] = []
    warnings: list[str] = []

    sid = doc.get("scenario_id")
    if not isinstance(sid, str) or not SCENARIO_ID_RE.match(sid):
        errors.append(
            "scenario_id must match ^[a-z][a-z0-9_]{1,63}$ (lowercase start, 2–64 chars)",
        )
    name = doc.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("name must be a non-empty string")

    pe = doc.get("policy_events")
    if not isinstance(pe, dict) or not pe:
        errors.append("policy_events must be a non-empty object (round number -> text)")
    else:
        try:
            for k in pe:
                int(k)
        except (TypeError, ValueError):
            errors.append("policy_events keys must be round numbers")

    personas = doc.get("personas")
    if not isinstance(personas, list) or len(personas) < 1:
        errors.append("personas must be a non-empty array")
    else:
        for i, p in enumerate(personas):
            if not isinstance(p, dict):
                errors.append(f"personas[{i}] must be an object")
                continue
            for req in ("persona_id", "role", "name", "role_level", "style_cues"):
                if req not in p:
                    errors.append(f"personas[{i}] missing required field {req!r}")
            if "role_level" in p and isinstance(p["role_level"], int):
                if p["role_level"] < 1:
                    warnings.append(
                        f"personas[{i}].role_level should be a positive integer (1 = highest authority)"
                    )
            if "initial_state" in p and p["initial_state"] is not None and not isinstance(p["initial_state"], dict):
                errors.append(f"personas[{i}].initial_state must be an object when present")
            if "initial_state" in p and isinstance(p.get("initial_state"), dict):
                for dim in ("support_level", "resistance_level", "workload_stress"):
                    v = p["initial_state"].get(dim)
                    if v is not None:
                        try:
                            fv = float(v)
                            if not (0.0 <= fv <= 1.0):
                                warnings.append(
                                    f"personas[{i}].initial_state.{dim} should be between 0.0 and 1.0 (got {fv})"
                                )
                        except (TypeError, ValueError):
                            errors.append(
                                f"personas[{i}].initial_state.{dim} must be a number (got {v!r})"
                            )
            for sec in ("identity", "attitudes", "personal_history"):
                if sec in p and p[sec] is not None and not isinstance(p[sec], dict):
                    errors.append(f"personas[{i}].{sec} must be an object when present")
            if "implementation_posture" in p and p["implementation_posture"] is not None:
                if not isinstance(p["implementation_posture"], str):
                    errors.append(
                        f"personas[{i}].implementation_posture must be a string when present (got {type(p['implementation_posture']).__name__})"
                    )

    groups = doc.get("groups")
    known_gids: set[str] = set()
    if groups is not None:
        if not isinstance(groups, list):
            errors.append("groups must be an array when present")
        else:
            for i, g in enumerate(groups):
                if not isinstance(g, dict) or "group_id" not in g or "name" not in g:
                    errors.append(f"groups[{i}] needs group_id and name")
                elif isinstance(g.get("group_id"), str):
                    known_gids.add(g["group_id"])

    if isinstance(personas, list) and known_gids:
        for i, p in enumerate(personas):
            if not isinstance(p, dict):
                continue
            glist = p.get("groups")
            if isinstance(glist, list):
                for gid in glist:
                    if str(gid) not in known_gids:
                        warnings.append(
                            f"personas[{i}] references unknown group_id {gid!r} (not in scenario.groups)",
                        )

    if doc.get("rag_enabled"):
        paths = doc.get("rag_corpus_paths")
        if not isinstance(paths, list) or not paths:
            warnings.append("rag_enabled is true but rag_corpus_paths is empty — RAG will have no files")
        elif isinstance(paths, list):
            for p in paths:
                ps = str(p)
                if ps not in allowed_corpus_paths:
                    errors.append(
                        f"rag_corpus_paths entry {ps!r} is not an allowed bundled path under scenarios/data",
                    )

    if errors:
        return errors, warnings

    try:
        scenario_from_mapping(doc)
    except (KeyError, TypeError, ValueError) as e:
        errors.append(f"scenario structure invalid: {e}")
        return errors, warnings

    if isinstance(sid, str) and is_builtin_scenario_id(sid):
        warnings.append(
            f"scenario_id {sid!r} matches a built-in package scenario; your saved row overrides it for this server only",
        )

    return errors, warnings
