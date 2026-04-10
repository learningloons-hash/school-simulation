import pytest

from mirofish_backend.roster.csv_roster import (
    ParsedRosterRow,
    merge_persona_for_slot,
    parse_roster_csv,
    personas_for_run,
)
from mirofish_backend.scenarios.registry import get_scenario


def test_parse_roster_empty_returns_empty_slots() -> None:
    cfg = get_scenario("fsbb_comparator")
    r = parse_roster_csv("", agent_limit=3, scenario=cfg)
    assert r.by_slot == {}
    assert r.unknown_group_ids == ()


def test_parse_roster_merges_slot_and_flags_unknown_group() -> None:
    cfg = get_scenario("fsbb_comparator")
    csv_text = (
        "slot,persona_id,role,name,groups\n"
        "2,,,Renamed HOD,leadership\n"
        "3,,,,made_up_faction\n"
    )
    r = parse_roster_csv(csv_text, agent_limit=3, scenario=cfg)
    assert "made_up_faction" in r.unknown_group_ids
    personas = personas_for_run(cfg, 3, r.by_slot)
    assert personas[1].name == "Renamed HOD"
    assert personas[1].groups == ("leadership",)
    assert personas[2].groups == ("made_up_faction",)


def test_parse_roster_slot_out_of_range() -> None:
    cfg = get_scenario("psle_reform_mvp")
    with pytest.raises(ValueError, match="out of range"):
        parse_roster_csv("slot\n99\n", agent_limit=3, scenario=cfg)


def test_merge_persona_beliefs_overlay() -> None:
    cfg = get_scenario("psle_reform_mvp")
    base = cfg.personas[0]
    row = ParsedRosterRow(slot=1, beliefs={"trust_in_moe_policy": 0.99})
    merged = merge_persona_for_slot(base, row)
    assert merged.beliefs["trust_in_moe_policy"] == 0.99
    assert "risk_aversion" in merged.beliefs
