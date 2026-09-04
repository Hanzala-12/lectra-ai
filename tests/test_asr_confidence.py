"""
Tests for asr_processor.py's confidence signals (combine_with_diarization) —
pure logic over plain dicts, no real WhisperModel needed. ASRProcessor's
__init__ eagerly loads a real model (heavy, out of scope for a unit test —
test_pipeline.py mocks it out entirely), but combine_with_diarization never
touches `self`, so it's called directly as an unbound method with a dummy
self here instead.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from asr_processor import ASRProcessor

_combine = ASRProcessor.combine_with_diarization


def test_no_diarization_returns_segments_unchanged():
    transcript = {"segments": [{"start": 0, "end": 1, "text": "hi"}]}
    assert _combine(None, transcript, []) == transcript["segments"]


def test_speaker_confidence_is_one_for_clean_single_speaker_overlap():
    transcript = {
        "segments": [{"start": 0.0, "end": 2.0, "text": "hello", "avg_logprob": -0.1}]
    }
    diarization = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["speaker"] == "SPEAKER_00"
    assert result[0]["speaker_confidence"] == 1.0


def test_speaker_confidence_reflects_partial_overlap():
    # segment spans 0-2s, diarization turn only covers 0-1s -> half overlap
    transcript = {
        "segments": [{"start": 0.0, "end": 2.0, "text": "hello", "avg_logprob": -0.1}]
    }
    diarization = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["speaker_confidence"] == 0.5


def test_picks_speaker_with_largest_overlap():
    transcript = {
        "segments": [{"start": 0.0, "end": 4.0, "text": "hello", "avg_logprob": -0.1}]
    }
    diarization = [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"start": 1.0, "end": 4.0, "speaker": "SPEAKER_01"},
    ]
    result = _combine(None, transcript, diarization)
    assert result[0]["speaker"] == "SPEAKER_01"
    assert result[0]["speaker_confidence"] == 0.75


def test_asr_confidence_converts_logprob_to_probability():
    transcript = {
        "segments": [{"start": 0.0, "end": 1.0, "text": "hi", "avg_logprob": -0.5}]
    }
    diarization = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["asr_confidence"] == round(math.exp(-0.5), 3)


def test_asr_confidence_none_when_avg_logprob_missing():
    # legacy transcript predating this field
    transcript = {"segments": [{"start": 0.0, "end": 1.0, "text": "hi"}]}
    diarization = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["asr_confidence"] is None


def test_zero_duration_segment_has_zero_speaker_confidence():
    transcript = {
        "segments": [{"start": 1.0, "end": 1.0, "text": "", "avg_logprob": -0.1}]
    }
    diarization = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["speaker_confidence"] == 0.0


def test_no_overlapping_speaker_defaults_to_unknown():
    transcript = {
        "segments": [{"start": 10.0, "end": 11.0, "text": "hi", "avg_logprob": -0.1}]
    }
    diarization = [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}]
    result = _combine(None, transcript, diarization)
    assert result[0]["speaker"] == "Unknown"
    assert result[0]["speaker_confidence"] == 0.0
