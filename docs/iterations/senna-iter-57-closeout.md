# senna-iter-57 — Scoring System Design (D1)

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC12.md`](../handoffs/HANDOFF_SENNA_ARC12.md) §4
**Arc:** 12 — Freeze and Study Readiness
**Date:** 2026-08-25
**Status:** Iteration scope **CLOSED** (Parts A–B + this closeout). **Arc 12 not complete** — iter-58 (pre-reg v2 + freeze, Mark signature) remains.

---

## What iter-57 delivered

GM-F scoring system v2 designed and implemented in the iter-43 harness pattern. Platform-measures statement corrected the Arc 11 build-rule misread before GM-F delivery.

| Part | Commit | Deliverable |
|------|--------|-------------|
| A — Platform measures | `c727045` | [`ARC12_PLATFORM_MEASURES_STATEMENT.md`](../diagnostics/ARC12_PLATFORM_MEASURES_STATEMENT.md) + §0 correction (in Part B commit) |
| B — Scoring harness v2 | `177306a` | `scripts/sstrf_*.py`, `backend/tests/test_sstrf_rq1_scoring.py` (56 tests), [`SSTRF_RATER_CALIBRATION_SET.md`](../research/SSTRF_RATER_CALIBRATION_SET.md) |

**GM-F delivery:** [`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](../research/SSTRF_RQ1_SCORING_SYSTEM_V2.md) (2026-08-25) — mechanisms **off**, convergence **null**, **20** fixed rounds, per-agent scoring (17 judgements/trial), `gpt-4o` judge primary, study pass **≥8/10**.

---

## Part A — Platform-measures statement (`c727045`)

**Goal:** Tell GM-F what Senna actually measures at study configuration so the scoring criterion is written against platform reality.

**Shipped:**

- Inventory of export v14 measures (orchestrator loop vs post-run diagnostics)
- Gap table: proposition scores via study-repo harness, not orchestrator output
- §0 correction (committed with Part B): build rule ≠ study scoring; correspondence is the study purpose; lexical CIEPSS overlap still prohibited

**Input to GM-F:** Used for v2 scoring system draft. Measures statement §6 still said "blocked until GM-F" at Part A — superseded by Part B delivery; housekeeping deferred to iter-58.

---

## Part B — GM-F scoring harness v2 (`177306a`)

**Goal:** Implement GM-F §10 in the iter-43 harness on product `main` with synthetic fixtures (study-repo `sstrf-local` diverged).

### §10 checklist

| Item | Status | Evidence |
|------|--------|----------|
| Calibration C1–C5 + 2-vs-−1 pairs; gate ≥8/10 + no double-miss | ✓ | 15 gating items; `calibration_gate_passes()` — ≥12/15 both passes + ≤1 miss/proposition; P5 regression test |
| Per-agent shape — 17 judgements/trial | ✓ | `sstrf_scoring_cells.py`; four staff personas + trial-level P2 |
| Rater packet + leakage check | ✓ | `build_rater_payload()`, `assert_rater_payload_clean()`; parent elicitation excluded |
| Two-pass adjudication §5 | ✓ | `sstrf_scoring_adjudication.py` — agree / lower-of-one / human-required |
| Aggregation §2.4 + §3 in harness | ✓ | `trial_passes()`, `study_passes()` |

### Key files

- `scripts/sstrf_scoring_judge.py` — propositions verbatim, `JUDGE_PRIMARY_MODEL = gpt-4o`, calibration items
- `scripts/sstrf_rq1_scoring.py` — CLI harness
- `backend/tests/test_sstrf_rq1_scoring.py` — **56 passed**

**Architect review:** PASS (2026-08-25).

---

## GM-F rulings now frozen for iter-58

| Field | Value | Source |
|-------|-------|--------|
| Mechanisms | All **off** | GM-F v2 §7 |
| Rounds | **20**, fixed | GM-F v2 §8–§9 |
| Convergence threshold | **`null`** (computed descriptively only) | GM-F v2 §8 — overrides iter-56 τ=0.02 recommendation for study runs |
| Study pass | ≥ **8 of 10** trials | GM-F v2 §3 |
| Judge | **`gpt-4o`** primary; no Claude-as-judge | GM-F v2 §5 |
| Scoring evidence | Elicitation + transcripts; staff only for propositions | GM-F v2 §2 |

**Note:** iter-56 documented τ=0.02 for optional early stopping. GM-F §8 explicitly sets `convergence_threshold: null` for the study — record both in pre-reg (calibrated value for future work; study uses fixed 20 rounds).

---

## Carried forward (not iter-57 scope)

- **Study-repo sync** — harness on `main`; live study runs need study-repo merge or pinned import path.
- **`SSTRF_RQ1_SCORING_SYSTEM_V2.md` placement** — GM-F: belongs in study repo; copy/move at iter-58.
- **Practitioner panel** — Mark, longest lead (GM-F §6).
- **RQ2** — deferred; no criterion in v2.
- **Mark signature** — scoring system and pre-reg unsigned until iter-58.

---

## Commits

| Part | Commit |
|------|--------|
| A — Platform measures | `c727045` |
| B — Scoring harness v2 | `177306a` |
| Closeout | *(this commit)* |

---

## iter-57 → iter-58 gate (ARC12 §8)

| Condition | Status |
|-----------|--------|
| GM-F has delivered the scoring system | ✓ `SSTRF_RQ1_SCORING_SYSTEM_V2.md` |
| Ops implemented §10 harness | ✓ `177306a`, 56 tests |

**Gate passed for iter-58.** Next: **pre-registration v2 + platform freeze** — **Mark signature required** before any study output exists.

---

## Is iter-57 complete?

**Build scope: yes.** Platform measures delivered, GM-F criterion implemented, tested, reviewed, this closeout written.

**Arc 12 complete: no.** iter-57 is the fourth of five Arc 12 iterations (`54`–`58`). Next: **iter-58** (pre-reg v2 + freeze, Mark signs).
