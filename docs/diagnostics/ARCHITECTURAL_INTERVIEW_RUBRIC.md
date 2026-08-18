# Architectural Interview Rubric (Senna iter-47)

Park et al. five-category **architectural diagnostic** — measures which memory/context
component may be failing in an agent run. This is **not** a simulation validity instrument
and is administered separately from CIEPSS / Likert self-report.

**Scale:** integer **0–2** per category response.

| Score | Label | Meaning |
|-------|-------|---------|
| 0 | inadequate | Cannot demonstrate the capability; vague, off-topic, or contradicts transcript |
| 1 | partial | Some relevant evidence but incomplete, inconsistent, or weakly grounded |
| 2 | adequate | Clear, transcript-grounded demonstration of the category capability |

**Rubric version:** `1`

---

## self_knowledge

Agent articulates its role, goals, constraints, and stance in the simulation.

- **0:** No identifiable goals or role; generic filler unrelated to the run.
- **1:** Names role or goals but without linking to specific simulation behavior.
- **2:** Coherent account of role, goals, and stance with at least one concrete reference to their own turns.

## memory_retrieval

Agent retrieves a specific prior turn or peer statement from the discussion history.

- **0:** No specific recall; only abstract claims about “the discussion.”
- **1:** Vague recall (e.g. “someone disagreed”) without round, speaker, or content detail.
- **2:** Identifies a specific moment (round/speaker/content) and explains why it mattered.

## planning

Agent describes how it chose what to say (message, audience, tone) before acting.

- **0:** No planning process described; purely reactive or unrelated narrative.
- **1:** Mentions intent or audience but no stepwise or causal planning chain.
- **2:** Explicit steps or criteria used to plan an utterance, tied to simulation context.

## reaction

Agent explains immediate response to disagreement or challenge during the run.

- **0:** No example of reacting to disagreement or pushback.
- **1:** Example given but reaction is unclear or not linked to subsequent behavior.
- **2:** Concrete disagreement example with immediate reaction and follow-up action.

## reflection

Agent looks back on the full simulation and identifies learning or changes.

- **0:** No retrospective view; cannot name anything learned or different next time.
- **1:** Generic reflection (“I would listen more”) without simulation-specific grounding.
- **2:** Specific lesson or change grounded in at least one episode from the run.

---

## Judge output format

The judge model must append exactly one block:

```xml
<judge_score>{"score": 0, "rationale": "..."}</judge_score>
```

`score` must be 0, 1, or 2. `rationale` is a short audit string (optional but recommended).
