import pytest

from mirofish_backend.llm.prompt_templates import build_user_prompt
from mirofish_backend.rag.chunk import chunk_text
from mirofish_backend.rag.retrieve import clear_rag_index_cache, retrieve_top_k
from mirofish_backend.rag.similarity import cosine_similarity


def test_chunk_text_overlap() -> None:
    t = "a" * 100
    parts = chunk_text(t, chunk_size=30, overlap=10)
    assert len(parts) >= 3
    assert all(len(p) <= 30 for p in parts)


def test_cosine_similarity_orthogonal() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_retrieve_top_k_uses_mock_embeddings() -> None:
    clear_rag_index_cache()

    async def fake_embed(*, base_url: str, model: str, texts: list[str]) -> list[list[float]]:
        _ = base_url, model
        out: list[list[float]] = []
        for tx in texts:
            # Simple bag-of-chars hash into 8 dims (deterministic).
            v = [0.0] * 8
            for ch in tx.lower():
                v[ord(ch) % 8] += 1.0
            out.append(v)
        return out

    snips = await retrieve_top_k(
        query="G1 G2 G3 subject bands",
        scenario_id="fsbb_comparator",
        rag_corpus_paths=("corpus/fsbb_comparator/brief.txt",),
        lmstudio_base_url="http://unused",
        embedding_model="fake-emb",
        top_k=2,
        chunk_size=120,
        chunk_overlap=20,
        max_chars=5000,
        embed_batch=fake_embed,
    )
    assert len(snips) >= 1
    assert all(s.score >= -1.0 for s in snips)
    clear_rag_index_cache()


def test_user_prompt_includes_rag_block() -> None:
    user = build_user_prompt(
        round_number=1,
        policy_event="Town hall",
        interaction_type="broadcast",
        target_scope="all",
        target_agent_name=None,
        intent_tag="policy_update",
        prior_agent_memory=[],
        recent_interactions=[],
        context_snippets=[
            {"source": "corpus/x.txt", "score": 0.9, "text": "Stub excerpt about bands."},
        ],
    )
    assert "Reference excerpts" in user
    assert "Stub excerpt about bands." in user
    assert "corpus/x.txt" in user
