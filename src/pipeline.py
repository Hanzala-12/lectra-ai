"""
Main Voice Cleaning Pipeline
Orchestrates the complete processing workflow
"""

import os
import time
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
import numpy as np

from media_loader import MediaLoader
from vad_processor import VADProcessor
from deepfilter_processor import DeepFilterProcessor
from silent_bed import SilentBedTransplant
from diarization import SpeakerDiarization
from asr_processor import ASRProcessor
from cache_manager import FileCache
from audio_quality_profiler import AudioQualityProfiler
from adaptive_router import AdaptiveRouter
from spectral_restoration import SpectralRestoration
from scipy.signal import butter, sosfiltfilt

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VoiceCleaningPipeline:
    """Main pipeline for voice cleaning with your optimized workflow"""

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
            "deepfilternet": {"model": "DeepFilterNet3", "post_filter": True},
            "silent_bed": {"fade_duration_ms": 20, "preserve_original_silence": True},
            "adaptive_processing": {"enabled": True},
            "restoration": {"enabled": True, "heavy_only": True},
            "speech_blend": {"background_gain": 0.06, "energy_threshold": 0.015},
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
            double_pass=dfn_config.get("double_pass", False),
            model_name=dfn_config["model"],
            post_filter=dfn_config["post_filter"],
        )

        # Silent bed transplant
        sb_config = self.config["silent_bed"]
        self.silent_bed = SilentBedTransplant(
            fade_duration_ms=sb_config["fade_duration_ms"], sample_rate=self.sample_rate
        )
        self.profiler = AudioQualityProfiler(sample_rate=self.sample_rate)
        self.router = AdaptiveRouter(sample_rate=self.sample_rate)
        self.restorer = SpectralRestoration(sample_rate=self.sample_rate)

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

        logger.info(
            "All components initialized successfully (ASR will load on first use)"
        )

    def _merge_segments(
        self, segments: List[Tuple[int, int]], max_length: int
    ) -> List[Tuple[int, int]]:
        """Merge overlapping sample segments and clip to valid audio bounds."""
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
            if start <= prev_end:
                merged[-1] = (prev_start, max(prev_end, end))
            else:
                merged.append((start, end))

        return merged

    def _build_processing_segments(
        self,
        speech_segments: List[Tuple[int, int]],
        diarization_results: List[Dict[str, Any]],
        sr: int,
        audio_length: int,
    ) -> List[Tuple[int, int]]:
        """Combine VAD and diarization spans into a single speech mask."""
        segments: List[Tuple[int, int]] = list(speech_segments)

        for seg in diarization_results:
            start_sample = int(seg.get("start", 0.0) * sr)
            end_sample = int(seg.get("end", 0.0) * sr)
            if end_sample > start_sample:
                segments.append((start_sample, end_sample))

        if not segments:
            segments = [(0, audio_length)]

        return self._merge_segments(segments, audio_length)

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
        logger.info(f"Starting voice cleaning pipeline for: {input_path}")
        logger.info("=" * 70)

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        input_name = Path(input_path).stem

        # STEP 1: Load media
        logger.info("STEP 1: Loading media")
        audio, sr, is_video = self.media_loader.load_media(input_path)
        logger.info(f"Loaded {len(audio)/sr:.2f}s from {'video' if is_video else 'audio'}")

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
                    logger.info(f"Identified {len(stats)} speaker(s), {len(diarization_results)} segments")
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
            speech_segments = self._merge_segments(speech_segments, len(audio))
        else:
            logger.info("No diarization — using VAD for speech boundaries")
            _, speech_segments = self.vad_processor.trim_silence(audio)

        logger.info(f"{len(speech_segments)} speech segment(s) to process")

        # STEP 3: Place speech on a zero-background (pure silence) track
        # This eliminates ALL background noise between words and speakers.
        logger.info("\nSTEP 3: Placing speech on silent background")
        clean_base = np.zeros(len(audio), dtype=np.float32)
        for start, end in speech_segments:
            clean_base[start:end] = audio[start:end]

        # STEP 4: DeepFilterNet — remove remaining noise inside speech segments
        logger.info("\nSTEP 4: DeepFilterNet noise removal on speech")
        enhanced_audio = self.deepfilter.process_audio(clean_base, sr)

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

        # Normalize to -0.5 dBFS
        max_val = np.abs(final_audio).max()
        if max_val > 0:
            final_audio = (final_audio / max_val * 0.95).astype(np.float32)

        # STEP 6: Save cleaned audio
        logger.info("\nSTEP 6: Saving cleaned audio")
        output_format = self.config["output"]["format"]
        bit_depth = self.config["output"]["bit_depth"]
        audio_output_path = output_dir / f"{input_name}_cleaned.{output_format}"
        self.media_loader.save_audio(
            final_audio, sr, str(audio_output_path),
            format=output_format, bit_depth=bit_depth,
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

        # Return results
        results = {
            "input_path": input_path,
            "is_video": is_video,
            "audio_output_path": str(audio_output_path),
            "video_output_path": str(video_output_path) if video_output_path else None,
            "transcript": transcript,
            "diarization": diarization_results,
            "duration_original": len(audio) / sr,
            "duration_processed": len(final_audio) / sr,
            "speech_segments": len(speech_segments),
            "processing_time": elapsed_time,
            "from_cache": False,
        }

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

    @staticmethod
    def _invert_segments(
        speech_segments: List[Tuple[int, int]], total_length: int
    ) -> List[Tuple[int, int]]:
        """Return the gaps (non-speech) between speech segments."""
        gaps: List[Tuple[int, int]] = []
        prev_end = 0
        for start, end in sorted(speech_segments):
            if start > prev_end:
                gaps.append((prev_end, start))
            prev_end = max(prev_end, end)
        if prev_end < total_length:
            gaps.append((prev_end, total_length))
        return gaps

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
