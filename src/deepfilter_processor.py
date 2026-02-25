"""
DeepFilterNet Noise Reduction Module
Processes speech chunks to remove background noise
"""

import numpy as np
import torch
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class DeepFilterProcessor:
    """DeepFilterNet-based noise reduction"""
    
    def __init__(self, 
                 model_name: str = "DeepFilterNet3",
                 post_filter: bool = True,
                 device: str = None):
        """
        Args:
            model_name: Model to use (DeepFilterNet2 or DeepFilterNet3)
            post_filter: Enable additional post-processing
            device: torch device (cuda/cpu), auto-detected if None
        """
        self.model_name = model_name
        self.post_filter = post_filter
        
        # Auto-detect device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        logger.info(f"Initializing {model_name} on {self.device}")
        self._load_model()
    
    def _load_model(self):
        """Load DeepFilterNet model"""
        try:
            from df.enhance import init_df, enhance
            from df import config
            
            # Load model
            self.model, self.df_state, _ = init_df(
                model_base_dir=None,  # Use default model location
                post_filter=self.post_filter,
                config_allow_defaults=True
            )
            
            self.model.to(self.device)
            self.enhance = enhance
            self.sample_rate = self.df_state.sr()
            
            logger.info(f"Model loaded successfully (SR: {self.sample_rate}Hz)")
            
        except Exception as e:
            logger.error(f"Error loading DeepFilterNet model: {e}")
            raise
    
    def process_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Process full audio through DeepFilterNet
        
        Args:
            audio: Input audio array (mono, float32)
            sr: Sample rate
            
        Returns:
            Enhanced audio array
        """
        # Resample if needed
        if sr != self.sample_rate:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=self.sample_rate)
            logger.info(f"Resampled audio from {sr}Hz to {self.sample_rate}Hz")
        
        # Convert to torch tensor
        audio_tensor = torch.from_numpy(audio).unsqueeze(0).to(self.device)
        
        # Enhance audio
        with torch.no_grad():
            enhanced = self.enhance(
                self.model,
                self.df_state,
                audio_tensor
            )
        
        # Convert back to numpy
        enhanced_audio = enhanced.cpu().numpy().squeeze()
        
        # Resample back if needed
        if sr != self.sample_rate:
            enhanced_audio = librosa.resample(
                enhanced_audio, 
                orig_sr=self.sample_rate, 
                target_sr=sr
            )
        
        logger.info("Audio enhancement completed")
        return enhanced_audio
    
    def process_segments(self, 
                        audio: np.ndarray,
                        sr: int,
                        segments: List[Tuple[int, int]]) -> np.ndarray:
        """
        Process only specific speech segments
        
        Args:
            audio: Full audio array
            sr: Sample rate
            segments: List of (start, end) sample indices
            
        Returns:
            Audio with enhanced segments
        """
        enhanced_audio = audio.copy()
        
        logger.info(f"Processing {len(segments)} segments")
        
        for i, (start, end) in enumerate(segments):
            segment = audio[start:end]
            
            # Process segment
            enhanced_segment = self.process_audio(segment, sr)
            
            # Replace in output
            enhanced_audio[start:end] = enhanced_segment
            
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(segments)} segments")
        
        return enhanced_audio
    
    def process_chunks(self, 
                      audio: np.ndarray,
                      sr: int,
                      chunk_duration: float = 30.0) -> np.ndarray:
        """
        Process audio in chunks for memory efficiency
        
        Args:
            audio: Input audio array
            sr: Sample rate
            chunk_duration: Duration of each chunk in seconds
            
        Returns:
            Enhanced audio array
        """
        chunk_samples = int(chunk_duration * sr)
        n_samples = len(audio)
        
        if n_samples <= chunk_samples:
            return self.process_audio(audio, sr)
        
        # Process in overlapping chunks for smooth transitions
        overlap = int(0.5 * sr)  # 0.5 second overlap
        enhanced_audio = np.zeros_like(audio)
        
        chunks = []
        positions = []
        
        # Create chunks
        pos = 0
        while pos < n_samples:
            end = min(pos + chunk_samples, n_samples)
            chunks.append(audio[pos:end])
            positions.append((pos, end))
            pos = end - overlap if end < n_samples else end
        
        logger.info(f"Processing {len(chunks)} chunks")
        
        # Process chunks
        for i, (chunk, (start, end)) in enumerate(zip(chunks, positions)):
            enhanced_chunk = self.process_audio(chunk, sr)
            
            # Blend overlapping regions
            if i == 0:
                enhanced_audio[start:end] = enhanced_chunk
            else:
                prev_end = positions[i-1][1]
                overlap_start = start
                overlap_len = prev_end - overlap_start
                
                if overlap_len > 0:
                    # Crossfade
                    fade_out = np.linspace(1, 0, overlap_len)
                    fade_in = np.linspace(0, 1, overlap_len)
                    
                    enhanced_audio[overlap_start:prev_end] = (
                        enhanced_audio[overlap_start:prev_end] * fade_out +
                        enhanced_chunk[:overlap_len] * fade_in
                    )
                    enhanced_audio[prev_end:end] = enhanced_chunk[overlap_len:]
                else:
                    enhanced_audio[start:end] = enhanced_chunk
            
            if (i + 1) % 5 == 0:
                logger.info(f"Processed {i + 1}/{len(chunks)} chunks")
        
        return enhanced_audio
