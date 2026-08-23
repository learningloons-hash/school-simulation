"""senna-iter-52 — Arc 11 memory ablation harness (stubbed CI path)."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from run_arc10_diagnostics import run_arc10_diagnostics  # noqa: E402

from mirofish_backend.db.schema import init_db
from mirofish_backend.diagnostics import architectural_interview as ai_mod
from mirofish_backend.diagnostics.arc11_ablation import (
    ABLATION_CONDITIONS,
    AblationRunProfile,
    build_ablation_results_payload,
    build_network_csv_for_scenario,
    compute_deltas_vs_baseline,
    condition_memory_flags,
    execute_ablation_cell,
    generate_ablation_markdown,
    load_measured_baseline_summary,
)
from mirofish_backend.llm.router import LLMCompletion

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulation_helpers import fake_llm_state_block  # noqa: E402

FIXTURES_DIR = _REPO / "backend/tests/fixtures/membench"
BASELINE_FIXTURE = _REPO / "backend/tests/fixtures/arc11/measured_baseline_summary.json"
SCHEMA_FIXTURE = _REPO / "backend/tests/fixtures/arc11/ablation_results_schema.json"


def _judge_block(score: int) -> str:
    return f'<judge_score>{{"score": {score}, "rationale": "test"}}</judge_score>'


async def _fake_llm_ablation(**kwargs: Any) -> LLMCompletion:
    messages = kwargs.get("messages") or []
    system = str((messages[0] or {}).get("content") or "")
    user = str((messages[1] or {}).get("content") or "") if len(messages) > 1 else ""
    if "rubric judge" in system.lower():
        if "reflection" in user.lower():
            return LLMCompletion(text=_judge_block(1), input_tokens=2, output_tokens=2)
        if "memory_retrieval" in user.lower():
            return LLMCompletion(text=_judge_block(2), input_tokens=2, output_tokens=2)
        return LLMCompletion(text=_judge_block(1), input_tokens=2, output_tokens=2)
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


async def _fake_embed(*, texts: list[str], **kwargs: Any) -> list[list[float]]:
    return [[1.0, 0.0, 0.0] for _ in texts]


def _patch_ablation_llm_stack(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mirofish_backend.simulation.orchestrator.llm_complete",
        _fake_llm_ablation,
    )
    monkeypatch.setattr(
        "mirofish_backend.simulation.importance_scoring.llm_complete",
        _fake_llm_ablation,
    )
    monkeypatch.setattr(
        "mirofish_backend.simulation.reflection.llm_complete",
        _fake_llm_ablation,
    )
    monkeypatch.setattr(ai_mod, "_llm_complete", _fake_llm_ablation)

    async def _count_embed(*, texts: list[str], **kwargs: Any) -> list[list[float]]:
        return await _fake_embed(texts=texts, **kwargs)

    monkeypatch.setattr(
        "mirofish_backend.rag.memory_index.embed_texts_openai_compatible",
        _count_embed,
    )
    monkeypatch.setattr(
        "mirofish_backend.rag.embeddings.embed_texts_openai_compatible",
        _count_embed,
    )


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        (
            "baseline",
            {
                "importance_scoring_enabled": False,
                "weighted_retrieval_enabled": False,
                "reflection_enabled": False,
            },
        ),
        (
            "+importance",
            {
                "importance_scoring_enabled": True,
                "weighted_retrieval_enabled": False,
                "reflection_enabled": False,
            },
        ),
        (
            "+importance+retrieval",
            {
                "importance_scoring_enabled": True,
                "weighted_retrieval_enabled": True,
                "reflection_enabled": False,
            },
        ),
        (
            "+importance+retrieval+reflection",
            {
                "importance_scoring_enabled": True,
                "weighted_retrieval_enabled": True,
                "reflection_enabled": True,
            },
        ),
    ],
)
def test_condition_memory_flags_ladder(condition: str, expected: dict[str, bool]) -> None:
    assert condition_memory_flags(condition) == expected


def test_unknown_condition_raises() -> None:
    with pytest.raises(ValueError, match="unknown ablation condition"):
        condition_memory_flags("full_stack")


def test_compute_deltas_vs_fixture_baseline() -> None:
    baseline = load_measured_baseline_summary(BASELINE_FIXTURE)
    metrics = {
        "membench_factual_mean": 0.8,
        "membench_reflective_mean": 0.9,
        "interview_category_means": {
            "reflection": 1.5,
            "memory_retrieval": 2.5,
        },
        "memory_group_addressed_proportion": 0.5,
        "memory_exclusion_breakdown": {
            "included_clean": 40,
            "recency_cut": 25,
        },
    }
    deltas = compute_deltas_vs_baseline(metrics, baseline["metrics"])
    assert deltas["membench_factual_mean"] == pytest.approx(-0.2)
    assert deltas["membench_reflective_mean"] == pytest.approx(-0.1)
    assert deltas["interview_category_means"]["reflection"] == pytest.approx(-0.5)
    assert deltas["interview_category_means"]["memory_retrieval"] == pytest.approx(0.5)
    assert deltas["memory_exclusion_breakdown"]["included_clean"] == -3
    assert deltas["memory_exclusion_breakdown"]["recency_cut"] == 4


def test_network_csv_for_fsbb_comparator() -> None:
    csv_text = build_network_csv_for_scenario(scenario_id="fsbb_comparator", agent_limit=3)
    lines = [ln for ln in csv_text.strip().splitlines() if ln]
    assert lines[0].startswith("source_agent_id")
    assert len(lines) >= 3


@pytest.mark.asyncio
async def test_ablation_harness_one_seed_four_conditions(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ablation_llm_stack(monkeypatch)
    baseline = load_measured_baseline_summary(BASELINE_FIXTURE)
    profile = AblationRunProfile(total_rounds=2)
    seed = 42
    records = []

    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "arc11.sqlite")
        await init_db(db_path)
        for condition in ABLATION_CONDITIONS:
            rec = await execute_ablation_cell(
                sqlite_path=db_path,
                condition=condition,
                seed=seed,
                profile=profile,
                fixtures_dir=FIXTURES_DIR,
                baseline_metrics=baseline["metrics"],
                run_arc10_diagnostics=run_arc10_diagnostics,
                execute_interview=True,
            )
            records.append(rec)
            flags = condition_memory_flags(condition)
            bundle = rec.diagnostics
            assert rec.simulation_id
            assert rec.metrics.get("membench_factual_mean") is not None
            assert rec.deltas_vs_baseline.get("membench_factual_mean") is not None
            assert rec.cost.get("wall_clock_seconds") is not None
            assert rec.dispersion.get("final_round_support_stdev") is not None
            assert bundle.get("architectural_interview")
            snap_flags = (rec.cost or {}).get("importance_scoring_token_totals")
            if flags["importance_scoring_enabled"]:
                assert snap_flags is not None or rec.cost.get("total_input_tokens") is not None

        payload = build_ablation_results_payload(
            profile=profile,
            seeds=[seed],
            conditions=list(ABLATION_CONDITIONS),
            records=records,
            baseline_ref=baseline,
            command="pytest test_senna_iter52_arc11_ablation.py",
        )
        assert payload["harness"] == "senna-iter-52"
        assert len(payload["runs"]) == 4
        assert set(payload["aggregated_by_condition"]) == set(ABLATION_CONDITIONS)
        md = generate_ablation_markdown(payload)
        assert "Arc 11 memory ablation results" in md
        assert "baseline" in md

        required = set(json.loads(SCHEMA_FIXTURE.read_text())["required"])
        assert required <= set(payload.keys())
