"""Multi-run experiment API (Iteration 27) — persisted bundles sharing seed and scenario.

**Blocking POST (known limitation):** ``POST /experiments`` runs the full sequential child-run loop
inside the request handler (each child can take up to ``wait_for_simulation_terminal``'s timeout).
Proxies or browsers may time out on large sweeps; the server may still finish child runs in the
background. A future slice may return ``experiment_id`` immediately and drive progress via
``GET /experiments/{id}`` polling (see architect review I1).
"""

from __future__ import annotations

import json
import zipfile
from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mirofish_backend.api.simulations import (
    LLM_PROVIDER_VALUES,
    POPULATION_SAMPLE_MODE_VALUES,
    SIMULATION_MODE_VALUES,
    RemainderConfigParams,
    SimulationRunRequest,
    queue_simulation_run,
    wait_for_simulation_terminal,
)
from mirofish_backend.config import Settings, get_settings
from mirofish_backend.db.repo import (
    create_experiment,
    get_experiment_row,
    get_merged_round_metrics,
    get_simulation_economics_summary,
    get_simulation_export_bundle,
    get_simulation_run_status_only,
    get_simulation_status_and_config_snapshot,
    insert_experiment_run_link,
    list_experiment_run_links,
    list_experiments,
    set_experiment_status,
)
from mirofish_backend.export_bundle import EXPORT_VERSION, build_export_zip, experiment_comparison_csv_bytes
from mirofish_backend.simulation.sampling_strategy import SAMPLING_STRATEGY_VALUES

router = APIRouter(prefix="/experiments", tags=["experiments"])


class ExperimentRunStep(BaseModel):
    """One queued simulation within an experiment; overrides base fields when set."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=256)
    sampling_strategy: str
    agent_limit: int | None = Field(default=None, ge=1, le=300)
    remainder_config: RemainderConfigParams | None = None
    network_csv: str | None = Field(default=None, max_length=500_000)
    simulation_mode: str | None = None
    speakers_per_round: int | None = Field(default=None, ge=1, le=300)
    turn_order_policy: str | None = None
    visibility_policy: str | None = None
    interaction_overlay: str | None = None
    llm_provider: str | None = None
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    rag_enabled: bool | None = None
    llm_concurrency_cap: int | None = Field(default=None, ge=1, le=16)
    aggregation_threshold: int | None = Field(default=None, ge=1, le=300)
    roster_csv: str | None = Field(default=None, max_length=500_000)
    population_csv: str | None = Field(default=None, max_length=500_000)
    population_sample_mode: str | None = None

    @field_validator("sampling_strategy")
    @classmethod
    def _norm_strategy(cls, v: str) -> str:
        s = (v or "").strip().lower().replace("-", "_")
        if s not in SAMPLING_STRATEGY_VALUES:
            raise ValueError(f"sampling_strategy must be one of: {sorted(SAMPLING_STRATEGY_VALUES)}")
        return s


class ExperimentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=512)
    scenario_id: str
    random_seed: int
    total_rounds: int = Field(..., ge=1, le=25)
    agent_limit: int = Field(default=3, ge=1, le=300)
    roster_csv: str | None = Field(default=None, max_length=500_000)
    population_csv: str | None = Field(default=None, max_length=500_000)
    population_sample_mode: str = Field(default="weighted")
    simulation_mode: str = Field(default="full_round_robin")
    speakers_per_round: int = Field(default=2, ge=1, le=300)
    turn_order_policy: str = Field(default="round_robin")
    visibility_policy: str = Field(default="full")
    interaction_overlay: str = Field(default="none")
    llm_provider: str | None = None
    max_tokens: int | None = Field(default=None, ge=64, le=8192)
    rag_enabled: bool | None = None
    llm_concurrency_cap: int | None = Field(default=None, ge=1, le=16)
    aggregation_threshold: int = Field(default=20, ge=1, le=300)
    convergence_threshold: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Shared across all runs in the experiment (fair cross-strategy comparison; Iteration 28+).",
    )
    convergence_patience: int = Field(default=2, ge=1, le=25)
    runs: list[ExperimentRunStep] = Field(..., min_length=1, max_length=16)

    @field_validator("population_sample_mode")
    @classmethod
    def _pop_mode(cls, v: str) -> str:
        s = (v or "weighted").strip().lower().replace("-", "_")
        if s not in POPULATION_SAMPLE_MODE_VALUES:
            raise ValueError("population_sample_mode must be 'weighted' or 'stratified'")
        return s

    @field_validator("simulation_mode")
    @classmethod
    def _sim_mode(cls, v: str) -> str:
        s = (v or "full_round_robin").strip().lower().replace("-", "_")
        if s not in SIMULATION_MODE_VALUES:
            raise ValueError("simulation_mode must be 'full_round_robin' or 'sample_k_per_round'")
        return s

    @field_validator("llm_provider")
    @classmethod
    def _llm(cls, v: str | None) -> str | None:
        if v is None:
            return None
        s = v.strip().lower()
        if s not in LLM_PROVIDER_VALUES:
            raise ValueError("llm_provider must be 'lmstudio', 'anthropic', or 'hybrid'")
        return s


class ExperimentCreateResponse(BaseModel):
    experiment_id: str
    simulation_ids: list[str]


def _deduplicate_key(base: str, used: set[str]) -> str:
    """Reserve a unique key in ``used``; append ``__N`` when ``base`` collides."""
    key = base
    n = 1
    while key in used:
        n += 1
        key = f"{base}__{n}"
    used.add(key)
    return key


def _series_key(step: ExperimentRunStep, step_index: int, used: set[str]) -> str:
    raw = (step.label or "").strip()
    base = raw if raw else f"{step.sampling_strategy}_{step_index + 1}"
    return _deduplicate_key(base, used)


def _series_key_for_link(
    run_label: str | None,
    sampling_strategy: str | None,
    step_index: int,
    used: set[str],
) -> str:
    raw = (run_label or "").strip()
    strat = (sampling_strategy or "full_census").strip().lower()
    if strat not in SAMPLING_STRATEGY_VALUES:
        strat = "full_census"
    base = raw if raw else f"{strat}_{step_index + 1}"
    return _deduplicate_key(base, used)


def _merge_to_simulation_request(exp: ExperimentCreateRequest, step: ExperimentRunStep) -> SimulationRunRequest:
    base = exp.model_dump(exclude={"name", "runs"})
    over = step.model_dump(exclude={"label"}, exclude_none=True)
    merged = {**base, **over}
    return SimulationRunRequest.model_validate(merged)


async def _build_comparison_table(
    sqlite_path: str,
    links: list[dict[str, Any]],
    series_keys: list[str],
    max_rounds: int,
) -> list[dict[str, Any]]:
    per_sim_metrics: list[dict[int, dict[str, Any]]] = []
    for link in links:
        sid = str(link["simulation_id"])
        per_sim_metrics.append(await get_merged_round_metrics(sqlite_path, simulation_id=sid))

    out: list[dict[str, Any]] = []
    for rnd in range(1, max_rounds + 1):
        by_run: dict[str, dict[str, Any]] = {}
        for sk, metrics_by_round in zip(series_keys, per_sim_metrics):
            m = metrics_by_round.get(rnd)
            if m:
                by_run[sk] = {
                    "implementation_readiness": m.get("implementation_readiness"),
                    "alignment_index": m.get("alignment_index"),
                    "adoption_momentum": m.get("adoption_momentum"),
                    "conflict_events": m.get("conflict_events"),
                    "consistency_index": m.get("consistency_index"),
                    "convergence_delta": m.get("convergence_delta"),
                }
        out.append({"round_number": rnd, "by_run": by_run})
    return out


def _flatten_comparison_for_csv(
    comparison: list[dict[str, Any]],
    economics_by_series: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    econ = economics_by_series or {}
    flat: list[dict[str, Any]] = []
    for row in comparison:
        rn = int(row["round_number"])
        for run_label, met in (row.get("by_run") or {}).items():
            e = econ.get(run_label) or {}
            flat.append(
                {
                    "run_label": run_label,
                    "round": rn,
                    "implementation_readiness": met.get("implementation_readiness"),
                    "alignment_index": met.get("alignment_index"),
                    "adoption_momentum": met.get("adoption_momentum"),
                    "conflict_events": met.get("conflict_events"),
                    "consistency_index": met.get("consistency_index"),
                    "convergence_delta": met.get("convergence_delta"),
                    "input_tokens": e.get("total_input_tokens"),
                    "output_tokens": e.get("total_output_tokens"),
                    "estimated_cost_usd": e.get("estimated_cost_usd"),
                }
            )
    return flat


async def _experiment_detail_payload(settings: Settings, experiment_id: str) -> dict[str, Any] | None:
    row = await get_experiment_row(settings.sqlite_path, experiment_id=experiment_id)
    if row is None:
        return None
    links = await list_experiment_run_links(settings.sqlite_path, experiment_id=experiment_id)
    used_keys: set[str] = set()
    series_keys: list[str] = []
    runs_out: list[dict[str, Any]] = []

    for i, link in enumerate(links):
        sid = str(link["simulation_id"])
        st = await get_simulation_run_status_only(settings.sqlite_path, simulation_id=sid)
        cfg_row = await get_simulation_status_and_config_snapshot(settings.sqlite_path, simulation_id=sid)
        cfg = cfg_row.get("config_snapshot") if cfg_row else None
        strat = None
        if isinstance(cfg, dict):
            strat = cfg.get("sampling_strategy")
        strat_s = str(strat) if strat else None
        lbl = link.get("run_label")
        sk = _series_key_for_link(lbl, strat_s, i, used_keys)
        series_keys.append(sk)
        econ = await get_simulation_economics_summary(settings.sqlite_path, simulation_id=sid)
        runs_out.append(
            {
                "step_index": link["step_index"],
                "simulation_id": sid,
                "run_label": lbl,
                "series_key": sk,
                "sampling_strategy": strat_s,
                "status": (st or {}).get("status"),
                "current_round": (st or {}).get("current_round"),
                "total_rounds": (st or {}).get("total_rounds"),
                "failure_reason": (st or {}).get("failure_reason"),
                "converged_at_round": (st or {}).get("converged_at_round"),
                "total_input_tokens": (st or {}).get("total_input_tokens"),
                "total_output_tokens": (st or {}).get("total_output_tokens"),
                "economics": econ,
            }
        )

    max_rounds = int(row["base_total_rounds"])
    comparison = await _build_comparison_table(settings.sqlite_path, links, series_keys, max_rounds)
    econ_by_series = {r["series_key"]: r["economics"] for r in runs_out if r.get("economics")}
    total_estimated = round(
        sum(float((e or {}).get("estimated_cost_usd") or 0.0) for e in econ_by_series.values()),
        6,
    )

    return {
        "experiment": row,
        "runs": runs_out,
        "comparison": comparison,
        "export_version": EXPORT_VERSION,
        "total_estimated_cost_usd": total_estimated,
    }


@router.get("")
async def list_experiments_endpoint(limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
    settings = get_settings()
    return await list_experiments(settings.sqlite_path, limit=limit)


@router.post("", response_model=ExperimentCreateResponse)
async def create_experiment_endpoint(body: ExperimentCreateRequest) -> ExperimentCreateResponse:
    """Queue all child runs sequentially in-process; see module docstring for timeout / proxy caveats."""
    settings = get_settings()
    exp_id = await create_experiment(
        settings.sqlite_path,
        name=body.name,
        scenario_id=body.scenario_id,
        base_random_seed=body.random_seed,
        base_total_rounds=body.total_rounds,
        status="pending",
    )
    simulation_ids: list[str] = []

    try:
        await set_experiment_status(settings.sqlite_path, experiment_id=exp_id, status="running")
        used_keys: set[str] = set()
        for i, step in enumerate(body.runs):
            _ = _series_key(step, i, used_keys)
            req = _merge_to_simulation_request(body, step)
            disp = f"{body.name} · {i + 1} · {step.sampling_strategy}"
            resp = await queue_simulation_run(
                settings,
                req,
                experiment_id=exp_id,
                experiment_step_index=i,
                experiment_run_label=step.label,
                run_display_name=disp,
            )
            simulation_ids.append(resp.id)
            await insert_experiment_run_link(
                settings.sqlite_path,
                experiment_id=exp_id,
                step_index=i,
                simulation_id=resp.id,
                run_label=step.label,
            )
            await wait_for_simulation_terminal(
                sqlite_path=settings.sqlite_path,
                simulation_id=resp.id,
                poll_interval=0.05,
                timeout_seconds=900.0,
            )
        await set_experiment_status(settings.sqlite_path, experiment_id=exp_id, status="completed")
    except Exception as exc:
        await set_experiment_status(settings.sqlite_path, experiment_id=exp_id, status="failed")
        raise HTTPException(status_code=500, detail="Experiment run failed") from exc

    return ExperimentCreateResponse(experiment_id=exp_id, simulation_ids=simulation_ids)


@router.get("/{experiment_id}")
async def get_experiment_detail(experiment_id: str) -> dict[str, Any]:
    settings = get_settings()
    payload = await _experiment_detail_payload(settings, experiment_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return payload


@router.get("/{experiment_id}/export.json")
async def get_experiment_export_json(experiment_id: str) -> JSONResponse:
    settings = get_settings()
    detail = await _experiment_detail_payload(settings, experiment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    links = await list_experiment_run_links(settings.sqlite_path, experiment_id=experiment_id)
    run_bundles: dict[str, Any] = {}
    for link in links:
        sid = str(link["simulation_id"])
        b = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=sid)
        if b:
            run_bundles[sid] = b
    econ_map = {r["series_key"]: r["economics"] for r in detail["runs"] if r.get("economics")}
    flat = _flatten_comparison_for_csv(detail["comparison"], econ_map)
    payload = {
        "export_version": EXPORT_VERSION,
        "experiment": detail["experiment"],
        "comparison": detail["comparison"],
        "comparison_flat": flat,
        "runs": run_bundles,
        "total_estimated_cost_usd": detail.get("total_estimated_cost_usd"),
    }
    return JSONResponse(content=payload)


@router.get("/{experiment_id}/export.zip")
async def get_experiment_export_zip(experiment_id: str) -> Response:
    settings = get_settings()
    detail = await _experiment_detail_payload(settings, experiment_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Experiment not found")
    row = detail["experiment"]
    links = await list_experiment_run_links(settings.sqlite_path, experiment_id=experiment_id)
    econ_map = {r["series_key"]: r["economics"] for r in detail["runs"] if r.get("economics")}
    flat = _flatten_comparison_for_csv(detail["comparison"], econ_map)
    bio = BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("comparison.csv", experiment_comparison_csv_bytes(flat))
        zf.writestr(
            "experiment.json",
            json.dumps(
                {
                    "export_version": EXPORT_VERSION,
                    "experiment": row,
                    "comparison": detail["comparison"],
                    "run_simulation_ids": [str(l["simulation_id"]) for l in links],
                },
                indent=2,
                sort_keys=True,
            ).encode("utf-8"),
        )
        for link in links:
            sid = str(link["simulation_id"])
            bundle = await get_simulation_export_bundle(settings.sqlite_path, simulation_id=sid)
            if bundle:
                prefix = f"runs/{sid}/"
                zf.writestr(f"{prefix}export.json", json.dumps(bundle, indent=2, sort_keys=True).encode("utf-8"))
                zf.writestr(f"{prefix}bundle.zip", build_export_zip(bundle))
    return Response(
        content=bio.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="experiment_{experiment_id}.zip"'},
    )
