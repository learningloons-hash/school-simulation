# M-ROSTER builder closeout

## 1. PR / SHAs

- **PR:** see GitHub PR for `m-roster-join-leave`
- **Branch tip:** branch HEAD (see PR after push)
- **Base branched from:** `9739f0962204d78273319af3436265b7ad634818`

## 2. Pytest baseline

| | passed | failed | skipped |
|---|--------|--------|---------|
| Baseline on `9739f09` | 564 | 15 | 2 |
| After M-ROSTER (branch HEAD) | 564 | 15 | 2 |

Same 15 failing nodeids:

- `tests/test_interaction_sample_k.py::test_sample_k_fewer_llm_turns_than_full_robin`
- `tests/test_iteration12.py::test_effective_provider_and_model_persisted_for_hybrid`
- `tests/test_iteration12.py::test_stress_many_fake_llm_turns_completes_quickly`
- `tests/test_iteration23.py::test_mixed_tiers_llm_only_for_one_and_two`
- `tests/test_iteration25.py::test_network_queued_run_audit_sampling_report_and_node_count`
- `tests/test_iteration26.py::test_posture_maxvar_queued_run_audit_and_sampling_report`
- `tests/test_iteration29.py::test_get_simulation_anthropic_provider_positive_estimated_cost`
- `tests/test_iteration29.py::test_economics_pure_functions`
- `tests/test_senna_arc8_economics.py::test_resolve_billing_provider_key_by_profile`
- `tests/test_sstrf_validity_v2_elicitation.py::test_dry_run_elicitation_for_trial_a`
- `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_updates_validity_manifest`
- `tests/test_sstrf_validity_v2_elicitation.py::test_batch_dry_run_leaves_production_manifest_untouched`
- `tests/test_sstrf_validity_v2_scoring.py::test_trial_record_from_validity_label_loads_elicitation`
- `tests/test_sstrf_validity_v2_scoring.py::test_validity_scoring_dry_run_one_trial`
- `tests/test_state_engine.py::test_state_timeline_and_demographics_are_persisted`

## 3. Files (purpose)

| File | Purpose |
|------|---------|
| `simulation/roster_windows.py` | Pure window resolve, gating, handover/absence, export rows |
| `roster/tenure_draw.py` | Seeded 7/5/4-style tenure window draw |
| `scripts/draw_tenure_windows.py` | CLI CSV output for roster import |
| `scenarios/registry.py` | Persona window fields + `RosterWindowsConfig` |
| `scenarios/validate.py` | §5 validation for YAML/CSV windows |
| `scenarios/serialize.py` | Round-trip new keys when set |
| `roster/csv_roster.py` | Optional window columns + merge |
| `llm/prompt_templates.py` | Handover/absence blocks after policy line |
| `simulation/memory_context.py` | `pre_join` exclusion reason |
| `simulation/transcript_writer.py` | Active-rounds column + membership line |
| `simulation/preflight.py` | `active_window_adjusted` snapshot block |
| `simulation/orchestrator.py` | Active sampling, metrics, audit |
| `api/simulations.py` | Preflight roster merge fix, queue/preflight 422 |
| `db/repo.py` | Export bundle `active_agents_per_round` |
| `export_bundle.py` | Zip member `active_agents_per_round.csv` |
| `api/capabilities.py` | Documents roster window columns |
| `docs/examples/m_roster_windows_demo.yaml` | Synthetic demo (not auto-registered) |
| `docs/research/M_ROSTER_SPEC.md` | Allowlisted spec copy |
| `docs/handoffs/HANDOFF_SENNA_M_ROSTER.md` | Milestone pointer |
| `.gitignore` | Allowlist `M_ROSTER_SPEC.md` |
| `CLAUDE.md` / `docs/SESSION_STATE.md` | Milestone status |

## 4. Prompt strings (from code)

Handover block (when set):

```text
Handover note (given to you on joining; only you can see this):
<rendered note>

```

Absence line:

```text
Not present this round: Name A (reason), Name B.
```

(transcript uses separate membership line; not the same as the user-prompt absence line)

## 5. Byte-identical gating

`windowing_active(windows, total_rounds)` in `roster_windows.py` returns false when every actor is active in `1..total_rounds`. Orchestrator sets `roster_windowing` once after `resolve_activity_windows` and skips all window-only branches (transcript columns, prompt kwargs, active subset sampling, adjusted metrics, config `roster_windows`, export member) when false.

## 6. Notes / ambiguities

- Implemented Mark’s locked Q1–Q5 (see spec tail); absence scope default `all_inactive`.
- Preflight `active_window_adjusted` uses the same token averages as headline estimate; headline stays uncredited per §13.
- Peer recency window sizing at orchestrator l.1063–1080 unchanged (spec C3).
- **Preflight roster merge** (`build_preflight_response` merges roster CSV before personas/tiers): changes preflight counts for requests that supply `roster_csv` where slots differ from YAML-only personas — intended fix for the pre-reg window visibility gap.
- **`ROSTER_CSV_TEMPLATE`:** adds four optional window columns (blank cells = inherit YAML / no window). User-visible additive change to the downloadable template.
- **Transcript membership line:** when everyone is active in a round, line is `*Active: ….*` only (no `Not present` clause). Spec §7.2 does not define the empty-inactive case.
- Self-check: full `uv run pytest`; `import senna_backend.simulation.roster_windows, senna_backend.roster.tenure_draw`; `npm run build` (frontend) — all as reported in §2 and builder notes above.

## 6b. Architect correction pass (PR #19 review)

1. Reverted Likert emission from `scenario_config_to_document` — M-ROSTER serialize changes only window/roster_windows keys.
2. Reverted explicit `likert_anchor_labels` copy in `merge_persona_for_slot` (out of scope for byte-identical roster merge).
3. Window-resolve soft warnings attached to preflight/queue only when `windowing_active()` is true; `ValueError` still → 422.
4. Transcript membership: omit `Not present` when the inactive list is empty.
5.–6. Documented template + preflight roster merge (see bullets in §6).

### Follow-ups (not fixed in M-ROSTER)

- `merge_persona_for_slot` on `main` omits `likert_anchor_labels` in the `PersonaTemplate(...)` call; dataclass defaults apply. Explicit pass-through might matter if roster merge should preserve scenario anchors when personas are rebuilt — separate from windows.

## 7. Don’ts confirmation

No test edits, no `LICENSE`/data/secrets touched, no force-push or amend of pushed commits (normal `git push` only).