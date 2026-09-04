"""
RAG engine tests. The real sentence-transformers model is never loaded here —
same philosophy as test_pipeline.py mocking DeepFilterProcessor/ASRProcessor/
SpeakerDiarization: a ~90MB model load is real-integration territory (verified
live against the running backend), not something every `pytest tests/` run
should pay for. A small deterministic fake embedding model exercises the same
retrieval logic (top-k, cosine similarity via normalized dot product, score
filtering) without it.

The TF-IDF fallback path (sentence-transformers unavailable) uses the real
scikit-learn vectorizer — that one's cheap, no model download involved.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np
import pytest

import rag_engine
from rag_engine import RagEngine, build_context, chunk_text


class _FakeEmbeddingModel:
    """Deterministic 2D stand-in: axis 0 tracks "cat" mentions, axis 1 tracks
    "dog" mentions. Lets tests construct chunks that are unambiguously more or
    less relevant to a query without needing real semantic understanding."""

    def encode(self, texts, normalize_embeddings=True):
        vecs = []
        for t in texts:
            low = t.lower()
            v = np.array([low.count("cat"), low.count("dog")], dtype=float)
            norm = np.linalg.norm(v)
            vecs.append(v / norm if norm > 0 else np.array([0.0, 0.0]))
        return np.array(vecs)


@pytest.fixture(autouse=True)
def fake_embedding_model(monkeypatch):
    """Every test in this file gets the fast fake by default."""
    fake = _FakeEmbeddingModel()
    monkeypatch.setattr(rag_engine, "_get_embedding_model", lambda: fake)
    yield fake


# ----------------------------------------------------------------- chunk_text


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("") == []
    assert chunk_text(None) == []


def test_chunk_text_short_text_single_chunk():
    chunks = chunk_text("one two three", chunk_words=180, overlap_words=40)
    assert chunks == ["one two three"]


def test_chunk_text_splits_and_overlaps():
    words = [f"w{i}" for i in range(500)]
    text = " ".join(words)
    chunks = chunk_text(text, chunk_words=180, overlap_words=40)
    assert len(chunks) > 1
    # consecutive chunks share the overlap region
    first_words = chunks[0].split()
    second_words = chunks[1].split()
    assert first_words[-40:] == second_words[:40]
    # every word appears somewhere
    assert "w0" in chunks[0]
    assert "w499" in chunks[-1]


# ----------------------------------------------------------------- RagEngine


def test_engine_with_no_chunks_has_no_mode():
    engine = RagEngine([])
    assert engine.mode is None
    assert engine.retrieve("anything") == []


def test_retrieve_ranks_by_relevance():
    engine = RagEngine(
        [
            "The cat sat on the mat and the cat purred.",
            "The dog barked loudly at the mailman.",
            "Cats and dogs can be friends if raised together.",
        ]
    )
    assert engine.mode == "embedding"
    results = engine.retrieve("Tell me about cats", k=3)
    assert results[0]["text"].startswith("The cat sat")
    # scores are sorted descending
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_respects_k():
    engine = RagEngine(["cat cat cat", "dog dog dog", "cat dog", "cat"])
    results = engine.retrieve("cat", k=2)
    assert len(results) == 2


def test_retrieve_filters_zero_score():
    # A chunk with neither "cat" nor "dog" encodes to the zero vector -> 0
    # similarity with anything, including itself - should never be returned.
    engine = RagEngine(["completely unrelated content", "cat cat cat"])
    results = engine.retrieve("cat", k=5)
    assert all(r["score"] > 0 for r in results)
    assert len(results) == 1


def test_from_transcript_builds_chunks():
    engine = RagEngine.from_transcript("cat dog " * 100)
    assert engine.mode == "embedding"
    assert len(engine.chunks) >= 1


def test_falls_back_to_tfidf_when_embedding_model_unavailable(monkeypatch):
    monkeypatch.setattr(rag_engine, "_get_embedding_model", lambda: None)
    engine = RagEngine(
        [
            "Photosynthesis converts light into chemical energy.",
            "Mitochondria produce ATP.",
        ]
    )
    assert engine.mode == "tfidf"
    results = engine.retrieve("photosynthesis energy", k=2)
    assert results
    assert "Photosynthesis" in results[0]["text"]


# ----------------------------------------------------------------- build_context


def test_build_context_joins_and_labels_passages():
    ctx = build_context(
        [{"text": "first", "score": 0.9}, {"text": "second", "score": 0.5}]
    )
    assert "[Passage 1]" in ctx
    assert "first" in ctx
    assert "[Passage 2]" in ctx
    assert "second" in ctx


def test_build_context_empty_passages_returns_empty_string():
    assert build_context([]) == ""


def test_build_context_respects_max_chars():
    passages = [{"text": "x" * 100, "score": 1.0} for _ in range(10)]
    ctx = build_context(passages, max_chars=250)
    assert len(ctx) < 400  # well short of the full ~1000+ chars all 10 would produce
    assert "[Passage 1]" in ctx
