"""Append-only JSONL log of outbound LLM request parameters (no secrets)."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from mirofish_backend.config import Settings, get_settings


def llm_request_log_basename(simulation_id: str) -> str:
    return f"{simulation_id}_llm_requests.jsonl"


def llm_request_log_path(transcript_dir: str, simulation_id: str) -> str:
    return os.path.join(transcript_dir, llm_request_log_basename(simulation_id))


def adhoc_llm_request_log_path(settings: Settings | None = None) -> str:
    s = settings or get_settings()
    return os.path.join(s.llm_request_log_dir, "adhoc_requests.jsonl")


_adhoc_logger_cache: dict[str, LLMRequestLogger] = {}


@dataclass
class LLMRequestLogger:
    """Append-only JSONL log for one file (per-run or shared adhoc)."""

    path: str
    simulation_id: str
    _seq: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        parent = os.path.dirname(self.path) or "."
        os.makedirs(parent, exist_ok=True)
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


def get_adhoc_llm_request_logger(settings: Settings | None = None) -> LLMRequestLogger:
    """Shared JSONL for LLM calls outside a queued simulation run."""
    path = adhoc_llm_request_log_path(settings)
    cached = _adhoc_logger_cache.get(path)
    if cached is not None:
        return cached
    logger = LLMRequestLogger(path=path, simulation_id="adhoc")
    _adhoc_logger_cache[path] = logger
    return logger


def resolve_llm_request_logger(
    *,
    run_logger: LLMRequestLogger | None,
    settings: Settings | None = None,
) -> LLMRequestLogger:
    """Per-run JSONL when simulating; otherwise adhoc JSONL under ``llm_request_log_dir``."""
    if run_logger is not None:
        return run_logger
    return get_adhoc_llm_request_logger(settings)
