"""
Custom Audio Quality Evaluation Metrics
From-scratch implementation of audio quality metrics using pure NumPy/SciPy mathematics.
NO sklearn, NO pre-built metric libraries - only raw mathematical implementations.

Author: Custom implementation for academic project
Purpose: Demonstrate mathematical competency and understanding of signal processing theory
"""

import numpy as np
from scipy import signal
from scipy.fft import rfft, rfftfreq
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioQualityMetrics:
    """
    Custom-built evaluation metrics for noise removal assessment.
    All metrics implemented from mathematical first principles.
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize metrics calculator.

        Args:
            sample_rate: Audio sampling rate in Hz
        """
        self.sample_rate = sample_rate

    def compute_snr(self, clean_signal: np.ndarray, noisy_signal: np.ndarray) -> float:
        """
        Signal-to-Noise Ratio - fundamental quality metric.

        Theory:
        SNR_dB = 10 * log₁₀(P_signal / P_noise)

        where:
        P_signal = power of clean signal
        P_noise = power of (noisy - clean)

        Args:
            clean_signal: Reference clean audio
            noisy_signal: Noisy audio to evaluate

        Returns:
            SNR in decibels (dB)
        """
        # Ensure same length
        min_len = min(len(clean_signal), len(noisy_signal))
        clean = clean_signal[:min_len]
        noisy = noisy_signal[:min_len]

        # Compute noise signal
        noise = noisy - clean

        # Compute power (mean squared amplitude)
        signal_power = np.mean(clean**2)
        noise_power = np.mean(noise**2)

        # Handle edge cases
        if noise_power == 0:
            return float("inf")
        if signal_power == 0:
            return float("-inf")

        # Compute SNR in dB
        snr_db = 10 * np.log10(signal_power / noise_power)

        logger.debug(f"SNR: {snr_db:.2f} dB")
        return float(snr_db)

    def compute_mse(self, reference: np.ndarray, processed: np.ndarray) -> float:
        """
        Mean Squared Error - basic distortion metric.

        Theory:
        MSE = (1/N) ∑(x[n] - y[n])²

        Lower is better (0 = perfect match).

        Args:
            reference: Reference signal
            processed: Processed signal to evaluate

        Returns:
            Mean squared error
        """
        min_len = min(len(reference), len(processed))
        ref = reference[:min_len]
        proc = processed[:min_len]

        mse = np.mean((ref - proc) ** 2)

        logger.debug(f"MSE: {mse:.6f}")
        return float(mse)

    def compute_psnr(self, reference: np.ndarray, processed: np.ndarray) -> float:
        """
        Peak Signal-to-Noise Ratio - normalized quality metric.

        Theory:
        PSNR_dB = 10 * log₁₀(MAX² / MSE)

        where MAX is the maximum possible signal value.
        For normalized audio [-1, 1], MAX = 1.

        Higher is better (typical range: 20-50 dB for audio).

        Args:
            reference: Reference signal
            processed: Processed signal

        Returns:
            PSNR in decibels
        """
        mse = self.compute_mse(reference, processed)

        if mse == 0:
            return float("inf")

        # For normalized audio, peak value is 1.0
        max_value = 1.0
        psnr_db = 10 * np.log10(max_value**2 / mse)

        logger.debug(f"PSNR: {psnr_db:.2f} dB")
        return float(psnr_db)

    def compute_segmental_snr(
        self, reference: np.ndarray, processed: np.ndarray, frame_length_ms: int = 20
    ) -> float:
        """
        Segmental SNR - frame-based SNR averaging.

        Theory: Divide signal into frames, compute SNR per frame, average.

        SegSNR = (1/M) ∑ SNR_m

        where:
        SNR_m = 10 * log₁₀(∑x_m[n]² / ∑(x_m[n] - y_m[n])²)

        More robust than global SNR for non-stationary signals.

        Args:
            reference: Reference signal
            processed: Processed signal
            frame_length_ms: Frame length in milliseconds

        Returns:
            Segmental SNR in dB
        """
        frame_length = int(frame_length_ms * self.sample_rate / 1000)
        min_len = min(len(reference), len(processed))

        ref = reference[:min_len]
        proc = processed[:min_len]

        snr_values = []
        epsilon = 1e-10  # Avoid log(0)

        # Process in frames
        for i in range(0, min_len - frame_length, frame_length):
            ref_frame = ref[i : i + frame_length]
            proc_frame = proc[i : i + frame_length]

            signal_power = np.sum(ref_frame**2)
            noise_power = np.sum((ref_frame - proc_frame) ** 2)

            # Skip silent frames
            if signal_power > epsilon:
                frame_snr = 10 * np.log10(signal_power / (noise_power + epsilon))

                # Clip to reasonable range to avoid outliers skewing average
                frame_snr = np.clip(frame_snr, -20, 60)
                snr_values.append(frame_snr)

        if len(snr_values) == 0:
            return 0.0

        seg_snr = np.mean(snr_values)

        logger.debug(f"Segmental SNR: {seg_snr:.2f} dB ({len(snr_values)} frames)")
        return float(seg_snr)

    def compute_spectral_distortion(
        self, reference: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Log-Spectral Distortion - frequency domain distortion measure.

        Theory:
        LSD = sqrt((1/K) ∑ (20*log₁₀|X[k]| - 20*log₁₀|Y[k]|)²)

        Measures deviation in spectral magnitude (in dB).
        Lower is better (0 = perfect match).

        Args:
            reference: Reference signal
            processed: Processed signal

        Returns:
            Log-spectral distortion in dB
        """
        min_len = min(len(reference), len(processed))
        ref = reference[:min_len]
        proc = processed[:min_len]

        # Compute magnitude spectra
        ref_spectrum = np.abs(rfft(ref))
        proc_spectrum = np.abs(rfft(proc))

        # Avoid log(0)
        epsilon = 1e-10
        ref_spectrum = np.maximum(ref_spectrum, epsilon)
        proc_spectrum = np.maximum(proc_spectrum, epsilon)

        # Compute log-spectral distance
        log_ref = 20 * np.log10(ref_spectrum)
        log_proc = 20 * np.log10(proc_spectrum)

        lsd = np.sqrt(np.mean((log_ref - log_proc) ** 2))

        logger.debug(f"Log-Spectral Distortion: {lsd:.2f} dB")
        return float(lsd)

    def compute_itakura_saito(
        self, reference: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Itakura-Saito Distance - perceptually-motivated spectral divergence.

        Theory:
        IS(x||y) = (1/K) ∑ (|X[k]|²/|Y[k]|² - log(|X[k]|²/|Y[k]|²) - 1)

        Non-symmetric measure of spectral shape difference.
        Lower is better (0 = perfect match).

        Args:
            reference: Reference signal
            processed: Processed signal

        Returns:
            Itakura-Saito distance
        """
        min_len = min(len(reference), len(processed))
        ref = reference[:min_len]
        proc = processed[:min_len]

        # Compute power spectra
        ref_power = np.abs(rfft(ref)) ** 2
        proc_power = np.abs(rfft(proc)) ** 2

        # Avoid division by zero
        epsilon = 1e-10
        proc_power = np.maximum(proc_power, epsilon)
        ref_power = np.maximum(ref_power, epsilon)

        # Compute IS divergence
        ratio = ref_power / proc_power
        is_distance = np.mean(ratio - np.log(ratio) - 1)

        logger.debug(f"Itakura-Saito Distance: {is_distance:.4f}")
        return float(is_distance)

    def compute_waveform_similarity(
        self, reference: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Pearson Correlation Coefficient - temporal similarity.

        Theory:
        ρ = Cov(X,Y) / (σ_X * σ_Y)

        Range: [-1, 1]
        1 = perfect correlation
        0 = no correlation
        -1 = perfect anti-correlation

        Args:
            reference: Reference signal
            processed: Processed signal

        Returns:
            Correlation coefficient [0, 1]
        """
        min_len = min(len(reference), len(processed))
        ref = reference[:min_len]
        proc = processed[:min_len]

        # Compute correlation
        ref_mean = np.mean(ref)
        proc_mean = np.mean(proc)

        numerator = np.sum((ref - ref_mean) * (proc - proc_mean))
        denominator = np.sqrt(
            np.sum((ref - ref_mean) ** 2) * np.sum((proc - proc_mean) ** 2)
        )

        if denominator == 0:
            return 0.0

        correlation = numerator / denominator

        logger.debug(f"Waveform Similarity: {correlation:.4f}")
        return float(correlation)

    def compute_envelope_distance(
        self, reference: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Envelope Distance - amplitude modulation preservation.

        Theory: Extract amplitude envelopes using Hilbert transform,
        then compute normalized MSE.

        Envelope(x) = |Hilbert(x)|

        Args:
            reference: Reference signal
            processed: Processed signal

        Returns:
            Normalized envelope distance [0, ∞], lower is better
        """
        min_len = min(len(reference), len(processed))
        ref = reference[:min_len]
        proc = processed[:min_len]

        # Extract envelopes using Hilbert transform
        ref_analytic = signal.hilbert(ref)
        proc_analytic = signal.hilbert(proc)

        ref_envelope = np.abs(ref_analytic)
        proc_envelope = np.abs(proc_analytic)

        # Normalize envelopes
        if np.max(ref_envelope) > 0:
            ref_envelope = ref_envelope / np.max(ref_envelope)
        if np.max(proc_envelope) > 0:
            proc_envelope = proc_envelope / np.max(proc_envelope)

        # Compute MSE
        envelope_mse = np.mean((ref_envelope - proc_envelope) ** 2)

        logger.debug(f"Envelope Distance: {envelope_mse:.4f}")
        return float(envelope_mse)

    def compute_noise_reduction_amount(
        self,
        original_noisy: np.ndarray,
        processed: np.ndarray,
        noise_reference: np.ndarray = None,
    ) -> float:
        """
        Noise Reduction Amount - measures how much noise was removed.

        Theory:
        If noise reference is available:
            NR = 10 * log₁₀(P_noise_before / P_noise_after)

        Otherwise estimate from high-frequency energy reduction.

        Args:
            original_noisy: Original noisy signal
            processed: Processed (cleaned) signal
            noise_reference: Optional clean noise sample

        Returns:
            Noise reduction in dB (positive = noise removed)
        """
        min_len = min(len(original_noisy), len(processed))
        noisy = original_noisy[:min_len]
        clean = processed[:min_len]

        if noise_reference is not None and len(noise_reference) > 0:
            # Compute noise power in original
            noise_power_before = np.mean(noise_reference**2)

            # Estimate residual noise (difference from original)
            residual = noisy - clean
            noise_power_after = np.mean(residual**2)

            if noise_power_after > 0:
                nr_db = 10 * np.log10(noise_power_before / noise_power_after)
            else:
                nr_db = float("inf")
        else:
            # Estimate from high-frequency energy reduction (noise typically HF-dominant)
            # Compute spectra
            noisy_spectrum = np.abs(rfft(noisy))
            clean_spectrum = np.abs(rfft(clean))

            freqs = rfftfreq(len(noisy), 1.0 / self.sample_rate)

            # Focus on 4-8 kHz (high for speech, typical for noise)
            hf_mask = (freqs >= 4000) & (freqs <= 8000)

            noisy_hf_energy = np.sum(noisy_spectrum[hf_mask] ** 2)
            clean_hf_energy = np.sum(clean_spectrum[hf_mask] ** 2)

            if clean_hf_energy > 0:
                nr_db = 10 * np.log10(noisy_hf_energy / clean_hf_energy)
            else:
                nr_db = float("inf")

        logger.debug(f"Noise Reduction: {nr_db:.2f} dB")
        return float(nr_db)

    def comprehensive_evaluation(
        self,
        reference_clean: np.ndarray,
        original_noisy: np.ndarray,
        processed: np.ndarray,
        noise_sample: np.ndarray = None,
    ) -> Dict[str, float]:
        """
        Perform comprehensive quality evaluation using all custom metrics.

        Args:
            reference_clean: Reference clean signal (ground truth)
            original_noisy: Original noisy signal
            processed: Processed signal to evaluate
            noise_sample: Optional isolated noise sample

        Returns:
            Dictionary of all computed metrics
        """
        logger.info("Computing comprehensive quality metrics...")

        metrics = {}

        # SNR-based metrics
        try:
            metrics["snr_db"] = self.compute_snr(reference_clean, processed)
        except Exception as e:
            logger.warning(f"SNR computation failed: {e}")
            metrics["snr_db"] = 0.0

        try:
            metrics["segmental_snr_db"] = self.compute_segmental_snr(
                reference_clean, processed
            )
        except Exception as e:
            logger.warning(f"Segmental SNR failed: {e}")
            metrics["segmental_snr_db"] = 0.0

        # Distortion metrics
        try:
            metrics["mse"] = self.compute_mse(reference_clean, processed)
        except Exception as e:
            logger.warning(f"MSE computation failed: {e}")
            metrics["mse"] = 0.0

        try:
            metrics["psnr_db"] = self.compute_psnr(reference_clean, processed)
        except Exception as e:
            logger.warning(f"PSNR computation failed: {e}")
            metrics["psnr_db"] = 0.0

        # Spectral metrics
        try:
            metrics["log_spectral_distortion_db"] = self.compute_spectral_distortion(
                reference_clean, processed
            )
        except Exception as e:
            logger.warning(f"LSD computation failed: {e}")
            metrics["log_spectral_distortion_db"] = 0.0

        try:
            metrics["itakura_saito_distance"] = self.compute_itakura_saito(
                reference_clean, processed
            )
        except Exception as e:
            logger.warning(f"IS distance failed: {e}")
            metrics["itakura_saito_distance"] = 0.0

        # Similarity metrics
        try:
            metrics["waveform_correlation"] = self.compute_waveform_similarity(
                reference_clean, processed
            )
        except Exception as e:
            logger.warning(f"Correlation computation failed: {e}")
            metrics["waveform_correlation"] = 0.0

        try:
            metrics["envelope_distance"] = self.compute_envelope_distance(
                reference_clean, processed
            )
        except Exception as e:
            logger.warning(f"Envelope distance failed: {e}")
            metrics["envelope_distance"] = 0.0

        # Noise reduction metric
        try:
            metrics["noise_reduction_db"] = self.compute_noise_reduction_amount(
                original_noisy, processed, noise_sample
            )
        except Exception as e:
            logger.warning(f"Noise reduction metric failed: {e}")
            metrics["noise_reduction_db"] = 0.0

        # Compute overall quality score (0-100)
        metrics["overall_quality_score"] = self._compute_overall_score(metrics)

        logger.info(
            f"Metrics computed: SNR={metrics['snr_db']:.1f}dB, "
            f"PSNR={metrics['psnr_db']:.1f}dB, "
            f"Overall={metrics['overall_quality_score']:.1f}"
        )

        return metrics

    def _compute_overall_score(self, metrics: Dict[str, float]) -> float:
        """
        Compute weighted overall quality score from individual metrics.

        Args:
            metrics: Dictionary of computed metrics

        Returns:
            Overall quality score [0, 100]
        """
        # Normalize and weight individual metrics
        score = 0.0

        # SNR contribution (0-40 points)
        snr = metrics.get("snr_db", 0)
        snr_score = np.clip(snr / 40 * 40, 0, 40)
        score += snr_score

        # Correlation contribution (0-30 points)
        corr = metrics.get("waveform_correlation", 0)
        corr_score = corr * 30
        score += corr_score

        # LSD contribution (0-20 points, inverted - lower is better)
        lsd = metrics.get("log_spectral_distortion_db", 10)
        lsd_score = np.clip((10 - lsd) / 10 * 20, 0, 20)
        score += lsd_score

        # Envelope preservation (0-10 points, inverted)
        env_dist = metrics.get("envelope_distance", 1)
        env_score = np.clip((1 - env_dist) * 10, 0, 10)
        score += env_score

        return float(np.clip(score, 0, 100))
