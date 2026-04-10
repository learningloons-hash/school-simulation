# Iteration 10 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Theme:** Thin **AgentContext v1** + interaction **simulation_mode** (`full_round_robin` | `sample_k_per_round`).

## Shipped

| Item | Detail |
|------|--------|
| `AgentContextV1` | [`simulation/agent_context.py`](../../backend/src/mirofish_backend/simulation/agent_context.py) — `version`, `slot_index`, `demographics`, `group_ids`; `to_prompt_demographics()`. |
| `AgentInstance` | Holds `context`; `demographics` property for compatibility. |
| Interaction v2 (MVP) | `_agents_for_round` — seed-stable subset for `sample_k_per_round`; orchestrator runs turns only for that subset per round. |
| API | `POST /simulations/run`: `simulation_mode`, `speakers_per_round` (1–50); `config_snapshot` adds `agent_context_version`, `simulation_mode`, `speakers_per_round` (**`null`** when `full_round_robin` so unused K default does not mislead analysts). |
| Traceability | End-of-round **`agent_state_snapshots.spoke_this_round`** (0/1) + JSON `state_timeline[].agents[].spoke_this_round` — distinguishes “not sampled this round” from missing data. |
| Frontend | Run tab: interaction mode + K; Live dashboard shows `simulation_mode` / K. |
| ADR | [`docs/adr/ADR-001-iteration-10-11-contracts.md`](../adr/ADR-001-iteration-10-11-contracts.md) — Interface section filled; status accepted for Iter 10 slice. |

## Not in scope (defer)

- Group-based **who hears whom** (visibility graph) — still broadcast/reply among **selected** speakers only within the round subset.
- Non-speaker state **aggregation** or passive updates when not sampled.
- Iteration **11** population import / weighted tables.

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q
cd ../frontend && npm run build
```

## Post-gate validation (session 2026-04-04)

- **Run id:** `ad901483b0a840689c71debb771cf0c1` (FSBB comparator, `agent_limit` 4, `full_round_robin`, 2 rounds).
- **DB / transcript:** All four agents have **two** turns each (8 rows total). A perceived “missing” fourth speaker was **not** an orchestration skip.
- **Model behavior:** Visible “Thinking Process” / long CoT can still appear (local model non-compliance with prompt ban). **`llm_max_tokens`** can truncate mid-reasoning — treat as **LLM / limits**, not engine routing.
- **Backlog (not Iter 10):** Stronger post-process CoT strip; clearer peer labels when roles duplicate; formal **IAD-style rules of engagement** in code (later iteration).

## Architect notes (post-close; incorporated vs deferred)

1. **Who spoke vs silent** — **Incorporated:** `spoke_this_round` on each end-of-round agent snapshot (export + `state_timeline`). Legacy rows may have `null` before migration.
2. **Interaction plan uses subset positions** — **Documented** in `_build_interaction_plan` docstring: small K ⇒ broadcast + meeting_note only; K ≥ 3 adds replies; roles vary by sampling order. Cite in thesis methods.
3. **`interaction_last_k` uses full roster size** — **Comment** in orchestrator; **Iteration 12** perf review if prompt windows grow too large (clip still applies).
4. **`effective_provider` per turn** — **Deferred Iteration 12** (persist + export); remains log-only today.
5. **`speakers_per_round` in `config_snapshot` for full robin** — **Incorporated:** stored as JSON **`null`** when `simulation_mode` is `full_round_robin`.

## Self-check (architect checklist, draft)

- ADR linked and Interface concrete — yes (`ADR-001`).
- Two modes behind API flag — yes (`simulation_mode`).
- Reproducibility — subset selection is deterministic given `random_seed` + `round_number`.
- Non-speaking agents — documented: state unchanged for non-sampled agents in a round.
