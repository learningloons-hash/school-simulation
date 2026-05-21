# Senna iter-37 closeout — Commercial OpenAI-Compatible Profiles

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](../handoffs/HANDOFF_SENNA_ARC8.md) **`## senna-iter-37`**.  
**Date:** 2026-05-19

## Shipped

- **Commercial profiles:** `openai_default` and `openrouter_default` registered in `llm/model_profiles.py` with `provider_type=openai_compatible`, settings-driven base URL / model id / `api_key_env`, `pricing_key`, and capability metadata.
- **Settings:** `openai_*` and `openrouter_*` fields on `Settings` (conservative defaults; no account required for tests).
- **Bearer auth:** `chat_completion_openai_compatible(..., api_key=)` adds `Authorization: Bearer` when a key is present; omitted for local LM Studio.
- **Run plumbing:** `run_openai_compatible_api_key()` resolves keys from env; passed through `queue_simulation_run` → orchestrator → `llm_complete`. Profile-only requests infer `llm_provider=lmstudio` for OpenAI-compatible profiles.
- **Capabilities / snapshot:** `/capabilities` lists four built-in profiles with capability blocks; only `api_key_env` names in snapshots (never key values).

## Files touched

- `backend/src/mirofish_backend/config.py`
- `backend/src/mirofish_backend/llm/model_profiles.py`
- `backend/src/mirofish_backend/llm/openai_compatible_client.py`
- `backend/src/mirofish_backend/llm/router.py`
- `backend/src/mirofish_backend/api/simulations.py`
- `backend/src/mirofish_backend/simulation/orchestrator.py`
- `backend/tests/test_model_profiles.py`
- `backend/tests/test_openai_compatible_client.py`

## Verification

- `uv run pytest` (from `backend/`): **261 passed, 1 skipped**
- Mocked tests: commercial profile resolution, capabilities without secrets, Authorization header on/off, router forwards API key

## Next

- **senna-iter-38** — pre-run context and cost checks (`HANDOFF_SENNA_ARC8.md` § senna-iter-38)
