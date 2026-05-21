"""Plan → run → analyze orchestration using in-process API handlers (Iteration 17)."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator

from mirofish_backend.api.capabilities import build_capabilities_dict
from mirofish_backend.api.scenarios_generate import GenerateFromBriefRequest, generate_scenario_from_brief
from mirofish_backend.api.simulations import (
    RemainderConfigParams,
    SimulationAnalyzeRequest,
    SimulationRunRequest,
    analyze_simulation_export,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.simulation.interaction_policy import VisibilityPolicy
from mirofish_backend.simulation.sampling_strategy import SAMPLING_STRATEGY_VALUES
from mirofish_backend.config import Settings
from mirofish_backend.db.repo import upsert_user_scenario
from mirofish_backend.llm.model_profiles import BUILTIN_PROFILE_IDS
from mirofish_backend.llm.router import llm_complete

logger = logging.getLogger("mirofish_backend.agent.orchestrator")


def _http_exception_message(exc: HTTPException) -> str:
    d = exc.detail
    if isinstance(d, dict):
        return json.dumps(d, ensure_ascii=False)
    return str(d)


class PlanSimulationParams(BaseModel):
    total_rounds: int = Field(default=2, ge=1, le=25)
    agent_limit: int = Field(default=3, ge=1, le=300)
    random_seed: int = 42
    simulation_mode: str = "full_round_robin"
    speakers_per_round: int = Field(default=2, ge=1, le=300)
    population_sample_mode: str = "weighted"
    llm_provider: str | None = None
    model_profile_id: str | None = Field(
        default=None,
        description="Optional built-in model profile (e.g. local_lmstudio_default, anthropic_default).",
    )
    turn_order_policy: str = "round_robin"
    visibility_policy: str = "full"
    interaction_overlay: str = "none"
    rag_enabled: bool | None = None
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    roster_csv: str | None = Field(default=None, max_length=500_000)
    population_csv: str | None = Field(default=None, max_length=500_000)
    llm_concurrency_cap: int | None = Field(
        default=None,
        ge=1,
        le=16,
        description="Max concurrent LLM calls per round (Iteration 19). Null = server default (4).",
    )
    aggregation_threshold: int = Field(
        default=20,
        ge=1,
        le=300,
        description="Agent count threshold for cohort aggregation in exports (Iteration 20).",
    )
    sampling_strategy: str = Field(
        default="full_census",
        description="full_census | role_stratified | hybrid_core_remainder | posture_maxvar | network_centrality.",
    )
    remainder_config: RemainderConfigParams | None = None
    network_csv: str | None = Field(
        default=None,
        max_length=500_000,
        description="Influence network CSV; required when sampling_strategy=network_centrality.",
    )
    convergence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional early stop when population attitude change stays below this (Iteration 28).",
    )
    convergence_patience: int = Field(default=2, ge=1, le=25)

    @model_validator(mode="after")
    def _remainder_fits_agent_limit(self) -> "PlanSimulationParams":
        rc = self.remainder_config
        if rc is not None and rc.remainder_count > 0:
            if rc.remainder_count >= self.agent_limit:
                raise ValueError("remainder_config.remainder_count must be less than agent_limit")
        return self

    @field_validator("model_profile_id")
    @classmethod
    def _normalize_model_profile_id(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip()
        if not s:
            return None
        if s not in BUILTIN_PROFILE_IDS:
            raise ValueError(
                f"model_profile_id must be one of: {sorted(BUILTIN_PROFILE_IDS)}; got {s!r}"
            )
        return s

    @field_validator("sampling_strategy")
    @classmethod
    def _normalize_sampling_strategy(cls, v: str) -> str:
        s = (v or "full_census").strip().lower().replace("-", "_")
        if s not in SAMPLING_STRATEGY_VALUES:
            raise ValueError(
                "sampling_strategy must be one of: full_census, role_stratified, hybrid_core_remainder, "
                "posture_maxvar, network_centrality"
            )
        return s

    @field_validator("visibility_policy")
    @classmethod
    def _normalize_plan_visibility(cls, v: str) -> str:
        s = (v or "full").strip().lower()
        valid = frozenset(x.value for x in VisibilityPolicy)
        if s not in valid:
            raise ValueError(f"visibility_policy must be one of: {', '.join(sorted(valid))}")
        return s


class PlanRunStep(BaseModel):
    label: str = ""
    research_question: str = Field(..., min_length=4, max_length=8000)
    scenario_id: str | None = None
    scenario_brief: str | None = Field(default=None, max_length=16000)
    simulation: PlanSimulationParams = Field(default_factory=PlanSimulationParams)

    @model_validator(mode="after")
    def _one_scenario_source(self) -> PlanRunStep:
        sid = (self.scenario_id or "").strip() or None
        brief = (self.scenario_brief or "").strip() or None
        object.__setattr__(self, "scenario_id", sid)
        object.__setattr__(self, "scenario_brief", brief)
        if sid and brief:
            raise ValueError("Provide only one of scenario_id or scenario_brief")
        if not sid and not brief:
            raise ValueError("Provide scenario_id or scenario_brief")
        if brief and len(brief) < 20:
            raise ValueError("scenario_brief must be at least 20 characters when used")
        return self


class ExecutionPlan(BaseModel):
    runs: list[PlanRunStep] = Field(..., min_length=1, max_length=8)


def _visibility_policy_for_capability_check(raw: str) -> str:
    """Normalize legacy API alias ``full`` → ``broadcast`` (matches run request / ADR-002)."""
    s = (raw or "").strip().lower()
    return "broadcast" if s == "full" else s


def validate_plan_against_capabilities(capabilities: dict[str, Any], plan: ExecutionPlan) -> list[str]:
    errors: list[str] = []
    sim_run = capabilities.get("simulation_run", {})
    sm = set(sim_run.get("simulation_modes", []))
    pm = set(sim_run.get("population_sample_modes", []))
    lp = set(sim_run.get("llm_providers", []))
    cap_range = sim_run.get("llm_concurrency_cap", {})
    cap_min = cap_range.get("min", 1)
    cap_max = cap_range.get("max", 16)
    ip = capabilities.get("interaction_policy", {})
    top = set(ip.get("turn_order_policies", []))
    vis = set(ip.get("visibility_policies", []))
    iov = set(ip.get("interaction_overlays", []))
    for i, r in enumerate(plan.runs):
        pfx = f"runs[{i}]"
        sim = r.simulation
        if sim.simulation_mode not in sm:
            errors.append(f"{pfx}.simulation: invalid simulation_mode {sim.simulation_mode!r}")
        if sim.population_sample_mode not in pm:
            errors.append(f"{pfx}.simulation: invalid population_sample_mode {sim.population_sample_mode!r}")
        if sim.llm_provider is not None and sim.llm_provider not in lp:
            errors.append(f"{pfx}.simulation: invalid llm_provider {sim.llm_provider!r}")
        mp_block = capabilities.get("model_profiles") or {}
        profile_ids = {
            str(p.get("profile_id"))
            for p in (mp_block.get("profiles") or [])
            if p.get("profile_id")
        }
        if sim.model_profile_id is not None and sim.model_profile_id not in profile_ids:
            errors.append(
                f"{pfx}.simulation: invalid model_profile_id {sim.model_profile_id!r}"
            )
        if sim.turn_order_policy not in top:
            errors.append(f"{pfx}.simulation: invalid turn_order_policy {sim.turn_order_policy!r}")
        vis_norm = _visibility_policy_for_capability_check(sim.visibility_policy)
        if vis_norm not in vis:
            errors.append(f"{pfx}.simulation: invalid visibility_policy {sim.visibility_policy!r}")
        if sim.interaction_overlay not in iov:
            errors.append(f"{pfx}.simulation: invalid interaction_overlay {sim.interaction_overlay!r}")
        if sim.llm_concurrency_cap is not None and not (cap_min <= sim.llm_concurrency_cap <= cap_max):
            errors.append(
                f"{pfx}.simulation: llm_concurrency_cap {sim.llm_concurrency_cap} out of range [{cap_min},{cap_max}]"
            )
        ss = set(sim_run.get("sampling_strategies", []))
        if sim.sampling_strategy not in ss:
            errors.append(f"{pfx}.simulation: invalid sampling_strategy {sim.sampling_strategy!r}")
        ct_meta = sim_run.get("convergence_threshold") or {}
        if isinstance(ct_meta, dict) and sim.convergence_threshold is not None:
            lo = float(ct_meta.get("min", 0.0))
            hi = float(ct_meta.get("max", 1.0))
            if not (lo <= sim.convergence_threshold <= hi):
                errors.append(
                    f"{pfx}.simulation: convergence_threshold {sim.convergence_threshold} out of range [{lo},{hi}]"
                )
        cp_meta = sim_run.get("convergence_patience") or {}
        if isinstance(cp_meta, dict):
            pmin = int(cp_meta.get("min", 1))
            pmax = int(cp_meta.get("max", 25))
            if not (pmin <= sim.convergence_patience <= pmax):
                errors.append(
                    f"{pfx}.simulation: convergence_patience {sim.convergence_patience} out of range [{pmin},{pmax}]"
                )
    return errors


def _parse_llm_json_object(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [ln for ln in lines if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}
    return parsed if isinstance(parsed, dict) else {}


_PLANNER_SYSTEM = """You are a planning assistant for the MiroFish policy simulation API.
Output ONLY valid JSON (no markdown fences). The JSON must match this shape:

{
  "runs": [
    {
      "label": "optional short label",
      "research_question": "string — passed to POST /simulations/{id}/analyze after the run",
      "scenario_id": "existing scenario slug OR null",
      "scenario_brief": "null OR plain-English brief (min 20 chars) to generate a new scenario first",
      "simulation": {
        "total_rounds": 2,
        "agent_limit": 3,
        "random_seed": 42,
        "simulation_mode": "full_round_robin",
        "speakers_per_round": 2,
        "population_sample_mode": "weighted",
        "llm_provider": null,
        "model_profile_id": null,
        "turn_order_policy": "round_robin",
        "visibility_policy": "full",
        "interaction_overlay": "none",
        "rag_enabled": null,
        "max_tokens": null,
        "roster_csv": null,
        "population_csv": null,
        "llm_concurrency_cap": null,
        "aggregation_threshold": 20,
        "sampling_strategy": "full_census",
        "remainder_config": null,
        "network_csv": null,
        "convergence_threshold": null,
        "convergence_patience": 2
      }
    }
  ]
}

Rules:
- Exactly one of scenario_id or scenario_brief must be non-null per run (not both).
- For a quick demo using packaged scenarios, prefer scenario_id "psle_reform_mvp" or "fsbb_comparator" with small total_rounds (1-3).
- Use only parameter values that appear in the capabilities JSON below.
- If the user asks for a custom fictional scenario, use scenario_brief with a rich brief; omit scenario_id (null).

Capabilities (authoritative vocabulary):
"""


async def llm_build_execution_plan(
    settings: Settings,
    *,
    question: str,
    constraints: str | None = None,
    plan_max_tokens: int = 2048,
    plan_temperature: float = 0.35,
) -> ExecutionPlan:
    caps = build_capabilities_dict()
    caps_json = json.dumps(caps, ensure_ascii=False)
    user = f"Research / task:\n{question.strip()}\n"
    if constraints and constraints.strip():
        user += f"\nAdditional constraints:\n{constraints.strip()}\n"

    provider = settings.llm_provider
    try:
        comp = await llm_complete(
            provider=provider if provider in ("lmstudio", "anthropic") else "lmstudio",
            messages=[
                {"role": "system", "content": _PLANNER_SYSTEM + caps_json},
                {"role": "user", "content": user},
            ],
            temperature=plan_temperature,
            max_tokens=plan_max_tokens,
            lmstudio_base_url=settings.lmstudio_base_url,
            lmstudio_model=settings.lmstudio_model,
            anthropic_api_key=settings.anthropic_api_key,
            anthropic_model=settings.anthropic_model,
        )
        raw = comp.text
    except Exception as e:
        logger.warning("agent plan LLM failed: %s", e)
        raise RuntimeError(f"Planner LLM call failed: {e}") from e

    parsed = _parse_llm_json_object(raw)
    if not parsed.get("runs"):
        raise ValueError("Planner returned no runs[]")

    try:
        plan = ExecutionPlan.model_validate(parsed)
    except Exception as e:
        raise ValueError(f"Invalid plan JSON from planner: {e}") from e

    v_errs = validate_plan_against_capabilities(caps, plan)
    if v_errs:
        raise ValueError("Plan failed capability validation: " + "; ".join(v_errs))

    return plan


def _simulation_run_request(scenario_id: str, sim: PlanSimulationParams) -> SimulationRunRequest:
    return SimulationRunRequest(
        scenario_id=scenario_id,
        total_rounds=sim.total_rounds,
        agent_limit=sim.agent_limit,
        random_seed=sim.random_seed,
        simulation_mode=sim.simulation_mode,
        speakers_per_round=sim.speakers_per_round,
        population_sample_mode=sim.population_sample_mode,
        llm_provider=sim.llm_provider,
        model_profile_id=sim.model_profile_id,
        turn_order_policy=sim.turn_order_policy,
        visibility_policy=sim.visibility_policy,
        interaction_overlay=sim.interaction_overlay,
        rag_enabled=sim.rag_enabled,
        max_tokens=sim.max_tokens,
        roster_csv=sim.roster_csv,
        population_csv=sim.population_csv,
        llm_concurrency_cap=sim.llm_concurrency_cap,
        aggregation_threshold=sim.aggregation_threshold,
        sampling_strategy=sim.sampling_strategy,
        remainder_config=sim.remainder_config,
        network_csv=sim.network_csv,
        convergence_threshold=sim.convergence_threshold,
        convergence_patience=sim.convergence_patience,
    )


EmitFn = Callable[[str, dict[str, Any]], Awaitable[None]]


async def execute_plan(
    settings: Settings,
    plan: ExecutionPlan,
    *,
    emit: EmitFn | None = None,
    wait_timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Run each plan step sequentially: optional generate → queue run → wait → analyze."""
    caps = build_capabilities_dict()
    v_errs = validate_plan_against_capabilities(caps, plan)
    if v_errs:
        raise ValueError("Plan failed capability validation: " + "; ".join(v_errs))

    run_reports: list[dict[str, Any]] = []

    async def _emit(event: str, detail: dict[str, Any]) -> None:
        if emit:
            await emit(event, detail)

    for idx, step in enumerate(plan.runs):
        label = step.label or f"run_{idx}"
        gen_warnings: list[str] = []
        await _emit("step_start", {"index": idx, "label": label})

        scenario_id: str = ""
        if step.scenario_brief:
            try:
                gen = await generate_scenario_from_brief(
                    GenerateFromBriefRequest(brief=step.scenario_brief),
                )
                doc = gen.document
                gen_warnings = list(gen.warnings)
                scenario_id = str(doc["scenario_id"])
                await upsert_user_scenario(
                    settings.sqlite_path,
                    scenario_id=scenario_id,
                    display_name=str(doc.get("name") or scenario_id),
                    document_json=json.dumps(doc, sort_keys=True),
                )
                await _emit("scenario_saved", {"scenario_id": scenario_id, "warnings": gen_warnings})
            except HTTPException as e:
                err_text = _http_exception_message(e)
                analysis_err = f"generate_from_brief failed (HTTP {e.status_code}): {err_text}"
                logger.warning("execute_plan step %s scenario_brief rejected: %s", label, analysis_err)
                await _emit(
                    "scenario_generate_failed",
                    {"label": label, "status_code": e.status_code, "detail": err_text},
                )
                run_reports.append(
                    {
                        "label": label,
                        "scenario_id": None,
                        "simulation_id": None,
                        "status": "generate_failed",
                        "failure_reason": None,
                        "queue_warnings": [],
                        "generate_warnings": gen_warnings,
                        "analysis": None,
                        "analysis_error": analysis_err,
                    }
                )
                continue
        else:
            scenario_id = step.scenario_id or ""
            await _emit("scenario_ready", {"scenario_id": scenario_id})

        try:
            req = _simulation_run_request(scenario_id, step.simulation)
            run_resp = await queue_simulation_run(settings, req)
        except HTTPException as e:
            err_text = _http_exception_message(e)
            analysis_err = f"queue_simulation_run failed (HTTP {e.status_code}): {err_text}"
            logger.warning("execute_plan step %s queue failed: %s", label, analysis_err)
            await _emit(
                "run_queue_failed",
                {"label": label, "scenario_id": scenario_id, "status_code": e.status_code},
            )
            run_reports.append(
                {
                    "label": label,
                    "scenario_id": scenario_id,
                    "simulation_id": None,
                    "status": "queue_failed",
                    "failure_reason": None,
                    "queue_warnings": [],
                    "generate_warnings": gen_warnings,
                    "analysis": None,
                    "analysis_error": analysis_err,
                }
            )
            continue
        sim_id = run_resp.id
        await _emit(
            "run_queued",
            {"simulation_id": sim_id, "scenario_id": scenario_id, "warnings": run_resp.warnings},
        )

        terminal = await wait_for_simulation_terminal(
            sqlite_path=settings.sqlite_path,
            simulation_id=sim_id,
            timeout_seconds=wait_timeout_seconds,
        )
        st = str(terminal.get("status") or "")
        await _emit(
            "run_finished",
            {
                "simulation_id": sim_id,
                "status": st,
                "failure_reason": terminal.get("failure_reason"),
            },
        )

        analysis: dict[str, Any] | None = None
        analysis_err: str | None = None
        if st == "completed":
            try:
                ar = await analyze_simulation_export(
                    sim_id,
                    SimulationAnalyzeRequest(research_question=step.research_question),
                )
                analysis = ar.model_dump()
                await _emit("analysis_done", {"simulation_id": sim_id})
            except Exception as e:
                analysis_err = f"{type(e).__name__}: {e}"
                logger.warning("analyze failed for %s: %s", sim_id, e)
                await _emit("analysis_error", {"simulation_id": sim_id, "error": analysis_err})
        else:
            analysis_err = str(terminal.get("failure_reason") or "run not completed")

        run_reports.append(
            {
                "label": label,
                "scenario_id": scenario_id,
                "simulation_id": sim_id,
                "status": st,
                "failure_reason": terminal.get("failure_reason"),
                "queue_warnings": list(run_resp.warnings),
                "generate_warnings": gen_warnings,
                "analysis": analysis,
                "analysis_error": analysis_err,
            }
        )

    await _emit("execute_complete", {"run_count": len(run_reports)})
    return {"runs": run_reports}
