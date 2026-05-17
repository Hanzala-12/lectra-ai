"""
Unit tests for custom DSP modules
"""

import pytest
import numpy as np
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audio_quality_metrics import AudioQualityMetrics
from audio_quality_profiler import AudioQualityProfiler
from spectral_restoration import SpectralRestoration
from adaptive_router import AdaptiveRouter
from optimized_utils import VectorizedAudioProcessor


@pytest.fixture
def sample_audio():
    """Generate 1-second sample audio at 16kHz"""
    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration))
    # Generate tone + noise
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.1 * np.random.randn(len(t))
    return audio.astype(np.float32), sample_rate


@pytest.fixture
def noisy_audio(sample_audio):
    """Generate noisy version of sample audio"""
    audio, sr = sample_audio
    noise = 0.3 * np.random.randn(len(audio)).astype(np.float32)
    noisy = audio + noise
    return audio, noisy, sr


# ============================================================================
# Audio Quality Metrics Tests
# ============================================================================


def test_metrics_initialization():
    """Test AudioQualityMetrics initialization"""
    metrics = AudioQualityMetrics(sample_rate=16000)
    assert metrics.sample_rate == 16000
    assert metrics.frame_length > 0


def test_metrics_snr_calculation(noisy_audio):
    """Test SNR calculation"""
    clean, noisy, sr = noisy_audio
    metrics = AudioQualityMetrics(sample_rate=sr)

    snr = metrics.compute_snr(clean, noisy)
    assert isinstance(snr, float)
    assert -10 < snr < 50  # Reasonable range


def test_metrics_comprehensive_evaluation(noisy_audio):
    """Test comprehensive evaluation"""
    clean, noisy, sr = noisy_audio
    metrics = AudioQualityMetrics(sample_rate=sr)

    results = metrics.comprehensive_evaluation(clean, noisy, sr)

    # Check all metrics are present
    assert "snr_db" in results
    assert "psnr_db" in results
    assert "segmental_snr_db" in results
    assert "log_spectral_distance" in results
    assert "itakura_saito_distance" in results
    assert "correlation_coefficient" in results
    assert "cepstral_distance" in results
    assert "envelope_distance" in results
    assert "overall_quality_score" in results

    # Check score is in valid range
    assert 0 <= results["overall_quality_score"] <= 100


def test_metrics_format_results(noisy_audio):
    """Test results formatting"""
    clean, noisy, sr = noisy_audio
    metrics = AudioQualityMetrics(sample_rate=sr)

    results = metrics.comprehensive_evaluation(clean, noisy, sr)
    formatted = metrics.format_results(results)

    assert isinstance(formatted, str)
    assert "SNR" in formatted
    assert "Overall Quality Score" in formatted


# ============================================================================
# Audio Quality Profiler Tests
# ============================================================================


def test_profiler_initialization():
    """Test AudioQualityProfiler initialization"""
    profiler = AudioQualityProfiler(sample_rate=16000)
    assert profiler.sample_rate == 16000


def test_profiler_profile_audio(sample_audio):
    """Test audio profiling"""
    audio, sr = sample_audio
    profiler = AudioQualityProfiler(sample_rate=sr)

    profile = profiler.profile_audio(audio, sr)

    # Check all profile metrics are present
    assert "snr_db" in profile
    assert "noise_floor_db" in profile
    assert "spectral_flatness" in profile
    assert "spectral_rolloff" in profile
    assert "zero_crossing_rate" in profile
    assert "dominant_frequency" in profile
    assert "recommended_processing" in profile

    # Check recommendation is valid
    assert profile["recommended_processing"] in ["light", "medium", "heavy"]


def test_profiler_format_profile(sample_audio):
    """Test profile formatting"""
    audio, sr = sample_audio
    profiler = AudioQualityProfiler(sample_rate=sr)

    profile = profiler.profile_audio(audio, sr)
    formatted = profiler.format_profile(profile)

    assert isinstance(formatted, str)
    assert "SNR" in formatted
    assert "Recommended Processing" in formatted


# ============================================================================
# Spectral Restoration Tests
# ============================================================================


def test_restoration_initialization():
    """Test SpectralRestoration initialization"""
    restorer = SpectralRestoration(sample_rate=16000)
    assert restorer.sample_rate == 16000


def test_restoration_adaptive(noisy_audio):
    """Test adaptive restoration"""
    clean, noisy, sr = noisy_audio
    restorer = SpectralRestoration(sample_rate=sr)

    # Simulate denoised audio (attenuated version)
    denoised = noisy * 0.7

    restored = restorer.adaptive_restoration(clean, denoised, strength="light")

    assert len(restored) == len(denoised)
    assert restored.dtype == np.float32


def test_restoration_pitch_detection(sample_audio):
    """Test pitch detection"""
    audio, sr = sample_audio
    restorer = SpectralRestoration(sample_rate=sr)

    pitch = restorer._detect_pitch(audio)

    # Should detect 440 Hz tone (or None if detection fails)
    if pitch is not None:
        assert 400 < pitch < 500  # Allow some tolerance


# ============================================================================
# Adaptive Router Tests
# ============================================================================


def test_router_initialization():
    """Test AdaptiveRouter initialization"""
    router = AdaptiveRouter(sample_rate=16000)
    assert router.sample_rate == 16000


def test_router_spectral_subtraction(sample_audio):
    """Test spectral subtraction"""
    audio, sr = sample_audio
    router = AdaptiveRouter(sample_rate=sr)

    cleaned = router._spectral_subtraction(audio)

    assert len(cleaned) == len(audio)
    assert cleaned.dtype == np.float32


def test_router_wiener_filter(sample_audio):
    """Test Wiener filter"""
    audio, sr = sample_audio
    router = AdaptiveRouter(sample_rate=sr)

    cleaned = router._wiener_filter(audio)

    assert len(cleaned) == len(audio)
    assert cleaned.dtype == np.float32


def test_router_route_processing(sample_audio):
    """Test routing decision"""
    audio, sr = sample_audio
    router = AdaptiveRouter(sample_rate=sr)

    # Create profile with high SNR (should use spectral subtraction)
    profile = {"snr_db": 20.0}

    processed, method = router.route_processing(audio, profile)

    assert len(processed) == len(audio)
    assert method in ["spectral_subtraction", "wiener_filter", "deepfilternet_required"]


# ============================================================================
# Optimized Utils Tests
# ============================================================================


def test_optimized_utils_initialization():
    """Test VectorizedAudioProcessor initialization"""
    processor = VectorizedAudioProcessor(sample_rate=16000)
    assert processor.sample_rate == 16000


def test_optimized_frame_energies(sample_audio):
    """Test frame energy calculation"""
    audio, sr = sample_audio
    processor = VectorizedAudioProcessor(sample_rate=sr)

    energies = processor.compute_frame_energies_vectorized(
        audio, frame_len=512, hop_len=256
    )

    assert len(energies) > 0
    assert all(e >= 0 for e in energies)


def test_optimized_snr_estimation(noisy_audio):
    """Test SNR estimation"""
    clean, noisy, sr = noisy_audio
    processor = VectorizedAudioProcessor(sample_rate=sr)

    snr = processor.estimate_snr_numba(clean, noisy)

    assert isinstance(snr, float)
    assert -10 < snr < 50


def test_optimized_fast_rms(sample_audio):
    """Test fast RMS calculation"""
    audio, sr = sample_audio
    processor = VectorizedAudioProcessor(sample_rate=sr)

    rms_values = processor.fast_rms(audio, frame_len=512)

    assert len(rms_values) > 0
    assert all(r >= 0 for r in rms_values)


def test_optimized_benchmark(sample_audio):
    """Test benchmark functionality"""
    audio, sr = sample_audio
    processor = VectorizedAudioProcessor(sample_rate=sr)

    results = processor.benchmark_optimizations(audio, n_iterations=10)

    assert "frame_energies" in results
    assert "snr_estimation" in results
    assert "rms_calculation" in results

    # Check speedup is positive
    for operation, metrics in results.items():
        assert metrics["speedup"] > 0


# ============================================================================
# Integration Tests
# ============================================================================


def test_full_pipeline_integration(sample_audio):
    """Test integration of all custom modules"""
    audio, sr = sample_audio

    # 1. Profile audio
    profiler = AudioQualityProfiler(sample_rate=sr)
    profile = profiler.profile_audio(audio, sr)
    assert profile is not None

    # 2. Route processing
    router = AdaptiveRouter(sample_rate=sr)
    processed, method = router.route_processing(audio, profile)
    assert processed is not None

    # 3. Apply restoration
    restorer = SpectralRestoration(sample_rate=sr)
    restored = restorer.adaptive_restoration(audio, processed, strength="light")
    assert restored is not None

    # 4. Compute metrics
    metrics = AudioQualityMetrics(sample_rate=sr)
    results = metrics.comprehensive_evaluation(audio, restored, sr)
    assert results is not None
    assert "overall_quality_score" in results


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
