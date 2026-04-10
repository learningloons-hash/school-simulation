# MiroFish MVP — architecture pointers

High-level orientation for reviewers. Detailed iteration logs live under `docs/iterations/`.

## Backend

- **FastAPI** app in `backend/src/mirofish_backend/main.py`; simulation routes in `api/simulations.py`.
- **SQLite** via `aiosqlite`; schema and migrations in `db/schema.py`; persistence in `db/repo.py`.
- **Simulation loop** in `simulation/orchestrator.py`: deterministic interaction plan, prompts, LLM call, state parse, round/global snapshots.
- **LLM routing** (`llm/router.py`): `lmstudio` (OpenAI-compatible local), `anthropic`, **`hybrid`** (frontier on **first turn of each round**, local for other turns — see `resolve_effective_provider`).
- **Scenarios** loaded from `scenarios/data/*.yaml` with embedded fallback in `scenarios/registry.py`. Personas support optional **`psychological_profile`** and **`implementation_profile`** maps (Iteration 7).
- **RAG** scaffold under `rag/` (chunk → LM Studio embeddings → top-k → user prompt).

## Frontend

- Vite + React `frontend/src/App.tsx`; API wrapper `frontend/src/lib/api.ts`.

## Exports

- JSON `export_version` **4** adds agent snapshot **attribute_sections** (Iteration 13); **3** added per-turn `effective_provider` / `effective_model`; **2** introduced `validity_notes`; ZIP adds `validity_notes.csv`.

## Observability & scale (Iteration 8+)

- **Live UI:** `frontend` **Live** tab — charts/tables from existing `GET /simulations/{id}` polling (~750ms while running).
- **Docs:** `docs/plans/iteration-8-live-dashboard-design.md`, `docs/plans/SCALE_LIMITS_AND_COST.md`.

## Session roadmap

See `docs/SESSION_STATE.md` for completed iterations and **Next Iteration Focus** after the latest gate.
