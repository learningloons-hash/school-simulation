# HANDOFF_SENNA_SENSITIVITY_PILOT — Configuration Sensitivity Pilot

**Owner:** GM-F → Senna-Ops → Cursor Architect → Cursor Builder
**Date:** 2026-09-15
**Status:** **DRAFT.** Written by Senna-Ops from GM-F's compressed ruling (Ops status-check response, 2026-09-15). GM's original full design was given to Mark in chat; Ops does not have that text verbatim and was instructed to draft from the summary and flag gaps rather than invent programme content. **Do not build against this file until §4's open items are closed by Mark/GM.**
**Predecessor:** GM-F ruling, Ops status check, 2026-09-15 — sequence item 2: "SENSITIVITY PILOT — 36 runs, ~US$12 — next run, before the CIEPSS re-run."

---

## 0. Why this runs before the CIEPSS re-run

GM-F's reasoning, verbatim: the pilot costs about twelve dollars and tells us whether configuration governs output at all. If seed noise swamps configuration, the CIEPSS re-run is pointless and would spend a pre-registration finding that out. This pilot is diagnostic/utility-track — it is not a validity run and does not touch `ciepss_school_b`.

## 1. Design (parameters GM-F gave)

Factorial: **3 programmes × 2 contexts × 2 rosters × 3 seeds = 36 runs.**

| Dimension | Given | Status |
|---|---|---|
| Programmes (3) | ALP CaRE, Positive Education, + one more | **GAP — third programme not named in the compressed ruling.** |
| Contexts (2) | Not specified | **GAP.** Working assumption: baseline vs adverse, mirroring the `sq_reading_culture` / `sq_reading_culture_adverse` precedent from Part B — needs GM/Mark confirmation, not an Architect guess. |
| Rosters (2) | Not specified | **GAP.** Unclear whether this is neutral-prior vs differentiated (the Arc 11/Part C persona-differentiation axis) or two distinct staffing rosters. |
| Seeds (3/cell) | Not specified | **GAP.** Per standing pre-reg discipline (iter-58), should be distinct from all development seeds already used in Arc 11/12 and Part C runs. |
| Tier | Not specified this round | Recommend **Anthropic tier**, consistent with the Arc 12 confound-test precedent ("the tier the study will use, not the local model"). Flag for GM confirmation. |

**Fixtures — ALP CaRE and Positive Education, "with inline event lists":** Ops has no source material for either programme. Event content must either be authored in-product (same discipline as `sq_reading_culture`'s `context:` blocks — "authored in-product," not reproduced from a copyrighted or MOE source) or sourced and run through the same no-reproduced-source-text check ARC12 §1.1 applied to `ciepss_school_b`. **Do not draft event lists from general knowledge of real MOE programmes without that check — this is a live risk of importing protected material into the public repo.**

## 2. Statistic and decision rule

- **Single statistic: variance decomposition** — attribute output variance to programme, context, roster, and seed/residual components.
- **GAP — dependent variable(s) not specified.** Candidates consistent with prior Senna diagnostics: architectural interview category scores (Arc 11/12 precedent), per-round support/dispersion measures (individuation-report precedent), or a proposition-style score. Needs GM to name this before Architect scopes the harness.
- **GAP — the decision rule itself.** GM's instruction is that the rule must be fixed before the run (no post-hoc threshold-picking), but the compressed ruling states only that a rule exists, not its content (e.g., what variance-share counts as "configuration governs output" vs "seed noise swamps it"). **This is the single most important gap — nothing should run until it's written down and signed off.**

## 3. Cost and scope

- ~US$12, 36 runs, per GM-F.
- Diagnostic/mechanics only — not a study run. No reading, citing, or scoring of substantive transcript content beyond the variance statistic itself, consistent with the Arc 12 standing constraint, unless GM rules otherwise for this pilot specifically.

## 4. Open items — close before Architect builds anything

1. Name the third programme (only ALP CaRE and Positive Education given).
2. Confirm the two context conditions.
3. Confirm the two roster conditions.
4. Confirm seed values (3, unused elsewhere).
5. Name the dependent variable(s) for the variance decomposition.
6. Write the decision-rule threshold, fixed in advance.
7. Confirm the fixture-content sourcing/clearance path for both programmes.

## 5. DoD (once §4 closes)

- Fixtures built for both (three) programmes, passing the no-reproduced-source-text check.
- 36 runs complete cleanly — zero `[LLM error]` entries, zero context-length failures.
- Variance decomposition computed and reported against the pre-fixed decision rule.
- Written recommendation, per the fixed rule: does configuration govern output, or does seed noise swamp it — this determines whether the CIEPSS re-run (sequence item 4) proceeds.

---

**Standing, unchanged:** neutral-prior discipline holds for `ciepss_school_b` — no invented persona attributes for the case that carries the validity claim. This pilot and any differentiated-roster work are utility-track only and do not touch that discipline.
