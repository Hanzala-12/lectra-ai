"""Extra unit tests for the optional DSP modules (adaptive router, spectral
restoration, optimized utilities) and the study-plan repository."""

import time

import numpy as np
import pytest

from src import adaptive_router as ar
from src import optimized_utils as ou
from src.adaptive_router import AdaptiveRouter
from src.spectral_restoration import SpectralRestoration
from src.study_plan_repository import StudyPlanRepository

SR = 16000


def _noisy_speech(seconds=2.0, noise=0.05, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * SR)) / SR
    voiced = 0.3 * np.sin(2 * np.pi * 180 * t) * (np.arange(len(t)) > SR // 5)
    return (voiced + rng.normal(0, noise, len(t))).astype(np.float32)


# ----------------------------------------------------------- adaptive router
class TestAdaptiveRouter:
    @pytest.mark.parametrize(
        "snr,method",
        [
            (25.0, "spectral_subtraction"),
            (10.0, "wiener_filter"),
            (2.0, "deepfilternet_required"),
        ],
    )
    def test_routing_by_snr(self, snr, method):
        audio = _noisy_speech()
        out, chosen = AdaptiveRouter(SR).route_processing(audio, {"snr_db": snr})
        assert chosen == method and out.shape == audio.shape and out.dtype == np.float32
        if method == "deepfilternet_required":
            assert out is audio  # untouched: caller must use DeepFilterNet

    def test_missing_snr_defaults_to_medium_noise(self):
        _, chosen = AdaptiveRouter(SR).route_processing(_noisy_speech(), {})
        assert chosen == "wiener_filter"

    def test_custom_spectral_subtraction_reduces_noise_floor(self):
        router = AdaptiveRouter(SR)
        audio = _noisy_speech(noise=0.1)
        out = router._custom_spectral_subtraction(audio)
        assert out.shape == audio.shape
        assert np.std(out[: SR // 10]) < np.std(audio[: SR // 10])

    def test_noisereduce_failure_falls_back_to_custom(self, monkeypatch):
        class Broken:
            @staticmethod
            def reduce_noise(**kw):
                raise RuntimeError("nr failed")

        monkeypatch.setattr(ar, "NOISEREDUCE_AVAILABLE", True)
        monkeypatch.setattr(ar, "nr", Broken, raising=False)
        out = AdaptiveRouter(SR)._spectral_subtraction(_noisy_speech())
        assert out.dtype == np.float32

    def test_uses_noisereduce_when_available(self, monkeypatch):
        class Fake:
            @staticmethod
            def reduce_noise(y, **kw):
                return y * 0.5

        monkeypatch.setattr(ar, "NOISEREDUCE_AVAILABLE", True)
        monkeypatch.setattr(ar, "nr", Fake, raising=False)
        audio = _noisy_speech()
        assert np.allclose(AdaptiveRouter(SR)._spectral_subtraction(audio), audio * 0.5)

    def test_custom_path_when_noisereduce_missing(self, monkeypatch):
        monkeypatch.setattr(ar, "NOISEREDUCE_AVAILABLE", False)
        assert AdaptiveRouter(SR)._spectral_subtraction(_noisy_speech()).shape == (
            2 * SR,
        )

    @pytest.mark.parametrize("method", ["minimum", "first_frames"])
    def test_noise_spectrum_estimation(self, method):
        Zxx = np.abs(np.random.default_rng(1).normal(size=(513, 40))) + 0j
        est = AdaptiveRouter(SR)._estimate_noise_spectrum(Zxx, method)
        assert est.shape == (513, 1) and np.all(est >= 0)

    def test_descriptions(self):
        r = AdaptiveRouter(SR)
        assert "Wiener" in r.get_method_description("wiener_filter")
        assert r.get_method_description("???") == "Unknown method"


# ------------------------------------------------------ spectral restoration
class TestSpectralRestoration:
    def _pair(self):
        t = np.arange(2 * SR) / SR
        original = (
            sum(np.sin(2 * np.pi * 150 * k * t) / k for k in range(1, 30)).astype(
                np.float32
            )
            * 0.2
        )
        from scipy.signal import butter, sosfilt

        denoised = sosfilt(butter(4, 2500, output="sos", fs=SR), original).astype(
            np.float32
        )
        return original, denoised

    @pytest.mark.parametrize(
        "strength", ["auto", "light", "medium", "heavy", "unknown-value"]
    )
    def test_all_strength_modes_return_same_length(self, strength):
        original, denoised = self._pair()
        out = SpectralRestoration(SR).adaptive_restoration(
            original, denoised, strength=strength
        )
        assert len(out) == len(denoised) and np.all(np.isfinite(out))

    def test_restoration_does_not_reduce_high_band_energy(self):
        original, denoised = self._pair()
        out = SpectralRestoration(SR).adaptive_restoration(
            original, denoised, strength="heavy"
        )

        def hf(x):
            spectrum = np.abs(np.fft.rfft(x)) ** 2
            freqs = np.fft.rfftfreq(len(x), 1 / SR)
            return float(spectrum[freqs > 3000].sum())

        # Safety property only: the stage must never attenuate the denoised
        # signal. (On this synthetic input the measured gain is ~0, see QA
        # report observation OBS-7.)
        assert hf(out) >= 0.99 * hf(denoised)

    def test_unvoiced_noise_uses_envelope_path(self):
        rng = np.random.default_rng(5)
        original = rng.normal(0, 0.1, 2 * SR).astype(np.float32)
        denoised = (original * 0.4).astype(np.float32)
        sr = SpectralRestoration(SR)
        out = sr.adaptive_restoration(original, denoised, strength="medium")
        assert out.shape == denoised.shape

    def test_pitch_detection(self):
        t = np.arange(SR) / SR
        pure = (0.5 * np.sin(2 * np.pi * 200 * t)).astype(np.float64)
        pitch = SpectralRestoration(SR)._detect_pitch(pure)
        assert pitch == pytest.approx(200, rel=0.05)
        # white noise has no clear periodicity above the 0.3 threshold
        noise = np.random.default_rng(9).normal(size=SR)
        assert SpectralRestoration(SR)._detect_pitch(noise) is None

    def test_silent_original_gets_default_light_strength(self):
        silent = np.zeros(2 * SR, dtype=np.float32)
        assert (
            SpectralRestoration(SR)._estimate_restoration_strength(silent, silent)
            == 0.3
        )

    def test_different_lengths_are_aligned(self):
        original, denoised = self._pair()
        out = SpectralRestoration(SR).adaptive_restoration(
            original, denoised[:-1000], strength="light"
        )
        assert len(out) == len(denoised) - 1000


# ------------------------------------------------------------ optimized utils
class TestOptimizedUtils:
    def test_vectorised_helpers_match_numpy_reference(self):
        proc = ou.VectorizedAudioProcessor(SR)
        audio = _noisy_speech()
        energies = proc.compute_frame_energies_vectorized(audio, 512, 256)
        ref = ou._compute_frame_energies_numpy(audio, 512, 256)
        assert np.allclose(energies, ref, rtol=1e-3, atol=1e-6)
        rms = proc.fast_rms(audio, 512)
        assert np.allclose(rms, ou._fast_rms_numpy(audio, 512), rtol=1e-3, atol=1e-6)
        clean, noisy = audio, audio + 0.05
        assert proc.estimate_snr_numba(clean, noisy) == pytest.approx(
            ou._estimate_snr_numpy(clean, noisy), rel=1e-3
        )

    def test_numpy_fallbacks_are_used_when_numba_missing(self, monkeypatch):
        monkeypatch.setattr(ou, "NUMBA_AVAILABLE", False)
        proc = ou.VectorizedAudioProcessor(SR)
        audio = _noisy_speech(1.0)
        assert proc.compute_frame_energies_vectorized(audio).ndim == 1
        assert proc.fast_rms(audio).ndim == 1
        assert isinstance(proc.estimate_snr_numba(audio, audio + 0.1), float)
        results = proc.benchmark_optimizations(audio, n_iterations=2)
        assert set(results) == {"frame_energies", "snr_estimation", "rms_calculation"}
        assert all(r["speedup"] == 1.0 for r in results.values())
        assert "Numba not available" in proc.format_benchmark_results(results)

    def test_benchmark_with_numba_available(self):
        proc = ou.VectorizedAudioProcessor(SR)
        results = proc.benchmark_optimizations(_noisy_speech(1.0), n_iterations=3)
        for metrics in results.values():
            assert {"numpy_time_ms", "numba_time_ms", "speedup"} <= set(metrics)
            assert metrics["speedup"] > 0
        text = proc.format_benchmark_results(results)
        assert "Performance Benchmark Results" in text

    def test_benchmark_generates_audio_when_none_given(self):
        results = ou.VectorizedAudioProcessor(1000).benchmark_optimizations(
            n_iterations=1
        )
        assert "frame_energies" in results


# ---------------------------------------------------- study plan repository
class TestStudyPlanRepository:
    def test_create_get_and_latest(self, tmp_path):
        repo = StudyPlanRepository(str(tmp_path))
        first = repo.create("lec1", "stu1", [{"day": 1}], ["tip"], "2h", "pass exam")
        time.sleep(0.05)  # distinct created_at even on coarse Windows clocks
        second = repo.create("lec1", "stu1", [{"day": 2}], [])
        repo.create("lec2", "stu1", [], [])
        assert repo.get(first["id"])["learning_goals"] == "pass exam"
        assert repo.get("missing") is None
        assert len(repo.list_for_lecture("lec1")) == 2
        assert repo.get_latest_for_lecture("lec1")["id"] == second["id"]
        assert repo.get_latest_for_lecture("nothing") is None

    def test_ignores_corrupt_files_and_traversal(self, tmp_path):
        repo = StudyPlanRepository(str(tmp_path / "plans"))
        (tmp_path / "plans" / "bad.json").write_text("{oops", encoding="utf-8")
        (tmp_path / "plans" / "notes.txt").write_text("x", encoding="utf-8")
        repo.create("lec1", "s", [], [])
        assert len(repo.list_for_lecture("lec1")) == 1
        (tmp_path / "secret.json").write_text("{}", encoding="utf-8")
        assert repo.get("../secret") is None
