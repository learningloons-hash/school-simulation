import io
import os
import tempfile
import zipfile

import pytest

from mirofish_backend.db.repo import (
    create_simulation_run,
    get_simulation_export_bundle,
    get_simulation_status_with_transcript,
    insert_validity_note,
)
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import build_export_zip


@pytest.mark.asyncio
async def test_validity_note_persists_and_exports() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "v.sqlite")
        await init_db(db_path)
        sim_id = await create_simulation_run(
            db_path,
            name="VTest",
            scenario_id="psle_reform_mvp",
            status="completed",
            total_rounds=4,
            random_seed=1,
            prompt_version="v1",
            model_used="m",
        )
        await insert_validity_note(
            db_path,
            simulation_id=sim_id,
            round_number=2,
            rater_id="rater_a",
            face_score=0.8,
            face_rubric="Plausible dialogue",
            construct_score=None,
            construct_rubric=None,
            predictive_score=0.5,
            predictive_rubric=None,
            notes="Spot check OK",
        )

        status = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        assert status is not None
        notes = status.get("validity_notes") or []
        assert len(notes) == 1
        assert notes[0]["round_number"] == 2
        assert notes[0]["rater_id"] == "rater_a"
        assert notes[0]["face_score"] == pytest.approx(0.8)
        assert notes[0]["predictive_score"] == pytest.approx(0.5)

        bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
        assert bundle is not None
        assert len(bundle["validity_notes"]) == 1
        zip_bytes = build_export_zip(bundle)
        with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as zf:
            assert "validity_notes.csv" in zf.namelist()
            body = zf.read("validity_notes.csv").decode()
        assert "rater_a" in body
        assert "face_score" in body
