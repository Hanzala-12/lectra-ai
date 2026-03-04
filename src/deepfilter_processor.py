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
                 double_pass: bool = False,
                 device: str = None):
        """
        Args:
            model_name: Model to use (DeepFilterNet2 or DeepFilterNet3)
            post_filter: Enable additional post-processing
            double_pass: Run enhancement twice for stubborn noise (costs 2x DeepFilter time)
            device: torch device (cuda/cpu), auto-detected if None
        """
        self.model_name = model_name
        self.post_filter = post_filter
        self.double_pass = double_pass
        
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
            import os
            from df.enhance import init_df, enhance
            from df import config

            # Redirect DeepFilterNet model to D:\fyp\models (not C:\Users\...\AppData)
            # init_df expects model_base_dir to be the folder containing config.ini directly
            df_cache_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'deepfilternet', 'DeepFilterNet3')
            df_cache_dir = os.path.abspath(df_cache_dir)
            os.makedirs(df_cache_dir, exist_ok=True)

            # Load model
            self.model, self.df_state, _ = init_df(
                model_base_dir=df_cache_dir,
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

        # Pass 1: enhance full audio — atten_lim_db=0 = no cap on noise attenuation
        with torch.no_grad():
            enhanced = self.enhance(
                self.model,
                self.df_state,
                audio_tensor,
                atten_lim_db=0
            )

        # Pass 2 (optional): re-run on the already-cleaned output to scrub residual noise
        if self.double_pass:
            logger.info("Double-pass: running second enhancement pass")
            with torch.no_grad():
                enhanced = self.enhance(
                    self.model,
                    self.df_state,
                    enhanced,
                    atten_lim_db=0
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
    
