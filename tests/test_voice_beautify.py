"""Unit tests for the Voice Beautify post-processing stage (pure DSP)."""

import numpy as np
import pytest

from src.voice_beautify import VoiceBeautifier, _peaking, _shelf

SR = 16000


def _voiced(seconds, freq=180.0, amp=0.3, seed=0):
    t = np.arange(int(seconds * SR)) / SR
    y = sum(np.sin(2 * np.pi * freq * k * t) / k for k in range(1, 12))
    y *= 0.6 + 0.4 * np.sin(2 * np.pi * 3 * t)
    y = amp * y / np.max(np.abs(y))
    return y.astype(np.float32)


def _scene(noise_amp=0.0005):
    """1 s silence, 2 s voice, 1 s silence, 2 s voice, 1 s silence + faint floor."""
    rng = np.random.default_rng(1)
    z = lambda s: np.zeros(int(s * SR), dtype=np.float32)  # noqa: E731
    audio = np.concatenate([z(1), _voiced(2), z(1), _voiced(2, amp=0.1), z(1)])
    audio = audio + rng.normal(0, noise_amp, len(audio)).astype(np.float32)
    segments = [(1 * SR, 3 * SR), (4 * SR, 6 * SR)]
    return audio.astype(np.float32), segments


def _cfg(**overrides):
    base = {
        "beautify": {
            "enabled": True,
            "air": {"enabled": False},
        }
    }
    base["beautify"].update(overrides)
    return base


class TestFilters:
    def test_peaking_biquad_gain_at_centre(self):
        b, a = _peaking(1000, 6.0, 1.0, SR)
        from scipy.signal import freqz

        w, h = freqz(b, a, worN=[2 * np.pi * 1000 / SR])
        assert 20 * np.log10(abs(h[0])) == pytest.approx(6.0, abs=0.2)

    @pytest.mark.parametrize("kind", ["low", "high"])
    def test_shelf_is_stable(self, kind):
        b, a = _shelf(300, 3.0, SR, kind)
        assert np.all(np.abs(np.roots(a)) < 1.0)


class TestConfigAndGuards:
    def test_defaults_and_overrides(self):
        vb = VoiceBeautifier(
            {
                "beautify": {
                    "enabled": True,
                    "target_loudness_dbfs": -16,
                    "leveler": {"strength": 0.4},
                    "air": {"output_sr": 32000},
                }
            },
            SR,
        )
        assert vb.enabled and vb.target_dbfs == -16
        assert vb.lev_strength == 0.4 and vb.air_out_sr == 32000
        assert VoiceBeautifier(None).enabled is False

    def test_disabled_returns_input_untouched(self):
        audio, segs = _scene()
        out, sr = VoiceBeautifier({"beautify": {"enabled": False}}, SR).process(
            audio, segs
        )
        assert out is audio and sr == SR

    def test_merge_segments(self):
        vb = VoiceBeautifier(_cfg(), SR)
        assert vb._merge_segments([]) == []
        merged = vb._merge_segments([(0, 100), (150, 300), (SR * 2, SR * 3), (5, 5)])
        assert merged == [(0, 300), (SR * 2, SR * 3)]

    def test_metrics_on_silence(self):
        vb = VoiceBeautifier(_cfg(), SR)
        silence = np.zeros(SR, dtype=np.float32)
        assert vb._noise_floor_db(silence) == -120.0
        assert vb._snr_db(silence) == 120.0


class TestStages:
    def test_tone_is_linear_and_finite(self):
        vb = VoiceBeautifier(_cfg(), SR)
        y = _voiced(1.0)
        out = vb._tone(y)
        assert out.shape == y.shape and np.all(np.isfinite(out))
        assert np.allclose(vb._tone(2 * y), 2 * out, atol=1e-4)  # linearity

    def test_leveler_never_boosts(self):
        vb = VoiceBeautifier(_cfg(), SR)
        audio, _ = _scene()
        out = vb._level(audio)
        # downward-only compression: no sample may grow beyond float tolerance
        assert np.all(np.abs(out) <= np.abs(audio) + 1e-6)
        assert vb._loudness_spread_db(out) <= vb._loudness_spread_db(audio) + 1e-6

    def test_leveler_skips_when_nothing_is_active(self):
        vb = VoiceBeautifier(_cfg(), SR)
        quiet = np.full(SR, 1e-6, dtype=np.float32)
        assert vb._level(quiet) is quiet

    def test_loudness_and_peak_limit(self):
        vb = VoiceBeautifier(_cfg(), SR)
        loud = _voiced(1.0, amp=0.99) * 3
        assert np.max(np.abs(vb._loudness_limit(loud))) <= 0.97 + 1e-6
        assert vb._loudness_limit(np.zeros(100, dtype=np.float32)).shape == (100,)
        assert vb._loudness_limit(np.array([], dtype=np.float32)).size == 0

    def test_remask_silences_outside_speech(self):
        vb = VoiceBeautifier(_cfg(), SR)
        y = np.ones(4 * SR, dtype=np.float32)
        out = vb._remask(y, [(SR, 2 * SR)], SR)
        assert np.all(out[:SR] == 0) and np.all(out[2 * SR :] == 0)
        assert out[SR + SR // 2] == pytest.approx(1.0)
        assert out[SR] < 1e-3  # faded edge

    def test_speech_mask_shape_and_values(self):
        vb = VoiceBeautifier(_cfg(), SR)
        m = vb._speech_mask(3 * SR, [(SR, 2 * SR), (5, 5)], SR)
        assert m[SR + SR // 2] == 1.0 and m[0] == 0.0 and m[-1] == 0.0

    def test_air_extends_to_higher_sample_rate(self):
        vb = VoiceBeautifier(
            {"beautify": {"enabled": True, "air": {"enabled": True}}}, SR
        )
        rng = np.random.default_rng(3)
        y = (_voiced(3.0) + rng.normal(0, 0.05, 3 * SR)).astype(np.float32)
        out, out_sr = vb._add_air(y, [(0, 3 * SR)])
        assert out_sr == 24000 and len(out) == 3 * 24000

    def test_air_skipped_for_band_limited_input(self):
        vb = VoiceBeautifier(
            {"beautify": {"enabled": True, "air": {"enabled": True}}}, SR
        )
        low = _voiced(1.0, freq=120.0)
        from scipy.signal import butter, sosfilt

        low = sosfilt(butter(6, 1500, output="sos", fs=SR), low).astype(np.float32)
        out, out_sr = vb._add_air(low, [(0, SR)])
        assert out_sr == 24000 and len(out) == 24000


class TestProcess:
    def test_full_chain_without_air(self):
        audio, segs = _scene()
        out, sr = VoiceBeautifier(_cfg(), SR).process(audio, segs)
        assert sr == SR and len(out) == len(audio)
        assert np.max(np.abs(out)) <= 0.97 + 1e-6
        # silence guarantee: gaps outside speech are exactly zero
        assert np.all(out[: SR - 200] == 0)
        assert np.all(out[3 * SR + 200 : 4 * SR - 200] == 0)

    def test_full_chain_with_air_raises_sample_rate(self):
        audio, segs = _scene()
        cfg = {
            "beautify": {
                "enabled": True,
                "air": {"enabled": True},
                "max_snr_drop_db": 60,
            }
        }
        out, sr = VoiceBeautifier(cfg, SR).process(audio, segs)
        assert sr in (SR, 24000) and len(out) > 0 and np.all(np.isfinite(out))

    def test_snr_guard_falls_back_to_input(self):
        audio, segs = _scene()
        vb = VoiceBeautifier(_cfg(max_snr_drop_db=-100.0), SR)  # impossible to satisfy
        out, sr = vb.process(audio, segs)
        assert sr == SR and np.array_equal(out, audio.astype(np.float32))
