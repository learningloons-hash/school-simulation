from mirofish_backend.llm.router import effective_model_id, resolve_effective_provider


def test_hybrid_frontier_on_first_turn_only() -> None:
    assert resolve_effective_provider(routing_mode="hybrid", round_number=1, turn_index=1) == "anthropic"
    assert resolve_effective_provider(routing_mode="hybrid", round_number=1, turn_index=2) == "lmstudio"
    assert resolve_effective_provider(routing_mode="hybrid", round_number=3, turn_index=1) == "anthropic"
    assert resolve_effective_provider(routing_mode="hybrid", round_number=3, turn_index=3) == "lmstudio"


def test_pure_modes_ignore_turn() -> None:
    assert resolve_effective_provider(routing_mode="lmstudio", round_number=9, turn_index=1) == "lmstudio"
    assert resolve_effective_provider(routing_mode="anthropic", round_number=9, turn_index=9) == "anthropic"


def test_effective_model_id_selects_configured_models() -> None:
    assert (
        effective_model_id(
            provider="lmstudio",
            lmstudio_model="  local-model  ",
            anthropic_model="claude-3",
        )
        == "local-model"
    )
    assert (
        effective_model_id(
            provider="anthropic",
            lmstudio_model="local-model",
            anthropic_model="claude-opus",
        )
        == "claude-opus"
    )
