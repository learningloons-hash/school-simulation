# Handoff to Architect

**Ritual:** Builder fills this file when work is **complete** (tests pass, committed). Architect reviews against [`handoff-to-builder.md`](./handoff-to-builder.md) and posts verdict in chat.

**Status:** Ready for review — `sstrf-validity-v2` Part A complete.

---

## Builder report

| Field | Value |
|-------|--------|
| **Task** | `sstrf-validity-v2` Part A — simulation harness (dry-run + CI) |
| **Branch** | `main` |
| **Commit** | `c35beca` — `sstrf-validity-v2 Part A (simulation harness)` |
| **Verification** | `cd backend && uv run pytest tests/test_sstrf_validity_v2_harness.py -q` → **6 passed** |

### Delivered

1. **`scripts/run_sstrf_validity_trials.py`** — validity-trial runner extending rehearsal pattern:
   - Loads seeds from `ARC12_STUDY_SEEDS.json` (trial-A…J → 500–509)
   - Asserts signed freeze + fixture provenance match before live runs (`--execute`)
   - Pre-flight: scenario seeded, study repo or inline network CSV
   - QA gate: 0 LLM errors, 0 context-length failures (reused arc12 helpers)
   - `--dry-run` (default): validate + write manifest with `status: planned`
   - `--execute`: queue all ten trials (Part B)
   - Output: `docs/diagnostics/sstrf_validity_v2_manifest.json`
   - Validity-trial banner + ANTHROPIC_API_KEY pitfall documented

2. **`backend/src/mirofish_backend/diagnostics/sstrf_validity_v2.py`** — shared types:
   - `ValidityTrialProfile`, `PREREG_FROZEN_CONFIG`, manifest builders
   - `build_validity_run_plan`, freeze/provenance assertions

3. **`backend/tests/test_sstrf_validity_v2_harness.py`** — 6 CI tests:
   - 10-trial plan from seeds
   - Frozen config matches pre-reg §4
   - Freeze signed + provenance match
   - Dry-run manifest write
   - Stub LLM single-trial `completed`

### Notes for Architect

- CI stub run uses `fsbb_comparator` (3 agents, 2 rounds) for speed; production profile remains `ciepss_school_b` / 8 / 20 per freeze.
- Manifest is written on dry-run (default when neither flag passed); live Part B uses `--execute`.
- No live Anthropic spend in Part A.
