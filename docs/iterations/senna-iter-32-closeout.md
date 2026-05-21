# Senna iter-32 closeout — Capabilities + Frontend Profile Selection (Arc 7)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](../handoffs/HANDOFF_SENNA_ARC7.md) **`## senna-iter-32`**.  
**Date:** 2026-05-19

## Shipped

### Backend

- **`llm/model_profiles.py`** — `profile_capability_dict`, `build_model_profiles_capabilities` (profiles + `hybrid_routing`).
- **`api/capabilities.py`** — `model_profiles` block on `GET /capabilities` / `build_capabilities_dict()`.

### Frontend

- **`lib/api.ts`** — `ModelProfileCapability`, `modelChoicesFromCapabilities`, `modelChoiceToRunRequest`, `FALLBACK_MODEL_CHOICES`; `StartSimulationRequest.model_profile_id`.
- **`App.tsx`** — loads capabilities on mount; AI model dropdown from profile data; sends `model_profile_id` + `llm_provider` for profile picks, `llm_provider=hybrid` for mixed; falls back to hardcoded choices if fetch fails.

### Tests

- **`tests/test_model_profiles.py`** — capabilities block shape and default flags.

## Behavior

| UI choice | Request body |
|-----------|----------------|
| Server default | (omit both) |
| Local model / Claude | `model_profile_id` + matching `llm_provider` |
| Mixed local + Claude | `llm_provider: hybrid` |
| Capabilities fetch fails | Legacy `llm_provider` values only (no `model_profile_id`) |

## Verification

- `uv run pytest` (from `backend/`): **219 passed, 1 skipped**
- `npm run build` (from `frontend/`): **PASS**

## Next

**senna-iter-33** — data-driven routing policies (`local_only`, `frontier_only`, `hybrid_first_turn`).
