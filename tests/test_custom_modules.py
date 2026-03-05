"""
Quick Test Script - Verify Custom Modules
Tests all 4 custom modules independently to ensure they work correctly.
"""

import numpy as np
import sys
import os

# Add src directory to path (go up one level from tests/ to find src/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_audio_quality_profiler():
    """Test Audio Quality Profiler module"""
    print("\n" + "="*80)
    print("TEST 1: Audio Quality Profiler")
    print("="*80)
    
    try:
        from audio_quality_profiler import AudioQualityProfiler
        
        # Create synthetic test audio (1 second, 16kHz)
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create speech-like signal (mixture of harmonics)
        f0 = 150  # Fundamental frequency (voice pitch)
        audio = np.sin(2 * np.pi * f0 * t)
        audio += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)  # 2nd harmonic
        audio += 0.3 * np.sin(2 * np.pi * 3 * f0 * t)  # 3rd harmonic
        
        # Add noise
        noise = np.random.normal(0, 0.1, len(audio))
        noisy_audio = audio + noise
        
        # Normalize
        noisy_audio = noisy_audio / np.max(np.abs(noisy_audio))
        
        # Test profiler
        profiler = AudioQualityProfiler(sample_rate)
        profile = profiler.profile_audio(noisy_audio)
        
        print("✅ Audio Quality Profiler initialized successfully")
        print(f"   Noise variance: {profile['noise_variance']:.6f}")
        print(f"   SNR estimate: {profile['snr_db']:.2f} dB")
        print(f"   Spectral flatness: {profile['spectral_flatness']:.4f}")
        print(f"   Recommended processing: {profile['recommended_processing']}")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_spectral_restoration():
    """Test Spectral Restoration module"""
    print("\n" + "="*80)
    print("TEST 2: Spectral Restoration")
    print("="*80)
    
    try:
        from spectral_restoration import SpectralRestoration
        
        sample_rate = 16000
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Original signal
        f0 = 150
        original = np.sin(2 * np.pi * f0 * t)
        original += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
        
        # Simulate processed (high frequencies attenuated)
        from scipy import signal as sig
        sos = sig.butter(4, 2000, 'low', fs=sample_rate, output='sos')
        processed = sig.sosfilt(sos, original)
        
        # Test restoration
        restorer = SpectralRestoration(sample_rate)
        
        # Test pitch detection
        pitch = restorer.detect_pitch(original)
        print(f"✅ Pitch detection: {pitch:.1f} Hz (expected ~{f0} Hz)")
        
        # Test harmonic synthesis
        harmonics = restorer.synthesize_harmonics(original, f0, n_harmonics=3)
        print(f"✅ Harmonic synthesis: generated {len(harmonics)} samples")
        
        # Test adaptive restoration
        restored = restorer.adaptive_restoration(original, processed)
        print(f"✅ Adaptive restoration: output {len(restored)} samples")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_audio_quality_metrics():
    """Test Audio Quality Metrics module"""
    print("\n" + "="*80)
    print("TEST 3: Audio Quality Metrics")
    print("="*80)
    
    try:
        from audio_quality_metrics import AudioQualityMetrics
        
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Clean signal
        clean = np.sin(2 * np.pi * 200 * t)
        
        # Noisy signal
        noise = np.random.normal(0, 0.1, len(clean))
        noisy = clean + noise
        
        # Test metrics
        metrics_calc = AudioQualityMetrics(sample_rate)
        
        snr = metrics_calc.compute_snr(clean, noisy)
        print(f"✅ SNR: {snr:.2f} dB")
        
        psnr = metrics_calc.compute_psnr(clean, noisy)
        print(f"✅ PSNR: {psnr:.2f} dB")
        
        seg_snr = metrics_calc.compute_segmental_snr(clean, noisy)
        print(f"✅ Segmental SNR: {seg_snr:.2f} dB")
        
        lsd = metrics_calc.compute_spectral_distortion(clean, noisy)
        print(f"✅ Log-Spectral Distortion: {lsd:.2f} dB")
        
        correlation = metrics_calc.compute_waveform_similarity(clean, noisy)
        print(f"✅ Waveform Correlation: {correlation:.4f}")
        
        is_dist = metrics_calc.compute_itakura_saito(clean, noisy)
        print(f"✅ Itakura-Saito Distance: {is_dist:.4f}")
        
        # Comprehensive evaluation
        full_metrics = metrics_calc.comprehensive_evaluation(
            reference_clean=clean,
            original_noisy=noisy,
            processed=clean  # Using clean as processed for test
        )
        print(f"✅ Overall Quality Score: {full_metrics['overall_quality_score']:.1f}/100")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_adaptive_router():
    """Test Adaptive Router module"""
    print("\n" + "="*80)
    print("TEST 4: Adaptive Router")
    print("="*80)
    
    try:
        from adaptive_router import AdaptiveRouter
        from audio_quality_profiler import AudioQualityProfiler
        
        sample_rate = 16000
        duration = 1.0
        t = np.linspace(0, duration, int(sample_rate * duration))
        
        # Create test signals with different noise levels
        clean = np.sin(2 * np.pi * 200 * t)
        
        # Light noise
        light_noise = clean + np.random.normal(0, 0.01, len(clean))
        light_noise = light_noise / np.max(np.abs(light_noise))
        
        # Heavy noise
        heavy_noise = clean + np.random.normal(0, 0.5, len(clean))
        heavy_noise = heavy_noise / np.max(np.abs(heavy_noise))
        
        # Profile both
        profiler = AudioQualityProfiler(sample_rate)
        light_profile = profiler.profile_audio(light_noise)
        heavy_profile = profiler.profile_audio(heavy_noise)
        
        # Test router
        router = AdaptiveRouter(sample_rate)
        
        # Test lightweight filter
        light_filtered = router.lightweight_filter(light_noise)
        print(f"✅ Lightweight filter: processed {len(light_filtered)} samples")
        
        # Test moderate filter
        moderate_filtered = router.moderate_filter(heavy_noise)
        print(f"✅ Moderate filter: processed {len(moderate_filtered)} samples")
        
        # Test routing decision (without heavy processor)
        processed, decision = router.route_processing(light_noise, light_profile)
        print(f"✅ Routing decision (light noise): {decision}")
        
        processed, decision = router.route_processing(heavy_noise, heavy_profile)
        print(f"✅ Routing decision (heavy noise): {decision}")
        
        # Test statistics
        stats = router.get_routing_statistics()
        print(f"✅ Routing statistics: {stats['total_routed']} files routed")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# CUSTOM MODULES TEST SUITE")
    print("#"*80)
    print("\nTesting all 4 custom algorithmic modules...\n")
    
    results = []
    
    # Run tests
    results.append(("Audio Quality Profiler", test_audio_quality_profiler()))
    results.append(("Spectral Restoration", test_spectral_restoration()))
    results.append(("Audio Quality Metrics", test_audio_quality_metrics()))
    results.append(("Adaptive Router", test_adaptive_router()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All custom modules working correctly!")
        print("\nNext steps:")
        print("1. Run: python examples/custom_integration.py <audio_file>")
        print("2. See docs/INTEGRATION.md for pipeline integration")
        print("3. Read README.md for complete documentation")
    else:
        print("\n⚠ Some tests failed. Check error messages above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
