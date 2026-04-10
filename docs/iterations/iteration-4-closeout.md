# Iteration 4 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Status:** Implementation complete; ready for architect (Opus) review.

This document records **all** Iteration 4 scope: the original review-gap batch plus follow-on fixes from integrated testing with LM Studio.

---

## Original plan (review gaps → shipped)

| Tag | Deliverable |
|-----|-------------|
| **C3** | Structured state: `<state>{...json...}</state>` in user prompt; `llm/state_parse.py`; `_apply_state_from_response` with keyword fallback (`_apply_state_update_keyword`). |
| **C2** | Default `llm_max_tokens=1024`; `POST /simulations/run` optional `max_tokens` (64–8192); threaded into orchestrator and `config_snapshot`. |
| **C5** | `llm/router.py` + `llm/claude_client.py`: `lmstudio` \| `anthropic` (Anthropic Messages API via httpx). Settings: `llm_provider`, `anthropic_api_key`, `anthropic_model`. |
| **I2** | YAML scenarios under `backend/src/mirofish_backend/scenarios/data/*.yaml`; `registry.py` loads YAML over minimal embedded fallback. |
| **I4** | `backend/pyproject.toml`: `requires-python = ">=3.11,<3.13"`; dependency `pyyaml`. |
| **I3** | `backend/.gitignore` for `venv/`, `.venv/`, sqlite, caches. |
| **Tests** | Prompt shape, state parse + orchestrator path, simulation failure guard, YAML registry, context clipping; state engine mocks `llm_complete` with `<state>` JSON. |

---

## Follow-on (same iteration, from real runs)

| Topic | Change |
|-------|--------|
| **LM Studio 400 / context** | `lmstudio_client.py`: non-200 responses raise `RuntimeError` with parsed LM Studio `error.message` (or body) so transcripts are debuggable. |
| **Reasoning models + n_ctx** | `llm/context_clip.py`: strip `<state>` from peer snippets; trim `Thinking Process` → `**Draft:**` when present; tail cap per snippet (`peer_context_max_chars`, default 1200). Config + `config_snapshot`. |
| **Prompt discipline** | User prompt: forbid visible chain-of-thought; only in-character text + `<state>`. |
| **Cross-round evolution** | `get_recent_interactions` returns `round_number`, `turn_index`, `agent_id`; peer lines labeled `[Round R, turn T]`; current agent **excluded** from “what others said”; round ≥ 2 evolution instruction; wider `interaction_last_k` on first turn of later rounds; `_policy_event_for_round` default text references prior dialogue. |
| **UX** | Frontend Run tab: note that round counter advances after full rounds; “Turns in transcript” while running. |

---

## Key files (for reviewers)

| Area | Paths |
|------|--------|
| Orchestrator | `backend/src/mirofish_backend/simulation/orchestrator.py` |
| Prompts | `backend/src/mirofish_backend/llm/prompt_templates.py` |
| State parse | `backend/src/mirofish_backend/llm/state_parse.py` |
| Context clip | `backend/src/mirofish_backend/llm/context_clip.py` |
| LM Studio | `backend/src/mirofish_backend/llm/lmstudio_client.py` |
| Router / Claude | `backend/src/mirofish_backend/llm/router.py`, `llm/claude_client.py` |
| API | `backend/src/mirofish_backend/api/simulations.py` |
| Config | `backend/src/mirofish_backend/config.py` |
| DB / memory queries | `backend/src/mirofish_backend/db/repo.py` (`get_recent_interactions`, …) |
| Scenarios | `backend/src/mirofish_backend/scenarios/registry.py`, `scenarios/data/psle_reform_mvp.yaml` |
| Frontend | `frontend/src/App.tsx`, `frontend/src/lib/api.ts` |
| Tests | `backend/tests/test_*.py` (see Gate Evidence) |

---

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q    # 18 passed (as of closeout)
cd ../frontend && npm run build                    # vite build OK
```

Manual: LM Studio on `127.0.0.1:1234`, model id must match `GET /v1/models`; optional `PEER_CONTEXT_MAX_CHARS`, `LMSTUDIO_MODEL`, `LLM_PROVIDER`, `ANTHROPIC_API_KEY`.

---

## For Opus / architect review

1. Use skill **mirofish-code-reviewer** (or equivalent deep pass).  
2. Read `docs/SESSION_STATE.md` and this file.  
3. Skim `docs/reviews/REVIEW_REQUEST_iteration-4.md` for scope checklist.  
4. Write findings to **`docs/reviews/review-iteration-4.md`** (create on review).

Suggested review lenses: validity of `<state>` vs second-pass extraction; context clipping vs thesis traceability; multi-provider security; YAML/packaging; alignment with architecture spec (router modes, RAG, validity scaffolding).

---

## Next iteration (indicative)

- RAG scaffold + second scenario (e.g. FSBB).  
- Validity structures (face / construct / predictive).  
- Richer personas in YAML; optional second-pass state validation.  
- Router modes beyond binary lmstudio/anthropic.
