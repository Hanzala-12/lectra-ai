"""
Integration Example: Custom Algorithms in Pipeline
Demonstrates how to integrate all custom modules into the existing pipeline.

This script shows how your custom mathematical code wraps around the pre-built models.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np
import soundfile as sf
from pathlib import Path

# Import custom modules
from audio_quality_profiler import AudioQualityProfiler
from spectral_restoration import SpectralRestoration
from audio_quality_metrics import AudioQualityMetrics
from adaptive_router import AdaptiveRouter

# Import existing pipeline components
from deepfilter_processor import DeepFilterProcessor

def demonstrate_custom_pipeline(input_audio_path: str):
    """
    Complete demonstration of custom algorithmic integration.
    
    Pipeline flow:
    1. [CUSTOM] Audio Quality Profiler - analyze input characteristics
    2. [CUSTOM] Adaptive Router - decide processing intensity
    3. [PRE-BUILT OR CUSTOM] Apply selected processor
    4. [CUSTOM] Spectral Restoration - restore lost frequencies
    5. [CUSTOM] Quality Metrics - evaluate results
    """
    
    print("=" * 80)
    print("CUSTOM ALGORITHMIC NOISE REMOVAL PIPELINE")
    print("Demonstrating custom mathematical implementations")
    print("=" * 80)
    
    # Load audio
    print(f"\n📂 Loading audio: {input_audio_path}")
    audio, sample_rate = sf.read(input_audio_path, dtype='float32')
    
    # Handle stereo
    if len(audio.shape) > 1:
        audio = np.mean(audio, axis=1)
    
    print(f"   Duration: {len(audio)/sample_rate:.2f}s @ {sample_rate}Hz")
    
    # ========================================================================
    # STEP 1: CUSTOM AUDIO QUALITY PROFILING
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: CUSTOM AUDIO QUALITY PROFILING")
    print("=" * 80)
    
    profiler = AudioQualityProfiler(sample_rate=sample_rate)
    profile = profiler.profile_audio(audio)
    
    print("\n📊 Computed Metrics (from scratch, no pre-built libraries):")
    print(f"   • Noise Variance (MAD wavelet): {profile['noise_variance']:.6f}")
    print(f"   • Estimated SNR: {profile['snr_db']:.2f} dB")
    print(f"   • Spectral Flatness (Wiener entropy): {profile['spectral_flatness']:.4f}")
    print(f"   • Zero Crossing Rate: {profile['zero_crossing_rate']:.4f}")
    print(f"   • Crest Factor: {profile['crest_factor_db']:.2f} dB")
    
    print("\n🎯 Frequency Spectrum Analysis:")
    for band, energy_pct in profile['frequency_spectrum'].items():
        print(f"   {band:>12}: {energy_pct:5.1f}%")
    
    print("\n🏷️  Classifications:")
    for key, value in profile['classifications'].items():
        print(f"   • {key}: {value}")
    
    print(f"\n💡 Recommended Processing: {profile['recommended_processing'].upper()}")
    
    # ========================================================================
    # STEP 2: CUSTOM ADAPTIVE ROUTING
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: CUSTOM ADAPTIVE ROUTING ALGORITHM")
    print("=" * 80)
    
    router = AdaptiveRouter(sample_rate=sample_rate)
    
    # Create heavy processor wrapper (DeepFilterNet)
    try:
        deepfilter = DeepFilterProcessor()
        heavy_processor = lambda audio, sr: deepfilter.process_audio(audio, sr)
        print("✓ Heavy processor (DeepFilterNet) loaded")
    except Exception as e:
        print(f"⚠ Heavy processor unavailable: {e}")
        heavy_processor = None
    
    # Route processing
    processed_audio, routing_decision = router.route_processing(
        audio,
        profile,
        heavy_processor=heavy_processor
    )
    
    print(f"\n🔀 Routing Decision: {routing_decision.upper()}")
    print(f"   This demonstrates intelligent algorithm selection based on signal analysis.")
    
    # Show routing statistics
    stats = router.get_routing_statistics()
    print(f"\n📈 Routing Statistics:")
    print(f"   Lightweight: {stats['lightweight_count']}")
    print(f"   Moderate:    {stats['moderate_count']}")
    print(f"   Heavy:       {stats['heavy_count']}")
    
    # ========================================================================
    # STEP 3: CUSTOM SPECTRAL RESTORATION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 3: CUSTOM SPECTRAL RESTORATION")
    print("=" * 80)
    
    restorer = SpectralRestoration(sample_rate=sample_rate)
    
    # Detect if high frequencies were lost
    print("\n🔬 Analyzing spectral damage...")
    
    # Adaptive restoration based on HF loss
    restored_audio = restorer.adaptive_restoration(audio, processed_audio)
    
    print("✓ Spectral restoration complete")
    print("   • Pitch detection via autocorrelation")
    print("   • Harmonic synthesis (f0, 2f0, 3f0, ...)")
    print("   • Perceptual A-weighting applied")
    
    # ========================================================================
    # STEP 4: CUSTOM QUALITY METRICS EVALUATION
    # ========================================================================
    print("\n" + "=" * 80)
    print("STEP 4: CUSTOM QUALITY METRICS (FROM-SCRATCH MATH)")
    print("=" * 80)
    
    metrics_calculator = AudioQualityMetrics(sample_rate=sample_rate)
    
    # For demonstration, we'll compare processed vs original
    # (In real scenario, you'd have a clean reference)
    print("\n📐 Computing custom metrics...")
    print("   All metrics implemented from mathematical first principles:")
    
    # Individual metrics
    snr = metrics_calculator.compute_snr(audio, processed_audio)
    print(f"\n   • SNR (Signal-to-Noise Ratio): {snr:.2f} dB")
    print(f"     Formula: SNR = 10*log₁₀(P_signal / P_noise)")
    
    seg_snr = metrics_calculator.compute_segmental_snr(audio, processed_audio)
    print(f"\n   • Segmental SNR: {seg_snr:.2f} dB")
    print(f"     Frame-based SNR averaging for non-stationary signals")
    
    lsd = metrics_calculator.compute_spectral_distortion(audio, processed_audio)
    print(f"\n   • Log-Spectral Distortion: {lsd:.2f} dB")
    print(f"     Formula: LSD = sqrt(mean((20*log|X| - 20*log|Y|)²))")
    
    correlation = metrics_calculator.compute_waveform_similarity(audio, processed_audio)
    print(f"\n   • Waveform Correlation: {correlation:.4f}")
    print(f"     Pearson correlation coefficient")
    
    is_dist = metrics_calculator.compute_itakura_saito(audio, processed_audio)
    print(f"\n   • Itakura-Saito Distance: {is_dist:.4f}")
    print(f"     Perceptually-motivated spectral divergence")
    
    env_dist = metrics_calculator.compute_envelope_distance(audio, processed_audio)
    print(f"\n   • Envelope Distance: {env_dist:.4f}")
    print(f"     Hilbert transform-based amplitude envelope comparison")
    
    # Comprehensive evaluation
    print("\n" + "-" * 80)
    print("COMPREHENSIVE EVALUATION REPORT")
    print("-" * 80)
    
    full_metrics = metrics_calculator.comprehensive_evaluation(
        reference_clean=audio,  # Using original as reference for demo
        original_noisy=audio,
        processed=restored_audio
    )
    
    print("\nComplete Metrics Suite:")
    for metric_name, value in full_metrics.items():
        if 'score' in metric_name.lower():
            print(f"   🏆 {metric_name}: {value:.2f}/100")
        else:
            print(f"   • {metric_name}: {value:.4f}")
    
    # ========================================================================
    # SAVE OUTPUTS
    # ========================================================================
    print("\n" + "=" * 80)
    print("SAVING OUTPUTS")
    print("=" * 80)
    
    output_dir = Path("outputs/custom_demo")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    input_name = Path(input_audio_path).stem
    
    # Save processed audio
    output_path = output_dir / f"{input_name}_custom_processed.wav"
    sf.write(output_path, processed_audio, sample_rate)
    print(f"\n✓ Processed audio: {output_path}")
    
    # Save restored audio
    restored_path = output_dir / f"{input_name}_custom_restored.wav"
    sf.write(restored_path, restored_audio, sample_rate)
    print(f"✓ Restored audio: {restored_path}")
    
    # Save metrics report
    metrics_path = output_dir / f"{input_name}_metrics.txt"
    with open(metrics_path, 'w') as f:
        f.write("CUSTOM ALGORITHMIC PIPELINE - METRICS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write("AUDIO QUALITY PROFILE\n")
        f.write("-" * 80 + "\n")
        for key, value in profile.items():
            if isinstance(value, dict):
                f.write(f"{key}:\n")
                for k, v in value.items():
                    f.write(f"  {k}: {v}\n")
            else:
                f.write(f"{key}: {value}\n")
        
        f.write("\n\nQUALITY METRICS\n")
        f.write("-" * 80 + "\n")
        for metric_name, value in full_metrics.items():
            f.write(f"{metric_name}: {value:.6f}\n")
        
        f.write("\n\nROUTING STATISTICS\n")
        f.write("-" * 80 + "\n")
        for key, value in stats.items():
            f.write(f"{key}: {value}\n")
    
    print(f"✓ Metrics report: {metrics_path}")
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("SUMMARY: CUSTOM VS PRE-BUILT COMPONENTS")
    print("=" * 80)
    
    print("\n✅ CUSTOM CODE (Your Original Work):")
    print("   1. Audio Quality Profiler - 12 mathematical metrics")
    print("      • Wavelet-based noise variance estimation")
    print("      • Energy-based SNR calculation")
    print("      • Spectral flatness (Wiener entropy)")
    print("      • Frequency spectrum analysis via FFT")
    print("      • Zero-crossing rate")
    print("      • Crest factor computation")
    print()
    print("   2. Adaptive Router - Intelligent decision algorithm")
    print("      • SNR-based routing logic")
    print("      • Custom spectral subtraction (lightweight)")
    print("      • Custom Wiener filter (moderate)")
    print("      • Dynamic processor selection")
    print()
    print("   3. Spectral Restoration - DSP mathematics")
    print("      • Cepstral analysis for envelope extraction")
    print("      • Autocorrelation-based pitch detection")
    print("      • Harmonic synthesis from fundamentals")
    print("      • Perceptual A-weighting")
    print()
    print("   4. Quality Metrics - 9 from-scratch metrics")
    print("      • SNR, Segmental SNR, PSNR")
    print("      • MSE, Log-Spectral Distortion")
    print("      • Itakura-Saito distance")
    print("      • Waveform correlation")
    print("      • Envelope distance (Hilbert transform)")
    print("      • Noise reduction measurement")
    
    print("\n🔧 PRE-BUILT MODELS (Only for heavy noise):")
    print("   • DeepFilterNet3 - Deep learning noise removal")
    print("   (Used only when routing algorithm determines it's necessary)")
    
    print("\n" + "=" * 80)
    print("KEY DEMONSTRATION POINTS")
    print("=" * 80)
    
    print("""
📌 Key Points to Emphasize:

1. MATHEMATICAL FOUNDATION:
   "I implemented signal processing algorithms from first principles,
    including wavelet decomposition, FFT analysis, autocorrelation,
    cepstral analysis, and Hilbert transforms."

2. ADAPTIVE INTELLIGENCE:
   "My system doesn't blindly use the pre-trained model. I built an
    intelligent router that profiles each audio file and selects the
    optimal processing path - often using my lightweight custom filters
    instead of the heavy DNN."

3. POST-PROCESSING RESTORATION:
   "After noise removal, my spectral restoration module mathematically
    synthesizes missing harmonics using pitch detection and harmonic
    series synthesis - this is pure DSP math, not a learned model."

4. COMPREHENSIVE EVALUATION:
   "I didn't rely on sklearn or pre-built metrics. I implemented 9
    evaluation metrics from scratch using NumPy, including SNR, PSNR,
    Itakura-Saito distance, and spectral distortion measures."

5. ENGINEERING CONTRIBUTION:
   "The pre-built model is one component in a larger system I designed.
    My custom code provides intelligent routing, quality assessment,
    spectral analysis, and adaptive restoration - demonstrating both
    theoretical understanding and practical engineering skill."
    """)
    
    print("=" * 80)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    else:
        # Look for any audio file in outputs directory
        test_files = list(Path("outputs").glob("*.wav"))
        if test_files:
            input_path = str(test_files[0])
            print(f"Using test file: {input_path}")
        else:
            print("Usage: python examples/custom_integration.py <audio_file.wav>")
            print("\nNo audio files found in outputs directory.")
            print("Please run the pipeline first to generate test files.")
            sys.exit(1)
    
    demonstrate_custom_pipeline(input_path)
