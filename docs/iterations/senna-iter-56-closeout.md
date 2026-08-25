# senna-iter-56 — Calibration, Cost, and Price Map

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC12.md`](../handoffs/HANDOFF_SENNA_ARC12.md) §3
**Arc:** 12 — Freeze and Study Readiness
**Date:** 2026-08-25
**Status:** Iteration scope **CLOSED** (Parts A–B + this closeout). **Arc 12 not complete** — iter-57 (scoring) and iter-58 (pre-reg freeze) remain. GM-F mechanism-defaults ruling **still pending**.

---

## What iter-56 delivered

Housekeeping from iter-55 RQ1 rehearsal data: per-model billing, convergence calibration, and a funder-facing cost table at study configuration. No new simulation runs.

| Part | Commit | Deliverable |
|------|--------|-------------|
| A — Price map | `866c992` | Per-model `PROVIDER_PRICE_MAP`, `resolve_anthropic_pricing_key`, profile wiring, 7 tests |
| B — Diagnostics | `3a19c11` | [`ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md), [`ARC12_STUDY_COST_TABLE.md`](../diagnostics/ARC12_STUDY_COST_TABLE.md) |

Standing constraint honoured: iter-56 docs analyse **mechanics only** from iter-55 runs — no substantive transcript reading, citing, or scoring.

---

## Part A — Per-model price map (`866c992`)

**Goal:** Stop billing every Anthropic model at the generic $3/$15 Sonnet-tier bucket.

**Shipped:**

- **`backend/src/mirofish_backend/simulation/economics.py`**
  - Granular keys: `anthropic_haiku_3_5`, `anthropic_haiku_4_5`, `anthropic_sonnet`, `anthropic_opus_4`, `anthropic_opus_5`
  - Generic `anthropic` retained as Sonnet-tier fallback for unknown model ids
  - `PRICE_MAP_DATE` → `2026-08-25`
  - Env overrides (`ANTHROPIC_*_PRICE_PER_MTOK`) apply only to generic fallback; granular keys use map defaults
  - `resolve_billing_provider_key` accepts `effective_model` for per-turn Anthropic billing

- **`backend/src/mirofish_backend/llm/model_profiles.py`**
  - `resolve_anthropic_pricing_key(model_id)` — Haiku / Sonnet / Opus resolution from model id string
  - `anthropic_default` sets `pricing_key` from `settings.anthropic_model`

- **Tests:** `backend/tests/test_senna_iter56_price_map.py` — 7 cases (Haiku 4.5, Opus 5, Opus 4 legacy, cost differential, unknown fallback, profile wiring, legacy provider path). Updated iter-29 / arc8 economics tests for default Haiku 3.5 rates.

**CI:** 428 passed, 2 skipped at Part A commit.

---

## Part B — Convergence calibration + study cost table (`3a19c11`)

**Goal:** Publish two diagnostics docs derived from iter-55 RQ1 rehearsal — documentation only, no live runs.

### Convergence calibration

[`docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md)

- Stopping rule documented: mean abs Δ across `support_level` / `resistance_level` / `workload_stress`; **`convergence_patience = 2`**; threshold **optional** (no API default — omit to run full horizon)
- Full `convergence_delta` by round for all six iter-55 runs (source: `global_state_snapshots` / export bundles; iter-55 runs had **no** `convergence_threshold` set)
- Counterfactual analysis:
  - **τ = 0.05** (integration-test value) → **round 3** on all six runs — **rejected** (false early stop during initial adjustment)
  - **τ = 0.02** → **round 8** uniformly across all seeds and both RQ1-15 / RQ1-20 configs
- **Recommendation:** `convergence_threshold = 0.02`, `convergence_patience = 2` for pre-reg / study runs

### Study cost table

[`docs/diagnostics/ARC12_STUDY_COST_TABLE.md`](../diagnostics/ARC12_STUDY_COST_TABLE.md)

- Per-run table: RQ1-15 and RQ1-20 × seeds 42/43/44 — tokens, cost, wall-clock, cost/round
- **Grand total:** US$**15.90** / ~899 s / 4.25M input tokens (6 runs, as recorded at run time)
- **Means:** RQ1-15 ≈ $2.00/run; RQ1-20 ≈ $3.30/run
- Config snapshot: `ciepss_school_b`, 8 agents, Anthropic Haiku 4.5, documented network, all mechanism flags **off** (interim)
- **Pricing footnote:** iter-55 costs used generic $3/$15 bucket; Haiku 4.5 list-rate retroactive estimate ≈ **$5.30** total (~67% lower) — future runs use Part A per-model map
- **RQ2:** explicitly deferred — no invented numbers
- Supersedes Phase C pilot figures (8 actors × **6** rounds)

---

## ARC12 §3 definition of done

| Item | Status | Evidence |
|------|--------|----------|
| Calibrated convergence threshold documented with reasoning | ✓ | [`ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md) — τ = 0.02 |
| Cost table published at study configuration | ✓ | [`ARC12_STUDY_COST_TABLE.md`](../diagnostics/ARC12_STUDY_COST_TABLE.md) |
| `PROVIDER_PRICE_MAP` resolves per model with passing tests | ✓ | Part A `866c992`; 7 iter-56 tests |

**ARC12 §3 DoD: met.**

---

## Carried forward (not iter-56 scope)

- **Memory char budget** — iter-55 flagged `char_budget_truncated` 0–6 on some 15-round cells. Not revisited in iter-56; review if GM-F enables memory mechanisms.
- **GM-F mechanism defaults** — still pending; iter-53 frozen flags (all off) remain interim for cost/convergence calibration inputs.

---

## iter-57 handoff notes (ARC12 §4)

**Scoring system design (D1)** — the deferred decision. Entire criterion designed **once** against the platform as it now stands.

| Role | Responsibility |
|------|----------------|
| **GM-F** | Drafts scoring system: binding propositions (incl. **P5 survival** — compound/hedged proposition scored 1 on 20/20 Phase V judge passes), per-trial and study-level thresholds, calibration set content for iter-43 harness (1-vs-2 discrimination), judge model + fallback chain, blind plausibility protocol + rater panel |
| **Ops (Builder)** | **Platform-measures statement only** — what the platform measures per trial, format, provenance — so GM-F writes criterion against what exists; implement calibration harness content **after** criterion is fixed |

**iter-57 → iter-58 gate:** GM-F delivers scoring system. iter-58 is pre-registration v2 + freeze — **requires Mark's signature** before any study output exists; records platform tag, study-repo fixture hash, model tier, full config snapshot (incl. τ = 0.02), scoring system from iter-57, and fixed seeds distinct from development.

---

## Commits

| Part | Commit |
|------|--------|
| A — Price map | `866c992` |
| B — Diagnostics | `3a19c11` |
| Closeout | *(this commit)* |

---

## iter-56 → iter-57 gate (ARC12 §8)

| Condition | Status |
|-----------|--------|
| Convergence threshold calibrated and documented | ✓ τ = 0.02 |
| Study cost table published | ✓ |
| Per-model price map with tests | ✓ |

**Gate passed for iter-57.** Next: **iter-57** (GM-F drafts scoring; Ops platform-measures statement). **iter-58** blocked on Mark signature + iter-57 scoring delivery.

---

## Is iter-56 complete?

**Build scope: yes.** All three ARC12 §3 items delivered, documented, committed, this closeout written.

**Arc 12 complete: no.** iter-56 is the third of five Arc 12 iterations (`54`–`58`). Next: **iter-57** (scoring system design), then **iter-58** (pre-reg v2 + freeze, Mark signature required).
