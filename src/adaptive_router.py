"""
Adaptive Processing Router
Intelligent decision system that routes audio through optimal processing paths
based on real-time signal analysis.

Author: Custom implementation for academic project
Purpose: Demonstrate algorithmic decision-making and adaptive system design
"""

import numpy as np
from typing import Dict, Tuple, Callable
import logging

logger = logging.getLogger(__name__)


class AdaptiveRouter:
    """
    Custom routing algorithm that dynamically selects processing intensity
    based on signal characteristics.

    This is a "lightweight custom filter or heavy DNN" decision gate.
    """

    def __init__(self, sample_rate: int = 16000):
        """
        Initialize adaptive router.

        Args:
            sample_rate: Audio sampling rate
        """
        self.sample_rate = sample_rate

        # Decision thresholds (can be tuned)
        self.thresholds = {
            "snr_light": 25.0,  # SNR > 25dB → lightweight processing
            "snr_moderate": 15.0,  # 15-25 dB → moderate processing
            "snr_heavy": 10.0,  # < 10 dB → heavy processing
            "noise_var_threshold": 0.03,  # Noise variance threshold
            "spectral_flatness_threshold": 0.6,  # Above this = very noisy
        }

        # Statistics tracking
        self.routing_stats = {"lightweight": 0, "moderate": 0, "heavy": 0, "total": 0}

    def lightweight_filter(self, audio: np.ndarray, silence_segments: list = None) -> np.ndarray:
        """
        Custom lightweight noise filter using spectral subtraction.

        Args:
            audio: Input audio signal
            silence_segments: Optional list of (start, end) sample ranges
                              known to be non-speech, used for accurate
                              noise estimation.

        Returns:
            Filtered audio
        """
        logger.info("Applying lightweight spectral subtraction filter...")

        # Parameters
        alpha = 1.8  # Over-subtraction factor
        beta = 0.1  # Spectral floor

        # Frame-based processing
        frame_length = int(0.025 * self.sample_rate)  # 25ms frames
        hop_length = frame_length // 2

        # --- Noise estimation from known silence regions when available ---
        noise_frames = []
        if silence_segments:
            for seg_start, seg_end in silence_segments:
                for i in range(seg_start, min(seg_end - frame_length, len(audio) - frame_length), frame_length):
                    noise_frames.append(audio[i : i + frame_length])
                    if len(noise_frames) >= 30:
                        break
                if len(noise_frames) >= 30:
                    break

        # Fallback: first 10 frames
        if len(noise_frames) == 0:
            for i in range(
                0, min(10 * frame_length, len(audio) - frame_length), frame_length
            ):
                noise_frames.append(audio[i : i + frame_length])

        if len(noise_frames) > 0:
            noise_estimate = np.mean(noise_frames, axis=0)
            noise_spectrum = np.abs(np.fft.rfft(noise_estimate))
        else:
            # Fallback: use whole signal's low-energy estimate
            noise_spectrum = np.abs(np.fft.rfft(audio[:frame_length])) * 0.1

        # Process audio in overlapping frames
        output = np.zeros_like(audio)
        window = np.hanning(frame_length)

        for i in range(0, len(audio) - frame_length, hop_length):
            # Extract frame
            frame = audio[i : i + frame_length] * window

            # FFT
            frame_spectrum = np.fft.rfft(frame)
            magnitude = np.abs(frame_spectrum)
            phase = np.angle(frame_spectrum)

            # Spectral subtraction
            enhanced_magnitude = np.maximum(
                magnitude - alpha * noise_spectrum, beta * magnitude
            )

            # Reconstruct
            enhanced_spectrum = enhanced_magnitude * np.exp(1j * phase)
            enhanced_frame = np.fft.irfft(enhanced_spectrum, n=frame_length)

            # Overlap-add
            output[i : i + frame_length] += enhanced_frame * window

        # Normalize
        max_val = np.max(np.abs(output))
        if max_val > 0:
            output = output / max_val * np.max(np.abs(audio))

        logger.info("Lightweight filter complete")
        return output

    def moderate_filter(self, audio: np.ndarray, silence_segments: list = None) -> np.ndarray:
        """
        Moderate filter using Wiener filtering.

        Args:
            audio: Input audio
            silence_segments: Optional list of (start, end) sample ranges
                              known to be non-speech.

        Returns:
            Filtered audio
        """
        logger.info("Applying moderate Wiener filter...")

        # Parameters
        h_min = 0.15  # Minimum gain

        # Frame-based processing
        frame_length = int(0.032 * self.sample_rate)  # 32ms
        hop_length = frame_length // 2

        # --- Noise power from known silence regions when available ---
        if silence_segments:
            noise_frames_power = []
            for seg_start, seg_end in silence_segments:
                for i in range(seg_start, min(seg_end - frame_length, len(audio) - frame_length), frame_length):
                    frame = audio[i : i + frame_length]
                    noise_frames_power.append(np.mean(frame ** 2))
                    if len(noise_frames_power) >= 30:
                        break
                if len(noise_frames_power) >= 30:
                    break
            if noise_frames_power:
                noise_power = float(np.mean(noise_frames_power))
            else:
                noise_power = None
        else:
            noise_power = None

        # Fallback: lowest 20% energy frames
        if noise_power is None:
            frame_powers = []
            for i in range(0, len(audio) - frame_length, frame_length):
                frame = audio[i : i + frame_length]
                power = np.mean(frame ** 2)
                frame_powers.append(power)

            frame_powers_sorted = np.sort(frame_powers)
            noise_power = float(np.mean(frame_powers_sorted[: len(frame_powers_sorted) // 5]))

        # Process frames
        output = np.zeros_like(audio)
        window = np.hanning(frame_length)

        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i : i + frame_length] * window

            # FFT
            frame_spectrum = np.fft.rfft(frame)
            power_spectrum = np.abs(frame_spectrum) ** 2
            phase = np.angle(frame_spectrum)

            # Wiener gain
            wiener_gain = np.maximum(
                1 - (noise_power / (power_spectrum + 1e-10)), h_min
            )

            # Apply gain
            enhanced_spectrum = (
                np.abs(frame_spectrum) * wiener_gain * np.exp(1j * phase)
            )
            enhanced_frame = np.fft.irfft(enhanced_spectrum, n=frame_length)

            # Overlap-add
            output[i : i + frame_length] += enhanced_frame * window

        # Normalize
        max_val = np.max(np.abs(output))
        if max_val > 0:
            output = output / max_val * np.max(np.abs(audio))

        logger.info("Moderate filter complete")
        return output

    def route_processing(
        self, audio: np.ndarray, noise_profile: Dict, heavy_processor: Callable = None,
        silence_segments: list = None,
    ) -> Tuple[np.ndarray, str]:
        """
        Main routing logic that decides processing path.

        Args:
            audio: Input audio
            noise_profile: Profile dict from AudioQualityProfiler
            heavy_processor: Optional heavy processing function (e.g., DeepFilterNet)
            silence_segments: List of (start, end) sample ranges known to be non-speech

        Returns:
            Tuple of (processed_audio, routing_decision)
        """
        logger.info("Routing decision in progress...")

        # Extract key metrics from profile
        snr = noise_profile.get("snr_db", 0)
        noise_var = noise_profile.get("noise_variance", 0)
        spectral_flatness = noise_profile.get("spectral_flatness", 0)

        # Decision logic with priority rules
        decision = None

        # Rule 1: Very clean audio → lightweight or skip
        if snr > self.thresholds["snr_light"] and noise_var < 0.01:
            decision = "lightweight"
            logger.info(f"✓ ROUTE: Lightweight (SNR={snr:.1f}dB, very clean)")

        # Rule 2: Extremely noisy → heavy processing required
        elif (
            snr < self.thresholds["snr_heavy"]
            or noise_var > self.thresholds["noise_var_threshold"]
            or spectral_flatness > self.thresholds["spectral_flatness_threshold"]
        ):
            decision = "heavy"
            logger.info(f"✓ ROUTE: Heavy (SNR={snr:.1f}dB, very noisy)")

        # Rule 3: Moderate noise → moderate processing
        elif (
            snr >= self.thresholds["snr_heavy"]
            and snr <= self.thresholds["snr_moderate"]
        ):
            decision = "moderate"
            logger.info(f"✓ ROUTE: Moderate (SNR={snr:.1f}dB, moderate noise)")

        # Rule 4: Default to moderate for unclear cases
        else:
            decision = "moderate"
            logger.info(f"✓ ROUTE: Moderate (default, SNR={snr:.1f}dB)")

        # Execute routing
        if decision == "lightweight":
            processed = self.lightweight_filter(audio, silence_segments=silence_segments)
            self.routing_stats["lightweight"] += 1

        elif decision == "moderate":
            processed = self.moderate_filter(audio, silence_segments=silence_segments)
            self.routing_stats["moderate"] += 1

        elif decision == "heavy":
            if heavy_processor is not None:
                logger.info("Invoking heavy processor (DeepFilterNet)...")
                processed = heavy_processor(audio, self.sample_rate)
                self.routing_stats["heavy"] += 1
            else:
                # Fallback to moderate if heavy processor not available
                logger.warning("Heavy processor not provided, falling back to moderate")
                processed = self.moderate_filter(audio)
                decision = "moderate_fallback"
                self.routing_stats["moderate"] += 1

        else:
            # Should never reach here
            processed = audio
            decision = "bypass"

        self.routing_stats["total"] += 1

        return processed, decision

    def get_routing_statistics(self) -> Dict:
        """
        Get routing statistics for reporting.

        Returns:
            Dictionary with routing counts and percentages
        """
        total = self.routing_stats["total"]
        if total == 0:
            return {
                "lightweight_pct": 0,
                "moderate_pct": 0,
                "heavy_pct": 0,
                "total_routed": 0,
            }

        return {
            "lightweight_count": self.routing_stats["lightweight"],
            "moderate_count": self.routing_stats["moderate"],
            "heavy_count": self.routing_stats["heavy"],
            "total_routed": total,
            "lightweight_pct": (self.routing_stats["lightweight"] / total) * 100,
            "moderate_pct": (self.routing_stats["moderate"] / total) * 100,
            "heavy_pct": (self.routing_stats["heavy"] / total) * 100,
        }

    def adaptive_dual_path(
        self,
        audio: np.ndarray,
        noise_profile: Dict,
        heavy_processor: Callable = None,
        blend_factor: float = None,
    ) -> np.ndarray:
        """
        Advanced: Blend lightweight and heavy processing based on confidence.

        Theory: If routing confidence is low (SNR near threshold), blend both paths.

        output = α * lightweight + (1-α) * heavy

        where α depends on distance from decision threshold.

        Args:
            audio: Input audio
            noise_profile: Noise profile dict
            heavy_processor: Heavy processing function
            blend_factor: Manual blend [0,1], or None for auto

        Returns:
            Blended processed audio
        """
        snr = noise_profile.get("snr_db", 15)

        # Auto-compute blend if not specified
        if blend_factor is None:
            # Near thresholds → blend; far from thresholds → pure route
            if abs(snr - self.thresholds["snr_moderate"]) < 3:
                # Near moderate threshold → blend
                blend_factor = 0.5
                logger.info("SNR near threshold, blending lightweight/heavy (50/50)")
            elif snr > self.thresholds["snr_moderate"]:
                blend_factor = 1.0  # Pure lightweight
            else:
                blend_factor = 0.0  # Pure heavy

        # Process both paths
        lightweight_output = self.lightweight_filter(audio)

        if heavy_processor is not None and blend_factor < 1.0:
            heavy_output = heavy_processor(audio, self.sample_rate)
        else:
            heavy_output = lightweight_output

        # Blend
        blended = blend_factor * lightweight_output + (1 - blend_factor) * heavy_output

        # Normalize
        max_val = np.max(np.abs(blended))
        if max_val > 0:
            blended = blended / max_val * 0.95

        logger.info(f"Dual-path blend complete (α={blend_factor:.2f})")
        return blended
