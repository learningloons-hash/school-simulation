# Senna Project — Claude Instructions

## Review Protocol
- **No documents** unless Mark explicitly approves. Arc and iteration reviews go in chat only.
- **Succinct replies** — summarise key points and follow-ups inline. Conserve credits.
- After each arc: verdict, what landed well, issues found, follow-up actions. Max ~8 lines.

## Project Context
- Codebase is `mirofish-mvp/`; the product is called **Senna** (renamed from MiroFish MVP)
- Backend (FastAPI, port 8100); **Arcs 1–5** left the API surface stable for UX work — **Arc 6** (`HANDOFF_SENNA_ARC6.md`) intentionally changes the backend (round summaries, transcripts, prompt caps) — no frontend in that arc unless a later handoff says so
- Frontend (React/TypeScript/Vite, port 3100) — Arcs 1–5 UX redesign complete
- Arc workflow: Claude designs handoff → Cursor Architect seeds → Cursor Builder implements → Cursor reviews → Claude reviews arc

## Design System
- Font: `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- Palette: bg `#F7F6F2`, card `#FFFFFF`, text `#1A1A1A`, secondary `#595F6B` (page / `theme.ts` token; `#6B7280` still used for muted text on white cards where noted), accent `#4A6FA5`, border `#E5E3DC`, success `#4CAF82`, error `#E05252`
- 75% Apple minimal, 25% practical warmth — labels and helper text stay visible where they help

## Arc Status
| Arc | Theme | Status |
|-----|-------|--------|
| 1 | Brand & Language Foundation | ✅ CLOSED |
| 2 | Run Setup Experience | ✅ CLOSED |
| 3 | Live Experience & Results | ✅ CLOSED |
| 4 | Advanced Features Accessible | ✅ CLOSED |
| 5 | Visual Design & Polish | ✅ CLOSED |
| 6 | Context Bounding & Simulation Transcripts | ✅ CLOSED |
| 7 | Model Portability Foundation | ✅ CLOSED (GM PASS) — [`docs/handoffs/HANDOFF_SENNA_ARC7.md`](docs/handoffs/HANDOFF_SENNA_ARC7.md) (`senna-iter-30`–`34`) |
| 8 | Model Ecosystem and Guardrails | ✅ CLOSED (GM PASS) — [`docs/handoffs/HANDOFF_SENNA_ARC8.md`](docs/handoffs/HANDOFF_SENNA_ARC8.md) (`senna-iter-35`–`39`) |
