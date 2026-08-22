"""senna-iter-51 — agent reflection synthesis from accumulated importance."""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
import zipfile
from typing import Any

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_export_bundle
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip
from mirofish_backend.llm.reflection_parse import resolve_reflection
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block, memory_context_run_kwargs  # noqa: E402

_REFLECTION_BLOCK = (
    '<reflection>{"reflection_text": "I notice peers are cautious about workload.", '
    '"source_turn_ids": ["abc123"]}</reflection>'
)


def test_resolve_reflection_model_parsed() -> None:
    text, sources, src = resolve_reflection(
        _REFLECTION_BLOCK,
        fallback_source_turn_ids=["abc123"],
    )
    assert "cautious" in text
    assert sources == ["abc123"]
    assert src == "model_parsed"


def test_resolve_reflection_fallback() -> None:
    text, sources, src = resolve_reflection(
        "unstructured reply",
        fallback_source_turn_ids=["t1", "t2"],
    )
    assert text
    assert sources == ["t1", "t2"]
    assert src == "fallback"


async def _fake_llm_with_reflection(**kwargs: Any) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    user = str((messages[1] or {}).get("content") or "") if len(messages) > 1 else ""
    if "memory-importance scorer" in system.lower():
        score = 8
        m = re.search(r"turn_index=(\d+)", user)
        if m:
            score = 5 + int(m.group(1))
        return LLMCompletion(
            text=f'<importance_score>{{"score": {score}}}</importance_score>',
            input_tokens=8,
            output_tokens=4,
        )
    if "reflection synthesiser" in system.lower():
        ids = re.findall(r"turn_id=([a-f0-9]+)", user)
        payload = {
            "reflection_text": "Synthesised insight from recent observations.",
            "source_turn_ids": ids[:3],
        }
        return LLMCompletion(
            text="<reflection>\n" + json.dumps(payload) + "\n</reflection>",
            input_tokens=20,
            output_tokens=12,
        )
    return await fake_llm_state_block(**kwargs)


async def _run_sim(
    db_path: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    reflection_enabled: bool,
    threshold: int = 10,
    seed: int = 511,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        _fake_llm_with_reflection,
    )
    monkeypatch.setattr(
        "mirofish_backend.simulation.importance_scoring.llm_complete",
        _fake_llm_with_reflection,
    )
    monkeypatch.setattr(
        "mirofish_backend.simulation.reflection.llm_complete",
        _fake_llm_with_reflection,
    )
    await init_db(db_path)
    sim_id = await create_simulation_run(
        db_path,
        name="iter51",
        scenario_id="psle_reform_mvp",
        status="pending",
        total_rounds=2,
        random_seed=seed,
        prompt_version="v0",
        model_used="lmstudio:local",
        config_snapshot={
            "reflection_enabled": reflection_enabled,
            "reflection_trigger_threshold": threshold,
            "importance_scoring_enabled": reflection_enabled,
        },
    )
    kwargs = memory_context_run_kwargs(agent_limit=2, total_rounds=2, llm_concurrency_cap=1)
    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        random_seed=seed,
        reflection_enabled=reflection_enabled,
        reflection_trigger_threshold=threshold,
        reflection_prompt_version="v1",
        importance_scoring_enabled=reflection_enabled,
        **kwargs,
    )
    bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
    assert bundle is not None
    return bundle


@pytest.mark.asyncio
async def test_flag_off_no_reflections(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "off.sqlite")
        bundle = await _run_sim(db_path, monkeypatch, reflection_enabled=False, seed=512)
        assert bundle.get("agent_reflections") == []


@pytest.mark.asyncio
async def test_flag_on_reflections_with_provenance(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "on.sqlite")
        bundle = await _run_sim(db_path, monkeypatch, reflection_enabled=True, threshold=10, seed=513)
        reflections = bundle.get("agent_reflections") or []
        assert reflections, "expected at least one reflection when threshold is low"
        for row in reflections:
            assert row.get("reflection_text")
            assert row.get("source_turn_ids")
            assert len(row["source_turn_ids"]) >= 1
            assert row.get("parse_source") in ("model_parsed", "repaired", "fallback")
            assert row.get("accumulated_importance", 0) >= 10
        cfg = bundle["run"].get("config_snapshot") or {}
        assert cfg.get("reflection_audit")
        zip_bytes = build_export_zip(bundle)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert "agent_reflections.csv" in zf.namelist()
            csv_text = zf.read("agent_reflections.csv").decode("utf-8")
            assert "source_turn_ids" in csv_text


@pytest.mark.asyncio
async def test_high_threshold_no_reflection(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "high.sqlite")
        bundle = await _run_sim(
            db_path, monkeypatch, reflection_enabled=True, threshold=500, seed=514
        )
        assert bundle.get("agent_reflections") == []


@pytest.mark.asyncio
async def test_flag_off_transcript_regression(monkeypatch: pytest.MonkeyPatch) -> None:
    def _sig(transcript: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
        return [
            (t["round_number"], t["turn_index"], t["agent_id"], t["raw_response"])
            for t in transcript
        ]

    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.sqlite")
        b = os.path.join(tmp, "b.sqlite")
        bundle_a = await _run_sim(a, monkeypatch, reflection_enabled=False, seed=515)
        bundle_b = await _run_sim(b, monkeypatch, reflection_enabled=False, seed=515)
        assert _sig(bundle_a["transcript"]) == _sig(bundle_b["transcript"])


def test_export_version_bumped() -> None:
    assert EXPORT_VERSION == "14"
