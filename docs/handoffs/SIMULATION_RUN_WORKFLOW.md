# Senna — Standard Simulation Run Workflow

**Author:** GM-F · **Date:** 2026-09-01
**Purpose:** The repeatable process for running a simulation end to end, from "we want to try programme X" to "here is what it showed and whether we trust it."
**Scope:** Exploratory and utility runs. Confirmatory study runs additionally require a signed pre-registration — see `PREREG_SSTRF_RQ1_V2.md`.

---

## 1. Roles

| Role | Who | Does | Does **not** |
|---|---|---|---|
| **GM** | Claude Opus 5 | Defines the question. Reviews mechanics and analysis together. Rules on whether the run is usable and what it shows. | Run simulations. Code. |
| **Ops** | Claude Sonnet 5 | Writes the run instruction, receives artefacts, reports **mechanics only**. | Interpret content. Execute — Ops has no terminal on the host. |
| **Runner** | Cursor | **Executes.** Builds the fixture, preflights, smokes, runs headless, captures artefacts, returns raw numbers. | Interpret. Change engine code during a run. |
| **Analyst** | Fresh session, briefed blind | Thematic coding, trajectory reading, cross-run frequency. | Know what the run was expected to show. |
| **Cursor Architect / Builder** | Cursor | Engine code changes only, outside a run. | Appear in a typical run at all. |

> **Correction, 2026-09-01:** an earlier version had Ops executing runs directly. Ops is a chat
> session with no shell on the Mac mini. Cursor executes; Ops directs and reports. Where steps
> below say "Ops," read: *Ops instructs, Cursor performs, Ops verifies and reports.*
| **Mark** | — | Chooses the programme. Decides what happens with the result. | — |

### Why an Analyst and not a Runner

Whoever executes a run has an interest in it having gone well. That is the same reason the
scoring judge is a different vendor from the generator. Separating execution from
interpretation costs one session and buys independence.

A dedicated *runner* agent buys nothing — Ops already does this, and a new agent would start
cold and re-derive context that Ops already holds.

**Analyst blinding, practically:** the Analyst receives the scenario description, the actor
roster, and the outputs. It does **not** receive the hypothesis, GM's expectations, prior run
results, or the reason the programme was chosen.

---

## 2. The run, step by step

### Step 1 — Define · *Mark + GM*

Settle before anything is configured:

- What programme is being simulated, and what actually happens in it.
- Which roster: reuse an existing one, or build new.
- How many seeds. **Minimum 3** — a single run tells you nothing about what is stable.
- How many rounds.
- What question this run answers.

**Output:** a short written brief. Three paragraphs is enough.

### Step 2 — Configure · *Ops*

- Scenario YAML: `scenario_id`, `policy_events` by round, personas with roles and `role_level`.
- Network CSV if links are being used.
- **Every persona attribute traceable to a stated source**, or left unset. Empty beats invented.

**Output:** committed fixture, path recorded.

### Step 3 — Preflight · *Ops* — free

```bash
POST /simulations/preflight
```

Record `estimated_cost_usd` and all warnings.

🚦 **Gate:** if the estimate is more than double expectation, stop and report before running.

### Step 4 — Smoke · *Ops* — pennies

One round, three agents, same config otherwise.

Verify: terminal status · all agents produced turns · `effective_profile_id` correct on every
LLM turn · `state_update_source` is `model_parsed` not fallback · economics populated · no
secrets in `config_snapshot` · if `network_bounded`, no silent fallback to broadcast.

🚦 **Gate:** any failure, fix and re-smoke. Never scale up on a broken fixture.

### Step 5 — Run · *Ops* — headless

Seeds fixed in advance and recorded. Drive from a script over SSH, not a browser.

> `POST /experiments` runs its child-run loop inside the request handler and will time out on a
> sweep. Use single runs from a script.

### Step 6 — Capture · *Ops*

Per run: `simulation_id`, seed, wall-clock, input and output tokens, `estimated_cost_usd`,
warnings, turn count, state-extraction provenance counts, `group_addressed_proportion`.

Pull `export.zip` for each. Store under `docs/research/runs/<scenario>/<date>/`.

### Step 7 — Mechanics report · *Ops*

**Mechanics only. No interpretation of content.**

Completion rates · cost · wall-clock · error counts · provenance counts · context growth ·
anything that behaved unexpectedly.

If Ops has read the transcripts and formed a view, that view does not go in this report.

🚦 **Gate:** GM reviews. A run with degraded provenance or silent fallbacks is not analysed —
it is re-run.

### Step 8 — Package for analysis · *Ops*

Bundle for the Analyst: transcripts (all runs, all rounds) · elicitation responses if
administered · attitude state per agent per round · scenario description and roster.

**Strip:** the brief from Step 1 · GM's expectations · prior run results · any framing of what
the run is meant to show.

Runs may keep their seed labels — the Analyst needs to distinguish runs to compute frequency.

**Redaction rule (GM-F, 2026-09-11 — filed after a persona-rich run shipped `[redacted]` in
measurement cells).** Redaction must not touch measurements. Redact only identifying
metadata — seed, temperature, `scenario_id`, run name, condition vocabulary. **Never** redact
state values (`support_level`, `resistance_level`, `workload_stress`, etc.), round numbers, or
agent ids — those are what the Analyst needs to compute the finding. Add an assertion to the
packaging script: if any numeric state cell is redacted, fail loudly rather than ship a
package with `[redacted]` in a measurement column.

**Persona experiments cannot be prompt-blinded (GM-F, 2026-09-11).** Where the manipulation
lives in persona configuration (rich vs. neutral `style_cues`, structured `Personal history`,
etc.), that material sits inside `raw_prompt` — the same file the Analyst must read to observe
voice and style. Extending a redaction word list does not fix this; the prose itself reveals
condition membership regardless of what's on the list. For any persona manipulation, choose
one of:

- withhold `raw_prompt` from the Analyst package entirely (ship transcripts —
  `raw_response` — and state only), or
- disclose in the brief that the manipulation is visible in the package, and rest the finding
  on mechanical measures (dispersion, not thematic coding) rather than blind content reading.

**Document which choice was made, per run**, in the mechanics report or manifest.

A package that rests its finding on mechanical dispersion (a standard deviation) is not
invalidated by a visible-condition leak — a stdev cannot be biased by knowing the condition.
Interpretive or thematic observations drawn from a package where condition membership leaked
are corroborative only, never independent evidence.

### Step 9 — Analyse · *Analyst*

Three layers, in this order:

**a. Thematic coding.** Read all elicitation responses and transcripts. Code inductively for
implementation challenges, facilitators, unintended consequences, points of friction. Do not
map onto any pre-existing framework.

**b. Cross-run frequency.** For each theme, in how many of the N runs does it appear? **This
is the credibility filter and the most important output.** A theme in 5 of 5 runs is what the
simulation reliably says. A theme in 1 of 5 is stochastic noise. Report the frequency beside
every theme.

**c. Attitude trajectories.** Plot support, resistance and workload stress per actor across
rounds, per run. Read: who moved, when, in response to what. Note where runs diverge.

**Output:** themes with run frequencies, trajectory plots, and a plain statement of what was
consistent versus what appeared once.

### Step 10 — Review · *GM*

Reads the mechanics report and the analysis together, and rules on:

- Is the run technically sound?
- What did it show, at what confidence?
- Does anything require a re-run?
- What is worth doing next?

### Step 11 — File

`docs/research/runs/<scenario>/<date>/` holds: brief, fixture path and commit, mechanics
report, raw exports, analysis, GM ruling.

---

## 3. Gates

| Gate | Blocks on |
|---|---|
| Preflight → Smoke | Cost estimate within expectation |
| Smoke → Run | All smoke checks pass |
| Run → Analysis | GM accepts the mechanics report |
| Analysis → Conclusion | GM ruling |

---

## 4. Testing the workflow itself

When the object is to test *this process* rather than the output:

- Use a **trivial programme and a small roster.** The point is to find where handoffs break,
  not to get good output.
- **Run the full sequence anyway**, including the blind analysis handoff. Skipping steps is
  how you discover in December that step 8 never worked.
- **Record where it was awkward** — that is the deliverable. A run that produces useless output
  but a clean process is a success.

**Recommended first workflow test:** the existing CIEPSS School B roster with a completely
different programme. Only the policy changes, so if the output shifts sensibly, the platform is
responding to the programme rather than replaying its personas. If the challenges come out
much the same regardless of what is being implemented, that is worth knowing immediately.
Three seeds, one afternoon, roughly ten dollars.

---

## 5. Standing constraints

- **Exploratory runs are not validity evidence.** No exploratory output is cited as showing
  Senna reproduces anything.
- **Ops reports mechanics; the Analyst reports content.** Neither does the other's job.
- **Frequency across runs, always.** A finding from one run is an anecdote.
- **Plausible is not accurate.** Without a documented case there is no way to check whether
  convincing output is correct. These runs test whether the platform generates useful
  hypotheses, not whether it predicts.
