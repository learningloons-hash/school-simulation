#!/usr/bin/env python3
"""Post-run Park et al. architectural diagnostic interview (Senna iter-47)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))

from mirofish_backend.config import get_settings
from mirofish_backend.db.repo import (
    get_simulation_export_bundle,
    insert_architectural_interview_response,
    insert_architectural_interview_score,
)
from mirofish_backend.db.schema import init_db as schema_init
from mirofish_backend.diagnostics.architectural_interview import (
    INTERVIEW_CATEGORIES,
    run_architectural_interview_for_simulation,
)
from mirofish_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID


async def _get_bundle(sqlite_path: str, simulation_id: str):
    return await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)


async def _run(args: argparse.Namespace) -> dict:
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    await schema_init(sqlite_path)

    if not args.execute:
        bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=args.simulation_id)
        if bundle is None:
            raise SystemExit(f"simulation not found: {args.simulation_id}")
        from mirofish_backend.diagnostics.architectural_interview import agents_from_snapshots

        agents = agents_from_snapshots(bundle.get("agent_state_snapshots") or [])
        return {
            "dry_run": True,
            "simulation_id": args.simulation_id,
            "agent_count": len(agents),
            "categories": list(INTERVIEW_CATEGORIES),
            "planned_calls_per_agent": len(INTERVIEW_CATEGORIES) * 2,
            "interview_profile_id": args.interview_profile_id,
            "judge_profile_id": args.judge_profile_id,
        }

    return await run_architectural_interview_for_simulation(
        sqlite_path=sqlite_path,
        simulation_id=args.simulation_id,
        interview_profile_id=args.interview_profile_id,
        judge_profile_id=args.judge_profile_id,
        insert_response=insert_architectural_interview_response,
        insert_score=insert_architectural_interview_score,
        get_export_bundle=_get_bundle,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        settings=settings,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Administer architectural diagnostic interview on a completed simulation",
    )
    parser.add_argument("simulation_id", help="Completed simulation UUID")
    parser.add_argument(
        "--sqlite-path",
        default="",
        help="SQLite path (defaults to server SQLITE_PATH / settings)",
    )
    parser.add_argument(
        "--interview-profile-id",
        default=LOCAL_LMSTUDIO_DEFAULT_ID,
        help="Built-in profile for interview questions",
    )
    parser.add_argument(
        "--judge-profile-id",
        default=LOCAL_LMSTUDIO_DEFAULT_ID,
        help="Built-in profile for rubric judge scoring",
    )
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run live LLM interview + judge (default is dry-run plan only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = asyncio.run(_run(args))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
