"""
Parse round-end Likert self-report blocks from LLM responses.

Models append ``<likert>{...json...}</likert>`` with indicator -> anchor-label choices.
Provenance mirrors ``state_parse.py`` (model_parsed / repaired / keyword_fallback).
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

LikertUpdateSource = Literal["model_parsed", "repaired", "keyword_fallback"]

# Six-point ordinal → 0–1 mapping (senna-iter-40; recorded in config_snapshot).
LIKERT_ORDINAL_FLOAT_MAP: tuple[float, ...] = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)

_LIKERT_BLOCK = re.compile(r"<likert>\s*([\s\S]*?)\s*</likert>", re.IGNORECASE)


def mapped_float_from_ordinal(ordinal: int) -> float:
    if ordinal < 0 or ordinal >= len(LIKERT_ORDINAL_FLOAT_MAP):
        raise ValueError(f"ordinal must be 0..{len(LIKERT_ORDINAL_FLOAT_MAP) - 1}, got {ordinal}")
    return LIKERT_ORDINAL_FLOAT_MAP[ordinal]


def float_to_nearest_ordinal(value: float) -> int:
    return min(range(len(LIKERT_ORDINAL_FLOAT_MAP)), key=lambda i: abs(value - LIKERT_ORDINAL_FLOAT_MAP[i]))


def extract_all_likert_blocks(raw_response: str) -> list[str]:
    return [m.group(1).strip() for m in _LIKERT_BLOCK.finditer(raw_response or "")]


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


def _normalize_label(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


def _match_label_to_ordinal(label: str, anchors: tuple[str, ...]) -> int | None:
    norm = _normalize_label(label)
    if not norm:
        return None
    for i, anchor in enumerate(anchors):
        if _normalize_label(anchor) == norm:
            return i
    matches = [
        i
        for i, anchor in enumerate(anchors)
        if norm in _normalize_label(anchor) or _normalize_label(anchor) in norm
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def parse_likert_payload(
    payload: dict[str, Any],
    *,
    indicators: tuple[str, ...],
    anchor_labels: dict[str, tuple[str, ...]],
) -> tuple[dict[str, tuple[str, int, float]], bool, bool]:
    """Parse payload; returns (parsed, label_repaired, numeric_repaired)."""
    out: dict[str, tuple[str, int, float]] = {}
    label_repaired = False
    numeric_repaired = False
    for ind in indicators:
        anchors = anchor_labels.get(ind)
        if not anchors or len(anchors) != 6:
            continue
        raw_val = payload.get(ind)
        if raw_val is None:
            continue
        if isinstance(raw_val, int) and 0 <= raw_val <= 5:
            ordinal = raw_val
            anchor_text = anchors[ordinal]
            numeric_repaired = True
        elif isinstance(raw_val, str):
            matched = _match_label_to_ordinal(raw_val, anchors)
            if matched is None:
                continue
            ordinal = matched
            anchor_text = anchors[ordinal]
            if _normalize_label(raw_val) != _normalize_label(anchor_text):
                label_repaired = True
        else:
            continue
        out[ind] = (anchor_text, ordinal, mapped_float_from_ordinal(ordinal))
    return out, label_repaired, numeric_repaired


def keyword_fallback_likert(
    *,
    indicators: tuple[str, ...],
    anchor_labels: dict[str, tuple[str, ...]],
    float_values: dict[str, float | None],
) -> dict[str, tuple[str, int, float]]:
    out: dict[str, tuple[str, int, float]] = {}
    for ind in indicators:
        anchors = anchor_labels.get(ind)
        fv = float_values.get(ind)
        if not anchors or len(anchors) != 6:
            continue
        if fv is not None:
            ordinal = float_to_nearest_ordinal(float(fv))
        else:
            ordinal = 2
        out[ind] = (anchors[ordinal], ordinal, mapped_float_from_ordinal(ordinal))
    return out


def resolve_likert_per_indicator(
    raw_response: str,
    *,
    indicators: tuple[str, ...],
    anchor_labels: dict[str, tuple[str, ...]],
    float_values: dict[str, float | None],
) -> dict[str, tuple[str, int, float, LikertUpdateSource]]:
    """Return exactly one parsed row per configured indicator."""
    blocks = extract_all_likert_blocks(raw_response)
    parsed_partial: dict[str, tuple[str, int, float]] = {}
    any_json_repaired = False
    any_label_repaired = False
    any_numeric_repaired = False
    multiple_blocks = len(blocks) > 1

    for block in blocks:
        data, json_repaired = _try_load_json_object(block)
        if json_repaired:
            any_json_repaired = True
        if data is None:
            continue
        parsed, label_repaired, numeric_repaired = parse_likert_payload(
            data,
            indicators=indicators,
            anchor_labels=anchor_labels,
        )
        if label_repaired:
            any_label_repaired = True
        if numeric_repaired:
            any_numeric_repaired = True
        parsed_partial.update(parsed)

    needs_repair = multiple_blocks or any_json_repaired or any_label_repaired or any_numeric_repaired

    out: dict[str, tuple[str, int, float, LikertUpdateSource]] = {}
    for ind in indicators:
        anchors = anchor_labels.get(ind)
        if not anchors or len(anchors) != 6:
            continue
        if ind in parsed_partial:
            anchor_label, ordinal, mapped_float = parsed_partial[ind]
            src: LikertUpdateSource = "repaired" if needs_repair else "model_parsed"
            out[ind] = (anchor_label, ordinal, mapped_float, src)
        else:
            fb = keyword_fallback_likert(
                indicators=(ind,),
                anchor_labels=anchor_labels,
                float_values=float_values,
            )
            anchor_label, ordinal, mapped_float = fb[ind]
            out[ind] = (anchor_label, ordinal, mapped_float, "keyword_fallback")
    return out


def resolve_likert_from_response(
    raw_response: str,
    *,
    indicators: tuple[str, ...],
    anchor_labels: dict[str, tuple[str, ...]],
    float_values: dict[str, float | None],
) -> tuple[dict[str, tuple[str, int, float]], LikertUpdateSource]:
    """Legacy aggregate provenance; prefer ``resolve_likert_per_indicator``."""
    per_ind = resolve_likert_per_indicator(
        raw_response,
        indicators=indicators,
        anchor_labels=anchor_labels,
        float_values=float_values,
    )
    parsed = {k: (v[0], v[1], v[2]) for k, v in per_ind.items()}
    sources = {v[3] for v in per_ind.values()}
    if sources == {"model_parsed"}:
        return parsed, "model_parsed"
    if "keyword_fallback" in sources and sources == {"keyword_fallback"}:
        return parsed, "keyword_fallback"
    return parsed, "repaired"
