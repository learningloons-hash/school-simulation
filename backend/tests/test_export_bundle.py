import io
import json
import os
import tempfile
import zipfile

import pytest

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_export_bundle,
    insert_agent_state_snapshot,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import build_export_zip


def test_build_export_zip_contains_expected_csvs() -> None:
    bundle = {
        "run": {
            "id": "abc123",
            "name": "test",
            "scenario_id": "psle_reform_mvp",
            "status": "completed",
            "total_rounds": 1,
            "current_round": 1,
            "random_seed": 42,
            "prompt_version": "v1",
            "model_used": "m",
            "config_snapshot": {"k": 1},
            "failure_reason": None,
            "created_at": "2026-01-01",
            "completed_at": "2026-01-01",
        },
        "transcript": [
            {
                "id": "t1",
                "simulation_id": "abc123",
                "round_number": 1,
                "turn_index": 1,
                "agent_id": "a1",
                "agent_role": "principal",
                "agent_name": "P",
                "interaction_type": "broadcast",
                "target_scope": "all",
                "target_agent_id": None,
                "target_agent_name": None,
                "intent_tag": "x",
                "raw_prompt": "p",
                "raw_response": "r",
                "latency_ms": 10,
                "group_ids": [],
                "effective_provider": "lmstudio",
                "effective_model": "m",
                "fidelity_tier": 1,
                "created_at": "2026-01-01",
            }
        ],
        "agent_state_snapshots": [],
        "global_state_snapshots": [],
        "round_outcomes": [],
        "validity_notes": [],
    }
    data = build_export_zip(bundle)
    with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
        names = set(zf.namelist())
    assert "simulation_run.csv" in names
    assert "agent_turns.csv" in names
    assert "agent_state_snapshots.csv" in names
    assert "global_state_snapshots.csv" in names
    assert "round_outcomes.csv" in names
    assert "validity_notes.csv" in names


@pytest.mark.asyncio
async def test_export_zip_includes_attribute_sections_from_bundle() -> None:
    """Regression: Iteration 13 snapshot attribute_sections reach JSON bundle + ZIP CSV."""
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "export_attr.sqlite")
        await init_db(db_path)
        sim_id = await create_simulation_run(
            db_path,
            name="ExportAttr",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
            config_snapshot={},
        )
        sections = {"identity": {"nationality": "Testland"}, "attitudes": {}, "personal_history": {}}
        await insert_agent_state_snapshot(
            db_path,
            simulation_id=sim_id,
            round_number=1,
            agent_id="principal_001_000",
            agent_role="principal",
            agent_name="P",
            age=40,
            sex="female",
            ethnicity="X",
            ses="middle",
            support_level=0.5,
            resistance_level=0.5,
            workload_stress=0.5,
            belief_posture="neutral",
            attribute_sections_json=json.dumps(sections, sort_keys=True),
        )
        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        snap = bundle["agent_state_snapshots"][0]
        assert snap["attribute_sections"]["identity"]["nationality"] == "Testland"
        zip_bytes = build_export_zip(bundle)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            csv_body = zf.read("agent_state_snapshots.csv").decode()
        assert "Testland" in csv_body
