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
