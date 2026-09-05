"""
Speaker Confidence Gate

Continuously, across the WHOLE file (not just diarization-flagged overlap
windows), suppresses audio that doesn't confidently match one of the
file's known/legitimate speakers - closing a gap `target_voice_isolation.py`
deliberately does not cover.

Why this exists: measured live this session, a solo-lecturer stretch with
no diarized overlap (94.8s-103s in a real test lecture) got almost zero
noise reduction (-0.3dB) from DeepFilterNet/MetricGAN+, vs. true silence
gaps getting crushed by +36 to +90dB. Diagnosis: faint background
voice-like content too quiet/diffuse for pyannote's diarization to ever
cluster as its OWN distinct speaker turn is invisible to BOTH
`target_voice_isolation.TargetVoiceIsolator` (only acts where 2
*recognized* speakers overlap) and DeepFilterNet/MetricGAN+ (protect
anything voice-shaped, can't tell "the known speaker" from "some other
voice"). See docs/NOISE_REMOVAL_AND_DIARIZATION.md "Problem 5".

Architecture: analyze early, apply late (see pipeline.py's two call
sites - one right after `speech_segments` is finalized, computing a
similarity curve on the LEAST-processed audio so it's directly comparable
to `diarize_with_embeddings()`'s centroids; one much later, after final
loudness normalization/limiting and before Voice Beautify, multiplying
the resulting gain curve into the fully-processed signal so nothing
downstream - adaptive_gain_ride's upward boosting, in particular - can
fight or undo the suppression).

Safety, two independent layers (this stage touches every speech frame in
the file, not rare flagged windows, so the blast radius of a false
positive is much larger than target_voice_isolation's - both layers exist
because either alone is not enough):
1. Bounded attenuation, never full silence (`max_attenuation_db`) - a
   false positive on the real speaker's own atypical-sounding moment
   (different mic distance, emotion, pitch) becomes "a bit quieter," not
   an obvious dropout.
2. Sustained-evidence requirement (`min_low_confidence_duration_s`) -
   attenuation only engages after a RUN of low-confidence hops, not a
   single one. This matters specifically because genuine overlap windows
   between two legitimate speakers (which target_voice_isolation
   deliberately sums together - see its _process_window's `kept +=
   candidate` for every stream matching any legitimate speaker) are
   still literal two-voice mixtures by the time this gate sees them, and
   a mixture's embedding sits away from either individual centroid - a
   real false-positive risk on wanted cross-talk that a brief-dip filter
   removes, using duration as a signal independent of the noisy
   instantaneous similarity score itself.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from .target_voice_isolation import identify_legitimate_speakers, cosine_similarity
except ImportError:
    from target_voice_isolation import identify_legitimate_speakers, cosine_similarity

logger = logging.getLogger(__name__)


def gate_similarity_curve(
    similarity: np.ndarray,
    hop_s: float,
    threshold: float,
    min_low_confidence_duration_s: float,
    max_attenuation_db: float,
) -> np.ndarray:
    """
    Turn a per-hop similarity curve into a per-hop TARGET gain-in-dB curve
    (0.0 = fully trust this hop, max_attenuation_db = fully distrust it),
    BEFORE smoothing. Pure function, no model - directly unit-testable
    with a synthetic similarity array.

    Attenuation only engages after a sustained run of sub-threshold hops
    (>= min_low_confidence_duration_s) reaches that length - not
    retroactively over the whole run, only from the point the run has
    proven itself sustained onward. A run shorter than that (a brief dip)
    never triggers any attenuation at all.

    Args:
        similarity: 1-D array, one max-cosine-similarity-to-any-legitimate-
            speaker value per hop (from SpeakerConfidenceGate.similarity_curve).
        hop_s: seconds per hop (matches the hop used to build `similarity`).
        threshold: below this, a hop counts as "doesn't match a known speaker".
        min_low_confidence_duration_s: required sustained run length before
            attenuation is allowed to engage at all.
        max_attenuation_db: target attenuation once engaged (negative dB).

    Returns:
        1-D array, same length as `similarity`, each value 0.0 or
        `max_attenuation_db`.
    """
    n = len(similarity)
    target_db = np.zeros(n, dtype=np.float64)
    if n == 0:
        return target_db

    min_run_hops = max(1, int(round(min_low_confidence_duration_s / hop_s)))
    below = similarity < threshold

    i = 0
    while i < n:
        if not below[i]:
            i += 1
            continue
        j = i
        while j < n and below[j]:
            j += 1
        run_len = j - i
        if run_len >= min_run_hops:
            # Attenuate from the hop where the run FIRST reaches
            # min_run_hops of sustained evidence (inclusive) through the
            # rest of the run - not retroactively over the hops that
            # accumulated that evidence. A run of exactly min_run_hops
            # still attenuates its last hop, rather than requiring the
            # run to be strictly longer than the minimum before anything
            # engages.
            target_db[i + min_run_hops - 1 : j] = max_attenuation_db
        i = j

    return target_db


def smooth_gain_db(
    gain_db: np.ndarray, hop_s: float, attack_s: float, release_s: float
) -> np.ndarray:
    """
    Asymmetric exponential smoothing over a per-hop dB gain curve - the
    same formula as voice_beautify.py's _level(): fast movement when the
    target gain is DROPPING (attack - suppression should engage promptly
    once genuinely triggered), slower when RISING back toward 0dB
    (release - avoids an abrupt, audible snap back to full volume). Pure
    function, no model.

    Args:
        gain_db: 1-D per-hop target gain curve (e.g. from gate_similarity_curve).
        hop_s: seconds per hop.
        attack_s: time constant for gain decreasing (getting quieter).
        release_s: time constant for gain increasing (getting louder again).

    Returns:
        1-D smoothed dB curve, same length as `gain_db`.
    """
    n = len(gain_db)
    sm = np.zeros(n, dtype=np.float64)
    if n == 0:
        return sm

    a_attack = 1 - np.exp(-hop_s / attack_s)
    a_release = 1 - np.exp(-hop_s / release_s)

    sm[0] = gain_db[0]
    for i in range(1, n):
        coef = a_attack if gain_db[i] < sm[i - 1] else a_release
        sm[i] = sm[i - 1] + coef * (gain_db[i] - sm[i - 1])

    return sm


def gain_curve_to_samples(
    gain_db_smoothed: np.ndarray, hop_s: float, sr: int, n_samples: int
) -> np.ndarray:
    """
    Sample-accurate linear interpolation of a smoothed per-hop dB curve
    into a full per-SAMPLE linear gain array - same np.interp approach as
    voice_beautify.py's _level(), avoiding the stair-stepping a
    piecewise-constant per-hop multiply would leave audible.

    Returns an all-ones (no-op) array of length `n_samples` if
    `gain_db_smoothed` is empty.
    """
    if len(gain_db_smoothed) == 0 or n_samples <= 0:
        return np.ones(max(0, n_samples), dtype=np.float32)

    hop_samples = hop_s * sr
    n_hops = len(gain_db_smoothed)
    hop_positions = np.arange(n_hops) * hop_samples
    sample_positions = np.arange(n_samples)
    gain_db_per_sample = np.interp(
        sample_positions,
        hop_positions,
        gain_db_smoothed,
        left=gain_db_smoothed[0],
        right=gain_db_smoothed[-1],
    )
    return (10 ** (gain_db_per_sample / 20.0)).astype(np.float32)


class SpeakerConfidenceGate:
    """
    Owns the speaker-embedding model used to continuously check "does this
    stretch of audio match a known speaker" across a whole file. Deliberately
    does NOT share an embedder instance with TargetVoiceIsolator - see
    module docstring / docs/NOISE_REMOVAL_AND_DIARIZATION.md "Problem 5" for
    why (independent device configs, TargetVoiceIsolator's Kaggle-live
    lifecycle not worth coupling into for a small load-time save). An
    already-built embedder can be injected via `embedder=` if that ever
    changes.
    """

    def __init__(
        self,
        embedding_model_name: str,
        device: str = "cpu",
        embedder=None,
        min_speaker_duration_s: float = 5.0,
        window_s: float = 0.75,
        hop_s: float = 0.2,
        embedding_batch_size: int = 32,
        match_confidence_threshold: float = 0.6,
        min_low_confidence_duration_s: float = 0.6,
        max_attenuation_db: float = -15.0,
        attack_s: float = 0.05,
        release_s: float = 0.3,
    ):
        import torch

        self.device = device
        self._torch = torch
        self.min_speaker_duration_s = min_speaker_duration_s
        self.window_s = window_s
        self.hop_s = hop_s
        self.embedding_batch_size = embedding_batch_size
        self.match_confidence_threshold = match_confidence_threshold
        self.min_low_confidence_duration_s = min_low_confidence_duration_s
        self.max_attenuation_db = max_attenuation_db
        self.attack_s = attack_s
        self.release_s = release_s

        if embedder is not None:
            self.embedder = embedder
        else:
            from pyannote.audio.pipelines.speaker_verification import (
                PretrainedSpeakerEmbedding,
            )

            logger.info(
                f"Loading speaker embedding model ({embedding_model_name}) "
                f"for the confidence gate"
            )
            self.embedder = PretrainedSpeakerEmbedding(
                embedding_model_name, device=torch.device(device)
            )

        logger.info("Speaker Confidence Gate ready")

    def similarity_curve(
        self,
        audio: np.ndarray,
        sr: int,
        speech_segments: List[Tuple[int, int]],
        legitimate_embeddings: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """
        The only method touching the real embedding model. Slides a
        `window_s` window at `hop_s` hop across the file, but only where
        `speech_segments` says there's speech at all (silence is already
        handled elsewhere - true gaps get crushed by DFN/MetricGAN+
        regardless of this gate, no need to spend embedding calls there).
        Embeds windows in BATCHES (`embedding_batch_size`, mirroring
        diarization.py's own `embedding_batch_size = 32`, empirically
        proven identical-output-but-faster there) rather than one call per
        window - this is the load-bearing performance fix; see
        scripts/benchmark_speaker_confidence_gate.py for the measured
        real-world cost this was calibrated against.

        Returns:
            1-D array, one value per hop across [0, len(audio)/sr), each
            the max cosine similarity to any legitimate speaker's centroid
            (or 1.0 - "fully trust it" - for hops outside any speech
            segment, since they're moot: STEP 5's zero-background mask
            already zeroes non-speech audio before this gate's resulting
            gain curve is ever multiplied in).
        """
        torch = self._torch
        hop_samples = int(self.hop_s * sr)
        window_samples = int(self.window_s * sr)
        n_samples = len(audio)
        n_hops = max(1, n_samples // hop_samples)

        similarity = np.ones(n_hops, dtype=np.float64)
        if not legitimate_embeddings:
            return similarity

        def _in_speech(hop_start: int, hop_end: int) -> bool:
            for seg_start, seg_end in speech_segments:
                if hop_start < seg_end and hop_end > seg_start:
                    return True
            return False

        centroids = {
            spk: np.asarray(emb).reshape(-1)
            for spk, emb in legitimate_embeddings.items()
        }

        pending_indices: List[int] = []
        pending_windows: List[np.ndarray] = []

        def _flush():
            if not pending_windows:
                return
            with torch.no_grad():
                batch = np.stack(pending_windows).astype(np.float32)
                tensor = torch.from_numpy(batch).unsqueeze(1)  # (B, 1, T)
                try:
                    embeddings = self.embedder(tensor)  # (B, dimension)
                except Exception as e:
                    logger.warning(
                        f"Speaker confidence gate: batch embedding failed: {e}"
                    )
                    pending_indices.clear()
                    pending_windows.clear()
                    return
            for idx, emb in zip(pending_indices, embeddings):
                best = max(
                    cosine_similarity(emb, centroid) for centroid in centroids.values()
                )
                similarity[idx] = best
            pending_indices.clear()
            pending_windows.clear()

        for h in range(n_hops):
            hop_start = h * hop_samples
            hop_end = min(hop_start + hop_samples, n_samples)
            if not _in_speech(hop_start, hop_end):
                continue

            win_start = max(0, min(hop_start, n_samples - window_samples))
            win_end = win_start + window_samples
            if win_end > n_samples:
                # File shorter than one window - pad with zeros so shape
                # stays uniform across the batch.
                window = np.zeros(window_samples, dtype=np.float32)
                available = audio[win_start:n_samples]
                window[: len(available)] = available
            else:
                window = audio[win_start:win_end]

            pending_indices.append(h)
            pending_windows.append(window)
            if len(pending_windows) >= self.embedding_batch_size:
                _flush()
        _flush()

        return similarity

    def compute_gain_curve(
        self,
        audio: np.ndarray,
        sr: int,
        speech_segments: List[Tuple[int, int]],
        diarization_results: List[Dict],
        speaker_embeddings: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """
        Orchestrates similarity_curve -> gate_similarity_curve ->
        smooth_gain_db -> gain_curve_to_samples into one full-length
        (`len(audio)`) linear gain array ready to multiply into the final
        processed signal. Never raises - returns an all-ones (no-op) array
        on any failure, matching TargetVoiceIsolator.process()'s "worst
        case: unchanged" contract.
        """
        try:
            legitimate = identify_legitimate_speakers(
                diarization_results, self.min_speaker_duration_s
            )
            legitimate_embeddings = {
                spk: speaker_embeddings[spk]
                for spk in legitimate
                if spk in speaker_embeddings
            }
            if not legitimate_embeddings:
                logger.info(
                    "Speaker Confidence Gate: no legitimate speaker embeddings available - skipping"
                )
                return np.ones(len(audio), dtype=np.float32)

            similarity = self.similarity_curve(
                audio, sr, speech_segments, legitimate_embeddings
            )
            target_db = gate_similarity_curve(
                similarity,
                self.hop_s,
                self.match_confidence_threshold,
                self.min_low_confidence_duration_s,
                self.max_attenuation_db,
            )
            attenuated_hops = int(np.sum(target_db < 0))
            logger.info(
                f"Speaker Confidence Gate: {attenuated_hops}/{len(target_db)} "
                f"hop(s) flagged for attenuation ({attenuated_hops * self.hop_s:.1f}s)"
            )
            smoothed_db = smooth_gain_db(
                target_db, self.hop_s, self.attack_s, self.release_s
            )
            return gain_curve_to_samples(smoothed_db, self.hop_s, sr, len(audio))
        except Exception as e:
            logger.warning(
                f"Speaker Confidence Gate failed, using unchanged audio: {e}"
            )
            return np.ones(len(audio), dtype=np.float32)
