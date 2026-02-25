"""
Speaker Diarization Module
Identifies who spoke when in the audio
"""

import numpy as np
import torch
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class SpeakerDiarization:
    """Speaker diarization using pyannote.audio"""
    
    def __init__(self, 
                 min_speakers: int = 1,
                 max_speakers: int = 10,
                 device: str = None):
        """
        Args:
            min_speakers: Minimum number of speakers
            max_speakers: Maximum number of speakers
            device: torch device (cuda/cpu)
        """
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing speaker diarization on {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load pyannote.audio pipeline"""
        try:
            from pyannote.audio import Pipeline
            
            # Load pretrained pipeline
            # Note: Requires HuggingFace token for access
            # Set environment variable: HUGGING_FACE_HUB_TOKEN
            self.pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=True
            )
            
            self.pipeline.to(torch.device(self.device))
            logger.info("Diarization pipeline loaded successfully")
            
        except Exception as e:
            logger.warning(f"Could not load diarization model: {e}")
            logger.warning("Diarization will be disabled. Set HUGGING_FACE_HUB_TOKEN to enable.")
            self.pipeline = None
    
    def diarize(self, audio_path: str) -> List[Dict]:
        """
        Perform speaker diarization
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of diarization segments with format:
            [{'start': float, 'end': float, 'speaker': str}, ...]
        """
        if self.pipeline is None:
            logger.warning("Diarization unavailable")
            return []
        
        try:
            # Run diarization
            diarization = self.pipeline(
                audio_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )
            
            # Convert to list format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    'start': turn.start,
                    'end': turn.end,
                    'speaker': speaker
                })
            
            n_speakers = len(set(seg['speaker'] for seg in segments))
            logger.info(f"Diarization complete: {n_speakers} speakers, {len(segments)} segments")
            
            return segments
            
        except Exception as e:
            logger.error(f"Diarization error: {e}")
            return []
    
    def get_speaker_statistics(self, segments: List[Dict]) -> Dict[str, float]:
        """
        Calculate speaking time for each speaker
        
        Args:
            segments: Diarization segments
            
        Returns:
            Dictionary of speaker: total_time_seconds
        """
        stats = {}
        for seg in segments:
            speaker = seg['speaker']
            duration = seg['end'] - seg['start']
            stats[speaker] = stats.get(speaker, 0) + duration
        
        return stats
