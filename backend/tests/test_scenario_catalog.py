import json

import pytest
from fastapi.testclient import TestClient

from mirofish_backend.db.repo import upsert_user_scenario
from mirofish_backend.db.schema import init_db
from mirofish_backend.main import app
from mirofish_backend.scenarios.loader import load_scenario_for_run
from mirofish_backend.scenarios.registry import get_scenario


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "api.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    with TestClient(app) as c:
        yield c


def _minimal_doc(sid: str = "analyst_test_scenario") -> dict:
    return {
        "scenario_id": sid,
        "name": "Analyst test",
        "policy_events": {"1": "Policy round 1 text."},
        "personas": [
            {
                "persona_id": "t1",
                "role": "teacher",
                "name": "Teacher One",
                "role_level": 3,
                "style_cues": "Concise.",
                "beliefs": {"k": 0.5},
            }
        ],
    }


def test_get_scenarios_includes_builtin(client: TestClient) -> None:
    r = client.get("/scenarios")
    assert r.status_code == 200
    data = r.json()
    ids = {x["id"]: x for x in data}
    assert "psle_reform_mvp" in ids
    assert ids["psle_reform_mvp"]["source"] == "builtin"


def test_post_scenario_then_list_and_run_resolution(client: TestClient) -> None:
    doc = _minimal_doc("analyst_acat")
    r = client.post("/scenarios", json={"document": doc})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "analyst_acat"
    r2 = client.get("/scenarios")
    row = next(x for x in r2.json() if x["id"] == "analyst_acat")
    assert row["source"] == "user"


@pytest.mark.asyncio
async def test_load_scenario_user_overrides_builtin(tmp_path, monkeypatch) -> None:
    db = tmp_path / "l.sqlite"
    monkeypatch.setenv("SQLITE_PATH", str(db))
    await init_db(str(db))
    base = get_scenario("psle_reform_mvp")
    doc = {
        "scenario_id": "psle_reform_mvp",
        "name": "Shadow PSLE",
        "policy_events": {1: "Custom only policy."},
        "personas": [
            {
                "persona_id": "principal_001",
                "role": "principal",
                "name": "P",
                "role_level": 1,
                "style_cues": "x",
                "beliefs": {},
            }
        ],
    }
    await upsert_user_scenario(
        str(db),
        scenario_id="psle_reform_mvp",
        display_name="Shadow",
        document_json=json.dumps(doc),
    )
    cfg, src = await load_scenario_for_run(str(db), "psle_reform_mvp")
    assert src == "user"
    assert cfg.name == "Shadow PSLE"
    assert cfg.policy_events[1] == "Custom only policy."


def test_clone_scenario(client: TestClient) -> None:
    r = client.post(
        "/scenarios/clone",
        json={"template_id": "psle_reform_mvp", "new_scenario_id": "analyst_clone1", "display_name": "Cloned"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == "analyst_clone1"
    doc_r = client.get("/scenarios/analyst_clone1/document")
    assert doc_r.status_code == 200
    assert doc_r.json()["scenario_id"] == "analyst_clone1"


def test_export_yaml(client: TestClient) -> None:
    r = client.get("/scenarios/psle_reform_mvp/export.yaml")
    assert r.status_code == 200
    assert "scenario_id" in r.text
    assert "psle_reform_mvp" in r.text


def test_put_requires_existing_user(client: TestClient) -> None:
    doc = _minimal_doc("analyst_putme")
    assert client.post("/scenarios", json={"document": doc}).status_code == 200
    doc["name"] = "Updated"
    r = client.put("/scenarios/analyst_putme", json={"document": doc})
    assert r.status_code == 200
    r2 = client.put("/scenarios/does_not_exist_user", json={"document": doc})
    assert r2.status_code == 404
