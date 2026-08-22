# senna-iter-50 — Relevance-Conditioned Retrieval (closeout)

## Delivered

- **Weighted retrieval** (`memory_retrieval.py`): `retrieval_score = w_r·recency + w_i·importance + w_rel·relevance`, each in [0,1]. Candidate pool widened, ranked, then top-k matches legacy k.
- **In-process memory index** (`rag/memory_index.py`): turn embeddings at write time via existing LM Studio `/v1/embeddings` path; situation embedding cached per sim + hash.
- **Flag-off path**: legacy SQL order + limits unchanged; no embedding calls.
- **Config/API**: `weighted_retrieval_enabled` (default off), three weights; wired through Settings, POST `/simulations/run`, preflight warning, `config_snapshot`, orchestrator.
- **Instrumentation**: `agent_context_inclusion.retrieval_signals` JSON on included rows; exported in bundle + CSV.
- **EXPORT_VERSION → 13**
- **iter-49 review fixes**: tier-3 excluded from batch importance LLM; importance scorer tokens folded into `simulation_runs` token totals at run end.

## Candidate caps

| Stream | Cap |
|--------|-----|
| Self | `min(24, max(3×k, k+8))` — `MEMORY_RETRIEVAL_SELF_CAP = 24` |
| Peer | `min(24, max(3×interaction_last_k, interaction_last_k + round_agents))` |

## Tests

- `tests/test_senna_iter50_weighted_retrieval.py` — unit rank tests (one weight at a time), flag-off embed regression, retrieval-signals on included rows, B2 bounded fetch scale check.

## Notes

- No ChromaDB; spec ChromaDB text is aspirational — existing RAG embedding stack only.
- Ablation harness integration deferred to iter-52.
- **Architect follow-up (post-review):** prompt turn-key regression tests, integration weight-order test, preflight/run rejection without embed model, `weighted_retrieval_embed_api_calls` in `config_snapshot`.
