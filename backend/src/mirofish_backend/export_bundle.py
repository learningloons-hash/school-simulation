"""Build analyst-ready export artifacts (ZIP of CSVs) from an export bundle dict.

``export.json`` ``export_version`` changelog (additive; see ADR-001):

- **1** — Base bundle (run, transcript with ``raw_prompt``, flat tables, derived timeline).
- **2** — ``validity_notes`` (+ ZIP ``validity_notes.csv``).
- **3** — Per-turn ``effective_provider`` / ``effective_model`` on transcript rows.
- **4** — Agent snapshot ``attribute_sections`` (Iteration 13; CSV cells JSON-encoded).
- **5** — ``cohort_summary`` (Iteration 20; ZIP ``cohort_summary.csv``).
- **6** — Transcript rows include ``fidelity_tier`` (Iteration 23; agent_turns CSV + JSON bundle).
- **7** — ``global_state_snapshots`` include optional ``convergence_delta`` (Iteration 28); run row ``converged_at_round``.
- **8** — Per-turn ``input_tokens`` / ``output_tokens``; run ``total_*_tokens``; ``run.economics`` (Iteration 29).
- **9** — ``likert_responses`` + ZIP ``agent_round_likert.csv`` (senna-iter-40).
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from typing import Any

# Single source of truth for GET /simulations/{id}/export.json and GET /capabilities.
EXPORT_VERSION = "9"


def compute_cohort_summary(snapshots: list[dict]) -> list[dict]:
    """Aggregate agent_state_snapshots by (group_id, round_number).

    Returns a list of group entries, each with a ``rounds`` sub-list containing
    per-round averages for support_level, resistance_level, and workload_stress.
    Agents with no group_ids (empty list or missing) are aggregated under group_id "".
    """
    from collections import defaultdict

    # bucket: (group_id, round_number) → list of snapshot dicts
    buckets: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for snap in snapshots:
        raw = snap.get("group_ids") or []
        if isinstance(raw, str):
            try:
                import json as _json
                raw = _json.loads(raw)
            except Exception:
                raw = []
        groups: list[str] = raw if raw else [""]
        rnd = snap.get("round_number", 0)
        for gid in groups:
            buckets[(gid, rnd)].append(snap)

    def _avg(items: list[dict], key: str) -> float | None:
        vals = [v for s in items if (v := s.get(key)) is not None]
        return round(sum(vals) / len(vals), 6) if vals else None

    # group by group_id
    group_rounds: dict[str, dict[int, list[dict]]] = defaultdict(dict)
    for (gid, rnd), snaps_list in buckets.items():
        group_rounds[gid][rnd] = snaps_list

    result: list[dict] = []
    for gid in sorted(group_rounds.keys()):
        rounds_data = group_rounds[gid]
        rounds_out = []
        for rnd in sorted(rounds_data.keys()):
            snaps_list = rounds_data[rnd]
            rounds_out.append(
                {
                    "round_number": rnd,
                    "agent_count": len(snaps_list),
                    "spoke_count": sum(1 for s in snaps_list if s.get("spoke_this_round")),
                    "avg_support_level": _avg(snaps_list, "support_level"),
                    "avg_resistance_level": _avg(snaps_list, "resistance_level"),
                    "avg_workload_stress": _avg(snaps_list, "workload_stress"),
                }
            )
        result.append({"group_id": gid, "rounds": rounds_out})
    return result


def _csv_cell(v: Any) -> Any:
    if isinstance(v, dict):
        return json.dumps(v, sort_keys=True)
    return v


def _csv_bytes(headers: list[str], rows: list[list[Any]]) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def build_export_zip(bundle: dict[str, Any]) -> bytes:
    """
    Produce a ZIP containing CSV tables for Excel-friendly workflows.
    Expected keys: run, transcript, agent_state_snapshots, global_state_snapshots, round_outcomes.
    """
    run = bundle["run"]
    run_headers = list(run.keys())
    run_rows = [[run.get(h) for h in run_headers]]

    transcript = bundle.get("transcript") or []
    if transcript:
        t_headers = list(transcript[0].keys())
        t_rows = [[t.get(h) for h in t_headers] for t in transcript]
    else:
        t_headers = [
            "id",
            "simulation_id",
            "round_number",
            "turn_index",
            "agent_id",
            "agent_role",
            "agent_name",
            "interaction_type",
            "target_scope",
            "target_agent_id",
            "target_agent_name",
            "intent_tag",
            "raw_prompt",
            "raw_response",
            "latency_ms",
            "group_ids",
            "effective_provider",
            "effective_model",
            "fidelity_tier",
            "created_at",
            "input_tokens",
            "output_tokens",
        ]
        t_rows = []

    snaps = bundle.get("agent_state_snapshots") or []
    if snaps:
        s_headers = list(snaps[0].keys())
        s_rows = [[_csv_cell(x.get(h)) for h in s_headers] for x in snaps]
    else:
        s_headers = [
            "id",
            "simulation_id",
            "round_number",
            "agent_id",
            "agent_role",
            "agent_name",
            "age",
            "sex",
            "ethnicity",
            "ses",
            "support_level",
            "resistance_level",
            "workload_stress",
            "belief_posture",
            "group_ids",
            "spoke_this_round",
            "attribute_sections",
            "created_at",
        ]
        s_rows = []

    globals_ = bundle.get("global_state_snapshots") or []
    if globals_:
        g_headers = list(globals_[0].keys())
        g_rows = [[x.get(h) for h in g_headers] for x in globals_]
    else:
        g_headers = [
            "id",
            "simulation_id",
            "round_number",
            "implementation_readiness",
            "alignment_index",
            "convergence_delta",
            "created_at",
        ]
        g_rows = []

    outcomes = bundle.get("round_outcomes") or []
    if outcomes:
        o_headers = list(outcomes[0].keys())
        o_rows = [[x.get(h) for h in o_headers] for x in outcomes]
    else:
        o_headers = ["id", "simulation_id", "round_number", "adoption_momentum", "conflict_events", "consistency_index", "created_at"]
        o_rows = []

    validity = bundle.get("validity_notes") or []
    if validity:
        v_headers = list(validity[0].keys())
        v_rows = [[x.get(h) for h in v_headers] for x in validity]
    else:
        v_headers = [
            "id",
            "simulation_id",
            "round_number",
            "rater_id",
            "face_score",
            "face_rubric",
            "construct_score",
            "construct_rubric",
            "predictive_score",
            "predictive_rubric",
            "notes",
            "created_at",
        ]
        v_rows = []

    cohort = compute_cohort_summary(snaps)
    cohort_headers = ["group_id", "round_number", "agent_count", "spoke_count",
                      "avg_support_level", "avg_resistance_level", "avg_workload_stress"]
    cohort_rows = [
        [r["group_id"], rd["round_number"], rd["agent_count"], rd["spoke_count"],
         rd["avg_support_level"], rd["avg_resistance_level"], rd["avg_workload_stress"]]
        for r in cohort
        for rd in r["rounds"]
    ]

    likert = bundle.get("likert_responses") or []
    if likert:
        lk_headers = list(likert[0].keys())
        lk_rows = [[x.get(h) for h in lk_headers] for x in likert]
    else:
        lk_headers = [
            "round_number",
            "agent_id",
            "indicator",
            "anchor_label",
            "ordinal_value",
            "mapped_float",
            "source",
            "float_value",
            "divergence",
            "created_at",
        ]
        lk_rows = []

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("simulation_run.csv", _csv_bytes(run_headers, run_rows))
        zf.writestr("agent_turns.csv", _csv_bytes(t_headers, t_rows))
        zf.writestr("agent_state_snapshots.csv", _csv_bytes(s_headers, s_rows))
        zf.writestr("global_state_snapshots.csv", _csv_bytes(g_headers, g_rows))
        zf.writestr("round_outcomes.csv", _csv_bytes(o_headers, o_rows))
        zf.writestr("validity_notes.csv", _csv_bytes(v_headers, v_rows))
        zf.writestr("cohort_summary.csv", _csv_bytes(cohort_headers, cohort_rows))
        if likert:
            zf.writestr("agent_round_likert.csv", _csv_bytes(lk_headers, lk_rows))
    return bio.getvalue()


def experiment_comparison_csv_bytes(flat_rows: list[dict[str, Any]]) -> bytes:
    """Long-form comparison rows for ZIP ``comparison.csv`` (Iteration 27+; economics cols Iteration 29)."""
    headers = [
        "run_label",
        "round",
        "implementation_readiness",
        "alignment_index",
        "adoption_momentum",
        "conflict_events",
        "consistency_index",
        "convergence_delta",
        "input_tokens",
        "output_tokens",
        "estimated_cost_usd",
    ]
    data_rows: list[list[Any]] = []
    for r in flat_rows:
        data_rows.append(
            [
                r.get("run_label"),
                r.get("round"),
                r.get("implementation_readiness"),
                r.get("alignment_index"),
                r.get("adoption_momentum"),
                r.get("conflict_events"),
                r.get("consistency_index"),
                r.get("convergence_delta"),
                r.get("input_tokens"),
                r.get("output_tokens"),
                r.get("estimated_cost_usd"),
            ]
        )
    return _csv_bytes(headers, data_rows)
