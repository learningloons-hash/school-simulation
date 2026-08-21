"""senna-iter-50 — weighted memory retrieval (recency + importance + relevance)."""

from __future__ import annotations

import os
import tempfile
from typing import Any

import pytest

from mirofish_backend.db.repo import create_simulation_run, get_simulation_export_bundle
from mirofish_backend.db.schema import init_db
from mirofish_backend.export_bundle import EXPORT_VERSION
from mirofish_backend.rag import memory_index
from mirofish_backend.simulation import orchestrator
from mirofish_backend.simulation.memory_retrieval import (
    RetrievalWeights,
    importance_component,
    rank_turns,
    recency_components,
)
from mirofish_backend.simulation.weighted_retrieval import weighted_retrieval_config_snapshot_fields

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block, memory_context_run_kwargs  # noqa: E402


def _candidates(n: int = 4) -> list[dict[str, Any]]:
    return [
        {
            "id": f"t{i}",
            "round_number": 1,
            "turn_index": i,
            "agent_id": "a1",
            "raw_response": f"turn {i}",
            "importance_score": score,
        }
        for i, score in enumerate([3, 5, 7, 10], start=1)
    ]


@pytest.fixture(autouse=True)
def _clear_memory_index() -> None:
    memory_index.clear_memory_index_cache()
    yield
    memory_index.clear_memory_index_cache()


def test_recency_components_monotonic() -> None:
    cands = _candidates(4)
    rec = recency_components(cands)
    assert rec["t1"] == 0.0
    assert rec["t4"] == 1.0


def test_importance_component_null_is_neutral() -> None:
    assert importance_component(None) == 0.5


def test_rank_recency_only_prefers_newest() -> None:
    cands = _candidates(4)
    for c in cands:
        memory_index._TURN_VECTORS[("sim", c["id"])] = [0.0, 1.0]  # noqa: SLF001
    ranked = rank_turns(
        cands,
        weights=RetrievalWeights(recency=1.0, importance=0.0, relevance=0.0),
        simulation_id="sim",
        situation_vector=[1.0, 0.0],
        top_k=1,
    )
    assert ranked[0].turn["id"] == "t4"


def test_rank_importance_only_prefers_high_score() -> None:
    cands = _candidates(4)
    for c in cands:
        memory_index._TURN_VECTORS[("sim", c["id"])] = [0.5, 0.5]  # noqa: SLF001
    ranked = rank_turns(
        cands,
        weights=RetrievalWeights(recency=0.0, importance=1.0, relevance=0.0),
        simulation_id="sim",
        situation_vector=[0.5, 0.5],
        top_k=1,
    )
    assert ranked[0].turn["id"] == "t4"


def test_rank_relevance_only_prefers_matching_vector() -> None:
    cands = _candidates(3)
    memory_index._TURN_VECTORS[("sim", "t1")] = [0.0, 1.0]  # noqa: SLF001
    memory_index._TURN_VECTORS[("sim", "t2")] = [1.0, 0.0]  # noqa: SLF001
    memory_index._TURN_VECTORS[("sim", "t3")] = [0.7, 0.7]  # noqa: SLF001
    ranked = rank_turns(
        cands[:3],
        weights=RetrievalWeights(recency=0.0, importance=0.0, relevance=1.0),
        simulation_id="sim",
        situation_vector=[1.0, 0.0],
        top_k=1,
    )
    assert ranked[0].turn["id"] == "t2"


async def _fake_embed(*, texts: list[str], **kwargs: Any) -> list[list[float]]:
    out: list[list[float]] = []
    for t in texts:
        if "peer_response" in t or "situation" in t.lower():
            out.append([1.0, 0.0, 0.0])
        elif "HIGHREL" in t:
            out.append([1.0, 0.0, 0.0])
        elif "LOWREL" in t:
            out.append([0.0, 1.0, 0.0])
        else:
            out.append([0.0, 0.0, 1.0])
    return out


async def _run_sim(
    db_path: str,
    monkeypatch: pytest.MonkeyPatch,
    *,
    weighted: bool,
    importance: bool = False,
    seed: int = 501,
) -> dict[str, Any]:
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        fake_llm_state_block,
    )
    embed_calls: list[int] = []

    async def _count_embed(*, texts: list[str], **kwargs: Any) -> list[list[float]]:
        embed_calls.append(len(texts))
        return await _fake_embed(texts=texts, **kwargs)

    monkeypatch.setattr(
        "mirofish_backend.rag.memory_index.embed_texts_openai_compatible",
        _count_embed,
    )
    monkeypatch.setattr(
        "mirofish_backend.rag.embeddings.embed_texts_openai_compatible",
        _count_embed,
    )

    weights = RetrievalWeights(recency=0.34, importance=0.33, relevance=0.33)
    await init_db(db_path)
    sim_id = await create_simulation_run(
        db_path,
        name="iter50",
        scenario_id="psle_reform_mvp",
        status="pending",
        total_rounds=2,
        random_seed=seed,
        prompt_version="v0",
        model_used="lmstudio:local",
        config_snapshot={
            "weighted_retrieval_enabled": weighted,
            "importance_scoring_enabled": importance,
            **weighted_retrieval_config_snapshot_fields(enabled=weighted, weights=weights),
        },
    )
    kwargs = memory_context_run_kwargs(agent_limit=2, total_rounds=2, llm_concurrency_cap=1)
    kwargs["embedding_model"] = "test-embed"
    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        random_seed=seed,
        weighted_retrieval_enabled=weighted,
        retrieval_weight_recency=0.34,
        retrieval_weight_importance=0.33,
        retrieval_weight_relevance=0.33,
        importance_scoring_enabled=importance,
        **kwargs,
    )
    bundle = await get_simulation_export_bundle(db_path, simulation_id=sim_id)
    assert bundle is not None
    bundle["_embed_call_batches"] = embed_calls
    return bundle


def _retrieval_signature(log: list[dict[str, Any]]) -> list[tuple[Any, ...]]:
    return sorted(
        (
            int(r.get("round_number") or 0),
            str(r.get("observer_agent_id") or ""),
            bool(r.get("included")),
            r.get("exclusion_reason"),
            str(r.get("target_scope") or ""),
            bool(r.get("retrieval_signals")),
        )
        for r in log
    )


@pytest.mark.asyncio
async def test_flag_off_no_embedding_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "off.sqlite")
        bundle = await _run_sim(db_path, monkeypatch, weighted=False, seed=502)
        assert sum(bundle["_embed_call_batches"]) == 0
        cfg = bundle["run"].get("config_snapshot") or {}
        assert cfg.get("weighted_retrieval_enabled") is False


@pytest.mark.asyncio
async def test_flag_off_retrieval_stable_on_fixed_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.sqlite")
        b = os.path.join(tmp, "b.sqlite")
        bundle_a = await _run_sim(a, monkeypatch, weighted=False, seed=503)
        bundle_b = await _run_sim(b, monkeypatch, weighted=False, seed=503)
        log_a = bundle_a.get("memory_context_log") or []
        log_b = bundle_b.get("memory_context_log") or []
        assert _retrieval_signature(log_a) == _retrieval_signature(log_b)


@pytest.mark.asyncio
async def test_flag_on_included_rows_carry_retrieval_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "on.sqlite")
        bundle = await _run_sim(db_path, monkeypatch, weighted=True, seed=504)
        assert sum(bundle["_embed_call_batches"]) > 0
        included = [r for r in (bundle.get("memory_context_log") or []) if r.get("included")]
        assert included
        with_signals = [r for r in included if r.get("retrieval_signals")]
        assert with_signals, "expected retrieval_signals on weighted included rows"
        sig = with_signals[0]["retrieval_signals"]
        assert "retrieval_score" in sig
        assert "retrieval_recency" in sig
        cfg = bundle["run"].get("config_snapshot") or {}
        assert cfg.get("weighted_retrieval_enabled") is True
        assert "retrieval_weight_recency" in cfg


@pytest.mark.asyncio
async def test_weighted_retrieval_bounded_db_work(monkeypatch: pytest.MonkeyPatch) -> None:
    """B2 scale: fetch calls grow ~linearly with rounds×agents, not O(turns²)."""
    self_calls: list[int] = []
    recent_calls: list[int] = []
    real_self = orchestrator.get_last_agent_turn_rows
    real_recent = orchestrator.get_recent_interactions

    async def _track_self(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self_calls.append(int(kwargs.get("last_k") or 0))
        return await real_self(*args, **kwargs)

    async def _track_recent(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        recent_calls.append(int(kwargs.get("last_k") or 0))
        return await real_recent(*args, **kwargs)

    monkeypatch.setattr(orchestrator, "get_last_agent_turn_rows", _track_self)
    monkeypatch.setattr(orchestrator, "get_recent_interactions", _track_recent)
    monkeypatch.setattr(
        "mirofish_backend.rag.memory_index.embed_texts_openai_compatible",
        _fake_embed,
    )

    async def _run_rounds(rounds: int) -> int:
        self_calls.clear()
        recent_calls.clear()
        with tempfile.TemporaryDirectory() as tmp:
            db_path = os.path.join(tmp, f"scale_{rounds}.sqlite")
            await init_db(db_path)
            sim_id = await create_simulation_run(
                db_path,
                name="scale",
                scenario_id="psle_reform_mvp",
                status="pending",
                total_rounds=rounds,
                random_seed=505,
                prompt_version="v0",
                model_used="lmstudio:local",
            )
            kwargs = memory_context_run_kwargs(
                agent_limit=2, total_rounds=rounds, llm_concurrency_cap=1
            )
            kwargs["embedding_model"] = "test-embed"
            monkeypatch.setattr(
                "mirofish_backend.simulation.orchestrator.llm_complete",
                fake_llm_state_block,
            )
            await orchestrator.run_simulation_task(
                sqlite_path=db_path,
                simulation_id=sim_id,
                random_seed=505,
                weighted_retrieval_enabled=True,
                **kwargs,
            )
        return len(self_calls) + len(recent_calls)

    calls_2 = await _run_rounds(2)
    calls_4 = await _run_rounds(4)
    # 2 agents × 2 rounds = 4 LLM turns vs 8 — expect ~2× calls, not ~4× (quadratic).
    assert calls_4 <= calls_2 * 3
    assert calls_2 > 0


def test_export_version_bumped() -> None:
    assert EXPORT_VERSION == "13"
