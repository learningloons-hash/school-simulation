# Iteration 9 closeout

**Project:** `mirofish-mvp`  
**Gate date:** 2026-04-02  
**Theme:** Rosters, groups/factions, bulk CSV import, higher `agent_limit` with soft warnings (Joan brief Iteration 9).

## Shipped

| Item | Detail |
|------|--------|
| Scenario model | Optional YAML **`groups`** (`group_id`, `name`, `description`); optional **`groups: [ids…]`** on personas; `GroupDef`, `ScenarioConfig.groups`, `PersonaTemplate.groups`. |
| Roster CSV | `mirofish_backend.roster.csv_roster`: 1-based **`slot`**, optional overrides + **`groups`** (pipe-separated); merge onto base persona; **`roster_unknown_group_ids`** in `config_snapshot` when ids are not declared on the scenario. |
| API | `POST /simulations/run` optional **`roster_csv`** (422 on parse errors); **`agent_limit` 1–50**; **`GET /simulations/roster-csv-template`** plain-text template. |
| DB | Migrated **`group_ids`** (JSON array text) on **`agent_turns`** and **`agent_state_snapshots`**; transcript, export bundle, state timeline expose **`group_ids`**. |
| Orchestrator | Optional **`personas_for_run`**; prompts include group labels when non-empty; persists **`group_ids`** per turn/snapshot. |
| Config snapshot | **`scenario_groups`**, **`scale_warning`** (`agent_limit > 20`), **`roster_csv_applied`**, **`roster_csv_row_count`**, **`roster_unknown_group_ids`**. |
| Frontend | Agent limit max **50**, optional roster **textarea**, link to CSV template, in-form warning when **> 20** agents. |
| FSBB YAML | Example **`groups`** + persona membership for tests and demos. |
| Docs | `SCALE_LIMITS_AND_COST.md` updated for cap **50** and soft warning. |

## Not in scope (defer to Iteration 10)

- Interaction model v2 (who hears whom by group); group-based routing or neighborhoods.

## Gate evidence

```bash
cd backend && PYTHONPATH=src pytest tests/ -q   # 31 passed
cd ../frontend && npm run build
```
