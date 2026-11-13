"""M3 Sonnet 5.5 pin — pricing-key resolution and cost math."""

from __future__ import annotations

import pytest

from senna_backend.llm.model_profiles import resolve_anthropic_pricing_key
from senna_backend.simulation.economics import (
    PROVIDER_PRICE_MAP,
    estimate_cost_usd,
    price_map_date_for_key,
)

SONNET_55_PRICE_MAP_DATE = "2026-11-12"


@pytest.mark.parametrize(
    "model_id",
    ["claude-sonnet-5-5", "claude-sonnet-5-5-20260928"],
)
def test_sonnet_55_resolves_to_dedicated_pricing_row_not_generic_bucket(model_id: str) -> None:
    key = resolve_anthropic_pricing_key(model_id)
    assert key == "anthropic_sonnet_5_5"
    assert key != "anthropic_sonnet"  # must not fall into the generic Sonnet bucket


def test_sonnet_55_price_row_is_2_and_10_dollars_dated_2026_11_12() -> None:
    row = PROVIDER_PRICE_MAP["anthropic_sonnet_5_5"]
    assert row["input_per_mtok"] == 2.00
    assert row["output_per_mtok"] == 10.00
    assert price_map_date_for_key("anthropic_sonnet_5_5") == SONNET_55_PRICE_MAP_DATE


def test_generic_sonnet_bucket_is_unchanged_and_distinct_from_55() -> None:
    generic = PROVIDER_PRICE_MAP["anthropic_sonnet"]
    sonnet_55 = PROVIDER_PRICE_MAP["anthropic_sonnet_5_5"]
    assert (generic["input_per_mtok"], generic["output_per_mtok"]) != (
        sonnet_55["input_per_mtok"],
        sonnet_55["output_per_mtok"],
    )


def test_sonnet_55_cost_uses_dedicated_rates() -> None:
    cost = estimate_cost_usd(
        input_tokens=1_000_000,
        output_tokens=1_000_000,
        provider_key="anthropic_sonnet_5_5",
    )
    assert cost == pytest.approx(12.0, rel=1e-9)  # 2.00 (in) + 10.00 (out)


def test_output_tokens_including_thinking_are_billed_at_the_output_rate() -> None:
    """
    The Anthropic Messages API reports thinking tokens as part of ``usage.output_tokens``
    (there is no separate thinking-token field anywhere in this codebase's accounting).
    So doubling the reported output-token count — as if thinking tokens were included
    in it — must scale cost linearly at the single output rate, not some blended rate.
    """
    base = estimate_cost_usd(
        input_tokens=0,
        output_tokens=1_000_000,
        provider_key="anthropic_sonnet_5_5",
    )
    doubled = estimate_cost_usd(
        input_tokens=0,
        output_tokens=2_000_000,
        provider_key="anthropic_sonnet_5_5",
    )
    assert base == pytest.approx(10.0, rel=1e-9)
    assert doubled == pytest.approx(2 * base, rel=1e-9)
