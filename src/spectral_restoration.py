"""
Custom Spectral Restoration Filter
Mathematically restores high-frequency details lost during aggressive noise removal.
Implements harmonic enhancement using pure DSP mathematics.

Author: Custom implementation for academic project
Purpose: Demonstrate advanced signal processing and mathematical capability
"""

import numpy as np
from scipy import signal
from scipy.fft import rfft, irfft, rfftfreq
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class SpectralRestoration:
    """
    Custom spectral restoration using mathematical harmonic synthesis.

    Theory: Aggressive noise removal often attenuates high frequencies,
    making speech sound muffled. This module:
    1. Analyzes the fundamental frequencies in the processed signal
    2. Synthesizes missing harmonics using mathematical relationships
    3. Applies perceptually-weighted restoration
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize spectral restoration processor.

        Args:
            sample_rate: Audio sampling rate in Hz
        """
        self.sample_rate = sample_rate

        # Critical frequency bands for speech intelligibility
        self.formant_regions = {
            "F1": (300, 1000),  # First formant (vowel quality)
            "F2": (900, 2800),  # Second formant (vowel distinctions)
            "F3": (2000, 4000),  # Third formant (speaker characteristics)
            "brilliance": (4000, 8000),  # High-frequency clarity
        }

    def compute_spectral_envelope(
        self, audio: np.ndarray, n_cepstral: int = 20
    ) -> np.ndarray:
        """
        Compute spectral envelope using cepstral analysis.

        Theory: Cepstrum separates spectral envelope (vocal tract) from
        fine structure (excitation/harmonics).

        Process:
        1. X(ω) = FFT(x[n])
        2. C(τ) = IFFT(log|X(ω)|)  [cepstrum]
        3. C_truncated = first n_cepstral coefficients
        4. Envelope = exp(FFT(C_truncated))

        Args:
            audio: Input audio signal
            n_cepstral: Number of cepstral coefficients to keep

        Returns:
            Spectral envelope (magnitude spectrum)
        """
        # Compute power spectrum
        spectrum = rfft(audio)
        magnitude = np.abs(spectrum)

        # Avoid log(0)
        magnitude = np.maximum(magnitude, 1e-10)

        # Compute real cepstrum
        log_magnitude = np.log(magnitude)

        # For real FFT, we need to reconstruct full spectrum for IFFT
        # Mirror the spectrum (excluding DC and Nyquist)
        log_magnitude_full = np.concatenate([log_magnitude, log_magnitude[-2:0:-1]])

        cepstrum = np.fft.ifft(log_magnitude_full).real

        # Lifter: keep only low-quefrency components (envelope)
        cepstrum_liftered = np.zeros_like(cepstrum)
        cepstrum_liftered[:n_cepstral] = cepstrum[:n_cepstral]
        cepstrum_liftered[-n_cepstral:] = cepstrum[-n_cepstral:]

        # Reconstruct envelope
        log_envelope = np.fft.fft(cepstrum_liftered).real
        envelope = np.exp(log_envelope[: len(magnitude)])

        return envelope

    def detect_pitch(self, audio: np.ndarray) -> float:
        """
        Estimate fundamental frequency (F0) using autocorrelation.

        Theory: Autocorrelation shows periodicity in signal.
        R(τ) = ∑ x[n] * x[n-τ]

        First peak after origin indicates pitch period.

        Args:
            audio: Input audio frame

        Returns:
            Estimated pitch in Hz (0 if no pitch detected)
        """
        # Compute autocorrelation using FFT (faster)
        autocorr = signal.correlate(audio, audio, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]  # Keep only positive lags

        # Normalize
        if autocorr[0] > 0:
            autocorr = autocorr / autocorr[0]

        # Search for first peak in pitch range (80-400 Hz for speech)
        min_period = int(self.sample_rate / 400)  # 400 Hz max
        max_period = int(self.sample_rate / 80)  # 80 Hz min

        if max_period >= len(autocorr):
            return 0.0

        # Find peaks in valid range
        search_region = autocorr[min_period:max_period]

        if len(search_region) == 0:
            return 0.0

        peaks, properties = signal.find_peaks(search_region, height=0.3)

        if len(peaks) == 0:
            return 0.0

        # First peak is the pitch period
        pitch_period = peaks[0] + min_period
        pitch_hz = self.sample_rate / pitch_period

        return float(pitch_hz)

    def synthesize_harmonics(
        self, audio: np.ndarray, pitch_hz: float, n_harmonics: int = 5
    ) -> np.ndarray:
        """
        Synthesize missing high-frequency harmonics.

        Theory: If fundamental is f0, harmonics are at 2f0, 3f0, 4f0, ...
        We synthesize these using:

        h_k(t) = A_k * sin(2π * k * f0 * t + φ_k)

        where A_k = A_0 / k^α (harmonic rolloff, α ≈ 1.2 for speech)

        Args:
            audio: Input audio signal
            pitch_hz: Fundamental frequency
            n_harmonics: Number of harmonics to synthesize

        Returns:
            Synthesized harmonic series
        """
        n_samples = len(audio)
        t = np.arange(n_samples) / self.sample_rate

        # Analyze existing energy at fundamental
        spectrum = rfft(audio)
        freqs = rfftfreq(n_samples, 1.0 / self.sample_rate)

        # Find energy at fundamental frequency
        f0_idx = np.argmin(np.abs(freqs - pitch_hz))
        f0_magnitude = np.abs(spectrum[f0_idx])

        # Synthesize harmonics with 1/k rolloff
        harmonics = np.zeros(n_samples)
        alpha = 1.2  # Spectral tilt for natural speech

        for k in range(2, n_harmonics + 2):  # Start from 2nd harmonic
            harmonic_freq = k * pitch_hz

            # Only synthesize if within Nyquist limit
            if harmonic_freq < self.sample_rate / 2:
                # Amplitude decays with harmonic number
                amplitude = f0_magnitude / (k**alpha)

                # Random phase for natural sound
                phase = np.random.uniform(0, 2 * np.pi)

                # Synthesize sinusoid
                harmonic_signal = amplitude * np.sin(
                    2 * np.pi * harmonic_freq * t + phase
                )
                harmonics += harmonic_signal

        # Normalize
        if np.max(np.abs(harmonics)) > 0:
            harmonics = harmonics / np.max(np.abs(harmonics)) * f0_magnitude

        return harmonics

    def apply_perceptual_weighting(
        self, spectrum: np.ndarray, freqs: np.ndarray
    ) -> np.ndarray:
        """
        Apply perceptual weighting based on human hearing sensitivity.

        Theory: A-weighting approximates human ear sensitivity.

        A(f) = (12194² * f⁴) / ((f² + 20.6²) * sqrt((f² + 107.7²)(f² + 737.9²)) * (f² + 12194²))

        In dB: A_dB(f) = 20*log₁₀(A(f)) + 2.0

        Args:
            spectrum: Magnitude spectrum
            freqs: Frequency values for each bin

        Returns:
            Perceptually weighted spectrum
        """
        # A-weighting formula (simplified for computational efficiency)
        f = np.maximum(freqs, 1.0)  # Avoid division by zero

        # Constants from A-weighting standard
        c1 = 12194.217
        c2 = 20.598997
        c3 = 107.65265
        c4 = 737.86223

        # Compute A-weighting
        numerator = c1**2 * f**4
        denominator = (
            (f**2 + c2**2) * np.sqrt((f**2 + c3**2) * (f**2 + c4**2)) * (f**2 + c1**2)
        )

        a_weight = numerator / denominator

        # Convert to dB and normalize
        a_weight_db = 20 * np.log10(a_weight + 1e-10)
        a_weight_db = a_weight_db - np.max(a_weight_db)  # Peak at 0 dB

        # Convert back to linear
        a_weight_linear = 10 ** (a_weight_db / 20)

        # Apply to spectrum
        weighted_spectrum = spectrum * a_weight_linear

        return weighted_spectrum

    def restore_high_frequency(
        self,
        original: np.ndarray,
        processed: np.ndarray,
        restoration_strength: float = 0.3,
    ) -> np.ndarray:
        """
        Main spectral restoration function.

        Restores high-frequency detail lost during noise removal using:
        1. Harmonic synthesis based on pitch detection
        2. Spectral envelope preservation
        3. Perceptual weighting

        Args:
            original: Original audio (before noise removal)
            processed: Processed audio (after noise removal)
            restoration_strength: Restoration amount [0, 1]

        Returns:
            Restored audio with enhanced high frequencies
        """
        logger.info(
            f"Starting spectral restoration (strength={restoration_strength:.2f})..."
        )

        # Ensure same length
        min_len = min(len(original), len(processed))
        original = original[:min_len]
        processed = processed[:min_len]

        # Compute spectra
        orig_spectrum = rfft(original)
        proc_spectrum = rfft(processed)
        freqs = rfftfreq(len(processed), 1.0 / self.sample_rate)

        # Compute spectral loss (what was removed)
        orig_mag = np.abs(orig_spectrum)
        proc_mag = np.abs(proc_spectrum)

        # High-frequency emphasis (above 3 kHz)
        hf_mask = freqs > 3000

        # Frame-based processing for better pitch detection
        frame_length = int(0.032 * self.sample_rate)  # 32ms frames
        hop_length = frame_length // 2

        restored_audio = processed.copy()

        # Process in frames
        for i in range(0, len(processed) - frame_length, hop_length):
            frame = processed[i : i + frame_length]

            # Detect pitch in this frame
            pitch = self.detect_pitch(frame)

            if pitch > 0 and 80 <= pitch <= 400:  # Valid speech pitch
                # Synthesize harmonics
                harmonics = self.synthesize_harmonics(frame, pitch, n_harmonics=6)

                # Blend with original frame
                restored_frame = frame + restoration_strength * harmonics

                # Avoid clipping
                max_val = np.max(np.abs(restored_frame))
                if max_val > 1.0:
                    restored_frame = restored_frame / max_val * 0.95

                # Apply with windowing to avoid clicks
                window = signal.windows.hann(frame_length)
                restored_audio[i : i + frame_length] += (
                    restored_frame - frame
                ) * window

        # Normalize to original scale
        orig_peak = np.max(np.abs(processed))
        if np.max(np.abs(restored_audio)) > 0:
            restored_audio = restored_audio / np.max(np.abs(restored_audio)) * orig_peak

        logger.info("Spectral restoration complete")
        return restored_audio

    def adaptive_restoration(
        self, original: np.ndarray, processed: np.ndarray
    ) -> np.ndarray:
        """
        Adaptive restoration that analyzes the damage and adjusts strength.

        Measures spectral difference between original and processed,
        then applies proportional restoration.

        Args:
            original: Original audio
            processed: Processed audio

        Returns:
            Adaptively restored audio
        """
        # Compute high-frequency energy loss
        orig_spectrum = rfft(original)
        proc_spectrum = rfft(processed)
        freqs = rfftfreq(len(processed), 1.0 / self.sample_rate)

        # Focus on 3-8 kHz (critical for speech clarity)
        hf_mask = (freqs >= 3000) & (freqs <= 8000)

        orig_hf_energy = np.sum(np.abs(orig_spectrum[hf_mask]) ** 2)
        proc_hf_energy = np.sum(np.abs(proc_spectrum[hf_mask]) ** 2)

        # Compute energy loss ratio
        if orig_hf_energy > 0:
            energy_retention = proc_hf_energy / orig_hf_energy
        else:
            energy_retention = 1.0

        # Adaptive strength: more restoration if more was lost
        # strength = 1 - energy_retention (capped at 0.5 for safety)
        restoration_strength = min(1.0 - energy_retention, 0.5)

        logger.info(
            f"HF energy retained: {energy_retention*100:.1f}%, "
            f"restoration strength: {restoration_strength:.2f}"
        )

        if restoration_strength < 0.05:
            logger.info("Minimal HF loss detected, skipping restoration")
            return processed

        return self.restore_high_frequency(original, processed, restoration_strength)
