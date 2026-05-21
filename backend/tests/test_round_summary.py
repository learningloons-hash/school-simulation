from mirofish_backend.llm.round_summary import build_round_summary


def test_build_round_summary_with_state():
    turns = [
        {
            "agent_name": "Principal_Lim",
            "agent_role": "school_principal",
            "raw_response": 'The banding approach aligns with MOE direction.\n<state>\n{"support_level":0.72,"resistance_level":0.21,"workload_stress":0.30,"belief_posture":"cautiously_supportive","perceived_conflict":false}\n</state>',
        },
        {
            "agent_name": "Parent_Rep",
            "agent_role": "parent_representative",
            "raw_response": "Parents are not ready for this change.",
        },
    ]
    result = build_round_summary(round_number=1, policy_event="PSLE banding rollout", turns=turns)
    assert "Round 1" in result
    assert "Principal_Lim" in result
    assert "support=0.72" in result
    assert "Parent_Rep" in result
    assert "support=?" in result


def test_build_round_summary_empty_turns():
    result = build_round_summary(round_number=3, policy_event="No speakers", turns=[])
    assert "Round 3" in result
