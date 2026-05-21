# Senna iter-34 closeout — Arc 7 Hardening + Migration Checks

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](../handoffs/HANDOFF_SENNA_ARC7.md) **`## senna-iter-34`**.  
**Date:** 2026-05-19

## Shipped

- **`backend/tests/test_senna_arc7_hardening.py`** — compatibility matrix (omitted `llm_provider`, legacy providers, `model_profile_id` profiles); E2E export JSON/ZIP provenance (`effective_provider`, `effective_model`, `effective_profile_id`, tokens, economics, routing/profile `config_snapshot`); hybrid turn routing regression.

## Compatibility verified (tests)

| Request shape | Verified |
|---------------|----------|
| Omitted `llm_provider` | Server default (`lmstudio`) + snapshot + export |
| `llm_provider=lmstudio` / `anthropic` / `hybrid` | Routing policy + snapshot metadata |
| `model_profile_id=local_lmstudio_default` | Local profile path + export |
| `model_profile_id=anthropic_default` | Frontier profile path + export |

## Export / economics verified

- `GET /simulations/{id}` — transcript tokens, economics, effective fields.
- `GET /simulations/{id}/export.json` — `export_version`, `run.economics`, `config_snapshot` routing/profile keys, transcript provenance.
- `GET /simulations/{id}/export.zip` — `agent_turns.csv` includes `effective_provider`, `effective_model`, `effective_profile_id`, token columns.

## Verification

- `uv run pytest` (from `backend/`): **239 passed, 1 skipped**
- `npm run build` (from `frontend/`): **PASS**
- Local LM Studio run: covered by mocked E2E with `local_lmstudio_default` profile (CI has no LM Studio); manual smoke on Mac mini optional.

## Post–GM (PASS_WITH_ISSUES follow-up, 2026-05-19)

- **`llm/model_profiles.py`:** `resolve_run_llm_provider` — when `llm_provider` is omitted, built-in `model_profile_id` infers `lmstudio` or `anthropic` (never `hybrid`); explicit request `llm_provider` still wins.
- **`api/simulations.py`:** `queue_simulation_run` calls resolver before `resolve_run_profiles`.
- **`tests/test_senna_arc7_hardening.py`:** profile-only anthropic/local queue + E2E; explicit `llm_provider` overrides profile regression.
- **`uv run pytest`:** **244 passed, 1 skipped**

## Arc 7

All gates **senna-iter-30**–**34** **PASS** (Cursor Architect, 2026-05-19). GM **PASS_WITH_ISSUES** follow-up — Architect re-review **PASS** (2026-05-19). **Return to GrandMaster for final Arc 7 PASS** before Arc 8.
