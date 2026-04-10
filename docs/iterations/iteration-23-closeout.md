# Iteration 23 closeout — Tier-aware orchestrator

**Date:** 2026-04-06  
**Status:** Shipped — **Architect PASS** (2026-04-06); **handoff optional follow-ups** applied in a later pass (same doc § *Optional backlog from HANDOFF*).  
**Theme:** Branch `_run_one_turn` by `AgentInstance.fidelity_tier`: Tier 1 full prompts + LLM (unchanged); Tier 2 `simplified_persona_prompt` + half peer context; Tier 3 no LLM in-turn, heuristic marker row (`effective_provider` `heuristic`, `latency_ms` 0). At ship time Tier-3 **bulk** state was unchanged until **Iteration 24** (post-round heuristic — see [`iteration-24-closeout.md`](iteration-24-closeout.md)).

## Post–Architect follow-up (Pre–Iteration 24)

- **`EXPORT_VERSION`** centralized in `export_bundle.py`; `api/simulations.py` and `api/capabilities.py` import it. Tests `test_iteration16.py` / `test_iteration20.py` assert against `EXPORT_VERSION` (avoids stale duplicate literals).

## Optional backlog from `HANDOFF_TO_BUILDER.md` (Iteration 23 PASS — applied)

Per architect **optional improvements** (non-blocking), implemented after the gate:

1. **Tier read** — `orchestrator._run_one_turn` uses `tier_raw = agent.fidelity_tier or 1` (no redundant `getattr` on `AgentInstance`).
2. **Named Tier-1 regression** — `test_tier_one_uses_full_system_prompt` in `tests/test_iteration23.py`: full template contains `Persona identity and stance:` and not `Fidelity: Tier 2`.
3. **Build hygiene** — `backend/.gitignore` includes `build/` (setuptools / `python -m build` mirror).
4. **Parallel LLM–safe mixed-tier assertions** — `test_mixed_tiers_llm_only_for_one_and_two` classifies Tier-1 vs Tier-2 prompts by content (not `llm_calls[0]` order), because **`asyncio.gather` completion order is not turn order**.

## Shipped

| Item | Detail |
|------|--------|
| **`llm/prompt_templates.py`** | `simplified_persona_prompt()` — role, style, beliefs, internal state only; omits identity/attitudes/history/psych/implementation/groups. |
| **`simulation/orchestrator.py`** | Tier 3 early path: `insert_agent_turn` with `raw_response` marker, `effective_provider` `heuristic`, `latency_ms` 0, no `llm_complete`. Tier 2: `peer_context_max_chars // 2` for memory + recent interactions; simplified system prompt. Tier 1: prior behavior. |
| **`db/schema.py` + `repo.py`** | `agent_turns.fidelity_tier` (default 1); `insert_agent_turn` + poll + export bundle SELECTs include field. |
| **`export_bundle.py`** | Changelog **v6**; empty transcript CSV header includes `fidelity_tier`. |
| **`api/simulations.py` + `capabilities.py`** | `export_version` from **`export_bundle.EXPORT_VERSION`** (**`"6"`**). |
| **Frontend** | `SimulationTurn.fidelity_tier`; Transcript tab shows “fidelity tier N”. |

## Out of scope (as specified at Iteration 23 gate)

- Real Tier-3 **post-round** state heuristic — shipped as **Iteration 24** (`hybrid_core_remainder`, `remainder_config`, etc.).  
- New sampling strategies beyond Iteration 22 set — **Iteration 24** added `hybrid_core_remainder`.

## Gate evidence (at closeout)

```bash
cd backend && uv run pytest --tb=short -q
# 153 passed, 1 skipped (includes Tier-1 named regression + parallel-safe mixed-tier test)
cd ../frontend && npm run build
```

## Tests (`tests/test_iteration23.py`)

| Test | What it verifies |
|------|-----------------|
| `test_simplified_persona_prompt_omits_deep_blocks` | Tier-2 system text excludes psych/identity/implementation |
| `test_tier_one_uses_full_system_prompt` | Tier-1 full template invariant vs Tier-2 marker (explicit DoD regression) |
| `test_mixed_tiers_llm_only_for_one_and_two` | `fidelity_tiers [1,2,3]`: two LLM calls; transcript tiers; Tier-3 heuristic row; export bundle; prompts classified without assuming gather order |
| `test_tier_three_preserves_prior_state_across_rounds` | All Tier-3 run: no LLM; timeline state matches persona initial (no Tier-1/2 speakers → no post-round heuristic in Iteration 24) |

## Next

**Pre–Iteration 24 fix:** ~~centralize `EXPORT_VERSION`~~ **done** (§ Post–Architect follow-up).

**Iteration 24:** ~~Tier-3 heuristic, `hybrid_core_remainder`, `agent_limit` 300~~ **done** — [`iteration-24-closeout.md`](iteration-24-closeout.md).

**After 24 (Opus build order):** **Iteration 26** before **25** — [`HANDOFF_TO_BUILDER.md`](../handoffs/HANDOFF_TO_BUILDER.md).
