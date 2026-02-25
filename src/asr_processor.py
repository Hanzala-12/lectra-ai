"""
Automatic Speech Recognition Module
Transcribes the cleaned audio
"""

import numpy as np
import torch
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class ASRProcessor:
    """Automatic Speech Recognition using Whisper"""
    
    def __init__(self,
                 model_size: str = "base",
                 language: Optional[str] = "en",
                 device: str = None,
                 compute_type: str = "float16"):
        """
        Args:
            model_size: Model size (tiny, base, small, medium, large)
            language: Language code or None for auto-detection
            device: torch device (cuda/cpu)
            compute_type: Computation type (float16, int8, float32)
        """
        self.model_size = model_size
        self.language = language
        self.compute_type = compute_type
        
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing Whisper {model_size} on {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        try:
            import whisper
            import os
            
            # Use local models folder
            models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
            os.makedirs(models_dir, exist_ok=True)
            
            logger.info(f"Loading Whisper {self.model_size} model to {models_dir}")
            
            self.model = whisper.load_model(
                self.model_size,
                device=self.device,
                download_root=models_dir
            )
            
            logger.info(f"Whisper model loaded successfully from {models_dir}")
            
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise
    
    def transcribe(self, 
                  audio_path: str,
                  word_timestamps: bool = True) -> Dict:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            word_timestamps: Include word-level timestamps
            
        Returns:
            Transcription result dictionary
        """
        try:
            result = self.model.transcribe(
                audio_path,
                language=self.language,
                word_timestamps=word_timestamps,
                verbose=False
            )
            
            n_segments = len(result.get('segments', []))
            logger.info(f"Transcription complete: {n_segments} segments")
            
            return result
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return {'text': '', 'segments': []}
    
    def transcribe_array(self,
                        audio: np.ndarray,
                        sample_rate: int = 16000) -> Dict:
        """
        Transcribe audio from numpy array
        
        Args:
            audio: Audio array (mono, float32)
            sample_rate: Sample rate
            
        Returns:
            Transcription result
        """
        import tempfile
        import soundfile as sf
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
            sf.write(f.name, audio, sample_rate)
            temp_path = f.name
        
        # Transcribe
        result = self.transcribe(temp_path)
        
        # Cleanup
        import os
        os.unlink(temp_path)
        
        return result
    
    def format_transcript(self, result: Dict, include_timestamps: bool = True) -> str:
        """
        Format transcription result as readable text
        
        Args:
            result: Whisper transcription result
            include_timestamps: Include timestamps in output
            
        Returns:
            Formatted transcript string
        """
        if not result.get('segments'):
            return result.get('text', '')
        
        lines = []
        for segment in result['segments']:
            if include_timestamps:
                start = segment['start']
                end = segment['end']
                text = segment['text'].strip()
                lines.append(f"[{start:.2f}s - {end:.2f}s] {text}")
            else:
                lines.append(segment['text'].strip())
        
        return '\n'.join(lines)
    
    def combine_with_diarization(self,
                                transcript: Dict,
                                diarization: List[Dict]) -> List[Dict]:
        """
        Combine ASR transcription with speaker diarization
        
        Args:
            transcript: Whisper transcription result
            diarization: Speaker diarization segments
            
        Returns:
            Combined segments with speaker labels
        """
        if not diarization:
            return transcript.get('segments', [])
        
        combined = []
        
        for seg in transcript.get('segments', []):
            start = seg['start']
            end = seg['end']
            text = seg['text']
            
            # Find overlapping speaker
            max_overlap = 0
            best_speaker = 'Unknown'
            
            for dia in diarization:
                # Calculate overlap
                overlap_start = max(start, dia['start'])
                overlap_end = min(end, dia['end'])
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    best_speaker = dia['speaker']
            
            combined.append({
                'start': start,
                'end': end,
                'text': text,
                'speaker': best_speaker
            })
        
        logger.info(f"Combined {len(combined)} transcript segments with speaker labels")
        return combined
    
    def save_transcript(self, 
                       result: Dict,
                       output_path: str,
                       format: str = 'txt',
                       diarization: Optional[List[Dict]] = None):
        """
        Save transcript to file
        
        Args:
            result: Transcription result
            output_path: Output file path
            format: Output format (txt, srt, vtt, json)
            diarization: Optional diarization for speaker labels
        """
        if format == 'txt':
            if diarization:
                combined = self.combine_with_diarization(result, diarization)
                lines = []
                for seg in combined:
                    lines.append(f"[{seg['speaker']}] {seg['text']}")
                text = '\n'.join(lines)
            else:
                text = self.format_transcript(result, include_timestamps=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
        
        elif format == 'json':
            import json
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
        
        elif format in ['srt', 'vtt']:
            self._save_subtitle_format(result, output_path, format)
        
        logger.info(f"Transcript saved to: {output_path}")
    
    def _save_subtitle_format(self, result: Dict, output_path: str, format: str):
        """Save transcript in subtitle format (SRT/VTT)"""
        segments = result.get('segments', [])
        
        lines = []
        if format == 'vtt':
            lines.append('WEBVTT\n')
        
        for i, seg in enumerate(segments, 1):
            start = self._format_timestamp(seg['start'], format)
            end = self._format_timestamp(seg['end'], format)
            text = seg['text'].strip()
            
            if format == 'srt':
                lines.append(f"{i}")
                lines.append(f"{start} --> {end}")
                lines.append(text)
                lines.append("")
            else:  # vtt
                lines.append(f"{start} --> {end}")
                lines.append(text)
                lines.append("")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
    
    def _format_timestamp(self, seconds: float, format: str) -> str:
        """Format timestamp for subtitle formats"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        if format == 'srt':
            return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
        else:  # vtt
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"
