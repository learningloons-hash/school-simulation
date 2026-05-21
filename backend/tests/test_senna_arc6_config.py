"""Senna iter-29: `Settings` flags for round summaries and transcript path (see HANDOFF_SENNA_ARC6 ## senna-iter-29)."""

from mirofish_backend.config import Settings, get_settings


def test_settings_senna_arc6_defaults() -> None:
    s = Settings()
    assert s.round_summary_enabled is True
    assert s.transcript_dir == "./data/transcripts"


def test_get_settings_includes_senna_arc6_flags() -> None:
    s = get_settings()
    assert hasattr(s, "round_summary_enabled")
    assert hasattr(s, "transcript_dir")
    assert isinstance(s.round_summary_enabled, bool)
    assert isinstance(s.transcript_dir, str)
