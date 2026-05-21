import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from mirofish_backend.llm import openai_compatible_client
from mirofish_backend.llm.lmstudio_client import (
    _format_lm_studio_error_body,
    chat_completion_openai_compatible as lmstudio_chat_completion,
)
from mirofish_backend.llm.openai_compatible_client import _format_openai_compatible_error_body
from mirofish_backend.llm.router import llm_complete, resolve_effective_provider


def test_format_error_body_parses_openai_json_message() -> None:
    body = json.dumps({"error": {"message": "model not loaded", "type": "invalid_request_error"}})
    assert _format_openai_compatible_error_body(400, body) == "model not loaded"
    assert _format_lm_studio_error_body(400, body) == "model not loaded"


def test_format_error_body_string_error_and_empty() -> None:
    assert _format_openai_compatible_error_body(500, '{"error": "server busy"}') == "server busy"
    assert _format_openai_compatible_error_body(502, "") == "(empty response body, status 502)"
    assert _format_openai_compatible_error_body(503, "plain text failure") == "plain text failure"


@pytest.mark.asyncio
async def test_chat_completion_parses_prompt_and_completion_tokens() -> None:
    payload = {
        "choices": [{"message": {"content": "hello"}}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 3},
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("mirofish_backend.llm.openai_compatible_client.httpx.AsyncClient", return_value=mock_client):
        text, inp, out = await openai_compatible_client.chat_completion_openai_compatible(
            base_url="http://127.0.0.1:1234/v1",
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.2,
            max_tokens=64,
        )

    assert text == "hello"
    assert inp == 12
    assert out == 3


@pytest.mark.asyncio
async def test_chat_completion_parses_input_and_output_token_aliases() -> None:
    payload = {
        "choices": [{"message": {"content": "ok"}}],
        "usage": {"input_tokens": 7, "output_tokens": 2},
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("mirofish_backend.llm.openai_compatible_client.httpx.AsyncClient", return_value=mock_client):
        text, inp, out = await openai_compatible_client.chat_completion_openai_compatible(
            base_url="http://127.0.0.1:1234/v1",
            model="test-model",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.0,
        )

    assert text == "ok"
    assert inp == 7
    assert out == 2


@pytest.mark.asyncio
async def test_chat_completion_http_error_includes_server_message() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.text = json.dumps({"error": {"message": "context length exceeded"}})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("mirofish_backend.llm.openai_compatible_client.httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(RuntimeError, match="context length exceeded"):
            await openai_compatible_client.chat_completion_openai_compatible(
                base_url="http://127.0.0.1:1234/v1",
                model="big-model",
                messages=[{"role": "user", "content": "x"}],
                temperature=0.0,
            )


def test_lmstudio_provider_resolves_to_openai_compatible_path() -> None:
    assert resolve_effective_provider(routing_mode="lmstudio", round_number=1, turn_index=1) == "lmstudio"


@pytest.mark.asyncio
async def test_llm_complete_lmstudio_uses_openai_compatible_adapter() -> None:
    with patch(
        "mirofish_backend.llm.router.chat_completion_openai_compatible",
        new_callable=AsyncMock,
        return_value=("reply", 5, 2),
    ) as mock_chat:
        result = await llm_complete(
            provider="lmstudio",
            messages=[
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "user"},
            ],
            temperature=0.3,
            max_tokens=128,
            lmstudio_base_url="http://127.0.0.1:1234/v1",
            lmstudio_model="local-model",
            anthropic_api_key="",
            anthropic_model="claude-test",
        )

    mock_chat.assert_awaited_once()
    assert result.text == "reply"
    assert result.input_tokens == 5
    assert result.output_tokens == 2


def test_lmstudio_client_reexports_generic_chat_completion() -> None:
    assert lmstudio_chat_completion is openai_compatible_client.chat_completion_openai_compatible


@pytest.mark.asyncio
async def test_chat_completion_sends_bearer_when_api_key_set() -> None:
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("mirofish_backend.llm.openai_compatible_client.httpx.AsyncClient", return_value=mock_client):
        await openai_compatible_client.chat_completion_openai_compatible(
            base_url="https://api.openai.com/v1",
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.0,
            api_key="sk-test-not-real",
        )

    _args, kwargs = mock_client.post.call_args
    headers = kwargs.get("headers") or {}
    assert headers.get("Authorization") == "Bearer sk-test-not-real"


@pytest.mark.asyncio
async def test_chat_completion_omits_auth_header_for_local_lm_studio() -> None:
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": {}}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("mirofish_backend.llm.openai_compatible_client.httpx.AsyncClient", return_value=mock_client):
        await openai_compatible_client.chat_completion_openai_compatible(
            base_url="http://127.0.0.1:1234/v1",
            model="local-model",
            messages=[{"role": "user", "content": "hi"}],
            temperature=0.0,
            api_key=None,
        )

    _args, kwargs = mock_client.post.call_args
    headers = kwargs.get("headers")
    assert headers is None or "Authorization" not in (headers or {})


@pytest.mark.asyncio
async def test_llm_complete_forwards_openai_compatible_api_key() -> None:
    with patch(
        "mirofish_backend.llm.router.chat_completion_openai_compatible",
        new_callable=AsyncMock,
        return_value=("reply", 1, 1),
    ) as mock_chat:
        await llm_complete(
            provider="lmstudio",
            messages=[{"role": "user", "content": "user"}],
            temperature=0.0,
            max_tokens=64,
            lmstudio_base_url="https://api.openai.com/v1",
            lmstudio_model="gpt-4o-mini",
            anthropic_api_key="",
            anthropic_model="unused",
            openai_compatible_api_key="sk-test-not-real",
        )

    assert mock_chat.await_args.kwargs.get("api_key") == "sk-test-not-real"
