# senna-iter-55 — Study-Scale Rehearsal

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC12.md`](../handoffs/HANDOFF_SENNA_ARC12.md) §2
**Arc:** 12 — Freeze and Study Readiness
**Date:** 2026-08-25
**Status:** Iteration scope **CLOSED** (Parts A–B + this closeout). **RQ2 deferred.** GM-F mechanism-defaults ruling **still pending** (interim iter-53 frozen flags used for all runs).

---

## What iter-55 delivered

First time Senna ran at study-shaped configuration: `ciepss_school_b`, 8 agents, 15–20 rounds, Anthropic tier, documented CIEPSS network CSV (not synthetic chain).

| Part | Commit | Deliverable |
|------|--------|-------------|
| A — Harness | `e093caa` | `run_arc12_study_rehearsal.py`, `load_documented_network_csv`, CI tests |
| B — RQ1 live runs | `e4f37fd` | `docs/diagnostics/arc12_study_rehearsal_results.{json,md}` |

Standing constraint honoured: mechanics only — no reading, citing, or scoring substantive transcript content.

---

## Part A — Study rehearsal harness (`e093caa`)

**Goal:** Build the execution path for study-scale rehearsal without live Anthropic runs in Part A.

**Shipped:**

- `backend/src/mirofish_backend/diagnostics/arc12_study_rehearsal.py` — documented network loader, mechanics extraction (tokens by round, QA counts, dispersion, provenance, `group_addressed_proportion`).
- `scripts/run_arc12_study_rehearsal.py` — RQ1 matrix CLI, `--skip-rq2`, requires seeded `ciepss_school_b`, interim mechanism-flags banner.
- `backend/tests/test_senna_iter55_study_rehearsal.py` — 4 CI tests; stub run asserts `config_snapshot.network_csv_applied`.

**Network:** Loads `docs/research/fixtures/ciepss_school_b_network.csv` from study repo checkout; validates endpoints against `{persona_id}_{slot:03d}` run agent ids. **Does not synthesise a chain.**

**Interim config (iter-54 → iter-55 gate):** All memory mechanism flags OFF per iter-53 frozen defaults until GM-F rules otherwise.

**CI:** 4/4 iter-55 tests; full suite 421 passed at Part A commit.

---

## Part B — RQ1 live runs (`e4f37fd`)

**Matrix (exactly as specced):**

| Config | Rounds | Seeds | Runs |
|--------|--------|-------|------|
| RQ1-15 | 15 | 42, 43, 44 | 3 |
| RQ1-20 | 20 | 42, 43, 44 | 3 |

**Total: 6 runs.** Scenario `ciepss_school_b`, 8 agents, Anthropic tier, documented network, `--skip-rq2`.

### QA

- **6/6** terminal `completed`
- **0** `[LLM error]` transcript entries
- **0** context-length failures
- **Total cost:** US$15.90 | **Wall-clock:** ~900 s (~15 min) | **Input tokens:** ~4.25M

**Env note:** `unset ANTHROPIC_API_KEY` before run so `backend/.env` loaded correctly (same shadowing issue as iter-54 Part B).

### Simulation IDs

| Label | Seed | Simulation ID |
|-------|------|---------------|
| RQ1-15 | 42 | `8c6d1ec1968348e4b2a3b14b008d8652` |
| RQ1-15 | 43 | `5e7d44a5da1d47cfb9a6dc7d2a590876` |
| RQ1-15 | 44 | `2f995f368c814d0e9b142f6c689bd720` |
| RQ1-20 | 42 | `fa54ad08d90a459ca352fb6d8aaf9dff` |
| RQ1-20 | 43 | `a91dcb4cd3f545ab9f2c96fcaeab7de2` |
| RQ1-20 | 44 | `5332c81e67f3402f9a11f35c68db9072` |

Full mechanics table: [`docs/diagnostics/ARC12_STUDY_REHEARSAL_RESULTS.md`](../diagnostics/ARC12_STUDY_REHEARSAL_RESULTS.md)

---

## ARC12 §2 findings (study rehearsal)

Mechanics-only synthesis from Part B results. This is the first evidence at **8 agents / 15–20 rounds / Anthropic / documented network / `ciepss_school_b`**.

### 1. Context growth

Per-run input tokens grow from **~3,446 (round 1)** to **~62–90k (final round)**. RQ1-20 final-round input per seed: 90,107 / 87,941 / 81,910. **No context-length failures** at this configuration — but round-20 per-round input is ~26× round 1 and is the primary scale risk if rounds or agent count increase.

### 2. `peer_context_max_chars` / `working_memory_last_k`

All runs used Arc 1 defaults from `config_snapshot`: **`peer_context_max_chars=1200`**, **`working_memory_last_k=2`**. Settings remain active (not overridden) but **cumulative transcript/history dominates** prompt growth — peer snippet size is a small fraction of total context at this scale.

### 3. `group_addressed_proportion`

**0.25** on all six runs — consistent with network-bounded visibility on the documented CIEPSS graph (broadcast turns are one quarter of total).

### 4. State-extraction provenance

All LLM turns recorded **`state_update_source=model_parsed`** (120 turns for 15-round runs; 160 for 20-round). No repair/heuristic fallback observed.

### 5. Dispersion on study profile

Final-round **support stdev: 0.017–0.071** across runs — non-zero on the 8-agent study profile. Contrast with near-zero ablation baseline on the 3-agent toy profile (iter-54 individuation report). Study-scale individuation **exists mechanically**; proposition-level testability remains a GM-F / scoring question, not settled here.

### 6. Likert / round machinery

`likert_self_report_enabled=false` on scenario — **not exercised**. `round_outcomes` present for all 20 rounds on sample check — round completion machinery **intact**. No structural failures detected.

### 7. Memory context budget (iter-56 flag)

`memory_exclusion_breakdown.char_budget_truncated`: **0–6** across six runs (not zero on all 15-round cells; up to 6 on some seeds). Low absolute count vs hundreds of `included_clean` inclusions, but non-zero truncation at study scale — **flag for iter-56** to review `rag_max_inject_chars` / memory char budget if mechanisms are ever enabled.

---

## RQ2 deferral

**Not run.** `--skip-rq2` on all Part B invocations.

RQ2 requires ~20 documented actors plus synthetic remainder. No platform scenario fixture exists today. Deferred pending **Lee (2020) case** access per ARC12 §7. Without it, RQ2 would run on a smaller documented roster plus synthetic remainder — defensible but weaker than the proposal implies.

Re-run with `--skip-rq2` removed when study-repo RQ2 fixture and scenario exist.

---

## iter-56 handoff notes (ARC12 §3)

iter-55 rehearsal runs are the **calibration input** for iter-56:

1. **Convergence threshold** — calibrate stopping rule against RQ1-15/20 runs; document reasoning (uncalibrated threshold either never fires or fires in round three).
2. **Cost table at study configuration** — publish measured table from these six runs (RQ1: 8 agents × 15/20 rounds, Anthropic, flags off); supersedes Phase C pilot figures.
3. **`PROVIDER_PRICE_MAP` per-model resolution** — generic $3/$15 Anthropic bucket is not acceptable for funder reporting; resolve `pricing_key` per model id (Haiku 4.5, Opus 5 at minimum).
4. **Memory char budget** — review `char_budget_truncated` counts from §2 finding 7 if memory mechanisms enter iter-56+ scope.

---

## Commits

| Part | Commit |
|------|--------|
| A — Harness | `e093caa` |
| B — RQ1 results | `e4f37fd` |
| Closeout | *(this commit)* |

---

## iter-55 → iter-56 gate (ARC12 §8)

| Condition | Status |
|-----------|--------|
| Study-scale rehearsal completes | ✓ 6/6 RQ1 runs |
| No context-length failures | ✓ |

**Gate passed for iter-56.** GM-F mechanism-defaults ruling remains open (does not block iter-56 housekeeping per ARC12 §3 scope).

---

## Is iter-55 complete?

**Build scope: yes.** Harness built, RQ1 executed, results committed, this closeout delivered.

**RQ2: explicitly deferred** — not a build failure.

**Arc 12 complete: no.** iter-55 is the second of five Arc 12 iterations (`54`–`58`). Next: **iter-56** (calibration, cost table, price map).
