"""
Silent-Bed Transplant Module
Preserves original silence while using enhanced speech
"""

import numpy as np
from typing import List, Tuple
from scipy import signal
import logging

logger = logging.getLogger(__name__)

class SilentBedTransplant:
    """Transplant enhanced speech onto original silent bed"""
    
    def __init__(self, fade_duration_ms: int = 20, sample_rate: int = 16000):
        """
        Args:
            fade_duration_ms: Crossfade duration in milliseconds
            sample_rate: Audio sample rate
        """
        self.fade_duration_ms = fade_duration_ms
        self.sample_rate = sample_rate
        self.fade_samples = int(fade_duration_ms * sample_rate / 1000)
    
    def _create_fade(self, length: int, fade_in: bool = True) -> np.ndarray:
        """Create fade envelope (cosine)"""
        if fade_in:
            return 0.5 * (1 - np.cos(np.linspace(0, np.pi, length)))
        else:
            return 0.5 * (1 + np.cos(np.linspace(0, np.pi, length)))
    
    def transplant(self,
                  original_audio: np.ndarray,
                  enhanced_audio: np.ndarray,
                  speech_segments: List[Tuple[int, int]]) -> np.ndarray:
        """
        Transplant enhanced speech onto original silent bed
        
        Args:
            original_audio: Original audio with natural silence
            enhanced_audio: DeepFilterNet enhanced audio
            speech_segments: List of (start, end) indices for speech
            
        Returns:
            Combined audio with enhanced speech and original silence
        """
        # Start with original audio (the "silent bed")
        output = original_audio.copy()
        
        logger.info(f"Transplanting {len(speech_segments)} speech segments")
        
        for i, (start, end) in enumerate(speech_segments):
            duration = end - start
            
            # Extract segments
            orig_segment = original_audio[start:end]
            enh_segment = enhanced_audio[start:end]
            
            # Apply crossfades at boundaries
            segment_output = enh_segment.copy()
            
            # Fade in at start
            if duration > 2 * self.fade_samples:
                fade_in = self._create_fade(self.fade_samples, fade_in=True)
                segment_output[:self.fade_samples] = (
                    orig_segment[:self.fade_samples] * (1 - fade_in) +
                    enh_segment[:self.fade_samples] * fade_in
                )
                
                # Fade out at end
                fade_out = self._create_fade(self.fade_samples, fade_in=False)
                segment_output[-self.fade_samples:] = (
                    enh_segment[-self.fade_samples:] * fade_out +
                    orig_segment[-self.fade_samples:] * (1 - fade_out)
                )
            else:
                # Short segment - use full crossfade
                fade = self._create_fade(duration, fade_in=True)
                segment_output = orig_segment * (1 - fade) + enh_segment * fade
            
            # Place in output
            output[start:end] = segment_output
        
        logger.info("Silent-bed transplant completed")
        return output
    
    def smart_transplant(self,
                        original_audio: np.ndarray,
                        enhanced_audio: np.ndarray,
                        speech_segments: List[Tuple[int, int]],
                        energy_threshold: float = 0.02) -> np.ndarray:
        """
        Smart transplant that analyzes energy levels
        
        Args:
            original_audio: Original audio
            enhanced_audio: Enhanced audio
            speech_segments: Speech segment boundaries
            energy_threshold: Threshold for detecting silence
            
        Returns:
            Optimally combined audio
        """
        output = original_audio.copy()
        
        for start, end in speech_segments:
            segment_len = end - start
            orig_seg = original_audio[start:end]
            enh_seg = enhanced_audio[start:end]
            
            # Calculate RMS energy in windows
            window_size = int(0.02 * self.sample_rate)  # 20ms windows
            
            # Detect truly silent regions within speech segment
            hop = window_size // 2
            orig_energy = []
            
            for i in range(0, segment_len - window_size, hop):
                window = orig_seg[i:i + window_size]
                rms = np.sqrt(np.mean(window ** 2))
                orig_energy.append(rms)
            
            # Create mixing envelope
            mix_envelope = np.ones(segment_len)
            
            for i, energy in enumerate(orig_energy):
                pos = i * hop
                if energy < energy_threshold:
                    # Use more of original in silent regions
                    mix_envelope[pos:pos + window_size] = 0.3
            
            # Smooth envelope
            if len(mix_envelope) > 100:
                smooth_window = signal.windows.hann(51)
                smooth_window /= smooth_window.sum()
                mix_envelope = signal.convolve(mix_envelope, smooth_window, mode='same')
            
            # Apply crossfades at boundaries
            if segment_len > 2 * self.fade_samples:
                fade_in = self._create_fade(self.fade_samples, fade_in=True)
                mix_envelope[:self.fade_samples] *= fade_in
                
                fade_out = self._create_fade(self.fade_samples, fade_in=False)
                mix_envelope[-self.fade_samples:] *= fade_out
            
            # Mix segments
            output[start:end] = (
                orig_seg * (1 - mix_envelope) +
                enh_seg * mix_envelope
            )
        
        logger.info("Smart silent-bed transplant completed")
        return output
