"""Iteration 17 — agent orchestration HTTP surface (plan / execute / ask)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from mirofish_backend.agent.orchestrator import ExecutionPlan, execute_plan, llm_build_execution_plan
from mirofish_backend.config import get_settings

router = APIRouter(tags=["agent"])


class AgentPlanRequest(BaseModel):
    question: str = Field(..., min_length=8, max_length=8000)
    constraints: str | None = Field(default=None, max_length=8000)
    plan_max_tokens: int | None = Field(default=None, ge=256, le=4096)
    plan_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Planner LLM temperature; default 0.35 if omitted.",
    )


class AgentAskRequest(BaseModel):
    question: str = Field(..., min_length=8, max_length=8000)
    constraints: str | None = Field(default=None, max_length=8000)
    plan_max_tokens: int | None = Field(default=None, ge=256, le=4096)
    plan_temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        description="Planner LLM temperature; default 0.35 if omitted.",
    )
    wait_timeout_seconds: float = Field(default=900.0, ge=30.0, le=7200.0)


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/agent/plan")
async def agent_plan(body: AgentPlanRequest) -> dict[str, Any]:
    settings = get_settings()
    try:
        plan = await llm_build_execution_plan(
            settings,
            question=body.question,
            constraints=body.constraints,
            plan_max_tokens=body.plan_max_tokens or 2048,
            plan_temperature=body.plan_temperature if body.plan_temperature is not None else 0.35,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
    return {"plan": plan.model_dump()}


@router.post("/agent/execute")
async def agent_execute(plan: ExecutionPlan) -> dict[str, Any]:
    settings = get_settings()
    try:
        return await execute_plan(settings, plan)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@router.post("/agent/ask", response_model=None)
async def agent_ask(
    body: AgentAskRequest,
    stream: bool = Query(default=False, description="If true, return text/event-stream (SSE)"),
):
    settings = get_settings()
    max_tok = body.plan_max_tokens or 2048
    plan_temp = body.plan_temperature if body.plan_temperature is not None else 0.35

    if not stream:
        try:
            plan = await llm_build_execution_plan(
                settings,
                question=body.question,
                constraints=body.constraints,
                plan_max_tokens=max_tok,
                plan_temperature=plan_temp,
            )
            result = await execute_plan(
                settings,
                plan,
                emit=None,
                wait_timeout_seconds=body.wait_timeout_seconds,
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except RuntimeError as e:
            raise HTTPException(status_code=502, detail=str(e)) from e
        except TimeoutError as e:
            raise HTTPException(status_code=504, detail=str(e)) from e
        return JSONResponse({"plan": plan.model_dump(), **result})

    async def event_gen():
        queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] = asyncio.Queue()

        async def emit(ev: str, detail: dict[str, Any]) -> None:
            await queue.put((ev, detail))

        async def work() -> None:
            try:
                plan_local = await llm_build_execution_plan(
                    settings,
                    question=body.question,
                    constraints=body.constraints,
                    plan_max_tokens=max_tok,
                    plan_temperature=plan_temp,
                )
                await queue.put(("plan_ready", {"plan": plan_local.model_dump()}))
                exec_result = await execute_plan(
                    settings,
                    plan_local,
                    emit=emit,
                    wait_timeout_seconds=body.wait_timeout_seconds,
                )
                await queue.put(("final", exec_result))
            except ValueError as e:
                await queue.put(("error", {"code": 422, "message": str(e)}))
            except RuntimeError as e:
                await queue.put(("error", {"code": 502, "message": str(e)}))
            except TimeoutError as e:
                await queue.put(("error", {"code": 504, "message": str(e)}))
            finally:
                await queue.put(None)

        task = asyncio.create_task(work())
        while True:
            msg = await queue.get()
            if msg is None:
                break
            ev, data = msg
            yield _sse(ev, data)
        await task

    return StreamingResponse(event_gen(), media_type="text/event-stream")
