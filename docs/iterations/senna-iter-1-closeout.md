# senna-iter-1 closeout — Rename Senna → Senna

**Date:** 2026-04-20  
**Scope:** Brand rename per `docs/handoffs/HANDOFF_SENNA_ARC1.md` § senna-iter-1.

## Shipped

- `frontend/index.html` — `<title>Senna</title>`
- `frontend/package.json` + `frontend/package-lock.json` — package name `senna-frontend`
- `frontend/src/App.tsx` — builtin scenario display names no longer use “(MVP)” suffix (product rename; not “Senna”)
- Product chrome (`SennaHeader`) shipped in the same arc gate as **senna-iter-5**; iter 1’s interim `<h1>Senna</h1>` was not left as a separate intermediate commit.
- `frontend/src/lib/api.ts` — JSON download default filename `senna_run_{id}.json`
- `docs/handoffs/HANDOFF_TO_BUILDER.md` — bootstrap line: Senna (formerly Senna)
- `docs/SESSION_STATE.md` — product name Senna in session header / current status

## Verification

- `grep -r "Senna" frontend/src/` — zero matches
- `npm run build` in `frontend/` — PASS

## Notes

- Backend crate / imports (`senna_backend`) intentionally unchanged per handoff.
