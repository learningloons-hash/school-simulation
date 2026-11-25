# M-DEPS: Dependabot security bumps + bind 127.0.0.1

**Branch:** `m-deps-security`  
**Base:** `main` @ `e605738`  
**Gate:** builder closeout

## Spec (source)

Security dependency bumps (backend `uv.lock`, frontend `package-lock.json`) and default dev bind `127.0.0.1` instead of `0.0.0.0`, with existing env/CLI overrides preserved.

## Changes

### Backend (`backend/pyproject.toml`, `backend/uv.lock`)

- Pinned `fastapi==0.135.3` (spec: hold FastAPI minor; starlette floor upgrade must not pull a newer FastAPI); constrained `starlette>=1.3.1,<1.4`.
- Raised floors: `pydantic-settings>=2.14.2`, `pytest>=9.0.3` (dev).
- `uv lock --upgrade-package` for: anyio, certifi, starlette, idna, pydantic-settings, pytest.

### Frontend (`frontend/package.json`, `frontend/package-lock.json`)

- `vite` `^5.4.14` → `^6.4.6`; `@vitejs/plugin-react` pinned `4.7.0`.
- Fresh lockfile via `npm install` (transitive bumps only; no Vite 7/8).
- `vite.config.ts` dev `host` → `127.0.0.1`; preview script host → `127.0.0.1`.

### Local-only binding

- `senna_backend.config.Settings.host` default `0.0.0.0` → `127.0.0.1` (`HOST` env / `run_dev()` unchanged).
- Docs: `docs/SESSION_STATE.md`, `docs/NEW_LAPTOP_PLATFORM_SETUP.md`; historical `HANDOFF_TO_OPUS_2026-04-06.md` table left period-accurate with M-DEPS footnote.

## Resolved versions

| Package | Resolved |
|---------|----------|
| anyio | 4.14.2 |
| certifi | 2026.11.20 |
| starlette | 1.3.1 |
| fastapi | 0.135.3 |
| idna | 3.20 |
| pydantic-settings | 2.16.3 |
| pytest | 9.2.0 |
| vite | 6.4.6 |
| @vitejs/plugin-react | 4.7.0 |
| @babel/core | 7.29.13 |
| browserslist | 4.29.6 |
| nanoid | 3.3.20 |
| postcss | 8.5.33 |
| source-map-js | 1.2.4 |
| baseline-browser-mapping | 2.11.39 |

## Test results

### Backend `uv run pytest` (from `backend/`)

| Ref | Passed | Failed | Skipped |
|-----|--------|--------|---------|
| `main` (pre-change) | 673 | 15 | 2 |
| `m-deps-security` | 673 | 15 | 2 |

**Warnings:** Pytest summary **3** on branch vs **1** on `main` (pre-change): Starlette 1.3 `TestClient` adds a `StarletteDeprecationWarning` (httpx2 migration); not a failure — deferred.

Same failing tests (pre-existing; not fixed in this milestone):

- `tests/test_interaction_sample_k.py::test_sample_k_fewer_llm_turns_than_full_robin`
- `tests/test_iteration12.py::test_effective_provider_and_model_persisted_for_hybrid`
- `tests/test_iteration12.py::test_stress_many_fake_llm_turns_completes_quickly`
- `tests/test_iteration23.py::test_mixed_tiers_llm_only_for_one_and_two`
- `tests/test_iteration25.py::test_network_queued_run_audit_sampling_report_and_node_count`
- `tests/test_iteration26.py::test_posture_maxvar_queued_run_audit_and_sampling_report`
- `tests/test_iteration29.py::test_get_simulation_anthropic_provider_positive_estimated_cost`
- `tests/test_iteration29.py::test_economics_pure_functions`
- `tests/test_senna_arc8_economics.py::test_resolve_billing_provider_key_by_profile`
- `tests/test_sstrf_validity_v2_elicitation.py::test_dry_run_elicitation_for_trial_a`
- `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_updates_validity_manifest`
- `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_leaves_production_manifest_untouched`
- `tests/test_sstrf_validity_v2_scoring.py::test_trial_record_from_validity_label_loads_elicitation`
- `tests/test_sstrf_validity_v2_scoring.py::test_validity_scoring_dry_run_one_trial`
- `tests/test_state_engine.py::test_state_timeline_and_demographics_are_persisted`

### Frontend

- `npm ci` + `npx tsc --noEmit`: only pre-existing `Sparkline.tsx` `title` prop error.
- `npm run build`: OK (Vite 6.4.6).

## Audit summaries

### npm audit

**Before** (`main`, Vite 5 lock; `npm ci` + `npm audit` on `main` lock): **8 vulnerabilities** (1 low, 2 moderate, 5 high) — `@babel/core` moderate; `baseline-browser-mapping` moderate; `browserslist` high; `esbuild` / `vite` moderate (dev SSRF); `nanoid` high; `postcss` high; `source-map-js` high (GHSA-68fv-2mgg-jv7q).

**After** (`m-deps-security`): `found 0 vulnerabilities`.

### pip-audit (`uvx pip-audit` on resolved backend env)

**Before:** No known vulnerabilities found (starlette 1.0.0 / older certifi still flagged by GitHub advisory DB).

**After:** No known vulnerabilities found (starlette 1.3.1, certifi 2026.11.20, anyio 4.14.2).

## Workarounds

- No `vite.config.ts` API changes required for Vite 6 beyond the host default; production build unchanged.
- Explicit `starlette` constraint in `pyproject.toml` so FastAPI 0.135.3 resolves to Starlette 1.3.x without bumping FastAPI minor.