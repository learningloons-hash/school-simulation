"""
Parse memory-importance scores from dedicated scorer LLM responses.

Models append ``<importance_score>{...json...}</importance_score>`` with integer score 1–10.
Provenance mirrors ``judge_score_parse.py`` (model_parsed / repaired / fallback).
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

ImportanceSource = Literal["model_parsed", "repaired", "fallback"]

VALID_SCORES = frozenset(range(1, 11))
FALLBACK_SCORE = 5

_IMPORTANCE_BLOCK = re.compile(
    r"<importance_score>\s*([\s\S]*?)\s*</importance_score>",
    re.IGNORECASE,
)
_SCORE_JSON = re.compile(r'"score"\s*:\s*([1-9]|10)\b')
_SCORE_BARE = re.compile(r"\bscore\s*[=:]\s*([1-9]|10)\b", re.IGNORECASE)


def extract_importance_blocks(raw_response: str) -> list[str]:
    return [m.group(1).strip() for m in _IMPORTANCE_BLOCK.finditer(raw_response or "")]


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


def _coerce_score(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value in VALID_SCORES:
        return value
    if isinstance(value, str) and value.strip().isdigit():
        n = int(value.strip())
        if n in VALID_SCORES:
            return n
    return None


def parse_importance_payload(payload: dict[str, Any]) -> int | None:
    return _coerce_score(payload.get("score"))


def keyword_fallback_importance(raw_response: str) -> int | None:
    text = raw_response or ""
    for pattern in (_SCORE_JSON, _SCORE_BARE):
        m = pattern.search(text)
        if m:
            return int(m.group(1))
    return None


def resolve_importance_score(raw_response: str) -> tuple[int, ImportanceSource]:
    """
    Resolve a single 1–10 importance score. Never raises; uses ``FALLBACK_SCORE`` when needed.
    """
    blocks = extract_importance_blocks(raw_response)
    json_repaired = False
    parsed_score: int | None = None

    for block in blocks:
        data, repaired = _try_load_json_object(block)
        if repaired:
            json_repaired = True
        if data is None:
            continue
        score = parse_importance_payload(data)
        if score is not None:
            parsed_score = score
            break

    if parsed_score is not None:
        src: ImportanceSource = "repaired" if json_repaired or len(blocks) > 1 else "model_parsed"
        return parsed_score, src

    fb = keyword_fallback_importance(raw_response)
    if fb is not None:
        return fb, "fallback"
    return FALLBACK_SCORE, "fallback"


def resolve_batch_importance_scores(
    raw_response: str,
    *,
    expected_turn_ids: list[str],
) -> dict[str, tuple[int, ImportanceSource]]:
    """
    Parse batch scorer output mapping turn ids to scores.

    Accepts ``{"turn_scores": [{"turn_id": "...", "score": N}, ...]}`` or
    ``{"scores": {"turn_id": N, ...}}``. Missing ids receive fallback scores.
    """
    out: dict[str, tuple[int, ImportanceSource]] = {}
    blocks = extract_importance_blocks(raw_response)
    json_repaired = False
    payload_scores: dict[str, int] = {}

    for block in blocks:
        data, repaired = _try_load_json_object(block)
        if repaired:
            json_repaired = True
        if data is None:
            continue
        rows = data.get("turn_scores")
        if isinstance(rows, list):
            for row in rows:
                if not isinstance(row, dict):
                    continue
                tid = str(row.get("turn_id") or "")
                score = _coerce_score(row.get("score"))
                if tid and score is not None:
                    payload_scores[tid] = score
        scores_map = data.get("scores")
        if isinstance(scores_map, dict):
            for tid, val in scores_map.items():
                score = _coerce_score(val)
                if score is not None:
                    payload_scores[str(tid)] = score

    base_src: ImportanceSource = "repaired" if json_repaired or len(blocks) > 1 else "model_parsed"
    if not payload_scores and blocks:
        base_src = "fallback"

    for tid in expected_turn_ids:
        if tid in payload_scores:
            out[tid] = (payload_scores[tid], base_src)
        else:
            out[tid] = (FALLBACK_SCORE, "fallback")

    if not blocks:
        for tid in expected_turn_ids:
            fb = keyword_fallback_importance(raw_response)
            out[tid] = (fb if fb is not None else FALLBACK_SCORE, "fallback")

    return out


def count_importance_sources(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        src = str(row.get("importance_source") or "unknown")
        counts[src] = counts.get(src, 0) + 1
    return counts
