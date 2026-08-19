# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active iteration** below. When finished (tests pass, commit, closeout), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

**Do not** start Arc 11 or new features in this session.

---

## Active task — Arc 10 independent review blockers B1–B6

| Field | Value |
|-------|--------|
| **Type** | Architect review fix — **not** a new iteration |
| **Branch** | `main` |
| **Trigger** | [`docs/reviews/independent-review.md`](../reviews/independent-review.md) — Arc 10 **FAIL**, blockers B1–B6 |

### Priority order (Architect)

1. **B3 / B6** — MemBench evidence-preserving fixtures; committed canonical baseline bundle
2. **B4 / B5** — Judge parse invalid ≠ zero; interview completeness gate
3. **B1 / B2** — Two-round deterministic memory-context test; prompt-aligned inclusion logging

### Scope by blocker

| Blocker | Fix |
|---------|-----|
| **B3** | Extend four MemBench fixtures so each QA answer appears in memory; `validate_fixture_evidence()` + test |
| **B6** | Commit `backend/tests/fixtures/arc10/canonical_baseline_inputs.json`; `--from-canonical` on runner; regression test vs `ARC10_BASELINE.md` |
| **B4** | `resolve_judge_score()` → `unparseable` / `score=None`; no averaging invalid rows; parse-source counts in baseline |
| **B5** | `validate_interview_completeness()` before baseline; exact agents × 5 responses/scores |
| **B1** | Integration test: 2 rounds, `llm_concurrency_cap=1`, assert round-2 prior-turn inclusion |
| **B2** | Derive inclusion from prompt inputs; `visibility_policy` / `same_round_peer`; non-fatal persist; drop 10k fetch |

### Verification

```bash
cd backend && uv run pytest -q
# → 334 passed, 2 skipped

python scripts/run_arc10_diagnostics.py --from-canonical backend/tests/fixtures/arc10/canonical_baseline_inputs.json --write-baseline
```

### Out of scope

- Arc 11 implementation, export version bump, frontend

---

## Completed (do not redo)

- **senna-iter-45**–**48** feature work + iter-48 gate fix (`f572860`)
- Independent review B1–B6 fixes (this session)
