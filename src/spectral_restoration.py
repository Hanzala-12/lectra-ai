"""
Spectral Restoration Module
Restores high-frequency content lost during aggressive noise removal
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, ifft, rfft, irfft
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class SpectralRestoration:
    """
    Restores spectral content using cepstral analysis and harmonic synthesis

    Features:
    - Cepstral separation of voice and noise
    - Autocorrelation-based pitch detection
    - Harmonic synthesis for frequency regeneration
    - Adaptive restoration strength control
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize spectral restoration

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.frame_length = 1024
        self.hop_length = 256
        self.n_harmonics = 5  # Number of harmonics to synthesize

    def adaptive_restoration(
        self,
        original_audio: np.ndarray,
        denoised_audio: np.ndarray,
        strength: str = "auto",
    ) -> np.ndarray:
        """
        Apply adaptive spectral restoration

        Args:
            original_audio: Original noisy audio
            denoised_audio: Denoised audio (may have lost high frequencies)
            strength: Restoration strength ('auto', 'light', 'medium', 'heavy')

        Returns:
            Enhanced audio with restored spectral content
        """
        # Ensure same length
        min_len = min(len(original_audio), len(denoised_audio))
        original = original_audio[:min_len].astype(np.float64)
        denoised = denoised_audio[:min_len].astype(np.float64)

        # Determine restoration strength
        if strength == "auto":
            strength_value = self._estimate_restoration_strength(original, denoised)
        else:
            strength_map = {"light": 0.3, "medium": 0.5, "heavy": 0.7}
            strength_value = strength_map.get(strength, 0.5)

        logger.info(f"Applying spectral restoration with strength={strength_value:.2f}")

        # Detect pitch for harmonic synthesis
        pitch = self._detect_pitch(denoised)

        if pitch is None or pitch < 50 or pitch > 500:
            # No valid pitch detected - use spectral envelope restoration only
            logger.info("No valid pitch detected, using envelope restoration")
            restored = self._restore_spectral_envelope(
                original, denoised, strength_value
            )
        else:
            # Valid pitch - use harmonic synthesis
            logger.info(f"Detected pitch: {pitch:.1f} Hz")
            restored = self._restore_with_harmonics(
                original, denoised, pitch, strength_value
            )

        return restored

    def _estimate_restoration_strength(
        self, original: np.ndarray, denoised: np.ndarray
    ) -> float:
        """
        Estimate optimal restoration strength based on spectral loss

        Returns:
            Strength value between 0 and 1
        """
        # Compute spectrograms
        f_orig, t_orig, Sxx_orig = signal.spectrogram(
            original,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        f_den, t_den, Sxx_den = signal.spectrogram(
            denoised,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Focus on high frequencies (> 2kHz)
        high_freq_idx = f_orig > 2000

        # Compute energy loss in high frequencies
        orig_high_energy = np.mean(Sxx_orig[high_freq_idx, :])
        den_high_energy = np.mean(Sxx_den[high_freq_idx, :])

        if orig_high_energy < 1e-10:
            return 0.3  # Default light restoration

        energy_loss_ratio = 1 - (den_high_energy / orig_high_energy)

        # Map loss ratio to strength (0.2 to 0.8)
        strength = np.clip(0.2 + energy_loss_ratio * 0.6, 0.2, 0.8)

        return float(strength)

    def _detect_pitch(self, audio: np.ndarray) -> Optional[float]:
        """
        Detect fundamental frequency using autocorrelation

        Args:
            audio: Input audio

        Returns:
            Pitch in Hz, or None if not detected
        """
        # Use middle portion of audio for pitch detection
        mid_start = len(audio) // 4
        mid_end = 3 * len(audio) // 4
        audio_segment = audio[mid_start:mid_end]

        # Compute autocorrelation
        autocorr = np.correlate(audio_segment, audio_segment, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        # Normalize
        autocorr = autocorr / autocorr[0]

        # Find peaks in autocorrelation
        # Search in typical pitch range: 50-500 Hz
        min_lag = int(self.sample_rate / 500)  # Max 500 Hz
        max_lag = int(self.sample_rate / 50)  # Min 50 Hz

        # Find first peak after minimum lag
        search_region = autocorr[min_lag:max_lag]

        if len(search_region) == 0:
            return None

        # Find peaks
        peaks, properties = signal.find_peaks(search_region, height=0.3)

        if len(peaks) == 0:
            return None

        # Use highest peak
        best_peak_idx = peaks[np.argmax(properties["peak_heights"])]
        lag = min_lag + best_peak_idx

        # Convert lag to frequency
        pitch = self.sample_rate / lag

        return float(pitch)

    def _restore_with_harmonics(
        self, original: np.ndarray, denoised: np.ndarray, pitch: float, strength: float
    ) -> np.ndarray:
        """
        Restore using harmonic synthesis

        Args:
            original: Original audio
            denoised: Denoised audio
            pitch: Detected pitch in Hz
            strength: Restoration strength (0-1)

        Returns:
            Restored audio
        """
        # Compute STFT of denoised audio
        f, t, Zxx = signal.stft(
            denoised,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Synthesize harmonics
        harmonic_freqs = [pitch * (i + 1) for i in range(self.n_harmonics)]

        # Add harmonic energy to STFT
        for harm_freq in harmonic_freqs:
            if harm_freq > self.sample_rate / 2:
                break

            # Find frequency bin
            freq_bin = int(harm_freq * self.frame_length / self.sample_rate)

            if freq_bin < len(f):
                # Add harmonic energy (scaled by strength)
                Zxx[freq_bin, :] += strength * 0.1 * np.abs(Zxx[freq_bin, :])

        # Inverse STFT
        _, restored = signal.istft(
            Zxx,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Ensure same length as input
        restored = restored[: len(denoised)]

        # Blend with denoised audio
        alpha = strength * 0.5  # Blend factor
        restored = (1 - alpha) * denoised + alpha * restored

        return restored.astype(np.float32)

    def _restore_spectral_envelope(
        self, original: np.ndarray, denoised: np.ndarray, strength: float
    ) -> np.ndarray:
        """
        Restore spectral envelope using cepstral analysis

        Args:
            original: Original audio
            denoised: Denoised audio
            strength: Restoration strength (0-1)

        Returns:
            Restored audio
        """
        # Compute STFTs
        f_orig, t_orig, Zxx_orig = signal.stft(
            original,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        f_den, t_den, Zxx_den = signal.stft(
            denoised,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Extract spectral envelopes using cepstral smoothing
        envelope_orig = self._extract_spectral_envelope(Zxx_orig)
        envelope_den = self._extract_spectral_envelope(Zxx_den)

        # Compute envelope difference (what was lost)
        envelope_diff = envelope_orig - envelope_den

        # Apply restoration (add back some of the lost envelope)
        Zxx_restored = Zxx_den * (1 + strength * envelope_diff)

        # Inverse STFT
        _, restored = signal.istft(
            Zxx_restored,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Ensure same length
        restored = restored[: len(denoised)]

        return restored.astype(np.float32)

    def _extract_spectral_envelope(self, Zxx: np.ndarray) -> np.ndarray:
        """
        Extract spectral envelope using cepstral smoothing

        Args:
            Zxx: STFT matrix

        Returns:
            Smoothed spectral envelope
        """
        magnitude = np.abs(Zxx) + 1e-10

        # Compute cepstrum for each frame
        n_frames = magnitude.shape[1]
        envelope = np.zeros_like(magnitude)

        for i in range(n_frames):
            # Log magnitude spectrum
            log_mag = np.log(magnitude[:, i])

            # Compute cepstrum
            cepstrum = np.real(ifft(log_mag))

            # Lifter (keep only low quefrency components for envelope)
            lifter_len = 20
            cepstrum[lifter_len:-lifter_len] = 0

            # Back to spectrum
            envelope[:, i] = np.exp(np.real(fft(cepstrum)))

        return envelope
