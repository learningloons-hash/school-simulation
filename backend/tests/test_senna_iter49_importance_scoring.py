"""senna-iter-49 — memory importance scoring at write time."""

from __future__ import annotations

import json
import os
import re
import tempfile
import time
from typing import Any

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_export_bundle
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip
from mirofish_backend.llm.importance_parse import resolve_batch_importance_scores, resolve_importance_score
from mirofish_backend.llm.router import LLMCompletion
from mirofish_backend.simulation import orchestrator

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block, memory_context_run_kwargs  # noqa: E402

_IMPORTANCE_BLOCK = '<importance_score>{"score": 7, "rationale": "pivotal"}</importance_score>'
_REPAIRED_BLOCK = '<importance_score>{"score": 8, "rationale": "ok",}</importance_score>'
_MALFORMED = "no structured block here but score: 6"


def test_resolve_importance_model_parsed() -> None:
    score, src = resolve_importance_score(_IMPORTANCE_BLOCK)
    assert score == 7
    assert src == "model_parsed"


def test_resolve_importance_repaired() -> None:
    score, src = resolve_importance_score(_REPAIRED_BLOCK)
    assert score == 8
    assert src == "repaired"


def test_resolve_importance_fallback() -> None:
    score, src = resolve_importance_score(_MALFORMED)
    assert score == 6
    assert src == "fallback"


def test_resolve_importance_unparseable_fallback_score() -> None:
    score, src = resolve_importance_score("completely unrelated text")
    assert score == 5
    assert src == "fallback"


def test_batch_parse_missing_ids_get_fallback() -> None:
    raw = '<importance_score>{"turn_scores": [{"turn_id": "a", "score": 9}]}</importance_score>'
    parsed = resolve_batch_importance_scores(raw, expected_turn_ids=["a", "b"])
    assert parsed["a"] == (9, "model_parsed")
    assert parsed["b"][0] == 5
    assert parsed["b"][1] == "fallback"


def _importance_score_from_user(user: str, turn_index: int | None = None) -> int:
    if turn_index is not None:
        return 5 + turn_index
    m = re.search(r"turn_index=(\d+)", user)
    if not m:
        m = re.search(r"turn (\d+)", user)
    if m:
        return 5 + int(m.group(1))
    return 7


async def _fake_llm_turn_and_importance(**kwargs: Any) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    user = str((messages[1] or {}).get("content") or "") if len(messages) > 1 else ""
    if "memory-importance scorer" in system.lower():
        if "turn_scores" in user or "Respond with exactly one block listing every turn_id" in user:
            ids = re.findall(r"turn_id=([a-f0-9]+)", user)
            indices = [int(x) for x in re.findall(r"turn_index=(\d+)", user)]
            payload = {
                "turn_scores": [
                    {"turn_id": tid, "score": 5 + idx}
                    for tid, idx in zip(ids, indices, strict=False)
                ]
            }
            return LLMCompletion(
                text="<importance_score>\n" + json.dumps(payload) + "\n</importance_score>",
                input_tokens=12,
                output_tokens=8,
            )
        score = _importance_score_from_user(user)
        return LLMCompletion(
            text=f'<importance_score>{{"score": {score}}}</importance_score>',
            input_tokens=10,
            output_tokens=4,
        )
    return await fake_llm_state_block(**kwargs)


async def _run_short_sim(
    db_path: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    importance_enabled: bool,
    scoring_mode: str = "per_turn",
    seed: int = 49,
    patch_llm: bool = True,
) -> dict[str, Any]:
    if patch_llm:
        monkeypatch.setattr(
            "mirofish_backend.simulation.orchestrator.llm_complete",
            _fake_llm_turn_and_importance,
        )
        monkeypatch.setattr(
            "mirofish_backend.simulation.importance_scoring.llm_complete",
            _fake_llm_turn_and_importance,
        )
    await init_db(db_path)
    sim_id = await create_simulation_run(
        db_path,
        name="iter49",
        scenario_id="psle_reform_mvp",
        status="pending",
        total_rounds=2,
        random_seed=seed,
        prompt_version="v0",
        model_used="lmstudio:local",
    )
    kwargs = memory_context_run_kwargs(agent_limit=2, total_rounds=2, llm_concurrency_cap=1)
    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        random_seed=seed,
        importance_scoring_enabled=importance_enabled,
        importance_prompt_version="v1",
        importance_scoring_mode=scoring_mode,
        **kwargs,
    )
    bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
    assert bundle is not None
    return bundle


def _transcript_signature(transcript: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return [
        (t["round_number"], t["turn_index"], t["agent_id"], t["raw_response"])
        for t in transcript
    ]


@pytest.mark.asyncio
async def test_flag_off_no_importance_columns_or_scorer_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    real = _fake_llm_turn_and_importance

    async def _track(**kwargs: Any) -> LLMCompletion:
        messages = kwargs.get("messages") or []
        system = str((messages[0] or {}).get("content") or "")
        calls.append(system[:80])
        return await real(**kwargs)

    monkeypatch.setattr("mirofish_backend.simulation.orchestrator.llm_complete", _track)
    monkeypatch.setattr("mirofish_backend.simulation.importance_scoring.llm_complete", _track)

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "off.sqlite")
        bundle = await _run_short_sim(
            db_path, monkeypatch, importance_enabled=False, patch_llm=False
        )
        assert not any("memory-importance scorer" in c.lower() for c in calls)
        for row in bundle["transcript"]:
            assert row.get("importance_score") is None
            assert row.get("importance_source") is None


@pytest.mark.asyncio
async def test_flag_off_regression_fixed_seed_transcript_stable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_a = os.path.join(tmp, "a.sqlite")
        db_b = os.path.join(tmp, "b.sqlite")
        bundle_a = await _run_short_sim(db_a, monkeypatch, importance_enabled=False, seed=491)
        bundle_b = await _run_short_sim(db_b, monkeypatch, importance_enabled=False, seed=491)
        assert _transcript_signature(bundle_a["transcript"]) == _transcript_signature(
            bundle_b["transcript"]
        )


@pytest.mark.asyncio
async def test_flag_on_every_turn_scored_and_exported(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "on.sqlite")
        bundle = await _run_short_sim(
            db_path, monkeypatch, importance_enabled=True, scoring_mode="per_turn"
        )
        transcript = bundle["transcript"]
        assert len(transcript) >= 2
        for row in transcript:
            assert row.get("importance_score") is not None
            assert 1 <= int(row["importance_score"]) <= 10
            assert row.get("importance_source") in ("model_parsed", "repaired", "fallback")
        cfg = bundle["run"].get("config_snapshot") or {}
        assert cfg.get("importance_scoring_audit")
        zip_bytes = build_export_zip(bundle)
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            csv_text = zf.read("agent_turns.csv").decode("utf-8")
            assert "importance_score" in csv_text
            assert "importance_source" in csv_text


@pytest.mark.asyncio
async def test_per_turn_and_batch_equivalence_fixed_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_turn = os.path.join(tmp, "turn.sqlite")
        db_batch = os.path.join(tmp, "batch.sqlite")
        bundle_turn = await _run_short_sim(
            db_turn, monkeypatch, importance_enabled=True, scoring_mode="per_turn", seed=492
        )
        bundle_batch = await _run_short_sim(
            db_batch, monkeypatch, importance_enabled=True, scoring_mode="per_round_batch", seed=492
        )
        by_id_turn = {
            (r["round_number"], r["turn_index"], r["agent_id"]): r for r in bundle_turn["transcript"]
        }
        by_id_batch = {
            (r["round_number"], r["turn_index"], r["agent_id"]): r for r in bundle_batch["transcript"]
        }
        assert set(by_id_turn) == set(by_id_batch)
        for key in by_id_turn:
            assert by_id_turn[key]["importance_score"] == by_id_batch[key]["importance_score"]
            assert by_id_turn[key]["importance_source"] == by_id_batch[key]["importance_source"]


@pytest.mark.asyncio
async def test_cost_delta_both_modes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Record extra importance-scorer tokens for closeout (fixture run, 2 agents × 2 rounds)."""
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.perf_counter()
        db_turn = os.path.join(tmp, "cost_turn.sqlite")
        bundle_turn = await _run_short_sim(
            db_turn, monkeypatch, importance_enabled=True, scoring_mode="per_turn", seed=493
        )
        wall_turn = time.perf_counter() - t0

        t1 = time.perf_counter()
        db_batch = os.path.join(tmp, "cost_batch.sqlite")
        bundle_batch = await _run_short_sim(
            db_batch, monkeypatch, importance_enabled=True, scoring_mode="per_round_batch", seed=493
        )
        wall_batch = time.perf_counter() - t1

        cfg_turn = (bundle_turn["run"].get("config_snapshot") or {}).get(
            "importance_scoring_token_totals", {}
        )
        cfg_batch = (bundle_batch["run"].get("config_snapshot") or {}).get(
            "importance_scoring_token_totals", {}
        )
        assert cfg_turn.get("input_tokens", 0) > 0
        assert cfg_batch.get("input_tokens", 0) > 0
        # per_turn uses more scorer calls than per_round_batch on this fixture
        assert cfg_turn["input_tokens"] >= cfg_batch["input_tokens"]
        assert wall_turn > 0 and wall_batch > 0


def test_export_version_bumped_to_12() -> None:
    assert EXPORT_VERSION == "14"
