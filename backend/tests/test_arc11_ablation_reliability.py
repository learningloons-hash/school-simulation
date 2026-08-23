"""Tests for Arc 11 ablation harness reliability improvements (post-iter-52).

Covers scripts/run_arc11_ablation.py: preflight probe, .env loading, CLI
defaults, and interview retry/backoff — the "local ablation reliability"
follow-up raised after Mark's Mac Mini sweep hit silent LM Studio failures
(ConnectError on interview, HTTP 400 "No models loaded" on embeddings).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from run_arc11_ablation import (  # noqa: E402
    build_parser,
    check_transcript_for_llm_errors,
    load_dotenv_if_present,
    load_existing_records,
    run_ablation_preflight,
    run_diagnostics_with_retry,
    write_ablation_artifacts,
)

from mirofish_backend.diagnostics.arc11_ablation import AblationRunProfile  # noqa: E402
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID  # noqa: E402


class _FakeSettings:
    lmstudio_base_url = "http://127.0.0.1:1234/v1"
    lmstudio_model = "google/gemma-4-26b-a4b"
    embedding_model = ""
    llm_provider = "lmstudio"
    sqlite_path = ":memory:"
    anthropic_api_key = "sk-ant-test-not-real"
    anthropic_model = "claude-haiku-4-5-20251001"


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------


def test_load_dotenv_sets_unset_vars_only(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "EMBEDDING_MODEL=text-embedding-nomic-embed-text-v1.5\n"
        "# a comment\n"
        "\n"
        "ANTHROPIC_API_KEY=should-not-override\n"
    )
    monkeypatch.delenv("EMBEDDING_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "already-set")

    assert load_dotenv_if_present(env_file) is True
    assert __import__("os").environ["EMBEDDING_MODEL"] == "text-embedding-nomic-embed-text-v1.5"
    assert __import__("os").environ["ANTHROPIC_API_KEY"] == "already-set"


def test_load_dotenv_fills_empty_shell_export(tmp_path, monkeypatch) -> None:
    """
    Regression: Mark's real key in backend/.env was correct (curl confirmed it worked),
    but the script still hit a 401 -- his shell had ANTHROPIC_API_KEY exported as an
    EMPTY string, which the original 'key not in os.environ' check treated as
    "already set" and refused to overwrite. A present-but-empty export must not shadow
    a real value from .env.
    """
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=sk-ant-real-value\n")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    assert load_dotenv_if_present(env_file) is True
    assert __import__("os").environ["ANTHROPIC_API_KEY"] == "sk-ant-real-value"


def test_load_dotenv_missing_file_returns_false(tmp_path) -> None:
    assert load_dotenv_if_present(tmp_path / "does-not-exist.env") is False


# ---------------------------------------------------------------------------
# CLI defaults
# ---------------------------------------------------------------------------


def test_cli_defaults_interview_and_judge_to_anthropic() -> None:
    args = build_parser().parse_args([])
    assert args.interview_profile_id == ANTHROPIC_DEFAULT_ID
    assert args.judge_profile_id == ANTHROPIC_DEFAULT_ID
    assert args.skip_preflight is False
    assert args.env_file.name == ".env"


def test_cli_accepts_skip_preflight_and_env_file_override(tmp_path) -> None:
    custom_env = tmp_path / "custom.env"
    args = build_parser().parse_args(["--skip-preflight", "--env-file", str(custom_env)])
    assert args.skip_preflight is True
    assert args.env_file == custom_env


# ---------------------------------------------------------------------------
# Preflight probe
# ---------------------------------------------------------------------------


def _mock_async_client(get_response=None, get_side_effect=None):
    mock_client = AsyncMock()
    if get_side_effect is not None:
        mock_client.get = AsyncMock(side_effect=get_side_effect)
    else:
        mock_client.get = AsyncMock(return_value=get_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


@pytest.mark.asyncio
async def test_preflight_unreachable_models_endpoint_raises_actionable_error() -> None:
    mock_client = _mock_async_client(
        get_side_effect=httpx.ConnectError("connection refused", request=None)
    )
    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="cannot reach LM Studio"):
            await run_ablation_preflight(_FakeSettings(), check_embeddings=True)


@pytest.mark.asyncio
async def test_preflight_chat_failure_names_the_model_and_gives_curl() -> None:
    models_resp = MagicMock()
    models_resp.status_code = 200
    mock_client = _mock_async_client(get_response=models_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            side_effect=RuntimeError("OpenAI-compatible HTTP 400: model not found"),
        ):
            with pytest.raises(RuntimeError, match="chat completion against model") as exc_info:
                await run_ablation_preflight(_FakeSettings(), check_embeddings=True)
    assert "google/gemma-4-26b-a4b" in str(exc_info.value)
    assert "curl" in str(exc_info.value)


@pytest.mark.asyncio
async def test_preflight_embedding_failure_flags_dual_model_requirement() -> None:
    models_resp = MagicMock()
    models_resp.status_code = 200
    mock_client = _mock_async_client(get_response=models_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                side_effect=RuntimeError("LM Studio embeddings HTTP 400: No models loaded"),
            ):
                with pytest.raises(RuntimeError, match="embedding call against model") as exc_info:
                    await run_ablation_preflight(_FakeSettings(), check_embeddings=True)
    assert "EMBEDDING_MODEL" in str(exc_info.value)
    assert "MLX chat models do not serve" in str(exc_info.value)


@pytest.mark.asyncio
async def test_preflight_skips_embedding_check_when_disabled() -> None:
    models_resp = MagicMock()
    models_resp.status_code = 200
    mock_client = _mock_async_client(get_response=models_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ) as mock_chat:
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
            ) as mock_embed:
                await run_ablation_preflight(_FakeSettings(), check_embeddings=False)
    mock_chat.assert_awaited_once()
    mock_embed.assert_not_awaited()


@pytest.mark.asyncio
async def test_preflight_all_green_passes_silently() -> None:
    models_resp = MagicMock()
    models_resp.status_code = 200
    mock_client = _mock_async_client(get_response=models_resp)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                return_value=[[0.1, 0.2, 0.3]],
            ):
                await run_ablation_preflight(_FakeSettings(), check_embeddings=True)  # no raise


# ---------------------------------------------------------------------------
# Interview retry/backoff
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_diagnostics_retry_succeeds_after_transient_connect_error() -> None:
    calls = {"n": 0}

    async def flaky(**_kwargs):
        calls["n"] += 1
        if calls["n"] < 2:
            raise httpx.ConnectError("reset", request=None)
        return {"ok": True}

    with patch("run_arc11_ablation.run_arc10_diagnostics", new=flaky):
        with patch("run_arc11_ablation.asyncio.sleep", new=AsyncMock()):
            result = await run_diagnostics_with_retry(
                settings=_FakeSettings(),
                simulation_id="sim-1",
                fixtures_dir=Path("."),
                seed=42,
                execute_interview=True,
                interview_profile_id=ANTHROPIC_DEFAULT_ID,
                judge_profile_id=ANTHROPIC_DEFAULT_ID,
                max_attempts=3,
                initial_backoff_s=0.01,
            )
    assert result == {"ok": True}
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_diagnostics_retry_gives_up_with_actionable_message() -> None:
    async def always_fails(**_kwargs):
        raise httpx.ConnectError("reset", request=None)

    with patch("run_arc11_ablation.run_arc10_diagnostics", new=always_fails):
        with patch("run_arc11_ablation.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(RuntimeError, match="gave up after 2 attempts") as exc_info:
                await run_diagnostics_with_retry(
                    settings=_FakeSettings(),
                    simulation_id="sim-1",
                    fixtures_dir=Path("."),
                    seed=42,
                    execute_interview=True,
                    interview_profile_id="local_lmstudio_default",
                    judge_profile_id="local_lmstudio_default",
                    max_attempts=2,
                    initial_backoff_s=0.01,
                )
    assert "anthropic_default" in str(exc_info.value)
    assert "--skip-interview" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Anthropic preflight leg
# ---------------------------------------------------------------------------


def _mock_lmstudio_ok_client():
    models_resp = MagicMock()
    models_resp.status_code = 200
    return _mock_async_client(get_response=models_resp)


@pytest.mark.asyncio
async def test_preflight_skips_anthropic_when_profiles_are_local() -> None:
    mock_client = _mock_lmstudio_ok_client()
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                return_value=[[0.1]],
            ):
                with patch(
                    "mirofish_backend.llm.claude_client.chat_completion_anthropic",
                    new_callable=AsyncMock,
                ) as mock_anthropic:
                    await run_ablation_preflight(
                        _FakeSettings(),
                        check_embeddings=True,
                        interview_profile_id="local_lmstudio_default",
                        judge_profile_id="local_lmstudio_default",
                    )
    mock_anthropic.assert_not_awaited()


@pytest.mark.asyncio
async def test_preflight_anthropic_401_gives_actionable_message() -> None:
    mock_client = _mock_lmstudio_ok_client()
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(401, request=request)
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                return_value=[[0.1]],
            ):
                with patch(
                    "mirofish_backend.llm.claude_client.chat_completion_anthropic",
                    new_callable=AsyncMock,
                    side_effect=httpx.HTTPStatusError("401", request=request, response=response),
                ):
                    with pytest.raises(RuntimeError, match="HTTP 401") as exc_info:
                        await run_ablation_preflight(
                            _FakeSettings(),
                            check_embeddings=True,
                            interview_profile_id=ANTHROPIC_DEFAULT_ID,
                            judge_profile_id=ANTHROPIC_DEFAULT_ID,
                        )
    assert "ANTHROPIC_API_KEY" in str(exc_info.value)
    assert "local_lmstudio_default" in str(exc_info.value)


@pytest.mark.asyncio
async def test_preflight_missing_anthropic_key_fails_before_call() -> None:
    class _NoKeySettings(_FakeSettings):
        anthropic_api_key = ""

    mock_client = _mock_lmstudio_ok_client()
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                return_value=[[0.1]],
            ):
                with patch.dict(__import__("os").environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
                    with pytest.raises(RuntimeError, match="no ANTHROPIC_API_KEY is set"):
                        await run_ablation_preflight(
                            _NoKeySettings(),
                            check_embeddings=True,
                            interview_profile_id=ANTHROPIC_DEFAULT_ID,
                            judge_profile_id=ANTHROPIC_DEFAULT_ID,
                        )


@pytest.mark.asyncio
async def test_preflight_anthropic_success_passes_silently() -> None:
    mock_client = _mock_lmstudio_ok_client()
    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch(
            "run_arc11_ablation.chat_completion_openai_compatible",
            new_callable=AsyncMock,
            return_value=("OK", 1, 1),
        ):
            with patch(
                "run_arc11_ablation.embed_texts_openai_compatible",
                new_callable=AsyncMock,
                return_value=[[0.1]],
            ):
                with patch(
                    "mirofish_backend.llm.claude_client.chat_completion_anthropic",
                    new_callable=AsyncMock,
                    return_value=("OK", 1, 1),
                ):
                    await run_ablation_preflight(
                        _FakeSettings(),
                        check_embeddings=True,
                        interview_profile_id=ANTHROPIC_DEFAULT_ID,
                        judge_profile_id=ANTHROPIC_DEFAULT_ID,
                    )  # no raise


# ---------------------------------------------------------------------------
# Post-run transcript LLM-error scan
# ---------------------------------------------------------------------------


def test_transcript_check_passes_clean_bundle() -> None:
    bundle = {"transcript": [{"raw_response": "I think we should..."}, {"raw_response": "Agreed."}]}
    check_transcript_for_llm_errors(bundle, simulation_id="sim-1", condition="baseline", seed=42)


def test_transcript_check_raises_on_llm_error_placeholder() -> None:
    bundle = {
        "transcript": [
            {"raw_response": "fine turn"},
            {"raw_response": "[LLM error] RuntimeError: OpenAI-compatible HTTP 400: Context size has been exceeded."},
        ]
    }
    with pytest.raises(RuntimeError, match=r"1/2 turns in simulation sim-1") as exc_info:
        check_transcript_for_llm_errors(bundle, simulation_id="sim-1", condition="baseline", seed=42)
    assert "context length" in str(exc_info.value)


def test_transcript_check_handles_empty_bundle() -> None:
    check_transcript_for_llm_errors({}, simulation_id="sim-1", condition="baseline", seed=42)


# ---------------------------------------------------------------------------
# Resume / incremental persistence
#
# Regression coverage for: Mark's sweep completed 3 baseline runs (~25 min of
# real local LLM + Anthropic-interview work) then hit a single-turn ReadTimeout
# on run 4 and aborted -- with the old write-once-at-the-end behavior, that
# would have thrown away all 3 successful runs and the JSON output would never
# even have been created. Resume + write-after-every-run fixes both.
# ---------------------------------------------------------------------------

_BASELINE_REF = {
    "source": "docs/diagnostics/ARC10_MEASURED_BASELINE_REAL_RUN.md",
    "simulation_id": "baseline-sim",
    "metrics": {"factual_accuracy": 1.0, "reflective_accuracy": 1.0},
}


def _write_artifacts(records, tmp_path, **overrides):
    kwargs = dict(
        profile=AblationRunProfile(),
        seeds=[42],
        conditions=["baseline"],
        records=records,
        baseline_ref=_BASELINE_REF,
        command="test-command",
        json_out=tmp_path / "results.json",
        markdown_out=tmp_path / "results.md",
    )
    kwargs.update(overrides)
    return write_ablation_artifacts(**kwargs), kwargs["json_out"], kwargs["markdown_out"]


def _fake_record(condition: str, seed: int, sim_id: str):
    from mirofish_backend.diagnostics.arc11_ablation import AblationRunRecord

    return AblationRunRecord(
        condition=condition,
        seed=seed,
        simulation_id=sim_id,
        wall_clock_seconds=123.0,
        diagnostics={"some": "diag"},
        cost={"wall_clock_seconds": 123.0},
        dispersion={},
        metrics={"factual_accuracy": 1.0},
        deltas_vs_baseline={},
    )


def test_write_ablation_artifacts_creates_json_and_markdown(tmp_path) -> None:
    records = [_fake_record("baseline", 42, "sim-a")]
    payload, json_out, md_out = _write_artifacts(records, tmp_path)
    assert json_out.is_file()
    assert md_out.is_file()
    assert payload["runs"][0]["simulation_id"] == "sim-a"


def test_load_existing_records_missing_file_returns_empty(tmp_path) -> None:
    assert load_existing_records(tmp_path / "nope.json") == []


def test_load_existing_records_round_trips_condition_and_seed(tmp_path) -> None:
    records = [
        _fake_record("baseline", 42, "sim-a"),
        _fake_record("baseline", 43, "sim-b"),
    ]
    _payload, json_out, _md = _write_artifacts(records, tmp_path)

    loaded = load_existing_records(json_out)
    assert {(r.condition, r.seed) for r in loaded} == {("baseline", 42), ("baseline", 43)}
    assert {r.simulation_id for r in loaded} == {"sim-a", "sim-b"}


def test_load_existing_records_handles_malformed_json(tmp_path) -> None:
    bad = tmp_path / "results.json"
    bad.write_text("{not valid json", encoding="utf-8")
    assert load_existing_records(bad) == []


def test_resume_pending_skips_completed_condition_seed_pairs(tmp_path) -> None:
    """Mirrors the skip-logic in _main_async without needing a live run."""
    existing = [
        _fake_record("baseline", 42, "sim-a"),
        _fake_record("baseline", 43, "sim-b"),
        _fake_record("baseline", 44, "sim-c"),
    ]
    _payload, json_out, _md = _write_artifacts(existing, tmp_path)

    loaded = load_existing_records(json_out)
    done = {(r.condition, r.seed) for r in loaded}
    all_pairs = [("baseline", s) for s in (42, 43, 44)] + [("+importance", s) for s in (42, 43, 44)]
    pending = [p for p in all_pairs if p not in done]

    assert pending == [("+importance", 42), ("+importance", 43), ("+importance", 44)]
