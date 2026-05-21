# Senna iter-30 closeout — Generic OpenAI-Compatible Provider (Arc 7)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](../handoffs/HANDOFF_SENNA_ARC7.md) **`## senna-iter-30`**.  
**Date:** 2026-05-19

## Shipped

- **`backend/src/mirofish_backend/llm/openai_compatible_client.py`** — generic `POST …/chat/completions` adapter; `_format_openai_compatible_error_body`; token usage from `prompt_tokens`/`completion_tokens` or `input_tokens`/`output_tokens`.
- **`backend/src/mirofish_backend/llm/lmstudio_client.py`** — thin compatibility shim re-exporting the generic client and error formatter (`_format_lm_studio_error_body` alias).
- **`backend/src/mirofish_backend/llm/router.py`** — local path imports `chat_completion_openai_compatible` from `openai_compatible_client` (not `lmstudio_client`).
- **`backend/tests/test_openai_compatible_client.py`** — error formatting, token aliases, HTTP error detail, `llm_provider=lmstudio` → adapter via `llm_complete`, lmstudio shim re-export.

## Unchanged (per spec)

- `LLM_PROVIDER_VALUES`: still `lmstudio`, `anthropic`, `hybrid`.
- No frontend, model profiles, or new public provider names.
- `rag/embeddings.py` still imports `_format_lm_studio_error_body` from `lmstudio_client` (shim).

## Verification

- `uv run pytest` (from `backend/`): **206 passed, 1 skipped**
- `rg 'openai_compatible_client' backend/src` — `router.py`, new module; `lmstudio_client.py` imports it
- `rg 'chat_completion_openai_compatible' backend/src/mirofish_backend/llm/router.py` — imports from `openai_compatible_client`

## Next

**senna-iter-31** — model profiles (`HANDOFF_SENNA_ARC7.md` § senna-iter-31). Architect PASS before seeding Builder.
