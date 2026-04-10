import os
import tempfile

import pytest

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_recent_interactions,
    get_simulation_export_bundle,
    get_simulation_status_with_transcript,
    insert_agent_turn,
    list_simulation_runs,
)
from mirofish_backend.db.schema import init_db


@pytest.mark.asyncio
async def test_create_and_fetch_simulation_transcript() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        await init_db(db_path)

        sim_id = await create_simulation_run(
            db_path,
            name="Test",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=3,
            random_seed=42,
            prompt_version="v0",
            model_used="lmstudio-test-model",
        )

        fetched = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        assert fetched is not None
        assert fetched["id"] == sim_id
        assert fetched["status"] == "pending"
        assert fetched["total_rounds"] == 3
        assert fetched["current_round"] == 0
        assert fetched["transcript"] == []


@pytest.mark.asyncio
async def test_insert_turn_persists_interaction_metadata() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        await init_db(db_path)

        sim_id = await create_simulation_run(
            db_path,
            name="Test",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=2,
            random_seed=42,
            prompt_version="v0",
            model_used="lmstudio-test-model",
        )

        await insert_agent_turn(
            db_path,
            simulation_id=sim_id,
            round_number=1,
            turn_index=1,
            agent_id="principal_001_000",
            agent_role="principal",
            agent_name="Principal",
            interaction_type="broadcast",
            target_scope="all",
            target_agent_id=None,
            target_agent_name=None,
            intent_tag="policy_update",
            raw_prompt="prompt",
            raw_response="response",
            latency_ms=100,
        )

        fetched = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        assert fetched is not None
        assert len(fetched["transcript"]) == 1
        turn = fetched["transcript"][0]
        assert turn["interaction_type"] == "broadcast"
        assert turn["target_scope"] == "all"
        assert turn["target_agent_name"] is None
        assert turn["intent_tag"] == "policy_update"
        assert turn.get("group_ids") == []
        assert turn.get("fidelity_tier") == 1

        recent = await get_recent_interactions(db_path, simulation_id=sim_id, last_k=5)
        assert len(recent) == 1
        assert recent[0]["interaction_type"] == "broadcast"


@pytest.mark.asyncio
async def test_list_and_export_bundle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.sqlite")
        await init_db(db_path)

        sim_id = await create_simulation_run(
            db_path,
            name="ExportTest",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=1,
            random_seed=7,
            prompt_version="v1",
            model_used="test-model",
            config_snapshot={"agent_limit": 1},
        )

        rows = await list_simulation_runs(db_path, limit=10)
        assert len(rows) == 1
        assert rows[0]["id"] == sim_id

        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        assert bundle["run"]["id"] == sim_id
        assert bundle["run"]["config_snapshot"]["agent_limit"] == 1
        assert bundle["transcript"] == []
        assert bundle["state_timeline"] == []
        assert bundle["outcome_indicators"] == []

