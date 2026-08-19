"""
Parse rubric judge scores from LLM responses.

Models append ``<judge_score>{...json...}</judge_score>`` with integer score 0–2.
Provenance mirrors ``likert_parse.py`` (model_parsed / repaired / keyword_fallback).
Unparseable output returns ``score=None`` with source ``unparseable`` (not a silent zero).
"""

from __future__ import annotations

import json
import re
from typing import Any, Literal

JudgeScoreSource = Literal["model_parsed", "repaired", "keyword_fallback", "unparseable"]

VALID_SCORES = frozenset({0, 1, 2})
SCORE_LABELS: dict[int, str] = {0: "inadequate", 1: "partial", 2: "adequate"}

_JUDGE_BLOCK = re.compile(r"<judge_score>\s*([\s\S]*?)\s*</judge_score>", re.IGNORECASE)
_SCORE_JSON = re.compile(r'"score"\s*:\s*([012])')
_SCORE_BARE = re.compile(r"\bscore\s*[=:]\s*([012])\b", re.IGNORECASE)


def score_label(score: int) -> str:
    if score not in SCORE_LABELS:
        raise ValueError(f"score must be 0..2, got {score}")
    return SCORE_LABELS[score]


def extract_judge_score_blocks(raw_response: str) -> list[str]:
    return [m.group(1).strip() for m in _JUDGE_BLOCK.finditer(raw_response or "")]


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


def parse_judge_payload(payload: dict[str, Any]) -> tuple[int | None, str | None]:
    score = _coerce_score(payload.get("score"))
    rationale = payload.get("rationale")
    if rationale is not None and not isinstance(rationale, str):
        rationale = str(rationale)
    return score, rationale


def keyword_fallback_judge(raw_response: str) -> tuple[int | None, str | None]:
    """Infer score from loose patterns; return ``(None, None)`` when nothing matches."""
    text = raw_response or ""
    for pattern in (_SCORE_JSON, _SCORE_BARE):
        m = pattern.search(text)
        if m:
            return int(m.group(1)), None
    lower = text.lower()
    if "inadequate" in lower or "clear fail" in lower or "does not demonstrate" in lower:
        return 0, None
    if "adequate" in lower or "clear pass" in lower or "fully demonstrates" in lower:
        return 2, None
    if "partial" in lower or "incomplete" in lower:
        return 1, None
    return None, None


def resolve_judge_score(raw_response: str) -> tuple[int | None, JudgeScoreSource, str | None]:
    """
    Resolve a single 0–2 score from judge model output.

    Never raises. Returns ``score=None`` with ``unparseable`` when no score can be
    inferred — callers must not treat that as a substantive zero.
    """
    blocks = extract_judge_score_blocks(raw_response)
    json_repaired = False
    parsed_score: int | None = None
    parsed_rationale: str | None = None

    for block in blocks:
        data, repaired = _try_load_json_object(block)
        if repaired:
            json_repaired = True
        if data is None:
            continue
        score, rationale = parse_judge_payload(data)
        if score is not None:
            parsed_score = score
            if rationale:
                parsed_rationale = rationale
            break

    if parsed_score is not None:
        src: JudgeScoreSource = "repaired" if json_repaired or len(blocks) > 1 else "model_parsed"
        return parsed_score, src, parsed_rationale

    fb_score, _ = keyword_fallback_judge(raw_response)
    if fb_score is not None:
        return fb_score, "keyword_fallback", None
    return None, "unparseable", None


def count_parse_sources(scores: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in scores:
        src = str(row.get("parse_source") or "unknown")
        counts[src] = counts.get(src, 0) + 1
    return counts
