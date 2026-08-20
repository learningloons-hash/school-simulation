"""
Park et al. five-category architectural diagnostic interview (Senna iter-47).

Post-run script administration only — not wired into the live orchestrator.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from mirofish_backend.config import Settings, get_settings
from mirofish_backend.diagnostics.judge_score_parse import (
    count_parse_sources,
    resolve_judge_score,
    score_label,
)
from mirofish_backend.llm.model_profiles import (
    resolve_run_llm_provider,
    resolve_run_profiles,
    run_llm_credentials,
    resolve_api_key_from_env,
)
from mirofish_backend.llm.router import LLMCompletion, LLMProvider, effective_model_id, llm_complete

RUBRIC_VERSION = "1"
INTERVIEW_CATEGORIES: tuple[str, ...] = (
    "self_knowledge",
    "memory_retrieval",
    "planning",
    "reaction",
    "reflection",
)

CATEGORY_LABELS: dict[str, str] = {
    "self_knowledge": "Self-knowledge",
    "memory_retrieval": "Memory retrieval",
    "planning": "Planning",
    "reaction": "Reaction",
    "reflection": "Reflection",
}

# Product-safe question bank (not CIEPSS wording).
QUESTION_TEMPLATES: dict[str, str] = {
    "self_knowledge": (
        "You just completed a multi-round simulation as {agent_name} ({agent_role}). "
        "In your own words, what were your main goals and constraints during the discussion? "
        "How did your stance on the scenario topic relate to your assigned role?"
    ),
    "memory_retrieval": (
        "Recall a specific moment from the simulation when another participant said something "
        "that changed or reinforced your thinking. Quote or paraphrase what they said, which "
        "round it occurred in, and why it mattered to you."
    ),
    "planning": (
        "Before you spoke in a later round, how did you decide what to say? Describe the steps "
        "you took (or would take) to choose your message, audience, and tone."
    ),
    "reaction": (
        "Describe how you responded when another participant disagreed with you or challenged "
        "your position. Give a concrete example from the simulation and explain your immediate "
        "reaction and what you did next."
    ),
    "reflection": (
        "Looking back at the full simulation, what would you do differently if the discussion "
        "restarted? What did you learn about your own approach to the scenario?"
    ),
}

RUBRIC_EXCERPTS: dict[str, str] = {
    "self_knowledge": (
        "0: No identifiable goals or role. "
        "1: Names role/goals without linking to behavior. "
        "2: Coherent role/goals/stance with concrete reference to own turns."
    ),
    "memory_retrieval": (
        "0: No specific recall. "
        "1: Vague recall without round/speaker/content. "
        "2: Specific moment (round/speaker/content) and why it mattered."
    ),
    "planning": (
        "0: No planning process. "
        "1: Intent/audience mentioned without stepwise chain. "
        "2: Explicit planning steps tied to simulation context."
    ),
    "reaction": (
        "0: No disagreement example. "
        "1: Example but unclear reaction or follow-up. "
        "2: Concrete disagreement with reaction and follow-up action."
    ),
    "reflection": (
        "0: No retrospective view. "
        "1: Generic reflection without simulation grounding. "
        "2: Specific lesson grounded in an episode from the run."
    ),
}

_repo_root = Path(__file__).resolve().parents[4]
RUBRIC_DOC_PATH = _repo_root / "docs" / "diagnostics" / "ARCHITECTURAL_INTERVIEW_RUBRIC.md"

# Patch point for tests (mirrors orchestrator.llm_complete pattern).
_llm_complete = llm_complete


@dataclass(frozen=True)
class AgentInterviewTarget:
    agent_id: str
    agent_role: str
    agent_name: str


@dataclass(frozen=True)
class InterviewResponseRecord:
    response_id: str
    agent_id: str
    category: str
    question_text: str
    response_text: str
    interview_provider: str
    interview_model: str
    interview_profile_id: str
    input_tokens: int | None
    output_tokens: int | None


@dataclass(frozen=True)
class InterviewScoreRecord:
    score_id: str
    response_id: str
    agent_id: str
    category: str
    score: int
    score_label: str
    rationale: str | None
    judge_raw_response: str
    judge_provider: str
    judge_model: str
    judge_profile_id: str
    parse_source: str
    rubric_version: str
    input_tokens: int | None
    output_tokens: int | None


def format_interview_question(*, category: str, agent_name: str, agent_role: str) -> str:
    if category not in QUESTION_TEMPLATES:
        raise ValueError(f"unknown interview category {category!r}")
    return QUESTION_TEMPLATES[category].format(agent_name=agent_name, agent_role=agent_role)


def build_agent_discussion_context(
    transcript: list[dict[str, Any]],
    *,
    agent_id: str,
    max_chars: int = 6000,
) -> str:
    lines: list[str] = []
    for turn in transcript:
        rnd = turn.get("round_number")
        resp = str(turn.get("raw_response") or "").strip()
        if not resp:
            continue
        if turn.get("agent_id") == agent_id:
            lines.append(f"[Round {rnd}] You said: {resp[:800]}")
        else:
            name = turn.get("agent_name") or turn.get("agent_id")
            lines.append(f"[Round {rnd}] {name}: {resp[:400]}")
    text = "\n".join(lines)
    if len(text) > max_chars:
        text = text[-max_chars:]
    return text


def build_interview_prompts(
    *,
    category: str,
    agent: AgentInterviewTarget,
    discussion_context: str,
) -> tuple[str, str]:
    question = format_interview_question(
        category=category,
        agent_name=agent.agent_name,
        agent_role=agent.agent_role,
    )
    system = (
        "You are participating in a post-simulation architectural diagnostic interview. "
        "Answer as the simulated agent named below, using only the discussion history provided. "
        "Be specific and ground claims in the transcript. Do not invent events that are not supported."
    )
    user_parts = [
        f"Agent: {agent.agent_name} ({agent.agent_role})",
        "",
        "Discussion history:",
        discussion_context or "(no transcript available)",
        "",
        "Interview question:",
        question,
        "",
        "Reply in plain text (no JSON).",
    ]
    return system, "\n".join(user_parts)


def build_judge_prompts(
    *,
    category: str,
    question_text: str,
    response_text: str,
    rubric_excerpt: str | None = None,
) -> tuple[str, str]:
    excerpt = rubric_excerpt if rubric_excerpt is not None else load_rubric_category_excerpt(category)
    label = CATEGORY_LABELS.get(category, category)
    system = (
        "You are a rubric judge for an architectural diagnostic interview. "
        "Score the agent response on a 0–2 scale (0=inadequate, 1=partial, 2=adequate). "
        "Use only the rubric criteria and the response text. "
        "Append exactly one block:\n"
        '<judge_score>{"score": N, "rationale": "..."}</judge_score>\n'
        "where N is 0, 1, or 2."
    )
    user = "\n".join(
        [
            f"Category: {label} ({category})",
            "",
            "Rubric criteria:",
            excerpt,
            "",
            "Question asked:",
            question_text,
            "",
            "Agent response:",
            response_text,
            "",
            "Return your score in the required <judge_score> block.",
        ]
    )
    return system, user


def agents_from_snapshots(snapshots: list[dict[str, Any]]) -> list[AgentInterviewTarget]:
    if not snapshots:
        return []
    max_round = max(int(s.get("round_number") or 0) for s in snapshots)
    latest = [s for s in snapshots if int(s.get("round_number") or 0) == max_round]
    seen: set[str] = set()
    out: list[AgentInterviewTarget] = []
    for snap in sorted(latest, key=lambda s: str(s.get("agent_name") or s.get("agent_id"))):
        aid = str(snap.get("agent_id") or "")
        if not aid or aid in seen:
            continue
        seen.add(aid)
        out.append(
            AgentInterviewTarget(
                agent_id=aid,
                agent_role=str(snap.get("agent_role") or ""),
                agent_name=str(snap.get("agent_name") or aid),
            )
        )
    return out


async def complete_with_profile(
    *,
    profile_id: str,
    messages: list[dict[str, Any]],
    temperature: float,
    max_tokens: int,
    settings: Settings | None = None,
) -> tuple[LLMCompletion, LLMProvider, str, str]:
    """Call ``llm_complete`` using a built-in ``model_profile_id``."""
    cfg = settings or get_settings()
    llm_provider = resolve_run_llm_provider(
        request_llm_provider=None,
        model_profile_id=profile_id,
        settings=cfg,
    )
    resolution = resolve_run_profiles(
        model_profile_id=profile_id,
        llm_provider=llm_provider,
        settings=cfg,
    )
    profile = resolution.primary_profile
    lm_model, lm_url, ant_model = run_llm_credentials(resolution, cfg)
    provider: LLMProvider = "anthropic" if profile.provider_type == "anthropic" else "lmstudio"
    anthropic_key = (
        resolve_api_key_from_env(profile.api_key_env)
        if profile.provider_type == "anthropic"
        else (cfg.anthropic_api_key or "")
    )
    openai_key = (
        resolve_api_key_from_env(profile.api_key_env)
        if profile.provider_type == "openai_compatible" and profile.api_key_env
        else ""
    )
    completion = await _llm_complete(
        provider=provider,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        lmstudio_base_url=lm_url,
        lmstudio_model=lm_model,
        anthropic_api_key=anthropic_key,
        anthropic_model=ant_model,
        openai_compatible_api_key=openai_key,
    )
    eff_model = effective_model_id(
        provider=provider,
        lmstudio_model=lm_model,
        anthropic_model=ant_model,
    )
    return completion, provider, eff_model, profile.profile_id


async def administer_category_interview(
    *,
    category: str,
    agent: AgentInterviewTarget,
    discussion_context: str,
    interview_profile_id: str,
    temperature: float,
    max_tokens: int,
    settings: Settings | None = None,
) -> tuple[str, str, str, str, str, int | None, int | None]:
    system, user = build_interview_prompts(
        category=category,
        agent=agent,
        discussion_context=discussion_context,
    )
    completion, provider, model, profile_id = await complete_with_profile(
        profile_id=interview_profile_id,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        settings=settings,
    )
    question_text = format_interview_question(
        category=category,
        agent_name=agent.agent_name,
        agent_role=agent.agent_role,
    )
    return (
        question_text,
        completion.text,
        provider,
        model,
        profile_id,
        completion.input_tokens,
        completion.output_tokens,
    )


async def score_interview_response(
    *,
    category: str,
    question_text: str,
    response_text: str,
    judge_profile_id: str,
    temperature: float,
    max_tokens: int,
    settings: Settings | None = None,
    rubric_excerpt: str | None = None,
) -> tuple[int, str, str | None, str, str, str, str, str, int | None, int | None]:
    excerpt = load_rubric_category_excerpt(category) if rubric_excerpt is None else rubric_excerpt
    system, user = build_judge_prompts(
        category=category,
        question_text=question_text,
        response_text=response_text,
        rubric_excerpt=excerpt,
    )
    completion, provider, model, profile_id = await complete_with_profile(
        profile_id=judge_profile_id,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=temperature,
        max_tokens=max_tokens,
        settings=settings,
    )
    raw = completion.text
    score, parse_source, rationale = resolve_judge_score(raw)
    if score is None or parse_source == "unparseable":
        raise ValueError(
            f"judge output for category {category!r} could not be scored "
            f"(parse_source={parse_source!r}); raw={raw[:200]!r}"
        )
    return (
        score,
        score_label(score),
        rationale,
        raw,
        parse_source,
        provider,
        model,
        profile_id,
        completion.input_tokens,
        completion.output_tokens,
    )


def validate_interview_completeness(
    responses: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    *,
    expected_agent_ids: list[str] | set[str] | None = None,
    agents_interviewed: int | None = None,
    categories: tuple[str, ...] | None = None,
) -> None:
    """
    Require a complete agents × categories grid with one score per response.

    ``expected_agent_ids`` must come from simulation snapshots (or the canonical
    bundle), not from response rows alone — partial grids must not satisfy count checks.

    Raises ``ValueError`` when an interrupted or partial run would skew baselines.
    """
    cats = categories or INTERVIEW_CATEGORIES
    if expected_agent_ids is not None:
        expected_agents = sorted({str(aid) for aid in expected_agent_ids if aid})
    elif agents_interviewed is not None:
        agent_ids_from_responses = sorted({str(r.get("agent_id") or "") for r in responses if r.get("agent_id")})
        if len(agent_ids_from_responses) != agents_interviewed:
            raise ValueError(
                f"architectural interview agent mismatch: {len(agent_ids_from_responses)} distinct "
                f"agents in responses, expected {agents_interviewed}"
            )
        expected_agents = agent_ids_from_responses
    else:
        raise ValueError("validate_interview_completeness requires expected_agent_ids or agents_interviewed")

    expected_count = len(expected_agents) * len(cats)
    if len(responses) != expected_count:
        raise ValueError(
            f"architectural interview incomplete: {len(responses)} responses, expected {expected_count}"
        )
    if len(scores) != expected_count:
        raise ValueError(
            f"architectural interview incomplete: {len(scores)} scores, expected {expected_count}"
        )

    grid: dict[str, dict[str, int]] = {}
    for resp in responses:
        aid = str(resp.get("agent_id") or "")
        cat = str(resp.get("category") or "")
        if aid not in expected_agents:
            raise ValueError(f"architectural interview unexpected agent_id {aid!r}")
        if cat not in cats:
            raise ValueError(f"architectural interview unexpected category {cat!r} for agent {aid!r}")
        grid.setdefault(aid, {})
        grid[aid][cat] = grid[aid].get(cat, 0) + 1

    for aid in expected_agents:
        if aid not in grid:
            raise ValueError(f"architectural interview missing agent {aid!r}")
        for cat in cats:
            count = grid[aid].get(cat, 0)
            if count != 1:
                raise ValueError(
                    f"architectural interview agent {aid!r} category {cat!r}: "
                    f"expected 1 response, got {count}"
                )

    response_ids = {str(r["id"]) for r in responses}
    if len(response_ids) != len(responses):
        raise ValueError("architectural interview has duplicate response ids")
    score_by_response = {str(s["response_id"]): s for s in scores}
    if len(score_by_response) != len(scores):
        raise ValueError("architectural interview has duplicate score response_ids")
    missing = response_ids - set(score_by_response)
    if missing:
        raise ValueError(
            f"architectural interview missing judge scores for response ids: {sorted(missing)[:5]}"
        )
    unparseable = [s for s in scores if str(s.get("parse_source") or "") == "unparseable"]
    if unparseable:
        raise ValueError(
            f"architectural interview has {len(unparseable)} unscorable judge rows; "
            "retry or re-run with --force"
        )


def summarize_interview_results(
    responses: list[dict[str, Any]],
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    by_agent: dict[str, dict[str, Any]] = {}
    score_by_response = {s["response_id"]: s for s in scores}
    for resp in responses:
        aid = resp["agent_id"]
        cat = resp["category"]
        sc = score_by_response.get(resp["id"]) or score_by_response.get(resp.get("response_id", ""))
        agent_entry = by_agent.setdefault(
            aid,
            {"agent_id": aid, "agent_name": resp.get("agent_name"), "categories": {}},
        )
        agent_entry["categories"][cat] = {
            "score": sc.get("score") if sc else None,
            "parse_source": sc.get("parse_source") if sc else None,
        }
    scorable_scores = [
        s for s in scores if s.get("score") is not None and s.get("parse_source") != "unparseable"
    ]
    return {
        "rubric_version": effective_rubric_version(),
        "response_count": len(responses),
        "score_count": len(scores),
        "scorable_score_count": len(scorable_scores),
        "parse_source_counts": count_parse_sources(scores),
        "scores": scorable_scores,
        "agents": list(by_agent.values()),
    }


InsertFn = Callable[..., Awaitable[str]]


async def run_architectural_interview_for_simulation(
    *,
    sqlite_path: str,
    simulation_id: str,
    interview_profile_id: str,
    judge_profile_id: str,
    insert_response: InsertFn,
    insert_score: InsertFn,
    get_export_bundle: Callable[[str, str], Awaitable[dict[str, Any] | None]],
    count_existing_responses: Callable[[str, str], Awaitable[int]] | None = None,
    delete_existing: Callable[[str, str], Awaitable[tuple[int, int]]] | None = None,
    force: bool = False,
    temperature: float = 0.2,
    max_tokens: int = 1024,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """
    Administer all five categories to every agent in the latest snapshot round,
    judge each response, and persist rows via injected repo callbacks.
    """
    bundle = await get_export_bundle(sqlite_path, simulation_id)
    if bundle is None:
        raise ValueError(f"simulation {simulation_id!r} not found")

    run = bundle.get("run") or {}
    status = str(run.get("status") or "")
    if status in ("pending", "running"):
        raise ValueError("simulation must be completed or failed before architectural interview")

    if count_existing_responses is not None:
        existing = await count_existing_responses(sqlite_path, simulation_id=simulation_id)
        if existing and not force:
            raise ValueError(
                "architectural interview already exists for this simulation "
                f"({existing} responses); re-run with force=True or --force to replace"
            )
        if existing and force and delete_existing is not None:
            await delete_existing(sqlite_path, simulation_id=simulation_id)

    agents = agents_from_snapshots(bundle.get("agent_state_snapshots") or [])
    if not agents:
        raise ValueError("no agents found in simulation snapshots")

    transcript = bundle.get("transcript") or []
    response_rows: list[dict[str, Any]] = []
    score_rows: list[dict[str, Any]] = []

    for agent in agents:
        context = build_agent_discussion_context(transcript, agent_id=agent.agent_id)
        for category in INTERVIEW_CATEGORIES:
            (
                question_text,
                response_text,
                i_provider,
                i_model,
                i_profile,
                i_in,
                i_out,
            ) = await administer_category_interview(
                category=category,
                agent=agent,
                discussion_context=context,
                interview_profile_id=interview_profile_id,
                temperature=temperature,
                max_tokens=max_tokens,
                settings=settings,
            )
            response_id = await insert_response(
                sqlite_path,
                simulation_id=simulation_id,
                agent_id=agent.agent_id,
                agent_role=agent.agent_role,
                agent_name=agent.agent_name,
                category=category,
                question_text=question_text,
                response_text=response_text,
                interview_provider=i_provider,
                interview_model=i_model,
                interview_profile_id=i_profile,
                input_tokens=i_in,
                output_tokens=i_out,
            )
            (
                score,
                s_label,
                rationale,
                judge_raw,
                parse_source,
                j_provider,
                j_model,
                j_profile,
                j_in,
                j_out,
            ) = await score_interview_response(
                category=category,
                question_text=question_text,
                response_text=response_text,
                judge_profile_id=judge_profile_id,
                temperature=temperature,
                max_tokens=max_tokens,
                settings=settings,
            )
            score_id = await insert_score(
                sqlite_path,
                simulation_id=simulation_id,
                response_id=response_id,
                agent_id=agent.agent_id,
                category=category,
                score=score,
                score_label=s_label,
                rationale=rationale,
                judge_raw_response=judge_raw,
                judge_provider=j_provider,
                judge_model=j_model,
                judge_profile_id=j_profile,
                parse_source=parse_source,
                rubric_version=effective_rubric_version(),
                input_tokens=j_in,
                output_tokens=j_out,
            )
            response_rows.append(
                {
                    "id": response_id,
                    "agent_id": agent.agent_id,
                    "agent_name": agent.agent_name,
                    "category": category,
                }
            )
            score_rows.append(
                {
                    "id": score_id,
                    "response_id": response_id,
                    "agent_id": agent.agent_id,
                    "agent_name": agent.agent_name,
                    "category": category,
                    "score": score,
                    "parse_source": parse_source,
                }
            )

    validate_interview_completeness(
        response_rows,
        score_rows,
        expected_agent_ids=[a.agent_id for a in agents],
    )
    summary = summarize_interview_results(response_rows, score_rows)
    return {
        "simulation_id": simulation_id,
        "interview_profile_id": interview_profile_id,
        "judge_profile_id": judge_profile_id,
        "agents_interviewed": len(agents),
        "categories_per_agent": len(INTERVIEW_CATEGORIES),
        **summary,
    }


def rubric_doc_exists() -> bool:
    return RUBRIC_DOC_PATH.is_file()


def load_rubric_doc_text() -> str:
    return RUBRIC_DOC_PATH.read_text(encoding="utf-8")


def parse_rubric_version_from_md(md_text: str) -> str:
    m = re.search(r"\*\*Rubric version:\*\*\s*`(\d+)`", md_text)
    return m.group(1) if m else RUBRIC_VERSION


def parse_category_excerpt_from_md(md_text: str, category: str) -> str:
    pattern = rf"## {re.escape(category)}\s*\n([\s\S]*?)(?=\n## |\n---|\Z)"
    m = re.search(pattern, md_text)
    if not m:
        return ""
    return m.group(1).strip()


def load_rubric_category_excerpt(category: str) -> str:
    """Load per-category criteria from rubric MD; fall back to inline excerpts."""
    if rubric_doc_exists():
        md_text = load_rubric_doc_text()
        excerpt = parse_category_excerpt_from_md(md_text, category)
        if excerpt:
            return excerpt
    return RUBRIC_EXCERPTS.get(category, "")


def effective_rubric_version() -> str:
    if rubric_doc_exists():
        return parse_rubric_version_from_md(load_rubric_doc_text())
    return RUBRIC_VERSION
