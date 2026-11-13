"""Append-only JSONL log of outbound LLM request parameters (no secrets)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def llm_request_log_basename(simulation_id: str) -> str:
    return f"{simulation_id}_llm_requests.jsonl"


def llm_request_log_path(transcript_dir: str, simulation_id: str) -> str:
    return os.path.join(transcript_dir, llm_request_log_basename(simulation_id))


@dataclass
class LLMRequestLogger:
    """One JSONL file per simulation run under ``transcript_dir``."""

    path: str
    simulation_id: str
    _seq: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        if not os.path.isfile(self.path):
            with open(self.path, "w", encoding="utf-8") as f:
                f.write("")

    def append(
        self,
        *,
        provider: str,
        model_id: str,
        thinking: dict[str, Any] | None,
        effort: str | None,
        max_tokens: int,
        temperature: float | None,
        seed: int | None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._seq += 1
        row: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "seq": self._seq,
            "simulation_id": self.simulation_id,
            "provider": provider,
            "model_id": model_id,
            "thinking": thinking,
            "effort": effort,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "seed": seed,
        }
        if extra:
            row.update(extra)
        line = json.dumps(row, ensure_ascii=False, separators=(",", ":"))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
