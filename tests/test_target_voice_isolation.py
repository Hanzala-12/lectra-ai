"""
Tests for target_voice_isolation.py.

Two parts, matching this project's established conventions:
(a) find_overlap_windows()/identify_legitimate_speakers() - pure functions
    over plain {start,end,speaker} dicts, no model involved - tested the
    same way tests/test_asr_confidence.py tests combine_with_diarization:
    plain dicts in, no mocking needed.
(b) TargetVoiceIsolator's orchestration/gating logic (process() /
    _process_window() / _splice()) - the real risk in this module. Rather
    than patching SepformerSeparation/PretrainedSpeakerEmbedding (both are
    imported LOCALLY inside __init__, matching metricgan_processor.py's
    own established pattern of not requiring speechbrain/torch just to
    import this module - so there's no module-level attribute for
    unittest.mock.patch to intercept), instances are built by bypassing
    __init__ entirely (object.__new__) and injecting small fake
    `separator`/`embedder` collaborators with known, controllable
    behavior - the same spirit as test_pipeline.py mocking out
    DeepFilterProcessor/ASRProcessor/SpeakerDiarization, adapted to this
    module's local-import structure.
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from target_voice_isolation import (
    TargetVoiceIsolator,
    find_overlap_windows,
    identify_legitimate_speakers,
)

# ---------------------------------------------------------------------------
# (a) find_overlap_windows
# ---------------------------------------------------------------------------


def test_no_diarization_has_no_overlap():
    assert find_overlap_windows([]) == []


def test_single_speaker_has_no_overlap():
    diarization = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 5.5, "end": 10.0, "speaker": "SPEAKER_00"},
    ]
    assert find_overlap_windows(diarization) == []


def test_sequential_speakers_have_no_overlap():
    diarization = [
        {"start": 0.0, "end": 5.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 10.0, "speaker": "SPEAKER_01"},
    ]
    # Touching exactly at the boundary is a zero-duration "overlap" at
    # best, filtered out by min_overlap_s regardless of default (0.3s).
    assert find_overlap_windows(diarization) == []


def test_partial_overlap_is_detected_with_correct_bounds():
    # SPEAKER_00 talks 0-10s; SPEAKER_01 interjects 5-8s (fully inside).
    # The overlap window must be the INTERSECTION (5-8s), not the union.
    diarization = [
        {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 8.0, "speaker": "SPEAKER_01"},
    ]
    windows = find_overlap_windows(diarization)
    assert len(windows) == 1
    assert windows[0]["start"] == pytest.approx(5.0)
    assert windows[0]["end"] == pytest.approx(8.0)
    assert windows[0]["speakers"] == ["SPEAKER_00", "SPEAKER_01"]


def test_overlap_shorter_than_min_overlap_s_is_dropped():
    diarization = [
        {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 5.1, "speaker": "SPEAKER_01"},  # 0.1s blip
    ]
    assert find_overlap_windows(diarization, min_overlap_s=0.3) == []
    # ...but is kept if the caller asks for a smaller minimum.
    assert len(find_overlap_windows(diarization, min_overlap_s=0.05)) == 1


def test_multiple_separate_overlap_regions_are_both_found():
    diarization = [
        {"start": 0.0, "end": 20.0, "speaker": "SPEAKER_00"},
        {"start": 2.0, "end": 4.0, "speaker": "SPEAKER_01"},
        {"start": 10.0, "end": 13.0, "speaker": "SPEAKER_01"},
    ]
    windows = find_overlap_windows(diarization)
    assert len(windows) == 2
    assert windows[0]["start"] == pytest.approx(2.0)
    assert windows[0]["end"] == pytest.approx(4.0)
    assert windows[1]["start"] == pytest.approx(10.0)
    assert windows[1]["end"] == pytest.approx(13.0)


def test_three_way_overlap_lists_all_active_speakers():
    diarization = [
        {"start": 0.0, "end": 10.0, "speaker": "SPEAKER_00"},
        {"start": 3.0, "end": 7.0, "speaker": "SPEAKER_01"},
        {"start": 4.0, "end": 5.0, "speaker": "SPEAKER_02"},
    ]
    windows = find_overlap_windows(diarization)
    assert len(windows) == 1
    assert windows[0]["speakers"] == ["SPEAKER_00", "SPEAKER_01", "SPEAKER_02"]


# ---------------------------------------------------------------------------
# (b) identify_legitimate_speakers
# ---------------------------------------------------------------------------


def test_no_speakers_are_legitimate_with_no_diarization():
    assert identify_legitimate_speakers([]) == []


def test_speaker_below_duration_threshold_is_excluded():
    diarization = [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}
    ]  # 1s < 5s default
    assert identify_legitimate_speakers(diarization) == []


def test_speaker_above_duration_threshold_is_included():
    diarization = [{"start": 0.0, "end": 6.0, "speaker": "SPEAKER_00"}]
    assert identify_legitimate_speakers(diarization) == ["SPEAKER_00"]


def test_duration_sums_across_multiple_segments():
    # No single segment alone meets the 5s threshold, but three together do.
    diarization = [
        {"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"},
        {"start": 5.0, "end": 7.0, "speaker": "SPEAKER_00"},
        {"start": 10.0, "end": 12.0, "speaker": "SPEAKER_00"},
    ]
    assert identify_legitimate_speakers(diarization) == ["SPEAKER_00"]


def test_mixed_legitimate_and_blip_speakers():
    diarization = [
        {"start": 0.0, "end": 8.0, "speaker": "SPEAKER_00"},  # legitimate
        {"start": 8.0, "end": 8.2, "speaker": "SPEAKER_01"},  # 0.2s blip
        {"start": 9.0, "end": 15.0, "speaker": "SPEAKER_02"},  # legitimate
    ]
    assert identify_legitimate_speakers(diarization, min_total_duration_s=5.0) == [
        "SPEAKER_00",
        "SPEAKER_02",
    ]


# ---------------------------------------------------------------------------
# (b) TargetVoiceIsolator - orchestration and safety gates
# ---------------------------------------------------------------------------

SR = 16000


def _tone(freq_hz, amplitude, duration_s, sr=SR, phase=0.0):
    t = np.arange(int(duration_s * sr)) / sr
    return (amplitude * np.sin(2 * np.pi * freq_hz * t + phase)).astype(np.float32)


class _FakeSeparator:
    """Stands in for speechbrain's SepformerSeparation. Ignores its input
    mixture entirely and always returns the two pre-baked candidate
    streams a test configured - deterministic by construction."""

    def __init__(self, candidate_a, candidate_b):
        self.candidate_a = candidate_a
        self.candidate_b = candidate_b

    def separate_batch(self, mix):
        import torch

        n = mix.shape[-1]
        a = np.resize(self.candidate_a, n).astype(np.float32)
        b = np.resize(self.candidate_b, n).astype(np.float32)
        stacked = np.stack([a, b], axis=-1)  # (T, 2)
        return torch.from_numpy(stacked).unsqueeze(0)  # (1, T, 2)


class _FakeEmbedder:
    """Stands in for pyannote's PretrainedSpeakerEmbedding. Looks up a
    fixed embedding by matching the waveform's content against known
    reference signals a test registered, so cosine-similarity outcomes
    are fully controlled rather than depending on a real model."""

    def __init__(self, reference_embeddings):
        # list of (reference_waveform, embedding) pairs
        self.reference_embeddings = reference_embeddings

    def __call__(self, tensor):
        wf = tensor.detach().cpu().numpy().reshape(-1)
        for ref_wf, emb in self.reference_embeddings:
            ref = np.resize(ref_wf, wf.shape).astype(np.float32)
            if np.allclose(wf, ref, atol=1e-4):
                return np.asarray(emb, dtype=np.float32).reshape(1, -1)
        return np.zeros((1, 2), dtype=np.float32)


def _make_isolator(separator, embedder, **overrides):
    """Build a TargetVoiceIsolator without running its real __init__ (which
    downloads/loads real SpeechBrain/pyannote checkpoints) - injects fake
    collaborators instead, matching test_pipeline.py's spirit of mocking
    out heavy model classes."""
    import torch

    isolator = object.__new__(TargetVoiceIsolator)
    isolator.device = "cpu"
    isolator._torch = torch
    isolator.separator = separator
    isolator.embedder = embedder
    isolator.min_overlap_duration_s = overrides.get("min_overlap_duration_s", 0.3)
    isolator.min_speaker_duration_s = overrides.get("min_speaker_duration_s", 5.0)
    isolator.match_confidence_threshold = overrides.get(
        "match_confidence_threshold", 0.65
    )
    isolator.context_padding_s = overrides.get("context_padding_s", 0.5)
    isolator.crossfade_s = overrides.get("crossfade_s", 0.25)
    isolator.low_freq_gate_hz = overrides.get("low_freq_gate_hz", 150.0)
    return isolator


def test_confident_match_is_accepted_and_gain_matched():
    original = _tone(1000, 0.1, 3.0)  # 3s @ 1kHz, no low-freq content
    window = {"start": 1.0, "end": 2.0, "speakers": ["SPEAKER_00", "SPEAKER_01"]}

    candidate_a = original  # "is" SPEAKER_00, exact match to original tone
    candidate_b = _tone(1000, 0.03, 3.0)  # small secondary content, SPEAKER_01

    isolator = _make_isolator(
        separator=_FakeSeparator(candidate_a, candidate_b),
        embedder=_FakeEmbedder([(candidate_a, [1, 0]), (candidate_b, [0, 1])]),
    )
    legitimate_embeddings = {
        "SPEAKER_00": np.array([1, 0]),
        "SPEAKER_01": np.array([0, 1]),
    }

    result = isolator._process_window(original, SR, window, legitimate_embeddings)

    assert result is not None
    pad = int(isolator.context_padding_s * SR)
    start_i = int(window["start"] * SR) - pad
    end_i = int(window["end"] * SR) + pad
    original_slice = original[start_i:end_i]
    # Gain-matched: result's RMS should track the ORIGINAL window's RMS,
    # not the (louder, a+b) unnormalized separated output.
    orig_rms = np.sqrt(np.mean(original_slice.astype(np.float64) ** 2))
    result_rms = np.sqrt(np.mean(result.astype(np.float64) ** 2))
    assert result_rms == pytest.approx(orig_rms, rel=0.05)


def test_low_confidence_match_falls_back_to_none():
    original = _tone(1000, 0.1, 3.0)
    window = {"start": 1.0, "end": 2.0, "speakers": ["SPEAKER_00", "SPEAKER_01"]}

    candidate_a = original
    candidate_b = _tone(1000, 0.03, 3.0)

    # Embedder returns an all-zero embedding for both candidates - cosine
    # similarity to any non-zero centroid is 0, well below any reasonable
    # threshold, so neither stream should ever be trusted.
    isolator = _make_isolator(
        separator=_FakeSeparator(candidate_a, candidate_b),
        embedder=_FakeEmbedder([]),  # no matches registered -> always returns zeros
    )
    legitimate_embeddings = {
        "SPEAKER_00": np.array([1, 0]),
        "SPEAKER_01": np.array([0, 1]),
    }

    result = isolator._process_window(original, SR, window, legitimate_embeddings)

    assert result is None


def test_low_frequency_artifact_gate_rejects_new_buzz():
    # Original window has NO low-frequency content (clean 1kHz tone).
    original = _tone(1000, 0.1, 3.0)
    window = {"start": 1.0, "end": 2.0, "speakers": ["SPEAKER_00", "SPEAKER_01"]}

    candidate_a = original  # confidently matches SPEAKER_00
    # candidate_b introduces a strong 50Hz component the original never
    # had - exactly Problem 3's measured "severe low-freq buzz" failure
    # mode this gate exists to catch.
    candidate_b = _tone(50, 0.2, 3.0)

    isolator = _make_isolator(
        separator=_FakeSeparator(candidate_a, candidate_b),
        embedder=_FakeEmbedder([(candidate_a, [1, 0]), (candidate_b, [0, 1])]),
    )
    legitimate_embeddings = {
        "SPEAKER_00": np.array([1, 0]),
        "SPEAKER_01": np.array([0, 1]),
    }

    result = isolator._process_window(original, SR, window, legitimate_embeddings)

    assert result is None


def test_rms_sanity_gate_rejects_anomalous_level_change():
    original = _tone(1000, 0.1, 3.0)
    window = {"start": 1.0, "end": 2.0, "speakers": ["SPEAKER_00", "SPEAKER_01"]}

    # Same frequency as original (won't trip the low-freq gate), but ~20x
    # quieter than the original mix - an anomalous level change no
    # legitimate separation of this window should produce.
    candidate_a = _tone(1000, 0.005, 3.0)
    candidate_b = np.zeros_like(original)  # matches nothing

    isolator = _make_isolator(
        separator=_FakeSeparator(candidate_a, candidate_b),
        embedder=_FakeEmbedder(
            [(candidate_a, [1, 0])]
        ),  # candidate_b stays unmatched (zeros)
    )
    legitimate_embeddings = {
        "SPEAKER_00": np.array([1, 0]),
        "SPEAKER_01": np.array([0, 1]),
    }

    result = isolator._process_window(original, SR, window, legitimate_embeddings)

    assert result is None


def test_process_is_a_no_op_with_fewer_than_two_legitimate_speakers():
    isolator = _make_isolator(separator=None, embedder=None)
    audio = _tone(1000, 0.1, 3.0)
    diarization = [{"start": 0.0, "end": 6.0, "speaker": "SPEAKER_00"}]

    result = isolator.process(audio, SR, diarization, {"SPEAKER_00": np.array([1, 0])})

    assert result is audio  # early-return path, not even a copy


def test_process_is_a_no_op_with_no_overlap_windows():
    isolator = _make_isolator(separator=None, embedder=None)
    audio = _tone(1000, 0.1, 3.0)
    diarization = [
        {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
        {"start": 1.5, "end": 2.5, "speaker": "SPEAKER_01"},
    ]
    embeddings = {"SPEAKER_00": np.array([1, 0]), "SPEAKER_01": np.array([0, 1])}

    result = isolator.process(audio, SR, diarization, embeddings)

    assert result is audio


def test_process_only_modifies_the_overlap_window_region():
    original = _tone(1000, 0.1, 3.0)
    candidate_a = original
    candidate_b = _tone(1000, 0.03, 3.0)

    isolator = _make_isolator(
        separator=_FakeSeparator(candidate_a, candidate_b),
        embedder=_FakeEmbedder([(candidate_a, [1, 0]), (candidate_b, [0, 1])]),
        min_speaker_duration_s=0.5,
    )
    diarization = [
        {"start": 0.0, "end": 3.0, "speaker": "SPEAKER_00"},
        {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"},
    ]
    embeddings = {"SPEAKER_00": np.array([1, 0]), "SPEAKER_01": np.array([0, 1])}

    result = isolator.process(original, SR, diarization, embeddings)

    pad = int(isolator.context_padding_s * SR)
    touched_start = int(1.0 * SR) - pad
    touched_end = int(2.0 * SR) + pad

    # Well outside the touched window: byte-identical to the input.
    assert np.array_equal(
        result[: touched_start - SR // 2], original[: touched_start - SR // 2]
    )
    assert np.array_equal(
        result[touched_end + SR // 2 :], original[touched_end + SR // 2 :]
    )
    # Inside the touched window: NOT byte-identical (isolation applied).
    assert not np.array_equal(
        result[touched_start:touched_end], original[touched_start:touched_end]
    )
