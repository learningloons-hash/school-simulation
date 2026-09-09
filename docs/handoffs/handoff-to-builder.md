# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — *(none — awaiting Architect seed for Part C or next workstream)*

---

## Queued — `scenario-context-field` Part C (run)

Execute utility/differentiation runs with authored fixtures. Not seeded here.

---

## Completed (do not redo)

- Arc 12 (`senna-iter-54`–`58`, pre-reg signed)
- `sstrf-validity-v2` Parts A–D harness (`ddcd417`…`f02adef`); live sims + elicitation complete; scoring escalated to human-only
- **`scenario-context-field` Part A** (`b122a0d`) — `ScenarioConfig.context` + prompt injection + sentinel test
- **`scenario-context-field` Part B** — `sq_reading_culture` / `sq_reading_culture_adverse` fixtures + provenance + round-trip serialize

### Part B spec (closed)

| Deliverable | Status |
|-------------|--------|
| `sq_reading_culture.yaml` + `sq_reading_culture_adverse.yaml` in `scenarios/data/` | ✅ |
| Identical `policy_events` + persona roster; context only differs | ✅ |
| Provenance JSON committed | ✅ (`dirty: true` — study repo untracked; context authored in-product) |
| `scenario_config_to_document()` round-trips `context` | ✅ |
| Tests in `test_sq_reading_culture_fixtures.py` | ✅ |

**Gap flagged:** Study-repo adverse YAML had round-5 policy shock — removed for context-only differentiation. Context strings are GM-F ecological contrasts, not CIEPSS site claims. MT department role still absent (known gap from source).
