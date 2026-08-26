# Handoff to Architect

**Ritual:** Builder fills this file when work is **complete** (tests pass, committed). Architect reviews against [`handoff-to-builder.md`](./handoff-to-builder.md) and posts verdict in chat.

**Status:** Ready for review — `sstrf-validity-v2` Part D harness complete; live judge runs pending Mark/CLI.

---

## Builder report

| Field | Value |
|-------|--------|
| **Task** | `sstrf-validity-v2` Part D — scoring wired to validity manifest |
| **Branch** | `main` |
| **Commit** | `17c15a2` |
| **Verification** | `cd backend && uv run pytest tests/test_sstrf_validity_v2_scoring.py tests/test_sstrf_rq1_scoring.py -q` → **60 passed** |

### Delivered

1. **`scripts/run_sstrf_validity_scoring.py`** — validity-v2 scoring pipeline:
   - `--run-calibration --execute-judge-calls` (gpt-4o gate)
   - `--score-all-trials --execute-judge-calls`
   - `--prepare-adjudication` → tier2 drift packets for Mark
   - `--import-human-scores` → `--finalize` → `validity_v2_scoring_manifest.json`
2. **`sstrf_scoring_evidence.py`** — validity manifest loaders, fixed trial-A…J mapping, tier2/stage1 validity builders
3. **`backend/src/mirofish_backend/diagnostics/sstrf_validity_v2_scoring.py`** — attach scoring block to validity manifest on finalize
4. **`backend/tests/test_sstrf_validity_v2_scoring.py`** — 4 CI tests (mapping, elicitation load, dry-run, instruments)

### Live ops (Mark/CLI — not run autonomously)

From `mirofish-mvp/backend`:

```bash
# 1. Calibration gate (OpenAI gpt-4o)
uv run python ../scripts/run_sstrf_validity_scoring.py --run-calibration --execute-judge-calls

# 2. Score all 10 trials (2 judge passes each)
uv run python ../scripts/run_sstrf_validity_scoring.py --score-all-trials --execute-judge-calls

# 3. Prepare adjudication + tier2 drift packets
uv run python ../scripts/run_sstrf_validity_scoring.py --prepare-adjudication

# 4. After Mark drift-check: import scores then finalize
uv run python ../scripts/run_sstrf_validity_scoring.py --import-human-scores /path/to/mark_scores.json
uv run python ../scripts/run_sstrf_validity_scoring.py --finalize
```

Outputs under `docs/research/runs/ciepss_school_b/validity_v2/scoring/`.

### Notes for Architect

- Validity trial labels are **fixed** (trial-A…J) — no Phase V shuffle.
- SQLite default: `backend/data/mirofish.sqlite` (Part B runs).
- `--finalize` updates `docs/diagnostics/sstrf_validity_v2_manifest.json` with `scoring_harness` block.
- Drift-check import is **Mark-only** per pre-reg — builder cannot finalize without it.
