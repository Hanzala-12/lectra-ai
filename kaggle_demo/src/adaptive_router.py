"""
Adaptive Router Module
Intelligently selects processing method based on noise level
"""

import numpy as np
from scipy import signal
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# Optional: noisereduce for spectral subtraction
try:
    import noisereduce as nr

    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False
    logger.warning("noisereduce not available - using custom implementations")


class AdaptiveRouter:
    """
    Routes audio to appropriate noise removal method based on SNR

    Methods:
    - Light noise (SNR > 15 dB): Spectral Subtraction
    - Medium noise (5-15 dB): Wiener Filter
    - Heavy noise (SNR < 5 dB): DeepFilterNet (external processor)
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize adaptive router

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.frame_length = 1024
        self.hop_length = 256

    def route_processing(
        self,
        audio: np.ndarray,
        profile: Dict[str, float],
        config: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, str]:
        """
        Route audio to appropriate processing method

        Args:
            audio: Input audio
            profile: Audio quality profile from AudioQualityProfiler
            config: Optional configuration dict

        Returns:
            Tuple of (processed_audio, method_name)
        """
        snr = profile.get("snr_db", 10.0)

        logger.info(f"Routing decision: SNR={snr:.1f}dB")

        # Route based on SNR
        if snr > 15:
            # Light noise - spectral subtraction
            logger.info("Selected method: Spectral Subtraction (light noise)")
            processed = self._spectral_subtraction(audio)
            method = "spectral_subtraction"

        elif snr > 5:
            # Medium noise - Wiener filter
            logger.info("Selected method: Wiener Filter (medium noise)")
            processed = self._wiener_filter(audio)
            method = "wiener_filter"

        else:
            # Heavy noise - should use DeepFilterNet (external)
            logger.info(
                "Selected method: DeepFilterNet (heavy noise - requires external processor)"
            )
            # Return original audio - caller should use DeepFilterNet
            processed = audio
            method = "deepfilternet_required"

        return processed, method

    def _spectral_subtraction(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply spectral subtraction for light noise removal

        Classic method: estimate noise spectrum and subtract from signal
        """
        if NOISEREDUCE_AVAILABLE:
            # Use noisereduce library if available
            try:
                reduced = nr.reduce_noise(
                    y=audio, sr=self.sample_rate, stationary=True, prop_decrease=0.8
                )
                return reduced.astype(np.float32)
            except Exception as e:
                logger.warning(f"noisereduce failed: {e}, using custom implementation")

        # Custom spectral subtraction implementation
        return self._custom_spectral_subtraction(audio)

    def _custom_spectral_subtraction(self, audio: np.ndarray) -> np.ndarray:
        """
        Custom spectral subtraction implementation
        """
        # Compute STFT
        f, t, Zxx = signal.stft(
            audio,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Estimate noise spectrum from first 10% of signal (assumed to be noise)
        noise_frames = int(0.1 * Zxx.shape[1])
        noise_spectrum = np.mean(np.abs(Zxx[:, :noise_frames]), axis=1, keepdims=True)

        # Spectral subtraction with over-subtraction factor
        alpha = 2.0  # Over-subtraction factor
        beta = 0.01  # Spectral floor

        magnitude = np.abs(Zxx)
        phase = np.angle(Zxx)

        # Subtract noise spectrum
        magnitude_clean = magnitude - alpha * noise_spectrum

        # Apply spectral floor
        magnitude_clean = np.maximum(magnitude_clean, beta * magnitude)

        # Reconstruct complex spectrum
        Zxx_clean = magnitude_clean * np.exp(1j * phase)

        # Inverse STFT
        _, audio_clean = signal.istft(
            Zxx_clean,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Ensure same length
        audio_clean = audio_clean[: len(audio)]

        return audio_clean.astype(np.float32)

    def _wiener_filter(self, audio: np.ndarray) -> np.ndarray:
        """
        Apply Wiener filter for medium noise removal

        Optimal MMSE filter based on SNR estimation
        """
        # Compute STFT
        f, t, Zxx = signal.stft(
            audio,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Estimate noise power spectrum from first 10% of signal
        noise_frames = int(0.1 * Zxx.shape[1])
        noise_power = np.mean(np.abs(Zxx[:, :noise_frames]) ** 2, axis=1, keepdims=True)

        # Signal power spectrum
        signal_power = np.abs(Zxx) ** 2

        # A priori SNR estimation
        snr_prior = np.maximum(signal_power / (noise_power + 1e-10) - 1, 0)

        # Wiener gain
        wiener_gain = snr_prior / (snr_prior + 1)

        # Apply gain
        Zxx_clean = Zxx * wiener_gain

        # Inverse STFT
        _, audio_clean = signal.istft(
            Zxx_clean,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Ensure same length
        audio_clean = audio_clean[: len(audio)]

        return audio_clean.astype(np.float32)

    def _estimate_noise_spectrum(
        self, Zxx: np.ndarray, method: str = "minimum"
    ) -> np.ndarray:
        """
        Estimate noise power spectrum

        Args:
            Zxx: STFT matrix
            method: 'minimum' or 'first_frames'

        Returns:
            Noise power spectrum (frequency bins x 1)
        """
        if method == "minimum":
            # Use minimum statistics
            power = np.abs(Zxx) ** 2
            noise_power = np.percentile(power, 10, axis=1, keepdims=True)
        else:
            # Use first frames
            noise_frames = int(0.1 * Zxx.shape[1])
            noise_power = np.mean(
                np.abs(Zxx[:, :noise_frames]) ** 2, axis=1, keepdims=True
            )

        return noise_power

    def get_method_description(self, method: str) -> str:
        """
        Get human-readable description of processing method

        Args:
            method: Method name

        Returns:
            Description string
        """
        descriptions = {
            "spectral_subtraction": "Spectral Subtraction (fast, for light noise)",
            "wiener_filter": "Wiener Filter (moderate complexity, for medium noise)",
            "deepfilternet_required": "DeepFilterNet required (heavy noise detected)",
        }

        return descriptions.get(method, "Unknown method")
