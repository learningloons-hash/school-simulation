"""senna-iter-48 — Arc 10 combined diagnostics baseline."""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from membench_adapter import run_membench_suite  # noqa: E402
from run_arc10_diagnostics import run_arc10_diagnostics  # noqa: E402

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_export_bundle,
    insert_architectural_interview_response,
    insert_architectural_interview_score,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.diagnostics import architectural_interview as ai_mod
from mirofish_backend.diagnostics.arc10_baseline import (
    evaluate_arc11_hypothesis,
    generate_baseline_markdown,
)
from mirofish_backend.diagnostics.arc10_canonical import (
    load_canonical_bundle,
    summary_from_canonical_bundle,
)
from mirofish_backend.diagnostics.architectural_interview import (
    INTERVIEW_CATEGORIES,
    run_architectural_interview_for_simulation,
)
from mirofish_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block, memory_context_run_kwargs  # noqa: E402

FIXTURES_DIR = _REPO / "backend/tests/fixtures/membench"


def _judge_block(score: int) -> str:
    return f'<judge_score>{{"score": {score}, "rationale": "test"}}</judge_score>'


async def _seed_completed_sim_with_memory(db_path: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", fake_llm_state_block)
    sim_id = await create_simulation_run(
        db_path,
        name="arc10 baseline",
        scenario_id="psle_reform_mvp",
        status="pending",
        total_rounds=2,
        random_seed=48,
        prompt_version="v0",
        model_used="lmstudio:local",
    )
    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        random_seed=48,
        **memory_context_run_kwargs(),
    )
    return sim_id


async def _fake_llm_interview(**kwargs) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    if "rubric judge" in system.lower():
        user = str((messages[1] or {}).get("content") or "")
        if "reflection" in user.lower():
            return LLMCompletion(text=_judge_block(0), input_tokens=2, output_tokens=2)
        if "memory_retrieval" in user.lower():
            return LLMCompletion(text=_judge_block(2), input_tokens=2, output_tokens=2)
        return LLMCompletion(text=_judge_block(1), input_tokens=2, output_tokens=2)
    return LLMCompletion(text="Grounded simulation answer with round 1 detail.", input_tokens=4, output_tokens=4)


async def _get_bundle(sqlite_path: str, simulation_id: str):
    return await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)


@pytest.fixture
def patched_interview(monkeypatch):
    monkeypatch.setattr(ai_mod, "_llm_complete", _fake_llm_interview)


@pytest.mark.asyncio
async def test_combined_runner_json(monkeypatch: pytest.MonkeyPatch, patched_interview) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "arc10.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim_with_memory(db_path, monkeypatch)
        await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
        )
        summary = await run_arc10_diagnostics(
            sqlite_path=db_path,
            simulation_id=sim_id,
            fixtures_dir=FIXTURES_DIR,
            membench_seed=42,
            membench_answer_mode="memory_match",
            execute_interview=False,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            force_interview=False,
            interview_temperature=0.0,
            interview_max_tokens=256,
        )
        assert summary["simulation_id"] == sim_id
        assert summary["memory_context"]
        assert summary["membench"]["participation"]["factual"]["metric"] == "memory_accuracy"
        assert summary["architectural_interview"]["response_count"] >= len(INTERVIEW_CATEGORIES)
        verdict, _ = evaluate_arc11_hypothesis(summary)
        assert verdict in ("supported", "not_supported", "mixed")


@pytest.mark.asyncio
async def test_baseline_markdown_generation(monkeypatch: pytest.MonkeyPatch, patched_interview) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "arc10_md.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim_with_memory(db_path, monkeypatch)
        await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
        )
        summary = await run_arc10_diagnostics(
            sqlite_path=db_path,
            simulation_id=sim_id,
            fixtures_dir=FIXTURES_DIR,
            membench_seed=42,
            membench_answer_mode="memory_match",
            execute_interview=False,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            force_interview=False,
            interview_temperature=0.0,
            interview_max_tokens=256,
        )
        md = generate_baseline_markdown(summary)
        assert "# Arc 10 diagnostics baseline" in md
        assert "**Verdict:**" in md
        assert re.search(r"\*\*(supported|not supported|mixed)\*\*", md, re.IGNORECASE)
        assert "Phase V" not in md or "not Phase V" in md.lower() or "not Phase V trial" in md


def test_membench_fixture_path_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail(*_args, **_kwargs):
        raise AssertionError("network fetch attempted")

    monkeypatch.setattr("urllib.request.urlopen", _fail)
    run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=42)


def test_baseline_body_stable_except_timestamp() -> None:
    sample = {
        "simulation_id": "abc123",
        "generated_at": "2026-01-01T00:00:00+00:00",
        "memory_context": {
            "group_addressed_proportion": 0.5,
            "exclusion_breakdown": {"recency_cut": 1},
        },
        "membench": run_membench_suite(fixtures_dir=FIXTURES_DIR, seed=42),
        "architectural_interview": {
            "response_count": 5,
            "score_count": 5,
            "scores": [
                {"category": "memory_retrieval", "score": 2},
                {"category": "reflection", "score": 0},
                {"category": "planning", "score": 1},
            ],
        },
    }
    md_a = generate_baseline_markdown(sample)
    sample["generated_at"] = "2026-02-02T00:00:00+00:00"
    md_b = generate_baseline_markdown(sample)
    body_a = md_a.split("**Generated at:**", 1)[1].split("\n", 1)[1]
    body_b = md_b.split("**Generated at:**", 1)[1].split("\n", 1)[1]
    assert body_a == body_b


def test_regenerate_baseline_from_canonical_bundle() -> None:
    bundle = load_canonical_bundle()
    summary = summary_from_canonical_bundle(bundle)
    md = generate_baseline_markdown(summary)
    committed_path = _REPO / "docs/diagnostics/ARC10_BASELINE.md"
    committed = committed_path.read_text(encoding="utf-8")
    body_md = md.split("**Generated at:**", 1)[1].split("\n", 1)[1]
    body_committed = committed.split("**Generated at:**", 1)[1].split("\n", 1)[1]
    assert body_md == body_committed
