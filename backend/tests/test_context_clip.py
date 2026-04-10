from mirofish_backend.llm.context_clip import (
    clip_recent_interactions,
    prepare_peer_response_for_prompt,
)


def test_strips_state_block() -> None:
    raw = "We agree.\n<state>\n{\"support_level\": 1}\n</state>"
    out = prepare_peer_response_for_prompt(raw, max_chars=500)
    assert "<state>" not in out
    assert "We agree" in out


def test_trims_after_draft_when_thinking_prefix() -> None:
    raw = "Thinking Process:\n\n1. Plan.\n\n**Draft:** We will align with MOE guidance."
    out = prepare_peer_response_for_prompt(raw, max_chars=500)
    assert "Thinking Process" not in out
    assert "We will align" in out


def test_tail_truncates_long_text() -> None:
    raw = "X" * 100 + "ENDMARKER"
    out = prepare_peer_response_for_prompt(raw, max_chars=20)
    assert "truncated" in out
    assert "ENDMARKER" in out


def test_clip_recent_interactions() -> None:
    rows = [
        {
            "round_number": 1,
            "turn_index": 1,
            "agent_id": "a_000",
            "agent_name": "A",
            "interaction_type": "broadcast",
            "target_scope": "all",
            "target_agent_name": "all",
            "raw_response": "Y" * 200,
        }
    ]
    clipped = clip_recent_interactions(rows, max_chars=30)
    assert len(clipped[0]["raw_response"]) < len(rows[0]["raw_response"])
