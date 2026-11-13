"""RAG scaffold: corpus chunks, LM Studio embeddings, top-k retrieval for prompts."""

from senna_backend.rag.retrieve import RetrievedSnippet, retrieve_top_k

__all__ = ["RetrievedSnippet", "retrieve_top_k"]
