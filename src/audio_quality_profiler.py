"""
Audio Quality Profiler Module
Analyzes input audio characteristics before processing
"""

import numpy as np
from scipy import signal
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Optional: PyWavelets for wavelet-based noise estimation
try:
    import pywt

    PYWT_AVAILABLE = True
except ImportError:
    PYWT_AVAILABLE = False
    logger.warning("PyWavelets not available - wavelet analysis disabled")


class AudioQualityProfiler:
    """
    Analyzes audio quality characteristics for optimal processing selection

    Features:
    - Wavelet-based noise estimation (if pywt available)
    - SNR calculation
    - Spectral flatness and rolloff
    - Zero-crossing rate
    - Dominant frequency identification
    """

    def __init__(self, sample_rate: int = 16000, wavelet: str = "db8"):
        """
        Initialize profiler

        Args:
            sample_rate: Audio sample rate in Hz
            wavelet: Wavelet type for decomposition (default: Daubechies 8)
        """
        self.sample_rate = sample_rate
        self.wavelet = wavelet
        self.frame_length = int(0.032 * sample_rate)  # 32ms frames
        self.hop_length = int(0.016 * sample_rate)  # 16ms hop

    def profile_audio(
        self, audio: np.ndarray, sample_rate: Optional[int] = None
    ) -> Dict[str, float]:
        """
        Analyze audio and return quality profile

        Args:
            audio: Input audio (1D array, mono)
            sample_rate: Sample rate (uses instance default if None)

        Returns:
            Dictionary with profile metrics including:
            - snr_db: Estimated signal-to-noise ratio
            - noise_floor_db: Estimated noise floor level
            - spectral_flatness: Tonality measure (0=tonal, 1=noisy)
            - spectral_rolloff: Frequency below which 85% of energy
            - zero_crossing_rate: Signal irregularity measure
            - dominant_frequency: Peak frequency in Hz
            - recommended_processing: 'light', 'medium', or 'heavy'
        """
        if sample_rate is not None:
            self.sample_rate = sample_rate

        audio = audio.astype(np.float64)

        # Compute all features
        profile = {}

        # Wavelet-based noise estimation
        if PYWT_AVAILABLE:
            profile["noise_floor_db"] = self._estimate_noise_wavelet(audio)
        else:
            profile["noise_floor_db"] = self._estimate_noise_simple(audio)

        # SNR estimation
        profile["snr_db"] = self._estimate_snr(audio, profile["noise_floor_db"])

        # Spectral features
        profile["spectral_flatness"] = self._compute_spectral_flatness(audio)
        profile["spectral_rolloff"] = self._compute_spectral_rolloff(audio)

        # Temporal features
        profile["zero_crossing_rate"] = self._compute_zero_crossing_rate(audio)
        profile["dominant_frequency"] = self._compute_dominant_frequency(audio)

        # Recommend processing level
        profile["recommended_processing"] = self._recommend_processing(profile)

        logger.info(
            f"Audio profile: SNR={profile['snr_db']:.1f}dB, "
            f"Recommended={profile['recommended_processing']}"
        )

        return profile

    def _estimate_noise_wavelet(self, audio: np.ndarray) -> float:
        """
        Estimate noise floor using wavelet decomposition

        Uses median absolute deviation (MAD) of detail coefficients
        """
        # Decompose signal using wavelet transform
        coeffs = pywt.wavedec(audio, self.wavelet, level=3)

        # Use highest frequency detail coefficients (most noise)
        detail_coeffs = coeffs[-1]

        # Robust noise estimation using MAD
        sigma = np.median(np.abs(detail_coeffs)) / 0.6745

        # Convert to dB
        noise_floor_db = 20 * np.log10(sigma + 1e-10)

        return float(noise_floor_db)

    def _estimate_noise_simple(self, audio: np.ndarray) -> float:
        """
        Simple noise floor estimation (fallback when pywt unavailable)

        Uses minimum energy frames as noise estimate
        """
        n_frames = (len(audio) - self.frame_length) // self.hop_length + 1
        frame_energies = []

        for i in range(n_frames):
            start = i * self.hop_length
            end = start + self.frame_length
            frame = audio[start:end]
            energy = np.sqrt(np.mean(frame**2))
            frame_energies.append(energy)

        # Use 10th percentile as noise floor estimate
        noise_floor = np.percentile(frame_energies, 10)
        noise_floor_db = 20 * np.log10(noise_floor + 1e-10)

        return float(noise_floor_db)

    def _estimate_snr(self, audio: np.ndarray, noise_floor_db: float) -> float:
        """
        Estimate signal-to-noise ratio

        Args:
            audio: Input audio
            noise_floor_db: Estimated noise floor in dB

        Returns:
            SNR in dB
        """
        # Signal power (RMS of entire signal)
        signal_rms = np.sqrt(np.mean(audio**2))
        signal_db = 20 * np.log10(signal_rms + 1e-10)

        # SNR = signal level - noise floor
        snr_db = signal_db - noise_floor_db

        return float(snr_db)

    def _compute_spectral_flatness(self, audio: np.ndarray) -> float:
        """
        Compute spectral flatness (Wiener entropy)

        Measures how tone-like (0) vs noise-like (1) the signal is
        """
        # Compute power spectrum
        f, Pxx = signal.periodogram(audio, fs=self.sample_rate)

        # Avoid log(0)
        Pxx = Pxx + 1e-10

        # Spectral flatness = geometric mean / arithmetic mean
        geometric_mean = np.exp(np.mean(np.log(Pxx)))
        arithmetic_mean = np.mean(Pxx)

        flatness = geometric_mean / arithmetic_mean

        return float(flatness)

    def _compute_spectral_rolloff(self, audio: np.ndarray) -> float:
        """
        Compute spectral rolloff frequency

        Frequency below which 85% of spectral energy is contained
        """
        # Compute power spectrum
        f, Pxx = signal.periodogram(audio, fs=self.sample_rate)

        # Cumulative energy
        cumulative_energy = np.cumsum(Pxx)
        total_energy = cumulative_energy[-1]

        # Find frequency where 85% of energy is reached
        threshold = 0.85 * total_energy
        rolloff_idx = np.where(cumulative_energy >= threshold)[0][0]
        rolloff_freq = f[rolloff_idx]

        return float(rolloff_freq)

    def _compute_zero_crossing_rate(self, audio: np.ndarray) -> float:
        """
        Compute zero-crossing rate

        Measures signal irregularity (higher = more noisy/irregular)
        """
        # Count sign changes
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio)))) / 2

        # Normalize by length
        zcr = zero_crossings / len(audio)

        return float(zcr)

    def _compute_dominant_frequency(self, audio: np.ndarray) -> float:
        """
        Find dominant frequency using FFT

        Returns:
            Dominant frequency in Hz
        """
        # Compute FFT
        fft_vals = np.fft.rfft(audio)
        fft_freqs = np.fft.rfftfreq(len(audio), 1.0 / self.sample_rate)

        # Find peak
        magnitude = np.abs(fft_vals)
        peak_idx = np.argmax(magnitude)
        dominant_freq = fft_freqs[peak_idx]

        return float(dominant_freq)

    def _recommend_processing(self, profile: Dict[str, float]) -> str:
        """
        Recommend processing level based on profile

        Args:
            profile: Audio profile dictionary

        Returns:
            'light', 'medium', or 'heavy'
        """
        snr = profile["snr_db"]
        flatness = profile["spectral_flatness"]

        # Decision logic based on SNR and spectral characteristics
        if snr > 15:
            # High SNR - light processing sufficient
            return "light"
        elif snr > 5:
            # Medium SNR - moderate processing
            if flatness > 0.5:
                # Noisy spectrum - may need heavier processing
                return "medium"
            else:
                return "medium"
        else:
            # Low SNR - heavy processing needed
            return "heavy"

    def format_profile(self, profile: Dict[str, float]) -> str:
        """
        Format profile as human-readable string

        Args:
            profile: Dictionary from profile_audio()

        Returns:
            Formatted string
        """
        lines = [
            "Audio Quality Profile",
            "=" * 50,
            f"SNR:                    {profile['snr_db']:>8.2f} dB",
            f"Noise Floor:            {profile['noise_floor_db']:>8.2f} dB",
            f"Spectral Flatness:      {profile['spectral_flatness']:>8.4f}",
            f"Spectral Rolloff:       {profile['spectral_rolloff']:>8.1f} Hz",
            f"Zero-Crossing Rate:     {profile['zero_crossing_rate']:>8.4f}",
            f"Dominant Frequency:     {profile['dominant_frequency']:>8.1f} Hz",
            "=" * 50,
            f"Recommended Processing: {profile['recommended_processing'].upper()}",
        ]

        return "\n".join(lines)
