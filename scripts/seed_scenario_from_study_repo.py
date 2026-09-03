#!/usr/bin/env python3
"""Seed user_scenarios from an external study-repo checkout (senna-iter-54 Part A)."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "backend" / "src"))

from mirofish_backend.config import get_settings  # noqa: E402
from mirofish_backend.db.repo import upsert_user_scenario, user_scenario_exists  # noqa: E402
from mirofish_backend.db.schema import init_db  # noqa: E402
from mirofish_backend.scenarios.validate import (  # noqa: E402
    list_allowed_corpus_paths,
    validate_scenario_document,
)


class SeedScenarioError(Exception):
    """Non-zero exit for validation or git guard failures."""


def default_scenarios_data_dir() -> Path:
    return _REPO_ROOT / "backend/src/mirofish_backend/scenarios/data"


def default_manifest_path(*, scenario_id: str) -> Path:
    return _REPO_ROOT / "docs/diagnostics" / f"{scenario_id}_provenance.json"


def resolve_git_toplevel(study_repo_path: Path) -> Path:
    study_repo_path = study_repo_path.resolve()
    try:
        out = subprocess.run(
            ["git", "-C", str(study_repo_path), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise SeedScenarioError(
            f"--study-repo-path is not a git repository: {study_repo_path}",
        ) from exc
    return Path(out.stdout.strip())


def git_porcelain(study_repo_path: Path) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(study_repo_path), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def assert_clean_working_tree(study_repo_path: Path, *, allow_dirty: bool) -> bool:
    dirty_lines = git_porcelain(study_repo_path)
    if not dirty_lines:
        return False
    if allow_dirty:
        print(
            "WARNING: study repo working tree is dirty; provenance commit may not match seeded content.",
            file=sys.stderr,
        )
        for ln in dirty_lines:
            print(f"  {ln}", file=sys.stderr)
        return True
    raise SeedScenarioError(
        "Study repo working tree is dirty; commit or stash changes before seeding, "
        "or pass --allow-dirty for local iteration only.",
    )


def get_source_provenance(study_repo_path: Path) -> tuple[str, str]:
    commit = subprocess.run(
        ["git", "-C", str(study_repo_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "-C", str(study_repo_path), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    if remote.returncode == 0 and remote.stdout.strip():
        return remote.stdout.strip(), commit
    print(
        f"WARNING: no git remote 'origin' in {study_repo_path}; recording path as source_repo.",
        file=sys.stderr,
    )
    return str(study_repo_path.resolve()), commit


def copy_corpus_files(
    *,
    study_repo_path: Path,
    corpus_rel_dir: str,
    scenario_id: str,
    scenarios_data_dir: Path,
) -> int:
    src_root = (study_repo_path / corpus_rel_dir).resolve()
    if not src_root.is_dir():
        raise SeedScenarioError(f"corpus directory not found: {src_root}")
    dest_root = scenarios_data_dir / scenario_id
    if dest_root.exists():
        shutil.rmtree(dest_root)
    dest_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for src in sorted(src_root.rglob("*")):
        if not src.is_file():
            continue
        rel = src.relative_to(src_root)
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1
    return copied


def build_manifest_payload(
    *,
    scenario_id: str,
    source_repo: str,
    source_commit: str,
    yaml_rel_path: str,
    corpus_rel_dir: str | None,
    dirty: bool,
    seeded_at: str | None = None,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario_id,
        "source_repo": source_repo,
        "source_commit": source_commit,
        "yaml_rel_path": yaml_rel_path,
        "corpus_rel_dir": corpus_rel_dir,
        "seeded_at": seeded_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
        "dirty": dirty,
    }


def write_manifest(manifest_path: Path, payload: dict[str, Any]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def format_rerun_command(
    *,
    study_repo_path: Path,
    yaml_rel_path: str,
    scenario_id: str,
    corpus_rel_dir: str | None,
    sqlite_path: str,
) -> str:
    parts = [
        "python3 scripts/seed_scenario_from_study_repo.py",
        f"  --study-repo-path {study_repo_path}",
        f"  --yaml-rel-path {yaml_rel_path}",
        f"  --scenario-id {scenario_id}",
        f"  --sqlite-path {sqlite_path}",
    ]
    if corpus_rel_dir:
        parts.append(f"  --corpus-rel-dir {corpus_rel_dir}")
    return " \\\n".join(parts)


async def seed_scenario_from_study_repo(
    *,
    study_repo_path: Path,
    yaml_rel_path: str,
    scenario_id: str = "ciepss_school_b",
    sqlite_path: str,
    corpus_rel_dir: str | None = None,
    allow_dirty: bool = False,
    force: bool = False,
    scenarios_data_dir: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    repo_root = resolve_git_toplevel(study_repo_path)
    dirty = assert_clean_working_tree(repo_root, allow_dirty=allow_dirty)
    source_repo, source_commit = get_source_provenance(repo_root)

    yaml_path = repo_root / yaml_rel_path
    if not yaml_path.is_file():
        raise SeedScenarioError(f"scenario YAML not found: {yaml_path}")

    doc = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict):
        raise SeedScenarioError(f"scenario YAML must be a mapping: {yaml_path}")

    doc = dict(doc)
    doc["scenario_id"] = scenario_id

    data_dir = scenarios_data_dir or default_scenarios_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    await init_db(sqlite_path)

    corpus_count = 0
    if corpus_rel_dir:
        corpus_count = copy_corpus_files(
            study_repo_path=repo_root,
            corpus_rel_dir=corpus_rel_dir,
            scenario_id=scenario_id,
            scenarios_data_dir=data_dir,
        )

    allowed = frozenset(list_allowed_corpus_paths())
    is_update = await user_scenario_exists(sqlite_path, scenario_id=scenario_id)
    if is_update and not force and sys.stdin.isatty():
        answer = input(
            f"Scenario {scenario_id!r} already exists in {sqlite_path}; overwrite? [y/N] ",
        ).strip()
        if answer.lower() not in ("y", "yes"):
            raise SeedScenarioError("Aborted: scenario already exists (pass --force to skip prompt).")

    errs, warns = validate_scenario_document(doc, is_update=is_update, allowed_corpus_paths=allowed)
    for w in warns:
        print(f"warning: {w}", file=sys.stderr)
    if errs:
        raise SeedScenarioError("validation failed:\n  " + "\n  ".join(errs))

    display_name = str(doc.get("name") or scenario_id)
    await upsert_user_scenario(
        sqlite_path,
        scenario_id=scenario_id,
        display_name=display_name,
        document_json=json.dumps(doc, sort_keys=True),
        source_repo=source_repo,
        source_commit=source_commit,
    )

    manifest_out = manifest_path or default_manifest_path(scenario_id=scenario_id)
    payload = build_manifest_payload(
        scenario_id=scenario_id,
        source_repo=source_repo,
        source_commit=source_commit,
        yaml_rel_path=yaml_rel_path,
        corpus_rel_dir=corpus_rel_dir,
        dirty=dirty,
    )
    write_manifest(manifest_out, payload)

    return {
        "scenario_id": scenario_id,
        "sqlite_path": sqlite_path,
        "source_repo": source_repo,
        "source_commit": source_commit,
        "corpus_files_copied": corpus_count,
        "manifest_path": str(manifest_out),
        "manifest": payload,
        "rerun_command": format_rerun_command(
            study_repo_path=repo_root,
            yaml_rel_path=yaml_rel_path,
            scenario_id=scenario_id,
            corpus_rel_dir=corpus_rel_dir,
            sqlite_path=sqlite_path,
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Seed a user_scenarios row from a study-repo checkout.")
    p.add_argument("--study-repo-path", required=True, help="Local path to senna-sstrf-study checkout")
    p.add_argument("--yaml-rel-path", required=True, help="Scenario YAML path relative to study repo root")
    p.add_argument("--scenario-id", required=True, help="Scenario id to register (required — no default, so a forgotten flag fails loudly instead of silently reusing another scenario's id)")
    p.add_argument("--corpus-rel-dir", default="", help="Corpus directory relative to study repo (when rag_enabled)")
    p.add_argument("--sqlite-path", default="", help="SQLite path (default: settings)")
    p.add_argument("--force", action="store_true", help="Skip overwrite confirmation when scenario exists")
    p.add_argument("--allow-dirty", action="store_true", help="Allow dirty study repo (manifest records dirty: true)")
    return p


async def _async_main(args: argparse.Namespace) -> int:
    settings = get_settings()
    sqlite_path = args.sqlite_path or settings.sqlite_path
    corpus_rel_dir = args.corpus_rel_dir.strip() or None
    try:
        summary = await seed_scenario_from_study_repo(
            study_repo_path=Path(args.study_repo_path),
            yaml_rel_path=args.yaml_rel_path,
            scenario_id=args.scenario_id,
            sqlite_path=sqlite_path,
            corpus_rel_dir=corpus_rel_dir,
            allow_dirty=args.allow_dirty,
            force=args.force,
        )
    except SeedScenarioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"Seeded scenario {summary['scenario_id']!r} into {summary['sqlite_path']}")
    print(f"  source_commit: {summary['source_commit']}")
    print(f"  corpus files copied: {summary['corpus_files_copied']}")
    print(f"  manifest: {summary['manifest_path']}")
    print("Re-run later with:")
    print(summary["rerun_command"])
    return 0


def main() -> None:
    args = _build_parser().parse_args()
    raise SystemExit(asyncio.run(_async_main(args)))


if __name__ == "__main__":
    main()
