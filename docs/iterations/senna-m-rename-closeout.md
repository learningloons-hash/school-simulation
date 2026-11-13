# M-RENAME closeout (builder pass)

## 1. Branch

- **Base (post-#16 `main`):** `161cbacde3ca933c91d756f16e008eddea2ba7b0`
- **Branch:** `m-rename-mirofish` (tip SHA recorded at PR open)

## 2. Grep

| | Files | Lines |
|--|------:|------:|
| Start (`main` @ `161cbac`) | 221 | 1047 |
| End (tracked) | 17 | 22 |

**Leftover hits (allowlisted + legacy):**

- `README.md:11` — MiroFish attribution
- `NOTICE:7` — MiroFish attribution
- `backend/pyproject.toml:29` — deprecated `mirofish-backend` script entry
- `backend/src/senna_backend/_deprecated_cli.py:12` — deprecation message
- `backend/src/senna_backend/config.py:117` — legacy `./data/mirofish.sqlite` fallback
- `backend/.env.example:51` — legacy SQLite comment
- `scripts/agent_ask_demo.py:26,29` — `MIROFISH_BACKEND_URL` fallback
- `scripts/sstrf_scoring_evidence.py:29,30` — legacy sqlite path helper
- `docs/research/PREREG_SSTRF_RQ1_V2.md` — published pre-reg (4 lines)
- `docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md:5` — historical extraction path
- `docs/diagnostics/ARC12_PLATFORM_FREEZE.json` + five `*_provenance.json` — frozen yaml paths

**Extra allowlist (beyond brief):** `docs/research/M_RENAME_SPEC.md` — milestone spec documents grep policy and legacy strings by design.

## 3. Pytest

`cd backend && uv run pytest`: **564 passed, 15 failed, 2 skipped** (matches post-#16 baseline).

Failing nodeids (unchanged):

1. `tests/test_interaction_sample_k.py::test_sample_k_fewer_llm_turns_than_full_robin`
2. `tests/test_iteration12.py::test_effective_provider_and_model_persisted_for_hybrid`
3. `tests/test_iteration12.py::test_stress_many_fake_llm_turns_completes_quickly`
4. `tests/test_iteration23.py::test_mixed_tiers_llm_only_for_one_and_two`
5. `tests/test_iteration25.py::test_network_queued_run_audit_sampling_report_and_node_count`
6. `tests/test_iteration26.py::test_posture_maxvar_queued_run_audit_and_sampling_report`
7. `tests/test_iteration29.py::test_get_simulation_anthropic_provider_positive_estimated_cost`
8. `tests/test_iteration29.py::test_economics_pure_functions`
9. `tests/test_senna_arc8_economics.py::test_resolve_billing_provider_key_by_profile`
10. `tests/test_sstrf_validity_v2_elicitation.py::test_dry_run_elicitation_for_trial_a`
11. `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_updates_validity_manifest`
12. `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_leaves_production_manifest_untouched`
13. `tests/test_sstrf_validity_v2_scoring.py::test_trial_record_from_validity_label_loads_elicitation`
14. `tests/test_sstrf_validity_v2_scoring.py::test_validity_scoring_dry_run_one_trial`
15. `tests/test_state_engine.py::test_state_timeline_and_demographics_are_persisted`

## 4. Frontend / health

- `npm run build` — pass (Vite production build)
- `npx tsc --noEmit` — **same pre-existing failure on `main`:** `src/components/Sparkline.tsx` SVG `title` prop (TS2322)
- `GET /health` @ `:8100` → `{"status":"healthy","service":"senna-backend"}`

## 5. LICENSE / data

- `LICENSE` — unchanged (`git diff main -- LICENSE` empty)
- No secrets, SQLite DBs, transcripts, or runtime exports committed

## 6. Notes for architect

- Independent review still required before merge.
- `git log --follow` on `backend/src/senna_backend/main.py` works after commit (package moved via `git mv`).
