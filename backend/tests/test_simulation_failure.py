import os
from unittest.mock import patch

import pytest

from mirofish_backend.api.simulations import run_simulation_task_guarded
from mirofish_backend.db.repo import create_simulation_run, get_simulation_status_with_transcript
from mirofish_backend.db.schema import init_db


@pytest.mark.asyncio
async def test_simulation_error_sets_failed_status() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "fail.sqlite")
        await init_db(db_path)

        sim_id = await create_simulation_run(
            db_path,
            name="FailTest",
            scenario_id="psle_reform_mvp",
            status="pending",
            total_rounds=1,
            random_seed=1,
            prompt_version="v1",
            model_used="fake",
        )

        async def boom(**_kwargs: object) -> None:
            raise RuntimeError("simulation task boom")

        with patch("mirofish_backend.api.simulations.run_simulation_task", new=boom):
            await run_simulation_task_guarded(
                sqlite_path=db_path,
                simulation_id=sim_id,
                scenario_id="psle_reform_mvp",
                total_rounds=1,
                agent_limit=1,
                random_seed=1,
                prompt_version="v1",
                model_used="fake",
                lmstudio_model="fake",
                lmstudio_base_url="http://unused",
                llm_temperature=0.0,
                llm_max_tokens=128,
                working_memory_last_k=1,
                llm_provider="lmstudio",
                anthropic_api_key="",
                anthropic_model="claude-test",
                peer_context_max_chars=1200,
                rag_effective=False,
                embedding_model="emb",
                rag_top_k=4,
                rag_chunk_size=400,
                rag_chunk_overlap=80,
                rag_max_inject_chars=2400,
            )

        res = await get_simulation_status_with_transcript(db_path, simulation_id=sim_id)
        assert res is not None
        assert res["status"] == "failed"
        assert res.get("failure_reason") is not None
        assert "RuntimeError" in (res.get("failure_reason") or "")
