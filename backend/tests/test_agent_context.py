from mirofish_backend.simulation.agent_context import (
    AGENT_CONTEXT_VERSION,
    attribute_sections_for_snapshot,
    build_agent_context_v1,
)


def test_agent_context_v1_version_and_prompt_projection() -> None:
    ctx = build_agent_context_v1(
        slot_index=2,
        demographics={"age": 40, "sex": "female", "ethnicity": "Chinese", "ses": "middle"},
        group_ids=("leadership",),
        identity={"nationality": "SG"},
        attitudes={"stance": "neutral"},
        personal_history={"years": 5},
    )
    assert ctx.version == AGENT_CONTEXT_VERSION
    assert ctx.slot_index == 2
    assert ctx.group_ids == ("leadership",)
    assert ctx.to_prompt_demographics() == ctx.demographics
    assert ctx.identity["nationality"] == "SG"
    snap = attribute_sections_for_snapshot(ctx)
    assert snap["identity"]["nationality"] == "SG"
    assert snap["attitudes"]["stance"] == "neutral"
