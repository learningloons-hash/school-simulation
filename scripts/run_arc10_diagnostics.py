#!/usr/bin/env python3
"""Run all Arc 10 diagnostics and generate baseline markdown (senna-iter-48)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))
sys.path.insert(0, str(_REPO_ROOT / "scripts"))

from membench_adapter import run_membench_suite
from mirofish_backend.config import get_settings
from mirofish_backend.db.repo import (
    count_architectural_interview_responses,
    delete_architectural_interview_for_simulation,
    get_simulation_export_bundle,
    insert_architectural_interview_response,
    insert_architectural_interview_score,
)
from mirofish_backend.db.schema import init_db as schema_init
from mirofish_backend.diagnostics.arc10_baseline import (
    build_combined_arc10_summary,
    generate_baseline_markdown,
)
from mirofish_backend.diagnostics.architectural_interview import (
    run_architectural_interview_for_simulation,
    summarize_interview_results,
)
from mirofish_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID

_DEFAULT_FIXTURES = _REPO_ROOT / "backend/tests/fixtures/membench"
_DEFAULT_BASELINE_MD = _REPO_ROOT / "docs/diagnostics/ARC10_BASELINE.md"


async def _get_bundle(sqlite_path: str, simulation_id: str):
    return await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)


def _interview_section_from_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    responses = bundle.get("architectural_interview_responses") or []
    scores = bundle.get("architectural_interview_scores") or []
    summary = summarize_interview_results(responses, scores)
    return {
        **summary,
        "responses": responses,
        "scores": scores,
    }


async def run_arc10_diagnostics(
    *,
    sqlite_path: str,
    simulation_id: str,
    fixtures_dir: Path,
    membench_seed: int,
    membench_answer_mode: str,
    execute_interview: bool,
    interview_profile_id: str,
    judge_profile_id: str,
    force_interview: bool,
    interview_temperature: float,
    interview_max_tokens: int,
) -> dict[str, Any]:
    await schema_init(sqlite_path)
    bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)
    if bundle is None:
        raise ValueError(f"simulation {simulation_id!r} not found")

    run = bundle.get("run") or {}
    status = str(run.get("status") or "")
    if status in ("pending", "running"):
        raise ValueError("simulation must be completed or failed before Arc 10 diagnostics")

    memory_context_summary = bundle.get("memory_context_summary") or {}
    membench = run_membench_suite(
        fixtures_dir=fixtures_dir,
        seed=membench_seed,
        answer_mode=membench_answer_mode,
    )

    existing = await count_architectural_interview_responses(sqlite_path, simulation_id=simulation_id)
    if execute_interview:
        await run_architectural_interview_for_simulation(
            sqlite_path=sqlite_path,
            simulation_id=simulation_id,
            interview_profile_id=interview_profile_id,
            judge_profile_id=judge_profile_id,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
            count_existing_responses=count_architectural_interview_responses,
            delete_existing=delete_architectural_interview_for_simulation,
            force=force_interview,
            temperature=interview_temperature,
            max_tokens=interview_max_tokens,
            settings=get_settings(),
        )
        bundle = await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)
        if bundle is None:
            raise ValueError(f"simulation {simulation_id!r} not found after interview")
    elif existing == 0:
        raise ValueError(
            "no architectural interview rows for simulation; pass --execute-interview or run "
            "scripts/run_architectural_interview.py first"
        )

    interview_section = _interview_section_from_bundle(bundle or {})

    return build_combined_arc10_summary(
        simulation_id=simulation_id,
        memory_context_summary=memory_context_summary,
        membench=membench,
        architectural_interview=interview_section,
        inputs={
            "membench_seed": membench_seed,
            "membench_answer_mode": membench_answer_mode,
            "execute_interview": execute_interview,
            "force_interview": force_interview,
            "fixtures_dir": str(fixtures_dir),
        },
    )


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    summary = await run_arc10_diagnostics(
        sqlite_path=sqlite_path,
        simulation_id=args.simulation_id,
        fixtures_dir=args.fixtures_dir.resolve(),
        membench_seed=args.membench_seed,
        membench_answer_mode=args.membench_answer_mode,
        execute_interview=args.execute_interview,
        interview_profile_id=args.interview_profile_id,
        judge_profile_id=args.judge_profile_id,
        force_interview=args.force_interview,
        interview_temperature=args.interview_temperature,
        interview_max_tokens=args.interview_max_tokens,
    )

    if args.write_baseline:
        md = generate_baseline_markdown(summary)
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(md, encoding="utf-8")
        summary = {**summary, "baseline_markdown_path": str(args.write_baseline)}

    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Arc 10 combined diagnostics baseline")
    parser.add_argument("simulation_id", help="Completed simulation UUID")
    parser.add_argument("--sqlite-path", default="", help="SQLite path (defaults to settings)")
    parser.add_argument("--fixtures-dir", type=Path, default=_DEFAULT_FIXTURES)
    parser.add_argument("--membench-seed", type=int, default=42)
    parser.add_argument(
        "--membench-answer-mode",
        choices=("memory_match", "ground_truth"),
        default="memory_match",
    )
    parser.add_argument(
        "--execute-interview",
        action="store_true",
        help="Run live architectural interview + judge (requires LLM)",
    )
    parser.add_argument(
        "--force-interview",
        action="store_true",
        help="Replace existing architectural interview rows when executing interview",
    )
    parser.add_argument(
        "--interview-profile-id",
        default=LOCAL_LMSTUDIO_DEFAULT_ID,
    )
    parser.add_argument(
        "--judge-profile-id",
        default=LOCAL_LMSTUDIO_DEFAULT_ID,
    )
    parser.add_argument("--interview-temperature", type=float, default=0.2)
    parser.add_argument("--interview-max-tokens", type=int, default=1024)
    parser.add_argument(
        "--write-baseline",
        type=Path,
        nargs="?",
        const=_DEFAULT_BASELINE_MD,
        help="Write docs/diagnostics/ARC10_BASELINE.md (optional path)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = asyncio.run(_run(args))
    except ValueError as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
