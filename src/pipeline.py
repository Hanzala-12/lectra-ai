"""
Main Lectra AI Pipeline
Orchestrates the complete processing workflow
"""

import os
import time
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np
from scipy.ndimage import uniform_filter1d
from scipy.signal import lfilter

# Setup logging early so optional import fallbacks can use logger safely
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def adaptive_gain_ride(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Adaptive per-frame gain riding to correct dimness caused by DeepFilterNet
    over-suppression in the 1-3kHz speech presence band.
    Replaces static peak normalization.
    """
    TARGET_RMS_DB = -18.0
    TARGET_RMS = 10 ** (TARGET_RMS_DB / 20)
    FRAME_LEN = int(sr * 0.03)
    HOP_LEN = int(sr * 0.010)
    MAX_GAIN_DB = (
        6.0  # was 10 — lower so quiet frames aren't over-boosted (reduces pumping)
    )
    MIN_GAIN_DB = -3.0
    SPEECH_FLOOR = 0.012  # was 0.004 (~-48dB) — raised to ~-38dB so quiet noise-only
    # frames between words are NOT boosted (that was lifting the background noise floor)
    ATTACK_SMOOTH = int(0.08 / (HOP_LEN / sr))
    RELEASE_SMOOTH = int(0.25 / (HOP_LEN / sr))

    num_hops = (len(audio) - FRAME_LEN) // HOP_LEN

    # Per-hop RMS
    rms_curve = np.array(
        [
            np.sqrt(np.mean(audio[i * HOP_LEN : i * HOP_LEN + FRAME_LEN] ** 2))
            for i in range(num_hops)
        ]
    )

    # Raw gain needed per hop
    gain_raw = np.ones(num_hops)
    for i in range(num_hops):
        rms = rms_curve[i]
        if rms >= SPEECH_FLOOR:
            needed_db = np.clip(
                20 * np.log10(TARGET_RMS / (rms + 1e-10)), MIN_GAIN_DB, MAX_GAIN_DB
            )
            gain_raw[i] = 10 ** (needed_db / 20)

    # Asymmetric smoothing (attack faster than release)
    gain_smooth = gain_raw.copy()
    for i in range(1, num_hops):
        alpha = (
            1 - np.exp(-1 / ATTACK_SMOOTH)
            if gain_raw[i] < gain_smooth[i - 1]
            else 1 - np.exp(-1 / RELEASE_SMOOTH)
        )
        gain_smooth[i] = gain_smooth[i - 1] + alpha * (gain_raw[i] - gain_smooth[i - 1])

    gain_smooth = uniform_filter1d(gain_smooth, size=5)

    # Apply gain frame by frame
    output = audio.copy()
    for i in range(num_hops):
        s = i * HOP_LEN
        e = min(s + HOP_LEN, len(output))
        output[s:e] *= gain_smooth[i]
    if num_hops * HOP_LEN < len(output):
        output[num_hops * HOP_LEN :] *= gain_smooth[-1]

    # Brick wall limiter — no clipping ever
    peak = np.max(np.abs(output))
    if peak > 0.93:
        output *= 0.93 / peak

    return output


def eq_clarity_boost(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Targeted EQ correction for DeepFilterNet's over-suppression
    of the 800Hz-2kHz clarity band (~10dB loss measured).
    Applies a gentle shelving boost centered at 1.2kHz.
    """
    BOOST_DB = 3.5  # was 5.0 — consonants are already restored by the dry mix; lower
    # boost avoids amplifying residual noise in the 1.2kHz band
    CENTER_HZ = 1200.0
    BANDWIDTH_OCT = 1.5

    # Convert to peak EQ biquad via bilinear transform
    # Using a simple bandpass boost approach
    w0 = 2 * np.pi * CENTER_HZ / sr
    bw = BANDWIDTH_OCT * np.log(2) / 2
    Q = 1 / (2 * np.sinh(bw))

    A = 10 ** (BOOST_DB / 40)
    alpha = np.sin(w0) / (2 * Q)

    b0 = 1 + alpha * A
    b1 = -2 * np.cos(w0)
    b2 = 1 - alpha * A
    a0 = 1 + alpha / A
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha / A

    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0, a1 / a0, a2 / a0])

    boosted = lfilter(b, a, audio)

    # Safety peak limit after EQ (EQ can push peaks up)
    peak = np.max(np.abs(boosted))
    if peak > 0.93:
        boosted *= 0.93 / peak

    return boosted.astype(audio.dtype)


def compute_adaptive_thresholds(audio: np.ndarray, sr: int = 16000) -> dict:
    """
    Computes silence threshold, min segment duration, and merge gap
    dynamically from the audio's own noise floor and speech rhythm.
    Works correctly for any recording — quiet, loud, clean, noisy.
    """
    frame_len = int(sr * 0.025)
    hop_len = int(sr * 0.010)
    n_frames = max(1, (len(audio) - frame_len) // hop_len)

    rms = np.array(
        [
            np.sqrt(np.mean(audio[i * hop_len : i * hop_len + frame_len] ** 2))
            for i in range(n_frames)
        ]
    )

    noise_floor = np.percentile(rms, 5)
    speech_level = np.percentile(rms, 70)
    silence_threshold = noise_floor + (speech_level - noise_floor) * 0.15
    silence_threshold = max(silence_threshold, 1e-4)

    is_speech = (rms > silence_threshold).astype(int)
    transitions = np.diff(is_speech)
    onsets = np.where(transitions == 1)[0]
    offsets = np.where(transitions == -1)[0]

    seg_lengths_ms = []
    for on, off in zip(onsets, offsets):
        if off > on:
            seg_lengths_ms.append((off - on) * hop_len / sr * 1000)

    gaps_ms = []
    for i in range(min(len(offsets), len(onsets) - 1)):
        gap = (onsets[i + 1] - offsets[i]) * hop_len / sr * 1000
        if gap > 0:
            gaps_ms.append(gap)

    if seg_lengths_ms:
        min_seg_ms = float(np.clip(np.percentile(seg_lengths_ms, 25), 80, 250))
    else:
        min_seg_ms = 120.0

    if gaps_ms:
        merge_gap_ms = float(np.clip(np.percentile(gaps_ms, 40), 150, 500))
    else:
        merge_gap_ms = 250.0

    median_seg = np.median(seg_lengths_ms) if seg_lengths_ms else 200.0
    tail_pad_ms = float(np.clip(median_seg * 0.12, 20, 80))

    return {
        "silence_threshold": silence_threshold,
        "min_segment_ms": min_seg_ms,
        "merge_gap_ms": merge_gap_ms,
        "tail_pad_ms": tail_pad_ms,
    }


def apply_pre_processing(audio: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Final peak safety normalization only.
    """

    peak = np.max(np.abs(audio))
    if peak > 0.95:
        audio = audio * (0.95 / peak)

    return audio


try:
    from .media_loader import MediaLoader
    from .vad_processor import VADProcessor
    from .deepfilter_processor import DeepFilterProcessor
    from .diarization import SpeakerDiarization
    from .asr_processor import ASRProcessor
    from .cache_manager import FileCache
except ImportError:
    from media_loader import MediaLoader
    from vad_processor import VADProcessor
    from deepfilter_processor import DeepFilterProcessor
    from diarization import SpeakerDiarization
    from asr_processor import ASRProcessor
    from cache_manager import FileCache


def _load_optional_class(module_name: str, class_name: str):
    """Load an optional DSP class using either package or flat-module imports."""
    module = None
    if __package__:
        try:
            module = __import__(f"{__package__}.{module_name}", fromlist=[class_name])
        except ImportError:
            module = None

    if module is None:
        try:
            module = __import__(module_name, fromlist=[class_name])
        except ImportError as exc:
            logger.warning("Optional module %s unavailable: %s", module_name, exc)
            return None

    return getattr(module, class_name, None)


class LectraAIPipeline:
    """Main pipeline for Lectra AI with your optimized workflow"""

    def __init__(self, config_path: str = "config.yaml", enable_cache: bool = True):
        """
        Initialize pipeline with configuration

        Args:
            config_path: Path to configuration file
            enable_cache: Enable file-based caching for faster repeated processing
        """
        self.config = self._load_config(config_path)
        self.enable_cache = enable_cache

        if self.enable_cache:
            self.cache = FileCache(cache_dir="./cache")
            logger.info("File caching enabled - repeated files will process instantly!")
        else:
            self.cache = None

        self._initialize_components()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            config = self._get_default_config()

        return config

    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            "audio": {"sample_rate": 16000, "chunk_duration": 30},
            "vad": {
                "aggressiveness": 3,
                "frame_duration_ms": 30,
                "padding_duration_ms": 300,
                "min_speech_duration_ms": 250,
            },
            "deepfilternet": {
                "model": "DeepFilterNet3",
                "post_filter": True,
                "atten_lim_db": 30.0,
            },
            "diarization": {"enabled": True, "min_speakers": 1, "max_speakers": 10},
            "asr": {"model": "base", "language": "en", "compute_type": "float16"},
            "output": {"format": "wav", "bit_depth": 16, "preserve_video": True},
        }

    def _initialize_components(self):
        """Initialize all pipeline components"""
        logger.info("Initializing pipeline components...")

        # Audio settings
        self.sample_rate = self.config["audio"]["sample_rate"]
        self.chunk_duration = self.config["audio"]["chunk_duration"]

        # Media loader
        self.media_loader = MediaLoader(target_sr=self.sample_rate)

        # VAD processor
        vad_config = self.config["vad"]
        self.vad_processor = VADProcessor(
            sample_rate=self.sample_rate,
            aggressiveness=vad_config["aggressiveness"],
            frame_duration_ms=vad_config["frame_duration_ms"],
            padding_duration_ms=vad_config["padding_duration_ms"],
            min_speech_duration_ms=vad_config["min_speech_duration_ms"],
        )

        # DeepFilterNet processor
        dfn_config = self.config["deepfilternet"]
        self.deepfilter = DeepFilterProcessor(
            double_pass=False,  # ENHANCEMENT 2: DOUBLE-PASS (controlled in pipeline loop)
            model_name=dfn_config["model"],
            post_filter=dfn_config["post_filter"],
            atten_lim_db=float(dfn_config.get("atten_lim_db", 30.0)),
        )
        # Fraction of the original (pre-DFN) speech blended back after enhancement.
        # Refills the low-energy gaps DeepFilterNet over-suppresses (quiet consonants,
        # syllable transitions, weaker overlapping voice) → no "missing syllables".
        self.dry_wet_mix = float(dfn_config.get("dry_wet_mix", 0.0))
        # High-pass the dry signal before blending so only the mid/high band (where
        # syllables live) is restored — the low-frequency noise/rumble stays removed.
        # 0 disables the HPF (legacy full-band crossfade behaviour).
        self.dry_mix_hpf_hz = float(dfn_config.get("dry_mix_hpf_hz", 0.0))
        # Low-band-only stationary denoise to remove residual low-frequency rumble.
        lbd = self.config.get("low_band_denoise", {})
        self.low_band_denoise_enabled = bool(lbd.get("enabled", False))
        self.low_band_denoise_cutoff_hz = float(lbd.get("cutoff_hz", 700))
        self.low_band_denoise_strength = float(lbd.get("strength", 0.85))

        # Neural enhancer (MetricGAN+) — final neural denoise after DeepFilterNet.
        # Light, faster-than-realtime on CPU, bounded spectral mask (no artifacts).
        self.neural_enhancer = None
        ne_cfg = self.config.get("neural_enhancer", {})
        if ne_cfg.get("enabled", False):
            enhancer_class = _load_optional_class(
                "metricgan_processor", "MetricGANProcessor"
            )
            if enhancer_class is not None:
                try:
                    self.neural_enhancer = enhancer_class(device="cpu")
                    logger.info("Neural enhancer (MetricGAN+) enabled")
                except Exception as e:
                    logger.warning(
                        f"Neural enhancer unavailable, continuing without it: {e}"
                    )
                    self.neural_enhancer = None

        # Voice Beautify — post-cleaning master (tone/leveler/air) on speech only.
        # Runs after all noise removal; makes the clean voice sound smooth/natural
        # instead of "broken-speaker". SNR-guarded so it can't add noise back.
        self.beautifier = None
        if self.config.get("beautify", {}).get("enabled", False):
            beautify_class = _load_optional_class("voice_beautify", "VoiceBeautifier")
            if beautify_class is not None:
                try:
                    self.beautifier = beautify_class(self.config, self.sample_rate)
                    logger.info("Voice Beautify enabled")
                except Exception as e:
                    logger.warning(
                        f"Voice Beautify unavailable, continuing without it: {e}"
                    )
                    self.beautifier = None

        # Diarization (optional)
        if self.config["diarization"]["enabled"]:
            dia_config = self.config["diarization"]
            self.diarization = SpeakerDiarization(
                min_speakers=dia_config["min_speakers"],
                max_speakers=dia_config["max_speakers"],
            )
        else:
            self.diarization = None

        # ASR processor — deferred; backend.py sets pipeline.asr with the user-selected model.
        # If running via CLI (clean_voice.py), it will be lazy-initialised on first call to process().
        self.asr = None

        # Optional DSP modules are initialized lazily inside process() so they
        # only load when the corresponding config flags are enabled.
        self.profiler = None
        self.quality_metrics = None
        self.spectral_restoration = None
        self.adaptive_router = None
        self._custom_modules_initialized = False

        logger.info(
            "All components initialized successfully (ASR will load on first use)"
        )

    def _initialize_custom_modules(self):
        """Initialize optional custom DSP modules"""
        if self._custom_modules_initialized:
            return

        # Audio Quality Profiler
        if self.config.get("profiler", {}).get("enabled", False):
            profiler_class = _load_optional_class(
                "audio_quality_profiler", "AudioQualityProfiler"
            )
            if profiler_class is not None:
                wavelet = self.config["profiler"].get("wavelet", "db8")
                self.profiler = profiler_class(
                    sample_rate=self.sample_rate, wavelet=wavelet
                )
                logger.info("Audio Quality Profiler enabled")
            else:
                self.profiler = None
        else:
            self.profiler = None

        # Quality Metrics
        if self.config.get("quality_metrics", {}).get("enabled", False):
            metrics_class = _load_optional_class(
                "audio_quality_metrics", "AudioQualityMetrics"
            )
            if metrics_class is not None:
                self.quality_metrics = metrics_class(sample_rate=self.sample_rate)
                logger.info("Audio Quality Metrics enabled")
            else:
                self.quality_metrics = None
        else:
            self.quality_metrics = None

        # Spectral Restoration
        if self.config.get("spectral_restoration", {}).get("enabled", False):
            restoration_class = _load_optional_class(
                "spectral_restoration", "SpectralRestoration"
            )
            if restoration_class is not None:
                self.spectral_restoration = restoration_class(
                    sample_rate=self.sample_rate
                )
                logger.info("Spectral Restoration enabled")
            else:
                self.spectral_restoration = None
        else:
            self.spectral_restoration = None

        # Adaptive Router
        if self.config.get("adaptive_router", {}).get("enabled", False):
            router_class = _load_optional_class("adaptive_router", "AdaptiveRouter")
            if router_class is not None:
                self.adaptive_router = router_class(sample_rate=self.sample_rate)
                logger.info("Adaptive Router enabled")
            else:
                self.adaptive_router = None
        else:
            self.adaptive_router = None

        self._custom_modules_initialized = True

    def _merge_segments(
        self,
        segments: List[Tuple[int, int]],
        max_length: int,
        max_gap_samples: int = 0,
    ) -> List[Tuple[int, int]]:
        """Merge overlapping or nearby sample segments and clip to valid audio bounds."""
        normalized = []
        for start, end in segments:
            start = max(0, int(start))
            end = min(max_length, int(end))
            if end > start:
                normalized.append((start, end))

        if not normalized:
            return []

        normalized.sort(key=lambda item: item[0])
        merged = [normalized[0]]

        for start, end in normalized[1:]:
            prev_start, prev_end = merged[-1]
            if start <= prev_end + max_gap_samples:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

        return merged

    def process(
        self,
        input_path: str,
        output_dir: str = "outputs",
        save_transcript: bool = True,
        transcript_format: str = "txt",
    ) -> Dict[str, Any]:
        """
        Process audio/video file through the complete pipeline

        Pipeline: Pre-VAD trim -> DeepFilterNet speech chunks ->
                  silent-bed transplant with 20ms fades ->
                  diarize first -> ASR per-speaker segment (or full-pass if no diarization)

        Args:
            input_path: Path to input audio/video file
            output_dir: Directory for output files
            save_transcript: Whether to save transcript
            transcript_format: Transcript format (txt, json, srt, vtt)

        Returns:
            Dictionary with results and output paths
        """
        start_time = time.time()

        # Check cache first
        if self.enable_cache and self.cache:
            cached = self.cache.get(input_path, self.config)
            if cached:
                logger.info("✅ CACHE HIT! Returning cached result instantly")
                elapsed = time.time() - start_time

                # Copy cached file to output directory
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)

                input_name = Path(input_path).stem
                output_audio = output_dir / f"{input_name}_cleaned.wav"

                import shutil

                shutil.copy2(cached["audio_path"], output_audio)

                cached_result = cached["metadata"].get("result", {})
                return {
                    "input_path": input_path,
                    "is_video": cached_result.get("is_video", False),
                    "audio_output_path": str(output_audio),
                    "video_output_path": cached_result.get("video_output_path"),
                    "transcript": cached_result.get("transcript", {}),
                    "diarization": cached_result.get("diarization", []),
                    "duration_original": cached_result.get("duration_original", 0.0),
                    "duration_processed": cached_result.get("duration_processed", 0.0),
                    "speech_segments": cached_result.get("speech_segments", 0),
                    "processing_time": elapsed,
                    "from_cache": True,
                }
        logger.info(f"Starting Lectra AI pipeline for: {input_path}")
        logger.info("=" * 70)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_name = Path(input_path).stem

        # STEP 1: Load media
        logger.info("STEP 1: Loading media")
        audio, sr, is_video = self.media_loader.load_media(input_path)
        logger.info(
            f"Loaded {len(audio)/sr:.2f}s from {'video' if is_video else 'audio'}"
        )

        thresholds = compute_adaptive_thresholds(audio, sr=sr)
        logger.info(
            f"[adaptive] silence_threshold={thresholds['silence_threshold']:.5f}"
        )
        logger.info(
            f"[adaptive] min_seg={thresholds['min_segment_ms']:.0f}ms  "
            f"merge_gap={thresholds['merge_gap_ms']:.0f}ms  "
            f"tail_pad={thresholds['tail_pad_ms']:.0f}ms"
        )
        self.vad_processor.silence_threshold = thresholds["silence_threshold"]
        self.vad_processor.min_speech_duration_ms = int(thresholds["min_segment_ms"])
        self.vad_processor.min_speech_frames = max(
            1,
            int(
                np.ceil(
                    thresholds["min_segment_ms"] / self.vad_processor.frame_duration_ms
                )
            ),
        )

        # Initialize optional custom DSP modules only when a file is actually processed.
        self._initialize_custom_modules()

        # STEP 1.5: Audio Quality Profiling (optional)
        audio_profile = None
        if self.profiler is not None:
            logger.info("\nSTEP 1.5: Audio Quality Profiling")
            try:
                audio_profile = self.profiler.profile_audio(audio, sr)
                logger.info(self.profiler.format_profile(audio_profile))
            except Exception as e:
                logger.warning(f"Profiling failed: {e}, continuing without profile")

        # STEP 2: Diarize — find who speaks when
        logger.info("\nSTEP 2: Diarizing — finding speaker segments")
        import soundfile as sf

        temp_audio_path = output_dir / f"{input_name}_temp.wav"
        sf.write(str(temp_audio_path), audio, sr)

        diarization_results = []
        if self.diarization is not None:
            try:
                diarization_results = self.diarization.diarize(str(temp_audio_path))
                if diarization_results:
                    stats = self.diarization.get_speaker_statistics(diarization_results)
                    logger.info(
                        f"Identified {len(stats)} speaker(s), {len(diarization_results)} segments"
                    )
            except Exception as e:
                logger.warning(f"Diarization failed, falling back to VAD: {e}")

        # Build speech segments from diarization; fall back to VAD if unavailable
        if diarization_results:
            speech_segments = []
            for seg in diarization_results:
                start_i = int(seg["start"] * sr)
                end_i = min(int(seg["end"] * sr), len(audio))
                if end_i > start_i:
                    speech_segments.append((start_i, end_i))
            speech_segments = self._merge_segments(
                speech_segments,
                len(audio),
                max_gap_samples=int(thresholds["merge_gap_ms"] / 1000 * sr),
            )
        else:
            logger.info("No diarization — using VAD for speech boundaries")
            _, speech_segments = self.vad_processor.trim_silence(audio)

        # ENHANCEMENT 3: VAD-FILTER (Tighten Minimum Segment Duration)
        min_segment_ms = thresholds["min_segment_ms"]
        min_segment_samples = int(min_segment_ms / 1000 * sr)
        filtered_segments = []
        dropped_count = 0
        for start, end in speech_segments:
            if end - start >= min_segment_samples:
                filtered_segments.append((start, end))
            else:
                dropped_count += 1
        speech_segments = filtered_segments
        if dropped_count > 0:
            logger.info(
                f"Dropped {dropped_count} segments as sub-threshold noise transients (<{min_segment_ms}ms)"
            )

        tail_pad_samples = int(thresholds["tail_pad_ms"] / 1000 * sr)
        padded_segments = []
        for start, end in speech_segments:
            padded_end = min(end + tail_pad_samples, len(audio))
            if padded_end > start:
                padded_segments.append((start, padded_end))
        speech_segments = self._merge_segments(
            padded_segments,
            len(audio),
            max_gap_samples=int(thresholds["merge_gap_ms"] / 1000 * sr),
        )

        logger.info(f"{len(speech_segments)} speech segment(s) to process")

        # STEP 3: Place speech on a zero-background (pure silence) track
        # This eliminates ALL background noise between words and speakers.
        logger.info("\nSTEP 3: Placing speech on silent background")
        clean_base = np.zeros(len(audio), dtype=np.float32)

        # ENHANCEMENT 1: HPF (High-Pass Filter PRE-DeepFilterNet)
        hpf_config = self.config.get("high_pass_filter", {})
        hpf_enabled = hpf_config.get("enabled", False)
        hpf_cutoff = hpf_config.get("cutoff_hz", 120)

        sos = None
        if hpf_enabled:
            import scipy.signal as signal

            cutoff = min(hpf_cutoff, 150)  # Constraint: Do not exceed 150 Hz
            sos = signal.butter(4, cutoff, btype="highpass", output="sos", fs=sr)
            logger.info(
                f"Applying 4th-order Butterworth HPF at {cutoff}Hz to speech segments"
            )

        for start, end in speech_segments:
            seg_audio = audio[start:end]
            if sos is not None:
                seg_audio = signal.sosfilt(sos, seg_audio)
            clean_base[start:end] = seg_audio

        # STEP 3.5: Adaptive Router (optional) - try lighter methods first
        use_deepfilter = True
        router_method = None
        if self.adaptive_router is not None and audio_profile is not None:
            logger.info("\nSTEP 3.5: Adaptive Router - selecting processing method")
            try:
                routed_audio, router_method = self.adaptive_router.route_processing(
                    clean_base, audio_profile, self.config
                )

                if router_method != "deepfilternet_required":
                    # Router handled the processing
                    logger.info(
                        f"Router used: {self.adaptive_router.get_method_description(router_method)}"
                    )
                    enhanced_audio = routed_audio
                    use_deepfilter = False
                else:
                    logger.info("Router recommends DeepFilterNet for heavy noise")
            except Exception as e:
                logger.warning(
                    f"Adaptive router failed: {e}, falling back to DeepFilterNet"
                )
                if self.config.get("adaptive_router", {}).get(
                    "fallback_to_deepfilter", True
                ):
                    use_deepfilter = True

        # STEP 4: Full-file DeepFilterNet noise removal
        if use_deepfilter:
            logger.info("\nSTEP 4: Full-file DeepFilterNet noise removal")

            import librosa as _lib

            df_sr = self.deepfilter.sample_rate  # 48000
            logger.info("[pipeline] DeepFilterNet mode: full-file")
            logger.info("[pipeline] second pass: disabled")
            logger.info(f"[pipeline] atten_lim_db: {self.deepfilter.atten_lim_db}")

            df_factor = df_sr / sr
            clean_df_in = (
                _lib.resample(clean_base, orig_sr=sr, target_sr=df_sr)
                if sr != df_sr
                else clean_base.copy()
            )

            n_df = int(np.ceil(len(clean_base) * df_factor))
            chunk_samples = int(30.0 * df_sr)
            overlap_samples = int(2.0 * df_sr)

            if len(clean_df_in) <= chunk_samples:
                enhanced_df = self.deepfilter.process_audio_native(clean_df_in)
            else:
                logger.info(
                    "  DeepFilterNet chunk fallback: 30s chunks with 2s overlap"
                )
                enhanced_df = np.zeros(len(clean_df_in), dtype=np.float32)
                blend_weights = np.zeros(len(clean_df_in), dtype=np.float32)
                step_samples = max(1, chunk_samples - 2 * overlap_samples)
                chunk_starts = list(range(0, len(clean_df_in), step_samples))
                final_start = max(0, len(clean_df_in) - chunk_samples)
                if chunk_starts[-1] != final_start:
                    chunk_starts.append(final_start)
                chunk_starts = sorted(set(chunk_starts))

                for i, chunk_start in enumerate(chunk_starts):
                    chunk_end = min(len(clean_df_in), chunk_start + chunk_samples)
                    chunk = clean_df_in[chunk_start:chunk_end]
                    chunk_enhanced = self.deepfilter.process_audio_native(chunk)

                    left_fade = overlap_samples if chunk_start > 0 else 0
                    right_fade = overlap_samples if chunk_end < len(clean_df_in) else 0

                    usable_start = chunk_start + left_fade
                    usable_end = chunk_end - right_fade
                    usable = chunk_enhanced[
                        left_fade : (
                            len(chunk_enhanced) - right_fade if right_fade > 0 else None
                        )
                    ]

                    if len(usable) == 0:
                        continue

                    window = np.ones(len(usable), dtype=np.float32)
                    if left_fade > 0:
                        window[:left_fade] = np.linspace(
                            0.0, 1.0, left_fade, endpoint=False, dtype=np.float32
                        )
                    if right_fade > 0:
                        window[-right_fade:] = np.minimum(
                            window[-right_fade:],
                            np.linspace(
                                1.0, 0.0, right_fade, endpoint=False, dtype=np.float32
                            ),
                        )

                    enhanced_df[usable_start:usable_end] += usable * window
                    blend_weights[usable_start:usable_end] += window

                    if (i + 1) % 5 == 0 or (i + 1) == len(chunk_starts):
                        logger.info(f"  Chunk {i+1}/{len(chunk_starts)} done")

                nonzero = blend_weights > 0
                enhanced_df[nonzero] /= blend_weights[nonzero]

            if len(enhanced_df) < n_df:
                enhanced_df = np.pad(enhanced_df, (0, n_df - len(enhanced_df)))
            elif len(enhanced_df) > n_df:
                enhanced_df = enhanced_df[:n_df]

            if df_sr != sr:
                enhanced_audio = _lib.resample(enhanced_df, orig_sr=df_sr, target_sr=sr)
            else:
                enhanced_audio = enhanced_df

            enhanced_audio = enhanced_audio[: len(clean_base)].astype(np.float32)
            if len(enhanced_audio) < len(clean_base):
                enhanced_audio = np.pad(
                    enhanced_audio, (0, len(clean_base) - len(enhanced_audio))
                )

            # STEP 4b: Neural enhancer (MetricGAN+) — final neural denoise pass.
            # DeepFilterNet removes the bulk; MetricGAN+ polishes the residual down
            # toward inaudible (~40 dB speech-to-noise) without artifacts.
            if self.neural_enhancer is not None:
                try:
                    logger.info("\nSTEP 4b: Neural enhancement (MetricGAN+)")
                    enhanced_audio = self.neural_enhancer.enhance(
                        enhanced_audio
                    ).astype(np.float32)
                    if len(enhanced_audio) < len(clean_base):
                        enhanced_audio = np.pad(
                            enhanced_audio, (0, len(clean_base) - len(enhanced_audio))
                        )
                    enhanced_audio = enhanced_audio[: len(clean_base)]
                    logger.info("[pipeline] MetricGAN+ enhancement applied")
                except Exception as e:
                    logger.warning(f"Neural enhancement failed, using DFN output: {e}")

            # Dry/wet blend: add a little of the original speech back so the
            # quiet consonants/syllables DeepFilterNet gates out are restored.
            # clean_base is zero outside speech segments, so no noise leaks into gaps.
            if self.dry_wet_mix > 0.0:
                dry = float(np.clip(self.dry_wet_mix, 0.0, 1.0))
                if self.dry_mix_hpf_hz > 0.0:
                    # Band-limited dry: high-pass so only mid/high (syllables) is added
                    # back; low-frequency rumble stays suppressed. Additive — the dry
                    # band is the high content DFN removed, not a level crossfade.
                    import scipy.signal as _sig

                    cutoff = float(np.clip(self.dry_mix_hpf_hz, 50.0, sr / 2 - 100))
                    _sos = _sig.butter(4, cutoff, btype="highpass", output="sos", fs=sr)
                    dry_band = _sig.sosfilt(_sos, clean_base).astype(np.float32)
                    enhanced_audio = (enhanced_audio + dry * dry_band).astype(
                        np.float32
                    )
                    logger.info(
                        f"[pipeline] dry mix applied: +{dry:.0%} original above {cutoff:.0f}Hz"
                    )
                else:
                    enhanced_audio = (
                        (1.0 - dry) * enhanced_audio + dry * clean_base
                    ).astype(np.float32)
                    logger.info(
                        f"[pipeline] dry/wet mix applied: {dry:.0%} original blended back"
                    )

            # Low-band-only denoise: kills the residual stationary low-frequency
            # rumble without touching consonants. noisereduce is applied with the
            # ACTUAL noise profile (a silent gap of the original), then only the
            # low band of that result is kept; the high band (consonants) is left
            # completely untouched. This is the surgical version of noisereduce —
            # broadband NR would gate syllables; band-limiting it does not.
            if self.low_band_denoise_enabled:
                try:
                    import noisereduce as _nr
                    import scipy.signal as _sig2

                    # Noise profile: lowest-energy 0.5s window of the original audio.
                    win = int(0.5 * sr)
                    if len(audio) > win:
                        step = max(1, win // 2)
                        starts = range(0, len(audio) - win, step)
                        idx = min(
                            starts,
                            key=lambda i: float(np.mean(audio[i : i + win] ** 2)),
                        )
                        noise_clip = audio[idx : idx + win].astype(np.float32)

                        denoised = _nr.reduce_noise(
                            y=enhanced_audio,
                            sr=sr,
                            y_noise=noise_clip,
                            stationary=True,
                            prop_decrease=self.low_band_denoise_strength,
                        ).astype(np.float32)

                        cut = float(
                            np.clip(self.low_band_denoise_cutoff_hz, 200.0, 2000.0)
                        )
                        lo = _sig2.butter(4, cut, btype="lowpass", output="sos", fs=sr)
                        hi = _sig2.butter(4, cut, btype="highpass", output="sos", fs=sr)
                        enhanced_audio = (
                            _sig2.sosfilt(lo, denoised)
                            + _sig2.sosfilt(hi, enhanced_audio)
                        ).astype(np.float32)
                        logger.info(
                            f"[pipeline] low-band denoise applied below {cut:.0f}Hz "
                            f"(strength {self.low_band_denoise_strength:.2f}) — rumble removed, consonants untouched"
                        )
                except Exception as e:
                    logger.warning(f"Low-band denoise skipped: {e}")

        # STEP 4.5: Spectral Restoration (optional)
        if self.spectral_restoration is not None:
            logger.info("\nSTEP 4.5: Spectral Restoration")
            try:
                strength = self.config.get("spectral_restoration", {}).get(
                    "strength", "auto"
                )
                enhanced_audio = self.spectral_restoration.adaptive_restoration(
                    audio, enhanced_audio, strength=strength
                )
                logger.info("Spectral restoration applied")
            except Exception as e:
                logger.warning(
                    f"Spectral restoration failed: {e}, using unrestored audio"
                )

        # STEP 5: Re-apply zero outside speech so DeepFilterNet output bleed is gone
        # Apply 10ms cosine fades at segment edges to avoid clicks.
        logger.info("\nSTEP 5: Re-masking — zeroing outside speech segments")
        fade_samples = int(0.010 * sr)
        final_audio = np.zeros(len(enhanced_audio), dtype=np.float32)
        for start, end in speech_segments:
            seg = enhanced_audio[start:end].copy()
            seg_len = end - start
            if seg_len > 2 * fade_samples:
                fade_in = 0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_samples)))
                seg[:fade_samples] *= fade_in
                fade_out = 0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_samples)))
                seg[-fade_samples:] *= fade_out
            final_audio[start:end] = seg

        # Adaptive gain riding replaces static peak normalization
        audio_before_gain = final_audio.copy()
        final_audio = adaptive_gain_ride(final_audio, sr=sr).astype(np.float32)
        final_audio = eq_clarity_boost(final_audio, sr=sr).astype(np.float32)

        # Final loudness normalization — keeps output at a consistent level no matter
        # how much energy the denoising/rumble-removal stripped out (prevents "dim"
        # output). Measured over speech-active samples only (zeros are excluded), then
        # brick-wall limited so peaks never clip.
        TARGET_RMS_DBFS = -20.0
        active_samples = final_audio[np.abs(final_audio) > 1e-4]
        if active_samples.size > 0:
            cur_rms = float(np.sqrt(np.mean(active_samples**2)))
            if cur_rms > 1e-6:
                makeup = (10 ** (TARGET_RMS_DBFS / 20)) / cur_rms
                makeup = float(np.clip(makeup, 0.25, 8.0))
                final_audio = (final_audio * makeup).astype(np.float32)
        peak = float(np.max(np.abs(final_audio))) if final_audio.size else 0.0
        if peak > 0.97:
            final_audio = (final_audio * (0.97 / peak)).astype(np.float32)
        audio_after_gain = final_audio
        logger.info(
            f"[gain_rider] input RMS: {20*np.log10(np.sqrt(np.mean(audio_before_gain**2))+1e-10):.1f} dBFS"
        )
        logger.info(
            f"[loudness] output RMS: {20*np.log10(np.sqrt(np.mean(audio_after_gain**2))+1e-10):.1f} dBFS "
            f"(target {TARGET_RMS_DBFS:.0f}), peak {20*np.log10(peak+1e-10):.1f} dBFS"
        )

        # STEP 5.5: Voice Beautify (post-cleaning master on speech segments only)
        out_sr = sr
        if self.beautifier is not None:
            logger.info("\nSTEP 5.5: Voice Beautify (tone / leveler / air)")
            try:
                final_audio, out_sr = self.beautifier.process(
                    final_audio, speech_segments
                )
                final_audio = final_audio.astype(np.float32)
            except Exception as e:
                logger.warning(f"Voice Beautify failed, using un-beautified audio: {e}")
                out_sr = sr

        # STEP 6: Save cleaned audio
        logger.info("\nSTEP 6: Saving cleaned audio")
        output_format = self.config["output"]["format"]
        bit_depth = self.config["output"]["bit_depth"]
        audio_output_path = output_dir / f"{input_name}_cleaned.{output_format}"
        self.media_loader.save_audio(
            final_audio,
            out_sr,
            str(audio_output_path),
            format=output_format,
            bit_depth=bit_depth,
        )

        # Clean up temp file
        if temp_audio_path.exists():
            temp_audio_path.unlink()

        # STEP 7: Automatic speech recognition
        logger.info("\nSTEP 8: Automatic speech recognition")
        transcript = {"text": "", "segments": []}

        if self.config["asr"].get("skip", False):
            logger.info(
                "ASR skipped (asr.skip=true in config.yaml — set false to enable)"
            )
        else:
            # Lazy-init ASR if not already set (CLI / non-backend usage)
            if self.asr is None:
                asr_config = self.config["asr"]
                logger.info(
                    f"Lazy-initialising ASR with model '{asr_config['model']}' from config"
                )
                self.asr = ASRProcessor(
                    model_size=asr_config["model"],
                    language=asr_config.get("language"),
                    compute_type=asr_config["compute_type"],
                )

            if diarization_results:
                # Best practice: transcribe each speaker slice separately so Whisper
                # sees clean, single-speaker audio — no cross-talk confusion.
                logger.info("Transcribing per speaker segment (diarization-guided)")
                import soundfile as sf
                import tempfile, shutil as _shutil

                full_audio_arr, full_sr = sf.read(str(audio_output_path))
                combined_segments = []
                full_text_parts = []

                for seg in diarization_results:
                    start_s = seg.get("start", 0)
                    end_s = seg.get("end", 0)
                    speaker = seg.get("speaker", "SPEAKER_00")

                    start_i = int(start_s * full_sr)
                    end_i = min(int(end_s * full_sr), len(full_audio_arr))
                    slice_audio = full_audio_arr[start_i:end_i]

                    if len(slice_audio) < full_sr * 0.2:  # skip < 200 ms clips
                        continue

                    with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False
                    ) as tmp:
                        tmp_path = tmp.name
                    try:
                        sf.write(tmp_path, slice_audio, full_sr)
                        seg_transcript = self.asr.transcribe(tmp_path)
                        seg_text = seg_transcript.get("text", "").strip()
                    finally:
                        try:
                            os.remove(tmp_path)
                        except Exception:
                            pass

                    if seg_text:
                        combined_segments.append(
                            {
                                "start": round(start_s, 2),
                                "end": round(end_s, 2),
                                "speaker": speaker,
                                "text": seg_text,
                            }
                        )
                        full_text_parts.append(f"[{speaker}] {seg_text}")

                transcript = {
                    "text": "\n".join(full_text_parts),
                    "segments": combined_segments,
                }
                logger.info(f"Transcribed {len(combined_segments)} speaker segments")
            else:
                # No diarization available — single-pass full-audio transcription
                logger.info("No diarization — transcribing full audio in one pass")
                transcript = self.asr.transcribe(str(audio_output_path))
                logger.info(
                    f"Transcribed: {len(transcript.get('text', ''))} characters"
                )

            # Save transcript
            if save_transcript:
                transcript_path = (
                    output_dir / f"{input_name}_transcript.{transcript_format}"
                )
                self.asr.save_transcript(
                    transcript,
                    str(transcript_path),
                    format=transcript_format,
                    diarization=diarization_results,
                )
                logger.info(f"Transcript saved to: {transcript_path}")

        # Step 9: Merge back to video if needed
        video_output_path = None
        if is_video and self.config["output"]["preserve_video"]:
            logger.info("\nSTEP 9: Merging cleaned audio back to video")
            video_output_path = output_dir / f"{input_name}_cleaned.mp4"
            try:
                self.media_loader.merge_audio_to_video(
                    input_path, str(audio_output_path), str(video_output_path)
                )
            except Exception as e:
                logger.error(f"Video merging failed: {e}")

        logger.info("\n" + "=" * 70)
        logger.info("Pipeline completed successfully!")

        elapsed_time = time.time() - start_time

        # STEP 10: Quality Metrics (optional)
        quality_metrics_results = None
        if self.quality_metrics is not None:
            logger.info("\nSTEP 10: Computing Quality Metrics")
            try:
                quality_metrics_results = self.quality_metrics.comprehensive_evaluation(
                    audio, final_audio, sr
                )
                logger.info(
                    self.quality_metrics.format_results(quality_metrics_results)
                )
            except Exception as e:
                logger.warning(f"Quality metrics computation failed: {e}")

        # Return results
        results = {
            "input_path": input_path,
            "is_video": is_video,
            "audio_output_path": str(audio_output_path),
            "video_output_path": str(video_output_path) if video_output_path else None,
            "transcript": transcript,
            "diarization": diarization_results,
            "duration_original": len(audio) / sr,
            "duration_processed": len(final_audio) / out_sr,
            "speech_segments": len(speech_segments),
            "processing_time": elapsed_time,
            "from_cache": False,
        }

        # Add optional custom DSP results
        if audio_profile is not None:
            results["audio_profile"] = audio_profile
        if router_method is not None:
            results["processing_method"] = router_method
        if quality_metrics_results is not None:
            results["quality_metrics"] = quality_metrics_results

        # Cache the results for next time
        if self.enable_cache and self.cache:
            try:
                transcript_path = None
                if save_transcript:
                    transcript_path = str(
                        output_dir / f"{input_name}_transcript.{transcript_format}"
                    )

                self.cache.set(
                    input_path,
                    self.config,
                    results,
                    str(audio_output_path),
                    transcript_path,
                )
                logger.info("✅ Results cached for faster future processing")
            except Exception as e:
                logger.warning(f"Failed to cache results: {e}")

        return results

    def process_batch(
        self,
        input_files: list,
        output_dir: str = "outputs",
        continue_on_error: bool = True,
    ):
        """
        Process multiple files in batch

        Args:
            input_files: List of input file paths
            output_dir: Output directory
            continue_on_error: Continue processing if one file fails
        """
        results = []
        failed = []

        for i, input_file in enumerate(input_files, 1):
            logger.info(f"\n{'='*70}")
            logger.info(f"Processing file {i}/{len(input_files)}: {input_file}")
            logger.info(f"{'='*70}")

            try:
                result = self.process(input_file, output_dir)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {input_file}: {e}")
                failed.append((input_file, str(e)))
                if not continue_on_error:
                    raise

        logger.info(f"\n{'='*70}")
        logger.info(f"Batch processing complete!")
        logger.info(f"Successfully processed: {len(results)}/{len(input_files)}")
        if failed:
            logger.info(f"Failed files: {len(failed)}")
            for file, error in failed:
                logger.info(f"  - {file}: {error}")
        logger.info(f"{'='*70}")

        return results, failed
