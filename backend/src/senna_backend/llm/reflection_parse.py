"""
Parse reflection synthesis LLM responses (senna-iter-51).

Provenance: model_parsed / repaired / fallback — mirrors importance_parse.
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

ReflectionSource = Literal["model_parsed", "repaired", "fallback"]

FALLBACK_REFLECTION_TEXT = "Unable to synthesise a reflection from recent observations."

_REFLECTION_BLOCK = re.compile(
    r"<reflection>\s*([\s\S]*?)\s*</reflection>",
    re.IGNORECASE,
)


def extract_reflection_blocks(raw_response: str) -> list[str]:
    return [m.group(1).strip() for m in _REFLECTION_BLOCK.finditer(raw_response or "")]


def _strip_code_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = [ln for ln in s.splitlines() if not ln.strip().startswith("```")]
    return "\n".join(lines).strip()


def _try_load_json_object(text: str) -> tuple[dict[str, Any] | None, bool]:
    s = _strip_code_fence(text)
    try:
        data = json.loads(s)
        if isinstance(data, dict):
            return data, False
    except json.JSONDecodeError:
        pass
    fixed = re.sub(r",\s*}", "}", s)
    fixed = re.sub(r",\s*]", "]", fixed)
    if fixed != s:
        try:
            data = json.loads(fixed)
            if isinstance(data, dict):
                return data, True
        except json.JSONDecodeError:
            pass
    return None, False


def _coerce_source_turn_ids(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        tid = str(item or "").strip()
        if tid:
            out.append(tid)
    return out


def resolve_reflection(
    raw_response: str,
    *,
    fallback_source_turn_ids: list[str],
) -> tuple[str, list[str], ReflectionSource]:
    """Never raises. Uses fallback text when parse fails."""
    blocks = extract_reflection_blocks(raw_response)
    json_repaired = False
    for block in blocks:
        data, repaired = _try_load_json_object(block)
        if repaired:
            json_repaired = True
        if data is None:
            continue
        text = str(data.get("reflection_text") or data.get("text") or "").strip()
        sources = _coerce_source_turn_ids(data.get("source_turn_ids"))
        if not sources and fallback_source_turn_ids:
            sources = list(fallback_source_turn_ids)
        if text:
            src: ReflectionSource = "repaired" if json_repaired or len(blocks) > 1 else "model_parsed"
            return text, sources, src

    stripped = (raw_response or "").strip()
    if stripped and not blocks:
        return stripped[:2000], list(fallback_source_turn_ids), "fallback"
    return FALLBACK_REFLECTION_TEXT, list(fallback_source_turn_ids), "fallback"
