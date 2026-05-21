import asyncio
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.config import Settings
from mirofish_backend.api.capabilities import build_capabilities_dict
from mirofish_backend.llm.model_profiles import (
    ANTHROPIC_DEFAULT_ID,
    BUILTIN_PROFILE_IDS,
    LOCAL_LMSTUDIO_DEFAULT_ID,
    OPENAI_DEFAULT_ID,
    OPENROUTER_DEFAULT_ID,
    _BUILTIN_PROFILE_FACTORIES,
    anthropic_default,
    build_model_profiles_capabilities,
    capabilities_dict,
    local_lmstudio_default,
    model_profile_config_snapshot,
    openai_default,
    openrouter_default,
    profile_snapshot_dict,
    resolve_api_key_from_env,
    resolve_run_llm_provider,
    resolve_run_profiles,
    run_llm_credentials,
    run_openai_compatible_api_key,
)
from mirofish_backend.main import app


def _settings() -> Settings:
    return Settings(
        lmstudio_base_url="http://127.0.0.1:1234/v1",
        lmstudio_model="local-test-model",
        anthropic_model="claude-test",
    )


def test_resolve_no_profile_lmstudio_maps_to_local_default() -> None:
    s = _settings()
    r = resolve_run_profiles(model_profile_id=None, llm_provider="lmstudio", settings=s)
    assert r.primary_profile.profile_id == LOCAL_LMSTUDIO_DEFAULT_ID
    assert r.requested_profile_id is None
    assert not r.hybrid_mode


def test_resolve_no_profile_anthropic_maps_to_anthropic_default() -> None:
    s = _settings()
    r = resolve_run_profiles(model_profile_id=None, llm_provider="anthropic", settings=s)
    assert r.primary_profile.profile_id == ANTHROPIC_DEFAULT_ID


def test_resolve_hybrid_without_profile_has_both_legs() -> None:
    s = _settings()
    r = resolve_run_profiles(model_profile_id=None, llm_provider="hybrid", settings=s)
    assert r.hybrid_mode
    assert r.local_profile.profile_id == LOCAL_LMSTUDIO_DEFAULT_ID
    assert r.frontier_profile.profile_id == ANTHROPIC_DEFAULT_ID


def test_resolve_invalid_profile_id_raises() -> None:
    s = _settings()
    with pytest.raises(ValueError, match="Unknown model_profile_id"):
        resolve_run_profiles(model_profile_id="openai_gpt4", llm_provider="lmstudio", settings=s)


def test_explicit_anthropic_profile() -> None:
    s = _settings()
    r = resolve_run_profiles(
        model_profile_id=ANTHROPIC_DEFAULT_ID,
        llm_provider="lmstudio",
        settings=s,
    )
    assert r.requested_profile_id == ANTHROPIC_DEFAULT_ID
    assert r.primary_profile.provider_type == "anthropic"
    assert r.primary_profile.model_id == "claude-test"


def test_builtin_profile_ids_derived_from_registry() -> None:
    assert BUILTIN_PROFILE_IDS == frozenset(_BUILTIN_PROFILE_FACTORIES.keys())
    assert BUILTIN_PROFILE_IDS == {
        LOCAL_LMSTUDIO_DEFAULT_ID,
        ANTHROPIC_DEFAULT_ID,
        OPENAI_DEFAULT_ID,
        OPENROUTER_DEFAULT_ID,
    }


def test_openai_default_profile_resolves_openai_compatible_metadata() -> None:
    s = Settings(
        openai_base_url="https://api.openai.com/v1",
        openai_model="gpt-4o-mini",
        openai_api_key_env="OPENAI_API_KEY",
    )
    p = openai_default(s)
    assert p.provider_type == "openai_compatible"
    assert p.base_url == "https://api.openai.com/v1"
    assert p.model_id == "gpt-4o-mini"
    assert p.api_key_env == "OPENAI_API_KEY"
    assert p.pricing_key == "openai"

    r = resolve_run_profiles(model_profile_id=OPENAI_DEFAULT_ID, llm_provider="lmstudio", settings=s)
    assert r.primary_profile.profile_id == OPENAI_DEFAULT_ID
    assert r.local_profile.profile_id == OPENAI_DEFAULT_ID
    lm_model, lm_url, _ = run_llm_credentials(r, s)
    assert lm_model == "gpt-4o-mini"
    assert lm_url == "https://api.openai.com/v1"


def test_openrouter_default_profile_resolves_metadata() -> None:
    s = Settings(
        openrouter_base_url="https://openrouter.ai/api/v1",
        openrouter_model="anthropic/claude-3.5-sonnet",
        openrouter_api_key_env="OPENROUTER_API_KEY",
    )
    p = openrouter_default(s)
    assert p.provider_type == "openai_compatible"
    assert p.base_url == "https://openrouter.ai/api/v1"
    assert p.model_id == "anthropic/claude-3.5-sonnet"
    assert p.api_key_env == "OPENROUTER_API_KEY"
    assert p.pricing_key == "openrouter"


def test_resolve_run_llm_provider_infers_lmstudio_for_commercial_profiles() -> None:
    s = _settings()
    assert (
        resolve_run_llm_provider(
            request_llm_provider=None,
            model_profile_id=OPENAI_DEFAULT_ID,
            settings=s,
        )
        == "lmstudio"
    )


def test_run_openai_compatible_api_key_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-not-real")
    s = _settings()
    r = resolve_run_profiles(model_profile_id=OPENAI_DEFAULT_ID, llm_provider="lmstudio", settings=s)
    assert run_openai_compatible_api_key(r) == "sk-test-not-real"
    assert resolve_api_key_from_env("OPENAI_API_KEY") == "sk-test-not-real"


def test_local_profile_capabilities_metadata() -> None:
    s = _settings()
    p = local_lmstudio_default(s)
    cap = capabilities_dict(p.capabilities)
    assert cap["context_window"] is None
    assert cap["supports_streaming"] is True
    assert cap["json_reliability"] == "medium"
    assert cap["state_block_reliability"] == "medium"
    assert cap["reasoning_leakage_risk"] == "high"
    assert cap["recommended_max_concurrency"] == 4


def test_anthropic_profile_capabilities_metadata() -> None:
    s = _settings()
    p = anthropic_default(s)
    cap = capabilities_dict(p.capabilities)
    assert cap["context_window"] == 200_000
    assert cap["supports_embeddings"] is False
    assert cap["json_reliability"] == "high"
    assert cap["state_block_reliability"] == "high"
    assert cap["reasoning_leakage_risk"] == "low"
    assert cap["recommended_max_concurrency"] == 8


def test_capabilities_api_includes_capability_block_without_secrets() -> None:
    cap = build_capabilities_dict()
    profiles = cap["model_profiles"]["profiles"]
    local_row = next(p for p in profiles if p["profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID)
    anthropic_row = next(p for p in profiles if p["profile_id"] == ANTHROPIC_DEFAULT_ID)
    assert local_row["is_builtin"] is True
    assert anthropic_row["is_builtin"] is True
    openai_row = next(p for p in profiles if p["profile_id"] == OPENAI_DEFAULT_ID)
    for row in (local_row, anthropic_row, openai_row):
        assert "capabilities" in row
        assert "api_key_env" not in row
    assert openai_row["provider_type"] == "openai_compatible"
    assert openai_row["capabilities"]["supports_usage"] is True
    assert local_row["capabilities"]["reasoning_leakage_risk"] == "high"
    assert anthropic_row["capabilities"]["context_window"] == 200_000


def test_profile_snapshot_dict_includes_capability_metadata() -> None:
    s = _settings()
    snap = profile_snapshot_dict(anthropic_default(s))
    assert snap["is_builtin"] is True
    assert snap["capabilities"]["json_reliability"] == "high"
    assert snap.get("api_key_env") == "ANTHROPIC_API_KEY"


def test_profile_snapshot_dict_includes_repro_fields() -> None:
    s = _settings()
    p = local_lmstudio_default(s)
    snap = profile_snapshot_dict(p)
    assert snap["profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID
    assert snap["provider_type"] == "openai_compatible"
    assert snap["model_id"] == "local-test-model"
    assert snap["base_url"] == "http://127.0.0.1:1234/v1"
    assert snap["pricing_key"] == "lmstudio"
    assert snap["supports_usage"] is True


def test_hybrid_config_snapshot_includes_local_and_frontier() -> None:
    s = _settings()
    r = resolve_run_profiles(model_profile_id=None, llm_provider="hybrid", settings=s)
    cfg = model_profile_config_snapshot(r)
    assert cfg["model_profile_id"] is None
    assert cfg["model_profile"] is None
    assert cfg["model_profile_local"]["profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID
    assert cfg["model_profile_frontier"]["profile_id"] == ANTHROPIC_DEFAULT_ID


def test_run_llm_credentials_explicit_local_profile() -> None:
    s = _settings()
    r = resolve_run_profiles(
        model_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        llm_provider="anthropic",
        settings=s,
    )
    lm_model, lm_url, ant_model = run_llm_credentials(r, s)
    assert lm_model == "local-test-model"
    assert lm_url == "http://127.0.0.1:1234/v1"
    assert ant_model == "claude-test"


def test_simulation_run_request_rejects_unknown_profile() -> None:
    from mirofish_backend.api.simulations import SimulationRunRequest

    with pytest.raises(ValueError, match="model_profile_id must be one of"):
        SimulationRunRequest(model_profile_id="does_not_exist")


def _discard_create_task(coro: object, *_args: object, **_kwargs: object) -> None:
    if asyncio.iscoroutine(coro):
        coro.close()
    return None


@pytest.mark.asyncio
async def test_queue_run_persists_model_profile_in_config_snapshot(tmp_path) -> None:
    from mirofish_backend.api import simulations as sim_api
    from mirofish_backend.api.simulations import SimulationRunRequest, queue_simulation_run

    db_path = str(tmp_path / "test.sqlite")
    settings = Settings(sqlite_path=db_path, lmstudio_model="snap-model", anthropic_model="snap-claude")

    created: dict[str, object] = {}

    async def fake_create(*_a, config_snapshot=None, **kwargs):
        created["config_snapshot"] = config_snapshot
        return "sim-profile-test"

    async def noop_guarded(**_kwargs):
        return None

    with (
        patch.object(sim_api, "create_simulation_run", side_effect=fake_create),
        patch.object(sim_api, "run_simulation_task_guarded", side_effect=noop_guarded),
        patch.object(sim_api, "load_scenario_for_run", return_value=(_minimal_scenario(), "builtin")),
        patch.object(sim_api.asyncio, "create_task", side_effect=_discard_create_task),
    ):
        req = SimulationRunRequest(
            scenario_id="psle_reform_mvp",
            model_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            llm_provider="lmstudio",
        )
        await queue_simulation_run(settings, req)

    snap = created.get("config_snapshot")
    assert isinstance(snap, dict)
    assert snap.get("routing_policy") == "local_only"
    assert snap.get("routing_profile_local_id") == LOCAL_LMSTUDIO_DEFAULT_ID
    assert snap.get("model_profile_id") == LOCAL_LMSTUDIO_DEFAULT_ID
    mp = snap.get("model_profile")
    assert isinstance(mp, dict)
    assert mp.get("model_id") == "snap-model"
    assert mp.get("pricing_key") == "lmstudio"
    assert mp.get("is_builtin") is True
    assert mp["capabilities"]["recommended_max_concurrency"] == 4


def _minimal_scenario():
    from mirofish_backend.scenarios.registry import PersonaTemplate, ScenarioConfig

    return ScenarioConfig(
        scenario_id="psle_reform_mvp",
        name="Test",
        policy_events={1: "policy"},
        personas=[
            PersonaTemplate(
                persona_id="agent_a",
                role="lead",
                name="Agent A",
                role_level=1,
                style_cues="neutral",
                beliefs={},
            )
        ],
    )


def test_capabilities_includes_model_profiles_block() -> None:
    cap = build_capabilities_dict()
    mp = cap.get("model_profiles")
    assert isinstance(mp, dict)
    profiles = mp.get("profiles")
    assert isinstance(profiles, list)
    assert len(profiles) == 4
    ids = {p["profile_id"] for p in profiles}
    assert ids == {
        LOCAL_LMSTUDIO_DEFAULT_ID,
        ANTHROPIC_DEFAULT_ID,
        OPENAI_DEFAULT_ID,
        OPENROUTER_DEFAULT_ID,
    }
    local_row = next(p for p in profiles if p["profile_id"] == LOCAL_LMSTUDIO_DEFAULT_ID)
    assert local_row["label"] == "Local model"
    assert local_row["supports_embeddings"] is True
    assert local_row["supports_usage"] is True
    assert "description" in local_row
    hybrid = mp.get("hybrid_routing")
    assert hybrid.get("llm_provider") == "hybrid"
    assert hybrid.get("label")


def test_build_model_profiles_capabilities_marks_server_default() -> None:
    s = Settings(llm_provider="anthropic")
    block = build_model_profiles_capabilities(s)
    anthropic_row = next(p for p in block["profiles"] if p["profile_id"] == ANTHROPIC_DEFAULT_ID)
    assert anthropic_row["is_default"] is True
    assert block["hybrid_routing"]["is_default"] is False


def test_post_run_invalid_model_profile_id_422(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "api.sqlite"))
    client = TestClient(app)
    resp = client.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "model_profile_id": "unknown_profile",
        },
    )
    assert resp.status_code == 422
