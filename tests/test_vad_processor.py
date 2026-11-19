"""Unit tests for the voice-activity-detection pre-trimmer."""

import numpy as np
import pytest

pytest.importorskip("webrtcvad")

from src.vad_processor import VADProcessor  # noqa: E402

SR = 16000


def _tone(seconds, freq=220.0, amp=0.6):
    t = np.arange(int(seconds * SR)) / SR
    # Harmonic-rich, amplitude-modulated signal: much closer to voiced speech
    # than a pure sine, so the WebRTC detector reliably flags it.
    sig = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 6))
    sig *= 0.5 * (1 + np.sin(2 * np.pi * 4 * t))
    return (amp * sig / np.max(np.abs(sig))).astype(np.float32)


def _silence(seconds):
    return np.zeros(int(seconds * SR), dtype=np.float32)


class TestVADProcessor:
    def test_frame_properties(self):
        vad = VADProcessor(
            sample_rate=SR, frame_duration_ms=30, padding_duration_ms=300
        )
        assert vad.frame_size == 480
        assert vad.padding_frames == 10

    def test_frame_generator_drops_partial_frame(self):
        vad = VADProcessor(sample_rate=SR)
        frames = list(vad._frame_generator(np.zeros(480 * 3 + 100, dtype=np.float32)))
        assert len(frames) == 3 and all(len(f) == 480 for f in frames)

    def test_pure_silence_has_no_segments_and_is_returned_unchanged(self):
        vad = VADProcessor(sample_rate=SR)
        audio = _silence(2.0)
        assert vad.detect_speech_segments(audio) == []
        trimmed, segments = vad.trim_silence(audio)
        assert segments == []
        assert len(trimmed) == len(audio)

    def test_speech_between_silence_is_trimmed(self):
        vad = VADProcessor(sample_rate=SR, aggressiveness=1, padding_duration_ms=60)
        audio = np.concatenate([_silence(2.0), _tone(2.0), _silence(2.0)])
        trimmed, segments = vad.trim_silence(audio)
        assert segments, "speech-like signal should be detected"
        assert len(trimmed) < len(audio)
        assert segments[0][0] >= 0
        assert segments[-1][1] <= len(trimmed)

    def test_padding_extends_flags_both_sides(self):
        vad = VADProcessor(sample_rate=SR, frame_duration_ms=30, padding_duration_ms=60)
        flags = [False] * 6 + [True] + [False] * 6
        padded = vad._add_padding(flags)
        assert padded[4:9] == [True] * 5
        assert padded[0] is False and padded[-1] is False

    def test_short_segments_are_discarded(self):
        vad = VADProcessor(
            sample_rate=SR, padding_duration_ms=0, min_speech_duration_ms=300
        )
        vad._is_speech = lambda frame: bool(frame[0])  # deterministic stub
        audio = _silence(1.0)
        audio[: vad.frame_size * 2] = 1.0  # only 2 speech frames < 10 required
        assert vad.detect_speech_segments(audio) == []

    def test_speech_running_to_end_of_audio(self):
        vad = VADProcessor(
            sample_rate=SR, padding_duration_ms=0, min_speech_duration_ms=30
        )
        vad._is_speech = lambda frame: bool(frame[0])
        audio = _silence(1.0)
        audio[SR // 2 :] = 1.0
        segments = vad.detect_speech_segments(audio)
        assert segments and segments[-1][1] == len(audio)

    def test_silence_threshold_gates_quiet_frames(self):
        vad = VADProcessor(sample_rate=SR)
        vad.silence_threshold = 0.5
        quiet = np.full(vad.frame_size, 0.01, dtype=np.float32)
        assert vad._is_speech(quiet) is False

    def test_invalid_frame_falls_back_without_raising(self):
        vad = VADProcessor(sample_rate=SR)
        bad = np.zeros(10, dtype=np.float32)  # wrong length for webrtcvad
        assert vad._is_speech(bad) is False
        vad.silence_threshold = 0.0
        assert vad._is_speech(bad) is True
