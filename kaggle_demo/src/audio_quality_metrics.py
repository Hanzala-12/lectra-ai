"""
Audio Quality Metrics Module
Implements 9 scientific metrics for evaluating audio processing quality
"""

import numpy as np
from scipy import signal
from scipy.fft import fft, ifft
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AudioQualityMetrics:
    """
    Comprehensive audio quality evaluation using 9 scientific metrics

    Metrics implemented:
    1. SNR (Signal-to-Noise Ratio)
    2. PSNR (Peak Signal-to-Noise Ratio)
    3. Segmental SNR
    4. Log-Spectral Distance
    5. Itakura-Saito Distance
    6. Correlation Coefficient
    7. Cepstral Distance
    8. Envelope Distance
    9. Composite Quality Score (0-100)
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize metrics calculator

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.frame_length = int(0.032 * sample_rate)  # 32ms frames
        self.hop_length = int(0.016 * sample_rate)  # 16ms hop

    def comprehensive_evaluation(
        self,
        clean_audio: np.ndarray,
        processed_audio: np.ndarray,
        sample_rate: Optional[int] = None,
    ) -> Dict[str, float]:
        """
        Compute all quality metrics between clean and processed audio

        Args:
            clean_audio: Reference clean audio (1D array)
            processed_audio: Processed/enhanced audio (1D array)
            sample_rate: Sample rate (uses instance default if None)

        Returns:
            Dictionary with all metric values
        """
        if sample_rate is not None:
            self.sample_rate = sample_rate

        # Ensure same length
        min_len = min(len(clean_audio), len(processed_audio))
        clean = clean_audio[:min_len].astype(np.float64)
        processed = processed_audio[:min_len].astype(np.float64)

        # Compute all metrics
        results = {
            "snr_db": self.compute_snr(clean, processed),
            "psnr_db": self.compute_psnr(clean, processed),
            "segmental_snr_db": self.compute_segmental_snr(clean, processed),
            "log_spectral_distance": self.compute_lsd(clean, processed),
            "itakura_saito_distance": self.compute_itakura_saito(clean, processed),
            "correlation_coefficient": self.compute_correlation(clean, processed),
            "cepstral_distance": self.compute_cepstral_distance(clean, processed),
            "envelope_distance": self.compute_envelope_distance(clean, processed),
        }

        # Compute composite score
        results["overall_quality_score"] = self.compute_composite_score(results)

        logger.info(
            f"Quality metrics computed: Overall score = {results['overall_quality_score']:.1f}/100"
        )

        return results

    def compute_snr(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Signal-to-Noise Ratio in dB

        SNR = 10 * log10(signal_power / noise_power)
        """
        signal_power = np.mean(clean**2)
        noise = processed - clean
        noise_power = np.mean(noise**2)

        if noise_power < 1e-10:
            return 100.0  # Very high SNR

        snr = 10 * np.log10(signal_power / noise_power)
        return float(snr)

    def compute_psnr(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Peak Signal-to-Noise Ratio in dB

        PSNR = 10 * log10(max_signal^2 / MSE)
        """
        max_signal = np.max(np.abs(clean))
        mse = np.mean((clean - processed) ** 2)

        if mse < 1e-10:
            return 100.0

        psnr = 10 * np.log10(max_signal**2 / mse)
        return float(psnr)

    def compute_segmental_snr(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Segmental SNR (frame-by-frame average)

        More robust to local variations than global SNR
        """
        n_frames = (len(clean) - self.frame_length) // self.hop_length + 1
        snr_values = []

        for i in range(n_frames):
            start = i * self.hop_length
            end = start + self.frame_length

            clean_frame = clean[start:end]
            proc_frame = processed[start:end]

            signal_power = np.mean(clean_frame**2)
            noise = proc_frame - clean_frame
            noise_power = np.mean(noise**2)

            if signal_power > 1e-10 and noise_power > 1e-10:
                frame_snr = 10 * np.log10(signal_power / noise_power)
                # Clip to reasonable range
                frame_snr = np.clip(frame_snr, -10, 35)
                snr_values.append(frame_snr)

        if not snr_values:
            return 0.0

        return float(np.mean(snr_values))

    def compute_lsd(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Log-Spectral Distance

        Measures frequency-domain distortion
        Lower is better (0 = identical)
        """
        # Compute STFT
        f_clean, t_clean, Zxx_clean = signal.stft(
            clean,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        f_proc, t_proc, Zxx_proc = signal.stft(
            processed,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Magnitude spectra
        mag_clean = np.abs(Zxx_clean) + 1e-10
        mag_proc = np.abs(Zxx_proc) + 1e-10

        # Log-spectral distance
        lsd = np.sqrt(np.mean((np.log10(mag_clean) - np.log10(mag_proc)) ** 2))

        return float(lsd)

    def compute_itakura_saito(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Itakura-Saito Distance

        Perceptual distance measure based on spectral envelopes
        Lower is better (0 = identical)
        """
        # Compute power spectra
        f_clean, t_clean, Zxx_clean = signal.stft(
            clean,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        f_proc, t_proc, Zxx_proc = signal.stft(
            processed,
            fs=self.sample_rate,
            nperseg=self.frame_length,
            noverlap=self.frame_length - self.hop_length,
        )

        # Power spectra
        P_clean = np.abs(Zxx_clean) ** 2 + 1e-10
        P_proc = np.abs(Zxx_proc) ** 2 + 1e-10

        # Itakura-Saito divergence
        is_dist = np.mean(P_clean / P_proc - np.log(P_clean / P_proc) - 1)

        return float(is_dist)

    def compute_correlation(self, clean: np.ndarray, processed: np.ndarray) -> float:
        """
        Compute Pearson correlation coefficient

        Measures waveform similarity
        Range: [-1, 1], higher is better (1 = perfect match)
        """
        # Normalize
        clean_norm = (clean - np.mean(clean)) / (np.std(clean) + 1e-10)
        proc_norm = (processed - np.mean(processed)) / (np.std(processed) + 1e-10)

        corr = np.corrcoef(clean_norm, proc_norm)[0, 1]

        return float(corr)

    def compute_cepstral_distance(
        self, clean: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Compute Cepstral Distance

        Measures voice characteristic preservation
        Lower is better (0 = identical)
        """
        # Compute cepstra using real cepstrum
        n_fft = 512
        n_frames = (len(clean) - n_fft) // (n_fft // 2) + 1

        cepstral_dists = []

        for i in range(n_frames):
            start = i * (n_fft // 2)
            end = start + n_fft

            if end > len(clean):
                break

            clean_frame = clean[start:end]
            proc_frame = processed[start:end]

            # Apply window
            window = np.hanning(n_fft)
            clean_frame = clean_frame * window
            proc_frame = proc_frame * window

            # Compute cepstrum (real cepstrum)
            clean_spectrum = np.abs(fft(clean_frame))
            proc_spectrum = np.abs(fft(proc_frame))

            clean_cepstrum = np.real(ifft(np.log(clean_spectrum + 1e-10)))
            proc_cepstrum = np.real(ifft(np.log(proc_spectrum + 1e-10)))

            # Use first 20 cepstral coefficients
            n_coef = 20
            dist = np.sqrt(
                np.sum((clean_cepstrum[:n_coef] - proc_cepstrum[:n_coef]) ** 2)
            )
            cepstral_dists.append(dist)

        if not cepstral_dists:
            return 0.0

        return float(np.mean(cepstral_dists))

    def compute_envelope_distance(
        self, clean: np.ndarray, processed: np.ndarray
    ) -> float:
        """
        Compute Envelope Distance

        Measures amplitude contour matching
        Lower is better (0 = identical)
        """
        # Extract envelopes using Hilbert transform
        clean_analytic = signal.hilbert(clean)
        proc_analytic = signal.hilbert(processed)

        clean_envelope = np.abs(clean_analytic)
        proc_envelope = np.abs(proc_analytic)

        # Normalize envelopes
        clean_envelope = clean_envelope / (np.max(clean_envelope) + 1e-10)
        proc_envelope = proc_envelope / (np.max(proc_envelope) + 1e-10)

        # Compute distance
        envelope_dist = np.sqrt(np.mean((clean_envelope - proc_envelope) ** 2))

        return float(envelope_dist)

    def compute_composite_score(self, metrics: Dict[str, float]) -> float:
        """
        Compute overall quality score (0-100)

        Weighted combination of all metrics normalized to 0-100 scale
        Higher is better
        """
        # Normalize each metric to 0-1 scale (higher = better)

        # SNR: map [-10, 30] dB to [0, 1]
        snr_norm = np.clip((metrics["snr_db"] + 10) / 40, 0, 1)

        # PSNR: map [0, 40] dB to [0, 1]
        psnr_norm = np.clip(metrics["psnr_db"] / 40, 0, 1)

        # Segmental SNR: map [-5, 25] dB to [0, 1]
        seg_snr_norm = np.clip((metrics["segmental_snr_db"] + 5) / 30, 0, 1)

        # LSD: map [5, 0] to [0, 1] (lower is better)
        lsd_norm = np.clip(1 - metrics["log_spectral_distance"] / 5, 0, 1)

        # IS distance: map [2, 0] to [0, 1] (lower is better)
        is_norm = np.clip(1 - metrics["itakura_saito_distance"] / 2, 0, 1)

        # Correlation: map [-1, 1] to [0, 1]
        corr_norm = (metrics["correlation_coefficient"] + 1) / 2

        # Cepstral distance: map [10, 0] to [0, 1] (lower is better)
        cep_norm = np.clip(1 - metrics["cepstral_distance"] / 10, 0, 1)

        # Envelope distance: map [1, 0] to [0, 1] (lower is better)
        env_norm = np.clip(1 - metrics["envelope_distance"], 0, 1)

        # Weighted average (emphasize SNR and correlation)
        weights = {
            "snr": 0.20,
            "psnr": 0.15,
            "seg_snr": 0.15,
            "lsd": 0.10,
            "is": 0.10,
            "corr": 0.15,
            "cep": 0.08,
            "env": 0.07,
        }

        composite = (
            weights["snr"] * snr_norm
            + weights["psnr"] * psnr_norm
            + weights["seg_snr"] * seg_snr_norm
            + weights["lsd"] * lsd_norm
            + weights["is"] * is_norm
            + weights["corr"] * corr_norm
            + weights["cep"] * cep_norm
            + weights["env"] * env_norm
        )

        # Scale to 0-100
        score = composite * 100

        return float(score)

    def format_results(self, metrics: Dict[str, float]) -> str:
        """
        Format metrics as human-readable string

        Args:
            metrics: Dictionary from comprehensive_evaluation()

        Returns:
            Formatted string
        """
        lines = [
            "Audio Quality Metrics",
            "=" * 50,
            f"SNR:                    {metrics['snr_db']:>8.2f} dB",
            f"PSNR:                   {metrics['psnr_db']:>8.2f} dB",
            f"Segmental SNR:          {metrics['segmental_snr_db']:>8.2f} dB",
            f"Log-Spectral Distance:  {metrics['log_spectral_distance']:>8.4f}",
            f"Itakura-Saito Distance: {metrics['itakura_saito_distance']:>8.4f}",
            f"Correlation:            {metrics['correlation_coefficient']:>8.4f}",
            f"Cepstral Distance:      {metrics['cepstral_distance']:>8.4f}",
            f"Envelope Distance:      {metrics['envelope_distance']:>8.4f}",
            "=" * 50,
            f"Overall Quality Score:  {metrics['overall_quality_score']:>8.1f}/100",
        ]

        return "\n".join(lines)
