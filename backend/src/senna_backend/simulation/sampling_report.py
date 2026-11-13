"""Reshape ``config_snapshot.sampling_audit`` for researchers (Iteration 26)."""

from __future__ import annotations

from typing import Any


def build_sampling_report_json(config_snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """
    Derive a readable report from persisted ``sampling_audit`` (no new DB tables).

    When ``per_agent`` rows include ``degree_centrality``, ``centrality`` is a map
    ``agent_id -> score``; otherwise ``null``.
    """
    if not config_snapshot:
        raise ValueError("config_snapshot is empty")
    audit = config_snapshot.get("sampling_audit")
    if not isinstance(audit, dict):
        raise ValueError("config_snapshot has no sampling_audit")

    per_agent_raw = audit.get("per_agent") or []
    if not isinstance(per_agent_raw, list):
        per_agent_raw = []

    tier_summary: dict[str, int] = {}
    raw_counts = audit.get("tier_counts") or {}
    if isinstance(raw_counts, dict):
        for k, v in raw_counts.items():
            tier_summary[str(int(k))] = int(v) if v is not None else 0

    by_role: dict[str, dict[str, int]] = {}
    by_posture: dict[str, dict[str, int]] = {}

    per_agent_out: list[dict[str, Any]] = []
    for row in per_agent_raw:
        if not isinstance(row, dict):
            continue
        entry = dict(row)
        role = str(entry.get("role") or "").strip() or "(unknown)"
        posture = str(entry.get("implementation_posture") or "").strip()
        posture_key = posture if posture else "(untagged)"
        tier = entry.get("tier")
        try:
            tk = str(int(tier)) if tier is not None else "?"
        except (TypeError, ValueError):
            tk = str(tier) if tier is not None else "?"

        by_role.setdefault(role, {"tier_1": 0, "tier_2": 0, "tier_3": 0, "total": 0})
        by_posture.setdefault(posture_key, {"tier_1": 0, "tier_2": 0, "tier_3": 0, "total": 0})
        if tk in ("1", "2", "3"):
            by_role[role][f"tier_{tk}"] = by_role[role].get(f"tier_{tk}", 0) + 1
            by_role[role]["total"] = by_role[role].get("total", 0) + 1
            by_posture[posture_key][f"tier_{tk}"] = by_posture[posture_key].get(f"tier_{tk}", 0) + 1
            by_posture[posture_key]["total"] = by_posture[posture_key].get("total", 0) + 1

        per_agent_out.append(entry)

    centrality_map: dict[str, Any] | None = None
    for row in per_agent_out:
        if "degree_centrality" in row and row.get("agent_id") is not None:
            if centrality_map is None:
                centrality_map = {}
            centrality_map[str(row["agent_id"])] = row.get("degree_centrality")

    return {
        "sampling_strategy": audit.get("sampling_strategy"),
        "tier_summary": tier_summary,
        "by_role": dict(sorted(by_role.items(), key=lambda x: x[0])),
        "by_posture": dict(sorted(by_posture.items(), key=lambda x: x[0])),
        "centrality": centrality_map,
        "scenario_roles_ordered": audit.get("scenario_roles_ordered"),
        "scenario_roles_not_represented": audit.get("scenario_roles_not_represented"),
        "per_agent": per_agent_out,
    }
