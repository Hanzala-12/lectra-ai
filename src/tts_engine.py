"""
TTS Engine — narrates the audio-recap feature (study_api.py::make_recap()).

Piper (https://github.com/OHF-Voice/piper1-gpl) — a small, fast, fully-offline
neural TTS. Chosen over the OS-native SAPI voice (robotic, dated) and over
heavier neural TTS stacks (multi-GB, GPU-oriented): Piper's per-voice models
are tens of MB, it runs comfortably in real time on CPU, and it reuses the
onnxruntime already installed for this project rather than pulling in a new
inference framework.

Same graceful-degradation pattern as llm_client.py / rag_engine.py:
is_available() lets callers return a clean 503 instead of crashing when
either the piper-tts package or the voice model file isn't present (e.g. a
fresh clone that hasn't run the model download step yet).
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

VOICE_NAME = "en_US-lessac-medium"
VOICE_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "piper")
VOICE_MODEL_PATH = os.path.join(VOICE_DIR, f"{VOICE_NAME}.onnx")

_voice = None
_load_attempted = False


def _get_voice():
    global _voice, _load_attempted
    if _load_attempted:
        return _voice
    _load_attempted = True
    if not os.path.exists(VOICE_MODEL_PATH):
        logger.warning(
            f"Piper voice model not found at {VOICE_MODEL_PATH} — audio recap "
            f"unavailable. Download it with: "
            f"python -m piper.download_voices --download-dir models/piper {VOICE_NAME}"
        )
        return None
    try:
        from piper import PiperVoice

        _voice = PiperVoice.load(VOICE_MODEL_PATH)
    except Exception as e:
        logger.warning(f"Could not load Piper voice ({e}) — audio recap unavailable")
    return _voice


def is_available() -> bool:
    return _get_voice() is not None


def synthesize(text: str, output_path: str) -> bool:
    """Write `text` as narrated speech to a WAV file at output_path. Returns
    False (does not raise) if TTS isn't available — callers check
    is_available() first via _require_tts() in study_api.py, so reaching
    here with no voice loaded would be a bug upstream, not a normal path."""
    voice = _get_voice()
    if voice is None:
        return False
    import wave

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return True
