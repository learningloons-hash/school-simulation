# M-RENAME closeout (builder pass)

## 1. Branch

- **Base (post-#16 `main`):** `161cbacde3ca933c91d756f16e008eddea2ba7b0`
- **Working branch:** the M-RENAME branch (see [PR #18](https://github.com/learningloons-hash/school-simulation/pull/18))
- **Tip SHA:** `0d3c0bf4f645ee44bde02e40e23111f06c7310d4`

## 2. Grep

| | Files | Lines |
|--|------:|------:|
| Start (`main` @ `161cbac`) | 221 | 1047 |
| End (tracked, at tip) | 17 | 45 |

**Leftover hits:** documented by path and line number only below. For category labels (attribution vs legacy fallback vs study artifact), see [`docs/research/M_RENAME_SPEC.md`](../research/M_RENAME_SPEC.md) §6 and [`HANDOFF_SENNA_M_RENAME.md`](../handoffs/HANDOFF_SENNA_M_RENAME.md).

- `README.md:11`
- `NOTICE:7`
- `backend/pyproject.toml:29`
- `backend/src/senna_backend/_deprecated_cli.py:12`
- `backend/src/senna_backend/config.py:117`
- `backend/.env.example:51`
- `scripts/agent_ask_demo.py:26`
- `scripts/agent_ask_demo.py:29`
- `scripts/sstrf_scoring_evidence.py:29`
- `scripts/sstrf_scoring_evidence.py:30`
- `docs/research/PREREG_SSTRF_RQ1_V2.md` (lines 53, 60, 90, 104)
- `docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md:5`
- `docs/diagnostics/ARC12_PLATFORM_FREEZE.json:17`
- `docs/diagnostics/ciepss_school_b_provenance.json:5`
- `docs/diagnostics/sq_reading_culture_provenance.json:4`
- `docs/diagnostics/sq_reading_culture_shock_provenance.json:4`
- `docs/diagnostics/sq_reading_culture_adverse_provenance.json:4`
- `docs/diagnostics/sq_reading_culture_adverse_shock_provenance.json:4`
- `docs/research/M_RENAME_SPEC.md` (milestone spec; extra allowlist)

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
- `npx tsc --noEmit` — fails with pre-existing `src/components/Sparkline.tsx` TS2322 (SVG `title` prop); **same on `main` @ `161cbac`**; not introduced by M-RENAME
- `GET /health` @ `:8100` → `{"status":"healthy","service":"senna-backend"}`

## 5. LICENSE / data

- `LICENSE` — unchanged (`git diff main -- LICENSE` empty)
- No secrets, SQLite DBs, transcripts, or runtime exports committed

## 6. Notes for architect

- Independent review still required before merge.
- Package move used `git mv`; `git log --follow` on `backend/src/senna_backend/main.py` preserves history. A plain `git diff main` may not show all paths as renames unless similarity is raised (e.g. `git diff -M50% main...HEAD`).
