"""Senna Arc 6: incremental .md simulation transcripts."""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest

from mirofish_backend.simulation.transcript_writer import (
    append_round_to_transcript,
    close_transcript,
    open_transcript,
)


@pytest.mark.asyncio
async def test_transcript_round_trip_in_temp_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        sid = "abc123sim"
        path = await open_transcript(
            tmp,
            simulation_id=sid,
            scenario_id="psle_reform_mvp",
            agent_names=[("A", "role_a"), ("B", "role_b")],
            total_rounds=2,
            model_used="fake-model",
        )
        assert path.endswith(f"{sid}.md")
        await append_round_to_transcript(
            tmp,
            simulation_id=sid,
            round_number=1,
            policy_event="Event one",
            turns=[
                {
                    "agent_name": "A",
                    "agent_role": "role_a",
                    "raw_response": "Hello <state>{}</state>",
                }
            ],
            round_summary="[Round 1 — Event one] A: ...",
        )
        await append_round_to_transcript(
            tmp,
            simulation_id=sid,
            round_number=2,
            policy_event="Event two",
            turns=[
                {
                    "agent_name": "B",
                    "agent_role": "role_b",
                    "raw_response": "Reply",
                }
            ],
            round_summary="[Round 2 — Event two] B: ...",
        )
        await close_transcript(
            tmp,
            simulation_id=sid,
            completed_rounds=2,
            status="completed",
        )
        assert os.path.isfile(path)
        text = open(path, encoding="utf-8").read()
        assert "# Senna Simulation Transcript" in text
        assert "Agent Roster" in text
        assert "## Round 1 — Event one" in text
        assert "## Round 2 — Event two" in text
        assert "Simulation Complete" in text
        assert "**Status:** completed" in text
        assert "Hello" in text
        assert "<state>" not in text


def test_transcript_writer_via_asyncio_run() -> None:
    async def _inner() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            sid = "sync_run_sim"
            await open_transcript(
                tmp,
                simulation_id=sid,
                scenario_id="s1",
                agent_names=[("X", "r")],
                total_rounds=1,
                model_used="m",
            )
            p = os.path.join(tmp, f"{sid}.md")
            assert os.path.isfile(p)

    asyncio.run(_inner())
