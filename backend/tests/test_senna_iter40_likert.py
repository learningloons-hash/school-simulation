"""senna-iter-40 — round-end Likert self-report."""

from __future__ import annotations

import io
import json
import os
import tempfile
import zipfile

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_economics_summary,
    get_simulation_export_bundle,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.main import app
from mirofish_backend.simulation import orchestrator


def _state_block() -> str:
    state = {
        "support_level": 0.5,
        "resistance_level": 0.5,
        "workload_stress": 0.5,
        "belief_posture": "neutral",
        "perceived_conflict": False,
    }
    return "Stub turn.\n\n<state>\n" + json.dumps(state) + "\n</state>"


def _likert_block() -> str:
    payload = {
        "support": "somewhat support",
        "resistance": "moderate resistance",
        "workload_stress": "manageable stress",
    }
    return "<likert>\n" + json.dumps(payload) + "\n</likert>"


async def _fake_llm_with_likert(**kwargs) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    if "round-end self-report" in system:
        return LLMCompletion(text=_likert_block(), input_tokens=4, output_tokens=4)
    return LLMCompletion(text=_state_block(), input_tokens=8, output_tokens=8)


@pytest.fixture
def client_skip_sim(monkeypatch, tmp_path):
    db = tmp_path / "iter40_api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))

    async def skip_run(**kwargs):
        return None

    monkeypatch.setattr(
        "mirofish_backend.api.simulations.run_simulation_task_guarded",
        skip_run,
    )
    with TestClient(app) as c:
        yield c


def test_likert_enabled_without_anchors_returns_422(client_skip_sim: TestClient) -> None:
    r = client_skip_sim.post(
        "/simulations/run",
        json={
            "scenario_id": "psle_reform_mvp",
            "total_rounds": 1,
            "agent_limit": 2,
            "likert_self_report_enabled": True,
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_likert_rows_persist_and_export() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "likert.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_with_likert
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="Likert run",
                scenario_id="fsbb_comparator",
                status="pending",
                total_rounds=1,
                random_seed=40,
                prompt_version="v0",
                model_used="lmstudio:local",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="fsbb_comparator",
                total_rounds=1,
                agent_limit=2,
                random_seed=40,
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
                likert_self_report_enabled=True,
            )
            bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
            likert = bundle.get("likert_responses") or []
            assert len(likert) >= 6
            row = likert[0]
            assert row["ordinal_value"] in range(6)
            assert row["source"] in ("model_parsed", "repaired", "keyword_fallback")
            assert "divergence" in row
            assert row["input_tokens"] == 4
            assert row["output_tokens"] == 4
            assert bundle["run"]["economics"]["tier_breakdown"]["likert_self_report_turns"] == 2
            summary = await get_simulation_economics_summary(db_path, simulation_id=sim_id)
            assert summary is not None
            assert summary["tier_breakdown"]["likert_self_report_turns"] == 2
            assert summary["estimated_cost_usd"] == bundle["run"]["economics"]["estimated_cost_usd"]
            zip_bytes = build_export_zip(bundle)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                assert "agent_round_likert.csv" in zf.namelist()
        finally:
            orchestrator.llm_complete = orig


@pytest.mark.asyncio
async def test_legacy_run_without_likert_has_no_rows() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "legacy.sqlite")
        await init_db(db_path)
        orig = orchestrator.llm_complete
        orchestrator.llm_complete = _fake_llm_with_likert
        try:
            sim_id = await create_simulation_run(
                db_path,
                name="Legacy",
                scenario_id="fsbb_comparator",
                status="pending",
                total_rounds=1,
                random_seed=41,
                prompt_version="v0",
                model_used="lmstudio:local",
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="fsbb_comparator",
                total_rounds=1,
                agent_limit=2,
                random_seed=41,
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
                likert_self_report_enabled=False,
            )
            bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
            assert bundle.get("likert_responses") == []
        finally:
            orchestrator.llm_complete = orig


def test_export_version_bumped_for_likert() -> None:
    assert EXPORT_VERSION == "9"
