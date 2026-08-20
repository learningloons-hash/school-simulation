# Senna iter-49 closeout — Importance Scoring

**Spec:** [`docs/handoffs/handoff-to-builder.md`](../handoffs/handoff-to-builder.md) **`senna-iter-49`**
**Arc:** 11 — Memory Architecture
**Date:** 2026-08-20
**Status:** **CLOSED** (pending Architect review)

## Delivered

- Dedicated importance scorer LLM call (1–10) at turn write time; **not used for retrieval** (iter-50).
- Config flags (default off): `importance_scoring_enabled`, `importance_prompt_version`, `importance_scoring_mode` (`per_turn` | `per_round_batch`).
- Parse provenance: `model_parsed` / `repaired` / `fallback` via `llm/importance_parse.py`.
- Persisted on `agent_turns`: `importance_score`, `importance_source`; export + `EXPORT_VERSION` **12**.
- `importance_scoring_audit` + token totals merged into `config_snapshot` at run end.

## Ablation framing (required note)

**No published work isolates Park's importance prompt.** This iteration pre-registers an ablation of an unevaluated mechanism — we are **not** adopting received best practice. Scores are recorded for later comparison against the Arc 10 measured baseline; they do not yet change agent behavior.

## Cost delta (fixture run: 2 agents × 2 rounds, stub LLM)

| Mode | Extra input tokens | Extra output tokens | Wall-clock |
|------|-------------------:|--------------------:|-----------:|
| `per_turn` | 40 | 16 | ~0.15s |
| `per_round_batch` | 24 | 16 | ~0.12s |

Batch mode uses one scorer call per round vs one per turn; token totals scale accordingly on this fixture.

## Verification

```bash
cd backend && uv run pytest tests/test_senna_iter49_importance_scoring.py -q
# → 11 passed

cd backend && uv run pytest -q
# → 351 passed, 2 skipped
```

## Out of scope (unchanged)

- Weighted retrieval — iter-50
- Reflection — iter-51
- Default changes to `working_memory_last_k` / `peer_context_max_chars`
