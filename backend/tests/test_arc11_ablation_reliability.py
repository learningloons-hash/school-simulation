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
    load_dotenv_if_present,
    run_ablation_preflight,
    run_diagnostics_with_retry,
)

from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID  # noqa: E402


class _FakeSettings:
    lmstudio_base_url = "http://127.0.0.1:1234/v1"
    lmstudio_model = "google/gemma-4-26b-a4b"
    embedding_model = ""
    llm_provider = "lmstudio"
    sqlite_path = ":memory:"


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
