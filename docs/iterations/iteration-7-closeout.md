# Iteration 7 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Status:** Implementation complete (MVP arc Iterations 5–7 closed).

## Deliverables

### Richer personas (backward compatible)

- YAML optional keys per persona: **`psychological_profile`**, **`implementation_profile`** (arbitrary key/value maps).
- `PersonaTemplate` adds two dict fields defaulting to `{}`; `_persona_from_mapping` loads them.
- `build_system_prompt` appends labeled sections when non-empty.
- Example on PSLE principal in `scenarios/data/psle_reform_mvp.yaml`.

### Hybrid LLM routing

- **`llm_provider`**: `lmstudio` | `anthropic` | **`hybrid`**.
- **Semantics**: `hybrid` → **Anthropic** when **`turn_index == 1`** (first agent each round — broadcast), **LM Studio** for **`turn_index >= 2`**.
- **`resolve_effective_provider`** in `llm/router.py`; orchestrator logs each turn: `routing_mode`, `effective_provider`.
- **`config_snapshot`**: `hybrid_routing_policy: "frontier_first_turn_of_round"` when hybrid; `model_used` like `hybrid:<local>|<frontier>`.
- **Bugfix**: orchestrator always receives real **`lmstudio_model`** id (not the composite `model_used` string) for local API calls.

### Polish / orientation

- **`references/ARCHITECTURE.md`**: short map of modules and hybrid behavior.
- Frontend: **LLM routing (optional)** on Run tab.

### Deferred / not in scope

- Opus review hardening (credits exhausted — no new review batch).
- Per-turn **`effective_provider`** column in DB (would aid analysis; can add later).

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q   # 27 passed
cd ../frontend && npm run build
```

## Manual note

Hybrid runs need a valid **`ANTHROPIC_API_KEY`** on frontier turns; missing key surfaces as `[LLM error]` on turn 1 of each round.
