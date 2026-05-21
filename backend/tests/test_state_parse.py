import json

from mirofish_backend.llm.state_parse import (
    extract_all_state_blocks,
    extract_state_json_block,
    resolve_state_from_response,
    try_parse_state_from_response,
)


def test_extract_state_json_block_finds_tag() -> None:
    raw = 'Hello.\n\n<state>\n{"support_level": 0.8}\n</state>'
    inner = extract_state_json_block(raw)
    assert inner is not None
    assert '"support_level"' in inner


def test_extract_all_state_blocks_duplicate() -> None:
    raw = (
        '<state>{"support_level": 0.1}</state>\n'
        'text\n'
        '<state>{"support_level": 0.9, "resistance_level": 0.1, '
        '"workload_stress": 0.2, "belief_posture": "supportive"}</state>'
    )
    blocks = extract_all_state_blocks(raw)
    assert len(blocks) == 2


def test_structured_state_overrides_previous_scalars() -> None:
    raw = (
        "Message.\n<state>\n"
        + json.dumps(
            {
                "support_level": 0.77,
                "resistance_level": 0.22,
                "workload_stress": 0.33,
                "belief_posture": "supportive",
                "perceived_conflict": False,
            }
        )
        + "\n</state>"
    )
    out = try_parse_state_from_response(
        raw,
        support_level=0.1,
        resistance_level=0.9,
        workload_stress=0.9,
        belief_posture="old",
    )
    assert out is not None
    s, r, w, posture, conflict = out
    assert s == 0.77
    assert r == 0.22
    assert w == 0.33
    assert posture == "supportive"
    assert conflict is False


def test_resolve_state_model_parsed_provenance() -> None:
    raw = "OK.\n<state>\n" + json.dumps({"support_level": 0.6}) + "\n</state>"
    values, source = resolve_state_from_response(
        raw,
        support_level=0.5,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="neutral",
    )
    assert values is not None
    assert source == "model_parsed"


def test_resolve_state_repaired_trailing_comma() -> None:
    raw = "OK.\n<state>\n{\"support_level\": 0.8,}\n</state>"
    values, source = resolve_state_from_response(
        raw,
        support_level=0.5,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="neutral",
    )
    assert values is not None
    assert values[0] == 0.8
    assert source == "repaired"


def test_resolve_state_repaired_duplicate_blocks() -> None:
    raw = (
        '<state>{"support_level": 0.1}</state>'
        '<state>{"support_level": 0.85, "resistance_level": 0.1, '
        '"workload_stress": 0.2, "belief_posture": "supportive"}</state>'
    )
    values, source = resolve_state_from_response(
        raw,
        support_level=0.5,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="neutral",
    )
    assert values is not None
    assert values[0] == 0.85
    assert source == "repaired"


def test_resolve_state_keyword_fallback_when_missing_block() -> None:
    values, source = resolve_state_from_response(
        "No structured block here.",
        support_level=0.5,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="neutral",
    )
    assert values is None
    assert source == "keyword_fallback"


def test_resolve_state_keyword_fallback_invalid_json() -> None:
    raw = "OK.\n<state>\nnot json at all\n</state>"
    values, source = resolve_state_from_response(
        raw,
        support_level=0.5,
        resistance_level=0.5,
        workload_stress=0.5,
        belief_posture="neutral",
    )
    assert values is None
    assert source == "keyword_fallback"


def test_state_update_uses_structured_output_in_orchestrator_path() -> None:
    """Regression: orchestrator prefers <state> JSON when present (via try_parse)."""
    from mirofish_backend.simulation.orchestrator import AgentState, _apply_state_from_response

    prev = AgentState(0.5, 0.5, 0.5, "mixed")
    raw = (
        "We are aligned.\n<state>\n"
        + json.dumps(
            {
                "support_level": 0.91,
                "resistance_level": 0.05,
                "workload_stress": 0.2,
                "belief_posture": "supportive",
                "perceived_conflict": False,
            }
        )
        + "\n</state>"
    )
    new_state, conflict, source = _apply_state_from_response(prev, raw)
    assert new_state.support_level == 0.91
    assert new_state.resistance_level == 0.05
    assert conflict is False
    assert source == "model_parsed"


def test_keyword_fallback_when_no_state_block() -> None:
    from mirofish_backend.simulation.orchestrator import AgentState, _apply_state_from_response

    prev = AgentState(0.5, 0.5, 0.5, "mixed")
    raw = "We support alignment and are ready to implement."
    new_state, _conflict, source = _apply_state_from_response(prev, raw)
    assert new_state.support_level > prev.support_level
    assert source == "keyword_fallback"
