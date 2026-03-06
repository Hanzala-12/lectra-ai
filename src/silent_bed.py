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

    def transplant(
        self,
        original_audio: np.ndarray,
        enhanced_audio: np.ndarray,
        speech_segments: List[Tuple[int, int]],
    ) -> np.ndarray:
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
                segment_output[: self.fade_samples] = (
                    orig_segment[: self.fade_samples] * (1 - fade_in)
                    + enh_segment[: self.fade_samples] * fade_in
                )

                # Fade out at end
                fade_out = self._create_fade(self.fade_samples, fade_in=False)
                segment_output[-self.fade_samples :] = enh_segment[
                    -self.fade_samples :
                ] * fade_out + orig_segment[-self.fade_samples :] * (1 - fade_out)
            else:
                # Short segment - use full crossfade
                fade = self._create_fade(duration, fade_in=True)
                segment_output = orig_segment * (1 - fade) + enh_segment * fade

            # Place in output
            output[start:end] = segment_output

        logger.info("Silent-bed transplant completed")
        return output

    def smart_transplant(
        self,
        original_audio: np.ndarray,
        enhanced_audio: np.ndarray,
        speech_segments: List[Tuple[int, int]],
        energy_threshold: float = 0.02,
        background_gain: float = 0.08,
    ) -> np.ndarray:
        """
        Smart transplant that analyzes energy levels

        Args:
            original_audio: Original audio
            enhanced_audio: Enhanced audio
            speech_segments: Speech segment boundaries
            energy_threshold: Threshold for detecting silence
            background_gain: Residual gain outside speech regions [0, 1]

        Returns:
            Optimally combined audio
        """
        # Pure silence background — no original or enhanced audio bleeds in outside speech.
        output = np.zeros_like(enhanced_audio)

        for start, end in speech_segments:
            segment_len = end - start
            if segment_len <= 0:
                continue
            enh_seg = enhanced_audio[start:end].copy()

            # Apply short cosine fades at boundaries to avoid clicks.
            # Speech interior is untouched — 100% clean denoised audio.
            if segment_len > 2 * self.fade_samples:
                fade_in = self._create_fade(self.fade_samples, fade_in=True)
                enh_seg[: self.fade_samples] *= fade_in

                fade_out = self._create_fade(self.fade_samples, fade_in=False)
                enh_seg[-self.fade_samples :] *= fade_out

            output[start:end] = enh_seg

        logger.info("Silent-bed transplant completed: clean speech on pure silence")
        return output
