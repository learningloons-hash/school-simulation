# Domain packs vs generic engine

MiroFish is a **domain-agnostic** simulation engine: policy rounds, agent state, LLM turns, exports, and interaction policies are not tied to schools or any single sector.

A **domain pack** is everything that makes a run *about* a specific context:

- **Scenario YAML** under `backend/src/mirofish_backend/scenarios/data/` — `policy_events`, `personas` (roles, `role_level`, beliefs, optional `initial_state`, attribute sections), `groups`, RAG paths.
- **Optional interaction overlay** — e.g. `interaction_overlay: school_trinidad` in the scenario document. Overlays are **plug-ins**: they adjust channel defaults and documentation expectations for a class of settings (here, Trinidad-style school sociology) without hardcoding that domain into orchestrator core logic. Future packs could add `corporate_hierarchy`, `public_forum`, etc., using the same hook pattern.
- **Bundled corpora** — text files referenced by `rag_corpus_paths` for that scenario.

The **engine** stays stable: `run_simulation_task`, SQLite persistence, `sample_k_per_round`, parallel LLM rounds, export bundles, and `GET /capabilities` describe mechanics, not subject matter.

**School as reference pack:** PSLE and FSBB scenarios in-repo are **example** domain packs (Singapore education policy language). They demonstrate roster CSV, groups, population pools, and `school_trinidad` — not a requirement for other domains.

For thesis or grant text: *MiroFish separates simulation mechanics from scenario content; a domain is defined by data and optional overlays, not by forked engine code.*
