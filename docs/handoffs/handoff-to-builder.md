# Handoff to Builder

**Ritual:** Architect seeds this file before each Builder session. Builder implements **only** what is under **Active task** below. When finished (tests pass, commit), Builder fills [`handoff-to-architect.md`](./handoff-to-architect.md) and stops.

---

## Active task — `senna-iter-54` closeout

| Field | Value |
|-------|--------|
| **Arc** | 12 — Freeze and Study Readiness |
| **Spec** | [`HANDOFF_SENNA_ITER54.md`](./HANDOFF_SENNA_ITER54.md) §4 + §5 |
| **Branch** | `main` |
| **Base** | `37d8419` (Part C) |
| **Commit** | One commit for closeout only |

### Goal

Write the combined iter-54 closeout doc. Documentation only — no code, no new runs.

### Deliverable

**New file:** `docs/iterations/senna-iter-54-closeout.md`

Follow the tone/structure of [`senna-iter-53-closeout.md`](../iterations/senna-iter-53-closeout.md) — evidence tables, plain findings, explicit gates.

### Required sections

1. **Header** — spec ref, arc, date, status: iter-54 scope **CLOSED**; mechanism-defaults verdict **pending GM-F** (iter-54 → iter-55 gate).

2. **Part A summary** — Option 1 fixture reunification (`93368c9`):
   - Study repo @ `47013659309c5ac047dbc53dcea3fd1441d74042`
   - `ciepss_school_b` seeded; smoke sim `c28fe9b01eb147cf924844287ea07d8b` → `completed`
   - `docs/diagnostics/ciepss_school_b_provenance.json` — **flag for iter-58 pre-reg citation**
   - `docs/SETUP_STUDY_FIXTURES.md`
   - Pre-flight §1.1: content clean, `rag_enabled` absent, 8 personas
   - 5 CI tests pass

3. **Part B summary** — confound test (`e448c03`):
   - Six runs, QA clean (0 LLM errors, 0 context-length failures)
   - Sim ID prefixes: baseline `2e962591`/`553b7d29`/`0b75a919`; full-stack `059b3122`/`aa1241a5`/`9a5a9303`
   - Cost **$0.96** total (~227 s wall-clock) vs ~$10 estimate
   - **Interpretation call:** `memory_retrieval` at 2.00 both arms on Anthropic → **model confound**, not mechanism effect
   - Env pitfall: shell `ANTHROPIC_API_KEY` shadowed `backend/.env` — document `unset` fix

4. **Part C pointer** — do not duplicate full report; summarise and link [`ARC12_INDIVIDUATION_FINDING.md`](../diagnostics/ARC12_INDIVIDUATION_FINDING.md) (`37d8419`):
   - Arc 11 vs Part B dispersion contrast
   - Study-validity framing (P1/P3/P4)
   - Ops does not conclude on defaults

5. **Evidence synthesis for GM-F** (§4 combined DoD) — quality, cost, dispersion together:
   - Mechanism confound result (Part B)
   - Individuation / study-validity evidence (Part C)
   - **Do not issue a mechanism-defaults recommendation** — present evidence, state what GM-F must rule on, stop
   - Reference iter-53 shipping config (all flags OFF) as current frozen state pending ruling

6. **iter-55 handoff notes** — carry forward from spec §5:
   - CIEPSS documented network has no loader path today (synthetic chain only)
   - Dispersion must be verified on study profile (8 actors, 15–20 rounds, `ciepss_school_b`)

7. **Commits table**

   | Part | Commit |
   |------|--------|
   | A | `93368c9` |
   | B | `e448c03` |
   | C | `37d8419` |

8. **Open question for GM-F** — mechanism defaults on/off before iter-55; cite iter-54 → iter-55 gate from ARC12 §8.

### Out of scope

- `CLAUDE.md` Arc Status update (GM-F PASS only)
- `senna-iter-55` implementation
- Code changes
- Re-running ablation or confound test

### Verification

No pytest. Closeout must be legible to someone who has not read Parts A/B/C handoffs.

### Commit

One commit on `main`: `senna-iter-54` closeout.

---

## Completed (do not redo)

- `senna-iter-54` Part A (`93368c9`)
- `senna-iter-54` Part B (`e448c03`)
- `senna-iter-54` Part C (`37d8419`)
- `senna-iter-54` closeout — `docs/iterations/senna-iter-54-closeout.md` (pending commit)
