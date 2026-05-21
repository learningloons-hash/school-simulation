# senna-iter-18 closeout — Quality Notes (validity tab) plain language

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC4.md` § senna-iter-18; `docs/handoffs/HANDOFF_TO_BUILDER.md` § Senna UX (iter-18 starter).

## Shipped

**File:** `frontend/src/App.tsx` — `tabPanelStyle("validity")` region only.

- Section title **Quality notes** (`<h2>` with Arc 4 interim styles per handoff).
- Intro paragraph and session hint unchanged in behaviour; copy updated per spec.
- Form card: `border` `#E5E3DC`, `borderRadius` 10, `background` `#FFFFFF`, `padding` 20.
- Labels / placeholders / button: Realism & Accuracy scores & notes, Predictive score & notes, Other notes; rater placeholder `e.g. mark, reviewer-1`; score placeholders `0.0 – 1.0`; **Save quality note** / **Saving…**.
- Empty-submit message: **Add at least one score or note before saving.** (same `hasAny` gate as before — any of round, rater, scores, rubric fields, or general notes still enables save).
- **Saved notes:** `sectionHeadingStyle` heading; `emptyStateCardStyle` empty state; list borders `#E5E3DC`; header **Whole run** / **Round n**, optional rater (no “rater” prefix), date via `formatRunDate`; conditional Realism / Accuracy / Predictive lines; **Other notes:** for `notes`.
- `vnError` colour **coral** → **`#E05252`**.

**API:** `ValidityNoteCreate` / `createValidityNote` payloads unchanged (`face_score`, `construct_score`, `face_rubric`, etc.).

## Verification

- `npm run build` in `frontend/` — **PASS**

## Grep notes (sanity)

- User-facing labels in this section should not include the words *face*, *construct*, *validity*, *rater id*, or *rubric* as standalone jargon (code identifiers and API fields remain).

## Not in scope

- senna-iter-19+; `ScenarioWizard`; backend.
