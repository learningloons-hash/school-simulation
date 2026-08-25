# SSTRF RQ1 Scoring System v2

**Author:** GM-F · **Date:** 2026-08-25 · **For:** `senna-iter-57` Part B and `senna-iter-58` pre-registration v2
**Status:** DELIVERED — Ops may now implement calibration content. **Not yet signed.** Mark signs at `iter-58`, before any study output exists.
**Supersedes:** the scoring system in `PREREG_SSTRF_RQ1.md` v1.6, which governs the closed Phase V study and is not reused.

**Placement:** this document belongs in the **study repo** (`senna-sstrf-study`). Written here because that repo is not mounted; Ops to move it.

---

## 0. Correction that shapes everything below

`ARC12_PLATFORM_MEASURES_STATEMENT.md` §1, §4 and §7.1 state that scoring must never use
correspondence with CIEPSS. That is a misreading of the Arc 11 non-negotiable and it must not
propagate into the pre-registration.

The Arc 11 rule was: **judge *builds* on platform measures, never on correspondence with a
study case** — because selecting architecture by whether it reproduces CIEPSS is fitting to the
test set. It governed development decisions.

**The study's entire purpose is correspondence with CIEPSS.** RQ1 asks whether the simulation
can meaningfully reproduce the implementation dynamics of a documented case. The propositions
are CIEPSS findings. Scoring them means asking whether the simulation exhibits what CIEPSS
documented.

What remains prohibited, and is the legitimate part of the concern:

- **No lexical matching.** Correspondence is never scored by text overlap, string matching or
  embedding similarity between transcripts and CIEPSS source text. That would be gameable and
  methodologically empty.
- Correspondence is judged at the level of **dynamics**, by a rater applying a written rubric
  to simulation-produced evidence.
- Raters are never shown CIEPSS source text during scoring. They score against proposition
  statements, not against the report.

### What is and is not a correspondence instrument

| Instrument | Measures | Role in this study |
|---|---|---|
| Transcript + elicitation responses | What the simulated actors did and said | **The correspondence evidence.** All proposition scoring draws on these. |
| Agent float state | Attitude trajectories | **Supporting quantitative evidence only.** Never decisive alone. |
| MemBench | Memory QA on benchmark fixtures | **Not a correspondence instrument.** Ops's own inventory says so. Excluded from scoring. |
| Architectural interview | Whether the agent architecture works | **Not a correspondence instrument.** Diagnostic only. Excluded from scoring. |
| Blind plausibility panel | Whether outputs read as real to practitioners | Separate generative arm. Reported alongside, never combined into the correspondence score. |

---

## 1. Binding propositions — final set for RQ1

Five propositions, derived from the CIEPSS Final Report (Silver et al., 2011) findings.

| # | Proposition | Scored at |
|---|---|---|
| **P1** | Authority for innovation sits at the school level rather than with individual teachers. | Per staff agent |
| **P2** | The school level filters policy: what reaches the classroom has been interpreted and reshaped by school leadership rather than transmitted intact. | Per trial |
| **P3** | Teachers do not regard themselves as policy actors in their own right; they regard themselves as part of a cohesive national implementation effort. | Per staff agent |
| **P4** | Adaptation is small in scale and intended to mesh with policy, not to depart from it. | Per staff agent |
| **P5** | Policy is perceived as less flexible than it was intended to be. | Per staff agent |

### P5 — kept, rewritten

**Diagnosis.** The Phase V wording was *"Policies travel relatively well through the system but
are sometimes perceived as less flexible than intended."* That is **two independent claims
joined by "but," with a hedge ("sometimes") on the second.** To score 2 — clearly present — a
trial had to evidence both clauses at strength. Most evidence supports one. So it landed on 1,
twenty times out of twenty. The instrument was structurally incapable of returning 2.

Calibration item 9 (P5, gold 2) was scored 1 in both passes. **The gate knew and the 8/10
threshold hid it.**

**Decision: keep P5, rewritten to the single distinctive clause** — perceived rigidity.

The dropped clause ("policies travel well / are largely accepted") substantially overlaps P3
and P4 and loses little. The rigidity perception is the distinctive CIEPSS finding and is
directly observable: staff either express that constraint or they do not.

**The justification is structural, not performance-based.** P5 was compound and hedged; that
would have been true whatever it scored. This reasoning is on the record and must be disclosed
in reporting: instrument revised between pilot and study, with the reason.

**Note on P1 and P4.** Both also carry a "not" clause. They are *not* compound in the same
sense — each states one claim along a single dimension with both poles named. That is a
sharpening, not a conjunction. They stand.

---

## 2. Per-trial scoring

### 2.1 Evidence base

Raters score **only**:

1. **The elicitation responses** — CIEPSS Appendix B protocols (teacher / HOD / VP) and
   Appendix C (parent), administered verbatim post-run by the study-repo runner.
2. **The round transcripts** — all turns, all rounds.

Seed, trial number, run ID and condition labels are stripped before rating.

Float state may be supplied as a supporting exhibit but **cannot alone move a score**. MemBench
and architectural interview outputs are **not supplied to raters at all**.

### 2.2 Scored population

Propositions P1, P3, P4 and P5 are scored **per staff agent** — the four documented CIEPSS
School B staff:

`vice_principal_001` · `hod_english_001` · `senior_teacher_001` · `teacher_001`

**Parents are excluded from proposition scoring.** All five propositions are staff-facing
findings. Parent elicitation is retained in the record and used only in the plausibility arm.

P2 is a system-level claim about transmission and is scored **once per trial**.

**Why per-agent.** Phase V scored each proposition once per trial, and everything clustered on
"partially present." Scoring per agent converts a mushy judgement into a countable one: *how
many of the four documented staff clearly exhibit this?* It also quadruples resolution — 17
judgements per trial rather than 5 — at no extra rater burden per judgement.

### 2.3 Scale

Each agent × proposition, and P2 at trial level:

| Score | Meaning |
|---|---|
| **2** | Clearly exhibited. Evident in this agent's conduct or account without prompting toward it. |
| **1** | Partially exhibited. Present but weak, hedged, ambiguous, or only when directly asked. |
| **0** | Not addressed. No discernible evidence either way. |
| **−1** | Contradicted. Positive evidence of the opposite dynamic. |

Rater instructions, unchanged from Phase V where they worked:

- Score only from supplied text.
- Do not reward eloquence or penalise brevity.
- A proposition **asserted when directly asked** is weaker evidence (maximum 1) than the same
  pattern arising unprompted in transcript.
- **"Contradicted" requires positive evidence of the opposite dynamic, not mere absence.**

### 2.4 Per-trial pass rule

Let `n(Px)` = number of the four staff agents scoring **2** on proposition Px.

A trial **passes** if and only if **all five** hold:

1. **No core contradiction** — no agent scores −1 on P1, P2 or P3.
2. **`n(P1) ≥ 3`** of 4
3. **`n(P3) ≥ 3`** of 4
4. **`P2 = 2`** at trial level
5. **`n(P4) ≥ 2`** and **`n(P5) ≥ 2`**

Anything else is a fail. There is no near-pass category.

**Rationale for the thresholds.** CIEPSS reports these as findings about the school, not about
one individual. For the simulation to have reproduced them, a majority of documented staff
should exhibit them clearly. Three of four is a majority with one dissenter allowed — which is
also faithful to the source, where staff were not uniform. P4 and P5 are set at two of four
because CIEPSS itself evidences them less uniformly across roles.

These thresholds are **substantively motivated, not statistically derived.** See §3.

---

## 3. Study-level aggregation

**The study passes if ≥ 8 of 10 trials pass.**

**Unchanged from the Phase V pre-registration, deliberately.** The per-trial instrument is
materially stricter than Phase V's, so 8/10 is now a harder bar. Holding the study-level number
constant while tightening the instrument removes any question of the goalposts having moved.

### Framing — must be stated in identical terms in all reporting

The ten trials share one fixture, one case, one model, one prompt structure, and differ only by
`random_seed`. **They are repeated samples of one generative process, not ten independent tests
of a hypothesis.** The 8/10 threshold measures **how consistently the simulation reproduces the
case across stochastic variation** — it is not a significance test against a chance model, and
no p-value derived from a Bernoulli null may be reported.

This carries forward pre-reg v1.2 amendment 2 and is non-negotiable.

### Reported regardless of outcome

All ten per-trial results including fails; all agent-level scores; both judge passes raw;
adjudicated scores; rater calibration results; judge model IDs; resolved generator model ID per
trial; all warnings; all technical failures and re-runs. A study-level fail is reported as a fail.

---

## 4. Calibration set — 1-vs-2 discrimination content

For the `iter-43` harness. Five items, one per proposition. In each, the proposition **is**
present but only weakly — single instance, hedged, or asserted on request rather than
demonstrated. **Correct score is 1.** A judge scoring 2 is over-reading.

Combine with the existing 2-vs-−1 pairs and the two non-gating 0-probes.

> **C1 (P1) — expected 1.** "I suppose the department does set the direction, broadly. I hadn't
> really thought about it. We were told at the start of term what the focus was, and I've gone
> along with that."
> *Weak: single unprompted-adjacent mention, hedged twice ("I suppose", "broadly"), no evidence
> of the authority boundary the proposition asserts.*

> **C2 (P2) — expected 1.** "The HOD went through the circular with us at the level meeting. She
> read out the parts she thought mattered most for our level."
> *Weak: shows selection, which is filtering-adjacent, but a single act of emphasis at one
> meeting is not the systematic reshaping P2 asserts.*

> **C3 (P3) — expected 1.** "No, I wouldn't say I make policy. That's not really my role, is it."
> *Weak: correct direction, but a bare denial produced only on being asked. No trace of the
> positive half — belonging to a cohesive national effort. Maximum 1 under the direct-question
> rule.*

> **C4 (P4) — expected 1.** "I changed the worksheet a bit for my class. Simplified some of the
> wording."
> *Weak: one small adaptation with no indication of intent. P4 asserts adaptations are meant to
> mesh with policy rather than depart from it; nothing here speaks to intent or alignment.*

> **C5 (P5) — expected 1.** "It's quite prescriptive, the way it's come down. Though I imagine
> they had their reasons."
> *Weak: perceived rigidity is present, and immediately softened. One remark from one actor,
> undercut in the same breath.*

**Gate rule** (built at `iter-43`): a judge configuration passes only if it scores **≥ 8 of 10
overall AND is not wrong on both items of any single proposition.** Phase V's gate was 8/10
alone, and a judge that systematically failed one proposition cleared it — on a criterion where
a single proposition can fail an entire trial.

---

## 5. Judge model and fallback chain

Generator is Anthropic (`claude-haiku-4-5-20251001`). The judge must be a **different vendor**.

| Tier | Model | Route |
|---|---|---|
| **Primary** | `gpt-4o` | `openai_default` with model override |
| **Backup** | `gpt-4o-mini` | `openai_default`, then `openrouter_default` |
| **Escalation** | Human (Mark) scores 100% of cells | — |

**Why `gpt-4o` primary, not `gpt-4o-mini`.** Phase V ran on mini and produced systematic
clustering at 1. The diagnosis was the calibration gate rather than the model, but we have no
positive evidence mini can do this task and one run of evidence that it struggled. The scoring
task is nuanced qualitative judgement over policy-implementation discourse. Cost is not a
reason to take the risk: 10 trials × 17 judgements × 2 passes = **340 judgements**, roughly
US$3–6 total.

Routing through OpenRouter to any Claude model is **prohibited** — same-family judging.

Two independent scoring passes with independent seeds, and proposition order and agent order
shuffled between passes. Adjudication unchanged from Phase V: agreement stands; a 1-point
difference resolves to the **lower**; ≥2 points or any −1 goes to the human rater, whose score
is final.

Drift check: Mark independently scores a random 20% sample of agent × proposition cells,
sampled by trial (whole trials, not scattered cells — see the Arc 12 drift-check design).

---

## 6. Blind plausibility protocol

The generative arm. **Reported alongside the correspondence result, never combined into it.**

**Panel.** 6–8 practitioners — Singapore school leaders, teachers, or MOE officers with school
implementation experience. Recruitment is Mark's, outside the arc. **This is the longest lead
item in the study; it should be in progress now.**

**Materials.** Each rater receives 8 implementation reports in randomised order: 4 derived from
simulation trials, 4 constructed from the documented CIEPSS case, in an identical format.
Condition labels, seeds, run IDs and filenames stripped. The key is held separately and is not
shipped.

**Task.** For each report: rate plausibility for a Singapore primary school of that type on a
1–6 scale; state whether they believe it is simulated or documented; give reasons in free text.

**Analysis.**
- **Discrimination rate** — proportion of reports correctly identified. Chance is 0.50.
- **Plausibility difference** between conditions.
- **Reasons given** for correct identifications — these say what the simulation is missing and
  are the most useful output of this arm.

**No pass/fail threshold is set.** This arm is descriptive and reported as such. Pre-specified
notable results: discrimination at or near chance with comparable plausibility ratings would be
a strong positive; discrimination well above chance with the reasons clustering on a single
identifiable feature would be a directly actionable finding.

---

## 7. Mechanism defaults — GM-F ruling

**Ruling: all three memory mechanisms remain OFF for the study.**
`importance_scoring_enabled: false` · `weighted_retrieval_enabled: false` · `reflection_enabled: false`

**Reasoning, on the Arc 12 evidence.**

The confound test resolves Arc 11's decline as a **model artefact**: on the Anthropic tier
`memory_retrieval` sits at 2.00 in both baseline and full-stack arms. The Arc 11 decline was
the 8B local model degrading under longer prompts. Mechanisms are not implicated — but neither
are they vindicated, because four of five interview categories are saturated at 2.00 on
Anthropic and only `reaction` carries range, where the full stack is *lower* (1.22 → 1.00).

**The individuation argument does not survive.** It was the one live case for switching
defaults on. It collapses twice over:

- On the Anthropic tier, dispersion is **worse** with mechanisms on — baseline 0.023 versus
  full-stack 0.017.
- At study scale with mechanisms **off**, dispersion is already 0.017–0.071 across eight agents.

The near-zero individuation observed in Arc 11 was an artefact of a 3-agent toy scenario on a
weak local model. At the scale and tier that matter, agents already differentiate without help.

Against no measured benefit: **40% more input tokens** (32.0k → 44.7k) and **70% more
wall-clock** (28s → 48s).

The mechanisms ship built, tested, flagged and documented — a real Arc 11 deliverable and a
reportable negative result on an unevaluated set of techniques. They are not switched on for a
study that has no evidence they help it.

---

## 8. Convergence for study runs — GM-F ruling

**Ruling: no convergence threshold is set. All study trials run a fixed round count.**
`convergence_threshold: null`

**Reasoning.** Early stopping would give different trials different round counts, and therefore
different evidence bases. For a study whose unit of analysis is the trial and which aggregates
across ten of them, variable trial length is an uncontrolled variable introduced to save money
we do not need to save. Rehearsal ran without a threshold, so we have no evidence about when
τ = 0.02 would fire at study scale.

τ = 0.02 with patience 2 is **accepted as the calibrated value** and recorded, for use in
future work and in any run where early stopping is wanted. It is simply not applied here.

`convergence_delta` continues to be computed and stored every round. **Report it descriptively**
— whether trials converge, and at what round — as an observation about the simulation's
behaviour. It does not stop anything.

### Round count

**20 rounds.** The proposal specifies 15–20; 20 gives the propositions more opportunity to
manifest, and P1 and P4 both require cross-round synthesis. Rehearsal cost was US$3.18–3.37 per
20-round run against US$1.95–2.09 at 15 — about **US$13 more across ten trials**. Round-20
input sits at 80–90k tokens, comfortably inside Haiku 4.5's window, with no context failures
observed in six rehearsal runs.

---

## 9. Frozen study profile

| Field | Value |
|---|---|
| Scenario | `ciepss_school_b` |
| Agents | 8 (4 staff scored, 4 parents unscored) |
| Rounds | **20**, fixed |
| Generator | `claude-haiku-4-5-20251001` |
| Visibility | `network_bounded`, documented CIEPSS network CSV |
| Turn order | `hierarchical` |
| Sampling | `full_census` |
| Likert self-report | **off** — not required by this criterion; the float state is supporting evidence only |
| Memory mechanisms | all **off** (§7) |
| Convergence threshold | **null** (§8) |
| `working_memory_last_k` / `peer_context_max_chars` | 2 / 1200 (Arc 1 defaults, unchanged) |
| Judge | `gpt-4o`, two passes (§5) |
| Trials | 10, seeds fixed in advance and **distinct from every development seed used in Arcs 9–12** |

---

## 10. What Ops implements now (`iter-57` Part B)

1. Calibration content from §4 into the `iter-43` harness, with the §4 gate rule.
2. Per-agent scoring shape from §2.2 — 17 judgements per trial, not 5.
3. Rater packet builder: elicitation responses plus transcripts, stripped of seed, trial
   number, run ID and condition. **Automated leakage check as the acceptance criterion.**
4. Adjudication logic per §5.
5. Aggregation per §2.4 and §3, computed and reported, never inferred by hand.

**Not implemented by Ops:** the propositions, thresholds or rubric wording. Those are fixed
above and change only by a new version of this document, signed before any study output exists.

---

## 11. Open items — Mark

| Item | Note |
|---|---|
| **Practitioner panel** (§6) | Longest lead item in the study. Nothing depends on the build. Start now. |
| **Seeds** | Ten study seeds to be fixed at `iter-58` and recorded. Must not overlap 42/43/44 or any Arc 9–12 development seed. |
| **RQ2** | Out of scope for this document. No verified case above 20 actors; NIE library access outstanding. RQ2 needs its own criterion once a case exists. |
