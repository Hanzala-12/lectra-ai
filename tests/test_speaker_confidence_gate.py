"""
Tests for speaker_confidence_gate.py.

Two parts, matching target_voice_isolation.py's established testing
convention:
(a) gate_similarity_curve()/smooth_gain_db()/gain_curve_to_samples() -
    pure functions over plain numpy arrays, no model involved - tested
    with synthetic similarity curves, no mocks needed.
(b) SpeakerConfidenceGate's orchestration (similarity_curve() /
    compute_gain_curve()) - built by bypassing __init__ (object.__new__)
    and injecting a small fake embedder, same spirit as
    test_target_voice_isolation.py's _make_isolator/_FakeEmbedder (the
    real PretrainedSpeakerEmbedding is a local import inside __init__,
    matching this codebase's established pattern of not requiring
    speechbrain/pyannote just to import the module).
"""

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from speaker_confidence_gate import (
    SpeakerConfidenceGate,
    gate_similarity_curve,
    gain_curve_to_samples,
    smooth_gain_db,
)

HOP_S = 0.2


# ---------------------------------------------------------------------------
# (a) gate_similarity_curve
# ---------------------------------------------------------------------------


def test_all_confident_has_no_attenuation():
    similarity = np.full(50, 0.9)
    target_db = gate_similarity_curve(
        similarity,
        hop_s=HOP_S,
        threshold=0.6,
        min_low_confidence_duration_s=0.6,
        max_attenuation_db=-15.0,
    )
    assert np.all(target_db == 0.0)


def test_sustained_low_confidence_is_attenuated_and_bounded():
    # 30 hops @ 0.2s = 6s of sustained low confidence - well past the 0.6s
    # (3-hop) minimum.
    similarity = np.full(30, 0.1)
    target_db = gate_similarity_curve(
        similarity,
        hop_s=HOP_S,
        threshold=0.6,
        min_low_confidence_duration_s=0.6,
        max_attenuation_db=-15.0,
    )
    assert np.any(target_db == -15.0)
    assert np.all(target_db <= 0.0)  # never boosts, only attenuates or leaves alone
    assert np.all((target_db == 0.0) | (target_db == -15.0))  # bounded, no overshoot


def test_isolated_single_hop_dip_is_never_attenuated():
    # A single low-confidence hop surrounded by confident hops - a brief
    # blip (cough, single frame of cross-talk) - must never trigger
    # attenuation on its own, regardless of how low the similarity is.
    similarity = np.full(20, 0.9)
    similarity[10] = 0.01
    target_db = gate_similarity_curve(
        similarity,
        hop_s=HOP_S,
        threshold=0.6,
        min_low_confidence_duration_s=0.6,  # 3 hops minimum
        max_attenuation_db=-15.0,
    )
    assert np.all(target_db == 0.0)


def test_run_exactly_at_minimum_duration_attenuates_its_last_hop():
    # min_low_confidence_duration_s=0.6s @ hop=0.2s -> min_run_hops=3.
    # A run of exactly 3 low-confidence hops should attenuate (at least)
    # its final hop, not require the run to be strictly longer than the
    # minimum before anything engages.
    similarity = np.array([0.9, 0.9, 0.1, 0.1, 0.1, 0.9, 0.9])
    target_db = gate_similarity_curve(
        similarity,
        hop_s=HOP_S,
        threshold=0.6,
        min_low_confidence_duration_s=0.6,
        max_attenuation_db=-15.0,
    )
    assert target_db[4] == -15.0  # last hop of the minimal-length run
    assert target_db[0] == 0.0
    assert target_db[1] == 0.0
    assert target_db[5] == 0.0
    assert target_db[6] == 0.0


def test_multiple_separate_low_confidence_runs_are_each_evaluated():
    similarity = np.array([0.9] * 5 + [0.1] * 5 + [0.9] * 5 + [0.1] * 5 + [0.9] * 5)
    target_db = gate_similarity_curve(
        similarity,
        hop_s=HOP_S,
        threshold=0.6,
        min_low_confidence_duration_s=0.6,
        max_attenuation_db=-15.0,
    )
    # Both 5-hop low-confidence runs are well past the 3-hop minimum;
    # each attenuates its last (5 - (3-1)) = 3 hops.
    assert np.sum(target_db == -15.0) == 3 + 3


# ---------------------------------------------------------------------------
# (a) smooth_gain_db
# ---------------------------------------------------------------------------


def test_smoothing_never_overshoots_a_step_input():
    gain_db = np.zeros(50)
    gain_db[20:] = -15.0
    smoothed = smooth_gain_db(gain_db, hop_s=HOP_S, attack_s=0.05, release_s=0.3)
    assert np.all(smoothed <= 0.0)
    assert np.all(smoothed >= -15.0)


def test_attack_is_faster_than_release():
    # A brief dip: gain drops then immediately recovers. Attack (dropping)
    # uses a shorter time constant than release (rising), so the curve
    # should reach further toward the target on the way down within N hops
    # than it recovers within the same N hops on the way back up.
    gain_db = np.zeros(40)
    gain_db[10:20] = -15.0
    smoothed = smooth_gain_db(gain_db, hop_s=HOP_S, attack_s=0.05, release_s=0.5)
    drop_progress = smoothed[10] - smoothed[9]  # first hop of the drop (negative)
    rise_progress = smoothed[20] - smoothed[19]  # first hop of the recovery (positive)
    assert drop_progress < 0
    assert rise_progress > 0
    assert abs(drop_progress) > abs(rise_progress)  # attack moves faster than release


def test_smooth_gain_db_empty_input():
    assert len(smooth_gain_db(np.array([]), HOP_S, 0.05, 0.3)) == 0


# ---------------------------------------------------------------------------
# (a) gain_curve_to_samples
# ---------------------------------------------------------------------------


def test_gain_curve_to_samples_no_attenuation_is_all_ones():
    gain_db = np.zeros(10)
    samples = gain_curve_to_samples(gain_db, hop_s=HOP_S, sr=16000, n_samples=32000)
    assert len(samples) == 32000
    assert np.allclose(samples, 1.0)


def test_gain_curve_to_samples_converts_db_to_linear():
    gain_db = np.full(10, -20.0)  # -20dB = 0.1x linear
    samples = gain_curve_to_samples(gain_db, hop_s=HOP_S, sr=16000, n_samples=32000)
    assert np.allclose(samples, 0.1, atol=1e-3)


def test_gain_curve_to_samples_empty_is_noop():
    samples = gain_curve_to_samples(np.array([]), hop_s=HOP_S, sr=16000, n_samples=1000)
    assert len(samples) == 1000
    assert np.all(samples == 1.0)


# ---------------------------------------------------------------------------
# (b) SpeakerConfidenceGate - orchestration
# ---------------------------------------------------------------------------

SR = 16000


class _FakeEmbedder:
    """Stands in for pyannote's PretrainedSpeakerEmbedding. Returns a fixed
    embedding based on which half of the (synthetic) audio buffer a window
    was drawn from, so tests can control similarity outcomes deterministically
    without a real model. Accepts a BATCH (B, 1, T) and returns (B, dim),
    matching the real embedder's contract - also records call shapes so
    batching behavior itself can be asserted."""

    def __init__(self, split_at_sample, embedding_before, embedding_after):
        self.split_at_sample = split_at_sample
        self.embedding_before = np.asarray(embedding_before, dtype=np.float32)
        self.embedding_after = np.asarray(embedding_after, dtype=np.float32)
        self.call_batch_sizes = []

    def __call__(self, tensor):
        batch = tensor.detach().cpu().numpy()  # (B, 1, T)
        self.call_batch_sizes.append(batch.shape[0])
        out = []
        for i in range(batch.shape[0]):
            window = batch[i, 0]
            # Use the window's mean absolute sample value as a stand-in
            # "position" signal: synthetic test audio is built so windows
            # from the first half are near 0.0 and windows from the second
            # half are near 1.0 (see _make_split_audio below).
            out.append(
                self.embedding_after
                if np.mean(np.abs(window)) > 0.5
                else self.embedding_before
            )
        return np.stack(out)


def _make_isolator_free_gate(embedder, **overrides):
    """Build a SpeakerConfidenceGate without running its real __init__
    (which loads a real pyannote embedding model)."""
    import torch

    gate = object.__new__(SpeakerConfidenceGate)
    gate.device = "cpu"
    gate._torch = torch
    gate.embedder = embedder
    gate.min_speaker_duration_s = overrides.get("min_speaker_duration_s", 5.0)
    gate.window_s = overrides.get("window_s", 0.75)
    gate.hop_s = overrides.get("hop_s", 0.2)
    gate.embedding_batch_size = overrides.get("embedding_batch_size", 32)
    gate.match_confidence_threshold = overrides.get("match_confidence_threshold", 0.6)
    gate.min_low_confidence_duration_s = overrides.get(
        "min_low_confidence_duration_s", 0.6
    )
    gate.max_attenuation_db = overrides.get("max_attenuation_db", -15.0)
    gate.attack_s = overrides.get("attack_s", 0.05)
    gate.release_s = overrides.get("release_s", 0.3)
    return gate


def _make_split_audio(duration_s, split_s, sr=SR):
    n = int(duration_s * sr)
    split = int(split_s * sr)
    audio = np.zeros(n, dtype=np.float32)
    audio[:split] = 0.1  # "before" half: quiet, low mean-abs
    audio[split:] = 1.0  # "after" half: loud, high mean-abs
    return audio


def test_similarity_curve_matches_known_speaker_throughout():
    audio = _make_split_audio(duration_s=5.0, split_s=5.0)  # all "before"
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(embedder)
    speech_segments = [(0, len(audio))]
    legit = {"SPEAKER_00": np.array([1, 0])}

    similarity = gate.similarity_curve(audio, SR, speech_segments, legit)

    assert np.all(similarity > 0.9)  # confidently matches the whole way through


def test_similarity_curve_drops_where_speaker_doesnt_match():
    # First half sounds like SPEAKER_00 (matches), second half sounds like
    # an unrecognized voice (embedding orthogonal to every legitimate
    # speaker's centroid).
    audio = _make_split_audio(duration_s=6.0, split_s=3.0)
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(embedder)
    speech_segments = [(0, len(audio))]
    legit = {"SPEAKER_00": np.array([1, 0])}  # only SPEAKER_00 is legitimate

    similarity = gate.similarity_curve(audio, SR, speech_segments, legit)

    hop_samples = int(gate.hop_s * SR)
    early_hop = int(1.0 * SR) // hop_samples
    late_hop = int(5.0 * SR) // hop_samples
    assert similarity[early_hop] > 0.9
    assert similarity[late_hop] < 0.1


def test_similarity_curve_skips_non_speech_regions():
    audio = _make_split_audio(duration_s=4.0, split_s=4.0)
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(embedder)
    speech_segments = []  # nothing is speech
    legit = {"SPEAKER_00": np.array([1, 0])}

    similarity = gate.similarity_curve(audio, SR, speech_segments, legit)

    assert np.all(
        similarity == 1.0
    )  # default "fully trust" - moot, no speech there anyway
    assert embedder.call_batch_sizes == []  # never even called the model


def test_similarity_curve_batches_embedder_calls():
    audio = _make_split_audio(duration_s=10.0, split_s=10.0)
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(
        embedder, embedding_batch_size=8, hop_s=0.2, window_s=0.75
    )
    speech_segments = [(0, len(audio))]
    legit = {"SPEAKER_00": np.array([1, 0])}

    gate.similarity_curve(audio, SR, speech_segments, legit)

    n_hops = len(audio) // int(0.2 * SR)
    expected_calls = -(-n_hops // 8)  # ceil division
    assert len(embedder.call_batch_sizes) == expected_calls
    assert all(size <= 8 for size in embedder.call_batch_sizes)
    assert sum(embedder.call_batch_sizes) == n_hops


def test_compute_gain_curve_never_raises_and_is_noop_with_no_legitimate_speakers():
    audio = _make_split_audio(duration_s=3.0, split_s=3.0)
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(embedder)

    result = gate.compute_gain_curve(
        audio,
        SR,
        speech_segments=[(0, len(audio))],
        diarization_results=[],
        speaker_embeddings={},
    )

    assert len(result) == len(audio)
    assert np.all(result == 1.0)


def test_compute_gain_curve_end_to_end_attenuates_unrecognized_stretch():
    audio = _make_split_audio(duration_s=6.0, split_s=3.0)
    embedder = _FakeEmbedder(
        split_at_sample=None, embedding_before=[1, 0], embedding_after=[0, 1]
    )
    gate = _make_isolator_free_gate(embedder, min_speaker_duration_s=1.0)
    diarization_results = [{"start": 0.0, "end": 6.0, "speaker": "SPEAKER_00"}]
    speaker_embeddings = {"SPEAKER_00": np.array([1, 0])}

    gain_curve = gate.compute_gain_curve(
        audio,
        SR,
        speech_segments=[(0, len(audio))],
        diarization_results=diarization_results,
        speaker_embeddings=speaker_embeddings,
    )

    assert len(gain_curve) == len(audio)
    early = gain_curve[int(1.0 * SR)]
    late = gain_curve[int(5.0 * SR)]
    assert early > 0.9  # matches the known speaker - untouched
    assert late < 0.5  # doesn't match - attenuated, but not necessarily to full silence
