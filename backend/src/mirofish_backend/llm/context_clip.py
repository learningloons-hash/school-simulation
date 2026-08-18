"""
Shrink prior-agent text before injecting into prompts.

Reasoning models often emit long chain-of-thought; replaying full raw_response
into the next turn can exceed small n_ctx (e.g. 4096) on the local server.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, cast

_STATE_WRAPPER = re.compile(r"<state>\s*[\s\S]*?\s*</state>", re.IGNORECASE)


def _strip_state_tags(text: str) -> str:
    return _STATE_WRAPPER.sub("", text or "").strip()


def _trim_leading_reasoning_blob(text: str) -> str:
    """
    If the model started with an explicit thinking scaffold, prefer content after **Draft:** when present.
    """
    head = (text or "")[:400].lower()
    if "thinking process" not in head:
        return text
    for needle in ("**draft:**", "**draft**:", "draft:"):
        pos = text.lower().find(needle)
        if pos != -1:
            return text[pos:].strip()
    return text


    return text


@dataclass(frozen=True)
class PeerClipResult:
    text: str
    truncated: bool


def prepare_peer_response_for_prompt_with_meta(raw: str, *, max_chars: int) -> PeerClipResult:
    t = (raw or "").strip()
    if not t:
        return PeerClipResult(text=t, truncated=False)
    t = _strip_state_tags(t)
    t = _trim_leading_reasoning_blob(t)
    if max_chars <= 0 or len(t) <= max_chars:
        return PeerClipResult(text=t, truncated=False)
    tail = t[-max_chars:].lstrip()
    return PeerClipResult(
        text=f"…[truncated from {len(t)} chars]\n{tail}",
        truncated=True,
    )


def prepare_peer_response_for_prompt(raw: str, *, max_chars: int) -> str:
    """
    Full raw_response stays in the DB/transcript; this is only for cross-agent context.
    """
    return prepare_peer_response_for_prompt_with_meta(raw, max_chars=max_chars).text


def clip_memory_lines(lines: list[str], *, max_chars: int) -> list[str]:
    return [prepare_peer_response_for_prompt(line, max_chars=max_chars) for line in lines]


def clip_recent_interactions(rows: list[dict[str, Any]], *, max_chars: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        r["raw_response"] = prepare_peer_response_for_prompt(
            cast(str, row.get("raw_response", "")), max_chars=max_chars
        )
        out.append(r)
    return out
