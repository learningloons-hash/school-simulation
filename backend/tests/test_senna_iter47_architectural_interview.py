"""senna-iter-47 — Park et al. architectural diagnostic interview."""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from typing import Any

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import (
    count_architectural_interview_responses,
    create_simulation_run,
    delete_architectural_interview_for_simulation,
    get_simulation_export_bundle,
    insert_agent_state_snapshot,
    insert_agent_turn,
    insert_architectural_interview_response,
    insert_architectural_interview_score,
    set_simulation_status,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.diagnostics import architectural_interview as ai_mod
from mirofish_backend.diagnostics.architectural_interview import (
    INTERVIEW_CATEGORIES,
    build_judge_prompts,
    load_rubric_category_excerpt,
    run_architectural_interview_for_simulation,
    score_interview_response,
)
from mirofish_backend.diagnostics.judge_score_parse import resolve_judge_score
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip
from mirofish_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app


async def _seed_completed_sim(db_path: str) -> str:
    sim_id = await create_simulation_run(
        db_path,
        name="arch interview",
        scenario_id="psle_reform_mvp",
        status="running",
        total_rounds=1,
        random_seed=47,
        prompt_version="v0",
        model_used="lmstudio:local",
    )
    await insert_agent_turn(
        db_path,
        simulation_id=sim_id,
        round_number=1,
        turn_index=0,
        agent_id="agent_a",
        agent_role="teacher",
        agent_name="Alex",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_id=None,
        target_agent_name=None,
        intent_tag="statement",
        raw_prompt="prompt",
        raw_response="In round 1 I argued for phased reform and listened to peer pushback.",
    )
    await insert_agent_turn(
        db_path,
        simulation_id=sim_id,
        round_number=1,
        turn_index=1,
        agent_id="peer_b",
        agent_role="parent",
        agent_name="Blake",
        interaction_type="direct",
        target_scope="agent",
        target_agent_id="agent_a",
        target_agent_name="Alex",
        intent_tag="challenge",
        raw_prompt="prompt",
        raw_response="I disagreed with Alex about timeline and asked for evidence.",
    )
    await insert_agent_state_snapshot(
        db_path,
        simulation_id=sim_id,
        round_number=1,
        agent_id="agent_a",
        agent_role="teacher",
        agent_name="Alex",
        age=35,
        sex="F",
        ethnicity="",
        ses="",
        support_level=0.6,
        resistance_level=0.3,
        workload_stress=0.4,
        belief_posture="cautious_support",
    )
    await set_simulation_status(
        db_path,
        simulation_id=sim_id,
        status="completed",
        current_round=1,
    )
    return sim_id


async def _seed_two_agent_sim(db_path: str) -> str:
    sim_id = await _seed_completed_sim(db_path)
    await insert_agent_state_snapshot(
        db_path,
        simulation_id=sim_id,
        round_number=1,
        agent_id="peer_b",
        agent_role="parent",
        agent_name="Blake",
        age=40,
        sex="M",
        ethnicity="",
        ses="",
        support_level=0.4,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="skeptical",
    )
    return sim_id


def _judge_block(score: int, rationale: str = "test") -> str:
    return f'<judge_score>{{"score": {score}, "rationale": "{rationale}"}}</judge_score>'


_CALL_LOG: list[dict[str, Any]] = []


async def _fake_llm(**kwargs) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    user = str((messages[1] or {}).get("content") or "") if len(messages) > 1 else ""
    _CALL_LOG.append({"system": system, "user": user, "kwargs": kwargs})

    if "rubric judge" in system.lower():
        if "CLEAR_PASS_MARKER" in user:
            return LLMCompletion(text=_judge_block(2, "clear pass"), input_tokens=3, output_tokens=3)
        if "CLEAR_FAIL_MARKER" in user:
            return LLMCompletion(text=_judge_block(0, "clear fail"), input_tokens=3, output_tokens=3)
        if "MALFORMED" in user:
            return LLMCompletion(text='{"score": 1, "rationale": "no block"}', input_tokens=3, output_tokens=3)
        return LLMCompletion(text=_judge_block(1, "default judge"), input_tokens=3, output_tokens=3)

    return LLMCompletion(
        text=(
            "As Alex the teacher, in round 1 I planned my message for staff, reacted to Blake's "
            "disagreement, and reflected that I would cite evidence earlier next time."
        ),
        input_tokens=5,
        output_tokens=5,
    )


@pytest.fixture(autouse=True)
def _reset_call_log():
    _CALL_LOG.clear()
    yield
    _CALL_LOG.clear()


@pytest.fixture
def patched_llm(monkeypatch):
    monkeypatch.setattr(ai_mod, "_llm_complete", _fake_llm)


async def _get_bundle(sqlite_path: str, simulation_id: str):
    return await get_simulation_export_bundle(sqlite_path, simulation_id=simulation_id)


@pytest.mark.asyncio
async def test_judge_prompts_load_rubric_md(patched_llm) -> None:
    excerpt = load_rubric_category_excerpt("memory_retrieval")
    assert "specific recall" in excerpt.lower() or "specific moment" in excerpt.lower()
    system, user = build_judge_prompts(
        category="memory_retrieval",
        question_text="Recall a moment.",
        response_text="Round 1 Blake disagreed.",
    )
    assert excerpt in user
    assert "rubric judge" in system.lower()


@pytest.mark.asyncio
async def test_two_agents_ten_responses_and_scores(patched_llm) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "iter47_multi.sqlite")
        await init_db(db_path)
        sim_id = await _seed_two_agent_sim(db_path)
        report = await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
            count_existing_responses=count_architectural_interview_responses,
            delete_existing=delete_architectural_interview_for_simulation,
        )
        assert report["response_count"] == 10
        assert report["score_count"] == 10
        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        assert len(bundle["architectural_interview_responses"]) == 10
        assert len(bundle["architectural_interview_scores"]) == 10


@pytest.mark.asyncio
async def test_rerun_without_force_returns_error_not_crash(patched_llm) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "iter47_rerun.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim(db_path)
        kwargs = dict(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
            count_existing_responses=count_architectural_interview_responses,
            delete_existing=delete_architectural_interview_for_simulation,
        )
        await run_architectural_interview_for_simulation(**kwargs)
        with pytest.raises(ValueError, match="already exists"):
            await run_architectural_interview_for_simulation(**kwargs)
        await run_architectural_interview_for_simulation(**kwargs, force=True)
        assert await count_architectural_interview_responses(db_path, simulation_id=sim_id) == 5


@pytest.mark.asyncio
async def test_all_five_categories_produce_response_and_score(patched_llm) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "iter47.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim(db_path)

        report = await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
        )
        assert report["response_count"] == len(INTERVIEW_CATEGORIES)
        assert report["score_count"] == len(INTERVIEW_CATEGORIES)

        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        responses = bundle["architectural_interview_responses"]
        scores = bundle["architectural_interview_scores"]
        assert len(responses) == 5
        assert len(scores) == 5
        assert {r["category"] for r in responses} == set(INTERVIEW_CATEGORIES)
        assert all(s["parse_source"] in ("model_parsed", "repaired", "keyword_fallback") for s in scores)


def test_calibration_clear_pass_and_fail() -> None:
    pass_raw = _judge_block(2, "Grounded role and goals with round reference.")
    fail_raw = _judge_block(0, "Generic filler unrelated to transcript.")
    pass_score, pass_src, _ = resolve_judge_score(pass_raw)
    fail_score, fail_src, _ = resolve_judge_score(fail_raw)
    assert pass_score == 2 and pass_src == "model_parsed"
    assert fail_score == 0 and fail_src == "model_parsed"


def test_malformed_judge_output_uses_fallback_not_crash() -> None:
    score, src, _ = resolve_judge_score('{"score": 1}')
    assert score == 1
    assert src == "keyword_fallback"

    score2, src2, _ = resolve_judge_score("totally unparseable output")
    assert score2 is None
    assert src2 == "unparseable"


@pytest.mark.asyncio
async def test_judge_scoring_two_profiles(patched_llm) -> None:
    question = "Recall a specific moment."
    response = "CLEAR_PASS_MARKER example from round 1."

    result_a = await score_interview_response(
        category="memory_retrieval",
        question_text=question,
        response_text=response,
        judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        temperature=0.0,
        max_tokens=256,
    )
    result_b = await score_interview_response(
        category="memory_retrieval",
        question_text=question,
        response_text=response,
        judge_profile_id=ANTHROPIC_DEFAULT_ID,
        temperature=0.0,
        max_tokens=256,
    )
    profile_a = result_a[7]
    profile_b = result_b[7]
    score_b = result_b[0]
    src_b = result_b[4]
    assert profile_a == LOCAL_LMSTUDIO_DEFAULT_ID
    assert profile_b == ANTHROPIC_DEFAULT_ID
    assert score_b == 2
    assert src_b == "model_parsed"


@pytest.mark.asyncio
async def test_export_bundle_includes_architectural_sections_and_version_12(patched_llm) -> None:
    assert EXPORT_VERSION == "14"
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "export47.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim(db_path)
        await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
        )
        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        assert "architectural_interview_responses" in bundle
        assert "architectural_interview_scores" in bundle
        assert "likert_responses" in bundle
        zip_bytes = build_export_zip(bundle)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "architectural_interview_responses.csv" in names
            assert "architectural_interview_scores.csv" in names


@pytest.mark.asyncio
async def test_separation_from_likert_tables(patched_llm) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "sep47.sqlite")
        await init_db(db_path)
        sim_id = await _seed_completed_sim(db_path)
        await run_architectural_interview_for_simulation(
            sqlite_path=db_path,
            simulation_id=sim_id,
            interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
            insert_response=insert_architectural_interview_response,
            insert_score=insert_architectural_interview_score,
            get_export_bundle=_get_bundle,
        )
        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        assert bundle["likert_responses"] == []
        assert bundle["architectural_interview_responses"]
        assert "indicator" not in (bundle["architectural_interview_scores"][0].keys())


@pytest.fixture
def client_arch(monkeypatch, tmp_path):
    db = tmp_path / "iter47_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs):
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


@pytest.mark.asyncio
async def test_architectural_interview_report_endpoint(client_arch: TestClient, patched_llm) -> None:
    db_path = os.environ["SQLITE_PATH"]
    await init_db(db_path)
    sim_id = await _seed_completed_sim(db_path)
    await run_architectural_interview_for_simulation(
        sqlite_path=db_path,
        simulation_id=sim_id,
        interview_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        judge_profile_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        insert_response=insert_architectural_interview_response,
        insert_score=insert_architectural_interview_score,
        get_export_bundle=_get_bundle,
    )
    r = client_arch.get(f"/simulations/{sim_id}/architectural-interview-report")
    assert r.status_code == 200
    body = r.json()
    assert body["instrument"] == "architectural_interview"
    assert body["response_count"] == 5
    assert "validity" in body["purpose"]


def test_validate_interview_partial_grid_raises() -> None:
    from mirofish_backend.diagnostics.architectural_interview import (
        INTERVIEW_CATEGORIES,
        validate_interview_completeness,
    )

    responses = [
        {"id": f"resp_a_{i}", "agent_id": "agent_a", "category": cat}
        for i, cat in enumerate(INTERVIEW_CATEGORIES)
    ]
    responses.extend(
        [
            {"id": "resp_b_0", "agent_id": "agent_b", "category": "self_knowledge"},
            {"id": "resp_b_1", "agent_id": "agent_b", "category": "memory_retrieval"},
            {"id": "resp_b_2", "agent_id": "agent_b", "category": "planning"},
            {"id": "resp_b_3", "agent_id": "agent_b", "category": "planning"},
            {"id": "resp_b_4", "agent_id": "agent_b", "category": "reaction"},
        ]
    )
    scores = [
        {"response_id": r["id"], "parse_source": "model_parsed", "score": 1}
        for r in responses
    ]
    with pytest.raises(ValueError, match="agent_b"):
        validate_interview_completeness(
            responses,
            scores,
            expected_agent_ids=["agent_a", "agent_b"],
        )


def test_validate_interview_wrong_agent_count_from_snapshots_raises() -> None:
    from mirofish_backend.diagnostics.architectural_interview import (
        INTERVIEW_CATEGORIES,
        validate_interview_completeness,
    )

    responses = [
        {"id": f"resp_{i}", "agent_id": "agent_a", "category": cat}
        for i, cat in enumerate(INTERVIEW_CATEGORIES)
    ]
    scores = [
        {"response_id": r["id"], "parse_source": "model_parsed", "score": 1}
        for r in responses
    ]
    with pytest.raises(ValueError, match="expected 10"):
        validate_interview_completeness(
            responses,
            scores,
            expected_agent_ids=["agent_a", "agent_b"],
        )
