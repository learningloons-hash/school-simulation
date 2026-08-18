#!/usr/bin/env python3
"""MemBench adapter for Senna — participation/observation × factual/reflective scoring."""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_FIXTURES = _REPO_ROOT / "backend/tests/fixtures/membench"

SCENARIO_PARTICIPATION = "participation"
SCENARIO_OBSERVATION = "observation"
MEMORY_FACTUAL = "factual"
MEMORY_REFLECTIVE = "reflective"

# MemBench env scoring (benchmark/env/Membenenv.py): exact multiple-choice letter match.
MemBenchAccuracy = float


class AnswerFn(Protocol):
    def __call__(
        self,
        *,
        scenario: str,
        memory_level: str,
        memory_text: str,
        question: str,
        time: str,
        choices: dict[str, str],
        ground_truth: str,
    ) -> str: ...


@dataclass(frozen=True)
class MemBenchQA:
    question: str
    time: str
    choices: dict[str, str]
    ground_truth: str
    answer: str | None = None
    qid: int | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MemBenchQA:
        return cls(
            qid=raw.get("qid"),
            question=str(raw["question"]),
            time=str(raw["time"]),
            choices={str(k): str(v) for k, v in raw["choices"].items()},
            ground_truth=str(raw["ground_truth"]).strip().upper(),
            answer=raw.get("answer"),
        )


@dataclass(frozen=True)
class MemBenchTrajectory:
    tid: int
    message_list: list[Any]
    qa: MemBenchQA


@dataclass(frozen=True)
class MemBenchFixture:
    scenario: str
    memory_level: str
    source_file: str
    trajectories: tuple[MemBenchTrajectory, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> MemBenchFixture:
        trajs = tuple(
            MemBenchTrajectory(
                tid=int(item["tid"]),
                message_list=list(item["message_list"]),
                qa=MemBenchQA.from_dict(item["QA"]),
            )
            for item in raw["trajectories"]
        )
        return cls(
            scenario=str(raw["scenario"]),
            memory_level=str(raw["memory_level"]),
            source_file=str(raw.get("source_file") or ""),
            trajectories=trajs,
        )


@dataclass
class TrajectoryScore:
    tid: int
    predicted: str
    ground_truth: str
    correct: bool


@dataclass
class MemBenchScoreReport:
    scenario: str
    memory_level: str
    accuracy: MemBenchAccuracy
    correct: int
    total: int
    trajectories: list[TrajectoryScore] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario": self.scenario,
            "memory_level": self.memory_level,
            "accuracy": self.accuracy,
            "correct": self.correct,
            "total": self.total,
            "metric": "memory_accuracy",
            "trajectories": [
                {
                    "tid": t.tid,
                    "predicted": t.predicted,
                    "ground_truth": t.ground_truth,
                    "correct": t.correct,
                }
                for t in self.trajectories
            ],
        }


def score_membench_answer(predicted: str, ground_truth: str) -> bool:
    """MemBench memory accuracy item: predicted choice letter equals ground_truth."""
    return predicted.strip().upper() == ground_truth.strip().upper()


def membench_accuracy(correct: int, total: int) -> MemBenchAccuracy:
    if total == 0:
        return 0.0
    return correct / total


def load_fixture(path: Path) -> MemBenchFixture:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return MemBenchFixture.from_dict(raw)


def discover_fixtures(fixtures_dir: Path) -> dict[tuple[str, str], MemBenchFixture]:
    out: dict[tuple[str, str], MemBenchFixture] = {}
    for path in sorted(fixtures_dir.glob("*.json")):
        fixture = load_fixture(path)
        key = (fixture.scenario, fixture.memory_level)
        if key in out:
            raise ValueError(f"duplicate fixture key {key!r} from {path}")
        out[key] = fixture
    return out


def _format_participation_message(message: dict[str, str]) -> str:
    return "'user': {}; 'agent': {}".format(message["user"], message["agent"])


class SennaMemBenchAgent:
    """Minimal Senna-facing memory runner mirroring MemBench store/recall flow."""

    def __init__(self, *, scenario: str, answer_fn: AnswerFn, memory_level: str) -> None:
        self.scenario = scenario
        self.memory_level = memory_level
        self.answer_fn = answer_fn
        self._memory_lines: list[str] = []

    def reset(self) -> None:
        self._memory_lines = []

    @property
    def memory_text(self) -> str:
        return "\n".join(self._memory_lines)

    def observe(self, message: Any, step: int) -> None:
        if self.scenario == SCENARIO_PARTICIPATION:
            if not isinstance(message, dict):
                raise TypeError("participation messages must be {user, agent} dicts")
            line = f"{step}[|]{_format_participation_message(message)}"
        else:
            line = f"{step}[|]{message}"
        self._memory_lines.append(line)

    def answer(self, qa: MemBenchQA) -> str:
        choice = self.answer_fn(
            scenario=self.scenario,
            memory_level=self.memory_level,
            memory_text=self.memory_text,
            question=qa.question,
            time=qa.time,
            choices=qa.choices,
            ground_truth=qa.ground_truth,
        )
        return choice.strip().upper()


def run_trajectory(
    trajectory: MemBenchTrajectory,
    *,
    scenario: str,
    memory_level: str,
    answer_fn: AnswerFn,
) -> TrajectoryScore:
    agent = SennaMemBenchAgent(
        scenario=scenario,
        memory_level=memory_level,
        answer_fn=answer_fn,
    )
    for step, message in enumerate(trajectory.message_list):
        agent.observe(message, step)
    predicted = agent.answer(trajectory.qa)
    gt = trajectory.qa.ground_truth
    return TrajectoryScore(
        tid=trajectory.tid,
        predicted=predicted,
        ground_truth=gt,
        correct=score_membench_answer(predicted, gt),
    )


def run_fixture(fixture: MemBenchFixture, answer_fn: AnswerFn) -> MemBenchScoreReport:
    results = [
        run_trajectory(
            traj,
            scenario=fixture.scenario,
            memory_level=fixture.memory_level,
            answer_fn=answer_fn,
        )
        for traj in fixture.trajectories
    ]
    correct = sum(1 for r in results if r.correct)
    total = len(results)
    return MemBenchScoreReport(
        scenario=fixture.scenario,
        memory_level=fixture.memory_level,
        accuracy=membench_accuracy(correct, total),
        correct=correct,
        total=total,
        trajectories=results,
    )


def run_all_fixtures(
    fixtures_dir: Path,
    answer_fn: AnswerFn,
) -> dict[tuple[str, str], MemBenchScoreReport]:
    fixtures = discover_fixtures(fixtures_dir)
    return {key: run_fixture(fixture, answer_fn) for key, fixture in fixtures.items()}


def make_ground_truth_agent() -> AnswerFn:
    def _answer(**kwargs: Any) -> str:
        return str(kwargs["ground_truth"]).strip().upper()

    return _answer


def make_memory_match_agent(seed: int) -> AnswerFn:
    """Deterministic stub: match choice text in memory, else seeded fallback letter."""

    rng = random.Random(seed)

    def _answer(**kwargs: Any) -> str:
        memory = str(kwargs["memory_text"]).lower()
        choices: dict[str, str] = kwargs["choices"]
        for letter in sorted(choices):
            if choices[letter].lower() in memory:
                return letter
        letters = sorted(choices)
        return letters[rng.randint(0, len(letters) - 1)]

    return _answer


def summarize_reports(
    reports: dict[tuple[str, str], MemBenchScoreReport],
) -> dict[str, Any]:
    return {
        "participation": {
            "factual": reports[(SCENARIO_PARTICIPATION, MEMORY_FACTUAL)].to_dict(),
            "reflective": reports[(SCENARIO_PARTICIPATION, MEMORY_REFLECTIVE)].to_dict(),
        },
        "observation": {
            "factual": reports[(SCENARIO_OBSERVATION, MEMORY_FACTUAL)].to_dict(),
            "reflective": reports[(SCENARIO_OBSERVATION, MEMORY_REFLECTIVE)].to_dict(),
        },
    }


def _required_fixture_keys(reports: dict[tuple[str, str], MemBenchScoreReport]) -> None:
    required = {
        (SCENARIO_PARTICIPATION, MEMORY_FACTUAL),
        (SCENARIO_PARTICIPATION, MEMORY_REFLECTIVE),
        (SCENARIO_OBSERVATION, MEMORY_FACTUAL),
        (SCENARIO_OBSERVATION, MEMORY_REFLECTIVE),
    }
    missing = required - set(reports)
    if missing:
        raise ValueError(f"missing fixture combinations: {sorted(missing)}")


def run_membench_suite(
    *,
    fixtures_dir: Path,
    seed: int,
    answer_mode: str = "memory_match",
) -> dict[str, Any]:
    if answer_mode == "ground_truth":
        answer_fn = make_ground_truth_agent()
    elif answer_mode == "memory_match":
        answer_fn = make_memory_match_agent(seed)
    else:
        raise ValueError(f"unknown answer_mode {answer_mode!r}")

    reports = run_all_fixtures(fixtures_dir, answer_fn)
    _required_fixture_keys(reports)
    payload = summarize_reports(reports)
    payload["seed"] = seed
    payload["answer_mode"] = answer_mode
    payload["fixtures_dir"] = str(fixtures_dir)
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Senna agents on MemBench fixture scenarios")
    parser.add_argument(
        "command",
        choices=("run",),
        help="Run vendored MemBench fixtures and print score report JSON",
    )
    parser.add_argument(
        "--fixtures-dir",
        type=Path,
        default=_DEFAULT_FIXTURES,
        help="Directory containing participation/observation × factual/reflective JSON fixtures",
    )
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for deterministic stub agent")
    parser.add_argument(
        "--answer-mode",
        choices=("memory_match", "ground_truth"),
        default="memory_match",
        help="Stub agent strategy (no live LLM in iter-46)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        report = run_membench_suite(
            fixtures_dir=args.fixtures_dir.resolve(),
            seed=args.seed,
            answer_mode=args.answer_mode,
        )
        print(json.dumps(report, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
