# Senna iter-31 closeout — Model Profiles (Arc 7)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](../handoffs/HANDOFF_SENNA_ARC7.md) **`## senna-iter-31`**.  
**Date:** 2026-05-19

## Shipped

- **`backend/src/mirofish_backend/llm/model_profiles.py`** — `ModelProfile`, built-ins `local_lmstudio_default` / `anthropic_default`, `resolve_run_profiles`, `profile_snapshot_dict`, `model_profile_config_snapshot`, `run_llm_credentials`.
- **`backend/src/mirofish_backend/api/simulations.py`** — optional `model_profile_id` on `SimulationRunRequest`; profile metadata in `config_snapshot`; resolved `lmstudio_model` / `lmstudio_base_url` / `anthropic_model` passed to orchestration.
- **`backend/tests/test_model_profiles.py`** — resolution (no profile, lmstudio, anthropic, hybrid, invalid id), snapshot fields, queue wiring, API 422 for unknown profile.

## Behavior

- Omitted `model_profile_id`: unchanged routing via `llm_provider`; snapshot records resolved built-in profile(s). Hybrid runs include `model_profile_local` + `model_profile_frontier`.
- Explicit `model_profile_id`: selects built-in profile; credentials override the matching leg for the run task.
- Legacy `llm_provider` remains on request and `config_snapshot`.

## Unchanged (per spec)

- No frontend, capabilities block, or data-driven routing policies (iter-32/33).
- `LLM_PROVIDER_VALUES` unchanged.

## Verification

- `uv run pytest` (from `backend/`): **217 passed, 1 skipped**

## Next

**senna-iter-32** — capabilities + frontend profile selector. Architect PASS before seeding Builder.
