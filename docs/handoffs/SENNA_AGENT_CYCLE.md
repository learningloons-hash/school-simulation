# Senna — GrandMaster / Architect / Builder agent cycle

**Purpose:** Single place for **GrandMaster**, **Cursor Architect**, **Cursor Builder**, and humans to learn the full gate loop without re-explaining it each session.

**Product:** Senna (`mirofish-mvp/`). **Arcs 1–5** UX work was **`frontend/`**-only; **Arc 6** and later arcs may touch **`backend/`** when their `HANDOFF_SENNA_ARC*.md` says so.

**Arc rule:** One arc is a bounded package of **at most five iterations**. GrandMaster plans the arc; Architect sequences and reviews each iteration; Builder implements one iteration at a time.

---

## Roles

| Role | Who | Job |
|------|-----|-----|
| **GrandMaster / GM** | Mark's strategy partner | Plans arcs, writes arc handoffs (`HANDOFF_SENNA_ARC*.md`), and reviews the entire arc after Architect marks the final iteration complete. |
| **Cursor Architect** | You in Cursor | Seeds Builder, **reviews** each iteration against the arc handoff, updates **sign-off** docs, points to next iter. |
| **Cursor Builder** | Separate Cursor chat | **Implements** one iteration spec only, runs build, writes **closeout**, updates **SESSION_STATE** Current Status. |

---

## Canonical files (always know these)

| File | Who updates | What it is |
|------|-------------|------------|
| [`docs/SESSION_STATE.md`](../SESSION_STATE.md) | **Builder** after each iter gate; **Architect** may adjust at arc boundaries | Cross-session truth: active arc, next iter, last gate, dates. |
| [`docs/iterations/senna-iter-N-closeout.md`](../iterations/) | **Builder** when iter N ships | What changed, verification, grep notes. |
| [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](./HANDOFF_SENNA_ARC7.md) (or prior arc handoffs) | **GrandMaster** — do not edit unless fixing a typo or explicitly revising scope | **Spec** for `senna-iter-NN` — single source of truth. Current model-portability arc: **Arc 7**. |
| [`docs/handoffs/HANDOFF_TO_BUILDER.md`](./HANDOFF_TO_BUILDER.md) | **Architect / human** when adding starters | **§ Senna UX** (Arc 4) + **§ Senna Arc 5** + **§ Senna Arc 6** — short paste blocks that **point** to the arc handoff (no spec fork). |
| [`docs/handoffs/HANDOFF_TO_ARCHITECT.md`](./HANDOFF_TO_ARCHITECT.md) | **Architect** after each **PASS** (or PASS_WITH_ISSUES) | Senna sign-off table, Opus arc verdict when received, “Next” pointer. |
| [`CLAUDE.md`](../../CLAUDE.md) (repo root) | **Builder** only when a handoff’s Definition of done says so (e.g. iter-20, iter-25) | Arc status table for Claude sessions. |

---

## Per-iteration cycle (every `senna-iter-N`)

### GrandMaster (before an arc starts)

1. Decide the arc theme and boundaries with Mark.
2. Keep the arc to **five iterations max**.
3. Write `docs/handoffs/HANDOFF_SENNA_ARC*.md` with each iteration's goal, scope, out-of-scope items, and Definition of Done.
4. Hand the arc to Cursor Architect. GrandMaster does not seed Builder directly unless Mark asks.

### Builder (end of work)

1. Implement **only** the active iteration section in [`HANDOFF_SENNA_ARC*.md`](./HANDOFF_SENNA_ARC7.md) (`### senna-iter-N` or `## senna-iter-N`, matching the active handoff).
2. Run the tests/build required by that iteration's Definition of Done.
3. Add **`docs/iterations/senna-iter-N-closeout.md`** — shipped summary, files touched, build result, optional grep notes vs Definition of done.
4. Update **`docs/SESSION_STATE.md`** § **Current Status** — e.g. “senna-iter-N complete”, “Next: senna-iter-(N+1)”, refresh **Last update date**, Arc in progress.
5. **Do not** edit `HANDOFF_TO_ARCHITECT.md` or arc handoffs unless the human asked for a doc fix.

### Architect (after Builder says done)

1. Read **closeout** + **diff** (or grep) against arc handoff **Definition of done** for that iter.
2. Re-run the relevant tests/build if you want independent confirmation.
3. Verdict: **PASS** / **PASS_WITH_ISSUES** / **FAIL** (chat or notes to Mark).
4. Update **[`HANDOFF_TO_ARCHITECT.md`](./HANDOFF_TO_ARCHITECT.md)** — Senna Arc sign-off table (add row or Architect column for iter N).
5. **Seed next Builder:** copy the right starter from [`HANDOFF_TO_BUILDER.md`](./HANDOFF_TO_BUILDER.md) or paste minimal bootstrap + link to `##` / `### senna-iter-(N+1)` in the arc handoff.
6. **Do not** paste the full arc spec into chat — point to `HANDOFF_SENNA_ARC*.md` (token-efficient, no drift).

---

## Per-arc cycle (when `senna-iter-…` arc completes)

1. **Architect:** Confirm last iter of arc **PASS**, tick **Definition of Arc Complete** in the arc handoff if used, add **completion record** there if the handoff has a slot for it.
2. **Builder (if last iter’s DoD requires it):** e.g. **`CLAUDE.md`** Arc row → CLOSED (iter-20, iter-25 per handoffs).
3. **SESSION_STATE:** **Architect** or **Builder** — set “Arc N complete”, “Arc N+1 next”, link to next `HANDOFF_SENNA_ARC*.md`.
4. **GrandMaster:** Arc review (chat-only is fine per `CLAUDE.md` Review Protocol). Verdict recorded in **`HANDOFF_TO_ARCHITECT.md`** (see Arc 4 § *Opus arc review* as template).
5. **Git push (after GM arc verdict is PASS or closed PASS_WITH_ISSUES):** **Architect or Mark** — commit all arc work and push to `origin` (see § Git push after arc close below). Do this **once per arc**, not after every iteration.
6. **Next arc:** GrandMaster writes the next `HANDOFF_SENNA_ARC*.md`; Architect then seeds Builder one iteration at a time.

---

## Git push after arc close

**When:** GrandMaster has reviewed the arc and the verdict is **PASS** (or **PASS_WITH_ISSUES** with follow-up merged and re-reviewed).

**Who:** Architect or Mark (Builder does **not** push unless explicitly asked).

**Pre-push checklist:**

| Check | Action |
|-------|--------|
| Secrets | No `.env`, `ANTHROPIC_API_KEY`, or API keys in staged files (`backend/.env.example` is OK — keys empty). |
| Runtime data | No `*.sqlite`, `backend/data/transcripts/`, `data/`, or run exports in the commit. |
| Tests | `cd backend && uv run pytest` — green (note count in commit message if helpful). |
| Frontend | `cd frontend && npm run build` — green when UI changed this arc. |
| Handoffs | `HANDOFF_TO_ARCHITECT.md`, `SESSION_STATE.md`, `CLAUDE.md` arc row, last iter closeout(s) updated. |

**Commands (from repo root):**

```bash
git status   # verify nothing under backend/data/transcripts or *.sqlite is staged
git add -A
git reset HEAD -- backend/data/transcripts backend/data/*.sqlite data/ 2>/dev/null || true
git commit -m "Senna Arc N: <short theme> (GM PASS, senna-iter-…)"
git push origin main
```

**Remote:** `https://github.com/learningloons-hash/mirofish-mvp` (private). Product name Senna; repo name may still be `mirofish-mvp`.

---

## Token discipline

- **Short chat + read repo handoff** beats pasting multi-kB specs in chat: one source of truth in git.
- Starters in **`HANDOFF_TO_BUILDER.md`** should **link** to the arc handoff heading (`###` or `## senna-iter-NN`), not duplicate the full spec.

---

## Thesis vs Senna (parallel tracks)

- **Senna** iterations: `senna-iter-*`, arc handoffs `HANDOFF_SENNA_ARC*.md`.
- **Thesis / backend** iterations: `iteration-*`, [`HANDOFF_TO_BUILDER.md`](./HANDOFF_TO_BUILDER.md) thesis starters — different numbering. Do not mix closeout names.

---

## Quick links

- Latest closed arc: **Arc 8** — [`HANDOFF_SENNA_ARC8.md`](./HANDOFF_SENNA_ARC8.md) (GM PASS). Next arc: await GM `HANDOFF_SENNA_ARC9.md`.
- Builder starters: [`HANDOFF_TO_BUILDER.md`](./HANDOFF_TO_BUILDER.md) or a minimal Architect seed that links to the active arc section.
- Architect sign-off / Opus: [`HANDOFF_TO_ARCHITECT.md`](./HANDOFF_TO_ARCHITECT.md).
