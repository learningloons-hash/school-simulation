"""M3 Sonnet 5.5 pin — in-run Anthropic call sites: agent turn, Likert, importance, reflection.

Also covers: Sonnet-only max_tokens floors, the per-run JSONL request log (one row
per request, fields matching the real wire payload, no secrets/prompt text), and
the ad-hoc JSONL log used outside a queued run.
"""

from __future__ import annotations

import json
import os

import pytest

from senna_backend.config import Settings
from senna_backend.db.repo import create_simulation_run
from senna_backend.db.schema import init_db
from senna_backend.llm.anthropic_request import (
    RunLLMExtras,
    SONNET_55_MAX_TOKENS_AGENT_TURN,
    SONNET_55_MAX_TOKENS_IMPORTANCE,
    SONNET_55_MAX_TOKENS_IMPORTANCE_BATCH,
    SONNET_55_MAX_TOKENS_LIKERT,
    SONNET_55_MAX_TOKENS_REFLECTION,
    resolve_anthropic_request_config,
)
from senna_backend.llm.llm_request_log import (
    LLMRequestLogger,
    adhoc_llm_request_log_path,
    llm_request_log_path,
)
from senna_backend.llm.model_profiles import ANTHROPIC_DEFAULT_ID, LOCAL_LMSTUDIO_DEFAULT_ID
from senna_backend.llm.router import llm_complete
from senna_backend.simulation import orchestrator
from senna_backend.simulation.importance_scoring import score_round_importance_batch, score_turn_importance
from senna_backend.simulation.reflection import PendingObservation, synthesize_reflection
from sonnet55_test_support import (  # noqa: F401 -- fixture referenced by name in test signatures
    FakeAnthropicTransport,
    anthropic_transport,
)

SONNET_55 = "claude-sonnet-5-5"


def _read_jsonl(path: str) -> list[dict[str, object]]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _no_secrets_or_prompt_text(row: dict[str, object], *, forbidden_substrings: list[str]) -> None:
    blob = json.dumps(row)
    for bad in ("api_key", "x-api-key", "Authorization", "anthropic_api_key", "sk-test-fake"):
        assert bad not in blob, f"log row leaked secret-shaped field: {bad!r} in {blob!r}"
    for needle in forbidden_substrings:
        assert needle not in blob, f"log row leaked raw prompt text: {needle!r} in {blob!r}"


# ---------------------------------------------------------------------------
# Full run: agent_turn + likert_round_end, via the real orchestrator entry point
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_turn_and_likert_send_thinking_effort_and_respect_floors(
    tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> None:
    db_path = os.path.join(str(tmp_path), "run.sqlite")
    await init_db(db_path)
    sim_id = await create_simulation_run(
        db_path,
        name="M3 sonnet55 run",
        scenario_id="fsbb_comparator",
        status="pending",
        total_rounds=1,
        random_seed=99,
        prompt_version="v0",
        model_used="anthropic:" + SONNET_55,
    )
    log_path = llm_request_log_path(str(tmp_path), sim_id)

    await orchestrator.run_simulation_task(
        sqlite_path=db_path,
        simulation_id=sim_id,
        scenario_id="fsbb_comparator",
        total_rounds=1,
        agent_limit=2,
        random_seed=99,
        prompt_version="v0",
        model_used="anthropic:" + SONNET_55,
        lmstudio_model="unused",
        lmstudio_base_url="http://127.0.0.1:9",
        llm_temperature=0.0,
        # Deliberately below every Sonnet-55 floor to prove the floor, not the
        # requested value, ends up on the wire.
        llm_max_tokens=64,
        working_memory_last_k=2,
        llm_provider="anthropic",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        peer_context_max_chars=800,
        rag_effective=False,
        embedding_model="unused",
        rag_top_k=2,
        rag_chunk_size=200,
        rag_chunk_overlap=40,
        rag_max_inject_chars=800,
        likert_self_report_enabled=True,
        transcript_dir=str(tmp_path),
        llm_request_log_path=log_path,
    )

    # --- every Anthropic wire call carried thinking + effort ---
    assert anthropic_transport.calls, "expected at least one Anthropic wire call"
    for call in anthropic_transport.calls:
        assert call.json["model"] == SONNET_55
        assert call.json["thinking"] == {"type": "between_tools"}
        assert call.json.get("output_config", {}).get("effort") == "medium"

    # --- request log: one row per request, fields match the real wire payload ---
    rows = _read_jsonl(log_path)
    assert len(rows) == len(anthropic_transport.calls)
    call_sites = {row.get("call_site") for row in rows}
    assert "agent_turn" in call_sites
    assert "likert_round_end" in call_sites

    for row, call in zip(rows, anthropic_transport.calls):
        assert row["model_id"] == call.json["model"]
        assert row["thinking"] == call.json.get("thinking")
        assert row["effort"] == call.json.get("output_config", {}).get("effort")
        assert row["max_tokens"] == call.json["max_tokens"]
        assert row["simulation_id"] == sim_id
        _no_secrets_or_prompt_text(row, forbidden_substrings=["[SYSTEM]", "[USER]"])

    # --- Sonnet-only max_tokens floors raised the requested 64 on the wire ---
    agent_turn_rows = [r for r in rows if r.get("call_site") == "agent_turn"]
    likert_rows = [r for r in rows if r.get("call_site") == "likert_round_end"]
    assert agent_turn_rows and all(r["max_tokens"] == SONNET_55_MAX_TOKENS_AGENT_TURN for r in agent_turn_rows)
    assert likert_rows and all(r["max_tokens"] == SONNET_55_MAX_TOKENS_LIKERT for r in likert_rows)


# ---------------------------------------------------------------------------
# importance scoring (per-turn and per-round batch) — direct call sites
# ---------------------------------------------------------------------------


def _extras(tmp_path: object, sim_id: str = "sim-importance") -> tuple[RunLLMExtras, str]:
    cfg = resolve_anthropic_request_config(model_id=SONNET_55, settings=Settings())
    log_path = os.path.join(str(tmp_path), f"{sim_id}_llm_requests.jsonl")
    logger_ = LLMRequestLogger(path=log_path, simulation_id=sim_id)
    return RunLLMExtras(anthropic_config=cfg, request_logger=logger_), log_path


@pytest.mark.asyncio
async def test_importance_per_turn_sends_thinking_effort_and_respects_floor(
    tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> None:
    extras, log_path = _extras(tmp_path)
    await score_turn_importance(
        raw_response="Agent spoke about budget concerns.",
        round_number=1,
        turn_index=1,
        agent_name="Agent A",
        agent_role="teacher",
        prompt_version="v1",
        llm_temperature=0.0,
        llm_max_tokens=64,  # below the 512 floor
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        openai_compatible_api_key="",
        routing_policy="frontier_only",
        routing_profile_local_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        routing_profile_frontier_id=ANTHROPIC_DEFAULT_ID,
        run_llm_extras=extras,
    )
    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["thinking"] == {"type": "between_tools"}
    assert payload.get("output_config", {}).get("effort") == "medium"
    assert payload["max_tokens"] == SONNET_55_MAX_TOKENS_IMPORTANCE

    rows = _read_jsonl(log_path)
    assert len(rows) == 1
    assert rows[0]["max_tokens"] == SONNET_55_MAX_TOKENS_IMPORTANCE
    _no_secrets_or_prompt_text(rows[0], forbidden_substrings=["Agent spoke about budget concerns."])


@pytest.mark.asyncio
async def test_importance_batch_sends_thinking_effort_and_respects_floor(
    tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> None:
    extras, log_path = _extras(tmp_path, sim_id="sim-importance-batch")
    await score_round_importance_batch(
        round_number=1,
        turns=[
            {"turn_id": "t1", "agent_name": "Agent A", "raw_response": "Spoke about budget."},
            {"turn_id": "t2", "agent_name": "Agent B", "raw_response": "Spoke about staffing."},
        ],
        prompt_version="v1",
        llm_temperature=0.0,
        llm_max_tokens=64,  # below the 1536 batch floor
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        openai_compatible_api_key="",
        routing_policy="frontier_only",
        routing_profile_local_id=LOCAL_LMSTUDIO_DEFAULT_ID,
        routing_profile_frontier_id=ANTHROPIC_DEFAULT_ID,
        run_llm_extras=extras,
    )
    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["thinking"] == {"type": "between_tools"}
    assert payload.get("output_config", {}).get("effort") == "medium"
    assert payload["max_tokens"] == SONNET_55_MAX_TOKENS_IMPORTANCE_BATCH

    rows = _read_jsonl(log_path)
    assert len(rows) == 1
    assert rows[0]["max_tokens"] == SONNET_55_MAX_TOKENS_IMPORTANCE_BATCH


# ---------------------------------------------------------------------------
# reflection — direct call site
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reflection_sends_thinking_effort_and_respects_floor(
    tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> None:
    extras, log_path = _extras(tmp_path, sim_id="sim-reflection")
    observations = [
        PendingObservation(
            turn_id="t1", importance_score=8, raw_response="Important budget concern.", round_number=1, turn_index=1
        ),
    ]
    await synthesize_reflection(
        agent_name="Agent A",
        agent_role="teacher",
        round_number=1,
        observations=observations,
        prompt_version="v1",
        llm_temperature=0.0,
        llm_max_tokens=64,  # below the 1024 floor
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        openai_compatible_api_key="",
        routing_policy="frontier_only",
        run_llm_extras=extras,
    )
    assert len(anthropic_transport.calls) == 1
    payload = anthropic_transport.calls[0].json
    assert payload["thinking"] == {"type": "between_tools"}
    assert payload.get("output_config", {}).get("effort") == "medium"
    assert payload["max_tokens"] == SONNET_55_MAX_TOKENS_REFLECTION

    rows = _read_jsonl(log_path)
    assert len(rows) == 1
    assert rows[0]["max_tokens"] == SONNET_55_MAX_TOKENS_REFLECTION


# ---------------------------------------------------------------------------
# Ad-hoc log: calls outside a queued run go to adhoc_requests.jsonl
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adhoc_call_without_run_context_logs_to_adhoc_file(
    tmp_path: object, anthropic_transport: FakeAnthropicTransport
) -> None:
    settings = Settings(
        llm_request_log_dir=str(tmp_path / "adhoc_logs"),
        anthropic_model=SONNET_55,
        anthropic_api_key="sk-test-fake",
    )
    await llm_complete(
        provider="anthropic",
        messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}],
        temperature=0.0,
        max_tokens=256,
        lmstudio_base_url="http://127.0.0.1:9",
        lmstudio_model="unused",
        anthropic_api_key="sk-test-fake",
        anthropic_model=SONNET_55,
        llm_request_logger=None,  # no run logger -> must fall back to adhoc
        settings=settings,
        llm_call_site="analyze_simulation",
    )
    expected_path = adhoc_llm_request_log_path(settings)
    assert expected_path == os.path.join(str(tmp_path / "adhoc_logs"), "adhoc_requests.jsonl")
    rows = _read_jsonl(expected_path)
    assert len(rows) == 1
    assert rows[0]["simulation_id"] == "adhoc"
    assert rows[0]["model_id"] == SONNET_55
