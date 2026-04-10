# Handoff: Opus → Cursor — 2026-04-06 (v2)

**From**: Claude Opus (architect-reviewer, Cowork)
**To**: Cursor (build agent)
**Re**: Sign-off on revised Iterations 21–27 + ADR-002 + priority ordering
**Cross-ref**: `docs/handoffs/HANDOFF_CURSOR_TO_OPUS_2026-04-06.md` (your revised roadmap — what I'm responding to)
**Supersedes**: v1 of this file (original Iterations 21–23 spec, written before I saw your revised plan)

---

## 1. Roadmap Sign-Off: Iterations 21–27

**Approved with adjustments noted below.**

The expansion from 3 large iterations to 7 focused ones is the right call. The three-dimensional sampling decomposition (population draw → sampling strategy → round participation) is exactly the conceptual separation needed. Each dimension composing left-to-right is clean and testable independently.

### Per-iteration notes

**Iteration 21 (Generic Engine Cleanup)** — ✅ Approve as scoped.
Do this first. The `school_trinidad` overlay should be explicitly documented as the canonical pattern for domain-specific scenario packs. This is what I'll reference in the grant proposal. One addition: add a brief `docs/domain-packs.md` explaining the pattern — it's a one-pager that helps reviewers understand the generic/domain split.

**Iteration 22 (Sampling Strategy Contract)** — ✅ Approve as scoped.
Two notes:
1. `role` values must be collected dynamically from the scenario YAML, not from any hardcoded list. This is non-negotiable for the generic engine.
2. The `fidelity_tier` override column on the roster CSV is important — for the FSBB validation study, I need to force specific personas (e.g. principal, VP) to Tier 1 regardless of strategy.

**Iteration 23 (Tier-Aware Orchestrator)** — ✅ Approve. One clarification on Tier 2:
- Include: role, current belief state, basic position on the policy, round context
- Omit: psychological profile, biographical detail, influence network edges
- This gives Tier 2 structural participation without expensive per-persona depth. Cursor can encode this as a `simplified_persona_prompt()` function.

**Iteration 24 (Tier-3 Heuristic + hybrid_core_remainder)** — ✅ Approve as scoped.
The dampened mean shift + seeded noise heuristic is methodologically sound. For the 300-agent stress test: 30 Tier-1 + 270 Tier-3. Raise `agent_limit` to 300 as part of this iteration (not a separate slice).

**Iterations 25, 26, 27** — ✅ Approve as scoped.

---

## 2. Priority Ordering: Iterations 24/25/26

**My order: 24 → 26 → 25** (differs from your suggested default of 24 → 25 → 26)

Rationale:
- **24** first: `hybrid_core_remainder` is the most research-valuable strategy and directly enables the grant proposal's validation study design.
- **26** second (posture_maxvar): Maps directly to Trinidad's school archetypes — `active_sense_maker`, `compliant_implementer`, `selective_adopter`. This is what I'm demoing at the **October 2026 MOE conference**. I need it before the conference, not after.
- **25** third (network_centrality + network_bounded): Important for the full research study but less time-critical for the October deadline.

---

## 3. 500-Agent Ceiling

Fold the `agent_limit` raise into Iteration 24's stress test — raise to 300 there. Do not create a separate hardening slice. Document 500 as architecturally feasible (your feasibility note already does this) but defer implementation until post-Iteration 27 based on actual stress test results.

---

## 4. ADR-002: Interaction Visibility Policy

Author as `docs/adr/ADR-002-interaction-visibility.md` before Iteration 25 starts. I'm writing the draft here so Cursor can implement directly.

```markdown
# ADR-002: Agent Interaction Visibility Policy

**Status**: ACCEPTED
**Date**: 2026-04-06
**Deciders**: Mark (research owner), Opus (architect)

## Context

In each simulation round, agents observe prior turns before generating their own response.
The set of turns visible to each agent is its "visibility window." This affects simulation
realism, computational cost, and — critically — the validity of the simulation as a model
of real organisational dynamics (where information is never fully broadcast).

Three visibility regimes need to be supported for different research designs.

## Decision

Implement three visibility policies, selectable per run via `interaction_visibility` on
`SimulationRunRequest`. Default: `broadcast` (preserves backward compatibility).

| Policy | Agent sees | When to use |
|--------|-----------|-------------|
| `broadcast` | All turns from the current round so far | Small populations, full-information baseline |
| `round_participants_only` | Only turns from agents selected to speak this round | Natural companion to `sample_k_per_round` mode |
| `network_bounded` | Only turns from agents with a direct edge in the network CSV | Network topology studies (Iteration 25+) |

## Implementation Notes

- Refactor existing `visible_turns_for_agent()` to accept `(policy, network_graph, ...)`.
- Network graph: simple adjacency dict `{agent_id: set(neighbor_ids)}`; load once at run
  creation, pass through to orchestrator. No external graph library needed.
- `network_bounded` falls back to `broadcast` with a logged warning if `network_csv` is absent.
- Do NOT implement `network_bounded` logic until Iteration 25 — design the interface now so
  it slots in cleanly.
- `interaction_visibility` must be recorded in `config_snapshot` for reproducibility.

## Consequences

- `broadcast` remains default; zero regressions.
- `round_participants_only` is now a first-class field, not an implicit side-effect.
- `network_bounded` unlocks sociologically realistic simulations where information follows
  the actual influence network (aligns with Spillane's distributed leadership model).
```

---

## 5. Pre-Iteration 21 Bug Fix

`build_capabilities_dict()` still returns `export_version: "4"` instead of `"5"`. This is a 1-line fix. Joan should clean this up before starting Iteration 21 — it's not a full iteration, just housekeeping.

---

## 6. Conference Demo Target (October 2026)

For awareness when scoping iterations: the October 2026 MOE internal conference demo needs:
- Generic engine (Iteration 21) ✓
- At least two sampling strategies working end-to-end (Iterations 22–23) ✓
- posture_maxvar live (Iteration 26) — **this is the demo centrepiece**
- Enough of the experiment framework (Iteration 27) to show side-by-side strategy comparison

If Iterations 21–26 are done before October, the demo is solid. Iteration 27 (full experiment framework) is a bonus.

---

## 7. Session Protocol

Going forward, Opus will read `HANDOFF_CURSOR_TO_OPUS_[latest-date].md` at the start of each MiroFish strategic session. For major roadmap changes, write a `HANDOFF_CURSOR_TO_OPUS` file as you did today — that's exactly the right communication pattern. Iteration closeout docs + `SESSION_STATE.md` remain the source of truth for build status.

---

*Written by Opus, 2026-04-06 (v2). Supersedes v1 of same date.*
*Next action for Joan: fix `export_version` bug → start Iteration 21.*
