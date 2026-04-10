# Architect sign-off checklist — Iteration 10–11

Use this before approving handback from Joan. The goal is to prevent semantic drift before performance hardening.

## Iteration 10 (interaction model v2 + thin agent context)

- [ ] **ADR exists and is linked** in `docs/iterations/iteration-10-closeout.md` and `docs/SESSION_STATE.md`.
- [ ] **Population semantics v1 is explicit**:
  - who can speak each round,
  - how speakers are selected,
  - how non-speaking agents are updated,
  - what counts as an interaction event.
- [ ] **Runtime interface is locked** (`AgentContext`/equivalent): versioned contract, backward-compatible projection from existing fields.
- [ ] **No hidden policy logic** in UI or ad-hoc scripts; interaction rules live in backend domain code.
- [ ] **Reproducibility**: sampling and interaction decisions are seed-driven and captured in `config_snapshot` (or referenced sidecar export).
- [ ] **Exports are coherent**: JSON/CSV reflect whichever interaction mode is used; labels are analysis-friendly.
- [ ] **Safety checks**: clear behavior when required external data is absent (fail fast or degrade predictably).

## Iteration 11 (single population-table contract + import + sampler)

- [ ] **One contract only** for population import (`population_schema_version` included).
- [ ] **Validation policy documented**:
  - required vs optional fields,
  - defaults/imputation,
  - error reporting for bad rows.
- [ ] **Weighted/stratified sampling ties to same context keys** used in Iteration 10 interface.
- [ ] **No second competing format** introduced; extensions are additive and versioned.
- [ ] **Traceability fields** included where relevant (e.g., data source, synthetic/empirical flags if used).
- [ ] **Thesis alignment note** explains representativeness limits and site-specific overlays (IAD core vs Trinidad school overlay).

## Cross-iteration quality gates (10 + 11)

- [ ] Backend tests pass (`PYTHONPATH=src pytest tests/`) and include new model-contract tests.
- [ ] Frontend build passes (`npm run build`) if UI touched.
- [ ] `docs/iterations/iteration-10-closeout.md` / `iteration-11-closeout.md` present with commands + outcomes.
- [ ] `docs/handoffs/HANDOFF_TO_ARCHITECT.md` filled with:
  - deviations from plan,
  - open questions,
  - explicit risks deferred to Iteration 12.

## Decision record

- [ ] **Approve**
- [ ] **Needs revision**

If revision is needed, list blocking issues and whether they are:
1) semantic (model invalid), 2) contract (schema/API drift), 3) operational (perf/UX), 4) documentation.
