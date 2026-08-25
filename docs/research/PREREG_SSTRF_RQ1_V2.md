# Pre-registration — SSTRF RQ1 Correspondence Study v2 (CIEPSS School B)

> ## STATUS: **UNSIGNED DRAFT**
>
> Mark must sign §Signature below **before any study output exists**. Until signed, this
> document is a draft for review only. No validity trial may be run, scored, or cited under
> this pre-registration.

| Field | Value |
|---|---|
| Document | `docs/research/PREREG_SSTRF_RQ1_V2.md` |
| Version | v2.0 (draft — iter-58 Part A) |
| Date drafted | 2026-08-25 |
| Arc | 12 — Freeze and Study Readiness (`senna-iter-58` Part A) |
| Governs | SSTRF RQ1 validity trials on CIEPSS School B (Silver et al., 2011, CRP 47/08 MS) |
| Supersedes for new work | **`PREREG_SSTRF_RQ1.md` v1.x** — see §0 |

---

## 0. Relationship to the Phase V pre-registration

**`docs/research/PREREG_SSTRF_RQ1.md` v1.x governs the closed Phase V pilot study and is not
reused.** Measurement instrument, per-trial thresholds, round count, mechanism defaults, judge
model, and platform architecture have all changed since v1.5 was signed (2026-08-08).

Phase V's substantive result (1/10 trials passed under v1 criteria) stands as **prior pilot
work** and is reported in any write-up. It is not re-run, re-scored, or combined with this
study.

This v2 pre-registration is filed under SL-2: the correspondence criterion is fixed **before**
any substantive validity-trial output under v2 is viewed, and may not be revised after such
output has been seen.

---

## 1. Research question and case

**RQ1:** Can a generative agent-based simulation (Senna) with fewer than ten documented actors
reproduce the documented **implementation dynamics** of a verified single-school policy
implementation case?

**Case:** CIEPSS School B — eight actors (Vice-Principal Miss C; English HOD Miss L; Senior
Teacher Miss T; P2 form teacher Miss M; four parents), per Table 2 (p.9) of the CIEPSS Final
Report (Silver et al., 2011, CRP 47/08 MS).

**Fixture identity:** scenario `ciepss_school_b`. Provenance is the **study-repo commit** in
§3 — not a product-database row or ad hoc local edit.

---

## 2. Frozen platform record

Recorded at pre-registration draft time from the **product repository** (`mirofish-mvp` /
Senna):

| Field | Value |
|---|---|
| **Platform commit** | `da906c3efee7e0e769c388e3dc09986eae6f93c3` |
| **Platform closeout** | senna-iter-57 (scoring harness on `main`, commit `177306a`) |
| **Export version** | 14 (`backend/src/mirofish_backend/export_bundle.py`) |

After Mark signs, the platform commit recorded in the formal freeze manifest
(`docs/diagnostics/ARC12_PLATFORM_FREEZE.json`, Part B) is binding. No platform changes until
the study completes or this pre-registration is formally amended.

---

## 3. Fixture provenance (study repo — not the product DB)

Fixture material is versioned in the **private study repository**, not on the public product
repo. The product repo holds a provenance pointer only.

**Source manifest:** [`docs/diagnostics/ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json)

| Field | Value |
|---|---|
| **Study repo** | `https://github.com/learningloons-hash/senna-sstrf-study.git` |
| **Fixture commit** | `47013659309c5ac047dbc53dcea3fd1441d74042` |
| **Scenario YAML** (at fixture commit) | `backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml` |
| **Influence network CSV** (at fixture commit) | `docs/research/fixtures/ciepss_school_b_network.csv` |
| **Seeded at** | 2026-08-24T05:54:30+00:00 |
| **Dirty** | false |

Ops loads scenario and network CSV from the pinned study-repo commit for every validity trial.
The simulation `config_snapshot` must record `network_csv_applied: true` and network
provenance fields per platform export v14.

---

## 4. Full simulation config snapshot

All validity trials use the **frozen study profile** ruled by GM-F (2026-08-25) and recorded in
[`SSTRF_RQ1_SCORING_SYSTEM_V2.md`](SSTRF_RQ1_SCORING_SYSTEM_V2.md) §9. Values below are the
binding API / run configuration.

| Field | Value |
|---|---|
| `scenario_id` | `ciepss_school_b` |
| `agent_limit` | 8 (4 staff scored for correspondence; 4 parents elicited but unscored on propositions) |
| `total_rounds` | **20** (fixed — no early stop) |
| `model_profile` / tier | Anthropic — **`claude-haiku-4-5-20251001`** |
| `visibility_policy` | `network_bounded` |
| `network_csv` | documented CIEPSS network from study repo (§3) |
| `turn_order_policy` | `hierarchical` |
| `sampling_strategy` | `full_census` |
| `likert_self_report_enabled` | **false** |
| `importance_scoring_enabled` | **false** |
| `weighted_retrieval_enabled` | **false** |
| `reflection_enabled` | **false** |
| `convergence_threshold` | **null** (not applied — §5) |
| `convergence_patience` | 2 (platform default when threshold is set; inactive while threshold is null) |
| `working_memory_last_k` | 2 |
| `peer_context_max_chars` | 1200 |

**Resolved generator model ID** per trial is taken from `config_snapshot.model_profile.model_id`
and reported with trial results. Routing must remain on the Anthropic tier above unless this
pre-registration is amended before any output exists.

---

## 5. Convergence — calibrated but not applied

Arc 12 rehearsal (iter-55, seeds 42/43/44) ran **without** a convergence threshold so mechanics
could be measured at full 15- and 20-round horizons. Separately, Ops calibrated a candidate
threshold:

| Parameter | Calibrated value | Applied in this study? |
|---|---|---|
| `convergence_threshold` | **0.02** | **No** — null (§4) |
| `convergence_patience` | **2** | N/A while threshold is null |

**Source:** [`docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md`](../diagnostics/ARC12_CONVERGENCE_CALIBRATION.md) — τ = 0.02 avoids round-3 false convergence (τ = 0.05) and yields stable counterfactual stop at round 8 across rehearsal seeds.

**GM-F ruling (§8):** Early stopping would give trials different evidence bases. This study uses
**fixed 20 rounds** for all ten trials. `convergence_delta` is still computed and stored every
round and reported **descriptively** (whether trials would have converged, and at what round) —
it does not stop runs.

---

## 6. Correspondence criterion — by reference (do not rewrite here)

The full binding criterion — propositions, per-agent scoring shape, per-trial pass rule,
study-level aggregation, calibration set, judge model chain, adjudication, plausibility arm, and
reporting obligations — is **`SSTRF_RQ1_SCORING_SYSTEM_V2.md`**, incorporated by reference.

| Field | Value |
|---|---|
| **Scoring document** | `docs/research/SSTRF_RQ1_SCORING_SYSTEM_V2.md` |
| **Blob hash (at platform commit above)** | `8130b7455422a1c474dd0cc1a647816b1fe593b8` |
| **Delivered** | GM-F, 2026-08-25 (`senna-iter-57` Part B) |
| **Harness implementation** | `scripts/sstrf_scoring_*.py`, `scripts/sstrf_rq1_scoring.py` on product `main` (commit `177306a`) |

**Incorporated sections (summary only — authoritative text is the scoring document):**

- **§1** — Five binding propositions (P1–P5); P5 rewritten single-clause rigidity wording.
- **§2** — Evidence = elicitation (Appendix B/C verbatim post-run) + round transcripts; 17
  judgements per trial (P1/P3/P4/P5 × four staff agents + P2 trial-level); parents excluded from
  proposition scoring.
- **§2.4** — Per-trial pass rule (no core contradiction on P1/P2/P3; n(P1)≥3, n(P3)≥3, P2=2,
  n(P4)≥2, n(P5)≥2 of four staff).
- **§3** — Study passes if ≥ **8 of 10** trials pass; framing in §11 below.
- **§4–§5** — Calibration gate and judge chain (`gpt-4o` primary).
- **§6** — Blind plausibility arm reported **alongside** correspondence, never combined into the
  correspondence score.
- **§7–§9** — Mechanism defaults off; convergence null; frozen study profile (§4 above).

Proposition wording, thresholds, and rubric language in the scoring document are **fixed**. They
change only by a new signed version of that document filed before any study output exists.

**Still prohibited:** lexical matching, string overlap, or embedding similarity to CIEPSS source
text. Raters score dynamics from simulation evidence against proposition statements — CIEPSS
source text is not shown during scoring.

**Not correspondence instruments** (diagnostic only; excluded from proposition scoring): MemBench,
architectural interview outputs.

---

## 7. Study seeds and trial labels

**Placeholder — fixed in Part B (`docs/diagnostics/ARC12_STUDY_SEEDS.json`).**

Ten trials will share one fixture, one case, one model, and one prompt structure; they differ
only by `random_seed`. Trial labels: `trial-A` … `trial-J`.

Seeds will be:

- Fixed in advance before any validity trial is run.
- **Distinct** from Arc 9–12 development seeds **42, 43, 44** and from every seed listed in
  Arc 9–12 diagnostic JSON under `docs/diagnostics/`.
- Recorded in the platform freeze manifest (Part B) and inserted into this section when Part B
  lands.

Until Part B commits, **no validity trial may be executed.**

---

## 8. Excluded development work

The following are **excluded from validity claims** under this pre-registration:

| Exclusion | Detail |
|---|---|
| **Arc 9–12 rehearsal** | iter-54 through iter-56 runs (mechanics, cost, convergence calibration only) |
| **Development seeds** | 42, 43, 44 (iter-55 RQ1 rehearsal) and any seed in Arc diagnostic JSON |
| **Phase C calibration** | Cost/performance runs per original handoff — no validity claim |
| **Phase V pilot** | Closed under `PREREG_SSTRF_RQ1.md` v1.x; 1/10 result is prior pilot only |
| **Pre-signing platform changes** | Any run after signing must use the frozen commit in the freeze manifest |

Substantive outputs from excluded runs are not read, cited, or scored toward this study's pass/fail.

---

## 9. Validity trial procedure (summary)

1. **Pre-flight:** Verify fixture and network CSV match §3 provenance; verify propositions do
   not appear in generator-visible fixture text (contamination guard, carried from v1).
2. **Run:** Queue simulation with §4 config; execute **20 rounds**; record full export bundle.
3. **Elicitation:** Administer CIEPSS Appendix B (staff) and Appendix C (parent) protocols
   verbatim post-run via study-repo runner; persist per-agent JSON.
4. **Scoring:** Judge calibration gate → two-pass automated scoring → adjudication → human queue
   per scoring v2 §5; study aggregation computed in harness, not hand-inferred.
5. **Report:** All trials, all agent-level scores, judge IDs, failures, and warnings regardless
   of outcome (scoring v2 §3).

---

## 10. Study-level framing — verbatim (GM-F v2 §3)

The ten trials share one fixture, one case, one model, one prompt structure, and differ only by
`random_seed`. **They are repeated samples of one generative process, not ten independent tests
of a hypothesis.** The 8/10 threshold measures **how consistently the simulation reproduces the
case across stochastic variation** — it is not a significance test against a chance model, and
no p-value derived from a Bernoulli null may be reported.

This carries forward pre-reg v1.2 amendment 2 and is non-negotiable in all reporting.

---

## 11. Freeze commitment

When Mark signs this document:

1. The platform commit, fixture commit, scoring document hash, and study seeds recorded in
   `ARC12_PLATFORM_FREEZE.json` are **binding**.
2. **No platform changes** until all ten validity trials are complete and scored, or this
   pre-registration is formally amended and re-signed before further outputs.
3. Any amendment must be filed and signed **before** viewing substantive outputs that the
   amendment would affect.

---

## Signature

**Status:** UNSIGNED — Mark must sign before any study output exists.

**Signed by:** ___________________

**Date:** ___________________
