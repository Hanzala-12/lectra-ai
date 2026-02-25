"""
Voice Activity Detection (VAD) Module
Pre-trims audio to remove silence before/after speech
"""

import numpy as np
import webrtcvad
import struct
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class VADProcessor:
    """Voice Activity Detection for pre-trimming"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 aggressiveness: int = 3,
                 frame_duration_ms: int = 30,
                 padding_duration_ms: int = 300,
                 min_speech_duration_ms: int = 250):
        """
        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            aggressiveness: VAD aggressiveness mode (0-3)
            frame_duration_ms: Frame duration in ms (10, 20, or 30)
            padding_duration_ms: Padding around speech segments
            min_speech_duration_ms: Minimum speech segment length to keep
        """
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad(aggressiveness)
        self.frame_duration_ms = frame_duration_ms
        self.padding_duration_ms = padding_duration_ms
        self.min_speech_duration_ms = min_speech_duration_ms
        
        # Calculate frame properties
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.padding_frames = int(padding_duration_ms / frame_duration_ms)
        self.min_speech_frames = int(min_speech_duration_ms / frame_duration_ms)
    
    def _frame_generator(self, audio: np.ndarray):
        """Generate audio frames with frame_duration_ms"""
        n = len(audio)
        offset = 0
        
        while offset + self.frame_size <= n:
            yield audio[offset:offset + self.frame_size]
            offset += self.frame_size
    
    def _is_speech(self, frame: np.ndarray) -> bool:
        """Check if frame contains speech"""
        # Convert float32 to int16 for VAD
        frame_int16 = (frame * 32767).astype(np.int16)
        frame_bytes = struct.pack("%dh" % len(frame_int16), *frame_int16)
        
        try:
            return self.vad.is_speech(frame_bytes, self.sample_rate)
        except:
            return False
    
    def detect_speech_segments(self, audio: np.ndarray) -> List[Tuple[int, int]]:
        """
        Detect speech segments in audio
        
        Args:
            audio: Audio array (float32, mono)
            
        Returns:
            List of (start_sample, end_sample) tuples for speech segments
        """
        frames = list(self._frame_generator(audio))
        is_speech_flags = [self._is_speech(frame) for frame in frames]
        
        # Add padding around speech
        padded_flags = self._add_padding(is_speech_flags)
        
        # Find contiguous speech segments
        segments = []
        start_idx = None
        
        for i, is_speech in enumerate(padded_flags):
            if is_speech and start_idx is None:
                start_idx = i
            elif not is_speech and start_idx is not None:
                # Check if segment is long enough
                if i - start_idx >= self.min_speech_frames:
                    start_sample = start_idx * self.frame_size
                    end_sample = min(i * self.frame_size, len(audio))
                    segments.append((start_sample, end_sample))
                start_idx = None
        
        # Handle case where speech goes to end
        if start_idx is not None:
            if len(padded_flags) - start_idx >= self.min_speech_frames:
                start_sample = start_idx * self.frame_size
                segments.append((start_sample, len(audio)))
        
        logger.info(f"Detected {len(segments)} speech segments")
        return segments
    
    def _add_padding(self, flags: List[bool]) -> List[bool]:
        """Add padding frames around speech segments"""
        padded = flags.copy()
        
        for i, is_speech in enumerate(flags):
            if is_speech:
                # Add padding before
                start = max(0, i - self.padding_frames)
                for j in range(start, i):
                    padded[j] = True
                
                # Add padding after
                end = min(len(flags), i + self.padding_frames + 1)
                for j in range(i + 1, end):
                    padded[j] = True
        
        return padded
    
    def trim_silence(self, audio: np.ndarray) -> Tuple[np.ndarray, List[Tuple[int, int]]]:
        """
        Trim leading/trailing silence and identify speech segments
        
        Args:
            audio: Input audio array
            
        Returns:
            Tuple of (trimmed_audio, speech_segments_in_original)
        """
        segments = self.detect_speech_segments(audio)
        
        if not segments:
            logger.warning("No speech detected in audio")
            return audio, []
        
        # Find overall speech boundaries
        first_speech_start = segments[0][0]
        last_speech_end = segments[-1][1]
        
        # Trim audio
        trimmed_audio = audio[first_speech_start:last_speech_end]
        
        # Adjust segment positions relative to trimmed audio
        adjusted_segments = [
            (start - first_speech_start, end - first_speech_start)
            for start, end in segments
        ]
        
        original_duration = len(audio) / self.sample_rate
        trimmed_duration = len(trimmed_audio) / self.sample_rate
        
        logger.info(f"Trimmed audio from {original_duration:.2f}s to {trimmed_duration:.2f}s")
        
        return trimmed_audio, adjusted_segments
