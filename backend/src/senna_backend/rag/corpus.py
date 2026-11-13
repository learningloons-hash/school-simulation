from __future__ import annotations

from pathlib import Path


_SCENARIOS_DATA = Path(__file__).resolve().parent.parent / "scenarios" / "data"
_RAG_DATA = Path(__file__).resolve().parent / "data"


def load_scenario_corpus_texts(*, rel_paths: tuple[str, ...]) -> list[tuple[str, str]]:
    """
    Load corpus files for a scenario. Paths are relative to scenarios/data/.
    Returns list of (source_label, text).
    """
    out: list[tuple[str, str]] = []
    for rel in rel_paths:
        p = (_SCENARIOS_DATA / rel).resolve()
        if not str(p).startswith(str(_SCENARIOS_DATA.resolve())):
            continue
        if not p.is_file():
            continue
        out.append((str(rel), p.read_text(encoding="utf-8")))
    return out


def load_default_rag_corpus_texts() -> list[tuple[str, str]]:
    """Optional shared snippets under rag/data/*.txt (when scenario lists no files)."""
    if not _RAG_DATA.is_dir():
        return []
    out: list[tuple[str, str]] = []
    for path in sorted(_RAG_DATA.glob("*.txt")):
        out.append((f"rag/data/{path.name}", path.read_text(encoding="utf-8")))
    return out
