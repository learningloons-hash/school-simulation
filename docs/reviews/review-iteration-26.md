# Review: Iteration 26

Date: 2026-04-07  
Reviewer: Claude Opus (Architect)  
Verdict: PASS_WITH_ISSUES

## Iteration Delta

- **`implementation_posture`** flows through persona YAML, roster CSV, population CSV, and `PersonaTemplate`; merge rules keep roster/population overlays as non-empty wins over base.
- **`posture_maxvar`** assigns Tier 1 to the first slot (in sorted index order) for each distinct non-empty posture; remainder uses the same role_level split as `role_stratified`; full fallback to role-stratified logic when no posture tags exist, with explicit rationale prefixing.
- **`GET /simulations/{id}/sampling-report`** exposes a researcher-oriented reshape of `config_snapshot.sampling_audit` (tier summary, `by_role`, `by_posture`, `centrality: null` reserved for Iteration 25); HTTP semantics 404 / 409 / 400 are correct.

## Critical Issues

_None._ No incorrect tier assignment or audit shape was found on code review; backend suite passes.

## Important Issues

### I1: `SESSION_STATE.md` out of sync with Iteration 26 gate

- Severity: IMPORTANT  
- Files: `docs/SESSION_STATE.md`  
- Problem: **Current Status** already says Iteration 26 completed and Iteration 25 next, but **Gate Evidence (Latest)** still lists **152** tests and Iteration **24**; **Next Iteration Focus** still instructs building Iteration **26** before 25; **Completed Work** has no **### Iteration 26** subsection.  
- Fix: Update Gate Evidence to **163 passed**, add a concise **Iteration 26** bullet block (mirror `iteration-26-closeout.md`), extend `config_snapshot` bullet to mention extended `per_agent` fields (`role`, `implementation_posture`), and replace **Next Iteration Focus** with **Iteration 25** (network adjacency + visibility) plus link to `HANDOFF_TO_BUILDER.md` Iteration 25 starter.

### I2: Sampling report is API-only

- Severity: IMPORTANT (demo / discoverability)  
- Files: `frontend/` (no consumer found)  
- Problem: Researchers must discover `GET /simulations/{id}/sampling-report` from docs or capabilities; the React app does not surface a link or tab after a run completes.  
- Fix: Optional stretch — add a **Run metadata** (or **Sampling**) panel with “Open sampling report” that fetches the endpoint for the loaded run id, or at minimum document the path in the Run tab help text.

### I3: No integration test for `posture_maxvar` through `queue_simulation_run`

- Severity: IMPORTANT (confidence, not correctness)  
- Files: `backend/tests/test_iteration26.py`  
- Problem: Tier logic is covered via `compute_fidelity_tiers`; API coverage is sampling-report + capabilities. There is no test that queues a run with `sampling_strategy=posture_maxvar` and asserts persisted `config_snapshot.sampling_audit.per_agent[*].implementation_posture` matches expectations.  
- Fix: Add one FastAPI test (fake LLM / minimal rounds) that completes a run and GETs sampling-report, asserting posture keys and tier counts.

## Minor Issues

### M1: Roster cannot clear a YAML posture with an empty cell

- Severity: MINOR  
- Files: `backend/src/mirofish_backend/roster/csv_roster.py` (`merge_persona_for_slot`)  
- Problem: Empty or whitespace `implementation_posture` in CSV leaves base persona posture unchanged — reasonable default, but worth one line in roster template comment so authors are not surprised.

## Architecture Alignment

| Component | Status | Gap |
|-----------|--------|-----|
| Orchestrator | ✅ | N/A for this slice (tier metadata + existing tier execution). |
| LLM Router | ✅ | Unchanged. |
| Memory System | ✅ | Unchanged. |
| Prompt Architecture | ✅ | Posture is sampling metadata only; not injected into prompts (acceptable for Iter 26). |
| RAG Pipeline | ✅ | Unchanged. |
| Persona System | ✅ | `implementation_posture` optional, validated as string in scenario validator. |
| Validity Module | ✅ | Unchanged. |
| Scenarios | ✅ | Example postures on bundled YAMLs. |
| Data Model | ✅ | Audit extended in snapshot JSON only. |
| Frontend | ⚠️ | No UI for sampling report. |
| Config/Reproducibility | ✅ | Audit persisted at queue time; deterministic tier assignment given roster + strategy. |
| Sampling Audit (Iter 22+) | ✅ | `role` + `implementation_posture` on `per_agent`; report aggregates by both. |

## Next Iteration Spec

### Priority 1 (must complete) — Iteration 25

1. Implement **network adjacency** and **network-bounded visibility** per `HANDOFF_TO_BUILDER.md` Iteration 25 starter and **ADR-002** (interaction policy).
2. When network metrics exist, populate **`centrality`** (and any related fields) in `build_sampling_report_json` — closeout already reserves `null`.

### Priority 2 (stretch goals)

1. Frontend surfacing for sampling report (see I2).  
2. E2E test for `posture_maxvar` run → persisted audit (see I3).  
3. Repair **SESSION_STATE** consistency (see I1).

## Test Requirements

1. `cd backend && uv run pytest` — **163 passed**, **1 skipped** (re-verified 2026-04-07).  
2. After any Iteration 25 change: extend or add tests for network visibility and sampling-report `centrality` when applicable.  
3. Optional: add integration test described in I3 before closing Iteration 26 follow-up (if treated as hardening).

## Note on prior review file

`docs/reviews/review-iteration-25.md` does not exist; no regression check against `review-iteration-N-1` was possible.
