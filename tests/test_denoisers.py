"""Unit tests for the DeepFilterNet and MetricGAN+ wrappers using fake models."""

import os
import sys
import types

import numpy as np
import pytest
import torch

from src import deepfilter_processor as dfp
from src import metricgan_processor as mgp
from src.deepfilter_processor import DeepFilterProcessor, _force_cpu_for_df
from src.metricgan_processor import MetricGANProcessor


# ---------------------------------------------------------------- DeepFilter
class FakeState:
    def sr(self):
        return 48000


def make_df(double_pass=False, sample_rate=48000):
    p = DeepFilterProcessor.__new__(DeepFilterProcessor)
    p.model_name, p.post_filter, p.double_pass = "DeepFilterNet3", True, double_pass
    p.atten_lim_db, p.device, p.sample_rate = 100.0, "cpu", sample_rate
    p.model, p.df_state = object(), FakeState()
    p.calls = []

    def enhance(model, state, tensor, atten_lim_db):
        p.calls.append(atten_lim_db)
        return tensor * 0.5

    p.enhance = enhance
    return p


class TestForceCpu:
    def test_cuda_reported_unavailable_inside_and_restored_after(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        with _force_cpu_for_df():
            assert torch.cuda.is_available() is False
        assert torch.cuda.is_available() is True

    def test_restored_even_on_exception(self, monkeypatch):
        monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
        with pytest.raises(RuntimeError):
            with _force_cpu_for_df():
                raise RuntimeError("boom")
        assert torch.cuda.is_available() is True


class TestDeepFilterProcessing:
    def test_native_single_and_double_pass(self):
        audio = np.ones(4800, dtype=np.float32)
        single = make_df().process_audio_native(audio)
        assert single.dtype == np.float32 and np.allclose(single, 0.5)
        p = make_df(double_pass=True)
        assert np.allclose(p.process_audio_native(audio), 0.25)
        assert len(p.calls) == 2

    def test_process_audio_at_native_rate_skips_resampling(self):
        out = make_df().process_audio(np.ones(4800, dtype=np.float32), 48000)
        assert out.shape == (4800,) and np.allclose(out, 0.5)

    def test_process_audio_resamples_and_restores_rate(self):
        t = np.arange(16000) / 16000
        audio = (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        out = make_df(double_pass=True).process_audio(audio, 16000)
        assert abs(len(out) - len(audio)) <= 2
        assert np.max(np.abs(out)) == pytest.approx(0.075, abs=0.02)  # 0.3 * 0.5 * 0.5

    def test_process_segments_only_changes_requested_ranges(self):
        audio = np.ones(48000, dtype=np.float32)
        out = make_df().process_segments(audio, 48000, [(4800, 9600), (19200, 24000)])
        assert np.allclose(out[:4800], 1.0) and np.allclose(out[4800:9600], 0.5)
        assert np.allclose(out[9600:19200], 1.0) and np.allclose(out[19200:24000], 0.5)
        assert np.allclose(audio, 1.0)  # input untouched

    def test_many_segments_logs_progress_without_error(self):
        audio = np.ones(48000, dtype=np.float32)
        segs = [(i * 1000, i * 1000 + 500) for i in range(11)]
        assert make_df().process_segments(audio, 48000, segs).shape == audio.shape


class TestLoadModel:
    def _install_fake_df(self, monkeypatch, tmp_path, state_sr=48000):
        calls = {}

        class FakeNet:
            def to(self, device):
                calls["device"] = device

        def init_df(
            model_base_dir=None, post_filter=False, config_allow_defaults=False
        ):
            calls["base_dir"] = model_base_dir
            return FakeNet(), FakeState(), None

        df = types.ModuleType("df")
        enh = types.ModuleType("df.enhance")
        enh.init_df, enh.enhance = init_df, lambda *a, **k: None
        df.enhance, df.config = enh, types.ModuleType("df.config")
        monkeypatch.setitem(sys.modules, "df", df)
        monkeypatch.setitem(sys.modules, "df.enhance", enh)
        monkeypatch.setitem(sys.modules, "df.config", df.config)
        monkeypatch.setattr(dfp, "_shim_torchaudio_backend", lambda: None)
        return calls

    def test_loads_model_and_reads_sample_rate(self, monkeypatch, tmp_path):
        calls = self._install_fake_df(monkeypatch, tmp_path)
        p = DeepFilterProcessor(device="cuda")  # request ignored: always CPU
        assert p.device == "cpu" and p.sample_rate == 48000
        assert calls["device"] == "cpu"

    def test_import_failure_propagates(self, monkeypatch):
        monkeypatch.setattr(dfp, "_shim_torchaudio_backend", lambda: None)
        monkeypatch.setitem(sys.modules, "df.enhance", None)  # forces ImportError
        with pytest.raises(ImportError):
            DeepFilterProcessor()


class TestTorchaudioBackendShim:
    def test_installs_stand_in_when_real_module_missing(self, monkeypatch):
        names = ("torchaudio.backend", "torchaudio.backend.common")
        saved = {n: sys.modules.pop(n, None) for n in names}
        real_import = __import__

        def fake_import(name, *a, **k):
            if name == "torchaudio.backend.common":
                raise ModuleNotFoundError(name)
            return real_import(name, *a, **k)

        try:
            with monkeypatch.context() as m:
                m.setattr("builtins.__import__", fake_import)
                dfp._shim_torchaudio_backend()
            meta = sys.modules["torchaudio.backend.common"].AudioMetaData(48000, 10, 1)
            assert meta.sample_rate == 48000 and meta.encoding == ""
        finally:
            for n in names:
                sys.modules.pop(n, None)
                if saved[n] is not None:
                    sys.modules[n] = saved[n]

    def test_noop_when_real_module_exists(self, monkeypatch):
        sentinel = types.ModuleType("torchaudio.backend.common")
        monkeypatch.setitem(sys.modules, "torchaudio.backend.common", sentinel)
        monkeypatch.setitem(
            sys.modules, "torchaudio.backend", types.ModuleType("torchaudio.backend")
        )
        dfp._shim_torchaudio_backend()
        assert sys.modules["torchaudio.backend.common"] is sentinel


# ------------------------------------------------------------------ MetricGAN
class FakeEnhancer:
    def __init__(self):
        self.calls = 0

    def enhance_batch(self, batch, lengths):
        self.calls += 1
        return batch * 0.5


def make_mg(chunk_seconds=30.0):
    p = MetricGANProcessor.__new__(MetricGANProcessor)
    p.device, p.sample_rate, p.chunk_seconds, p._torch = (
        "cpu",
        16000,
        chunk_seconds,
        torch,
    )
    p.model = FakeEnhancer()
    return p


class TestMetricGANEnhance:
    def test_empty_audio(self):
        assert len(make_mg().enhance(np.array([], dtype=np.float32))) == 0

    def test_short_audio_single_call(self):
        p = make_mg()
        out = p.enhance(np.ones(8000, dtype=np.float64))
        assert out.dtype == np.float32 and np.allclose(out, 0.5) and p.model.calls == 1

    def test_long_audio_is_chunked_with_seamless_crossfade(self):
        p = make_mg(chunk_seconds=1.0)  # 16000-sample chunks, 8000-sample overlap
        audio = np.ones(16000 * 3, dtype=np.float32)
        out = p.enhance(audio)
        assert p.model.calls > 1
        assert out.shape == audio.shape
        assert np.allclose(out, 0.5, atol=1e-4)  # overlap-add weights normalise out

    def test_output_never_longer_than_input(self):
        p = make_mg()
        p.model.enhance_batch = lambda batch, lengths: torch.cat([batch, batch], dim=1)
        assert len(p._enhance_one(np.ones(100, dtype=np.float32))) == 100


class TestCompatPatches:
    def test_symlink_falls_back_to_copy(self, monkeypatch, tmp_path):
        monkeypatch.setattr(os, "symlink", os.symlink)  # restore after test

        def deny(*a, **k):
            raise OSError("no privilege")

        monkeypatch.setattr(os, "symlink", deny)
        mgp._install_compat_patches()
        src = tmp_path / "a.txt"
        src.write_text("hello")
        os.symlink(str(src), str(tmp_path / "b.txt"))
        assert (tmp_path / "b.txt").read_text() == "hello"
        srcdir = tmp_path / "d"
        srcdir.mkdir()
        (srcdir / "f.txt").write_text("x")
        os.symlink(str(srcdir), str(tmp_path / "d2"))
        assert (tmp_path / "d2" / "f.txt").read_text() == "x"
        os.symlink(str(src), str(src))  # SameFileError is swallowed

    def test_hf_wrappers_drop_use_auth_token(self, monkeypatch):
        import huggingface_hub as hf

        seen = {}
        monkeypatch.setattr(os, "symlink", os.symlink)
        monkeypatch.setattr(hf, "hf_hub_download", lambda *a, **k: seen.update(k))
        monkeypatch.setattr(hf, "snapshot_download", hf.snapshot_download)
        mgp._install_compat_patches()
        hf.hf_hub_download("repo", "file", use_auth_token="secret", token="t")
        assert "use_auth_token" not in seen and seen["token"] == "t"
