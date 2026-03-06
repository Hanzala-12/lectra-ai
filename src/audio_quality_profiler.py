"""
Custom Audio Quality Profiler
Analyzes input audio characteristics using pure mathematical signal processing.
This module provides intelligent input profiling for adaptive noise removal routing.

Author: Custom implementation for academic project
Purpose: Demonstrate mathematical signal processing capability
"""

import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioQualityProfiler:
    """
    Custom-built audio quality analyzer using raw DSP mathematics.
    Profiles noise characteristics, frequency spectrum, and signal quality
    WITHOUT relying on pre-built ML models.
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize profiler with sample rate.

        Args:
            sample_rate: Audio sampling rate in Hz
        """
        self.sample_rate = sample_rate

        # Define frequency bands for analysis (Hz)
        self.freq_bands = {
            "sub_bass": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "upper_mid": (2000, 4000),
            "presence": (4000, 6000),
            "brilliance": (6000, sample_rate // 2),
        }

    def compute_noise_variance(self, audio: np.ndarray) -> float:
        """
        Estimate noise variance using Median Absolute Deviation (MAD).

        Theory: In a noisy signal, the high-frequency wavelet coefficients
        are dominated by noise. MAD provides a robust noise estimate.

        σ_noise = MAD(HH₁) / 0.6745

        where HH₁ are the finest-scale wavelet detail coefficients.

        Args:
            audio: Input audio signal

        Returns:
            Estimated noise variance (σ²)
        """
        # Compute discrete wavelet transform (Haar wavelet - simplest case)
        # Split signal into approximation (low-freq) and detail (high-freq)
        length = len(audio)
        if length < 2:
            return 0.0

        # Level 1 Haar decomposition (manual implementation)
        # Approximation: (x[n] + x[n+1]) / sqrt(2)
        # Detail: (x[n] - x[n+1]) / sqrt(2)

        # Ensure even length
        if length % 2 != 0:
            audio = audio[:-1]
            length -= 1

        # Reshape for paired processing
        pairs = audio.reshape(-1, 2)
        detail_coeffs = (pairs[:, 0] - pairs[:, 1]) / np.sqrt(2)

        # Compute MAD (Median Absolute Deviation)
        median = np.median(detail_coeffs)
        mad = np.median(np.abs(detail_coeffs - median))

        # Scale by 0.6745 to estimate standard deviation for Gaussian noise
        sigma_noise = mad / 0.6745
        noise_variance = sigma_noise**2

        logger.debug(f"Estimated noise variance: {noise_variance:.6f}")
        return float(noise_variance)

    def compute_snr_estimate(self, audio: np.ndarray) -> float:
        """
        Estimate Signal-to-Noise Ratio using energy-based segmentation.

        Theory: Divide audio into frames, sort by energy. Assume top 60%
        are signal-dominant, bottom 20% are noise-dominant.

        SNR_dB = 10 * log₁₀(P_signal / P_noise)

        Args:
            audio: Input audio signal

        Returns:
            SNR estimate in dB
        """
        frame_length = int(0.025 * self.sample_rate)  # 25ms frames
        hop_length = frame_length // 2

        # Compute frame energies
        frame_energies = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i : i + frame_length]
            energy = np.sum(frame**2)
            frame_energies.append(energy)

        if len(frame_energies) < 10:
            return 0.0

        energies = np.array(frame_energies)
        energies_sorted = np.sort(energies)

        # Bottom 20% = noise estimate
        noise_threshold_idx = int(0.2 * len(energies_sorted))
        noise_power = np.mean(energies_sorted[:noise_threshold_idx])

        # Top 60% = signal estimate
        signal_start_idx = int(0.4 * len(energies_sorted))
        signal_power = np.mean(energies_sorted[signal_start_idx:])

        # Compute SNR in dB
        if noise_power > 0 and signal_power > 0:
            snr_db = 10 * np.log10(signal_power / noise_power)
        else:
            snr_db = -np.inf

        logger.debug(f"Estimated SNR: {snr_db:.2f} dB")
        return float(snr_db)

    def compute_spectral_flatness(self, audio: np.ndarray) -> float:
        """
        Wiener Entropy (Spectral Flatness Measure).

        Theory: Ratio of geometric mean to arithmetic mean of power spectrum.

        SFM = (∏|X[k]|)^(1/N) / (1/N ∑|X[k]|)

        SFM ≈ 1: noise-like (flat spectrum)
        SFM ≈ 0: tonal (peaky spectrum)

        Args:
            audio: Input audio signal

        Returns:
            Spectral flatness measure [0, 1]
        """
        # Compute power spectrum using FFT
        fft_vals = rfft(audio)
        power_spectrum = np.abs(fft_vals) ** 2

        # Avoid log(0) issues
        power_spectrum = power_spectrum + 1e-10

        # Geometric mean
        geo_mean = np.exp(np.mean(np.log(power_spectrum)))

        # Arithmetic mean
        arith_mean = np.mean(power_spectrum)

        # Spectral flatness
        sfm = geo_mean / arith_mean if arith_mean > 0 else 0.0

        logger.debug(f"Spectral flatness: {sfm:.4f}")
        return float(sfm)

    def compute_frequency_spectrum(self, audio: np.ndarray) -> Dict[str, float]:
        """
        Analyze energy distribution across frequency bands.

        Theory: Apply FFT and integrate power within defined bands.

        E_band = ∫_{f1}^{f2} |X(f)|² df

        Args:
            audio: Input audio signal

        Returns:
            Dictionary mapping band name to energy percentage
        """
        # Compute FFT
        fft_vals = rfft(audio)
        frequencies = rfftfreq(len(audio), 1.0 / self.sample_rate)
        power_spectrum = np.abs(fft_vals) ** 2

        # Compute energy in each band
        band_energies = {}
        total_energy = np.sum(power_spectrum)

        if total_energy == 0:
            return {band: 0.0 for band in self.freq_bands.keys()}

        for band_name, (f_low, f_high) in self.freq_bands.items():
            # Find frequency bins in this band
            mask = (frequencies >= f_low) & (frequencies < f_high)
            band_energy = np.sum(power_spectrum[mask])
            band_energies[band_name] = float(band_energy / total_energy * 100)

        logger.debug(f"Frequency spectrum: {band_energies}")
        return band_energies

    def compute_zero_crossing_rate(self, audio: np.ndarray) -> float:
        """
        Zero Crossing Rate - measures frequency content.

        Theory: Count sign changes in the signal.

        ZCR = (1 / 2N) ∑ |sign(x[n]) - sign(x[n-1])|

        High ZCR → high frequency / noisy content
        Low ZCR → low frequency / tonal content

        Args:
            audio: Input audio signal

        Returns:
            Zero crossing rate (crossings per sample)
        """
        # Count zero crossings
        signs = np.sign(audio)
        signs[signs == 0] = 1  # Treat zero as positive
        crossings = np.abs(np.diff(signs))
        zcr = np.sum(crossings) / (2 * len(audio))

        logger.debug(f"Zero crossing rate: {zcr:.4f}")
        return float(zcr)

    def compute_crest_factor(self, audio: np.ndarray) -> float:
        """
        Crest Factor - ratio of peak to RMS value.

        Theory:
        CF = |x|_peak / x_RMS

        High CF → high dynamic range (speech)
        Low CF → compressed/heavily processed (noise)

        Args:
            audio: Input audio signal

        Returns:
            Crest factor in dB
        """
        peak = np.max(np.abs(audio))
        rms = np.sqrt(np.mean(audio**2))

        if rms > 0:
            crest_factor_db = 20 * np.log10(peak / rms)
        else:
            crest_factor_db = 0.0

        logger.debug(f"Crest factor: {crest_factor_db:.2f} dB")
        return float(crest_factor_db)

    def profile_audio(self, audio: np.ndarray) -> Dict[str, any]:
        """
        Comprehensive audio quality profiling.

        Combines all mathematical metrics to create a complete profile
        of the input audio characteristics.

        Args:
            audio: Input audio signal (mono, float32)

        Returns:
            Dictionary containing all computed metrics and quality assessment
        """
        logger.info("Starting comprehensive audio quality profiling...")

        # Compute all metrics
        noise_variance = self.compute_noise_variance(audio)
        snr_estimate = self.compute_snr_estimate(audio)
        spectral_flatness = self.compute_spectral_flatness(audio)
        frequency_spectrum = self.compute_frequency_spectrum(audio)
        zcr = self.compute_zero_crossing_rate(audio)
        crest_factor = self.compute_crest_factor(audio)

        # Derive quality classifications
        # Heavy noise: SNR < 10 dB or high noise variance
        is_heavy_noise = snr_estimate < 10.0 or noise_variance > 0.05

        # Noisy spectrum: high spectral flatness (noise-like)
        is_noisy_spectrum = spectral_flatness > 0.5

        # Voice activity confidence (high mid-range energy + moderate ZCR)
        mid_energy_pct = frequency_spectrum.get("mid", 0) + frequency_spectrum.get(
            "upper_mid", 0
        )
        has_voice_characteristics = mid_energy_pct > 30 and 0.1 < zcr < 0.3

        # Recommended processing level
        if is_heavy_noise:
            processing_level = "aggressive"
        elif snr_estimate > 20.0:
            processing_level = "light"
        else:
            processing_level = "moderate"

        profile = {
            "noise_variance": noise_variance,
            "snr_db": snr_estimate,
            "spectral_flatness": spectral_flatness,
            "frequency_spectrum": frequency_spectrum,
            "zero_crossing_rate": zcr,
            "crest_factor_db": crest_factor,
            "classifications": {
                "is_heavy_noise": is_heavy_noise,
                "is_noisy_spectrum": is_noisy_spectrum,
                "has_voice_characteristics": has_voice_characteristics,
            },
            "recommended_processing": processing_level,
            "duration_seconds": len(audio) / self.sample_rate,
            "sample_rate": self.sample_rate,
        }

        logger.info(
            f"Audio profile complete: SNR={snr_estimate:.1f}dB, "
            f"Processing={processing_level}, Voice={has_voice_characteristics}"
        )

        return profile

    def should_use_heavy_processing(self, profile: Dict) -> bool:
        """
        Intelligent routing decision based on profile.

        Returns True if heavy processing (DeepFilterNet) is needed,
        False if lightweight custom filtering is sufficient.

        Args:
            profile: Audio profile dictionary

        Returns:
            Boolean decision
        """
        # Use heavy processing if:
        # 1. Heavy noise detected, OR
        # 2. Low SNR, OR
        # 3. Noisy spectrum AND voice present

        heavy_noise = profile["classifications"]["is_heavy_noise"]
        low_snr = profile["snr_db"] < 15.0
        noisy_with_voice = (
            profile["classifications"]["is_noisy_spectrum"]
            and profile["classifications"]["has_voice_characteristics"]
        )

        return heavy_noise or low_snr or noisy_with_voice
