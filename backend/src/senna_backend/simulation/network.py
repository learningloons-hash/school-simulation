"""Optional influence network CSV — Iteration 25 (degree centrality + visibility)."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NetworkParseResult:
    """Parsed edges between simulation ``agent_id`` strings (``persona_id_NNN`` format)."""

    edges: tuple[tuple[str, str, float], ...]
    """(source_agent_id, target_agent_id, influence_weight) with weight in (0, 1]."""

    warnings: tuple[str, ...] = ()
    """Unknown endpoints and similar — analyst-visible, non-fatal."""

    skipped_row_count: int = 0


def parse_network_csv(text: str, *, known_agent_ids: frozenset[str]) -> NetworkParseResult:
    """
    CSV header: ``source_agent_id,target_agent_id,influence_weight`` (weight float 0.0–1.0).

    Rows referencing an endpoint not in ``known_agent_ids`` are skipped and warned.
    Self-loops and non-positive weights are skipped (no warning for self-loop).

    Duplicate ``(source, target)`` pairs are all kept: :func:`degree_centrality` sums every
    incident weight; :func:`undirected_neighbor_map` treats endpoints as neighbors once.
    """
    warnings: list[str] = []
    edges_list: list[tuple[str, str, float]] = []
    skipped = 0
    if not (text or "").strip():
        return NetworkParseResult(edges=(), warnings=(), skipped_row_count=0)

    reader = csv.DictReader(io.StringIO(text.strip()))
    if not reader.fieldnames:
        warnings.append("network_csv: no header row")
        return NetworkParseResult(edges=(), warnings=tuple(warnings), skipped_row_count=0)

    fn = [h.strip().lower() if h else "" for h in reader.fieldnames]
    required = ("source_agent_id", "target_agent_id", "influence_weight")
    if not all(x in fn for x in required):
        raise ValueError(
            "network_csv: header must include source_agent_id, target_agent_id, influence_weight"
        )

    for i, row in enumerate(reader, start=2):
        lr = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        s = lr.get("source_agent_id", "")
        t = lr.get("target_agent_id", "")
        wraw = lr.get("influence_weight", "")
        if not s and not t and not wraw:
            continue
        if not s or not t:
            warnings.append(f"network_csv: line {i}: missing source or target; row skipped")
            skipped += 1
            continue
        try:
            w = float(wraw)
        except ValueError:
            warnings.append(f"network_csv: line {i}: invalid influence_weight {wraw!r}; row skipped")
            skipped += 1
            continue
        if not (0.0 <= w <= 1.0):
            warnings.append(
                f"network_csv: line {i}: influence_weight {w} out of [0,1]; row skipped"
            )
            skipped += 1
            continue
        if w <= 0.0:
            skipped += 1
            continue
        if s == t:
            skipped += 1
            continue
        unk: list[str] = []
        if s not in known_agent_ids:
            unk.append(s)
        if t not in known_agent_ids:
            unk.append(t)
        if unk:
            warnings.append(
                f"network_csv: line {i}: unknown agent_id(s) {unk!r} (not in this run); row skipped"
            )
            skipped += 1
            continue
        edges_list.append((s, t, w))

    return NetworkParseResult(
        edges=tuple(edges_list),
        warnings=tuple(warnings),
        skipped_row_count=skipped,
    )


def degree_centrality(agent_ids: list[str], edges: tuple[tuple[str, str, float], ...]) -> dict[str, float]:
    """
    Sum of ``influence_weight`` on incident edges (each undirected edge contributes to both endpoints).
    Agents with no incident edges get ``0.0``.
    """
    out: dict[str, float] = {a: 0.0 for a in agent_ids}
    for s, t, w in edges:
        if s in out:
            out[s] += w
        if t in out:
            out[t] += w
    return out


def undirected_neighbor_map(
    agent_ids: frozenset[str],
    edges: tuple[tuple[str, str, float], ...],
) -> dict[str, frozenset[str]]:
    """Adjacency for visibility: neighbors share a strictly positive-weight edge."""
    adj: dict[str, set[str]] = {a: set() for a in agent_ids}
    for s, t, w in edges:
        if w <= 0:
            continue
        if s in adj and t in adj:
            adj[s].add(t)
            adj[t].add(s)
    return {k: frozenset(v) for k, v in adj.items()}
