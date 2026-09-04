"""
RAG Engine — the "RAG" box: retrieve the transcript passages most relevant to a
question so the LLM answers grounded in the actual lecture (not hallucinated).

Retrieval is embedding-based (sentence-transformers, all-MiniLM-L6-v2 — small,
fast on CPU, fully offline once cached) with a cosine-similarity search over
per-lecture chunk embeddings. This gives materially better semantic matching
than plain keyword overlap: a question can retrieve a passage that answers it
without sharing many of the same words.

Falls back to TF-IDF (scikit-learn) automatically if sentence-transformers
isn't installed or the model can't be loaded (e.g. no internet on first run,
before it's cached) — same graceful-degradation philosophy as the rest of the
LLM/RAG layer (LLMNotConfigured returns a clean response instead of crashing;
this does the same for retrieval). The public interface is unchanged either
way, so callers never need to know which mode is active.
"""

import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Lazily loaded once and reused across every RagEngine instance/request —
# loading the model itself takes real time (a fresh download the very first
# run, a couple of seconds from cache after that); encoding a lecture's ~10-30
# chunks against an already-loaded model is fast.
_embedding_model = None
_embedding_load_attempted = False


def _get_embedding_model():
    global _embedding_model, _embedding_load_attempted
    if _embedding_load_attempted:
        return _embedding_model
    _embedding_load_attempted = True
    try:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    except Exception as e:
        logger.warning(
            f"Embedding model unavailable ({e}) — falling back to TF-IDF retrieval"
        )
    return _embedding_model


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
    """Builds a per-lecture retrieval index (embeddings, or TF-IDF as a
    fallback) and retrieves the top passages for a query."""

    def __init__(self, chunks: List[str]):
        self.chunks = chunks
        self.mode: Optional[str] = None  # "embedding" | "tfidf" | None (no chunks)
        self._vectorizer = None
        self._matrix = None
        self._embeddings = None
        if chunks:
            self._build()

    def _build(self):
        model = _get_embedding_model()
        if model is not None:
            self.mode = "embedding"
            self._embeddings = model.encode(self.chunks, normalize_embeddings=True)
            return

        self.mode = "tfidf"
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self._matrix = self._vectorizer.fit_transform(self.chunks)

    def retrieve(self, query: str, k: int = 4) -> List[Dict]:
        if not self.chunks or self.mode is None:
            return []
        import numpy as np

        if self.mode == "embedding":
            model = _get_embedding_model()
            q_vec = model.encode([query], normalize_embeddings=True)[0]
            sims = self._embeddings @ q_vec  # both L2-normalized -> dot == cosine
        else:
            from sklearn.metrics.pairwise import cosine_similarity

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
