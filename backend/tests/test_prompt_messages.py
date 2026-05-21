from mirofish_backend.llm.prompt_templates import build_system_prompt, build_user_prompt


def test_prompt_has_system_message_shape() -> None:
    system = build_system_prompt(
        scenario_id="psle_reform_mvp",
        role="principal",
        name="Principal",
        style_cues="Formal.",
        beliefs={"k": 1},
        demographics={"age": 40},
        state={
            "support_level": 0.5,
            "resistance_level": 0.3,
            "workload_stress": 0.4,
            "belief_posture": "strategic_support",
        },
        prompt_version="v1",
    )
    user = build_user_prompt(
        round_number=1,
        policy_event="Test event",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="policy_update",
        prior_agent_memory=[],
        recent_interactions=[],
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    assert messages[0]["role"] == "system"
    assert "Principal" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "<state>" in messages[1]["content"]
    assert "Earlier simulation rounds" not in messages[1]["content"]


def test_system_prompt_includes_optional_profiles() -> None:
    system = build_system_prompt(
        scenario_id="psle_reform_mvp",
        role="principal",
        name="Principal",
        style_cues="Formal.",
        beliefs={"k": 1},
        demographics={"age": 40},
        state={
            "support_level": 0.5,
            "resistance_level": 0.3,
            "workload_stress": 0.4,
            "belief_posture": "strategic_support",
        },
        prompt_version="v1",
        psychological_profile={"trait_x": 0.2},
        implementation_profile={"band": "G2"},
    )
    assert "Psychological profile" in system
    assert "trait_x" in system
    assert "Implementation profile" in system
    assert "band" in system


def test_system_prompt_includes_structured_attribute_sections() -> None:
    system = build_system_prompt(
        scenario_id="psle_reform_mvp",
        role="principal",
        name="Principal",
        style_cues="Formal.",
        beliefs={"k": 1},
        demographics={"age": 40},
        state={
            "support_level": 0.5,
            "resistance_level": 0.3,
            "workload_stress": 0.4,
            "belief_posture": "strategic_support",
        },
        prompt_version="v1",
        identity={"gender_identity": "woman"},
        attitudes={"policy_stance": "cautious"},
        personal_history={"years_in_role": 8},
    )
    assert "Identity (structured attributes)" in system
    assert "gender_identity" in system
    assert "Attitudes / stance (structured)" in system
    assert "Personal history (structured)" in system


def test_prompt_round_two_includes_evolution_instruction() -> None:
    user = build_user_prompt(
        round_number=2,
        policy_event="Round 2 policy",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="policy_update",
        prior_agent_memory=["My round 1 line"],
        recent_interactions=[
            {
                "round_number": 1,
                "turn_index": 2,
                "agent_id": "other",
                "agent_name": "HoD",
                "interaction_type": "reply",
                "target_scope": "agent",
                "target_agent_name": "Principal",
                "raw_response": "We need phased rollout.",
            }
        ],
    )
    assert "Earlier simulation rounds" in user
    assert "[Round 1, turn 2]" in user
    assert "HoD" in user


def test_user_prompt_prior_round_summaries_block() -> None:
    user = build_user_prompt(
        round_number=2,
        policy_event="Round 2 policy",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="policy_update",
        prior_agent_memory=[],
        recent_interactions=[],
        round_summaries=['[Round 1 — intro] A: support=0.1, resistance=0.2, posture=x — "Hi"'],
    )
    assert "Prior rounds" in user
    assert "Current round — what others have said so far" in user
    assert "compact summaries" in user
