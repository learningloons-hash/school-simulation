# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — `sstrf-validity-v2` Part A (simulation harness)

| Field | Value |
|-------|--------|
| **Workstream** | SSTRF RQ1 validity trials (post–Arc 12) |
| **Pre-reg** | [`PREREG_SSTRF_RQ1_V2.md`](../research/PREREG_SSTRF_RQ1_V2.md) — **signed** 2026-08-25 |
| **Freeze** | [`ARC12_PLATFORM_FREEZE.json`](../diagnostics/ARC12_PLATFORM_FREEZE.json) — platform `da906c3`, seeds [`ARC12_STUDY_SEEDS.json`](../diagnostics/ARC12_STUDY_SEEDS.json) |
| **Branch** | `main` at **`da906c3`** for simulation code — freeze binding; doc-only commits after signature are OK |
| **Base** | `1b5ca4c` (signature commit) |
| **Commit** | One commit for Part A only |

### Goal

Build the **validity-trial simulation harness** — ten frozen-config runs (seeds 500–509), manifest for downstream elicitation/scoring. **Part A: harness + CI only — no live Anthropic spend.**

### Frozen run profile (pre-reg §4 — do not deviate)

| Field | Value |
|-------|-------|
| `scenario_id` | `ciepss_school_b` |
| `agent_limit` | 8 |
| `total_rounds` | **20** |
| `model_profile` | Anthropic — `claude-haiku-4-5-20251001` |
| `visibility_policy` | `network_bounded` |
| `sampling_strategy` | `full_census` |
| `network_csv` | study repo `docs/research/fixtures/ciepss_school_b_network.csv` |
| Mechanisms | all **off** |
| `convergence_threshold` | **omit** (null) |
| `rag_enabled` | **false** |
| Seeds | load from `ARC12_STUDY_SEEDS.json` — trial-A…J → 500–509 |

### Required deliverables

1. **`scripts/run_sstrf_validity_trials.py`** — extend [`run_arc12_study_rehearsal.py`](../../scripts/run_arc12_study_rehearsal.py) pattern:
   - Load seeds/labels from `ARC12_STUDY_SEEDS.json`
   - Assert freeze manifest `signature_status == signed` before live runs
   - Assert fixture provenance matches `ciepss_school_b_provenance.json`
   - Pre-flight: scenario seeded, study repo path, `unset ANTHROPIC_API_KEY` pitfall documented (iter-54/55)
   - QA gate: 0 LLM errors, 0 context-length failures (reuse rehearsal helpers)
   - `--dry-run`: validate config + plan, no API calls
   - Output: `docs/diagnostics/sstrf_validity_v2_manifest.json` (trial_label, seed, simulation_id, status, rounds, economics summary — **no substantive transcript in manifest**)

2. **`backend/src/mirofish_backend/diagnostics/sstrf_validity_v2.py`** — shared types/helpers (manifest schema, run plan from seeds file, freeze assertion)

3. **`backend/tests/test_sstrf_validity_v2_harness.py`** — CI with stub LLM:
   - Seeds file → 10-trial plan
   - Freeze config fields match pre-reg
   - Dry-run / manifest write path
   - Stub run reaches `completed` for one trial

4. **Banner** — print frozen config + pre-reg pointer; **not** "mechanics only / interim" (these are validity trials when executed live in Part B)

### Out of scope (Part A)

- Live Anthropic execution of all 10 trials (Part B)
- Elicitation (Part C)
- Judge calibration / scoring (Part D)
- Platform code changes beyond harness + tests
- Changing seeds, pre-reg, or freeze manifest

### Verification

```bash
cd backend && uv run pytest tests/test_sstrf_validity_v2_harness.py -q
```

### Commit

`sstrf-validity-v2` Part A (simulation harness).

---

## Queued — Part B (live simulations)

Execute ten trials via harness; fill manifest with real simulation IDs. **~$33** Anthropic (rehearsal rates). Requires seeded fixture + study repo checkout @ `47013659…`.

```bash
unset ANTHROPIC_API_KEY  # if shell shadows backend/.env
python3 scripts/run_sstrf_validity_trials.py \
  --study-repo-path /path/to/senna-sstrf-study \
  --execute
```

Record total cost/wall-clock in manifest; QA must pass all 10 before Part C.

---

## Queued — Part C (elicitation)

Port from study repo (`senna-sstrf-study` @ fixture commit):

- `scripts/sstrf_elicitation_instruments.py`
- `scripts/sstrf_phase_v_elicitation.py` → adapt as `run_sstrf_validity_elicitation.py`

Run Appendix B/C post-run for each manifest trial; write per-agent JSON under `docs/research/runs/ciepss_school_b/validity_v2/elicitation/`. Update manifest with elicitation paths.

---

## Queued — Part D (scoring)

Wire [`sstrf_rq1_scoring.py`](../../scripts/sstrf_rq1_scoring.py) to validity manifest (not Phase V paths):

1. `--run-calibration` (gpt-4o gate)
2. `--score-all-trials --execute-judge-calls`
3. `--prepare-adjudication` → **Mark drift-check** (tier2 packets) → `--import-human-scores` if needed
4. `--finalize` → `phase_v_scoring_manifest.json` equivalent for v2

Report `study_pass` regardless of outcome per pre-reg §9.

---

## Completed (do not redo)

- Arc 12 (`senna-iter-54`–`58`, pre-reg signed)
- Scoring harness v2 (`177306a`, 56 tests)
