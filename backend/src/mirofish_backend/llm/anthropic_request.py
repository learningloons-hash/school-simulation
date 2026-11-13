"""Anthropic Messages API request options (Sonnet 5.5 thinking / effort)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from mirofish_backend.config import Settings

ThinkingType = Literal["between_tools", "adaptive", "disabled"]
EffortLevel = Literal["low", "medium", "high", "xhigh", "max"]

SONNET_55_MODEL_ID = "claude-sonnet-5-5"
VALID_EFFORT_LEVELS = frozenset({"low", "medium", "high", "xhigh", "max"})
SONNET_55_THINKING_TYPES = frozenset({"between_tools", "adaptive"})


def is_claude_sonnet_5_5(model_id: str | None) -> bool:
    mid = (model_id or "").strip().lower()
    if not mid:
        return False
    if mid == SONNET_55_MODEL_ID:
        return True
    return mid.startswith(f"{SONNET_55_MODEL_ID}-")


def anthropic_request_params_supported(model_id: str | None) -> bool:
    """Whether ``thinking`` and ``output_config.effort`` should be sent for this model id."""
    return is_claude_sonnet_5_5(model_id)


def validate_sonnet_55_thinking_effort(
    *,
    model_id: str,
    thinking_type: str,
    effort: str,
) -> None:
    """
    Reject API combinations that return HTTP 400 before any request is sent.

    Verified against Anthropic Sonnet 5.5 migration guide (2026-11-12):
    - ``thinking: {"type": "disabled"}`` → 400
    - ``between_tools`` with ``xhigh`` or ``max`` effort → 400
    """
    if not is_claude_sonnet_5_5(model_id):
        return
    tt = (thinking_type or "").strip().lower()
    ef = (effort or "").strip().lower()
    if tt == "disabled":
        raise ValueError(
            'thinking type "disabled" is rejected on claude-sonnet-5-5; '
            'use "between_tools" (no up-front thinking) or "adaptive".'
        )
    if tt not in SONNET_55_THINKING_TYPES:
        raise ValueError(
            f'Invalid thinking type {thinking_type!r} for claude-sonnet-5-5; '
            f'expected one of: {sorted(SONNET_55_THINKING_TYPES)}'
        )
    if ef not in VALID_EFFORT_LEVELS:
        raise ValueError(f"anthropic_effort must be one of: {sorted(VALID_EFFORT_LEVELS)}; got {effort!r}")
    if tt == "between_tools" and ef in ("xhigh", "max"):
        raise ValueError(
            f'thinking "between_tools" cannot be used with effort {effort!r} on claude-sonnet-5-5; '
            'use effort low, medium, or high, or switch thinking to "adaptive".'
        )


@dataclass(frozen=True)
class AnthropicRequestConfig:
    """Resolved Anthropic request knobs for one simulation run (freezeable in config_snapshot)."""

    model_id: str
    thinking: dict[str, str] | None
    effort: str | None
    random_seed: int | None
    price_map_key: str | None
    price_map_date: str | None

    def payload_thinking(self) -> dict[str, str] | None:
        return dict(self.thinking) if self.thinking else None

    def payload_effort(self) -> str | None:
        return self.effort


@dataclass(frozen=True)
class RunLLMExtras:
    """Forwarded into every ``llm_complete`` call for a simulation run."""

    anthropic_config: AnthropicRequestConfig | None
    request_logger: Any | None  # LLMRequestLogger | None — avoid circular import in types

    def llm_complete_kwargs(self) -> dict[str, Any]:
        if self.anthropic_config is None:
            return {"llm_request_logger": self.request_logger, "llm_request_context": None}
        cfg = self.anthropic_config
        return {
            "anthropic_thinking": cfg.payload_thinking(),
            "anthropic_effort": cfg.payload_effort(),
            "anthropic_random_seed": cfg.random_seed,
            "llm_request_logger": self.request_logger,
        }


def resolve_anthropic_request_config(
    *,
    model_id: str,
    settings: Settings,
    request_thinking_type: str | None = None,
    request_effort: str | None = None,
    random_seed: int | None = None,
) -> AnthropicRequestConfig:
    """
    Merge run request → settings → model defaults for thinking and effort.

    Only ``claude-sonnet-5-5`` receives ``thinking`` / ``output_config.effort`` on the wire.
    """
    from mirofish_backend.llm.model_profiles import resolve_anthropic_pricing_key
    from mirofish_backend.simulation.economics import price_map_date_for_key

    mid = (model_id or "").strip()
    thinking: dict[str, str] | None = None
    effort: str | None = None

    if anthropic_request_params_supported(mid):
        tt = (request_thinking_type or settings.anthropic_thinking_type or "between_tools").strip().lower()
        ef = (request_effort or settings.anthropic_effort or "medium").strip().lower()
        validate_sonnet_55_thinking_effort(model_id=mid, thinking_type=tt, effort=ef)
        thinking = {"type": tt}
        effort = ef

    pk = resolve_anthropic_pricing_key(mid) if mid else None
    pmd = price_map_date_for_key(pk) if pk else None

    return AnthropicRequestConfig(
        model_id=mid,
        thinking=thinking,
        effort=effort,
        random_seed=random_seed,
        price_map_key=pk,
        price_map_date=pmd,
    )


def anthropic_request_config_snapshot(cfg: AnthropicRequestConfig) -> dict[str, Any]:
    """``config_snapshot`` / export manifest fields for Anthropic request provenance."""
    return {
        "anthropic_model_resolved": cfg.model_id,
        "anthropic_thinking": cfg.thinking,
        "anthropic_effort": cfg.effort,
        "anthropic_random_seed_recorded": cfg.random_seed,
        "anthropic_price_map_key": cfg.price_map_key,
        "anthropic_price_map_date": cfg.price_map_date,
    }


def run_manifest_from_anthropic_config(
    cfg: AnthropicRequestConfig,
    *,
    llm_request_log_basename: str | None,
) -> dict[str, Any]:
    """Compact run manifest block for exports and study freeze checks."""
    out: dict[str, Any] = {
        "resolved_model_id": cfg.model_id,
        "thinking": cfg.thinking,
        "effort": cfg.effort,
        "price_map_date": cfg.price_map_date,
        "price_map_key": cfg.price_map_key,
    }
    if llm_request_log_basename:
        out["llm_request_log_file"] = llm_request_log_basename
    return out
