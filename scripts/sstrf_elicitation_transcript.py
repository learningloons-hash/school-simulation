"""Minimal transcript helpers for SSTRF scoring evidence assembly."""

from __future__ import annotations

import re


def _strip_state_block(text: str) -> str:
    return re.sub(r"<state>.*?</state>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()
