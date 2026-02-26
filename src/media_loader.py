"""
Audio/Video Input Handler
Extracts audio from video files or loads audio directly
"""

import os
from pathlib import Path
from typing import Tuple, Optional
import numpy as np
import soundfile as sf
import librosa
from pydub import AudioSegment
try:
    from moviepy.editor import VideoFileClip
except ImportError:
    VideoFileClip = None
import logging

logger = logging.getLogger(__name__)

class MediaLoader:
    """Handles loading audio from audio/video files"""
    
    AUDIO_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'}
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    
    def __init__(self, target_sr: int = 16000):
        """
        Args:
            target_sr: Target sample rate for processing
        """
        self.target_sr = target_sr
    
    def load_media(self, file_path: str) -> Tuple[np.ndarray, int, bool]:
        """
        Load audio from media file (audio or video)
        
        Args:
            file_path: Path to media file
            
        Returns:
            Tuple of (audio_array, sample_rate, is_video)
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = file_path.suffix.lower()
        
        if ext in self.AUDIO_EXTENSIONS:
            logger.info(f"Loading audio file: {file_path.name}")
            audio, sr = self._load_audio(str(file_path))
            return audio, sr, False
            
        elif ext in self.VIDEO_EXTENSIONS:
            logger.info(f"Extracting audio from video: {file_path.name}")
            audio, sr = self._extract_audio_from_video(str(file_path))
            return audio, sr, True
            
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def _load_audio(self, file_path: str) -> Tuple[np.ndarray, int]:
        """Load audio file using librosa"""
        try:
            audio, sr = librosa.load(file_path, sr=self.target_sr, mono=True)
            logger.info(f"Loaded audio: {len(audio)/sr:.2f}s @ {sr}Hz")
            return audio, sr
        except Exception as e:
            logger.error(f"Error loading audio: {e}")
            raise
    
    def _extract_audio_from_video(self, video_path: str) -> Tuple[np.ndarray, int]:
        """Extract audio from video file"""
        if VideoFileClip is None:
            raise ImportError("moviepy is not installed. Install it with: pip install moviepy")
        
        try:
            # Create temporary audio file
            temp_audio = "temp_extracted_audio.wav"
            
            # Extract audio using moviepy
            video = VideoFileClip(video_path)
            if video.audio is None:
                raise ValueError("Video file has no audio track")
            
            video.audio.write_audiofile(temp_audio, fps=self.target_sr, 
                                       nbytes=2, codec='pcm_s16le',
                                       logger=None)
            video.close()
            
            # Load extracted audio
            audio, sr = librosa.load(temp_audio, sr=self.target_sr, mono=True)
            
            # Clean up temp file
            if os.path.exists(temp_audio):
                os.remove(temp_audio)
            
            logger.info(f"Extracted audio from video: {len(audio)/sr:.2f}s @ {sr}Hz")
            return audio, sr
            
        except Exception as e:
            logger.error(f"Error extracting audio from video: {e}")
            raise

    def save_audio(self, audio: np.ndarray, sr: int, output_path: str, 
                   format: str = 'wav', bit_depth: int = 16):
        """
        Save audio to file
        
        Args:
            audio: Audio array
            sr: Sample rate
            output_path: Output file path
            format: Output format (wav, mp3, flac)
            bit_depth: Bit depth for wav files (16 or 24)
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        subtype_map = {16: 'PCM_16', 24: 'PCM_24'}
        
        if format.lower() == 'wav':
            sf.write(str(output_path), audio, sr, 
                    subtype=subtype_map.get(bit_depth, 'PCM_16'))
        else:
            # For mp3/flac, convert via pydub
            temp_wav = "temp_output.wav"
            sf.write(temp_wav, audio, sr, subtype='PCM_16')
            sound = AudioSegment.from_wav(temp_wav)
            sound.export(str(output_path), format=format)
            os.remove(temp_wav)
        
        logger.info(f"Saved audio to: {output_path}")

    def merge_audio_to_video(self, video_path: str, audio_path: str, 
                            output_path: str):
        """
        Replace video audio with processed audio
        
        Args:
            video_path: Original video file
            audio_path: Processed audio file
            output_path: Output video file
        """
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip
            
            video = VideoFileClip(video_path)
            audio = AudioFileClip(audio_path)
            
            # Replace audio
            video_with_new_audio = video.set_audio(audio)
            
            # Write output
            video_with_new_audio.write_videofile(output_path, 
                                                 codec='libx264',
                                                 audio_codec='aac',
                                                 logger=None)
            
            video.close()
            audio.close()
            video_with_new_audio.close()
            
            logger.info(f"Merged audio back to video: {output_path}")
            
        except Exception as e:
            logger.error(f"Error merging audio to video: {e}")
            raise
