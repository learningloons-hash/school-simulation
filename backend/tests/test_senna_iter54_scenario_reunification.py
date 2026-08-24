"""senna-iter-54 Part A — fixture reunification (synthetic CI path)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import seed_scenario_from_study_repo as seeder  # noqa: E402

from mirofish_backend.db.repo import get_user_scenario_row, user_scenario_exists  # noqa: E402
from mirofish_backend.db.schema import init_db  # noqa: E402
from mirofish_backend.rag.corpus import load_scenario_corpus_texts  # noqa: E402
from mirofish_backend.scenarios.loader import load_scenario_for_run  # noqa: E402

FIXTURE_YAML = _REPO / "backend/tests/fixtures/dummy_external_scenario.yaml"
FIXTURE_CORPUS = _REPO / "backend/tests/fixtures/dummy_external_scenario_corpus"
SCENARIO_ID = "dummy_external_scenario"


def _init_git_repo(path: Path) -> None:
    subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)


def _commit_all(path: Path, message: str = "init") -> None:
    subprocess.run(["git", "-C", str(path), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", message], check=True, capture_output=True)


def _allowed_paths_for(data_dir: Path) -> list[str]:
    if not data_dir.is_dir():
        return []
    out: list[str] = []
    for p in sorted(data_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in (".txt", ".md"):
            rel = p.relative_to(data_dir).as_posix()
            if ".." not in rel and not rel.startswith("/"):
                out.append(rel)
    return out


@pytest.fixture
def fake_study_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "fake_study"
    repo.mkdir()
    yaml_dir = repo / "scenarios/data"
    yaml_dir.mkdir(parents=True)
    shutil.copy(FIXTURE_YAML, yaml_dir / "dummy.yaml")
    corpus_src = yaml_dir / "corpus"
    corpus_src.mkdir()
    shutil.copy(FIXTURE_CORPUS / "brief.txt", corpus_src / "brief.txt")
    _init_git_repo(repo)
    _commit_all(repo)
    return repo


@pytest.fixture
def reunification_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    scenarios_data = tmp_path / "scenarios_data"
    scenarios_data.mkdir()
    manifest_path = tmp_path / "provenance.json"
    db_path = tmp_path / "test.sqlite"

    monkeypatch.setattr(
        "mirofish_backend.rag.corpus._SCENARIOS_DATA",
        scenarios_data,
    )
    monkeypatch.setattr(
        "mirofish_backend.scenarios.validate.list_allowed_corpus_paths",
        lambda: _allowed_paths_for(scenarios_data),
    )
    monkeypatch.setattr(
        seeder,
        "list_allowed_corpus_paths",
        lambda: _allowed_paths_for(scenarios_data),
    )
    return {
        "sqlite_path": str(db_path),
        "scenarios_data_dir": scenarios_data,
        "manifest_path": manifest_path,
    }


@pytest.mark.asyncio
async def test_seed_reunification_happy_path(
    fake_study_repo: Path,
    reunification_paths: dict,
) -> None:
    summary = await seeder.seed_scenario_from_study_repo(
        study_repo_path=fake_study_repo,
        yaml_rel_path="scenarios/data/dummy.yaml",
        scenario_id=SCENARIO_ID,
        sqlite_path=reunification_paths["sqlite_path"],
        corpus_rel_dir="scenarios/data/corpus",
        force=True,
        scenarios_data_dir=reunification_paths["scenarios_data_dir"],
        manifest_path=reunification_paths["manifest_path"],
    )

    assert await user_scenario_exists(reunification_paths["sqlite_path"], scenario_id=SCENARIO_ID)

    cfg, src = await load_scenario_for_run(reunification_paths["sqlite_path"], SCENARIO_ID)
    assert src == "user"
    assert cfg.scenario_id == SCENARIO_ID
    assert len(cfg.personas) == 3
    assert cfg.personas[0].persona_id == "agent_alpha"

    corpus_dest = reunification_paths["scenarios_data_dir"] / SCENARIO_ID / "brief.txt"
    assert corpus_dest.is_file()
    rel_path = f"{SCENARIO_ID}/brief.txt"
    assert rel_path in seeder.list_allowed_corpus_paths()
    loaded = load_scenario_corpus_texts(rel_paths=(rel_path,))
    assert len(loaded) == 1
    assert "Synthetic briefing" in loaded[0][1]

    row = await get_user_scenario_row(reunification_paths["sqlite_path"], scenario_id=SCENARIO_ID)
    assert row is not None
    assert row["source_repo"]
    assert row["source_commit"]
    assert row["seeded_at"] is not None

    manifest = json.loads(reunification_paths["manifest_path"].read_text(encoding="utf-8"))
    assert manifest["scenario_id"] == SCENARIO_ID
    assert manifest["source_commit"] == summary["source_commit"]
    assert manifest["dirty"] is False
    assert manifest["corpus_rel_dir"] == "scenarios/data/corpus"

    # Idempotent re-run
    summary2 = await seeder.seed_scenario_from_study_repo(
        study_repo_path=fake_study_repo,
        yaml_rel_path="scenarios/data/dummy.yaml",
        scenario_id=SCENARIO_ID,
        sqlite_path=reunification_paths["sqlite_path"],
        corpus_rel_dir="scenarios/data/corpus",
        force=True,
        scenarios_data_dir=reunification_paths["scenarios_data_dir"],
        manifest_path=reunification_paths["manifest_path"],
    )
    assert summary2["source_commit"] == summary["source_commit"]
    assert await user_scenario_exists(reunification_paths["sqlite_path"], scenario_id=SCENARIO_ID)


@pytest.mark.asyncio
async def test_dirty_working_tree_aborts_by_default(fake_study_repo: Path, reunification_paths: dict) -> None:
    dirty_file = fake_study_repo / "dirty_marker.txt"
    dirty_file.write_text("uncommitted", encoding="utf-8")

    with pytest.raises(seeder.SeedScenarioError, match="dirty"):
        await seeder.seed_scenario_from_study_repo(
            study_repo_path=fake_study_repo,
            yaml_rel_path="scenarios/data/dummy.yaml",
            scenario_id=SCENARIO_ID,
            sqlite_path=reunification_paths["sqlite_path"],
            corpus_rel_dir="scenarios/data/corpus",
            allow_dirty=False,
            force=True,
            scenarios_data_dir=reunification_paths["scenarios_data_dir"],
            manifest_path=reunification_paths["manifest_path"],
        )


@pytest.mark.asyncio
async def test_allow_dirty_records_manifest_flag(
    fake_study_repo: Path,
    reunification_paths: dict,
) -> None:
    dirty_file = fake_study_repo / "dirty_marker.txt"
    dirty_file.write_text("uncommitted", encoding="utf-8")

    await seeder.seed_scenario_from_study_repo(
        study_repo_path=fake_study_repo,
        yaml_rel_path="scenarios/data/dummy.yaml",
        scenario_id=SCENARIO_ID,
        sqlite_path=reunification_paths["sqlite_path"],
        corpus_rel_dir="scenarios/data/corpus",
        allow_dirty=True,
        force=True,
        scenarios_data_dir=reunification_paths["scenarios_data_dir"],
        manifest_path=reunification_paths["manifest_path"],
    )

    manifest = json.loads(reunification_paths["manifest_path"].read_text(encoding="utf-8"))
    assert manifest["dirty"] is True


def test_git_clean_check_helpers(fake_study_repo: Path) -> None:
    assert seeder.assert_clean_working_tree(fake_study_repo, allow_dirty=False) is False
    (fake_study_repo / "touch.txt").write_text("x", encoding="utf-8")
    with pytest.raises(seeder.SeedScenarioError, match="dirty"):
        seeder.assert_clean_working_tree(fake_study_repo, allow_dirty=False)
    assert seeder.assert_clean_working_tree(fake_study_repo, allow_dirty=True) is True


@pytest.mark.asyncio
async def test_ui_upsert_does_not_wipe_provenance(tmp_path: Path) -> None:
    from mirofish_backend.db.repo import upsert_user_scenario

    db = str(tmp_path / "prov.sqlite")
    await init_db(db)
    doc = json.dumps({"scenario_id": "x", "name": "X"})
    await upsert_user_scenario(
        db,
        scenario_id="x",
        display_name="X",
        document_json=doc,
        source_repo="https://example.com/study.git",
        source_commit="abc123",
    )
    await upsert_user_scenario(
        db,
        scenario_id="x",
        display_name="X updated",
        document_json=doc,
    )
    row = await get_user_scenario_row(db, scenario_id="x")
    assert row is not None
    assert row["source_repo"] == "https://example.com/study.git"
    assert row["source_commit"] == "abc123"
    assert row["seeded_at"] is not None
