"""senna-iter-56 Part A — per-model PROVIDER_PRICE_MAP and profile pricing_key wiring."""

from __future__ import annotations

import pytest

from mirofish_backend.config import Settings
from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    anthropic_default,
    resolve_anthropic_pricing_key,
)
from mirofish_backend.simulation.economics import (
    PROVIDER_PRICE_MAP,
    estimate_cost_usd,
    resolve_billing_provider_key,
)


def test_haiku_4_5_resolves_to_granular_rates() -> None:
    model = "claude-haiku-4-5-20251001"
    key = resolve_anthropic_pricing_key(model)
    assert key == "anthropic_haiku_4_5"
    rates = PROVIDER_PRICE_MAP[key]
    assert rates["input_per_mtok"] == 1.0
    assert rates["output_per_mtok"] == 5.0
    assert (
        resolve_billing_provider_key(
            effective_profile_id=ANTHROPIC_DEFAULT_ID,
            effective_provider="anthropic",
            effective_model=model,
        )
        == key
    )


def test_opus_5_resolves_to_opus_tier_rates() -> None:
    model = "claude-opus-5-20260201"
    key = resolve_anthropic_pricing_key(model)
    assert key == "anthropic_opus_5"
    rates = PROVIDER_PRICE_MAP[key]
    assert rates["input_per_mtok"] == 5.0
    assert rates["output_per_mtok"] == 25.0


def test_opus_4_legacy_resolves_to_opus_4_rates() -> None:
    model = "claude-opus-4-20250514"
    key = resolve_anthropic_pricing_key(model)
    assert key == "anthropic_opus_4"
    rates = PROVIDER_PRICE_MAP[key]
    assert rates["input_per_mtok"] == 15.0
    assert rates["output_per_mtok"] == 75.0


def test_haiku_and_opus_costs_differ_for_same_tokens() -> None:
    haiku = estimate_cost_usd(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        provider_key="anthropic_haiku_4_5",
    )
    opus = estimate_cost_usd(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        provider_key="anthropic_opus_5",
    )
    assert haiku == pytest.approx(6.0, rel=1e-9)
    assert opus == pytest.approx(30.0, rel=1e-9)
    assert opus > haiku


def test_unknown_anthropic_model_falls_back_to_generic_bucket() -> None:
    assert resolve_anthropic_pricing_key("claude-future-unknown-20990101") == "anthropic"
    cost = estimate_cost_usd(
        input_tokens=1_000_000,
        output_tokens=0,
        provider_key="anthropic",
    )
    assert cost == pytest.approx(3.0, rel=1e-9)


def test_anthropic_default_profile_pricing_key_from_settings() -> None:
    haiku = anthropic_default(Settings(anthropic_model="claude-haiku-4-5-20251001"))
    assert haiku.pricing_key == "anthropic_haiku_4_5"
    opus = anthropic_default(Settings(anthropic_model="claude-opus-5-20260201"))
    assert opus.pricing_key == "anthropic_opus_5"


def test_legacy_anthropic_without_model_uses_generic_fallback() -> None:
    assert (
        resolve_billing_provider_key(
            effective_profile_id=None,
            effective_provider="anthropic",
            effective_model=None,
        )
        == "anthropic"
    )
