"""Shared kwargs for memory-context integration tests."""

from __future__ import annotations

import json
from typing import Any

from mirofish_backend.llm.router import LLMCompletion


async def fake_llm_state_block(**kwargs: Any) -> LLMCompletion:
    state = {
        "support_level": 0.5,
        "resistance_level": 0.5,
        "workload_stress": 0.5,
        "belief_posture": "neutral",
        "perceived_conflict": False,
    }
    return LLMCompletion(
        text="Stub.\n\n<state>\n" + json.dumps(state) + "\n</state>",
        input_tokens=10,
        output_tokens=10,
    )


def memory_context_run_kwargs(
    *,
    agent_limit: int = 2,
    total_rounds: int = 2,
    llm_concurrency_cap: int = 1,
) -> dict[str, Any]:
    """Tier-1 simulation kwargs so inclusion logging runs (tier 3 skips it)."""
    return {
        "scenario_id": "psle_reform_mvp",
        "total_rounds": total_rounds,
        "agent_limit": agent_limit,
        "prompt_version": "v0",
        "model_used": "lmstudio:local",
        "lmstudio_model": "local-test",
        "lmstudio_base_url": "http://127.0.0.1:9",
        "llm_temperature": 0.0,
        "llm_max_tokens": 256,
        "working_memory_last_k": 2,
        "llm_provider": "lmstudio",
        "anthropic_api_key": "",
        "anthropic_model": "unused",
        "peer_context_max_chars": 800,
        "rag_effective": False,
        "embedding_model": "unused",
        "rag_top_k": 2,
        "rag_chunk_size": 200,
        "rag_chunk_overlap": 40,
        "rag_max_inject_chars": 800,
        "fidelity_tiers": [1] * agent_limit,
        "llm_concurrency_cap": llm_concurrency_cap,
    }
