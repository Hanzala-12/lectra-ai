#!/usr/bin/env python3
"""
Custom Integration Demo
Demonstrates full workflow with all custom DSP modules
"""

import sys
import os
from pathlib import Path
import numpy as np

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from audio_quality_profiler import AudioQualityProfiler
from audio_quality_metrics import AudioQualityMetrics
from spectral_restoration import SpectralRestoration
from adaptive_router import AdaptiveRouter
from optimized_utils import VectorizedAudioProcessor

try:
    import soundfile as sf

    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    print("Warning: soundfile not available, using synthetic audio")


def generate_test_audio(duration=5.0, sample_rate=16000):
    """Generate synthetic test audio with noise"""
    t = np.linspace(0, duration, int(sample_rate * duration))

    # Generate speech-like signal (multiple harmonics)
    fundamental = 150  # Hz
    signal = np.zeros(len(t))
    for harmonic in range(1, 6):
        signal += (1.0 / harmonic) * np.sin(2 * np.pi * fundamental * harmonic * t)

    # Add noise
    noise = 0.3 * np.random.randn(len(t))
    noisy_audio = signal + noise

    # Normalize
    noisy_audio = noisy_audio / np.max(np.abs(noisy_audio)) * 0.8

    return noisy_audio.astype(np.float32), signal.astype(np.float32), sample_rate


def main():
    print("=" * 70)
    print("Custom DSP Integration Demo")
    print("=" * 70)
    print()

    # Check if audio file provided
    if len(sys.argv) > 1 and SOUNDFILE_AVAILABLE:
        audio_path = sys.argv[1]
        print(f"Loading audio from: {audio_path}")
        try:
            audio, sample_rate = sf.read(audio_path)
            if audio.ndim > 1:
                audio = audio[:, 0]  # Use first channel
            audio = audio.astype(np.float32)
            clean_reference = audio  # Use as reference (not truly clean)
        except Exception as e:
            print(f"Error loading audio: {e}")
            print("Using synthetic audio instead")
            audio, clean_reference, sample_rate = generate_test_audio()
    else:
        print("Using synthetic test audio (5 seconds)")
        audio, clean_reference, sample_rate = generate_test_audio()

    print(f"Audio duration: {len(audio) / sample_rate:.2f}s")
    print(f"Sample rate: {sample_rate} Hz")
    print()

    # ========================================================================
    # Step 1: Audio Quality Profiling
    # ========================================================================
    print("Step 1: Audio Quality Profiling")
    print("-" * 70)

    profiler = AudioQualityProfiler(sample_rate=sample_rate)
    profile = profiler.profile_audio(audio, sample_rate)

    print(profiler.format_profile(profile))
    print()

    # ========================================================================
    # Step 2: Adaptive Routing
    # ========================================================================
    print("Step 2: Adaptive Routing")
    print("-" * 70)

    router = AdaptiveRouter(sample_rate=sample_rate)
    processed_audio, method = router.route_processing(audio, profile)

    print(f"Selected method: {router.get_method_description(method)}")
    print()

    # ========================================================================
    # Step 3: Spectral Restoration
    # ========================================================================
    print("Step 3: Spectral Restoration")
    print("-" * 70)

    restorer = SpectralRestoration(sample_rate=sample_rate)
    restored_audio = restorer.adaptive_restoration(
        audio, processed_audio, strength="auto"
    )

    print(f"Restoration applied (output length: {len(restored_audio)} samples)")
    print()

    # ========================================================================
    # Step 4: Quality Metrics
    # ========================================================================
    print("Step 4: Quality Metrics Evaluation")
    print("-" * 70)

    metrics_calc = AudioQualityMetrics(sample_rate=sample_rate)

    # Compare original vs processed
    metrics_processed = metrics_calc.comprehensive_evaluation(
        clean_reference, processed_audio, sample_rate
    )

    # Compare original vs restored
    metrics_restored = metrics_calc.comprehensive_evaluation(
        clean_reference, restored_audio, sample_rate
    )

    print("Metrics after routing:")
    print(metrics_calc.format_results(metrics_processed))
    print()

    print("Metrics after restoration:")
    print(metrics_calc.format_results(metrics_restored))
    print()

    # ========================================================================
    # Step 5: Performance Benchmarks (Optional)
    # ========================================================================
    print("Step 5: Performance Benchmarks")
    print("-" * 70)

    processor = VectorizedAudioProcessor(sample_rate=sample_rate)
    benchmark_results = processor.benchmark_optimizations(audio, n_iterations=50)

    print(processor.format_benchmark_results(benchmark_results))
    print()

    # ========================================================================
    # Save outputs (if soundfile available)
    # ========================================================================
    if SOUNDFILE_AVAILABLE:
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)

        sf.write(output_dir / "demo_original.wav", audio, sample_rate)
        sf.write(output_dir / "demo_processed.wav", processed_audio, sample_rate)
        sf.write(output_dir / "demo_restored.wav", restored_audio, sample_rate)

        print("Outputs saved to outputs/ directory:")
        print("  - demo_original.wav")
        print("  - demo_processed.wav")
        print("  - demo_restored.wav")
        print()

    # ========================================================================
    # Summary
    # ========================================================================
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  Input SNR:              {profile['snr_db']:.1f} dB")
    print(f"  Processing method:      {method}")
    print(
        f"  Quality score (processed): {metrics_processed['overall_quality_score']:.1f}/100"
    )
    print(
        f"  Quality score (restored):  {metrics_restored['overall_quality_score']:.1f}/100"
    )
    print()

    improvement = (
        metrics_restored["overall_quality_score"]
        - metrics_processed["overall_quality_score"]
    )
    if improvement > 0:
        print(f"  ✓ Restoration improved quality by {improvement:.1f} points")
    else:
        print(f"  ✗ Restoration decreased quality by {abs(improvement):.1f} points")
    print()


if __name__ == "__main__":
    main()
