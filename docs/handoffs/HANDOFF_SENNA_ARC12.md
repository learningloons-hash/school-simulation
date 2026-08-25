# HANDOFF_SENNA_ARC12 — Freeze and Study Readiness

**Owner:** GM-F → Senna-Ops → Cursor Architect → Cursor Builder
**Date:** 2026-08-24
**Arc:** 12 — Freeze and Study Readiness
**Iterations:** `senna-iter-54` through `senna-iter-58`
**Predecessor:** Arc 11 closed **PASS WITH ISSUES** (GM-F, 2026-08-24)
**Goal:** Take a platform that has never been exercised at study configuration and make it a defensible study instrument.

---

## 0. Read this first — the honest state

Arcs 9–11 built the machinery. **None of it has ever run at study configuration.**

| Dimension | What has been tested | What the study requires |
|---|---|---|
| Scenario | `fsbb_comparator`, `psle_reform_mvp` | `ciepss_school_b` |
| Agents | 3 | 8 (RQ1), ~20 + remainder (RQ2) |
| Rounds | 5–6 | 15–20 |
| Model | `dolphin3.0-llama3.1-8b` (local) | Anthropic tier |
| Network | synthetic chain | CIEPSS documented links |

Every row differs. Arc 12 closes that gap or the study does not run.

### 🚨 Blocking defect found on GM-F review

**`backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml` is not in the platform
repository.** The scenarios directory contains only `fsbb_comparator.yaml` and
`psle_reform_mvp.yaml`. The fixture was caught by the gitignore rules during the 2026-08-18
repo split and exists only on the study side.

**The platform cannot load the case the study is meant to run.** Resolve this in `iter-54`
before anything else. See §1.

---

## 1. `senna-iter-54` — Fixture reunification and the confound test

### Part A — Fixture reunification 🚧 BLOCKING

The two-repo split separated the platform from the scenario it needs. Decide and implement a
loading path that keeps copyright and MOE material out of the public repo while making the
fixture available at runtime.

**Constraints, non-negotiable:**
- No CIEPSS PDF, no MOE proposal material, no paywalled source in the public repo.
- The scenario YAML itself contains only roster, roles, network, policy events and
  `# source: p.N` provenance comments — no reproduced source text. Confirm this by reading it
  before deciding where it lives.
- Whatever path is chosen, the **frozen configuration recorded in `iter-58` must name the
  fixture's exact commit and repo**, and it must resolve.

Options for Ops to evaluate and recommend (do not pick unilaterally — bring the
recommendation to GM-F):
1. Fixture lives in the study repo; platform loads external scenario paths via config.
2. Fixture lives in the public repo (if it genuinely contains no protected material).
3. Study repo vendored as a submodule at a pinned commit.

**DoD:** the platform loads `ciepss_school_b` and runs a smoke simulation from a clean
checkout, with a documented setup step. Test asserts the scenario resolves.

### Part B — The confound test

Arc 11's `memory_retrieval` decline (2.00 → 1.67 → 1.67 → 1.22) tracks input-token growth
(26k → 31k → 33k → 37k) on an 8B local model. That is the signature of context degradation.
The Arc 11 sweep cannot separate mechanism effect from model limitation. This resolves it.

**Design — exactly this, no expansion:**
- Two conditions only: `baseline` and `+importance+retrieval+reflection`.
- Three seeds each. **Six runs.**
- **Anthropic tier** — the tier the study will use. Not the local model.
- **Same scenario and same network CSV in both conditions.** The Arc 11 results file records
  that its network was a "synthetic chain… not identical to Arc 10 measured baseline network."
  That uncontrolled variable does not recur here.
- Report: architectural interview by category, MemBench, **between-agent dispersion**, input
  tokens, cost, wall-clock.

**Interpretation, fixed in advance:**
- `memory_retrieval` recovers toward 2.00 in the full-stack arm ⇒ the Arc 11 decline was the
  8B model degrading under longer prompts. Mechanisms are not implicated.
- The decline persists ⇒ it is a mechanism effect and the mechanisms stay off.

**Cost:** ~US$10. Do not expand this into a larger sweep. It answers one question.

### Part C — The individuation question

Arc 11's dispersion table is the most important number produced in that arc and has not been
acted on. At baseline, cross-agent interview-score stdev is **~0.00** — agents give each
other's answers. Adding importance and retrieval raises it to **~0.31**.

**Senna as currently configured for the study produces near-identical actors.** The study's
propositions require the opposite: P1 concerns where authority sits, P3 concerns self-concept,
P4 concerns adaptation scale. If every agent answers alike, the case cannot be reproduced
regardless of how good the scoring is.

**Report dispersion from Part B explicitly and separately.** If individuation holds on the
Anthropic tier, the case for turning the mechanisms on by default becomes a study-validity
argument rather than a quality argument, and GM-F will rule accordingly.

**DoD for `iter-54`:** fixture loads; six runs complete; a written recommendation on the
mechanism defaults with quality, cost and dispersion evidence. **GM-F ruling required before
`iter-55` begins.**

---

## 2. `senna-iter-55` — Study-scale rehearsal

The first time Senna runs anything resembling the study.

- Scenario `ciepss_school_b`, **8 actors**, **15 and 20 rounds**, Anthropic tier, CIEPSS
  documented network, mechanism flags per the `iter-54` ruling.
- A second configuration approximating RQ2: ~20 documented actors plus synthetic remainder.
- Three seeds each.
- Non-study in status: **substantive outputs are not read, cited or scored.** This is a
  load test. Ops reports mechanics only — completion, token growth, error rates, wall-clock,
  state-extraction provenance counts, `group_addressed_proportion`.

**Watch for, and report:**
- Context growth across 20 rounds. Arc 11 hit 37k input tokens at 3 agents and 5 rounds.
  Eight agents at 20 rounds is a different order of magnitude and may hit context limits.
- Whether `peer_context_max_chars: 1200` and `working_memory_last_k: 2` remain sane at this
  scale, or whether the peer context becomes vestigial.
- Whether the elicitation runner and Likert self-report survive a 20-round run intact.

**DoD:** all runs reach terminal status; no context-length failures; a written report of
mechanics with the above four items addressed explicitly.

---

## 3. `senna-iter-56` — Calibration, cost, and the price map

Three pieces of housekeeping that must be settled before anything is frozen.

**Convergence threshold.** The stopping rule fires when mean attitude change falls below a
threshold for two consecutive rounds. Convergence is computed on the continuous float, not the
Likert (D2). Calibrate against the `iter-55` rehearsal runs and **document the calibration and
the reasoning** — an uncalibrated threshold either never fires or fires in round three.

**Cost table at study configuration.** Full measured table: RQ1 and RQ2 configurations, at the
tier the study will use, with the mechanism flags as ruled. This supersedes the Phase C figures
in the SSTRF cover note, which were 8 actors × 6 rounds on a pilot configuration.

**`PROVIDER_PRICE_MAP` per-model resolution.** *(Builder)* It currently bills every Anthropic
model at a generic $3/$15 bucket. The env-override workaround is not acceptable as the
permanent answer for a study that reports costs to a funder. Resolve `pricing_key` per model
id. Tests for at least Haiku 4.5 and Opus 5 rates.

**DoD:** calibrated threshold documented; cost table published; price map resolves per model
with passing tests.

---

## 4. `senna-iter-57` — Scoring system design (D1)

The deferred decision. The entire scoring system is designed **once**, here, against the
platform as it finally stands.

**GM-F drafts. Ops does not write this content.** Ops's role is to state what the platform can
now measure, and to implement the calibration content once the criterion is fixed.

Covers:
- The binding propositions — including whether P5 survives. It scored 1 on 20 of 20 judge
  passes in Phase V because it is a compound proposition ("travels well **but** perceived as
  inflexible") with a hedge ("sometimes") built in, making 2 structurally unreachable.
- Per-trial and study-level thresholds, recalibrated to whatever proposition count results.
- Calibration set content written into the `iter-43` harness — including the 1-vs-2
  discrimination items the harness was built for.
- Judge model and the fallback chain.
- The blind plausibility protocol and its rater panel.

**Input required from Ops before GM-F drafts:** a short statement of what the platform now
measures per trial, in what format, with what provenance — so the criterion is written against
what exists rather than what was assumed.

---

## 5. `senna-iter-58` — Pre-registration v2 and freeze

**The old pre-registration governs a closed study and cannot be reused.** Measurement,
criterion, round count and architecture have all changed.

Records, all of which must resolve:

| Field | Source |
|---|---|
| Platform commit hash and tag | product repo |
| Fixture commit hash and repo | **study repo** — not `origin`; the research material does not exist on the public repo |
| Model ID and tier | as ruled |
| Full config snapshot | mechanism flags, weights, thresholds, `working_memory_last_k`, `peer_context_max_chars`, convergence threshold |
| Scoring system | `iter-57` |
| Seeds | fixed in advance, distinct from all development seeds |

**Signed by Mark before any study output exists.** Development seeds and any run performed in
Arcs 9–12 are excluded from validity claims, as Phase C and Phase V are.

**After signing: freeze.** No platform changes until the study completes or the
pre-registration is formally amended.

---

## 6. Standing constraints

- **Nothing in `iter-54` through `iter-56` is a study run.** Substantive outputs are not read,
  cited or scored. Ops reports mechanics only.
- **Judge builds on platform measures.** Never on correspondence with CIEPSS.
- **Phase V's 1/10 stands** as prior pilot work and is reported in any write-up.
- Each iteration independently shippable.
- Escalate rather than absorb — D5 stands, there is no contingency plan and no scope drops.

---

## 7. Outside the arc — Mark only, and both have long lead times

Neither depends on the build, and both get more expensive the longer they wait.

1. **NIE library access** — Ho (2009) thesis, Lee (2020) thesis, Hong (2020) report. Lee is the
   only verified route to an RQ2 case above 20 actors. Without it RQ2 runs on a 13–17 actor
   case plus synthetic remainder, which is defensible but weaker than the proposal implies.
2. **Expert recruitment for the blind plausibility arm.** Committed in the resubmission.
   Practitioners, not code. This is the single most likely thing to be the bottleneck in a
   nine-month window.

---

## 8. Gates — do not pass without them

| Gate | Condition |
|---|---|
| `iter-54` → `iter-55` | Fixture loads from clean checkout **and** GM-F has ruled on mechanism defaults |
| `iter-55` → `iter-56` | Study-scale rehearsal completes with no context-length failures |
| `iter-57` → `iter-58` | GM-F has delivered the scoring system |
| `iter-58` → study | Mark has signed pre-registration v2 and the platform is frozen |
