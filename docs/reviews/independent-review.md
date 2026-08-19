# Independent Review: Senna Arc 10 — Memory Diagnostics

Date: 2026-08-19  
Branch: `main`  
Reviewed commits: `e644a28`, `1bdb199`, `c890c2a`, `5a23fbc`, `f572860`  
Scope: platform memory/context diagnostics only; this is not a CIEPSS validity review.

## Verdict

| Gate | Verdict | Reason |
|---|---|---|
| senna-iter-45 | **FAIL** | Inclusion logging is not behavior-isolated, can mislabel prompt inclusion, and its integration gate remains race-dependent. |
| senna-iter-46 | **FAIL** | Vendored MemBench fixtures omit the evidence targeted by their QAs, so scores partly measure guessing rather than memory. |
| senna-iter-47 | **FAIL** | Unparseable judge output silently becomes a substantive zero; interrupted runs can also leave partial data accepted as complete. |
| senna-iter-48 | **FAIL** | The mixed verdict is arithmetically honest, but it is built on invalid fixtures and an unavailable canonical run, so the committed baseline is not independently reproducible. |
| **Arc 10 overall** | **FAIL** | Core scaffolding is useful, but the baseline is not yet reliable enough to direct Arc 11 architecture work. |

## Blockers

### B1 — Iter-45 gate and same-round context are race-dependent

The gate fix forces Tier 1 but still uses a one-round parallel run. Every speaker can query before any peer turn is persisted, producing a legitimately empty log; alternatively, scheduling can expose a same-round turn. Repeating the focused test produced one pass followed by failure at `assert len(log) > 0`.

- `backend/tests/test_senna_iter45_memory_context.py:187-215`
- `backend/tests/simulation_helpers.py:26-50`
- `backend/src/mirofish_backend/simulation/orchestrator.py:790-868`

Fix: make the integration test use at least two rounds and assert deterministic prior-round candidates. Define whether same-round turns may ever enter context under parallel execution and enforce that contract.

### B2 — Instrumentation can change behavior and does not exactly describe the prompt

Instrumentation adds a 10,000-row candidate read and awaited SQLite batch write before prompt construction/LLM execution. A logging failure can fail the turn, and added latency can alter concurrent visibility. It is always enabled and can grow toward quadratic row volume on large runs.

Self turns are marked visible/included before being removed from `recent_interactions`; only a separate, shorter `prior_agent_memory` window is actually placed in the prompt. Older self turns can therefore be reported as included when absent. The label `network_filtered` also covers every non-broadcast visibility policy, not only network filtering.

- `backend/src/mirofish_backend/simulation/orchestrator.py:812-868`
- `backend/src/mirofish_backend/simulation/memory_context.py:26-93`
- `backend/src/mirofish_backend/simulation/interaction_policy.py:336-372`

Fix: derive records from the final prompt inputs, distinguish visibility-policy reasons, and make diagnostic persistence non-fatal or explicitly gated. Add scale/row-volume coverage.

### B3 — MemBench fixtures remove the answer evidence

The factual participation fixture retains steps 0–3 while its QA targets step 119; factual observation retains four steps while targeting step 10. Both reflective fixtures also omit at least one declared target step. The canonical `memory_match` baseline therefore compares cells with systematically different evidence availability.

- `backend/tests/fixtures/membench/participation_factual.json:8-43`
- `backend/tests/fixtures/membench/observation_factual.json:8-28`
- `backend/tests/fixtures/membench/participation_reflective.json:8-51`
- `backend/tests/fixtures/membench/observation_reflective.json:8-39`
- `backend/tests/fixtures/membench/README.md:13-24`

Fix: vendor complete trajectories or a minimal evidence-preserving subset containing every `target_step_id`; add a test proving each QA's supporting target survives fixture trimming.

### B4 — Judge parse failure silently becomes evidence of incapability

When no score can be parsed or inferred, `resolve_judge_score()` returns `0, "keyword_fallback"`. Baseline means include that zero without a parse-quality gate. An empty/error response is therefore indistinguishable in the headline result from a genuine rubric score of inadequate.

- `backend/src/mirofish_backend/diagnostics/judge_score_parse.py:82-127`
- `backend/src/mirofish_backend/diagnostics/arc10_baseline.py:32-39`

Fix: represent unscorable output as invalid/missing, retry or fail the diagnostic, and report parse-source counts. Do not average invalid judge rows.

### B5 — Partial interviews can be accepted as complete

Each response is committed before its judge score. Interruption can leave an unmatched response, while the combined runner accepts any non-zero response count and summarizes whatever rows exist.

- `backend/src/mirofish_backend/diagnostics/architectural_interview.py:467-560`
- `scripts/run_arc10_diagnostics.py:87-113`

Fix: validate exact `agents × 5` response and score counts with one-to-one IDs before baseline generation; use per-item transactions or resumable completeness checks.

### B6 — Canonical baseline cannot be reproduced from a fresh checkout

`ARC10_BASELINE.md` identifies simulation `9296236e203f40e7b46dd29bc0823730`, but no SQLite database or canonical export containing that run is committed. The runner requires that simulation in a local DB. Recorded inputs also omit model profiles, temperature, token cap, code commit and fixture hashes.

- `docs/diagnostics/ARC10_BASELINE.md:3-7`
- `scripts/run_arc10_diagnostics.py:56-73,120-126`

Fix: commit a sanitized canonical input bundle/diagnostic JSON and complete provenance, then add a regression that regenerates the checked-in baseline body from those committed inputs.

## Warnings

1. MemBench scoring is a letter comparison, not a Senna rubric, but it uppercases/strips answers rather than using upstream exact equality (`scripts/membench_adapter.py:130-132`).
2. `ground_truth` is passed to the evaluated answer callback and an oracle mode is CLI-selectable; remove ground truth from the normal agent interface (`scripts/membench_adapter.py:26-37,186-195,304-315`).
3. Tier-3 turns correctly have no LLM prompt, but reports lack a coverage denominator and no regression test asserts this explicit exclusion.
4. Fixture output records a machine-specific absolute directory instead of portable fixture identifiers/hashes (`scripts/membench_adapter.py:320-323`).
5. The closeouts link to an Arc 10 handoff that is not committed on `main`; the current lowercase handoff file is untracked.
6. Full suite emits two unregistered `pytest.mark.manual` warnings.

## What Passed

- Four implementation iterations are separate commits.
- `agent_context_inclusion`, export `memory_context_log`, and additive export versions 10/11 are present.
- Group-addressed proportion is derived from existing `agent_turns.target_scope`.
- All four MemBench scenario/level cells, offline execution, pinned upstream source and MIT notice are present.
- The architectural interview has all five Park categories, separate tables/exports, profile-selectable interview and judge calls, and clear non-validity wording.
- Rubric-document wiring was fixed in iter-48.
- The reported `mixed` hypothesis verdict follows the implemented arithmetic; no Phase V trial figures appear in Arc 10 product documentation.
- One full run passed: **332 passed, 2 skipped**. Repeated iter-45 focused execution exposed the race despite that aggregate pass.

## Definition of Complete

| Requirement | Result |
|---|---|
| Four iterations committed separately | **PASS** |
| Network/recency/char-budget inclusion log | **FAIL** — categories exist, but records can disagree with final prompt and logging is not behavior-isolated |
| Group-addressed proportion from `target_scope` | **PASS** |
| Four-cell MemBench, offline MIT fixtures | **FAIL** — structure/licensing pass; evidence-preserving fixture validity fails |
| Five-category separate architectural interview | **FAIL** — structure passes; silent judge zeros and partial-run acceptance compromise scores |
| Reproducible baseline and explicit hypothesis verdict | **FAIL** — verdict exists; canonical inputs are unavailable and underlying evidence is invalid |
| No Phase V figures in product docs | **PASS** |

## Arc 11 Recommendation

**Do not use this baseline to choose or validate Arc 11 memory mechanisms yet.** Arc 11 design work may proceed, but implementation prioritization and before/after claims should wait until B1–B6 are fixed and the baseline is regenerated from committed, evidence-preserving inputs.

