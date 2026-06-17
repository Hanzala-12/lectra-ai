"""
RAG Engine — the "RAG" box: retrieve the transcript passages most relevant to a
question so the LLM answers grounded in the actual lecture (not hallucinated).

Uses TF-IDF cosine retrieval (scikit-learn) — dependency-light, fully offline,
and plenty effective for single-lecture transcripts. The interface is designed so
it can be swapped for embedding-based retrieval later without touching callers.
"""

import re
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_words: int = 180, overlap_words: int = 40) -> List[str]:
    """Split transcript into overlapping word windows (keeps context across cuts)."""
    words = (text or "").split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_words - overlap_words)
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + chunk_words])
        if chunk.strip():
            chunks.append(chunk)
        if start + chunk_words >= len(words):
            break
    return chunks


class RagEngine:
    """Builds a per-lecture TF-IDF index and retrieves top passages."""

    def __init__(self, chunks: List[str]):
        self.chunks = chunks
        self._vectorizer = None
        self._matrix = None
        if chunks:
            self._build()

    def _build(self):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(self.chunks)

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:
        if not self.chunks or self._vectorizer is None:
            return []
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np

        q_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self._matrix)[0]
        top = np.argsort(sims)[::-1][:k]
        return [
            {"text": self.chunks[i], "score": float(sims[i])}
            for i in top
            if sims[i] > 0.0
        ]

    @classmethod
    def from_transcript(cls, transcript_text: str, **kwargs) -> "RagEngine":
        return cls(chunk_text(transcript_text, **kwargs))


def build_context(passages: List[Dict], max_chars: int = 4000) -> str:
    """Concatenate retrieved passages into a context block for the LLM prompt."""
    out, total = [], 0
    for i, p in enumerate(passages, 1):
        piece = f"[Passage {i}]\n{p['text']}\n"
        if total + len(piece) > max_chars:
            break
        out.append(piece)
        total += len(piece)
    return "\n".join(out)
