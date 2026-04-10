from __future__ import annotations

import hashlib
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from mirofish_backend.rag.chunk import chunk_text
from mirofish_backend.rag.corpus import load_default_rag_corpus_texts, load_scenario_corpus_texts
from mirofish_backend.rag.embeddings import embed_texts_openai_compatible
from mirofish_backend.rag.similarity import cosine_similarity

logger = logging.getLogger("mirofish_backend.rag.retrieve")

EmbedBatchFn = Callable[..., Awaitable[list[list[float]]]]


@dataclass(frozen=True)
class RetrievedSnippet:
    text: str
    score: float
    source: str


_CHUNK_ROWS: dict[str, list[tuple[str, str, list[float]]]] = {}


def _corpus_fingerprint(
    corpus: list[tuple[str, str]],
    *,
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str,
) -> str:
    h = hashlib.sha256()
    h.update(embedding_model.encode())
    h.update(f"{chunk_size}:{chunk_overlap}".encode())
    for label, txt in sorted(corpus, key=lambda x: x[0]):
        h.update(label.encode())
        h.update(b"\0")
        h.update(txt.encode())
        h.update(b"\xff")
    return h.hexdigest()


def clear_rag_index_cache() -> None:
    """Test helper: drop in-memory embedding index."""
    _CHUNK_ROWS.clear()


def _build_chunk_texts(corpus: list[tuple[str, str]], *, chunk_size: int, chunk_overlap: int) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for source_label, doc in corpus:
        for piece in chunk_text(doc, chunk_size=chunk_size, overlap=chunk_overlap):
            rows.append((source_label, piece))
    return rows


async def _embed_chunks(
    *,
    base_url: str,
    model: str,
    chunk_texts: list[str],
    embed_batch: EmbedBatchFn,
) -> list[list[float]]:
    if not chunk_texts:
        return []
    batch_size = 32
    all_vecs: list[list[float]] = []
    for i in range(0, len(chunk_texts), batch_size):
        batch = chunk_texts[i : i + batch_size]
        vecs = await embed_batch(base_url=base_url, model=model, texts=batch)
        all_vecs.extend(vecs)
    return all_vecs


async def get_chunk_index(
    *,
    scenario_id: str,
    rag_corpus_paths: tuple[str, ...],
    lmstudio_base_url: str,
    embedding_model: str,
    chunk_size: int,
    chunk_overlap: int,
    embed_batch: EmbedBatchFn | None = None,
) -> list[tuple[str, str, list[float]]]:
    """
    Load corpus, chunk, embed (cached in-process by fingerprint).
    """
    embed_fn = embed_batch or embed_texts_openai_compatible
    corpus = load_scenario_corpus_texts(rel_paths=rag_corpus_paths)
    if not corpus:
        corpus = load_default_rag_corpus_texts()
    if not corpus:
        logger.warning("RAG enabled for scenario %s but no corpus files found", scenario_id)
        return []

    fp = _corpus_fingerprint(
        corpus,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embedding_model=embedding_model,
    )
    cache_key = f"{scenario_id}:{fp}"
    if cache_key in _CHUNK_ROWS:
        return _CHUNK_ROWS[cache_key]

    pairs = _build_chunk_texts(corpus, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    if not pairs:
        _CHUNK_ROWS[cache_key] = []
        return []

    texts = [p[1] for p in pairs]
    vectors = await _embed_chunks(
        base_url=lmstudio_base_url,
        model=embedding_model,
        chunk_texts=texts,
        embed_batch=embed_fn,
    )
    rows = [(pairs[i][0], pairs[i][1], vectors[i]) for i in range(len(pairs))]
    _CHUNK_ROWS[cache_key] = rows
    return rows


async def retrieve_top_k(
    *,
    query: str,
    scenario_id: str,
    rag_corpus_paths: tuple[str, ...],
    lmstudio_base_url: str,
    embedding_model: str,
    top_k: int,
    chunk_size: int,
    chunk_overlap: int,
    max_chars: int,
    embed_batch: EmbedBatchFn | None = None,
) -> list[RetrievedSnippet]:
    q = query.strip()
    if not q or top_k <= 0:
        return []

    embed_fn = embed_batch or embed_texts_openai_compatible
    index = await get_chunk_index(
        scenario_id=scenario_id,
        rag_corpus_paths=rag_corpus_paths,
        lmstudio_base_url=lmstudio_base_url,
        embedding_model=embedding_model,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        embed_batch=embed_fn,
    )
    if not index:
        return []

    q_vecs = await embed_fn(base_url=lmstudio_base_url, model=embedding_model, texts=[q])
    qv = q_vecs[0]

    scored: list[tuple[float, str, str]] = []
    for source, text, vec in index:
        scored.append((cosine_similarity(qv, vec), source, text))
    scored.sort(key=lambda x: -x[0])

    out: list[RetrievedSnippet] = []
    used = 0
    for score, source, text in scored:
        if len(out) >= top_k:
            break
        if used + len(text) > max_chars and out:
            break
        out.append(RetrievedSnippet(text=text, score=score, source=source))
        used += len(text)
    return out


def snippets_for_prompt(snippets: list[RetrievedSnippet]) -> list[dict[str, Any]]:
    return [{"text": s.text, "score": s.score, "source": s.source} for s in snippets]
