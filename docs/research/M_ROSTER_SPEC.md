# M-ROSTER: roster join/leave (per-actor activity windows)

**Repo:** [learningloons-hash/school-simulation](https://github.com/learningloons-hash/school-simulation) (public)
**Milestone:** M-ROSTER. The pre-reg calls this **M-joinleave** (§14.2 table, line 712), and the two names mean the same milestone. It is a research/platform milestone, not a numbered UX Arc.
**Branch:** `m-roster-join-leave`, cut from `main` @ `9739f09` (merge of PR #18, M-RENAME).
**PR:** one branch, one PR against `main`. Mark merges. The builder does not merge or deploy.
**Tests:** written by an independent tester (Claude Code) in a separate PR on branch `m-roster-tests`. The builder writes no tests.
**Drafted:** 2026-11-16 (Asia/Singapore). Code refs were read at `9739f09`, and line numbers are from that commit. Anything marked **[unverified]** was not read in code.
**Data rule:** synthetic and de-identified data only. Do not put the School S or Ahn fixtures, names, or paper text into this PR. Examples below use synthetic names.

---

## 1. Goal

Give each roster actor an optional **activity window**, `active_from_round` … `active_until_round` (inclusive, 1-based). Outside that window the actor takes no turns, is not sampled, gives no Likert, and is left out of convergence and spread metrics.

A **newcomer** (an actor whose window starts after round 1) joins **without the prior transcript**. It has no peer turns or round summaries from before its join round. It gets an optional **handover note** rendered from **one fixed scenario-level template**, and the note is visible only to that actor and labelled as a handover. Active actors are told who is absent each round, with a reason only where the fixture supplies one. Every windowed run exports **active agents per round** and a window-compliance audit.

**Hard invariant:** if no actor has an inactive round inside `1..total_rounds`, the run is **byte-identical** to `main`. That means the same prompts, turn order, RNG draws, DB rows, metrics, transcript markdown (apart from existing timestamps), config_snapshot keys, export zip members and preflight output. Every new behaviour is gated on `windowing_active` (§4.1).

---

## 2. Pre-registration traceability

Source: `/workspace/senna/PREREG_SENNA_SSTRF_V3_2_DRAFT.md` (v3.2 draft). Quoted text is verbatim from that file.

| Pre-reg ref | Requirement (verbatim or near-verbatim) | Where this spec covers it |
|---|---|---|
| §7.3 Rule (l. 280–286) | "Each actor has `active_from_round` and `active_until_round` (inclusive). Outside that window the actor: does not speak; is not sampled as a speaker; is excluded from that round's convergence statistic and from between-agent spread metrics. The actor may remain on the roster as an inactive record so that a later join is possible. Every confirmatory and single-author export reports **active agents per round**." | §3, §4.2–4.5, §7 |
| §7.3 Information rule (l. 290) | "A newcomer **does not** receive the prior transcript." | §4.3 |
| §7.3 (l. 291) | "The newcomer receives a handover note from **one fixed template**, limited to **given-as-input** facts only: cycle or mapped year, topic if the fixture already names it as a scheduled episode, and schedule. The note must not contain can-emerge findings, proposition wording, or invented gossip. Colleagues can brief the newcomer inside the run." | §3.2, §4.4 |
| §7.3 (l. 292) | "**Round summaries from before the join round are excluded** from the newcomer's context (otherwise they leak the prior transcript)." | §4.3 |
| §7.3 (l. 293) | "Active agents are told **who is absent** that round, with a reason **only where the paper gives one** … Where the paper gives no reason, absence is announced without a reason." | §4.6 |
| §7.3 (l. 294) | "Departed actors do not keep speaking, and their later absence is simply absence, not a scripted farewell, unless the paper documents a handover." | §4.2, §4.7 (no farewell turn is generated) |
| §7 item 1 (l. 231) | Perception covers "contributions of linked *active* actors". | §4.2: only active actors produce contributions |
| §7 item 2 (l. 232) | "Group-addressed contributions reach every *active* actor. Inactive actors' prior turns are not in a newcomer's context except via the optional handover note (§7.3)." Knobs `working_memory_last_k`=2, `peer_context_max_chars`=1200 and `round_summary_enabled`=true are "subject to … the join/leave information rule". | §4.3 |
| §7 item 3 (l. 233) | "Turns proceed in seniority order among **active** agents." | §4.2 (turn order applied to the active subset) |
| §8 (l. 362–367) | Report "**active agents per round**". "Inactive actors are excluded from `convergence_delta` and from between-agent spread for the rounds they are inactive." | §4.5, §7 |
| §7.3 Process audit (l. 336) | "report whether activity windows were respected (who spoke in which rounds)." | §7.3 `roster_window_audit` |
| §7.3 Platform (l. 338) | "Current `main` builds a fixed roster for the whole run. That is the gap this milestone closes, including the handover template, pre-join summary exclusion, and absence notices." | Whole spec. Confirmed in code: `orchestrator.py` l. 749 builds `agents` once and l. 824–836 iterates it every round. |
| §7.3 Ahn windows (l. 332), D35 (l. 972) | "Ahn 7 / 5 / 4 allocation is **one random draw under a frozen ID**, held constant across all cells." | §3.4 (pure draw helper), Q5 |
| §13 (l. 584, 618, 654) | "Join/leave reducing billed turns: **Not credited.** … the envelope bills as if the full included roster spoke every round." | §6 (the headline stays uncredited) |
| §13.3 (l. 662) | "Join/leave can only reduce those counts." | §6, §7 |
| §14.2 M-joinleave (l. 712) | "Roster join/leave by round; inactive actors do not speak, are not sampled, and are excluded from convergence and spread; **fixed handover template** …; **exclude pre-join round summaries**; **absence notices** …; frozen 7 / 5 / 4 draw; active-agent export." "Required before freeze." | Whole spec |
| §14.2 M4 (l. 704) | "skip Likert LLM calls for fidelity Tier 3 / synthetic remainder **and for inactive actors**". | §4.5 (the inactive-actor half only; the Tier-3 skip stays in M4) |
| Freeze manifest (l. 393), ODD annex (l. 1098) | The freeze records the "activity-window table, handover template, absence-notice rule, frozen 7 / 5 / 4 draw ID", and the annex carries "handover template; absence-notice wording". | §4.4, §4.6 fix exact wording; §7 records them in config_snapshot |
| §4 (l. 156), §7.1 (l. 258), §7.3 (l. 304) | School S windows are "**inferred from an interview table**". | Fixture label only (fixture freeze, out of scope). The platform carries an optional free-text `window_basis` (§3.1). |

---

## 3. Data model

### 3.1 Per-actor fields

These are optional everywhere. Absent or empty means "active in every round", which is today's behaviour.

| Field | Type | Meaning |
|---|---|---|
| `active_from_round` | int ≥ 1 | First active round (inclusive). Default 1. |
| `active_until_round` | int ≥ 1 | Last active round (inclusive). Default `total_rounds`. |
| `absence_reason` | short string | Reason stated in absence notices. Use it **only** if the source documents one. Empty means the actor is announced without a reason. |
| `window_basis` | short string | Provenance label, e.g. `inferred from interview table`. Export and audit only. **Never shown in prompts.** |

Where they live:

1. **Scenario YAML persona:** new optional keys on each `personas[]` item. Today `PersonaTemplate` is at `scenarios/registry.py` l. 24–44 and is parsed by `_persona_from_mapping` at l. 196–215.
   - Add `active_from_round: int | None = None`, `active_until_round: int | None = None`, `absence_reason: str = ""` and `window_basis: str = ""` as the **last** fields, with defaults. There are 12 `PersonaTemplate(` call sites, and positional construction must not break.
2. **Roster CSV:** new optional columns `active_from_round`, `active_until_round`, `absence_reason`, `window_basis`.
   - Today `ParsedRosterRow` is at `roster/csv_roster.py` l. 12–35, `parse_roster_csv` at l. 64–161 and `merge_persona_for_slot` at l. 164–202.
   - Add the matching `ParsedRosterRow` fields with default `None`.
   - Merge rule: a non-empty cell overrides YAML and an empty cell inherits YAML. This is the same convention as `implementation_posture` (l. 182–186).
3. **Population CSV:** **out of scope** (see §10).
4. **`scenarios/serialize.py`** (`scenario_config_to_document`, l. 10): emit the new keys **only when set**, so existing scenario documents round-trip unchanged.

### 3.2 Scenario-level fields

These go in a new optional YAML block, `roster_windows:`, on `ScenarioConfig` (`registry.py` l. 48–65; parsed in `_scenario_from_mapping`, l. 246–274).

```yaml
roster_windows:                 # optional; omitted = today's behaviour
  handover_template: |          # optional; omitted = newcomers get no handover note
    You are joining this group from round {join_round} of {total_rounds}.
    This round's scheduled activity: {join_policy_event}
  absence_notice_scope: all_inactive   # all_inactive | departed_only | none   (Q1)
```

- **Allowed placeholders, a closed set:** `{name}`, `{role}`, `{join_round}`, `{total_rounds}`, `{join_policy_event}`. `{join_policy_event}` is the text `_policy_event_for_round(scenario, join_round)` returns (`orchestrator.py` l. 574–580), and it is already given-as-input text. Validate the set with `string.Formatter().parse`. Any other placeholder, or a positional `{}`, is a validation error. `{{` and `}}` escapes are allowed.
- **Fixed template:** the template is the single "fixed template" of pre-reg §7.3. There is **no per-actor free-text handover note** in this build (see Q3 and §11, conflict C1).
- Add a `roster_windows: RosterWindowsConfig | None = None` field to `ScenarioConfig` as the last field, with a default.

### 3.3 Resolved run model (new module)

New module **`backend/src/senna_backend/simulation/roster_windows.py`**. It holds pure functions only (no I/O and no RNG), so the future single-author runner (M-baseline) can reuse it.

```python
@dataclass(frozen=True)
class ActivityWindow:
    agent_id: str
    active_from_round: int      # resolved, 1..total_rounds
    active_until_round: int     # resolved, active_from_round..total_rounds
    absence_reason: str         # "" if none
    window_basis: str           # "" if none

def resolve_activity_windows(agent_ids: list[str], personas: list[PersonaTemplate],
                             total_rounds: int) -> tuple[dict[str, ActivityWindow], list[str]]:
    """Return (windows_by_agent_id, warnings). Raises ValueError on §5 errors."""

def windowing_active(windows: dict[str, ActivityWindow], total_rounds: int) -> bool:
    """True iff some agent has an inactive round inside 1..total_rounds."""

def is_active(window: ActivityWindow, round_number: int) -> bool
def active_agent_ids_for_round(windows, ordered_agent_ids, round_number) -> list[str]   # preserves input order
def join_round(window) -> int | None      # active_from_round if > 1 else None
def render_handover_note(template: str, *, name, role, join_round, total_rounds, join_policy_event) -> str
def absence_notice_for_round(windows, agents_by_id, round_number, scope) -> str | None   # exact wording §4.6
def active_agents_per_round_rows(windows, ordered_agent_ids, total_rounds) -> list[dict]  # §7.2
```

Synthetic remainder agents (`simulation/remainder.py`) never carry windows. They are active in every round.

### 3.4 Frozen tenure draw helper (pre-reg §7.3, l. 332; see Q5)

New module **`backend/src/senna_backend/roster/tenure_draw.py`**, plus a CLI wrapper **`scripts/draw_tenure_windows.py`**. The wrapper reads a synthetic or fixture slot list and writes a windows CSV that `roster_csv` can consume.

```python
def draw_tenure_windows(*, slot_ids: list[str], tenure_counts: dict[int, int],   # e.g. {3: 7, 2: 5, 1: 4}
                        year_bands: list[tuple[int, int]],                       # e.g. [(1, 8), (9, 14), (15, 20)]
                        draw_id: str, pinned: dict[str, int] | None = None,     # slot_id -> tenure years
                        pool: str = "teachers") -> dict[str, tuple[int, int]]
```

- **Determinism:** `rng = random.Random(int.from_bytes(hashlib.sha256(f"{draw_id}|{pool}|v1".encode()).digest()[:8], "big"))`.
  - Never touch the global `random` module. `orchestrator.py` l. 736 calls `random.seed(random_seed)`, and global draws would perturb runs.
  - Process `slot_ids` in sorted order.
  - Pinned slots consume their tenure count first.
  - Then shuffle the remaining slots, and assign the remaining tenure multiset in a fixed order (longest first).
  - For each L-year slot (L < number of bands), pick a start band uniformly from the valid consecutive starts, in sorted slot order.
- **Window value:** a slot's window is `(year_bands[start][0], year_bands[start+L-1][1])`.
- **Errors:** raise `ValueError` if `sum(tenure_counts.values()) != len(slot_ids)`, if a pinned tenure isn't in `tenure_counts`, or if any L is greater than `len(year_bands)`.
- **Output:** the CLI writes `slot,active_from_round,active_until_round,window_basis` with `window_basis = "frozen tenure draw {draw_id} (algorithm v1)"`.
- **Not in scope:** the year-band map and slot list are fixture-freeze inputs. This PR ships **no** Ahn fixture.

---

## 4. Semantics

### 4.1 Gating

Before round 1, `run_simulation_task` (`orchestrator.py` l. 650) resolves the windows from the built `agents` (l. 749–751) and `scenario`. If `windowing_active(...)` is False, **every code path below is skipped** and behaviour is unchanged. That includes a scenario with a `roster_windows` block but full windows.

### 4.2 Turns, sampling and turn order

- **Active subset.** At the top of each round (`orchestrator.py` l. 824–836), compute `active_agents = [a for a in agents if is_active(...)]` and pass it to `_agents_for_round` (l. 255–282) in place of `agents`.
  - `full_round_robin` returns all active agents.
  - `sample_k_per_round` samples K from the active agents only. It uses the same seed mix (l. 277), with `n = len(active_agents)` and `k = min(speakers_per_round, n)`.
- **Turn order.** `apply_turn_order` (l. 835; `interaction_policy.py` l. 223) then runs on the active subset, which gives "seniority order among active agents" (pre-reg §7 item 3).
- **Interaction plan.** `_build_interaction_plan` (l. 583–647) already works over `round_agents`. Broadcast, reply and meeting roles are therefore computed among active speakers only, and a `reply` can only target an active agent.
- **Spoken IDs.** `spoke_ids` (l. 836) holds only active speakers, so `ROUND_PARTICIPANTS_ONLY` visibility (`interaction_policy.py` l. 284–297) is naturally limited to active actors.
- **Departures.** Inactive actors never call the LLM, never get an `agent_turns` row, and produce no farewell turn.
- **Recency window.** The peer window size at l. 1063–1080 stays **unchanged**: it still uses `len(agents)` at l. 1077, not the active count. This is deliberate. Changing it would alter prompt windows in windowed runs beyond the information rule. See §11 C3 for a related pre-existing mismatch.

### 4.3 Newcomer information rule (no prior transcript)

For an agent with `join_round = J > 1`, every **peer** context source must drop items from rounds `< J`.

1. **Peer turns, non-weighted path.** Filter `recent_visible` / `recent_interactions` (l. 1226–1251) to `round_number >= J`. Peer prompts only hold prior-round turns (`_peer_turns_for_prompt`, l. 114–126), so in round J the newcomer sees **no** peer lines and gets "- (none)". From round J+1 it sees round-J turns onward.
2. **Peer turns, weighted-retrieval path.** Apply the same filter to `peer_pool` (l. 1160–1164) before `rank_turns`. Memory mechanisms are off for confirmatory runs (pre-reg D17, l. 342), but this path must still be correct.
3. **Round summaries.** `get_round_summaries` (`db/repo.py` l. 2132–2161) returns every round `< round_number`. Filter the returned rows to `round_number >= J` before building `prior_summaries` (l. 1270–1277). In round J the newcomer gets `round_summaries=None`, so `build_user_prompt` uses its no-summary heading (`prompt_templates.py` l. 164–168).
4. **Self memory.** The newcomer has no own turns before J because inactive actors never insert turns, so working memory starts empty by construction. Do not add code here. The tester asserts it.
5. **Likert visible history.** In `_collect_round_end_likert` (l. 428–448), filter `recent_visible` to `round_number >= J` for that agent.
6. **Memory-context inclusion log.**
   - Pre-join candidates the observer could otherwise have seen are logged with a new exclusion reason, `"pre_join"`.
   - Extend the `ExclusionReason` Literal (`memory_context.py` l. 10–15).
   - In `summarize_memory_context_log` (l. 236–260), add the `"pre_join"` key to `exclusion_breakdown` **only if at least one row has it**. Existing summaries and fixtures pin the current key set: `tests/test_senna_iter45_memory_context.py` l. 312 and `tests/fixtures/arc10|arc11/*.json`.
7. **Scope of the rule.**
   - It applies only to the newcomer's own context.
   - Active agents keep seeing departed agents' earlier turns inside their normal recency window, because those turns were spoken.
   - Agents with `active_from_round == 1` are never newcomers.

### 4.4 Handover note

- **When it appears.** Only for a newcomer (J > 1), only if `roster_windows.handover_template` is set, and only on the newcomer's turn(s) in **round J** (Q2).
- **Where it goes.** Add a new optional kwarg `handover_note: str | None = None` to `build_user_prompt` (`prompt_templates.py` l. 116–128). When it is not None, insert this block immediately after the `Policy event:` line:

  ```
  Handover note (given to you on joining; only you can see this):
  {rendered note}
  ```

  followed by one blank line. When it is None, the output is byte-identical to today.
- **Visibility.** It is never written as a turn, never in round summaries, never in another agent's context, and never in the Likert prompt.
- **Audit record.** The rendered text is stored per agent in `config_snapshot.roster_windows.handover_notes` (§7.1). It also appears inside that turn's existing `raw_prompt`.

### 4.5 Likert, state and metrics

- **Likert.** `_collect_round_end_likert` is called with `agents=agents` (l. 1637), i.e. **everyone**. Pass the round's **active** agents instead, which means no LLM call and no `agent_round_likert` rows for inactive agents. A leaver's Likert series simply stops after `active_until_round`, and a joiner's starts at J. Nothing is back-filled or imputed.
- **Float state.** An inactive agent's float state is not updated (it takes no turn). It stays frozen at its last value, or at its initial value before joining.
- **Tier-3 heuristic.** The update (l. 1614–1630) applies only to active Tier-3 IDs. Remainder agents are always active, so hybrid runs are unchanged.
- **Global aggregates.** `avg_support`, `avg_resistance`, `avg_workload`, `spread_support`, and therefore `implementation_readiness`, `alignment_index` and `consistency_index` (l. 1664–1678), are computed over **active agents' states** in that round. Spread is `max − min` over active agents only, per pre-reg §7.3 / §8.
- **`convergence_delta`.** Computed over agents **active in both round r−1 and round r** (Q4). A joiner's first round and a leaver's first absent round contribute nothing. Implement it by passing that filtered list to `_population_convergence_delta` (l. 324–347), whose docstring (l. 331–332) already anticipates mid-run roster changes. Keep `prev_agent_triples` (l. 1750–1757) for all agents. If no agent qualifies, `conv_delta = None`.
- **Early stop.** It is unchanged, but it now reads the filtered delta. Confirmatory runs keep `convergence_threshold` null (pre-reg §8).
- **State snapshots.** `insert_agent_state_snapshot` (l. 1701–1722) writes rows **only for active agents** in windowed runs. Inactive rounds have no row, and that gap is the inactive record. Do **not** add a DB column: export CSV headers are taken from row keys (`export_bundle.py` l. 110–113, 143–146), so a new column would change exports for every legacy run.

### 4.6 Absence notice (exact wording, for the ODD annex)

- **Who gets it.** In windowed runs, every active LLM speaker's user prompt gets a notice whenever at least one roster actor is inactive in that round and in scope.
- **Placement.** It comes after the `Policy event:` line, and after the handover block if present. Use a new optional `absence_notice: str | None = None` kwarg on `build_user_prompt`.
- **Format:**

  ```
  Not present this round: {entry}, {entry}, ….
  ```

  - Each `{entry}` is `{name}` alone, or `{name} ({absence_reason})` if `absence_reason` is non-empty.
  - Order follows roster order: slot order, which is the `agents` list order.
  - The line ends with exactly one period.
- **Scope** (`absence_notice_scope`, Q1):
  - `all_inactive` is the default: every roster actor inactive this round, including those not yet joined.
  - `departed_only`: only actors with `active_until_round < round_number`.
  - `none`: no notice.
- **Where it does not go.** It is not added to the Likert prompt, round summaries or the transcript body (the transcript gets its own membership line, §7.2).

### 4.7 After an actor leaves

- **Memory store.** The leaver's `agent_turns`, reflections and embeddings stay in SQLite untouched. Nothing is deleted, but none of it is read for that agent again, because it takes no turns.
- **Visibility to others.** Other agents can still see the leaver's earlier turns through the normal recency window and summaries.
- **Likert and snapshots.** Its Likert series and snapshot series end at `active_until_round`.
- **No rejoin.** Each actor has one contiguous window, and a second window is out of scope (§10).

---

## 5. Validation errors

| Check | Where | Result |
|---|---|---|
| `active_from_round` / `active_until_round` not an integer | `parse_roster_csv` (follow the existing `fidelity_tier` style, l. 135–143); `validate_scenario_document` (`scenarios/validate.py` l. 29–166); `_persona_from_mapping` | `ValueError` → HTTP 422. Message: `roster_csv: line {i}: invalid active_from_round {raw!r}` (same pattern for YAML: `personas[{i}].active_from_round must be an integer`) |
| Value < 1 | same | 422 `… must be >= 1` |
| `active_from_round > active_until_round` | same | 422 `… active_from_round > active_until_round` |
| `active_from_round > total_rounds` (never active) | `resolve_activity_windows`, run queue + preflight | 422 `activity window for {agent_id} starts after total_rounds={R}` |
| `active_until_round > total_rounds` | `resolve_activity_windows` | Clip to R. Add a run **warning** `activity window for {agent_id} clipped to total_rounds={R}` |
| Some round in `1..R` has **zero** active agents | `resolve_activity_windows` | 422 `round {r} has no active agents` |
| `handover_template` has an unknown or positional placeholder | `validate_scenario_document`, `_scenario_from_mapping` | error `roster_windows.handover_template: unknown placeholder {x}` |
| `absence_notice_scope` not in the allowed set | same | error |
| `absence_reason` set but the actor is never inactive in `1..R` | `resolve_activity_windows` | warning only |
| Windows set on synthetic remainder | n/a (remainder personas carry none) | not reachable |

Run warnings go into the existing `run_warnings` list (`api/simulations.py` l. 947–953).

---

## 6. Preflight cost adjustment

- **Headline numbers unchanged.** `estimated_cost_usd`, `llm_turns` and related fields stay **uncredited**: full included roster, every round. This follows pre-reg §13 (l. 584): "Join/leave reducing billed turns: **Not credited**", and l. 654. The spend guard (M5) will read the headline.
- **New optional parameter.** Add `active_counts_per_round: list[int] | None = None` to `estimate_run_preflight` (`preflight.py` l. 61–80).
- **New block, only when that parameter is given.** Add a separate `active_window_adjusted` block to the returned estimate:
  - `active_agents_per_round` (list);
  - `speaking_turns`, computed as Σ_r min(per_round_r, active_r);
  - `likert_llm_turns`, computed as Σ_r active_r when Likert is on;
  - `llm_turns`, `estimated_input_tokens`, `estimated_output_tokens` and `estimated_cost_usd`, all computed with the same per-call averages as l. 164–187.
- **Snapshot output.** The block appears in `PreflightEstimate.to_snapshot()` (l. 33–45) **only** when present. Use a new field `active_window_adjusted: dict | None = None` added last, and leave it out of the dict when None.
- **Preflight wiring bug the builder must fix.** `build_preflight_response` (`api/simulations.py` l. 641–720) builds personas **without** the roster merge (l. 676: `build_personas_for_agent_limit(scenario_cfg, core_limit, None)`) and passes `roster_by_slot` separately. Windows from the roster CSV would therefore be invisible to preflight unless the builder merges them, with `merge_persona_for_slot`, before resolving windows.
- Validation errors from §5 must surface from preflight too, as 422.

---

## 7. Transcript, config snapshot and export fields

All of these exist **only when `windowing_active`**.

### 7.1 `config_snapshot.roster_windows`

Merge this before round 1 via the existing `merge_simulation_config_snapshot`, or add it at the config_snapshot build (`api/simulations.py` l. 1119+).

```json
"roster_windows": {
  "schema_version": "v1",
  "windows": [{"agent_id": "...", "name": "...", "active_from_round": 1, "active_until_round": 10,
               "absence_reason": "", "window_basis": ""}],
  "absence_notice_scope": "all_inactive",
  "absence_notice_format": "Not present this round: {entries}.",
  "handover_template": "... or null",
  "handover_notes": {"<agent_id>": "<rendered text>"},
  "active_agents_per_round": [{"round_number": 1, "active_count": 7, "active_agent_ids": ["..."]}]
}
```

At run end, merge `"roster_window_audit": {"turns_outside_window": 0, "likert_rows_outside_window": 0, "spoke_by_round": {"1": ["agent_id", …], …}}`. This is computed from the DB, not from the plan, so that it is a real check. `turns_outside_window` must be 0. If it isn't, log an ERROR, but do not fail the run.

### 7.2 Transcript markdown (`simulation/transcript_writer.py`)

- **Header.** `open_transcript` (l. 26–55) is called at `orchestrator.py` l. 813–822 with `(name, role)` pairs. In windowed runs only, the roster table gains an `Active rounds` column (`| Name | Role | Active rounds |`, with values like `1–10`). Add this through a new optional kwarg. Without the kwarg, output is unchanged.
- **Per round.** `append_round_to_transcript` (l. 58–78) gains an optional `membership_line`. When given, it is written directly under the `## Round N — …` heading as `*Active: {names}. Not present: {names}.*`. The handover note is **not** written to the transcript. It lives in the prompt and in config_snapshot.
- **Prerequisite.** Transcripts are only written when `round_summary_enabled` (l. 813, 1724).

### 7.3 Export zip (`export_bundle.py`)

- **New member** `active_agents_per_round.csv`, written only when `bundle["active_agents_per_round"]` is non-empty. Columns:
  - `round_number, active_count, active_agent_ids, joined_agent_ids, left_agent_ids, inactive_agent_ids`;
  - IDs are `|`-joined;
  - `joined` means first active round = this round, and `left` means last active round = previous round.
- **Bundle assembly.** Both export routes (`api/simulations.py` l. 1461 / 1475) call `get_simulation_export_bundle` (`db/repo.py` l. 1480). Build `active_agents_per_round` there from `config_snapshot.roster_windows`, and add the key **only** when that block exists, so the legacy JSON export is unchanged.
- **Existing members.** `simulation_run.csv` already carries `config_snapshot`. Leave the other members unchanged. With snapshots now written only for active agents, `agent_state_snapshots.csv` has no rows for inactive rounds.

---

## 8. Determinism with seeds

- **Windows use no RNG.** They are deterministic config, so `resolve_activity_windows` and friends use no randomness.
- **`sample_k_per_round`.** It keeps the seed mix at l. 277 and draws from the active list. Given the same seed and windows, it makes the same picks. With no windows the active list is the full list, so the draws are identical to `main`.
- **No global RNG.** No new code may call the module-level `random.*` functions, which are seeded globally at l. 736. The tenure draw uses its own `random.Random` seeded from a SHA-256 of `draw_id|pool|v1`. The same `draw_id` gives the same windows on any machine and any Python 3.11/3.12.
- **Tier-3 heuristic.** It keeps `tier3_heuristic_rng(random_seed, round_number)` (l. 1620; `heuristic.py` l. 87–90). The noise draws are taken per ID in list order (`heuristic.py` l. 62–78), so removing an inactive Tier-3 ID would shift later draws. That can't happen in practice, because synthetic remainder agents are always active and documented core agents are Tier 1. With no windows, the ID list is unchanged.
- **LLM outputs** are not seeded (Anthropic has no seed, per pre-reg). Determinism claims cover planning, sampling, filtering and prompts, not model text.

---

## 9. Files in scope

**Change**

- `backend/src/senna_backend/scenarios/registry.py`: persona fields, `RosterWindowsConfig`, parse.
- `backend/src/senna_backend/scenarios/validate.py`: §5 checks.
- `backend/src/senna_backend/scenarios/serialize.py`: emit only when set.
- `backend/src/senna_backend/roster/csv_roster.py`: columns, parse, merge.
- `backend/src/senna_backend/roster/__init__.py`: exports, if needed.
- `backend/src/senna_backend/simulation/orchestrator.py`: §4.2–4.7 and §7.
- `backend/src/senna_backend/llm/prompt_templates.py`: `build_user_prompt` optional `handover_note` and `absence_notice`.
- `backend/src/senna_backend/simulation/memory_context.py`: `"pre_join"` reason; conditional breakdown key.
- `backend/src/senna_backend/simulation/transcript_writer.py`: optional kwargs.
- `backend/src/senna_backend/simulation/preflight.py`: `active_counts_per_round` and the `active_window_adjusted` block.
- `backend/src/senna_backend/api/simulations.py`:
  - resolve and validate windows in the queue path (l. 880–962) and preflight path (l. 641–720, including the roster merge fix);
  - config_snapshot;
  - `ROSTER_CSV_TEMPLATE` (l. 131–139): add the new columns **and** a `#` comment line per column;
  - export bundle wiring.
- `backend/src/senna_backend/api/capabilities.py`: describe the new roster columns (pattern at l. 67–70).
- `backend/src/senna_backend/export_bundle.py`: the new zip member.
- `backend/src/senna_backend/db/repo.py`: in `get_simulation_export_bundle` (l. 1480), add the `active_agents_per_round` key only when windowed. **No schema change.**

**Add**

- `backend/src/senna_backend/simulation/roster_windows.py` (§3.3)
- `backend/src/senna_backend/roster/tenure_draw.py` and `scripts/draw_tenure_windows.py` (§3.4; Q5)
- `docs/research/M_ROSTER_SPEC.md`: this spec. Add `!docs/research/M_ROSTER_SPEC.md` to the `.gitignore` allowlist (the existing pattern is at `.gitignore` l. 48–54).
- `docs/handoffs/HANDOFF_SENNA_M_ROSTER.md`: short pointer, same shape as `HANDOFF_SENNA_M_RENAME.md`.
- `docs/iterations/senna-m-roster-closeout.md`
- One **synthetic** demo scenario, at **`docs/examples/m_roster_windows_demo.yaml`** (not ignored; verified with `git check-ignore`). It has 4 to 5 invented personas ("Teacher A"…"Teacher E"), a 6-round horizon, one late joiner, one leaver with an `absence_reason`, a `handover_template`, and Likert anchors. No School S or Ahn names or text.
  - Do **not** put it in `scenarios/data/`. `_load_yaml_dir` (`registry.py` l. 277–287) auto-registers every YAML there as a built-in scenario, which would change `GET /scenarios` (`tests/test_scenario_catalog.py` l. 40) and the catalog.

**Update (docs)**

- `CLAUDE.md`: add an M-ROSTER entry to the "Research milestones" line (l. 33).
- `docs/SESSION_STATE.md`: a Current Status bullet.

**Do not change**

- `LICENSE`, `NOTICE`.
- `docs/research/PREREG_SSTRF_RQ1_V2.md`, `docs/diagnostics/ARC12_PLATFORM_FREEZE.json`, `docs/diagnostics/*_provenance.json`, `docs/diagnostics/ARC12_CONVERGENCE_CALIBRATION.md`.
- Any `*.sqlite`, transcript, export, or `data/` content.
- The frontend.
- Anything in `backend/tests/`.
- `population/csv_population.py`.

---

## 10. Out of scope

- More than one window per actor (leave and rejoin). One contiguous window only.
- Population-CSV windows.
- Per-actor free-text handover notes (Q3).
- Any LLM-generated handover or farewell.
- Absence notices in Likert prompts.
- Changing peer-window sizing (l. 1063–1080), round-summary depth, or the "last two rounds" knob semantics (see §11 C3; this belongs to M-baseline / M-state-audit).
- The single-author runner (M-baseline). It should reuse `roster_windows.py` later.
- Inclusion sampling (M2), the Likert Tier-3 skip (M4), remainder-marker hiding (M-hybrid-visibility), the spend guard (M5), the scoring harness (M6), and the freeze manifest (M8).
- Fixture work: the School S and Ahn rosters, windows tables, year-band maps, handover template text, and the actual frozen draw ID. These are fixture-freeze objects, signed separately.
- Frontend UI for windows.
- DB schema changes.
- Any live LLM call.

---

## 11. Conflicts and gaps: pre-reg vs code vs brief

- **C1. Handover note: brief vs pre-reg.** Mark's 13 Nov decision and this brief say "optionally with a handover note". The pre-reg v3.2 §7.3 (l. 291) and D35 (l. 972) tighten that to **one fixed template, limited to given-as-input facts**. This spec follows the pre-reg: a scenario-level template with a closed placeholder set, and no per-actor free text. See Q3.
- **C2. 7/5/4 draw scope.** The pre-reg puts the "frozen 7 / 5 / 4 draw" inside M-joinleave (l. 712). The parent brief did not mention it. This spec includes a small pure helper and leaves the actual draw to the fixture freeze. See Q5.
- **C3. Pre-existing mismatch, not fixed here.**
  - **What the pre-reg says.** §7 item 2 (l. 232) maps `working_memory_last_k = 2` to "the last two rounds".
  - **What the code does.**
    - `working_memory_last_k` sets the agent's **own** last-k turns (l. 1198–1203).
    - Peer context is the last `working_memory_last_k*2` = 4 turns for turn_index > 1. For the first speaker it is up to 12 turns (l. 1063–1080).
    - Round summaries are **uncapped**, covering all prior rounds (`repo.py` l. 2145, `round_number < ?`; orchestrator l. 1271–1277).
  - **Consequence.** The agents' window is not literally "the last two rounds". This matters for the "same frozen two-round capped window" promise to the single-author baseline (§10.2 / D28).
  - **Action.** Flag it for M-baseline / M-state-audit, and either amend the pre-reg wording or change the code there. Not in M-ROSTER.
- **C4. "Excluded from spread".** The pre-reg says inactive actors are excluded from "between-agent spread metrics". In code the only spread is `spread_support` → `alignment_index` (l. 1668–1671), plus the derived `consistency_index`. This spec restricts all global aggregates, including `implementation_readiness`, to active agents. That goes slightly beyond the pre-reg's wording, and it is needed so inactive frozen states don't drag the means.
- **C5. Likert for non-speakers.** Today Likert runs for **all** agents, including non-speakers in `sample_k_per_round` (l. 1637). The pre-reg's ODD process text (l. 1086) says "Likert at round end for active LLM agents". After this milestone, "active" means in-window, so non-speaking in-window agents still give Likert. That is consistent; it's flagged only so nobody reads "active" as "spoke".
- **C6. Naming.** The pre-reg's "Platform name as of `bb00410`" columns use the pre-rename package. `main` is now `senna_backend` @ `9739f09`. This is cosmetic.

---

## 12. Acceptance tests (for the independent tester)

The tester writes these on branch `m-roster-tests`, in new files under `backend/tests/`, without editing non-test files.

- **Mocking.** Mock the LLM by monkeypatching `senna_backend.simulation.orchestrator.llm_complete`, as `tests/test_interaction_sample_k.py` l. 55–56 and `tests/test_senna_iter51_reflection.py` l. 91 do. Have the fake echo a valid `<state>` block, and record `messages` per call along with `llm_request_context` (`call_site`, `round_number`, `agent_id`).
- **Data.** Use synthetic scenarios only, built with `scenario_from_mapping` or the demo YAML.

**A. Byte-identical default**

- **A1.** For an existing built-in scenario with no windows, the following are identical between `scenario` and the same scenario with every actor explicitly windowed `1..R`:
  - the sequence of `(round, turn_index, agent_id, interaction_type, target_agent_id)`;
  - every system/user prompt string;
  - global snapshot values;
  - Likert row count;
  - `config_snapshot` keys;
  - transcript text (minus timestamp lines);
  - zip member list.
- **A2.** With no windows, `build_user_prompt` output contains neither `Handover note` nor `Not present this round`, and equals the output from a call that omits the new kwargs.
- **A3.** The `exclusion_breakdown` keys are unchanged (no `pre_join`) when there are no windows.
- **A4.** The `roster-csv-template` endpoint still parses as a valid roster CSV, and an old-format roster CSV without the new columns still parses with windows = None.

**B. Turns and sampling**

- **B1.** An actor windowed `3..4` in a 6-round run has `agent_turns` rows only in rounds 3–4, and no LLM call outside them.
- **B2.** In `sample_k_per_round` (K=2, 5 agents, 2 inactive in a round), only active agents are picked. With a fixed seed, the picks are deterministic across two runs.
- **B3.** With `turn_order_policy=hierarchical`, the active speakers are in role_level order. No `reply` turn targets an inactive agent.
- **B4.** A round with zero active agents is rejected with 422 at queue and at preflight.

**C. Newcomer information rule**

- **C1.** In its join round J, the newcomer's user prompt:
  - contains no text from any turn in rounds < J (check unique sentinel strings planted in earlier turns via the fake LLM);
  - has "Working memory" `- (none)`;
  - has no `Prior rounds — compact summaries` block.
- **C2.** In round J+1, the newcomer sees round-J turns and the round-J summary, and still no pre-J summary or turn.
- **C3.** An agent active from round 1 in the same run still receives the pre-J summaries (the rule applies only to newcomers).
- **C4.** The newcomer's Likert prompt in round J contains no pre-J sentinel.
- **C5.** The memory-context log has `pre_join` exclusions for the newcomer, and the summary breakdown includes `pre_join`.
- **C6.** The weighted-retrieval path (with the embedding call mocked) also excludes pre-J peer turns.

**D. Handover note**

- **D1.** With a template set:
  - the newcomer's round-J prompt contains `Handover note (given to you on joining; only you can see this):` followed by the rendered text, with `{join_round}`, `{total_rounds}` and `{join_policy_event}` substituted;
  - it is absent from the newcomer's J+1 prompt (Q2 default);
  - it is absent from every other agent's prompts, from all round summaries, `agent_turns.raw_response`, the transcript body, and Likert prompts.
- **D2.** With no template, no handover block appears anywhere.
- **D3.** A template with an unknown placeholder fails validation, and one with `{{literal}}` passes.
- **D4.** `config_snapshot.roster_windows.handover_notes[agent_id]` equals the rendered text.

**E. Absence notices**

- **E1.** With `all_inactive`, an active agent's prompt in round r contains exactly `Not present this round: X (reason), Y.`, in roster order. Y has no reason and no parentheses.
- **E2.** With `departed_only`, not-yet-joined actors are omitted. With `none`, no notice appears.
- **E3.** No notice appears in a round where everyone is active.

**F. Likert, metrics, snapshots**

- **F1.** No `agent_round_likert` rows exist for inactive (agent, round) pairs. The Likert series of a leaver ends at `active_until_round`.
- **F2.** `alignment_index` in a round equals `1 − (max − min)` of support over **active** agents' post-round states only. Construct the states so that including an inactive agent would change it.
- **F3.** `convergence_delta` at round r averages only agents active in both r−1 and r. A joiner's first round contributes nothing. If nobody qualifies, the value is `None`.
- **F4.** `agent_state_snapshots` has no rows for inactive (agent, round) pairs in windowed runs.
- **F5.** A leaver's earlier turns are still in the DB after the run, and nothing is deleted.

**G. Validation**

- Each §5 error row gives the stated exception or 422, for both roster CSV and scenario YAML.
- An `until > R` window is clipped with a warning.

**H. Preflight**

- **H1.** With windows present, the headline `estimated_cost_usd` / `llm_turns` equal the no-windows values. `active_window_adjusted` exists and its `speaking_turns` equals Σ active per round (full_round_robin), with Likert turns = Σ active when Likert is on.
- **H2.** With no windows, the `to_snapshot()` dict has no `active_window_adjusted` key.
- **H3.** Windows supplied via roster CSV are seen by `POST /simulations/preflight`. This guards the l. 676 merge gap.

**I. Export and transcript**

- **I1.** The zip has `active_agents_per_round.csv` with the correct joined/left/inactive columns for the demo scenario. Without windows, the member is absent.
- **I2.** The transcript header has the `Active rounds` column, and each round has the membership line (windowed only).
- **I3.** `roster_window_audit.turns_outside_window == 0`.

**J. Tenure draw**

- **J1.** The same `draw_id` gives identical output across two calls. A different `draw_id` gives different output for a 16-slot {3:7, 2:5, 1:4} case. Output counts per tenure match exactly, and pinned slots keep their tenure.
- **J2.** Windows lie on band boundaries and are consecutive.
- **J3.** A count mismatch raises.
- **J4.** Calling it does not change `random.random()`'s next value after `random.seed(1)`.

**K. Regression**

- The full suite reports the main baseline (564 passed / 15 failed / 2 skipped, same 15 nodeids) plus the new tests. Any new failure is reported as a spec failure, and the tester must not fix product code.

---

## 13. Open questions for Mark (each has a recommended default)

1. **Absence notice for not-yet-joined actors.** Should School S agents hear "Not present this round: Zaiton, Malik." in cycle 1, even though Malik has not joined yet? **Default: yes (`all_inactive`).** It matches pre-reg wording ("Zaiton is absent in cycle 1"), and Malik is a school colleague. Switch to `departed_only` per fixture if this reads as a leak.
2. **How long the handover note lasts.** **Default: the join round only.** From round J+1 the newcomer has its own memory and colleagues' briefings. The alternative is to keep it for `working_memory_last_k` rounds.
3. **Per-actor free-text handover.** **Default: not built.** One fixed scenario template only, per pre-reg §7.3 / D35. Your 13 Nov wording ("optionally with a handover note") is met by the template being optional.
4. **Convergence across a membership change.** **Default: average only agents active in both r−1 and r.** The alternative counts a joiner's first round as Δ vs initial state, which would inject artificial jumps.
5. **Tenure draw (7/5/4) in this PR.** **Default: yes, as the small pure helper + CLI in §3.4, with no fixture.** The pre-reg lists it under M-joinleave. The real `draw_id` and year bands are set at fixture freeze.

## DECISIONS LOCKED (Mark, 16 Nov 2026), superseding the "open questions" above
- Q1: the absence notice names BOTH actors who have departed AND actors who have not joined yet (absence_notice_scope = all_inactive).
- Q2: the handover note appears in the newcomer's prompt in their join round ONLY.
- Q3: no per-actor free-text note; one fixed scenario-level handover_template only (pre-reg §7.3).
- Q4: convergence in round r counts only agents active in both r−1 and r.
- Q5: INCLUDE the seeded 7/5/4 tenure-draw helper plus script in this PR (the draw id and year bands are set at fixture freeze, not here).
