# Senna iter-36 closeout — Profile Registry + Model Capability Registry

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](../handoffs/HANDOFF_SENNA_ARC8.md) **`## senna-iter-36`**.  
**Date:** 2026-05-19

## Shipped

- **Profile registry:** Built-ins registered via `@register_builtin_profile` in `llm/model_profiles.py`; `get_builtin_profile` / `list_builtin_profiles` resolve from `_BUILTIN_PROFILE_FACTORIES`. `BUILTIN_PROFILE_IDS` derived from registry keys (stable: `local_lmstudio_default`, `anthropic_default`).
- **Model capabilities:** `ModelCapabilities` dataclass with `context_window`, usage/embeddings/streaming flags, reliability/leakage tiers, `recommended_max_concurrency`. Exposed on `GET /capabilities` as `profiles[].capabilities` and in `config_snapshot` via `profile_snapshot_dict` (includes `is_builtin`).
- **Backward compatibility:** `ModelProfile` keeps `context_window` / `supports_*` properties; Arc 7 resolution and request validation unchanged.

## Files touched

- `backend/src/mirofish_backend/llm/model_profiles.py`
- `backend/tests/test_model_profiles.py`

## Verification

- `uv run pytest` (from `backend/`): **254 passed, 1 skipped**
- Registry IDs match prior built-ins; local + frontier capability rows tested; queue snapshot includes `capabilities` block

## Next

- **senna-iter-37** — commercial OpenAI-compatible profiles (`HANDOFF_SENNA_ARC8.md` § senna-iter-37)
