"""CIEPSS Appendix B/C instrument text for SSTRF elicitation (pre-reg §2.2)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

# Distinctive phrases from pre-reg §2.1 P1–P5 — must not appear in elicitation prompts.
FORBIDDEN_CONTAMINATION_PHRASES: tuple[str, ...] = (
    "authority for innovation devolves",
    "school level but not to individual teachers",
    "acts as a strong filter",
    "strong filter for policy",
    "policy actors in their own right",
    "cohesive national implementation strategy",
    "small-scale adaptations",
    "mesh with moe policy, not departures",
    "travel relatively well through the system",
    "less flexible than intended",
    "binding benchmarkable proposition",
    "correspondence criterion",
)

# Stable bracket fills from ciepss_school_b policy_events (handoff §3).
BRACKET_FILLS: dict[str, str] = {
    "[PERI]": "PERI",
    "[the curriculum change]": "the PERI/STELLAR curriculum reforms",
    "[the initiatives]": "the PERI/STELLAR initiatives",
    "[the initiative have]": "the PERI/STELLAR initiatives have",
    "[your concerns]": "your concerns",
}

CIEPSS_STUDY_ID = "ciepss_school_b"

TEACHER_INSTRUMENT = "CIEPSS Appendix B — Teacher (P2 form teacher)"
TEACHER_QUESTIONS: tuple[str, ...] = (
    "What is the focus of curriculum change in this school?",
    "How do you feel about the new initiatives that are being implemented?",
    "Who decides what teaching strategies/content in your classroom?",
    "Where do you find help in understanding and implementing new curriculum ideas?",
    "Since the PERI/STELLAR reform has been started, can you talk about a lesson that you think worked well?",
    "How do you know when the students are really engaged?",
    "Can you talk about the ways in which you think children learn best?",
    "Is there anything else you would like to tell me? Or is there a question you hoped I would ask?",
)

HOD_SENIOR_INSTRUMENT = "CIEPSS Appendix B — HOD / Senior Teacher / Teacher Mentor"
HOD_SENIOR_QUESTIONS: tuple[str, ...] = (
    "How do you feel about implementing new initiatives in your school?",
    'What would you say is the "push" or focus of curriculum/pedagogical change here?',
    "Who/where do you expect to find help or guidance in implementing new initiatives?",
    "How will you be monitoring the progress of the new initiatives?",
    "How will you encourage and help your staff in implementing the initiatives?",
    "What information and/or PD have you been able to provide to help staff understand the changes?",
    "What processes are in place to listen to the teachers' suggestions for plans and practices in carrying out the initiatives?",
    "Is there a question or something you hoped I would ask you about and I didn't? What else would you like to share with me, or emphasize again, about your experiences in managing changes in your department?",
)

VP_INSTRUMENT = "CIEPSS Appendix B — Vice-Principal"
VP_QUESTIONS: tuple[str, ...] = (
    "What is the focus of curriculum (change?) in this school?",
    "How would you describe the essence of this change?",
    "How do you feel about implementing the new initiatives from PERI?",
    "Can you please talk about the procedures you have in place to build confidence in your staff in implementing the new initiatives?",
    "Can you describe the processes for developing teaching plans and practices at this school?",
    "Where do you get the guidelines for new initiatives?",
    "Where can you find advice/information about PD for your staff in relation to the PERI/STELLAR initiatives?",
    "What PD have you found to be very useful for your staff?",
    "How will you know if an initiative has been successful/is worth pursuing?",
    "Where would you like to see the changes heading from here?",
    "What challenges can you identify for the PERI/STELLAR initiatives?",
    "What strengths/weaknesses do you think the PERI/STELLAR initiatives have?",
    "How do you identify progress with regard to the PERI/STELLAR initiatives?",
    "Who do you report your concerns to with regard to the PERI/STELLAR initiatives? Can you talk me through that process?",
    "Is there a question or something you hoped I would ask you about and I didn't? What else would you like to share with me, or emphasize again, about the experiences in this school?",
)

PARENT_INSTRUMENT = "CIEPSS Appendix C — Parent focus-group protocol (individual elicitation)"
PARENT_QUESTIONS: tuple[str, ...] = (
    "If you were in charge of education for Singapore (i.e., if you were the one shaping educational policy), what types of educational opportunities would you like to see more of for P1–P2 children? Why? What would you like to see less of? Why?",
    "Have you heard or read about the new ideas the Ministry of Education has for P1 and P2? If yes, how do you feel about the new initiatives that are being implemented?",
    "There are three policy changes MOE has recently proposed for early primary education — called PERI. I would be interested in your views on how you feel about each of these three initiatives:\n"
    "   a. single session schools (i.e., instead of a morning and an afternoon session in primary schools, only one group of children would attend that school per day);\n"
    "   b. formative assessment (i.e., this would involve more classroom-based assessment, such as children's portfolios of their learning, and less emphasis on high-stakes examinations);\n"
    "   c. a stronger emphasis on social-emotional aspects of education (i.e., in addition to academic subjects, there would be more time and space for subjects such as art, music and physical education within the week's curriculum).",
)


def apply_bracket_fills(text: str) -> str:
    out = text
    for bracket, fill in BRACKET_FILLS.items():
        out = out.replace(bracket, fill)
    return out


def _normalize_questions(questions: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(apply_bracket_fills(q) for q in questions)


TEACHER_QUESTIONS_RESOLVED = _normalize_questions(TEACHER_QUESTIONS)
HOD_SENIOR_QUESTIONS_RESOLVED = _normalize_questions(HOD_SENIOR_QUESTIONS)
VP_QUESTIONS_RESOLVED = _normalize_questions(VP_QUESTIONS)
PARENT_QUESTIONS_RESOLVED = _normalize_questions(PARENT_QUESTIONS)

CIEPSS_EXPECTED_PERSONA_IDS: tuple[str, ...] = (
    "vice_principal_001",
    "hod_english_001",
    "senior_teacher_001",
    "teacher_001",
    "parent_001",
    "parent_002",
    "parent_003",
    "parent_004",
)


def _ciepss_instrument_for_persona(persona_id: str) -> tuple[str, tuple[str, ...]]:
    if persona_id == "teacher_001":
        return TEACHER_INSTRUMENT, TEACHER_QUESTIONS_RESOLVED
    if persona_id in ("hod_english_001", "senior_teacher_001"):
        return HOD_SENIOR_INSTRUMENT, HOD_SENIOR_QUESTIONS_RESOLVED
    if persona_id == "vice_principal_001":
        return VP_INSTRUMENT, VP_QUESTIONS_RESOLVED
    if persona_id.startswith("parent_"):
        return PARENT_INSTRUMENT, PARENT_QUESTIONS_RESOLVED
    raise ValueError(f"no elicitation instrument for persona_id={persona_id!r}")


InstrumentResolver = Callable[[str], tuple[str, tuple[str, ...]]]


@dataclass(frozen=True)
class StudyInstrumentRegistry:
    study_id: str
    expected_persona_ids: tuple[str, ...]
    resolve: InstrumentResolver


_STUDY_REGISTRIES: dict[str, StudyInstrumentRegistry] = {}


def _register_default_studies() -> None:
    if CIEPSS_STUDY_ID not in _STUDY_REGISTRIES:
        register_study_registry(
            StudyInstrumentRegistry(
                study_id=CIEPSS_STUDY_ID,
                expected_persona_ids=CIEPSS_EXPECTED_PERSONA_IDS,
                resolve=_ciepss_instrument_for_persona,
            )
        )


def register_study_registry(registry: StudyInstrumentRegistry) -> None:
    _STUDY_REGISTRIES[registry.study_id] = registry


def get_study_registry(study_id: str) -> StudyInstrumentRegistry:
    _register_default_studies()
    if study_id not in _STUDY_REGISTRIES:
        raise KeyError(f"unknown study_id for elicitation instruments: {study_id!r}")
    return _STUDY_REGISTRIES[study_id]


def persona_id_from_agent_id(agent_id: str) -> str:
    """Strip roster slot suffix ``_{idx:03d}`` from simulation agent_id."""
    if re.fullmatch(r".+_\d{3}", agent_id):
        return agent_id.rsplit("_", 1)[0]
    return agent_id


def instrument_for_persona(persona_id: str, *, study_id: str = CIEPSS_STUDY_ID) -> tuple[str, tuple[str, ...]]:
    return get_study_registry(study_id).resolve(persona_id)


def expected_elicitation_persona_ids(*, study_id: str = CIEPSS_STUDY_ID) -> tuple[str, ...]:
    return get_study_registry(study_id).expected_persona_ids


def build_elicitation_user_prompt(
    *,
    questions: tuple[str, ...],
    transcript_context: str | None = None,
    instrument_label: str | None = None,
) -> str:
    label = (instrument_label or "elicitation interview").strip()
    lines = [
        f"You are now at the end of the simulation. A researcher is administering the "
        f"published {label} to you. Answer each question below in character, drawing on "
        "everything that happened across all simulation rounds. "
        "Number your answers to match the questions.",
        "",
    ]
    if transcript_context:
        lines.append(transcript_context.strip())
        lines.append("")
    for i, question in enumerate(questions, start=1):
        lines.append(f"{i}. {question}")
        lines.append("")
    return "\n".join(lines).strip()


def contamination_hits(text: str) -> list[str]:
    lowered = text.lower()
    return [phrase for phrase in FORBIDDEN_CONTAMINATION_PHRASES if phrase.lower() in lowered]


def assert_no_contamination(text: str, *, label: str) -> None:
    hits = contamination_hits(text)
    if hits:
        raise RuntimeError(f"contamination guard failed for {label}: matched {hits!r}")


def validate_instruments(*, study_id: str = CIEPSS_STUDY_ID) -> dict[str, Any]:
    """Pre-flight check: all instruments resolve and pass contamination guard."""
    registry = get_study_registry(study_id)
    report: dict[str, Any] = {"study_id": study_id, "instruments": [], "passed": True}
    for persona_id in registry.expected_persona_ids:
        instrument_name, questions = registry.resolve(persona_id)
        user_prompt = build_elicitation_user_prompt(
            questions=questions,
            instrument_label=instrument_name,
        )
        hits = contamination_hits(user_prompt)
        entry = {
            "persona_id": persona_id,
            "instrument_name": instrument_name,
            "question_count": len(questions),
            "contamination_hits": hits,
        }
        report["instruments"].append(entry)
        if hits:
            report["passed"] = False
    return report


_register_default_studies()
