#!/usr/bin/env python3
"""CLI: draw tenure-based activity windows CSV for roster import (M-ROSTER)."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))

from senna_backend.roster.tenure_draw import draw_tenure_windows  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Draw frozen tenure windows for roster CSV columns.")
    p.add_argument("--slots-file", required=True, help="Text file with one slot id per line")
    p.add_argument("--draw-id", required=True, help="Frozen draw identifier")
    p.add_argument("--pool", default="teachers")
    p.add_argument("--tenure-3", type=int, default=0, dest="tenure_3")
    p.add_argument("--tenure-2", type=int, default=0, dest="tenure_2")
    p.add_argument("--tenure-1", type=int, default=0, dest="tenure_1")
    p.add_argument(
        "--year-bands",
        default="1-8,9-14,15-20",
        help="Comma-separated inclusive bands, e.g. 1-8,9-14,15-20",
    )
    p.add_argument("-o", "--output", default="-", help="Output CSV path or - for stdout")
    args = p.parse_args()

    slots = [ln.strip() for ln in Path(args.slots_file).read_text(encoding="utf-8").splitlines() if ln.strip()]
    bands: list[tuple[int, int]] = []
    for part in args.year_bands.split(","):
        lo_s, hi_s = part.strip().split("-", 1)
        bands.append((int(lo_s), int(hi_s)))

    counts = {3: args.tenure_3, 2: args.tenure_2, 1: args.tenure_1}
    counts = {k: v for k, v in counts.items() if v > 0}
    windows = draw_tenure_windows(
        slot_ids=slots,
        tenure_counts=counts,
        year_bands=bands,
        draw_id=args.draw_id,
        pool=args.pool,
    )
    basis = f'frozen tenure draw {args.draw_id} (algorithm v1)'
    rows = [
        ("slot", "active_from_round", "active_until_round", "window_basis"),
    ] + [
        (sid, str(w[0]), str(w[1]), basis) for sid in sorted(windows.keys()) for w in [windows[sid]]
    ]

    if args.output == "-":
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerows(rows)
    else:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())