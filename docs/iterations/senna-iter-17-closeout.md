# senna-iter-17 closeout — Compare Runs (ExperimentConsole) plain language

**Date:** 2026-04-22  
**Scope:** `docs/handoffs/HANDOFF_SENNA_ARC4.md` § senna-iter-17 (Arc 4).

## Shipped

**File:** `frontend/src/components/ExperimentConsole.tsx`

- Local `sectionHeadingStyle` (same spec as `App.tsx`); all named section titles use styled `<div>`s — no `<h2>` / `<h3>`.
- **`shortStatusLabel`** imported from `frontend/src/lib/runStatusCopy.ts` (no duplication).
- **`strategyLabel(s)`** with handoff map; fallback to raw `s` for unknown backend values. Sampling `<option>` **values** unchanged; visible text uses labels.
- **Comparison metric** `<select>` **values** unchanged; **labels** use plain-English map. Sparkline caption uses **`comparisonMetricLabel`** (same map).
- Create flow: new intro, form labels (comparison name, policy scenario, reproducibility seed, discussion rounds, participants, auto-stop copy), **Runs to compare**, placeholders, **Add run** / **Start comparison** / **Running…**, **Comparison ID** + monospace fragment (`slice(0, 14)…` when `lastExperimentId` is set).
- **Metric trends:** status line `Run group {id.slice(0,10)}… · {shortStatusLabel(...)}`; **Chart by** selector; details summary **All metrics by round**; table cells expanded to line-broken readiness/agreement/adoption/etc.; column subheaders use **`formatTokensCost`** (`Tokens: {total} · $…` or **Free (local model)** / **—**, aligned with Run Details in `App.tsx`).
- **Run results:** strategy + status labels; **Consensus at Round n** / **All n rounds**; per-run economics **`experimentRunEconomicsSuffix`** (`~{total} tokens · …`).
- **Previous comparisons:** `shortStatusLabel`, id span styling, **Load** button.
- **Compare two individual runs:** new description and placeholders; headers **Run A ·** / **Run B ·**; **Status:** + `shortStatusLabel`; round lines **Round n: Adoption … · Disagreements … · Consistency …**.
- Borders: all former `#ddd` / `#eee` → `#E5E3DC`; error colour **coral** → **`#E05252`**; export link borders aligned to `#E5E3DC`.

**Supporting types:** `ExperimentRunRow`, `RunEconomics` imported from `../lib/api` for helpers.

## Verification

- `npm run build` in `frontend/` — **PASS**

## Grep notes

From repo root (examples):

- `rg 'GET /|POST /' frontend/src/components/ExperimentConsole.tsx` — no matches
- `rg '#ddd|#eee' frontend/src/components/ExperimentConsole.tsx` — no matches
- `rg '<h2|<h3' frontend/src/components/ExperimentConsole.tsx` — no matches

Snake_case strategy/metric strings remain only in **types**, **maps**, **`value=` attributes**, **`useState` defaults**, and **data field access** (e.g. `met.implementation_readiness`), not in user-visible labels.

## Not in scope

- senna-iter-18+; backend; other tabs.
