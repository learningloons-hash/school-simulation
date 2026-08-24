# senna-iter-53 — Results, Selection, Arc Closeout

**Spec:** [`docs/handoffs/HANDOFF_SENNA_ARC11.md`](../handoffs/HANDOFF_SENNA_ARC11.md) **`senna-iter-53`**
**Arc:** 11 — Memory Architecture
**Date:** 2026-08-24
**Status:** Iteration scope **CLOSED**; Arc verdict **pending GM-F ruling** (see Open Question below — same shape as the open question the handoff itself raised before `iter-51`)

## Sweep executed

- Harness: `senna-iter-52` (`scripts/run_arc11_ablation.py`), local LM Studio (`dolphin3.0-llama3.1-8b`) + Anthropic-routed architectural interview.
- 4 conditions × 3 seeds (42/43/44) = 12/12 runs complete, clean. No `[LLM error]` transcript entries, no context-length failures on the final pass.
- One reliability bug found and fixed mid-sweep: the interview retry path could collide with the "already exists" uniqueness guard after a partial write from a failed first attempt (`scripts/run_arc11_ablation.py`, commit `cea1df2`) — fixed, regression-tested, does not affect result validity (the affected run was fully redone from a fresh simulation, not salvaged).
- Baseline reference: `docs/diagnostics/ARC10_MEASURED_BASELINE_REAL_RUN.md` (real run, not fixture).

## Results table (condition-arm means, n=3 seeds each)

| Condition | MemBench factual | MemBench reflective | Interview: memory_retrieval | Interview: reaction | Interview: planning | Interview: reflection | Interview: self_knowledge | Mean input tokens | Wall-clock (mean, s) |
|---|---|---|---|---|---|---|---|---|---|
| `baseline` | 1.0 | 1.0 | 2.00 | 0.56 | 2.00 | 2.00 | 2.00 | 25,887 | 178.7 |
| `+importance` | 1.0 | 1.0 | 1.67 | 0.56 | 2.00 | 2.00 | 2.00 | 30,739 (+18.7%) | 159.4 |
| `+importance+retrieval` | 1.0 | 1.0 | 1.67 | 0.33 | 1.89 | 2.00 | 2.00 | 33,022 (+27.6%) | 198.9 |
| `+importance+retrieval+reflection` | 1.0 | 1.0 | 1.22 | 0.33 | 1.89 | 2.00 | 2.00 | 37,002 (+43.0%) | 184.8 |

Interview scores are 0–2 per category, averaged across 3 agents × 3 seeds. These are condition-arm means computed directly from `arc11_ablation_results.json`, not the file's own `deltas_vs_baseline` field — that field compares each run against the single Arc 10 reference simulation (n=1), which is too noisy to read as a trend. Cost USD reads $0.00 throughout (local model has no metered cost; Anthropic is used only for the interview, which is a fixed per-run cost not modeled here).

## Dispersion (Cui, Li & Zhou 2025 false-homogeneity check)

| Condition | Final-round support stdev (mean) | Cross-agent interview-score stdev |
|---|---|---|
| `baseline` | 0.0438 | ~0.00 (agents answer near-identically) |
| `+importance` | 0.0438 | ~0.31 (agents differentiate) |
| `+importance+retrieval` | 0.0438 | ~0.31 |
| `+importance+retrieval+reflection` | 0.0492 | ~0.27 |

No collapse toward homogeneity as mechanisms stack — the opposite, if anything: baseline agents give each other's interview answers, and adding importance + retrieval breaks that up. This is the one clearly positive, hypothesis-consistent finding in the sweep.

## Findings

**1. MemBench cannot discriminate on this run profile.** Factual and reflective accuracy sit at 1.0 in all 12 runs — a ceiling effect, not evidence of "no difference." The recall-vs-synthesis prioritization hypothesis (the arc's stated reason for ordering importance → retrieval → reflection) is **untested**, not confirmed or refuted, by this instrument at this scenario size (3 agents, 5 rounds).

**2. Architectural interview scores trend down, not up, as mechanisms stack.** `memory_retrieval` goes 2.00 → 1.67 → 1.67 → 1.22 from baseline to full stack — the opposite of what the prioritization hypothesis predicts for the category most directly tied to recall. `reaction` and `planning` show smaller declines in the same direction. `reflection` and `self_knowledge` are pinned at the 2.0 ceiling in every single arm — iter-51's own DoD question ("does the interview `reflection` category improve against the real baseline?") has a direct answer here: **no measured movement at all**, ceiling or otherwise.

**3. Cost scales up substantially with no offsetting measured gain.** Mean input tokens rise 19% (`+importance`), 28% (`+retrieval`), 43% (`+reflection`) over baseline. Nothing in MemBench or the interview shows a compensating quality improvement to justify that spend on this evidence.

**4. This is a power/instrument problem, not necessarily a negative result.** n=3 seeds, a 3-agent/5-round toy scenario, a single 8B local model, and a 0–2 integer interview rubric together make this a low-resolution instrument. The interview decline could be a real mechanism effect, or it could be the local model's context/attention degrading as prompts grow from ~26k to ~37k tokens — the ablation as run cannot separate those two explanations. **This should be reported as inconclusive, not as "importance/retrieval/reflection don't work."**

## Selection decision (D3 — decided on the evidence at this point)

**Recommendation: ship all three mechanisms behind their existing flags, all default OFF.** None demonstrated measured benefit on the platform's own instruments at the evidence quality this sweep can produce; the honest position is "not enough signal to flip the default," not "proven not to help." Flipping any flag on by default now would mean shipping a cost increase (up to 43% more tokens) on the strength of a null result from an instrument that was ceilinged for half of what it was meant to measure.

**What would make this decisive:** a re-run at a scenario size where MemBench isn't saturated (more distinct facts/rounds than 5), more seeds (5–10), and ideally a second model tier to separate "mechanism effect" from "small local model under longer prompts." Not proposed as in-scope for Arc 11 — flagging for Arc 12 pre-registration per D3's requirement that the selection call is an input to that document.

## Shipping configuration (frozen for Arc 12)

| Flag | Default | Notes |
|---|---|---|
| `importance_scoring_enabled` | `false` | Unchanged from Arc 10 |
| `weighted_retrieval_enabled` | `false` | Unchanged from Arc 10 |
| `reflection_enabled` | `false` | Unchanged from Arc 10 |
| `working_memory_last_k` / `peer_context_max_chars` | Arc 1 defaults (2 / 1200) | Not touched this arc, per non-negotiables |

`EXPORT_VERSION` remains **14** (set at `iter-51`) — no new fields this iteration.

## Open question for GM-F (carried from the handoff's own Open Question 1)

The handoff explicitly asked: *"If the item-1 real baseline contradicts the prioritisation hypothesis... does Arc 11 proceed as scoped, or is the emphasis re-ordered?"* This sweep didn't contradict the hypothesis outright — it couldn't test it (MemBench ceiling) and produced a mild, likely-confounded signal in the opposite direction on the interview. Escalating rather than absorbing: **does this count as the contradiction the handoff anticipated, and if so, does Arc 12's pre-registration need to address instrument resolution (MemBench scenario size, model tier) before re-litigating the mechanism question?**

## Is Arc 11 complete?

Build scope is done — `iter-49` through `iter-52` are individually closed, the ablation ran clean end to end (12/12), and this closeout delivers the required selection decision, shipping configuration, and Arc 12 handoff note. What's outstanding is the same as every prior arc in this project: **GM-F review and a PASS ruling** before the Arc Status table in `CLAUDE.md` can move from open to `✅ CLOSED (GM PASS)`.
