"""
TTS engine tests. Unlike the embedding model (test_rag_engine.py) or the
heavy audio-pipeline models (test_pipeline.py), these use the REAL Piper
voice directly: it's a small ONNX model (~60MB) that loads in a few seconds
and synthesizes short text in well under a second, so the cost of proving
the actual integration works is small enough to pay in the normal suite —
no fake needed.

If the voice model hasn't been downloaded (fresh clone, no model files),
these skip rather than fail — same "optional, gracefully absent" philosophy
as tts_engine.py itself.
"""

import os
import sys
import wave

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import tts_engine

pytestmark = pytest.mark.skipif(
    not tts_engine.is_available(),
    reason="Piper voice model not downloaded — see tts_engine.py's VOICE_MODEL_PATH",
)


def test_is_available():
    assert tts_engine.is_available() is True


def test_synthesize_writes_valid_wav(tmp_path):
    out = tmp_path / "recap.wav"
    ok = tts_engine.synthesize("This is a short test recap.", str(out))
    assert ok is True
    assert out.exists()

    with wave.open(str(out), "rb") as f:
        assert f.getnframes() > 0
        assert f.getnchannels() == 1
        assert f.getsampwidth() == 2  # 16-bit PCM


def test_synthesize_creates_parent_directory(tmp_path):
    out = tmp_path / "nested" / "dir" / "recap.wav"
    ok = tts_engine.synthesize("Hello.", str(out))
    assert ok is True
    assert out.exists()


def test_synthesize_longer_text_produces_longer_audio(tmp_path):
    short_out = tmp_path / "short.wav"
    long_out = tmp_path / "long.wav"
    tts_engine.synthesize("A short sentence.", str(short_out))
    tts_engine.synthesize(
        "A much longer sentence with quite a few more words in it, "
        "meant to take noticeably longer to speak aloud than the short one.",
        str(long_out),
    )
    with wave.open(str(short_out), "rb") as f:
        short_frames = f.getnframes()
    with wave.open(str(long_out), "rb") as f:
        long_frames = f.getnframes()
    assert long_frames > short_frames
