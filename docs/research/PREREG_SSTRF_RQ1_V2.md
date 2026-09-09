# Pre-registration — SSTRF RQ1 Correspondence Study v2 (CIEPSS School B)

> ## STATUS: **SIGNED**
>
> Signed 2026-08-25 by Mark. Validity trials may proceed under this pre-registration and the
> binding freeze in [`ARC12_PLATFORM_FREEZE.json`](../diagnostics/ARC12_PLATFORM_FREEZE.json).

| Field | Value |
|---|---|
| Document | `docs/research/PREREG_SSTRF_RQ1_V2.md` |
| Version | v2.0 (signed — 2026-08-25) |
| Date drafted | 2026-08-25 |
| Date signed | 2026-08-25 |
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

## 3. Research artefact provenance (verifier pointers)

**Location correction (2026-09-09):** Methodological study artefacts below are committed in the
**public product repository** (`school-simulation`). They are no longer gitignored-only on
that repo. **Case fixture material** (CIEPSS scenario YAML, influence network CSV, elicitation
transcripts, source PDFs) remains in the **private study repository** only.

### 3a. Public methodological artefacts (`school-simulation`)

Repository: `https://github.com/learningloons-hash/school-simulation.git`

| Artefact | Commit (reachable on `main`) | Path |
|---|---|---|
| **Pre-registration (signed)** | `1b5ca4c2f290359cf4841164583302e45d256b4f` | `docs/research/PREREG_SSTRF_RQ1_V2.md` |
| **Scoring system v2** | `177306a75725e1fb168fc173cf104d289c3726ae` | `docs/research/SSTRF_RQ1_SCORING_SYSTEM_V2.md` |
| **Rater calibration set** | `177306a75725e1fb168fc173cf104d289c3726ae` | `docs/research/SSTRF_RATER_CALIBRATION_SET.md` |
| **Platform freeze manifest** | `66ea88e` (see `ARC12_PLATFORM_FREEZE.json` for signed record) | `docs/diagnostics/ARC12_PLATFORM_FREEZE.json` |
| **Validity-v2 trial manifest** | `750509f` | `docs/diagnostics/sstrf_validity_v2_manifest.json` |
| **Validity-v2 scoring manifest (scores)** | `e5aa26bb558401ac606c0d6b16786dd4d3e9bae2` | `docs/research/runs/ciepss_school_b/validity_v2/scoring/validity_v2_scoring_manifest.json` |
| **Validity-v2 result narrative** | `befeaad` | `docs/research/runs/ciepss_school_b/validity_v2/scoring/SSTRF_RQ1_RESULT_V2.md` |

**Utility fixtures (`sq_reading_culture*`):** authoritative copies live in this repository at
`backend/src/mirofish_backend/scenarios/data/`. The private study repository may hold
non-authoritative mirrors for ops convenience; verifiers should use `school-simulation` only.

The signed STATUS block at the top of this document is unchanged. Criterion, thresholds, and
signature date (`2026-08-25`) are not amended by this pointer correction.

### 3b. Private case fixture material (`senna-sstrf-study`)

**Source manifest (pointer):** [`docs/diagnostics/ciepss_school_b_provenance.json`](../diagnostics/ciepss_school_b_provenance.json)

| Field | Value |
|---|---|
| **Study repo** | `https://github.com/learningloons-hash/senna-sstrf-study.git` |
| **Fixture commit** | `47013659309c5ac047dbc53dcea3fd1441d74042` (YAML/CSV content); elicitation @ `437d72b` |
| **Scenario YAML** | `backend/src/mirofish_backend/scenarios/data/ciepss_school_b.yaml` |
| **Influence network CSV** | `docs/research/fixtures/ciepss_school_b_network.csv` |
| **Elicitation transcripts (validity v2)** | `docs/research/runs/ciepss_school_b/validity_v2/elicitation/` (study repo only) |
| **Result narrative (mirror)** | `docs/research/runs/ciepss_school_b/validity_v2/scoring/SSTRF_RQ1_RESULT_V2.md` (non-authoritative; public copy in §3a) |

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

Ten trials share one fixture, one case, one model, and one prompt structure; they differ only
by `random_seed`. Trial labels: `trial-A` … `trial-J`.

**Manifest:** [`docs/diagnostics/ARC12_STUDY_SEEDS.json`](../diagnostics/ARC12_STUDY_SEEDS.json)

**Selection rule:** first ten integers ≥ 500 not in the Arc 9–12 development exclusion set
(42, 43, 44) → seeds **500–509**.

| Trial label | `random_seed` |
|---|---|
| trial-A | 500 |
| trial-B | 501 |
| trial-C | 502 |
| trial-D | 503 |
| trial-E | 504 |
| trial-F | 505 |
| trial-G | 506 |
| trial-H | 507 |
| trial-I | 508 |
| trial-J | 509 |

**Platform freeze:** [`docs/diagnostics/ARC12_PLATFORM_FREEZE.json`](../diagnostics/ARC12_PLATFORM_FREEZE.json)
records platform commit, fixture provenance, scoring document hash, and seed manifest.

Validity trials may proceed under this signed pre-registration and the binding freeze manifest.

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

**Status:** SIGNED

**Signed by:** Mark

**Date:** 2026-08-25
