from mirofish_backend.scenarios.registry import get_scenario


def test_psle_yaml_loads_three_personas() -> None:
    cfg = get_scenario("psle_reform_mvp")
    assert cfg.scenario_id == "psle_reform_mvp"
    assert len(cfg.personas) == 3
    roles = {p.role for p in cfg.personas}
    assert roles == {"principal", "middle_manager", "teacher"}
    assert 1 in cfg.policy_events
    assert 5 in cfg.policy_events
    assert cfg.rag_enabled is False
    principal = cfg.personas[0]
    assert principal.psychological_profile.get("cognitive_style") == "integrative_strategic"
    assert principal.implementation_profile.get("change_posture") == "phased_governance"


def test_fsbb_yaml_has_rag_and_corpus() -> None:
    cfg = get_scenario("fsbb_comparator")
    assert cfg.scenario_id == "fsbb_comparator"
    assert cfg.rag_enabled is True
    assert "corpus/fsbb_comparator/brief.txt" in cfg.rag_corpus_paths
    assert len(cfg.personas) == 3
    assert 1 in cfg.policy_events
    assert 5 in cfg.policy_events
    gids = {g.group_id for g in cfg.groups}
    assert gids == {"leadership", "teaching_staff"}
    assert cfg.personas[0].groups == ("leadership",)
    assert cfg.personas[2].groups == ("teaching_staff",)
