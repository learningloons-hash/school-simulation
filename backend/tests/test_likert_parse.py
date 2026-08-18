import json

from mirofish_backend.simulation.likert import compute_divergence
from mirofish_backend.llm.likert_parse import (
    LIKERT_ORDINAL_FLOAT_MAP,
    extract_all_likert_blocks,
    float_to_nearest_ordinal,
    mapped_float_from_ordinal,
    parse_likert_payload,
    resolve_likert_from_response,
)


ANCHORS = {
    "support": (
        "strongly oppose",
        "oppose",
        "somewhat oppose",
        "somewhat support",
        "support",
        "strongly support",
    ),
    "resistance": (
        "no resistance",
        "minimal resistance",
        "low resistance",
        "moderate resistance",
        "high resistance",
        "very high resistance",
    ),
}


def test_mapped_float_from_ordinal() -> None:
    assert mapped_float_from_ordinal(0) == 0.0
    assert mapped_float_from_ordinal(5) == 1.0
    assert len(LIKERT_ORDINAL_FLOAT_MAP) == 6


def test_extract_all_likert_blocks() -> None:
    raw = "Note.\n<likert>\n{\"support\": \"support\"}\n</likert>"
    blocks = extract_all_likert_blocks(raw)
    assert len(blocks) == 1
    assert "support" in blocks[0]


def test_parse_likert_payload_label_match() -> None:
    payload = {"support": "somewhat support", "resistance": 3}
    parsed, label_repaired, numeric_repaired = parse_likert_payload(
        payload,
        indicators=("support", "resistance"),
        anchor_labels=ANCHORS,
    )
    assert label_repaired is False
    assert numeric_repaired is True
    assert parsed["support"][1] == 3
    assert parsed["resistance"][1] == 3


def test_resolve_likert_per_indicator_covers_all_indicators() -> None:
    from mirofish_backend.llm.likert_parse import resolve_likert_per_indicator

    raw = "Done.\n<likert>\n" + json.dumps({"support": "support"}) + "\n</likert>"
    per = resolve_likert_per_indicator(
        raw,
        indicators=("support", "resistance"),
        anchor_labels=ANCHORS,
        float_values={"support": 0.8, "resistance": 0.4},
    )
    assert set(per.keys()) == {"support", "resistance"}
    assert per["resistance"][3] == "keyword_fallback"


def test_resolve_likert_model_parsed_provenance() -> None:
    raw = (
        "Done.\n<likert>\n"
        + json.dumps({"support": "support", "resistance": "moderate resistance"})
        + "\n</likert>"
    )
    parsed, source = resolve_likert_from_response(
        raw,
        indicators=("support", "resistance"),
        anchor_labels=ANCHORS,
        float_values={"support": 0.8, "resistance": 0.6},
    )
    assert source == "model_parsed"
    assert parsed["support"][1] == 4


def test_resolve_likert_repaired_trailing_comma() -> None:
    raw = "Done.\n<likert>\n{\"support\": \"support\",}\n</likert>"
    parsed, source = resolve_likert_from_response(
        raw,
        indicators=("support",),
        anchor_labels=ANCHORS,
        float_values={"support": 0.5},
    )
    assert source == "repaired"
    assert parsed["support"][1] == 4


def test_resolve_likert_keyword_fallback() -> None:
    raw = "No structured likert block here."
    parsed, source = resolve_likert_from_response(
        raw,
        indicators=("support",),
        anchor_labels=ANCHORS,
        float_values={"support": 0.82},
    )
    assert source == "keyword_fallback"
    ordinal = parsed["support"][1]
    assert mapped_float_from_ordinal(ordinal) == mapped_float_from_ordinal(
        float_to_nearest_ordinal(0.82)
    )


def test_compute_divergence() -> None:
    assert compute_divergence(0.8, 0.6) == 0.2
    assert compute_divergence(None, 0.5) is None
