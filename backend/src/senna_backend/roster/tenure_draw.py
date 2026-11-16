"""Frozen tenure draw for activity windows (M-ROSTER). Uses a local RNG only."""

from __future__ import annotations

import hashlib
import random
from collections import Counter


def draw_tenure_windows(
    *,
    slot_ids: list[str],
    tenure_counts: dict[int, int],
    year_bands: list[tuple[int, int]],
    draw_id: str,
    pinned: dict[str, int] | None = None,
    pool: str = "teachers",
) -> dict[str, tuple[int, int]]:
    """
    Assign consecutive round windows from year_bands for each slot.
    Returns slot_id -> (active_from_round, active_until_round).
    """
    slots = sorted(slot_ids)
    if sum(tenure_counts.values()) != len(slots):
        raise ValueError(
            f"tenure_counts sum {sum(tenure_counts.values())} != slot count {len(slots)}",
        )
    pinned = pinned or {}
    for sid, L in pinned.items():
        if sid not in slots:
            raise ValueError(f"pinned slot {sid!r} not in slot_ids")
        if tenure_counts.get(L, 0) < 1:
            raise ValueError(f"pinned tenure {L} for {sid!r} not in tenure_counts")

    digest = hashlib.sha256(f"{draw_id}|{pool}|v1".encode()).digest()
    rng = random.Random(int.from_bytes(digest[:8], "big"))

    remaining_counts = Counter(tenure_counts)
    assignments: dict[str, int] = {}
    for sid in slots:
        if sid in pinned:
            L = pinned[sid]
            assignments[sid] = L
            remaining_counts[L] -= 1
            if remaining_counts[L] < 0:
                raise ValueError(f"pinned slots exceed tenure count for {L}-year tenure")

    unpinned = [s for s in slots if s not in pinned]
    rng.shuffle(unpinned)
    tenure_multiset: list[int] = []
    for L in sorted(remaining_counts.keys(), reverse=True):
        tenure_multiset.extend([L] * remaining_counts[L])
    if len(tenure_multiset) != len(unpinned):
        raise ValueError("tenure multiset length mismatch after pinned allocation")
    for sid, L in zip(unpinned, tenure_multiset, strict=True):
        assignments[sid] = L

    num_bands = len(year_bands)
    out: dict[str, tuple[int, int]] = {}
    for sid in slots:
        L = assignments[sid]
        if L > num_bands:
            raise ValueError(f"tenure {L} for slot {sid!r} exceeds {num_bands} year bands")
        valid_starts = [i for i in range(num_bands - L + 1)]
        start_idx = rng.choice(valid_starts)
        from_r = year_bands[start_idx][0]
        until_r = year_bands[start_idx + L - 1][1]
        out[sid] = (from_r, until_r)
    return out