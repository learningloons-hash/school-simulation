"""senna-iter-45 — memory context inclusion instrumentation."""

from __future__ import annotations

import json
import os
import tempfile
import uuid

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_group_addressed_turn_summary,
    get_simulation_export_bundle,
    insert_agent_turn,
)
from mirofish_backend.db.schema import init_db as schema_init
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip
from mirofish_backend.llm.context_clip import prepare_peer_response_for_prompt_with_meta
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app
from mirofish_backend.simulation.interaction_policy import (
    build_interaction_policy,
    partition_turns_by_visibility,
)
from mirofish_backend.simulation.memory_context import build_memory_context_inclusion_records


def _fake_observer():
    from types import SimpleNamespace

    return SimpleNamespace(
        agent_id="observer_001",
        context=SimpleNamespace(group_ids=("teaching_staff",)),
    )


def test_char_clip_meta_detects_truncation() -> None:
    long = "x" * 200
    result = prepare_peer_response_for_prompt_with_meta(long, max_chars=50)
    assert result.truncated
    assert "truncated from" in result.text


def test_build_inclusion_recency_cut() -> None:
    extended = [
        {"id": "old", "target_scope": "agent", "raw_response": "older turn content here"},
        {"id": "new", "target_scope": "all", "raw_response": "newer turn content here"},
    ]
    recency = [extended[1]]
    visible = recency
    records = build_memory_context_inclusion_records(
        observer_agent_id="observer_001",
        round_number=2,
        extended_candidates=extended,
        recency_window=recency,
        visible_turns=visible,
        peer_limit=500,
    )
    by_id = {r.candidate_turn_id: r for r in records}
    assert by_id["old"].exclusion_reason == "recency_cut"
    assert by_id["new"].included


def test_build_inclusion_network_filtered() -> None:
    observer = _fake_observer()
    policy = build_interaction_policy(
        turn_order_policy="round_robin",
        visibility_policy="network_bounded",
        interaction_overlay="none",
    )
    turns = [
        {
            "id": "self",
            "agent_id": "observer_001",
            "interaction_type": "broadcast",
            "target_scope": "all",
            "raw_response": "my own prior statement about classroom practice",
        },
        {
            "id": "peer",
            "agent_id": "peer_002",
            "interaction_type": "direct",
            "target_scope": "agent",
            "raw_response": "peer outside network says something about planning",
        },
    ]
    neighbors = {"observer_001": frozenset()}
    visible, excluded = partition_turns_by_visibility(
        turns,
        observer,
        policy,
        effective_visibility=policy.visibility_policy,
        network_neighbors=neighbors,
    )
    records = build_memory_context_inclusion_records(
        observer_agent_id="observer_001",
        round_number=2,
        extended_candidates=turns,
        recency_window=turns,
        visible_turns=visible,
        peer_limit=400,
    )
    by_id = {r.candidate_turn_id: r for r in records}
    assert by_id["peer"].exclusion_reason == "network_filtered"
    assert excluded


def test_group_addressed_proportion() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db = os.path.join(tmp, "ga.sqlite")
        import asyncio

        async def _run() -> dict:
            await schema_init(db)
            sim_id = await create_simulation_run(
                db,
                name="ga",
                scenario_id="psle_reform_mvp",
                status="completed",
                total_rounds=1,
                random_seed=1,
                prompt_version="v0",
                model_used="lmstudio",
            )
            await insert_agent_turn(
                db,
                simulation_id=sim_id,
                round_number=1,
                turn_index=1,
                agent_id="a1",
                agent_role="teacher",
                agent_name="T1",
                interaction_type="broadcast",
                target_scope="all",
                target_agent_id=None,
                target_agent_name="all",
                intent_tag="x",
                raw_prompt="p",
                raw_response="broadcast group message about curriculum",
            )
            await insert_agent_turn(
                db,
                simulation_id=sim_id,
                round_number=1,
                turn_index=2,
                agent_id="a2",
                agent_role="teacher",
                agent_name="T2",
                interaction_type="direct",
                target_scope="agent",
                target_agent_id="a1",
                target_agent_name="T1",
                intent_tag="x",
                raw_prompt="p",
                raw_response="direct reply about workload",
            )
            return await get_group_addressed_turn_summary(db, simulation_id=sim_id)

        summary = asyncio.run(_run())
        assert summary["total_turns"] == 2
        assert summary["group_addressed_turns"] == 1
        assert summary["group_addressed_proportion"] == 0.5


@pytest.fixture
def client_mem(monkeypatch, tmp_path):
    db = tmp_path / "iter45.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


async def _fake_llm(**kwargs) -> LLMCompletion:
    state = {
        "support_level": 0.5,
        "resistance_level": 0.5,
        "workload_stress": 0.5,
        "belief_posture": "neutral",
        "perceived_conflict": False,
    }
    return LLMCompletion(
        text="Stub.\n\n<state>\n" + json.dumps(state) + "\n</state>",
        input_tokens=10,
        output_tokens=10,
    )


@pytest.mark.asyncio
async def test_run_persists_memory_context_export() -> None:
    from mirofish_backend.simulation import orchestrator

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "mem.sqlite")
        await schema_init(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="mem ctx",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=1,
                random_seed=45,
                prompt_version="v0",
                model_used="lmstudio:local",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=2,
                random_seed=45,
                prompt_version="v0",
                model_used="lmstudio:local",
                lmstudio_model="local-test",
                lmstudio_base_url="http://127.0.0.1:9",
                llm_temperature=0.0,
                llm_max_tokens=256,
                working_memory_last_k=2,
                llm_provider="lmstudio",
                anthropic_api_key="",
                anthropic_model="unused",
                peer_context_max_chars=800,
                rag_effective=False,
                embedding_model="unused",
                rag_top_k=2,
                rag_chunk_size=200,
                rag_chunk_overlap=40,
                rag_max_inject_chars=800,
            )
            bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
            assert bundle is not None
            log = bundle.get("memory_context_log") or []
            assert len(log) > 0
            summary = bundle.get("memory_context_summary") or {}
            assert "exclusion_breakdown" in summary
            assert "group_addressed_proportion" in summary
            zip_bytes = build_export_zip(bundle)
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                assert "memory_context_log.csv" in zf.namelist()
                assert "memory_context_summary.json" in zf.namelist()
        finally:
            orchestrator.llm_complete = orig


def test_export_version_bumped() -> None:
    assert EXPORT_VERSION == "11"


def test_memory_context_report_endpoint(client_mem: TestClient) -> None:
    from mirofish_backend.simulation import orchestrator

    async def run_and_complete():
        import asyncio

        settings_db = os.environ["SQLITE_PATH"]
        await schema_init(settings_db)
        orchestrator.llm_complete = _fake_llm
        sim_id = await create_simulation_run(
            settings_db,
            name="api",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=1,
            random_seed=46,
            prompt_version="v0",
            model_used="lmstudio",
        )
        await orchestrator.run_simulation_task(
            sqlite_path=settings_db,
            simulation_id=sim_id,
            scenario_id="psle_reform_mvp",
            total_rounds=1,
            agent_limit=2,
            random_seed=46,
            prompt_version="v0",
            model_used="lmstudio",
            lmstudio_model="local",
            lmstudio_base_url="http://127.0.0.1:9",
            llm_temperature=0.0,
            llm_max_tokens=256,
            working_memory_last_k=2,
            llm_provider="lmstudio",
            anthropic_api_key="",
            anthropic_model="unused",
            peer_context_max_chars=800,
            rag_effective=False,
            embedding_model="unused",
            rag_top_k=2,
            rag_chunk_size=200,
            rag_chunk_overlap=40,
            rag_max_inject_chars=800,
        )
        return sim_id

    import asyncio

    sim_id = asyncio.run(run_and_complete())
    r = client_mem.get(f"/simulations/{sim_id}/memory-context-report")
    assert r.status_code == 200
    body = r.json()
    assert body.get("memory_context_summary")
