"""Two-pass judge-model harness for SSTRF RQ1 scoring (GM-F v2, iter-57)."""

from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from mirofish_backend.config import Settings, get_settings
from mirofish_backend.llm.model_profiles import (
    OPENAI_DEFAULT_ID,
    OPENROUTER_DEFAULT_ID,
    get_builtin_profile,
    resolve_api_key_from_env,
)
from mirofish_backend.llm.openai_compatible_client import chat_completion_openai_compatible

from sstrf_scoring_evidence import TrialEvidence, build_rater_payload

from sstrf_scoring_cells import (
    JUDGEMENTS_PER_TRIAL,
    PER_AGENT_PROPOSITIONS,
    PROPOSITION_IDS,
    SCORED_STAFF_AGENTS,
    all_trial_cell_ids,
    proposition_for_cell,
    trial_cell_id,
)

VALID_SCORES = frozenset({-1, 0, 1, 2})

# GM-F v2 §1 — verbatim
PROPOSITIONS_VERBATIM: dict[str, str] = {
    "P1": "Authority for innovation sits at the school level rather than with individual teachers.",
    "P2": (
        "The school level filters policy: what reaches the classroom has been interpreted and "
        "reshaped by school leadership rather than transmitted intact."
    ),
    "P3": (
        "Teachers do not regard themselves as policy actors in their own right; they regard "
        "themselves as part of a cohesive national implementation effort."
    ),
    "P4": "Adaptation is small in scale and intended to mesh with policy, not to depart from it.",
    "P5": "Policy is perceived as less flexible than it was intended to be.",
}

# GM-F v2 §2.3 — per-agent scale (verbatim)
SCALE_VERBATIM = """| Score | Meaning |
|---|---|
| **2** | Clearly exhibited. Evident in this agent's conduct or account without prompting toward it. |
| **1** | Partially exhibited. Present but weak, hedged, ambiguous, or only when directly asked. |
| **0** | Not addressed. No discernible evidence either way. |
| **−1** | Contradicted. Positive evidence of the opposite dynamic. |"""

# Pre-reg §3.3 — verbatim instructions
INSTRUCTIONS_VERBATIM = (
    "Score only from the supplied text; do not reward eloquence or penalise "
    "brevity; a proposition asserted by an agent when directly asked counts as weaker "
    "evidence (max score 1) than the same pattern arising unprompted in round "
    "transcripts; \"contradicted\" requires positive evidence of the opposite dynamic, "
    "not mere absence."
)

# Supplementary (not pre-reg verbatim) — appended in build_rubric_block() after §3.3.
JUDGE_SUPPLEMENTARY_GUIDANCE = (
    "Some passages describe a policy or authority explicitly NOT being exercised "
    "as the proposition describes, even while using the same vocabulary (school "
    "leadership, HOD, MOE, department) — score these −1, not 2. Matching "
    "vocabulary is not evidence of the dynamic; read what the passage says "
    "actually happened."
)
JUDGE_CONTRADICTION_GUIDANCE_LOCATION = "build_rubric_block supplementary section (JUDGE_SUPPLEMENTARY_GUIDANCE)"

JUDGE_SYSTEM_PROMPT = (
    "You are an independent judge scoring CIEPSS correspondence propositions. "
    "Use only the supplied evidence. Respond with JSON only."
)

JUDGE_BACKUP_MODEL = "gpt-4o-mini"
JUDGE_PRIMARY_MODEL = "gpt-4o"
JUDGE_OPENROUTER_MODEL = "openai/gpt-4o-mini"
JUDGE_TEMPERATURE = 0.0
JUDGE_MAX_TOKENS = 512

CALIBRATION_ITEMS: list[dict[str, Any]] = [
    {
        "item_id": 1,
        "passage": "When new MOE initiatives arrive, it's really the school leadership who decides how they get implemented — individual teachers don't have the authority to redesign the curriculum on their own, though they can make small tweaks that still fit within what the school and MOE expect.",
        "expected_proposition": "P1",
        "expected_score": 2,
    },
    {
        "item_id": 2,
        "passage": "School leadership deliberately stepped back on this one. We were told the department would not be setting a common approach, and that whatever each of us decided for our own classes would stand — even where that meant two teachers on the same level running quite different programmes. Nobody was asked to align it upward.",
        "expected_proposition": "P1",
        "expected_score": -1,
    },
    {
        "item_id": 3,
        "passage": "Before anything from MOE reaches the classroom, it passes through the school's own leadership and department heads, who interpret and reshape it — what finally lands with the teacher isn't the raw MOE directive but something the school has already filtered.",
        "expected_proposition": "P2",
        "expected_score": 2,
    },
    {
        "item_id": 4,
        "passage": "The HOD's role here was really just to forward the circular. She said outright that she didn't want to put her own gloss on it, so what we each read was the MOE document itself, and we worked out our own reading of it without the department shaping that either way.",
        "expected_proposition": "P2",
        "expected_score": -1,
    },
    {
        "item_id": 5,
        "passage": "The teacher didn't talk about herself as someone shaping policy — she saw her role as carrying out a shared, nationwide effort, part of something larger than her own classroom decisions.",
        "expected_proposition": "P3",
        "expected_score": 2,
    },
    {
        "item_id": 6,
        "passage": "I do see myself as making policy here, not just receiving it. What we settle on in this school about how the initiative actually runs is the policy, as far as our students are concerned. The national framing is really a backdrop — I don't think of my work as part of some larger rollout.",
        "expected_proposition": "P3",
        "expected_score": -1,
    },
    {
        "item_id": 7,
        "passage": "She adjusted the materials to suit her students, but the changes were minor tweaks to make things easier to use — she never questioned or departed from the curriculum itself.",
        "expected_proposition": "P4",
        "expected_score": 2,
    },
    {
        "item_id": 8,
        "passage": "We kept the MOE labels on it, because that is what the paperwork wants. Underneath, though, we have rebuilt the sequence completely — different assessment points, different order, and we dropped two of the required components because they don't serve our students. On paper it looks aligned.",
        "expected_proposition": "P4",
        "expected_score": -1,
    },
    {
        "item_id": 9,
        "passage": "For the most part, the new MOE guidance made its way down to the classroom without much resistance and was broadly accepted, though some staff felt it was more rigid in practice than it was probably meant to be.",
        "expected_proposition": "P5",
        "expected_score": 2,
    },
    {
        "item_id": 10,
        "passage": "Honestly, most of it never landed. Two years on, a fair number of staff still could not tell you what the initiative actually requires, and there was never enough definition in it to argue about one way or the other — people simply carried on as before.",
        "expected_proposition": "P5",
        "expected_score": -1,
    },
    # GM-F v2 §4 — C1–C5 (gold=1 partial-presence; verbatim)
    {
        "item_id": 13,
        "item_kind": "partial_presence",
        "calibration_id": "C1",
        "passage": (
            "I suppose the department does set the direction, broadly. I hadn't really thought "
            "about it. We were told at the start of term what the focus was, and I've gone along "
            "with that."
        ),
        "expected_proposition": "P1",
        "expected_score": 1,
    },
    {
        "item_id": 14,
        "item_kind": "partial_presence",
        "calibration_id": "C2",
        "passage": (
            "The HOD went through the circular with us at the level meeting. She read out the "
            "parts she thought mattered most for our level."
        ),
        "expected_proposition": "P2",
        "expected_score": 1,
    },
    {
        "item_id": 15,
        "item_kind": "partial_presence",
        "calibration_id": "C3",
        "passage": "No, I wouldn't say I make policy. That's not really my role, is it.",
        "expected_proposition": "P3",
        "expected_score": 1,
    },
    {
        "item_id": 16,
        "item_kind": "partial_presence",
        "calibration_id": "C4",
        "passage": "I changed the worksheet a bit for my class. Simplified some of the wording.",
        "expected_proposition": "P4",
        "expected_score": 1,
    },
    {
        "item_id": 17,
        "item_kind": "partial_presence",
        "calibration_id": "C5",
        "passage": (
            "It's quite prescriptive, the way it's come down. Though I imagine they had their "
            "reasons."
        ),
        "expected_proposition": "P5",
        "expected_score": 1,
    },
]

# Non-gating probes (calibration set items 11–12; GM-F signed 2026-08-08, Ops token fix 2026-08-11).
# Scored with the same rubric/call as CALIBRATION_ITEMS but excluded from the 8/10 gate.
PROBE_ITEMS: list[dict[str, Any]] = [
    {
        "item_id": 11,
        "probe_kind": "on_topic_scope_silent",
        "passage": (
            "We have been reworking the Primary 2 materials this term. Some of it is mine, "
            "some came out of the level meeting. It is ongoing — we will see how it settles "
            "by the end of the year."
        ),
        "expected_proposition": "P4",
        "expected_score": 0,
    },
    {
        "item_id": 12,
        "probe_kind": "vocabulary_adjacent_absence",
        "passage": (
            "Our school is fairly small, so a lot of decisions just happen over lunch in the "
            "staff room rather than through any formal process — who is covering recess duty, "
            "whether we swap classrooms for an activity, that sort of thing."
        ),
        "expected_proposition": "P1",
        "expected_score": 0,
    },
]


@dataclass
class CalibrationItemResult:
    item_id: int
    expected_proposition: str
    expected_score: int
    actual_proposition: str
    actual_score: int
    scored_correctly: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "expected_proposition": self.expected_proposition,
            "expected_score": self.expected_score,
            "actual_proposition": self.actual_proposition,
            "actual_score": self.actual_score,
            "scored_correctly": self.scored_correctly,
        }


@dataclass
class ProbeItemResult:
    item_id: int
    probe_kind: str
    expected_proposition: str
    expected_score: int
    actual_proposition: str
    actual_score: int
    scored_correctly: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "probe_kind": self.probe_kind,
            "expected_proposition": self.expected_proposition,
            "expected_score": self.expected_score,
            "actual_proposition": self.actual_proposition,
            "actual_score": self.actual_score,
            "scored_correctly": self.scored_correctly,
        }


@dataclass
class CalibrationPassResult:
    gate_correct: int
    model_id: str
    profile_id: str
    gate_item_results: list[CalibrationItemResult] = field(default_factory=list)
    probe_results: list[ProbeItemResult] = field(default_factory=list)

    def to_gate_dicts(self) -> list[dict[str, Any]]:
        return [g.to_dict() for g in self.gate_item_results]

    def to_probe_dicts(self) -> list[dict[str, Any]]:
        return [p.to_dict() for p in self.probe_results]


CALIBRATION_GATE_ITEM_COUNT = len(CALIBRATION_ITEMS)
# 12/15 ≡ 8/10 at 80%; GM-F v2 §4 aggregate + iter-43 double-miss rule
CALIBRATION_GATE_THRESHOLD = 12
CALIBRATION_GATE_THRESHOLD_EQUIVALENT = "8/10"
CALIBRATION_MAX_INCORRECT_PER_PROPOSITION = 1


def _gate_item_fields(item: CalibrationItemResult | dict[str, Any]) -> tuple[str, bool]:
    if isinstance(item, CalibrationItemResult):
        return item.expected_proposition, item.scored_correctly
    return str(item["expected_proposition"]), bool(item["scored_correctly"])


def count_gate_correct(gate_items: list[CalibrationItemResult] | list[dict[str, Any]]) -> int:
    return sum(1 for item in gate_items if _gate_item_fields(item)[1])


def proposition_incorrect_counts(
    gate_items: list[CalibrationItemResult] | list[dict[str, Any]],
) -> dict[str, int]:
    counts = {pid: 0 for pid in PROPOSITION_IDS}
    for item in gate_items:
        prop, scored_correctly = _gate_item_fields(item)
        if not scored_correctly:
            counts[prop] += 1
    return counts


def no_proposition_double_miss(
    gate_items: list[CalibrationItemResult] | list[dict[str, Any]],
    *,
    max_incorrect_per_proposition: int = CALIBRATION_MAX_INCORRECT_PER_PROPOSITION,
) -> bool:
    """True when no proposition has more than ``max_incorrect_per_proposition`` misses."""
    return all(
        count <= max_incorrect_per_proposition
        for count in proposition_incorrect_counts(gate_items).values()
    )


def calibration_gate_passes(
    *,
    pass_1_items: list[CalibrationItemResult] | list[dict[str, Any]],
    pass_2_items: list[CalibrationItemResult] | list[dict[str, Any]],
    threshold: int = CALIBRATION_GATE_THRESHOLD,
) -> bool:
    """15-item gate: ≥threshold/15 both passes and ≤1 miss per proposition each pass."""
    pass_1_correct = count_gate_correct(pass_1_items)
    pass_2_correct = count_gate_correct(pass_2_items)
    if pass_1_correct < threshold or pass_2_correct < threshold:
        return False
    return no_proposition_double_miss(pass_1_items) and no_proposition_double_miss(pass_2_items)


@dataclass
class JudgeProfileSpec:
    profile_id: str
    model_id: str | None = None


@dataclass
class JudgePassResult:
    scores: dict[str, int]
    proposition_order: list[str]
    agent_orders: dict[str, list[str]]
    elicitation_order: list[int]
    transcript_order: list[int]
    judge_model_id: str
    parse_failed: list[str] = field(default_factory=list)


JudgeCallFn = Callable[..., Awaitable[tuple[str, str]]]


def shuffle_orders(
    seed: int,
    *,
    elicitation_count: int,
    transcript_count: int,
) -> tuple[list[str], dict[str, list[str]], list[int], list[int]]:
    """Shuffle proposition order, per-proposition agent order, elicitation and transcript."""
    rng = random.Random(seed)
    props = list(PER_AGENT_PROPOSITIONS)
    rng.shuffle(props)
    props.append("P2")
    agent_orders: dict[str, list[str]] = {}
    for pid in PER_AGENT_PROPOSITIONS:
        agents = list(SCORED_STAFF_AGENTS)
        rng.shuffle(agents)
        agent_orders[pid] = agents
    elic_order = list(range(elicitation_count))
    rng.shuffle(elic_order)
    trans_order = list(range(transcript_count))
    rng.shuffle(trans_order)
    return props, agent_orders, elic_order, trans_order


def build_rubric_block() -> str:
    staff = ", ".join(SCORED_STAFF_AGENTS)
    lines = [
        "## Binding propositions (GM-F v2 §1)",
        "",
        f"Score P1, P3, P4 and P5 **per staff agent** ({staff}). Score P2 **once per trial**.",
        "",
    ]
    for pid in PROPOSITION_IDS:
        lines.append(f"- **{pid}:** {PROPOSITIONS_VERBATIM[pid]}")
    lines.extend(
        [
            "",
            "## Scoring scale (§2.3)",
            "",
            SCALE_VERBATIM,
            "",
            "## Instructions (§2.3)",
            "",
            INSTRUCTIONS_VERBATIM,
            "",
            "## Supplementary guidance",
            "",
            JUDGE_SUPPLEMENTARY_GUIDANCE,
        ]
    )
    return "\n".join(lines)


def build_judge_user_prompt(
    evidence: TrialEvidence,
    *,
    proposition_order: list[str],
    agent_orders: dict[str, list[str]],
    elicitation_order: list[int],
    transcript_order: list[int],
) -> str:
    payload = build_rater_payload(evidence)
    elicitation = [payload["elicitation"][i] for i in elicitation_order]
    transcript = [payload["transcript"][i] for i in transcript_order]
    prop_block = "\n".join(
        f"{pid}: {PROPOSITIONS_VERBATIM[pid]}" for pid in PROPOSITION_IDS
    )
    score_keys = all_trial_cell_ids()
    example = {key: "<int>" for key in score_keys}
    return (
        f"{build_rubric_block()}\n\n"
        f"Score in this proposition order: {', '.join(proposition_order)}\n"
        f"Within each per-agent proposition, score agents in the order given in agent_orders.\n\n"
        f"## Elicitation responses (staff only)\n{json.dumps(elicitation, indent=2)}\n\n"
        f"## Round transcript\n{json.dumps(transcript, indent=2)}\n\n"
        f"Return JSON only with exactly these {JUDGEMENTS_PER_TRIAL} keys "
        f"(per-agent: P1:agent_id, …; trial-level: P2):\n"
        f"{json.dumps(example, indent=2)}\n\n"
        f"Proposition reference:\n{prop_block}\n\n"
        f"Agent order this pass:\n{json.dumps(agent_orders, indent=2)}"
    )


def build_calibration_prompt(item: dict[str, Any]) -> str:
    return (
        f"{build_rubric_block()}\n\n"
        f"Calibration passage:\n{item['passage']}\n\n"
        "Identify which single proposition (P1–P5) this passage best relates to and score it "
        "using the scale above. Return JSON: "
        '{"proposition": "P1", "score": 2}'
    )


def parse_trial_scores(text: str) -> dict[str, int]:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in judge response")
    data = json.loads(match.group(0))
    scores: dict[str, int] = {}
    for cell_id in all_trial_cell_ids():
        if cell_id not in data:
            raise ValueError(f"missing {cell_id}")
        val = int(data[cell_id])
        if val not in VALID_SCORES:
            raise ValueError(f"invalid score for {cell_id}: {val}")
        scores[cell_id] = val
    return scores


def parse_calibration_score(text: str) -> tuple[str, int]:
    match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
    if not match:
        raise ValueError("no JSON object in calibration response")
    data = json.loads(match.group(0))
    prop = str(data.get("proposition") or data.get("proposition_id") or "").upper()
    score = int(data["score"])
    if prop not in PROPOSITION_IDS:
        raise ValueError(f"invalid proposition {prop!r}")
    if score not in VALID_SCORES:
        raise ValueError(f"invalid score {score}")
    return prop, score


def resolve_judge_chain(settings: Settings | None = None) -> list[JudgeProfileSpec]:
    return [
        JudgeProfileSpec(OPENAI_DEFAULT_ID, model_id=JUDGE_PRIMARY_MODEL),
        JudgeProfileSpec(OPENAI_DEFAULT_ID, model_id=JUDGE_BACKUP_MODEL),
        JudgeProfileSpec(OPENROUTER_DEFAULT_ID, model_id=JUDGE_OPENROUTER_MODEL),
    ]


def profile_spec_from_calibration_gate(gate: dict[str, Any]) -> JudgeProfileSpec:
    """Select the judge profile that passed calibration (pre-reg §3.5)."""
    profile_id = str(gate.get("judge_profile_id") or "").strip()
    model_id = str(gate.get("judge_model_id") or "").strip() or None
    if profile_id:
        return JudgeProfileSpec(profile_id, model_id=model_id)
    if model_id:
        for spec in resolve_judge_chain():
            resolved_model = spec.model_id or JUDGE_PRIMARY_MODEL
            if model_id == resolved_model:
                return JudgeProfileSpec(spec.profile_id, model_id=model_id)
    return resolve_judge_chain()[0]


def resolve_profile_model(spec: JudgeProfileSpec, settings: Settings) -> tuple[str, str, str]:
    profile = get_builtin_profile(spec.profile_id, settings)
    if profile is None:
        raise RuntimeError(f"unknown profile {spec.profile_id!r}")
    if profile.provider_type == "anthropic":
        raise RuntimeError("Anthropic provider prohibited for judging (pre-reg §3.1)")
    model_id = spec.model_id or profile.model_id
    if "claude" in model_id.lower():
        raise RuntimeError(f"Claude model route prohibited for judging: {model_id!r}")
    base_url = profile.base_url or ""
    if not base_url:
        raise RuntimeError(f"profile {spec.profile_id!r} missing base_url")
    api_key = resolve_api_key_from_env(profile.api_key_env)
    return base_url, model_id, api_key


async def default_judge_call(
    *,
    messages: list[dict[str, str]],
    profile_spec: JudgeProfileSpec,
    settings: Settings | None = None,
) -> tuple[str, str]:
    settings = settings or get_settings()
    base_url, model_id, api_key = resolve_profile_model(profile_spec, settings)
    text, _, _ = await chat_completion_openai_compatible(
        base_url=base_url,
        model=model_id,
        messages=messages,
        temperature=JUDGE_TEMPERATURE,
        max_tokens=JUDGE_MAX_TOKENS,
        api_key=api_key or None,
    )
    return text, model_id


async def run_judge_pass(
    evidence: TrialEvidence,
    *,
    pass_seed: int,
    profile_spec: JudgeProfileSpec,
    judge_call: JudgeCallFn | None = None,
    settings: Settings | None = None,
) -> JudgePassResult:
    prop_order, agent_orders, elic_order, trans_order = shuffle_orders(
        pass_seed,
        elicitation_count=len(build_rater_payload(evidence)["elicitation"]),
        transcript_count=len(evidence.transcript),
    )
    user_prompt = build_judge_user_prompt(
        evidence,
        proposition_order=prop_order,
        agent_orders=agent_orders,
        elicitation_order=elic_order,
        transcript_order=trans_order,
    )
    system_prompt = JUDGE_SYSTEM_PROMPT
    call = judge_call or default_judge_call
    parse_failed: list[str] = []
    model_id = profile_spec.model_id or "unknown"
    cell_ids = all_trial_cell_ids()
    for attempt in range(2):
        try:
            text, model_id = await call(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                profile_spec=profile_spec,
                settings=settings,
            )
            scores = parse_trial_scores(text)
            return JudgePassResult(
                scores=scores,
                proposition_order=prop_order,
                agent_orders=agent_orders,
                elicitation_order=elic_order,
                transcript_order=trans_order,
                judge_model_id=model_id,
                parse_failed=parse_failed,
            )
        except (ValueError, json.JSONDecodeError, KeyError):
            if attempt == 1:
                parse_failed = list(cell_ids)
                return JudgePassResult(
                    scores={cid: 0 for cid in cell_ids},
                    proposition_order=prop_order,
                    agent_orders=agent_orders,
                    elicitation_order=elic_order,
                    transcript_order=trans_order,
                    judge_model_id=model_id,
                    parse_failed=parse_failed,
                )
    raise RuntimeError("unreachable")


async def run_calibration_pass(
    *,
    pass_seed: int,
    profile_spec: JudgeProfileSpec,
    judge_call: JudgeCallFn | None = None,
    settings: Settings | None = None,
) -> CalibrationPassResult:
    rng = random.Random(pass_seed)
    items = CALIBRATION_ITEMS.copy()
    rng.shuffle(items)
    call = judge_call or default_judge_call
    gate_correct = 0
    gate_item_results: list[CalibrationItemResult] = []
    model_id = profile_spec.model_id or "unknown"
    system_prompt = JUDGE_SYSTEM_PROMPT

    for item in items:
        text, model_id = await call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_calibration_prompt(item)},
            ],
            profile_spec=profile_spec,
            settings=settings,
        )
        prop, score = parse_calibration_score(text)
        scored_correctly = (
            prop == item["expected_proposition"] and score == item["expected_score"]
        )
        if scored_correctly:
            gate_correct += 1
        gate_item_results.append(
            CalibrationItemResult(
                item_id=int(item["item_id"]),
                expected_proposition=str(item["expected_proposition"]),
                expected_score=int(item["expected_score"]),
                actual_proposition=prop,
                actual_score=score,
                scored_correctly=scored_correctly,
            )
        )

    probe_results: list[ProbeItemResult] = []
    for probe in PROBE_ITEMS:
        text, model_id = await call(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": build_calibration_prompt(probe)},
            ],
            profile_spec=profile_spec,
            settings=settings,
        )
        prop, score = parse_calibration_score(text)
        probe_results.append(
            ProbeItemResult(
                item_id=int(probe["item_id"]),
                probe_kind=str(probe["probe_kind"]),
                expected_proposition=str(probe["expected_proposition"]),
                expected_score=int(probe["expected_score"]),
                actual_proposition=prop,
                actual_score=score,
                scored_correctly=(
                    prop == probe["expected_proposition"]
                    and score == probe["expected_score"]
                ),
            )
        )

    return CalibrationPassResult(
        gate_correct=gate_correct,
        model_id=model_id,
        profile_id=profile_spec.profile_id,
        gate_item_results=gate_item_results,
        probe_results=probe_results,
    )
