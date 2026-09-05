"""
Target Voice Isolation Module

Separates genuinely overlapping speech (e.g. a student talking over the
lecturer, or voice-like background chatter) BEFORE DeepFilterNet/MetricGAN+
run - STEP 2.5 in pipeline.py, right after diarization.

Why this exists: measured on a real lecture this session, DeepFilterNet3->
MetricGAN+ crush stationary noise almost perfectly (~-73dB on quiet-only
frames) but only manage ~-2dB on frames where two people are talking at
once - they are speech-PRESERVING denoisers, not source separators, so
anything voice-like (including a second, unwanted voice) is exactly what
they're built to protect rather than remove. See
docs/NOISE_REMOVAL_AND_DIARIZATION.md "Problem 4" for the full writeup and
"Problem 3" for why an earlier SepFormer checkpoint (a single-stream
*enhancer*, competing with MetricGAN+ at MetricGAN+'s own job, run on an
*entire* file) was rejected - this module uses a different checkpoint for a
different task (2-speaker separation) on a tiny fraction of the audio
(detected overlap windows only), but takes that prior rejection's measured
failure mode (severe low-freq buzz) seriously enough to gate against it
directly (see _low_freq_energy below).

Models (both via SpeechBrain, already a pinned dependency for MetricGAN+ -
no new heavy dependency, just a new pretrained checkpoint downloaded on
first use, same as MetricGAN+ already does):
- Separation: speechbrain/sepformer-whamr16k (2-speaker, 16kHz, Apache 2.0,
  trained on WHAMR! = WSJ0-2mix + injected noise/reverb - NOTE this is
  scripted clean read speech, not spontaneous classroom audio, a real
  domain shift that's the reason every gate below exists).
- Speaker matching: pyannote's OWN diarization embedding model, reused
  rather than loading a second one - SpeakerDiarization.pipeline.embedding
  names it (this project's cached checkpoint: WeSpeaker ResNet34-LM via
  ONNX Runtime, already an installed transitive dependency via piper-tts).

Safety philosophy (matches this codebase's established "degrade, don't
risk making it worse" pattern - GPU tunnel fallback, missing HF_TOKEN
fallback, beautify's own max_snr_drop_db auto-disable): every overlap
window this module touches passes through a chain of gates (confidence,
low-frequency-energy, RMS/SNR sanity) before its separated audio is
trusted. Failing ANY gate falls back to that window's original,
untouched audio - this module can only ever leave a window unchanged or
make it better, never silently accept a worse result.
"""

import os
import logging
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def find_overlap_windows(
    diarization_results: List[Dict], min_overlap_s: float = 0.3
) -> List[Dict]:
    """
    Find time ranges where 2+ distinct diarized speakers' segments
    intersect - i.e. genuine overlapping speech, the one thing
    DeepFilterNet/MetricGAN+ cannot remove (see module docstring).

    Pure function over plain {start,end,speaker} dicts (the exact shape
    SpeakerDiarization.diarize() already returns) - no model involved,
    directly unit-testable.

    Args:
        diarization_results: [{'start': float, 'end': float, 'speaker': str}, ...]
        min_overlap_s: ignore overlaps shorter than this (not worth the
            SepFormer cost - likely a diarization boundary-rounding blip)

    Returns:
        [{'start': float, 'end': float, 'speakers': [str, ...]}, ...],
        sorted by start - each entry a maximal overlap interval with every
        distinct speaker label active anywhere inside it.
    """
    if not diarization_results:
        return []

    events = []
    for seg in diarization_results:
        if seg["end"] <= seg["start"]:
            continue
        events.append((seg["start"], 1, seg["speaker"]))
        events.append((seg["end"], -1, seg["speaker"]))
    # Process every start at a timestamp before any end at that same
    # timestamp, so two segments that touch exactly at a shared boundary
    # register as briefly overlapping rather than missing each other.
    events.sort(key=lambda e: (e[0], -e[1]))

    active_counts: Dict[str, int] = {}
    windows = []
    window_start = None
    window_speakers: set = set()

    def _distinct_active() -> int:
        return sum(1 for c in active_counts.values() if c > 0)

    for time, delta, speaker in events:
        was_overlap = _distinct_active() >= 2
        active_counts[speaker] = active_counts.get(speaker, 0) + delta
        is_overlap = _distinct_active() >= 2

        if is_overlap and not was_overlap:
            window_start = time
            window_speakers = {s for s, c in active_counts.items() if c > 0}
        elif is_overlap:
            window_speakers |= {s for s, c in active_counts.items() if c > 0}
        elif was_overlap and not is_overlap:
            if window_start is not None and time - window_start >= min_overlap_s:
                windows.append(
                    {
                        "start": window_start,
                        "end": time,
                        "speakers": sorted(window_speakers),
                    }
                )
            window_start = None
            window_speakers = set()

    return windows


def identify_legitimate_speakers(
    diarization_results: List[Dict], min_total_duration_s: float = 5.0
) -> List[str]:
    """
    Which diarized speaker labels are worth treating as "a real speaker to
    preserve" rather than a one-off blip (a cough, a chair scrape, a
    boundary artifact briefly misclustered as its own "speaker"). Gates
    two things in TargetVoiceIsolator.process(): which overlap windows are
    worth the SepFormer cost at all (an overlap only involving
    illegitimate speakers isn't), and which centroids a separated
    candidate stream is allowed to be matched against (matching against a
    blip's low-duration, noisy centroid would be unreliable).

    Pure function, same input shape as find_overlap_windows().

    Args:
        diarization_results: [{'start','end','speaker'}, ...]
        min_total_duration_s: minimum cumulative speaking time (summed
            across every segment for that label, not just the longest
            one) a speaker needs to count as legitimate.

    Returns:
        Sorted list of speaker labels meeting the duration threshold.
    """
    totals: Dict[str, float] = {}
    for seg in diarization_results:
        duration = seg["end"] - seg["start"]
        if duration <= 0:
            continue
        totals[seg["speaker"]] = totals.get(seg["speaker"], 0.0) + duration

    return sorted(spk for spk, total in totals.items() if total >= min_total_duration_s)


def _rms(waveform: np.ndarray) -> float:
    if len(waveform) == 0:
        return 0.0
    return float(np.sqrt(np.mean(waveform.astype(np.float64) ** 2)))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Public (not module-private) since speaker_confidence_gate.py also
    imports this across the module boundary."""
    a = np.asarray(a).reshape(-1)
    b = np.asarray(b).reshape(-1)
    denom = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-10
    return float(np.dot(a, b) / denom)


class TargetVoiceIsolator:
    """
    Separates genuinely overlapping speech before it reaches
    DeepFilterNet/MetricGAN+. Only ever touches the specific time windows
    find_overlap_windows() flags as genuine overlap between legitimate
    speakers; every other sample of the input is returned byte-identical.
    """

    SEPARATOR_REPO = "speechbrain/sepformer-whamr16k"
    SEPARATOR_SAMPLE_RATE = 16000

    def __init__(
        self,
        embedding_model_name: str,
        device: str = "cpu",
        model_dir: str = None,
        min_overlap_duration_s: float = 0.3,
        min_speaker_duration_s: float = 5.0,
        match_confidence_threshold: float = 0.65,
        context_padding_s: float = 0.5,
        crossfade_s: float = 0.25,
        low_freq_gate_hz: float = 150.0,
    ):
        """
        Args:
            embedding_model_name: the SAME embedding model name pyannote's
                diarization pipeline itself uses (SpeakerDiarization's
                `pipeline.embedding` attribute, e.g.
                'pyannote/wespeaker-voxceleb-resnet34-LM') - reused here so
                a newly-separated candidate stream is embedded in the same
                space as the centroids diarize_with_embeddings() returns.
            device: 'cuda' or 'cpu'. Caller (pipeline.py) is expected to
                have already checked config's require_gpu before
                constructing this - Problem 3 measured this model family
                at ~7x realtime on CPU for a full-file pass; this module
                only ever processes short windows, but still isn't meant
                for routine CPU use.
        """
        # Reuse MetricGAN+'s Windows/huggingface_hub compat patches
        # (symlink->copy fallback, use_auth_token->token rename) rather
        # than duplicating them - same SpeechBrain download path.
        try:
            from .metricgan_processor import _install_compat_patches
        except ImportError:
            from metricgan_processor import _install_compat_patches
        _install_compat_patches()

        import torch

        self.device = device
        self._torch = torch
        self.min_overlap_duration_s = min_overlap_duration_s
        self.min_speaker_duration_s = min_speaker_duration_s
        self.match_confidence_threshold = match_confidence_threshold
        self.context_padding_s = context_padding_s
        self.crossfade_s = crossfade_s
        self.low_freq_gate_hz = low_freq_gate_hz

        if model_dir is None:
            model_dir = os.path.join(
                os.path.dirname(__file__), "..", "models", "target_voice_isolation"
            )
        model_dir = os.path.abspath(model_dir)
        os.makedirs(model_dir, exist_ok=True)

        if not os.path.exists(os.path.join(model_dir, "hyperparams.yaml")):
            from huggingface_hub import snapshot_download

            logger.info("Downloading SepFormer (whamr16k) model (first use)...")
            snapshot_download(
                self.SEPARATOR_REPO,
                allow_patterns=["*.yaml", "*.ckpt", "*.bin", "*.txt", "*.py"],
                local_dir=model_dir,
            )

        # Force COPY instead of symlink when SpeechBrain populates savedir
        # (same fix metricgan_processor.py already needs on Windows).
        import speechbrain.utils.fetching as _fetch

        _ls = _fetch.LocalStrategy
        _orig_link = _fetch.link_with_strategy
        _fetch.link_with_strategy = lambda s, d, st: _orig_link(s, d, _ls.COPY)

        from speechbrain.inference.separation import SepformerSeparation

        logger.info(f"Loading SepFormer (whamr16k) on {device}")
        self.separator = SepformerSeparation.from_hparams(
            source=model_dir, savedir=model_dir, run_opts={"device": device}
        )

        # Public factory pyannote itself uses internally to build its own
        # embedding model - passing the same model name reused from
        # SpeakerDiarization.pipeline.embedding gives numerically
        # consistent embeddings without touching any private attribute.
        from pyannote.audio.pipelines.speaker_verification import (
            PretrainedSpeakerEmbedding,
        )

        logger.info(
            f"Loading speaker embedding model ({embedding_model_name}) for stream matching"
        )
        self.embedder = PretrainedSpeakerEmbedding(
            embedding_model_name, device=torch.device(device)
        )

        logger.info("Target Voice Isolator ready")

    def process(
        self,
        audio: np.ndarray,
        sr: int,
        diarization_results: List[Dict],
        speaker_embeddings: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """
        Returns a possibly-modified COPY of `audio`: overlap windows that
        pass every safety gate are replaced with the isolated, gain-
        matched, crossfaded-in target speaker audio; every other sample -
        including any overlap window that fails a gate - is untouched.
        Never raises: any per-window failure keeps that window's original
        audio, and a total failure (e.g. no legitimate speakers at all)
        returns `audio` completely unchanged.
        """
        legitimate = identify_legitimate_speakers(
            diarization_results, self.min_speaker_duration_s
        )
        if len(legitimate) < 2:
            logger.info(
                "Target Voice Isolation: fewer than 2 legitimate speakers - nothing to separate"
            )
            return audio

        windows = find_overlap_windows(diarization_results, self.min_overlap_duration_s)
        legitimate_set = set(legitimate)
        windows = [w for w in windows if len(set(w["speakers"]) & legitimate_set) >= 2]
        if not windows:
            logger.info("Target Voice Isolation: no genuine overlap windows found")
            return audio

        legitimate_embeddings = {
            spk: speaker_embeddings[spk]
            for spk in legitimate
            if spk in speaker_embeddings
        }
        if len(legitimate_embeddings) < 2:
            logger.info(
                "Target Voice Isolation: fewer than 2 speaker embeddings available - skipping"
            )
            return audio

        out = audio.copy()
        accepted, rejected = 0, 0
        for window in windows:
            try:
                replacement = self._process_window(
                    out, sr, window, legitimate_embeddings
                )
            except Exception as e:
                logger.warning(
                    f"Target Voice Isolation failed on window "
                    f"{window['start']:.2f}-{window['end']:.2f}s ({e}) - "
                    f"keeping original audio for this window"
                )
                replacement = None

            if replacement is None:
                rejected += 1
                continue
            accepted += 1
            self._splice(out, sr, window, replacement)

        logger.info(
            f"Target Voice Isolation: {accepted} window(s) isolated, "
            f"{rejected} window(s) kept as original (of {len(windows)} candidate)"
        )
        return out

    def _process_window(
        self,
        audio: np.ndarray,
        sr: int,
        window: Dict,
        legitimate_embeddings: Dict[str, np.ndarray],
    ) -> Optional[np.ndarray]:
        """Run separation + matching + safety gates on one overlap window.
        Returns replacement audio at the padded window's original sample
        rate/length, or None if any gate rejects it."""
        torch = self._torch

        pad = int(self.context_padding_s * sr)
        start_i = max(0, int(window["start"] * sr) - pad)
        end_i = min(len(audio), int(window["end"] * sr) + pad)
        original_slice = audio[start_i:end_i].astype(np.float32)
        if len(original_slice) < sr * 0.1:
            return None

        if sr != self.SEPARATOR_SAMPLE_RATE:
            import librosa

            sep_input = librosa.resample(
                original_slice, orig_sr=sr, target_sr=self.SEPARATOR_SAMPLE_RATE
            ).astype(np.float32)
        else:
            sep_input = original_slice

        with torch.no_grad():
            mix = torch.from_numpy(sep_input).float().unsqueeze(0)  # (1, T)
            est_sources = self.separator.separate_batch(mix)  # (1, T, num_spks)
        num_spks = est_sources.shape[-1]
        candidates = [
            est_sources[0, :, i].detach().cpu().numpy().astype(np.float32)
            for i in range(num_spks)
        ]

        embedded = [
            (candidate, self._embed(candidate, self.SEPARATOR_SAMPLE_RATE))
            for candidate in candidates
        ]

        # Keep every candidate stream that confidently matches ANY
        # legitimate speaker (both voices in a real overlapping exchange
        # should survive, not just whichever one scores highest).
        kept = np.zeros_like(sep_input)
        any_kept = False
        for candidate, emb in embedded:
            if emb is None:
                continue
            sims = {
                speaker: cosine_similarity(emb, centroid)
                for speaker, centroid in legitimate_embeddings.items()
            }
            top_speaker = max(sims, key=sims.get)
            if sims[top_speaker] >= self.match_confidence_threshold:
                kept += candidate
                any_kept = True

        if not any_kept:
            return None

        # Low-frequency artifact gate: Problem 3's own measured failure
        # mode for this model family was "severe low-freq buzz". Reject if
        # this candidate materially INCREASED low-band energy versus the
        # original mixed window (some headroom allowed - separation
        # legitimately redistributes energy between streams).
        original_low = self._low_freq_energy(sep_input, self.SEPARATOR_SAMPLE_RATE)
        kept_low = self._low_freq_energy(kept, self.SEPARATOR_SAMPLE_RATE)
        if kept_low > original_low * 1.5 + 1e-8:
            return None

        if sr != self.SEPARATOR_SAMPLE_RATE:
            import librosa

            kept = librosa.resample(
                kept, orig_sr=self.SEPARATOR_SAMPLE_RATE, target_sr=sr
            ).astype(np.float32)
        # A resample round-trip can drift by a sample or two.
        if len(kept) != len(original_slice):
            if len(kept) > len(original_slice):
                kept = kept[: len(original_slice)]
            else:
                kept = np.pad(kept, (0, len(original_slice) - len(kept)))

        # RMS/SNR sanity gate, mirroring beautify.max_snr_drop_db's
        # existing auto-disable pattern: reject an anomalously quiet or
        # loud result rather than trust it blindly.
        orig_rms = _rms(original_slice)
        kept_rms = _rms(kept)
        if orig_rms < 1e-6:
            return None
        ratio_db = 20 * np.log10((kept_rms + 1e-10) / (orig_rms + 1e-10))
        if abs(ratio_db) > 6:
            return None

        # Gain-match: separate_batch() does NOT auto-normalize like
        # separate_file() does - match RMS to the original window before
        # splicing so there's no audible level jump at the boundary.
        if kept_rms > 1e-8:
            kept = kept * (orig_rms / kept_rms)

        return kept.astype(np.float32)

    def _splice(
        self, audio: np.ndarray, sr: int, window: Dict, replacement: np.ndarray
    ) -> None:
        """In-place crossfade of `replacement` into `audio` at the
        window's padded offsets - the same linear-ramp overlap-add pattern
        already used for DeepFilterNet chunking (pipeline.py) and
        MetricGAN+ chunking (metricgan_processor.py), not a 10ms click-
        fade (too short to blend two differently-processed real signals)."""
        pad = int(self.context_padding_s * sr)
        start_i = max(0, int(window["start"] * sr) - pad)
        end_i = min(len(audio), int(window["end"] * sr) + pad)
        n = end_i - start_i
        if n <= 0 or len(replacement) != n:
            return

        fade = min(int(self.crossfade_s * sr), n // 2)
        weight = np.ones(n, dtype=np.float32)
        if fade > 0:
            weight[:fade] = np.linspace(0, 1, fade, dtype=np.float32)
            weight[-fade:] = np.minimum(
                weight[-fade:], np.linspace(1, 0, fade, dtype=np.float32)
            )

        original = audio[start_i:end_i]
        audio[start_i:end_i] = original * (1 - weight) + replacement * weight

    def _embed(self, waveform: np.ndarray, sr: int) -> Optional[np.ndarray]:
        """Embed one candidate waveform via the SAME embedding model
        pyannote's diarization pipeline itself uses, so this lands in the
        same space as diarize_with_embeddings()'s centroids."""
        torch = self._torch
        if len(waveform) < sr * 0.25:  # too short for a reliable embedding
            return None
        try:
            tensor = torch.from_numpy(waveform).float().reshape(1, 1, -1)
            emb = self.embedder(tensor)  # (1, dimension) numpy array
            return np.asarray(emb).reshape(-1)
        except Exception as e:
            logger.warning(f"Speaker embedding failed: {e}")
            return None

    def _low_freq_energy(self, waveform: np.ndarray, sr: int) -> float:
        from scipy.signal import butter, sosfilt

        nyq = sr / 2
        cutoff = min(self.low_freq_gate_hz, nyq * 0.9)
        sos = butter(4, cutoff, btype="lowpass", output="sos", fs=sr)
        low = sosfilt(sos, waveform)
        return float(np.mean(low.astype(np.float64) ** 2))
