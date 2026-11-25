"""
M-ROSTER independent tester — acceptance gap-fill (spec §12 A1/A4, B1–B3, C2/C5/C6,
D1/D3, E1–E3, F1/F3, G, I1/I2).

Complements test_m_roster_unit.py / test_m_roster_sim.py / test_m_roster_preflight.py.
LLM mocked via senna_backend.simulation.orchestrator.llm_complete; embeddings mocked.
Synthetic data only.
"""

from __future__ import annotations

import dataclasses
import io
import json
import os
import re
import zipfile
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
import yaml
from fastapi.testclient import TestClient

from senna_backend.db.repo import (
    create_simulation_run,
    get_simulation_export_bundle,
    get_simulation_status_with_transcript,
)
from senna_backend.db.schema import init_db
from senna_backend.export_bundle import build_export_zip
from senna_backend.llm.model_profiles import LOCAL_LMSTUDIO_DEFAULT_ID
from senna_backend.llm.router import LLMCompletion
from senna_backend.main import app
from senna_backend.roster.csv_roster import parse_roster_csv
from senna_backend.scenarios.registry import get_scenario, scenario_from_mapping
from senna_backend.scenarios.serialize import scenario_config_to_document
from senna_backend.scenarios.validate import validate_scenario_document
from senna_backend.simulation import orchestrator
from senna_backend.simulation.roster_windows import resolve_activity_windows

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEMO_YAML = _REPO_ROOT / "docs" / "examples" / "m_roster_windows_demo.yaml"

_HANDOVER_HEADER = "Handover note (given to you on joining; only you can see this):"
_LIKERT_JSON = json.dumps({"support": 3, "resistance": 2, "workload_stress": 4})

# ---------------------------------------------------------------------------
# Synthetic 5-actor scenario builder
# ---------------------------------------------------------------------------

_LETTERS = ["a", "b", "c", "d", "e"]
_ROLE_LEVEL = {"a": 1, "b": 2, "c": 3, "d": 2, "e": 3}
_SUPPORT = {"a": 0.8, "b": 0.6, "c": 0.2, "d": 0.7, "e": 0.5}


def aid(letter: str) -> str:
    return f"teacher_{letter}_{_LETTERS.index(letter):03d}"


def _scenario(
    *,
    rounds: int,
    windows: dict[str, tuple[int | None, int | None, str]] | None = None,
    roster_windows: dict[str, Any] | None = None,
    likert: bool = False,
    letters: list[str] | None = None,
    scenario_id: str = "m_roster_acc",
) -> Any:
    letters = letters or _LETTERS
    windows = windows or {}
    personas = []
    for L in letters:
        p: dict[str, Any] = {
            "persona_id": f"teacher_{L}",
            "role": f"Role {L.upper()}",
            "name": f"Teacher {L.upper()}",
            "role_level": _ROLE_LEVEL[L],
            "style_cues": "Synthetic.",
            "beliefs": {"support_policy": 0.5},
            "initial_state": {
                "support_level": _SUPPORT[L],
                "resistance_level": 0.3,
                "workload_stress": 0.5,
                "belief_posture": "neutral",
            },
        }
        if L in windows:
            f, u, reason = windows[L]
            if f is not None:
                p["active_from_round"] = f
            if u is not None:
                p["active_until_round"] = u
            if reason:
                p["absence_reason"] = reason
        personas.append(p)
    raw: dict[str, Any] = {
        "scenario_id": scenario_id,
        "name": "M-ROSTER acceptance synthetic",
        "policy_events": {str(r): f"Policy event for round {r}." for r in range(1, rounds + 1)},
        "personas": personas,
    }
    if roster_windows is not None:
        raw["roster_windows"] = roster_windows
    if likert:
        six = ["SD", "D", "sD", "sA", "A", "SA"]
        raw["likert_self_report_enabled"] = True
        raw["likert_anchor_labels"] = {"support": six, "resistance": six, "workload_stress": six}
    return scenario_from_mapping(raw)


def _fake_llm(calls: list[dict], *, support_override: dict[str, float] | None = None) -> Any:
    support_override = support_override or {}

    async def fake(*, messages: list[dict], llm_request_context: dict | None = None, **kw: Any) -> LLMCompletion:
        ctx = dict(llm_request_context or {})
        calls.append({"messages": [dict(m) for m in messages], "context": ctx})
        if ctx.get("call_site") == "likert_round_end":
            return LLMCompletion(text=f"<likert>{_LIKERT_JSON}</likert>", input_tokens=5, output_tokens=5)
        a = str(ctx.get("agent_id", "?"))
        rn = ctx.get("round_number", 0)
        try:
            slot = int(a.split("_")[-1])
        except ValueError:
            slot = 0
        support = support_override.get(a, _SUPPORT.get(_LETTERS[slot] if slot < 5 else "a", 0.5))
        state = {
            "support_level": support,
            "resistance_level": 0.3,
            "workload_stress": 0.5,
            "belief_posture": "neutral",
            "perceived_conflict": False,
        }
        return LLMCompletion(
            text=f"Response. SENTINEL-r{rn}-a{a}\n\n<state>\n{json.dumps(state)}\n</state>",
            input_tokens=10,
            output_tokens=10,
        )

    return fake


async def _run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    scenario: Any,
    *,
    rounds: int,
    agent_limit: int | None = None,
    tag: str = "run",
    support_override: dict[str, float] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    calls: list[dict] = []
    monkeypatch.setattr(
        "senna_backend.simulation.orchestrator.llm_complete",
        _fake_llm(calls, support_override=support_override),
    )
    n = agent_limit if agent_limit is not None else len(scenario.personas)
    db = str(tmp_path / f"{tag}.sqlite")
    tdir = str(tmp_path / f"transcripts_{tag}")
    await init_db(db)
    seed = int(extra.pop("random_seed", 42))
    sim_id = await create_simulation_run(
        db, name=tag, scenario_id=scenario.scenario_id, status="pending",
        total_rounds=rounds, random_seed=seed, prompt_version="v0", model_used="fake",
    )
    kw: dict[str, Any] = dict(
        sqlite_path=db, simulation_id=sim_id, scenario_id=scenario.scenario_id,
        scenario_config=scenario, total_rounds=rounds, agent_limit=n, random_seed=seed,
        prompt_version="v0", model_used="fake", lmstudio_model="fake",
        lmstudio_base_url="http://unused", llm_temperature=0.0, llm_max_tokens=256,
        working_memory_last_k=2, llm_provider="lmstudio", anthropic_api_key="",
        anthropic_model="unused", peer_context_max_chars=4000, rag_effective=False,
        embedding_model="unused", rag_top_k=4, rag_chunk_size=400, rag_chunk_overlap=80,
        rag_max_inject_chars=2400, round_summary_enabled=True, transcript_dir=tdir,
        llm_concurrency_cap=1,
    )
    kw.update(extra)
    await orchestrator.run_simulation_task(**kw)
    status = await get_simulation_status_with_transcript(db, simulation_id=sim_id)
    assert status["status"] == "completed", status
    bundle = await get_simulation_export_bundle(db, simulation_id=sim_id)
    tpath = os.path.join(tdir, f"{sim_id}.md")
    transcript = open(tpath, encoding="utf-8").read() if os.path.exists(tpath) else None
    return {
        "db": db, "sim_id": sim_id, "calls": calls, "status": status,
        "bundle": bundle, "transcript": transcript,
    }


def _turn_calls(calls: list[dict], agent: str | None = None, rnd: int | None = None) -> list[dict]:
    return [
        c for c in calls
        if c["context"].get("call_site") == "agent_turn"
        and (agent is None or c["context"].get("agent_id") == agent)
        and (rnd is None or c["context"].get("round_number") == rnd)
    ]


def _user(c: dict) -> str:
    return c["messages"][-1]["content"]


def _pre_round_sentinels(text: str, before: int) -> list[str]:
    return [m for m in re.findall(r"SENTINEL-r(\d+)-a", text) if int(m) < before]


async def _rows(db: str, sql: str, params: tuple) -> list[tuple]:
    async with aiosqlite.connect(db) as conn:
        cur = await conn.execute(sql, params)
        return list(await cur.fetchall())


# ---------------------------------------------------------------------------
# A1 — byte-identical default (full contract)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_a1_full_windows_identical_to_no_windows(monkeypatch, tmp_path) -> None:
    """A1: built-in scenario vs same scenario with every actor windowed 1..R."""
    rounds, n = 3, 3
    six = ("SD", "D", "sD", "sA", "A", "SA")
    base = dataclasses.replace(
        get_scenario("psle_reform_mvp"),
        likert_anchor_labels={"support": six, "resistance": six, "workload_stress": six},
    )
    win_personas = [
        dataclasses.replace(p, active_from_round=1, active_until_round=rounds) for p in base.personas
    ]
    windowed = dataclasses.replace(base, personas=type(base.personas)(win_personas))

    common = dict(rounds=rounds, agent_limit=n, likert_self_report_enabled=True)
    r0 = await _run(monkeypatch, tmp_path, base, tag="a1_base", **common)
    r1 = await _run(monkeypatch, tmp_path, windowed, tag="a1_win", **common)

    def seq(r: dict) -> list[tuple]:
        return [
            (t["round_number"], t["turn_index"], t["agent_id"], t["interaction_type"], t.get("target_agent_id"))
            for t in r["status"]["transcript"]
        ]

    assert seq(r0) == seq(r1)
    assert len(seq(r0)) > 0

    def prompts(r: dict) -> list[tuple]:
        return [
            (c["context"].get("call_site"), tuple((m["role"], m["content"]) for m in c["messages"]))
            for c in r["calls"]
        ]

    assert prompts(r0) == prompts(r1), "system/user prompt strings differ"

    def gstate(r: dict) -> list[dict]:
        drop = {"id", "simulation_id", "created_at"}
        return [{k: v for k, v in g.items() if k not in drop} for g in r["bundle"]["global_state_snapshots"]]

    assert gstate(r0) == gstate(r1)

    n0 = (await _rows(r0["db"], "SELECT COUNT(*) FROM agent_round_likert WHERE simulation_id=?", (r0["sim_id"],)))[0][0]
    n1 = (await _rows(r1["db"], "SELECT COUNT(*) FROM agent_round_likert WHERE simulation_id=?", (r1["sim_id"],)))[0][0]
    assert n0 == n1 and n0 > 0

    cfg0 = r0["status"]["config_snapshot"] or {}
    cfg1 = r1["status"]["config_snapshot"] or {}
    assert set(cfg0) == set(cfg1)
    assert "roster_windows" not in cfg1 and "roster_window_audit" not in cfg1

    def norm(t: str, sim_id: str) -> list[str]:
        return [ln for ln in t.replace(sim_id, "<SIM>").splitlines() if "UTC" not in ln]

    assert r0["transcript"] is not None and r1["transcript"] is not None
    assert norm(r0["transcript"], r0["sim_id"]) == norm(r1["transcript"], r1["sim_id"])

    z0 = zipfile.ZipFile(io.BytesIO(build_export_zip(r0["bundle"]))).namelist()
    z1 = zipfile.ZipFile(io.BytesIO(build_export_zip(r1["bundle"]))).namelist()
    assert z0 == z1
    assert "active_agents_per_round" not in r1["bundle"]


# ---------------------------------------------------------------------------
# A4 — roster-csv-template endpoint still parses
# ---------------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "api.sqlite"))
    with TestClient(app) as c:
        yield c


def test_a4_roster_csv_template_parses(client: TestClient) -> None:
    r = client.get("/simulations/roster-csv-template")
    assert r.status_code == 200
    text = r.text
    for col in ("active_from_round", "active_until_round", "absence_reason", "window_basis"):
        assert col in text.splitlines()[0]
    res = parse_roster_csv(text.strip(), agent_limit=4, scenario=get_scenario("psle_reform_mvp"))
    for row in res.by_slot.values():
        assert row.active_from_round is None and row.active_until_round is None


# ---------------------------------------------------------------------------
# B1–B3 — turns, sampling, order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_b1_window_3_to_4_in_six_rounds(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=6, windows={"c": (3, 4, "")}, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=6)
    rows = await _rows(r["db"], "SELECT DISTINCT round_number FROM agent_turns WHERE simulation_id=? AND agent_id=?",
                       (r["sim_id"], aid("c")))
    assert {x[0] for x in rows} == {3, 4}
    llm_rounds = {c["context"]["round_number"] for c in r["calls"] if c["context"].get("agent_id") == aid("c")}
    assert llm_rounds == {3, 4}, f"LLM calls for windowed actor outside 3..4: {llm_rounds}"


_FIVE_WIN = {"b": (None, 2, "on leave"), "e": (4, None, "")}  # round 3: B and E inactive


@pytest.mark.asyncio
async def test_b2_sample_k_five_agents_two_inactive(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=5, windows=_FIVE_WIN)
    extra = dict(simulation_mode="sample_k_per_round", speakers_per_round=2, random_seed=7)
    r1 = await _run(monkeypatch, tmp_path, sc, rounds=5, tag="b2a", **extra)
    r2 = await _run(monkeypatch, tmp_path, sc, rounds=5, tag="b2b", **extra)
    t1 = r1["status"]["transcript"]
    for t in t1:
        rn = t["round_number"]
        if rn in (3, 4, 5):
            assert t["agent_id"] != aid("b")
        if rn in (1, 2, 3):
            assert t["agent_id"] != aid("e")
    r3_speakers = {t["agent_id"] for t in t1 if t["round_number"] == 3}
    assert len(r3_speakers) == 2 and r3_speakers <= {aid("a"), aid("c"), aid("d")}
    assert [(t["round_number"], t["agent_id"]) for t in t1] == [
        (t["round_number"], t["agent_id"]) for t in r2["status"]["transcript"]
    ]


@pytest.mark.asyncio
async def test_b3_hierarchical_full_order_among_active(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=5, windows=_FIVE_WIN)
    r = await _run(monkeypatch, tmp_path, sc, rounds=5, turn_order_policy="hierarchical")
    turns = r["status"]["transcript"]
    level = {aid(L): _ROLE_LEVEL[L] for L in _LETTERS}
    for rn in range(1, 6):
        order = [t["agent_id"] for t in sorted(
            (t for t in turns if t["round_number"] == rn), key=lambda t: t["turn_index"])]
        levels = [level[a] for a in order]
        assert levels == sorted(levels), f"round {rn} order {order} not by role_level"
    r3 = [t["agent_id"] for t in sorted((t for t in turns if t["round_number"] == 3), key=lambda t: t["turn_index"])]
    assert r3 == [aid("a"), aid("d"), aid("c")]
    active = {rn: {aid(L) for L in _LETTERS
                   if not (L == "b" and rn > 2) and not (L == "e" and rn < 4)} for rn in range(1, 6)}
    for t in turns:
        if t.get("target_agent_id"):
            assert t["target_agent_id"] in active[t["round_number"]], t


# ---------------------------------------------------------------------------
# C2 / C5 / C6 — newcomer information rule
# ---------------------------------------------------------------------------

_NEWCOMER_WIN = {"c": (3, None, "")}


@pytest.mark.asyncio
async def test_c2_newcomer_sees_round_j_summary_only(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=4)
    p4 = _user(_turn_calls(r["calls"], aid("c"), 4)[0])
    assert "Prior rounds — compact summaries" in p4
    assert "[Round 3 —" in p4
    assert "[Round 1 —" not in p4 and "[Round 2 —" not in p4
    assert f"SENTINEL-r3-a{aid('a')}" in p4
    assert _pre_round_sentinels(p4, 3) == []
    pa4 = _user(_turn_calls(r["calls"], aid("a"), 4)[0])
    assert "[Round 1 —" in pa4 and "[Round 2 —" in pa4


@pytest.mark.asyncio
async def test_c5_summary_breakdown_includes_pre_join(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=4)
    summary = r["bundle"]["memory_context_summary"]
    assert summary["exclusion_breakdown"].get("pre_join", 0) > 0
    pre_join_rows = [x for x in r["bundle"]["memory_context_log"] if x.get("exclusion_reason") == "pre_join"]
    assert pre_join_rows and all(x["observer_agent_id"] == aid("c") for x in pre_join_rows)


@pytest.mark.asyncio
async def test_c6_weighted_retrieval_excludes_pre_join(monkeypatch, tmp_path) -> None:
    async def fake_embed(*, texts: list[str], **kw: Any) -> list[list[float]]:
        return [[1.0, float(len(t) % 7), 0.5] for t in texts]

    monkeypatch.setattr("senna_backend.rag.memory_index.embed_texts_openai_compatible", fake_embed)
    monkeypatch.setattr("senna_backend.rag.embeddings.embed_texts_openai_compatible", fake_embed)
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"])
    r = await _run(
        monkeypatch, tmp_path, sc, rounds=4,
        weighted_retrieval_enabled=True, embedding_model="test-embed", lmstudio_model="local-test",
    )
    for rn in (3, 4):
        p = _user(_turn_calls(r["calls"], aid("c"), rn)[0])
        assert _pre_round_sentinels(p, 3) == [], f"weighted path leaked pre-J content in round {rn}"
    p3 = _user(_turn_calls(r["calls"], aid("c"), 3)[0])
    assert "Prior rounds — compact summaries" not in p3
    pa3 = _user(_turn_calls(r["calls"], aid("a"), 3)[0])
    assert _pre_round_sentinels(pa3, 3), "sanity: round-1 agent should still see pre-J peer turns"


# ---------------------------------------------------------------------------
# D1 / D3 / D4 — handover note
# ---------------------------------------------------------------------------

_TEMPLATE = "Welcome {name} ({role}). Join round {join_round} of {total_rounds}. Today: {join_policy_event} {{literal}}"


@pytest.mark.asyncio
async def test_d1_handover_exact_placement_and_nowhere_else(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"], likert=True,
                   roster_windows={"handover_template": _TEMPLATE})
    r = await _run(monkeypatch, tmp_path, sc, rounds=4, likert_self_report_enabled=True)
    rendered = "Welcome Teacher C (Role C). Join round 3 of 4. Today: Policy event for round 3. {literal}"
    p3 = _user(_turn_calls(r["calls"], aid("c"), 3)[0])
    assert f"Policy event: Policy event for round 3.\n{_HANDOVER_HEADER}\n{rendered}\n\n" in p3

    for c in r["calls"]:
        is_join = (c["context"].get("call_site") == "agent_turn" and c["context"].get("agent_id") == aid("c")
                   and c["context"].get("round_number") == 3)
        if is_join:
            continue
        for m in c["messages"]:
            assert _HANDOVER_HEADER not in m["content"] and rendered not in m["content"], c["context"]

    summaries = await _rows(r["db"], "SELECT summary_text FROM round_summaries WHERE simulation_id=?", (r["sim_id"],))
    assert summaries and all(rendered not in s[0] and "Handover note" not in s[0] for s in summaries)
    raws = await _rows(r["db"], "SELECT raw_response FROM agent_turns WHERE simulation_id=?", (r["sim_id"],))
    assert all(rendered not in (x[0] or "") and "Handover note" not in (x[0] or "") for x in raws)
    assert r["transcript"] and rendered not in r["transcript"] and "Handover note" not in r["transcript"]

    notes = r["status"]["config_snapshot"]["roster_windows"]["handover_notes"]
    assert notes == {aid("c"): rendered}


def _valid_doc(**rw: Any) -> dict[str, Any]:
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"], scenario_id="m_roster_user_doc")
    doc = scenario_config_to_document(sc)
    if rw:
        doc["roster_windows"] = rw
    return doc


def _validate(doc: dict[str, Any]) -> list[str]:
    errors, _warnings = validate_scenario_document(doc, is_update=False, allowed_corpus_paths=frozenset())
    return errors


def test_d3_validate_document_placeholders() -> None:
    assert _validate(_valid_doc()) == []
    assert _validate(_valid_doc(handover_template="Hi {name}, {{literal}} braces ok")) == []
    errs = _validate(_valid_doc(handover_template="Hi {nickname}"))
    assert any("roster_windows.handover_template: unknown placeholder {nickname}" in e for e in errs), errs
    assert any("handover_template" in e for e in _validate(_valid_doc(handover_template="Hi {}"))), "positional {}"


def test_d3_scenario_from_mapping_rejects_unknown_placeholder() -> None:
    """§5: unknown placeholder is an error in _scenario_from_mapping as well."""
    doc = _valid_doc(handover_template="Hi {nickname}")
    with pytest.raises(ValueError, match="unknown placeholder"):
        scenario_from_mapping(doc)


def test_d3_scenario_from_mapping_accepts_literal_braces() -> None:
    sc = scenario_from_mapping(_valid_doc(handover_template="Hi {name} {{literal}}"))
    assert sc.roster_windows is not None


# ---------------------------------------------------------------------------
# E1–E3 — absence notice in live prompts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e1_absence_notice_exact_roster_order(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=5, windows=_FIVE_WIN, roster_windows={"absence_notice_scope": "all_inactive"}, likert=True)
    r = await _run(monkeypatch, tmp_path, sc, rounds=5, likert_self_report_enabled=True)
    expected = {
        1: "Not present this round: Teacher E.",
        2: "Not present this round: Teacher E.",
        3: "Not present this round: Teacher B (on leave), Teacher E.",
        4: "Not present this round: Teacher B (on leave).",
        5: "Not present this round: Teacher B (on leave).",
    }
    for rn, line in expected.items():
        calls = _turn_calls(r["calls"], rnd=rn)
        assert calls
        for c in calls:
            p = _user(c)
            assert f"\n{line}\n" in p, (rn, p[:400])
            assert p.count("Not present this round:") == 1
    for c in r["calls"]:
        if c["context"].get("call_site") == "likert_round_end":
            assert "Not present this round" not in _user(c)
    summaries = await _rows(r["db"], "SELECT summary_text FROM round_summaries WHERE simulation_id=?", (r["sim_id"],))
    assert all("Not present this round" not in s[0] for s in summaries)
    assert "Not present this round" not in r["transcript"]


@pytest.mark.asyncio
async def test_e2_departed_only_and_none(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=5, windows=_FIVE_WIN, roster_windows={"absence_notice_scope": "departed_only"})
    r = await _run(monkeypatch, tmp_path, sc, rounds=5, tag="dep")
    for rn in (1, 2):
        assert all("Not present this round" not in _user(c) for c in _turn_calls(r["calls"], rnd=rn))
    for c in _turn_calls(r["calls"], rnd=3):
        assert "\nNot present this round: Teacher B (on leave).\n" in _user(c)

    sc2 = _scenario(rounds=5, windows=_FIVE_WIN, roster_windows={"absence_notice_scope": "none"})
    r2 = await _run(monkeypatch, tmp_path, sc2, rounds=5, tag="none")
    assert all("Not present this round" not in _user(c) for c in _turn_calls(r2["calls"]))


@pytest.mark.asyncio
async def test_e3_no_notice_when_everyone_active(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=3, windows={"b": (None, 2, "away")}, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=3)
    for rn in (1, 2):
        assert all("Not present this round" not in _user(c) for c in _turn_calls(r["calls"], rnd=rn))
    assert all("Not present this round: Teacher B (away)." in _user(c) for c in _turn_calls(r["calls"], rnd=3))


# ---------------------------------------------------------------------------
# F1 / F3 — Likert series end, convergence_delta values
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_f1_leaver_likert_series_ends_at_until(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=5, windows=_FIVE_WIN, likert=True)
    r = await _run(monkeypatch, tmp_path, sc, rounds=5, likert_self_report_enabled=True)
    rows = await _rows(r["db"], "SELECT DISTINCT round_number, agent_id FROM agent_round_likert WHERE simulation_id=?",
                       (r["sim_id"],))
    by_agent: dict[str, set[int]] = {}
    for rn, a in rows:
        by_agent.setdefault(a, set()).add(rn)
    assert by_agent[aid("b")] == {1, 2}
    assert by_agent[aid("e")] == {4, 5}
    assert by_agent[aid("a")] == {1, 2, 3, 4, 5}


@pytest.mark.asyncio
async def test_f3_joiner_contributes_nothing_and_none_when_no_overlap(monkeypatch, tmp_path) -> None:
    # Joiner C's first-round state jumps far from its initial 0.2; A/B are static.
    sc = _scenario(rounds=4, windows=_NEWCOMER_WIN, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=4, support_override={aid("c"): 0.95})
    gs = {g["round_number"]: g for g in r["bundle"]["global_state_snapshots"]}
    c3 = await _rows(r["db"], "SELECT support_level FROM agent_state_snapshots WHERE simulation_id=? AND agent_id=? "
                     "AND round_number=3", (r["sim_id"], aid("c")))
    assert c3 and abs(c3[0][0] - 0.2) > 0.05, "sanity: joiner state moved in join round"
    assert gs[3]["convergence_delta"] is not None
    assert abs(gs[3]["convergence_delta"]) < 1e-9, "joiner's first round leaked into convergence_delta"

    sc2 = _scenario(rounds=2, windows={"a": (1, 1, ""), "b": (2, 2, "")}, letters=["a", "b"])
    r2 = await _run(monkeypatch, tmp_path, sc2, rounds=2, tag="f3none")
    gs2 = {g["round_number"]: g for g in r2["bundle"]["global_state_snapshots"]}
    assert gs2[2].get("convergence_delta") is None  # export omits the key when NULL


# ---------------------------------------------------------------------------
# G — validation table §5, roster CSV (HTTP) and scenario YAML
# ---------------------------------------------------------------------------

def _post(client: TestClient, path: str, roster_csv: str, rounds: int = 4, n: int = 4):
    return client.post(path, json={
        "scenario_id": "psle_reform_mvp", "total_rounds": rounds, "agent_limit": n,
        "model_profile_id": LOCAL_LMSTUDIO_DEFAULT_ID, "roster_csv": roster_csv,
    })


@pytest.mark.parametrize("endpoint", ["/simulations/preflight", "/simulations/run"])
@pytest.mark.parametrize(
    ("csv_body", "needle"),
    [
        ("slot,active_from_round\n1,abc\n", "invalid active_from_round 'abc'"),
        ("slot,active_until_round\n1,x2\n", "invalid active_until_round 'x2'"),
        ("slot,active_from_round\n1,0\n", "active_from_round must be >= 1"),
        ("slot,active_until_round\n1,0\n", "active_until_round must be >= 1"),
        ("slot,active_from_round,active_until_round\n1,4,2\n", "active_from_round > active_until_round"),
        ("slot,active_from_round,active_until_round\n1,5,6\n", "starts after total_rounds=4"),
        ("slot,active_from_round,active_until_round\n1,1,1\n2,3,4\n3,3,4\n4,3,4\n", "round 2 has no active agents"),
    ],
)
def test_g_roster_csv_errors_422(client: TestClient, endpoint: str, csv_body: str, needle: str) -> None:
    r = _post(client, endpoint, csv_body)
    assert r.status_code == 422, r.text
    assert needle in r.text, r.text


def test_g_from_gt_r_with_default_until_gives_starts_after_message(client: TestClient) -> None:
    """§5 row 4: active_from_round > total_rounds (until left at default R) -> 'starts after total_rounds'."""
    r = _post(client, "/simulations/preflight", "slot,active_from_round\n1,5\n")
    assert r.status_code == 422, r.text
    assert "starts after total_rounds=4" in r.text, r.text


def test_g_roster_csv_clip_and_reason_warnings_preflight(client: TestClient) -> None:
    r = _post(client, "/simulations/preflight",
              "slot,active_from_round,active_until_round,absence_reason\n1,2,9,\n2,,,sick\n")
    assert r.status_code == 200, r.text
    w = r.json()["warnings"]
    assert any("clipped to total_rounds=4" in x for x in w), w
    assert any("absence_reason set but actor is active every round" in x for x in w), w


@pytest.mark.parametrize(
    ("field", "value", "needle"),
    [
        ("active_from_round", "two", "personas[2].active_from_round must be an integer"),
        ("active_until_round", 1.5, "personas[2].active_until_round must be an integer"),
        ("active_from_round", 0, "personas[2].active_from_round must be >= 1"),
        ("active_until_round", -1, "personas[2].active_until_round must be >= 1"),
    ],
)
def test_g_yaml_window_type_errors(field: str, value: Any, needle: str) -> None:
    doc = _valid_doc()
    doc["personas"][2][field] = value
    errs = _validate(doc)
    assert any(needle in e for e in errs), errs
    with pytest.raises(ValueError, match=re.escape(needle.split(".", 1)[1])):
        scenario_from_mapping(doc)


def test_g_yaml_from_gt_until() -> None:
    doc = _valid_doc()
    doc["personas"][2]["active_from_round"] = 4
    doc["personas"][2]["active_until_round"] = 2
    assert any("active_from_round > active_until_round" in e for e in _validate(doc))
    sc = scenario_from_mapping(doc)
    ids = [f"{p.persona_id}_{i:03d}" for i, p in enumerate(sc.personas)]
    with pytest.raises(ValueError, match="active_from_round > active_until_round"):
        resolve_activity_windows(ids, list(sc.personas), 4)


def test_g_yaml_resolve_errors_and_clip() -> None:
    def ids_personas(doc):
        sc = scenario_from_mapping(doc)
        return [f"{p.persona_id}_{i:03d}" for i, p in enumerate(sc.personas)], list(sc.personas)

    doc = _valid_doc()
    doc["personas"][2]["active_from_round"] = 6
    doc["personas"][2]["active_until_round"] = 7
    ids, ps = ids_personas(doc)
    with pytest.raises(ValueError, match=r"activity window for teacher_c_002 starts after total_rounds=4"):
        resolve_activity_windows(ids, ps, 4)

    doc = _valid_doc()
    for p in doc["personas"]:
        p["active_from_round"] = 2
    ids, ps = ids_personas(doc)
    with pytest.raises(ValueError, match="round 1 has no active agents"):
        resolve_activity_windows(ids, ps, 4)

    doc = _valid_doc()
    doc["personas"][0]["active_until_round"] = 10
    ids, ps = ids_personas(doc)
    windows, warnings = resolve_activity_windows(ids, ps, 4)
    assert windows["teacher_a_000"].active_until_round == 4
    assert "activity window for teacher_a_000 clipped to total_rounds=4" in warnings


def test_g_yaml_bad_absence_scope() -> None:
    doc = _valid_doc(absence_notice_scope="sometimes")
    assert any("absence_notice_scope" in e for e in _validate(doc))


def test_g_scenario_from_mapping_rejects_bad_absence_scope() -> None:
    """§5: absence_notice_scope outside the allowed set is an error in _scenario_from_mapping too."""
    with pytest.raises(ValueError, match="absence_notice_scope"):
        scenario_from_mapping(_valid_doc(absence_notice_scope="sometimes"))


# ---------------------------------------------------------------------------
# I1 / I2 — demo scenario export, transcript membership (windowed only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_i1_demo_scenario_active_agents_csv(monkeypatch, tmp_path) -> None:
    demo = scenario_from_mapping(yaml.safe_load(_DEMO_YAML.read_text(encoding="utf-8")))
    r = await _run(monkeypatch, tmp_path, demo, rounds=6, likert_self_report_enabled=True)
    zf = zipfile.ZipFile(io.BytesIO(build_export_zip(r["bundle"])))
    text = zf.read("active_agents_per_round.csv").decode("utf-8")
    lines = [ln.split(",") for ln in text.strip().splitlines()]
    assert lines[0] == ["round_number", "active_count", "active_agent_ids", "joined_agent_ids",
                        "left_agent_ids", "inactive_agent_ids"]
    rows = {int(x[0]): x for x in lines[1:]}
    a, b, c, d, e = (f"teacher_{L}_{i:03d}" for i, L in enumerate(_LETTERS))
    assert rows[1] == ["1", "4", "|".join([a, b, c, e]), "|".join([a, b, c, e]), "", d]
    assert rows[2] == ["2", "4", "|".join([a, b, c, e]), "", "", d]
    assert rows[3] == ["3", "5", "|".join([a, b, c, d, e]), d, "", ""]
    assert rows[4] == ["4", "5", "|".join([a, b, c, d, e]), "", "", ""]
    assert rows[5] == ["5", "4", "|".join([a, c, d, e]), "", b, b]
    assert rows[6] == ["6", "4", "|".join([a, c, d, e]), "", "", b]


@pytest.mark.asyncio
async def test_i2_membership_lines_windowed_only(monkeypatch, tmp_path) -> None:
    sc = _scenario(rounds=4, windows={"b": (None, 2, ""), "c": (3, None, "")}, letters=["a", "b", "c"])
    r = await _run(monkeypatch, tmp_path, sc, rounds=4, tag="win")
    t = r["transcript"]
    assert "| Name | Role | Active rounds |" in t
    assert "| Teacher B | Role B | 1–2 |" in t and "| Teacher C | Role C | 3–4 |" in t
    expected = {
        1: "*Active: Teacher A, Teacher B. Not present: Teacher C.*",
        3: "*Active: Teacher A, Teacher C. Not present: Teacher B.*",
    }
    for rn in range(1, 5):
        m = re.search(rf"^## Round {rn} — .*\n\s*(.*)\n", t, flags=re.M)
        assert m, f"no heading for round {rn}"
        assert m.group(1).startswith("*Active:"), f"round {rn} membership line missing: {m.group(1)!r}"
        if rn in expected:
            assert m.group(1) == expected[rn]

    sc0 = _scenario(rounds=2, letters=["a", "b", "c"])
    r0 = await _run(monkeypatch, tmp_path, sc0, rounds=2, tag="nowin")
    assert "Active rounds" not in r0["transcript"]
    assert "*Active:" not in r0["transcript"]
