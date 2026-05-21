# senna-iter-2 closeout — Controls plain-English + Advanced options

**Date:** 2026-04-20  
**Scope:** `HANDOFF_SENNA_ARC1.md` § senna-iter-2.

## Shipped

- Controls (Set Up & Run) form: labels and helper text per mapping table; AI model option labels localized to plain English.
- **Advanced options** — `<details>` / `<summary>` containing: reproducibility seed, roster CSV, participant pool CSV, pool selection mode (when pool present), full auto-stop / consensus block with new sensitivity + confirmation copy.
- Removed visible “Iteration N” references, doc path link, `config_snapshot` jargon in warnings, and inline `<code>` field names from user-visible Controls copy.
- Primary fields reordered: scenario → rounds → turn-taking → speakers (if rotating) → participant count → AI model → advanced → start.

## Verification

- `npm run build` — PASS  
- Form request payload unchanged (same field names to API).

## Notes

- Population helper text paraphrases draw behaviour without snake_case or internal identifiers.
