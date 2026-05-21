# senna-iter-19 closeout — Policy Scenarios (ScenarioWizard) accessibility

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC4.md` § senna-iter-19; `docs/handoffs/HANDOFF_TO_BUILDER.md` (Senna UX table).

## Shipped

**File:** `frontend/src/components/ScenarioWizard.tsx`

- Intro copy; **`STEPS`** renamed (Participants, Knowledge base, etc.).
- Step pills: **`#EEF3FA` / `#4A6FA5`** when active, **`#FFFFFF` / `#E5E3DC`** when inactive.
- **Start from a template:** load/clone labels; catalog options **`catalogOptionLabel`** — `(custom)` only for user scenarios, no `(builtin)`; generate-from-description placeholder + **Generate** button; clone block **Copy a scenario**, **New scenario ID** + helper, placeholder **e.g. my-reform-scenario**.
- **Basics:** Scenario ID + helper; radios **Create new scenario** / **Update existing scenario**; **Choose scenario to edit**.
- **Participants:** card border **`#E5E3DC`**; placeholders; role options **Principal / Middle manager / Teacher** (values unchanged); **Seniority (1–3)**; beliefs block with grey helper + monospace textarea; **AI Fill** + tooltip; **+ Add … field**; **Remove participant** / **Add participant**; attributes rail **`#E5E3DC`**.
- **Groups:** placeholders **group-id**, **Group name**, **Brief description**.
- **Knowledge base:** checkbox + helper; path **`#6B7280`** `<code>`.
- **Review:** preamble line; **Save scenario** / **Save changes**; Export YAML unchanged.
- Success / error alerts: green and red bordered panels per handoff.
- Outer section: **`#E5E3DC`** border, **`#FFFFFF`** background.

**Copy-only behaviour tweaks (no API contract change):** load/generate success strings and brief length error reworded to avoid internal path/slug jargon where reasonable; invalid-beliefs JSON error message plain English.

## Verification

- `npm run build` in `frontend/` — **PASS**

## Grep notes

- `rg '#ddd|#eee|#eef' frontend/src/components/ScenarioWizard.tsx` — no matches (replaced with palette / `#E5E3DC` / `#EEF3FA` as specified).
- Banned jargon in **labels/placeholders** per DoD removed; `persona_id` / `group_id` remain as **TypeScript + data field names** only.

## Not in scope

- senna-iter-20; backend.
