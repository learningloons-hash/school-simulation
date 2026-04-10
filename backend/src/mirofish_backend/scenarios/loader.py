"""Resolve ScenarioConfig for a run: user_scenarios row overrides package registry."""

from __future__ import annotations

import json
from typing import Literal

from mirofish_backend.db.repo import get_user_scenario_json
from mirofish_backend.scenarios.registry import ScenarioConfig, get_scenario, scenario_from_mapping

ScenarioSource = Literal["user", "builtin"]


async def load_scenario_for_run(sqlite_path: str, scenario_id: str) -> tuple[ScenarioConfig, ScenarioSource]:
    raw = await get_user_scenario_json(sqlite_path, scenario_id=scenario_id)
    if raw:
        doc = json.loads(raw)
        if not isinstance(doc, dict):
            raise ValueError("stored user scenario is not a JSON object")
        return scenario_from_mapping(doc), "user"
    return get_scenario(scenario_id), "builtin"
