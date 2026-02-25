"""
Main Voice Cleaning Pipeline
Orchestrates the complete processing workflow
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

from media_loader import MediaLoader
from vad_processor import VADProcessor
from deepfilter_processor import DeepFilterProcessor
from silent_bed import SilentBedTransplant
from diarization import SpeakerDiarization
from asr_processor import ASRProcessor
from cache_manager import FileCache

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
        else:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            config = self._get_default_config()
        
        return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return default configuration"""
        return {
            'audio': {'sample_rate': 16000, 'chunk_duration': 30},
            'vad': {
                'aggressiveness': 3,
                'frame_duration_ms': 30,
                'padding_duration_ms': 300,
                'min_speech_duration_ms': 250
            },
            'deepfilternet': {
                'model': 'DeepFilterNet3',
                'post_filter': True
            },
            'silent_bed': {
                'fade_duration_ms': 20,
                'preserve_original_silence': True
            },
            'diarization': {
                'enabled': True,
                'min_speakers': 1,
                'max_speakers': 10
            },
            'asr': {
                'model': 'base',
                'language': 'en',
                'compute_type': 'float16'
            },
            'output': {
                'format': 'wav',
                'bit_depth': 16,
                'preserve_video': True
            }
        }
    
    def _initialize_components(self):
        """Initialize all pipeline components"""
        logger.info("Initializing pipeline components...")
        
        # Audio settings
        self.sample_rate = self.config['audio']['sample_rate']
        self.chunk_duration = self.config['audio']['chunk_duration']
        
        # Media loader
        self.media_loader = MediaLoader(target_sr=self.sample_rate)
        
        # VAD processor
        vad_config = self.config['vad']
        self.vad_processor = VADProcessor(
            sample_rate=self.sample_rate,
            aggressiveness=vad_config['aggressiveness'],
            frame_duration_ms=vad_config['frame_duration_ms'],
            padding_duration_ms=vad_config['padding_duration_ms'],
            min_speech_duration_ms=vad_config['min_speech_duration_ms']
        )
        
        # DeepFilterNet processor
        dfn_config = self.config['deepfilternet']
        self.deepfilter = DeepFilterProcessor(
            model_name=dfn_config['model'],
            post_filter=dfn_config['post_filter']
        )
        
        # Silent bed transplant
        sb_config = self.config['silent_bed']
        self.silent_bed = SilentBedTransplant(
            fade_duration_ms=sb_config['fade_duration_ms'],
            sample_rate=self.sample_rate
        )
        
        # Diarization (optional)
        if self.config['diarization']['enabled']:
            dia_config = self.config['diarization']
            self.diarization = SpeakerDiarization(
                min_speakers=dia_config['min_speakers'],
                max_speakers=dia_config['max_speakers']
            )
        else:
            self.diarization = None
        
        # ASR processor
        asr_config = self.config['asr']
        self.asr = ASRProcessor(
            model_size=asr_config['model'],
            language=asr_config.get('language'),
            compute_type=asr_config['compute_type']
        )
        
        logger.info("All components initialized successfully")
    
    def process(self, 
                input_path: str,
                output_dir: str = "outputs",
                save_transcript: bool = True,
                transcript_format: str = "txt") -> Dict[str, Any]:
        """
        Process audio/video file through the complete pipeline
        
        Pipeline: Pre-VAD trim -> DeepFilterNet speech chunks -> 
                  silent-bed transplant with 20ms fades -> 
                  diarization + raw-ASR branch
        import time
        start_time = time.time()
        
        logger.info(f"Starting voice cleaning pipeline for: {input_path}")
        logger.info("=" * 70)
        
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
                shutil.copy2(cached['audio_path'], output_audio)
                
                return {
                    'audio_output_path': output_audio,
                    'transcript': cached['metadata'].get('result', {}).get('transcript', {}),
                    'processing_time': elapsed,
                    'from_cache': True
                }
            input_path: Path to input audio/video file
            output_dir: Directory for output files
            save_transcript: Whether to save transcript
            transcript_format: Transcript format (txt, json, srt, vtt)
            
        Returns:
            Dictionary with results and output paths
        """
        logger.info(f"Starting voice cleaning pipeline for: {input_path}")
        logger.info("=" * 70)
        
        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        input_name = Path(input_path).stem
        
        # Step 1: Load media
        logger.info("STEP 1: Loading media and extracting audio")
        audio, sr, is_video = self.media_loader.load_media(input_path)
        logger.info(f"Loaded: {len(audio)/sr:.2f}s audio from {'video' if is_video else 'audio'}")
        
        # Step 2: Pre-VAD trim
        logger.info("\nSTEP 2: Pre-VAD trim (removing silence at edges)")
        trimmed_audio, speech_segments = self.vad_processor.trim_silence(audio)
        logger.info(f"Trimmed to {len(trimmed_audio)/sr:.2f}s with {len(speech_segments)} speech segments")
        
        # Step 3: DeepFilterNet on speech chunks
        logger.info("\nSTEP 3: DeepFilterNet processing on speech chunks")
        if len(speech_segments) > 0:
            enhanced_audio = self.deepfilter.process_segments(
                trimmed_audio, 
                sr, 
                speech_segments
            )
        else:
            logger.warning("No speech segments detected, processing full audio")
            enhanced_audio = self.deepfilter.process_audio(trimmed_audio, sr)
        
        # Step 4: Silent-bed transplant with 20ms fades
        logger.info("\nSTEP 4: Silent-bed transplant with 20ms crossfades")
        if len(speech_segments) > 0:
            final_audio = self.silent_bed.smart_transplant(
                trimmed_audio,
                enhanced_audio,
                speech_segments
            )
        else:
            final_audio = enhanced_audio
        
        # Normalize audio
        max_val = np.abs(final_audio).max()
        if max_val > 0:
            final_audio = final_audio / max_val * 0.95
        
        # Step 5: Save cleaned audio
        logger.info("\nSTEP 5: Saving cleaned audio")
        output_format = self.config['output']['format']
        bit_depth = self.config['output']['bit_depth']
        
        audio_output_path = output_dir / f"{input_name}_cleaned.{output_format}"
        self.media_loader.save_audio(
            final_audio, 
            sr, 
            str(audio_output_path),
            format=output_format,
            bit_depth=bit_depth
        )
        
        # Step 6: Diarization branch (parallel with ASR)
        logger.info("\nSTEP 6: Speaker diarization")
        diarization_results = None
        if self.diarization is not None:
            try:
                diarization_results = self.diarization.diarize(str(audio_output_path))
                if diarization_results:
                    stats = self.diarization.get_speaker_statistics(diarization_results)
                    logger.info(f"Speaker statistics: {stats}")
            except Exception as e:
                logger.warning(f"Diarization failed: {e}")
        
        # Step 7: Raw-ASR branch
        logger.info("\nSTEP 7: Automatic speech recognition")
        transcript = self.asr.transcribe(str(audio_output_path))
        logger.info(f"Transcribed: {len(transcript.get('text', ''))} characters")
        
        # Save transcript
        if save_transcript:
            transcript_path = output_dir / f"{input_name}_transcript.{transcript_format}"
            self.asr.save_transcript(
                transcript,
                str(transcript_path),
                format=transcript_format,
                diarization=diarization_results
            )
            logger.info(f"Transcript saved to: {transcript_path}")
        
        # Step 8: Merge back to video if needed
        video_output_path = None
        if is_video and self.config['output']['preserve_video']:
            logger.info("\nSTEP 8: Merging cleaned audio back to video")
            video_output_path = output_dir / f"{input_name}_cleaned.mp4"
            try:
                self.media_loader.merge_audio_to_video(
                    input_path,
                    str(audio_output_path),
                    str(video_output_path)
                )
            except Exception as e:
                logger.error(f"Video merging failed: {e}")
        
        logger.info("\n" + "=" * 70)
        logger.info("Pipeline completed successfully!")
        
        elapsed_time = time.time() - start_time
        
        # Return results
        results = {
            'input_path': input_path,
            'is_video': is_video,
            'audio_output_path': str(audio_output_path),
            'video_output_path': str(video_output_path) if video_output_path else None,
            'transcript': transcript,
            'diarization': diarization_results,
            'duration_original': len(audio) / sr,
            'duration_processed': len(final_audio) / sr,
            'speech_segments': len(speech_segments),
            'processing_time': elapsed_time,
            'from_cache': False
        }
        
        # Cache the results for next time
        if self.enable_cache and self.cache:
            try:
                transcript_path = None
                if save_transcript:
                    transcript_path = str(output_dir / f"{input_name}_transcript.{transcript_format}")
                
                self.cache.set(
                    input_path,
                    self.config,
                    results,
                    str(audio_output_path),
                    transcript_path
                )
                logger.info("✅ Results cached for faster future processing")
            except Exception as e:
                logger.warning(f"Failed to cache results: {e}")
        
        return results

    def process_batch(self, 
                     input_files: list,
                     output_dir: str = "outputs",
                     continue_on_error: bool = True):
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
