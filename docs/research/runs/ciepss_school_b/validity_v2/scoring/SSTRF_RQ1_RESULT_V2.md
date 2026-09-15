# SSTRF RQ1 — Result (v2)

**Status:** Confirmatory result final. Reported regardless of outcome, per `PREREG_SSTRF_RQ1_V2.md` §9 and `SSTRF_RQ1_SCORING_SYSTEM_V2.md` §3.
**Scoring record:** `docs/research/runs/ciepss_school_b/validity_v2/scoring/validity_v2_scoring_manifest.json`
**Scored by:** Mark (human-only escalation, GM-F v2 §5 — automated judge failed calibration twice: 8/15, then 9/15 against a ≥12/15 gate)
**Date:** 2026-09-01

---

## 1. The confirmatory result: FAIL

**0 of 10 trials pass. The pre-registered bar is ≥8 of 10.**

| Trial | Result | Failing on |
|---|---|---|
| A | FAIL | P3: only 0 of 4 staff score a clear 2 (need ≥3) |
| B | FAIL | P3 |
| C | FAIL | P3 |
| D | FAIL | P3 |
| E | FAIL | P3 |
| F | FAIL | P3 |
| G | FAIL | P4: only 1 of 4 staff score a clear 2 (need ≥2) |
| H | FAIL | P3 |
| I | FAIL | P3 |
| J | FAIL | P3 |

`study_pass: false`. This is the confirmatory RQ1 result.

---

## 2. This result is robust to which scoring pass is used

Mark scored the worksheet twice: an initial pass, then a full revision after a within-trial duplication error was caught and corrected (each of the 4 staff per trial re-read and scored independently, with per-cell justifications). The revision resolved that concern — 174 of 174 notes are now unique, citing specific rounds and quotes per trial, rather than the 40-unique-of-174 pattern in the first pass.

Both passes were run through the identical pre-registered pass rule (`sstrf_scoring_adjudication.py::trial_passes`). **Both produce 0 of 10.** The initial pass failed every trial on P5 alone (no staff member ever scored a clear 2 on P5, in either pass — see §3). The revised pass fails nine trials on P3 and the tenth on P4. The overall verdict does not depend on which pass is used.

---

## 3. A known limitation in the instrument, disclosed here

Two propositions are doing nearly all of the failing, and they fail in different, diagnostic shapes.

**P3 shows a ceiling, not noise.** In 9 of 10 trials, all four staff land on exactly 1 — not a scatter, a flat wall. P3's own wording is two joined claims: staff must both *deny* being policy-makers **and** *affirmatively describe themselves* as part of a cohesive national implementation effort, in the same account, to score a clear 2. The scoring doc's own calibration example (C3) confirms the second clause is what caps real answers at 1: *"No, I wouldn't say I make policy... Weak: correct direction, but a bare denial... No trace of the positive half. Maximum 1."* This is the identical failure mode `SSTRF_RQ1_SCORING_SYSTEM_V2.md` §1 already diagnosed and fixed once for P5 ("the instrument was structurally incapable of returning 2") — P3 never received the same treatment.

**P5 shows a floor.** Even in its already-rewritten, single-clause form, no staff member across all 170 cells, in either scoring pass, ever scores a clear 2. This could be a genuine finding (the simulated staff never spontaneously volunteer that the policy itself is rigid) rather than an instrument defect, since P5 was already revised once. It is flagged here, not resolved.

This is reported as a **limitation of the RQ1 instrument**, discovered by inspecting the scored data, not as a revision to the confirmatory test. The confirmatory result in §1 stands as scored, against the rubric as pre-registered.

---

## 4. What this result does and doesn't mean

Per `SSTRF_RQ1_SCORING_SYSTEM_V2.md` §3, the ten trials share one fixture, one case, one model, and one prompt structure, differing only by seed. **They are repeated samples of one generative process, not ten independent tests of a hypothesis**, and no p-value derived from a chance model applies here. The correct reading of "0/10" is: across ten stochastic replications of the same documented CIEPSS School B scenario, the simulation did not reproduce, at the pre-registered threshold, the specific finding that staff describe themselves as co-owners of policy (P3) or perceive the policy itself as rigid (P5) — while it did reliably reproduce staff absorbing and transmitting the policy's authority (P1, P2 both essentially max out across all ten trials).

### 4.1 The dissociation, and why it is a finding rather than an excuse

**Added 2026-09-11. The scored result in §1 is unchanged; this is interpretation.**

Inspection of `ciepss_school_b.yaml` after scoring establishes that all eight personas shared a single YAML anchor (`&neutral_calibration_prior`) and carried forty empty field declarations: `style_cues: ""`, `beliefs: {}`, `identity: {}`, `attitudes: {}`, `personal_history: {}`. The actors differed only by `persona_id`, `role`, `name` and `role_level`.

The configuration therefore supplied **structure** — role hierarchy, influence network, turn order — and supplied **no identity**. The results split along exactly that line:

| Proposition | Type | Result |
|---|---|---|
| P1 — where authority for innovation sits | structural | maxed out, all ten trials |
| P2 — the school level filters policy | structural | maxed out, all ten trials |
| P3 — how teachers regard themselves | identity | floored; 0 of 4 staff scored 2 in 9 of 10 trials |
| P5 — policy perceived as inflexible | perception | never scored 2 in 170 cells, either pass |

**Structure in, structure out. No identity in, no identity out.**

This is a clean input–output correspondence and it is evidence that the instrument reports what is present rather than what is expected. Consider the alternative: had eight personas with `identity: {}` and `beliefs: {}` reproduced P3 — agents reporting on how they regard themselves — that would have been alarming. It would mean the method generates plausible findings from nothing, and every positive result it ever produced would be suspect.

**The null on P3 and P5 is therefore partial evidence that the method does not confabulate.** For a methodological proof-of-concept, that is worth more than a clean pass would have been.

### 4.2 Standing caution

The above is a post-hoc explanation that fits: mechanistically plausible, visible in the fixture, and arriving after the results. *"Our null had a fixable cause"* is the most seductive story available in research, and it becomes more seductive the more elegant it gets.

**It remains a hypothesis until tested.** A re-run of the ten trials with differentiated personas, under a new pre-registration, converts it from story to evidence. That study must name its directional prediction for *every* proposition in advance, including the outcome that would falsify this reading — P1 and P2 dropping when personas are differentiated, which would indicate individuation interfering with structural reproduction, a different and more interesting problem than the one under test.

It must also state that P1 and P2 are saturated and carry no headroom, so the study's entire power sits in P3 and P5. Naming that in advance is what prevents the analysis from later being accused of finding its effect in the only place it had room to find one.

---

## 5. Complementary qualitative synthesis (exploratory — not part of the confirmatory test)

**Method.** All 40 staff elicitation responses (CIEPSS Appendix B, the 4 documented staff × 10 trials) were read in full and coded inductively for recurring challenge-themes, deliberately without mapping anything onto P1–P5. The 160-turn round transcripts were not incorporated in this first pass. This is a first test of the method, run at Mark's request, to see whether it surfaces anything the propositional rubric misses.

This section is descriptive, reported alongside the confirmatory result, and is never combined into it — the same logic `SSTRF_RQ1_SCORING_SYSTEM_V2.md` §6 already applies to the blind plausibility protocol.

**Recurring themes, in rough order of prominence:**

1. **The core operational collision: H1N1 health protocols vs. collaborative pedagogy.** Named in essentially every one of the 40 responses. STELLAR's mechanism runs on peer/group work; H1N1 protocols restrict grouping. Staff describe redesigning around it (rotating pairs, dyads, asynchronous feedback, staggered small groups) rather than treating it as a side issue. *VP, Trial D: "H1N1 health protocols directly constrain the collaborative pedagogy STELLAR requires. This isn't a workaround problem; it's a genuine conflict that requires active resolution."*

2. **"Protected time" as the credibility test.** Every role, at every level, distinguishes *promised* protected time from *timetabled* protected time, and treats the latter as the real signal of whether leadership is serious. *Teacher, Trial B: "seeing protected peer mentoring time appear in my actual timetable by Week 3... not aspirational language, but actual timetable changes."*

3. **Commitment language vs. execution language.** A specific, repeated distinction — leadership *announcing* intent doesn't move anyone; a dated, named, written deliverable does. *HOD, Trial E: "What shifted momentum was when she moved from commitment language ('I will release...') to execution language ('By end of day Friday, these three documents go live simultaneously...')."*

4. **Trust erosion from repeated naming without action.** Several trials (F, G especially) describe 15–20 rounds of naming the same constraint before concrete resolution, and staff explicitly say this pattern — not the constraint itself — is what damages trust. *Senior Teacher, Trial G: "Twenty rounds of naming the same constraint without concrete response eroded trust — not in the vision, but in leadership's ability to act."*

5. **Shift from consultation to co-design.** Staff consistently describe a move from "being asked for feedback that leadership then decides on" to "naming problems together, solving together" via working groups — and treat this shift itself as the operative change, more than the pedagogy. *HOD, Trial E: "we've moved from consultation... to co-design. That's what sustains implementation."*

6. **Fidelity drift under adaptation.** A recurring worry that redesigning practices to fit H1N1 constraints could quietly hollow out the pedagogy into "compliance theater" rather than preserving its intent. *VP, Trial F: "we need enough structure that adaptations preserve pedagogical intent, not just reduce workload."*

7. **Equity risk from staged/phased rollout.** Piloting some elements before others creates inconsistency across departments/cohorts, which several staff flag as a fairness question, not just a sequencing detail.

8. **Assessment misalignment with external accountability.** Concern that formative, lower-stakes assessment could collide with MOE/external standardized expectations, risking a reversion to test-prep if that alignment isn't resolved explicitly.

9. **Parent anxiety and communication needs.** Multiple staff flag that parents may read reduced high-stakes assessment as reduced rigor, and treat parent communication as a live implementation task, not an afterthought.

10. **Sustainability beyond the current crisis, and leadership-dependency.** Several staff explicitly ask what happens to the collaborative, responsive culture if the current VP moves on, or once the immediate H1N1 pressure passes — flagging that the gains look person-dependent rather than structurally embedded.

11. **Measurement ambiguity for soft constructs.** The VP explicitly names that "values alignment" and "collaborative capacity" are hard to measure reliably, and multiple staff push for concrete, observable markers (protected-time logs, mentoring completion rates) over reassurance.

12. **Uneven staff readiness.** A minority-but-present theme: not all teachers take to the collaborative/formative shift at the same pace, and a few responses note the risk that some staff read the reform as implicit criticism of prior practice.

13. **Dependency on district/MOE for resourcing and protocol flexibility.** Recurring escalations beyond the school itself — for explicit MOE guidance on H1N1 duration, or district curriculum support — with staff naming this as a real constraint on what school-level leadership can unilaterally fix.

14. **Psychological safety to push back.** Named directly by more than one HOD/senior-teacher response as a specific, fragile enabling condition: leadership explicitly inviting dissent rather than treating it as resistance. *HOD, Trial A: "HODs need permission to push back... create explicit space for professional dissent, and act on it visibly."*

**What this is worth.** Themes 1–4 are strikingly consistent across all four roles and all ten trials — that consistency is itself informative about what the simulation reliably produces (a specific, coherent implementation-tension narrative), independent of whether any of it satisfies P1–P5's specific thresholds. Themes 2–3 in particular line up with what §3 already found structurally wrong with P3 and P5: staff are extremely articulate about the *operational mechanics* of implementation (which is what P1/P2/P4 capture) and comparatively terse about *self-identity as a policy actor* or *the policy's own rigidity* (P3/P5) — the two propositions asking about something these responses just don't dwell on, regardless of how good the response is.

---

## 6. Blind plausibility protocol (§6) — status check

`SSTRF_RQ1_SCORING_SYSTEM_V2.md` §6 pre-registers a separate, descriptive arm: 6–8 outside practitioners blind-rating simulated vs. documented CIEPSS reports for plausibility. It's explicitly the correct outlet for "this reads as genuinely plausible" as evidence, reported *alongside* but never combined with the confirmatory result above. As of the pre-reg signature (2026-08-25) this was flagged as "the longest lead item... should be in progress now." Status needs to be confirmed with Mark.

---

## 7. Recommended framing for the thesis

Report §1 as the confirmatory RQ1 finding, exactly as scored, with the calibration-gate history and human-only escalation disclosed per pre-reg. Report §3 as a named limitation of the v2 instrument, discovered post hoc from the scored data — legitimate to flag, not a basis for rescoring. Use §5 as descriptive characterization of what the simulation does and doesn't reproduce, explicitly labeled non-confirmatory. If the plausibility panel (§6) completes, it's the strongest complementary evidence available and stands entirely independent of this result.
