# MiroFish MVP — Frontend user guide

This guide explains the **web UI** in everyday language: what each **tab** is for, and what each **field or control** does. You do **not** need to be a programmer to use the Run tab and watch results; some tabs (Agent, Experiments, Scenarios) assume you are comfortable with concepts like “simulation run ID” or optional CSV data.

**How the tabs behave:** Switching tabs does **not** reset your forms. You can start a run on **Run**, switch to **Live** or **Transcript**, then come back — your settings stay. Many views need a **loaded run**: either press **Start simulation** on the **Run** tab, or **Load in UI** / **Open run by ID** so the app knows which simulation to show.

---

## Tab: Run

This is the main place to **configure and start** a simulation, **see status**, **download data**, and **open past runs**.

### Scenario

- **What it is:** Which world / policy story the simulation uses (for example PSLE reform, FSBB comparator).
- **What you do:** Pick one from the dropdown. Built-in scenarios may show “RAG” if that scenario can attach documents for the model to read.

### Total rounds

- **What it is:** How many **discussion rounds** the simulation will run (each round can include several agent “turns,” depending on mode).
- **What you do:** Enter a number from 1 to 25. Higher = longer runs and more API cost if you use a cloud model.

### Convergence stop (optional)

- **Threshold (0–1, empty = off)**  
  - **What it is:** If you type a number here, the engine can **stop early** when attitudes have **barely changed** for several rounds in a row (instead of always running all “total rounds”).  
  - **Lay explanation:** Think of it as “stop when the crowd has settled.” Leave **empty** to always run the full number of rounds you set above.  
  - **Typical values:** Small decimals like `0.01` or `0.05` — the UI hint explains it’s about average change in support, resistance, and workload stress across agents.

- **Patience (consecutive rounds)**  
  - **What it is:** How many rounds in a row the “small change” condition must hold before the run stops.  
  - **Example:** Patience `2` means “two rounds in a row must look stable.”

### Agent limit

- **What it is:** How many **simulated people** (agents) are in the run.
- **What you do:** Enter a number (the UI shows a cap; large values mean **long** wall-clock time because the model may run many turns per round).

### Roster CSV (optional)

- **What it is:** A **table** (pasted as text) that lists **who** is in the simulation — roles, names, optional groups, etc.  
- **What you do:** Leave blank to use the scenario’s default cast, **or** paste CSV rows. Use the **download template** link for the exact column headers the server expects.

### Population pool CSV (optional)

- **What it is:** A larger **pool** of people; the engine can **sample** a subset to fill the roster, using your **random seed** so runs can be repeated.
- **What you do:** Leave blank if you don’t need a custom population. If you paste data here, you can choose **Population sample mode**:
  - **Weighted** — draw from the full pool with weights.
  - **Stratified** — balance draws using a “stratum” column (when your CSV has one).

### Random seed

- **What it is:** A number that controls **random choices** (who gets sampled, speaker order in some modes, etc.).
- **What you do:** Keep the same seed if you want a **reproducible** run; change it for a different random draw.

### Interaction mode

- **Full round-robin** — In each round, **every** agent gets a turn (subject to scenario rules).
- **Sample K speakers per round** — Only **K** agents speak each round; others still **exist** and keep state, but fewer LLM calls per round.

When you pick **Sample K**, **Speakers per round (K)** appears: that is how many speakers per round.

### LLM routing (optional)

- **What it is:** Which **model backend** handles the agents’ language generation.
- **Choices (typical):**
  - **Server default** — use whatever the server is configured for.
  - **lmstudio** — a **local** model on your machine (no Anthropic billing through this path).
  - **anthropic** — cloud model (costs money; token counts and estimated USD appear in **Run metadata** when usage is recorded).
  - **hybrid** — a mix (for example frontier on some turns); see server docs for exact rules.

### Start simulation

- **What it does:** Sends your settings to the server and starts a new run. While it runs, status shows **starting** then **running**.

### Warnings from server

- **What it is:** Non-fatal messages (for example unknown roster IDs). The run may still proceed; details often appear in **Config snapshot** on **Run metadata**.

### Current run (same tab, below the form)

- **Status** — idle, starting, running, completed, failed, etc.
- **Progress (rounds completed)** — Goes up **after each full round** finishes. If it stays at 0, the first round may still be working; check **Transcript** for turns appearing.
- **Run id** — Unique ID for this simulation. You’ll need it for exports and for loading later.
- **Failure** — If something went wrong, a message appears here.
- **Download ZIP / Download JSON** — Export data for analysis (CSVs in ZIP, full JSON bundle).
- **Sampling report (JSON)** — After the run finishes (or fails), opens a structured report about **who was sampled** and tiers (useful for research).

### Recent runs

- **What it is:** A short list of simulations stored on the server.
- **Load in UI** — Loads that run’s results into the app (same as starting fresh, but for an old id).
- **ZIP** — Quick download for that run.

### Open run by ID

- **What it is:** Paste any **simulation id** (long hex string) and press **Load** to view it without scrolling the list.

---

## Tab: Live

**Purpose:** A **dashboard** for the **currently loaded run**: progress, sparkline charts, and per-agent trends.

- You must have **started** a run or **loaded** one from the **Run** tab.
- While the run is **running**, the page **polls** the server every ~750ms so charts update.

### What you see

- **Converged at round** (green banner, if applicable) — Early stop triggered by convergence settings; shows threshold and patience if saved.
- **Status / Run id** — Same run you loaded.
- **Progress** — Rounds completed vs total, number of **transcript turns** so far, and reminders of **agent limit**, **interaction mode**, and **population** info if used.
- **Global state sparklines** — **Implementation readiness**, **Alignment index**, **Convergence δ** (only meaningful from round 2 onward — round 1 has nothing to compare to).
- **Round outcomes** — Table of adoption momentum, conflict count, consistency per round.
- **Agents** — For each agent: latest support / resistance / workload / posture, plus small charts of how those three numbers move over time.

---

## Tab: Transcript

**Purpose:** Read the **raw dialogue**: what each agent “said” (model output) each turn.

For each turn you typically see:

- **Round** and **agent role / name**
- **Interaction type** and **target** (who they addressed)
- **Fidelity tier** — How “heavy” the model treatment was for that turn (tier 1 = full prompt, higher tiers may use cheaper or heuristic paths depending on server setup)
- **LLM** — Which provider/model bucket was used, if recorded
- **Text** — The actual response content

---

## Tab: Outcomes

**Purpose:** A **simple list** of **round-level outcome metrics**: adoption momentum, conflict events, consistency index — one row per round.

Use this when you want numbers **without** opening the Live charts.

---

## Tab: State

**Purpose:** **Per-round snapshots** of the whole population: a **global** headline for the round, then **each agent’s** numeric state (support, resistance, workload, belief posture) and optional **structured sections** (identity, attitudes, history) as JSON.

This is the deepest view of **how attitudes evolved**; it can be long for many agents.

---

## Tab: Run metadata

**Purpose:** **IDs, status, failure message**, **economics**, and the full **config snapshot** (everything the server stored about how this run was configured).

### Run economics (green panel, when available)

- **Tokens in / out** — Total input and output tokens recorded for the run (when the provider returns usage).
- **Estimated cost (USD)** — Rough dollar estimate using **list-price** defaults for billable provider turns (local / heuristic turns are often **$0**).
- **Provider (request)** — What you asked for at run start (`lmstudio`, `anthropic`, etc.).
- **Tier turns** — Count of turns at fidelity tier 1, 2, and 3.

### Config snapshot

- **What it is:** A JSON blob — the “receipt” for the run: scenario id, seeds, sampling strategy, convergence settings, experiment link if any, etc.
- **What you do:** Skim or copy for **reproducibility** and troubleshooting. No need to edit it here.

### Sampling report link

- Same JSON report as on the **Run** tab — tier/role/posture audit from the server.

---

## Tab: Validity

**Purpose:** Attach **your own research notes** to a run: **face**, **construct**, and **predictive** scores and rubrics (for validation / qualitative coding). Saved notes are included in API responses and exports.

You must **load a run** first (run id shown at the top of the form).

### Fields

- **Round (empty = whole run)** — Leave blank to attach the note to the **entire** run, or enter a round number for **that round only**.
- **Rater id** — Who is coding (you, a colleague, a codebook ID).
- **Face / Construct / Predictive score** — Optional numbers (often 0–1 in studies); leave blank if unused.
- **Face / Construct / Predictive rubric / notes** — Short text explaining how you scored or what you observed.
- **General notes** — Free text.
- **Save validity note** — Stores the note; it appears under **Saved notes** below.

---

## Tab: Experiments

**Purpose:** Run **several simulations in a row** with the **same** scenario and **same** random seed, but **different sampling strategies** — so you can **compare** strategies fairly. The server runs child simulations **one after another** (not in parallel).

### Create experiment

- **Name** — Label for your experiment (for your own records).
- **Scenario / Random seed / Total rounds / Agent limit** — Same idea as on the **Run** tab; these apply to **every** child run unless you extend the API elsewhere.
- **Convergence (optional)** — Same threshold/patience idea as **Run**, applied **equally** to every child run so comparisons stay fair.
- **Runs** — One row per child simulation:
  - **Label** — Short name (A, B, …) used in charts and tables.
  - **Sampling strategy** — How agents are chosen (full census, role stratified, network centrality, etc.).
  - **Add run row** / **Remove** — Build your list.
- **Start experiment** — Queues all runs. This can take a long time; **Cancel** aborts the **browser request** (the server may still finish in-flight work — see the message if you cancel).
- **Elapsed** — Seconds since you clicked start.

### Comparison chart

After an experiment is loaded or finishes:

- Shows **status**, optional **total estimated cost (USD)** across all runs.
- **Sparkline metric** — Choose which number to plot over rounds (readiness, alignment, adoption, conflicts, consistency, convergence delta).
- **All metrics by round (table)** — Expandable table; column headers may show **token counts and estimated cost** per strategy.
- **Download experiment ZIP / Open experiment JSON** — Full bundle for analysis (includes `comparison.csv`).

### Per-run status

- Each child run: strategy, status, convergence summary, tokens/cost, and the **simulation id** (useful to open in **Run** or **Compare two runs**).

### Recent experiments

- **Refresh** — Reload the list.
- **Load detail** — Opens that experiment’s charts and tables.

### Compare two runs (by ID)

- **What it is:** A **side-by-side** view of **outcome indicators** for **any two simulation IDs** (they do not have to be from an experiment).
- **What you do:** Paste two run IDs and press **Compare**.

---

## Tab: Agent

**Purpose:** Ask the built-in **assistant** to **plan** and/or **run** simulations in **plain English**, or to **plan only** / **execute** a JSON plan — useful for power users and automation.

### Research question

- **What it is:** What you want in natural language (at least **8 characters**).
- **Ask** — The server **plans** a multi-step execution, **runs** simulations, and returns **structured results** (key findings, narrative, etc.).

### Results (after Ask)

- One **card per simulated run** in the plan: status, simulation id, warnings, and **analysis** text (findings, narrative, follow-ups).
- **Show execution plan (JSON)** — Reveals the machine-readable plan the server produced.

### Advanced (constraints, plan/execute, tuning)

Expand **Advanced** for more control:

- **Constraints** — Extra instructions to the **planner** (optional).
- **Wait timeout per run (seconds)** — How long to wait for each simulation in the plan before timing out (large values for long runs).
- **Planner temperature (0–2)** — How “creative” the planner is; leave empty for defaults.
- **Plan max tokens** — Cap on planner output size; leave empty for defaults.
- **Run plan only** — Calls the planner **without** running simulations; fills the **Execute JSON** box.
- **Execute JSON plan** — Paste an **ExecutionPlan** (must include a `runs` array) and run it. Use this to replay or tweak a plan without re-asking.
- **Cancel request** — Stops the in-flight browser request (same idea as Experiments cancel).

---

## Tab: Scenarios

**Purpose:** **Author or copy** scenario definitions (policy text, personas, groups, optional RAG documents) through a **step-by-step wizard**, then **save** them to the server so they appear in the **Scenario** dropdown on **Run** and **Experiments**.

Typical steps (labels may vary slightly in the UI):

1. **Basics** — Scenario id, display name.
2. **Policy rounds** — What happens in each round (policy announcements, etc.).
3. **Personas** — Roles, names, beliefs, structured sections (identity, attitudes, history).
4. **Groups** — Optional stakeholder groups.
5. **RAG** — Optional document paths for scenarios that support retrieval.
6. **Review** — Check YAML / export, save, clone from template.

Exact buttons (generate from brief, LLM-fill persona, export YAML) depend on server features — use on-screen messages and errors as your guide.

---

## Quick “where do I click?”

| I want to… | Go to… |
|------------|--------|
| Start a single simulation with full control | **Run** → fill fields → **Start simulation** |
| Watch charts while it runs | **Live** (after starting or loading a run) |
| Read what agents said | **Transcript** |
| See attitudes per round | **State** |
| See tokens and estimated cost | **Run metadata** (after run completes or loads) |
| Compare sampling strategies fairly | **Experiments** |
| Ask the assistant to run something for me | **Agent** |
| Edit or add a scenario | **Scenarios** |
| Add my own validation scores | **Validity** |

---

## Document history

- **2026-04-09** — First version (matches MiroFish MVP frontend tabs and fields as implemented).
