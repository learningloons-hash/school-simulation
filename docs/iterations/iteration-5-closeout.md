# Iteration 5 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Status:** Implementation complete; ready for architect review.

## Plan (from SESSION_STATE)

| Deliverable | Notes |
|-------------|--------|
| Second YAML scenario | `fsbb_comparator` — FSBB-themed policy rounds, three personas, corpus paths. |
| RAG scaffold | Chunk → LM Studio `/v1/embeddings` → cosine top‑k → inject into **user** prompt. In-process index cache; not Chroma/production vector DB. |
| Provenance | `config_snapshot` + exports carry `rag_effective`, `embedding_model_id`, server/scenario flags, corpus paths, RAG hyperparameters. |

## What shipped

### Scenarios

- `backend/src/mirofish_backend/scenarios/data/fsbb_comparator.yaml` — `rag_enabled: true`, `rag_corpus_paths` list.
- `backend/src/mirofish_backend/scenarios/data/corpus/fsbb_comparator/brief.txt` — stub reference corpus for retrieval.
- `registry.py` — `ScenarioConfig.rag_enabled`, `rag_corpus_paths`; YAML loader backward compatible.

### RAG package

| Module | Role |
|--------|------|
| `rag/chunk.py` | Overlapping character windows. |
| `rag/embeddings.py` | `embed_texts_openai_compatible` → `POST {base}/embeddings`. |
| `rag/similarity.py` | Cosine similarity (stdlib only). |
| `rag/corpus.py` | Load texts from `scenarios/data/{rel_path}`; optional fallback `rag/data/*.txt`. |
| `rag/retrieve.py` | Build/embed chunk index (cached), `retrieve_top_k`, `snippets_for_prompt`, `clear_rag_index_cache` for tests. |

### Orchestrator & API

- `simulation/orchestrator.py` — If `rag_effective`, `retrieve_top_k` per turn; on failure, warning + no snippets.
- `llm/prompt_templates.py` — Optional `context_snippets` → “Reference excerpts” block after policy event line.
- `api/simulations.py` — Resolve `rag_effective` from `settings.rag_enabled OR scenario.rag_enabled`, with `POST` body `rag_enabled` override; extend `config_snapshot`; pass RAG params into `run_simulation_task` / guarded wrapper.
- `config.py` — `rag_enabled`, `embedding_model`, `rag_top_k`, `rag_chunk_size`, `rag_chunk_overlap`, `rag_max_inject_chars`.

### Frontend

- `frontend/src/App.tsx` — Scenario option `fsbb_comparator`.
- `frontend/src/lib/api.ts` — Optional `rag_enabled` on start request.

### Tests

- `backend/tests/test_rag.py` — Chunking, cosine, retrieve with mocked embed batch, prompt contains RAG block.
- `backend/tests/test_scenarios_yaml.py` — FSBB RAG flags + corpus path.
- `test_state_engine.py` / `test_simulation_failure.py` — Updated orchestrator/guarded kwargs.

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q    # 23 passed
cd ../frontend && npm run build                  # vite build OK
```

## Manual smoke

1. LM Studio: loaded chat model + embedding-capable model if chat model does not serve embeddings; set **`EMBEDDING_MODEL`** if different from **`LMSTUDIO_MODEL`**.
2. `POST /simulations/run` with `"scenario_id": "fsbb_comparator"` — expect `config_snapshot.rag_effective` true and transcript `raw_prompt` containing “Reference excerpts” when embeddings succeed.

## Not in scope (Iteration 6+)

- Dedicated HTTP “retrieval API” endpoint (retrieval is internal to orchestrator for this scaffold).
- Chroma / persistent vector store / cross-process cache invalidation.
- Validity notes, router hybrid mode, richer personas (roadmap items).

## For architect

- Confirm RAG semantics: **query** = policy event + intent tag; **effective** = `(server.rag_enabled OR scenario.rag_enabled)` with optional request override.
- Decide whether PSLE (or others) should ship a default corpus under `rag/data/` for experiments without FSBB.
