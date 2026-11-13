from __future__ import annotations


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """Split plain text into overlapping character windows (scaffold; no tokenizer)."""
    t = text.strip()
    if not t:
        return []
    if chunk_size <= 0:
        return [t]
    ov = max(0, min(overlap, chunk_size - 1)) if chunk_size > 1 else 0
    chunks: list[str] = []
    start = 0
    n = len(t)
    while start < n:
        end = min(start + chunk_size, n)
        piece = t[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end - ov
    return chunks
