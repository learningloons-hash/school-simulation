# Handoff to Architect

**Ritual:** Builder fills this file when work is **complete** (tests pass, committed). Architect reviews against [`handoff-to-builder.md`](./handoff-to-builder.md) and posts verdict in chat.

**Status:** Ready for Architect review — `senna-iter-49`.

---

## Builder report — `senna-iter-49` Importance Scoring

| Field | Value |
|-------|--------|
| **Task** | `senna-iter-49` — importance scoring |
| **Branch** | `main` |
| **Commit** | _(pending)_ |
| **Date** | 2026-08-20 |

### Definition of Done

| Item | Done? | Notes |
|------|-------|-------|
| Flag off — fixed-seed regression | YES | Transcript signature stable; no scorer LLM calls |
| Flag on — every turn scored + exported | YES | Scores/sources on transcript + CSV; audit in config_snapshot |
| Parse provenance (`model_parsed` / `repaired` / `fallback`) | YES | `llm/importance_parse.py` |
| Both batching modes + cost report | YES | See cost table below |
| `EXPORT_VERSION` → 12 | YES | Transcript columns additive |
| Closeout doc + ablation framing note | YES | `senna-iter-49-closeout.md` |

### Verification

```text
cd backend && uv run pytest tests/test_senna_iter49_importance_scoring.py -q
→ 11 passed

cd backend && uv run pytest -q
→ 351 passed, 2 skipped
```

### Cost (both modes)

| Mode | Extra input tokens | Extra output tokens | Wall-clock (fixture run) |
|------|-------------------:|--------------------:|-------------------------:|
| `per_turn` | 40 | 16 | ~0.15s |
| `per_round_batch` | 24 | 16 | ~0.12s |

Fixture: 2 tier-1 agents × 2 rounds, stub LLM (`test_cost_delta_both_modes`).

### Self-assessment

- **Ready for review:** YES
- **Open questions:** Scorer uses same routing as main turns; no separate profile id yet (acceptable for iter-49 ablation).
