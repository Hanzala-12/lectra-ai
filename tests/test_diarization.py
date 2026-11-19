"""Unit tests for SpeakerDiarization using a fake pyannote pipeline."""

import sys
import types
from types import SimpleNamespace as NS

import numpy as np
import pytest
import soundfile as sf
import torch

from src import diarization as dz
from src.diarization import SpeakerDiarization


class FakeAnnotation:
    def __init__(self, turns):
        self._turns = turns

    def itertracks(self, yield_label=False):
        for start, end, spk in self._turns:
            yield NS(start=start, end=end), None, spk

    def labels(self):
        return sorted({t[2] for t in self._turns})


TURNS = [(0.0, 1.0, "SPEAKER_00"), (1.0, 2.5, "SPEAKER_01"), (2.5, 3.0, "SPEAKER_00")]


@pytest.fixture
def wav(tmp_path):
    p = tmp_path / "a.wav"
    sf.write(str(p), np.zeros(16000, dtype=np.float32), 16000)
    return str(p)


def make(pipeline, monkeypatch):
    monkeypatch.setattr(SpeakerDiarization, "_load_model", lambda self: None)
    d = SpeakerDiarization(min_speakers=1, max_speakers=4, device="cpu")
    d.pipeline = pipeline
    return d


class TestInit:
    def test_device_selection(self, monkeypatch):
        monkeypatch.setattr(SpeakerDiarization, "_load_model", lambda self: None)
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert SpeakerDiarization().device == "cpu"
        assert SpeakerDiarization(device="cuda").device == "cuda"

    def test_missing_token_disables_diarization(self, monkeypatch):
        """With no HF token the model load degrades to 'disabled', never crashes."""
        fake_pyannote = types.ModuleType("pyannote")
        fake_audio = types.ModuleType("pyannote.audio")
        fake_audio.Pipeline = object
        monkeypatch.setitem(sys.modules, "pyannote", fake_pyannote)
        monkeypatch.setitem(sys.modules, "pyannote.audio", fake_audio)
        monkeypatch.delenv("HF_TOKEN", raising=False)
        monkeypatch.delenv("HUGGING_FACE_HUB_TOKEN", raising=False)
        import huggingface_hub as hf

        # _load_model monkey-patches these globals; register them so pytest
        # restores the originals after the test.
        monkeypatch.setattr(torch, "load", torch.load)
        monkeypatch.setattr(hf, "hf_hub_download", hf.hf_hub_download)
        monkeypatch.setattr(hf, "snapshot_download", hf.snapshot_download)
        monkeypatch.setenv("HF_HOME", "")
        monkeypatch.setenv("TORCH_HOME", "")
        d = SpeakerDiarization(device="cpu")
        assert d.pipeline is None
        assert d.diarize("x.wav") == []
        assert d.diarize_with_embeddings("x.wav") == ([], {})


class TestDiarize:
    def test_returns_plain_segments(self, monkeypatch, wav):
        calls = {}

        def pipe(audio_input, **kw):
            calls["kw"], calls["sr"] = kw, audio_input["sample_rate"]
            assert audio_input["waveform"].shape[0] == 1  # (C, T)
            return FakeAnnotation(TURNS)

        d = make(pipe, monkeypatch)
        segs = d.diarize(wav)
        assert segs[1] == {"start": 1.0, "end": 2.5, "speaker": "SPEAKER_01"}
        assert calls["kw"] == {"min_speakers": 1, "max_speakers": 4}
        assert calls["sr"] == 16000

    def test_pipeline_error_returns_empty(self, monkeypatch, wav):
        def pipe(*a, **k):
            raise RuntimeError("cuda oom")

        assert make(pipe, monkeypatch).diarize(wav) == []

    def test_unreadable_file_returns_empty(self, monkeypatch, tmp_path):
        d = make(lambda *a, **k: FakeAnnotation(TURNS), monkeypatch)
        assert d.diarize(str(tmp_path / "missing.wav")) == []


class TestEmbeddings:
    def test_maps_labels_to_embeddings(self, monkeypatch, wav):
        emb = np.array([[1.0, 0.0], [0.0, 1.0]])
        d = make(lambda *a, **k: (FakeAnnotation(TURNS), emb), monkeypatch)
        segs, speakers = d.diarize_with_embeddings(wav)
        assert len(segs) == 3
        assert set(speakers) == {"SPEAKER_00", "SPEAKER_01"}
        assert np.array_equal(speakers["SPEAKER_01"], emb[1])

    def test_none_embeddings_yield_empty_map(self, monkeypatch, wav):
        d = make(lambda *a, **k: (FakeAnnotation(TURNS), None), monkeypatch)
        segs, speakers = d.diarize_with_embeddings(wav)
        assert len(segs) == 3 and speakers == {}

    def test_failure_falls_back_to_plain_diarize(self, monkeypatch, wav):
        def pipe(audio_input, **kw):
            if kw.get("return_embeddings"):
                raise TypeError("unsupported")
            return FakeAnnotation(TURNS)

        segs, speakers = make(pipe, monkeypatch).diarize_with_embeddings(wav)
        assert len(segs) == 3 and speakers == {}


def test_speaker_statistics(monkeypatch):
    d = make(None, monkeypatch)
    stats = d.get_speaker_statistics(
        [
            {"start": 0, "end": 1, "speaker": "A"},
            {"start": 1, "end": 3.5, "speaker": "B"},
            {"start": 4, "end": 5, "speaker": "A"},
        ]
    )
    assert stats == {"A": 2.0, "B": 2.5}
    assert d.get_speaker_statistics([]) == {}


class TestTorchaudioShim:
    def test_adds_missing_legacy_api(self, monkeypatch):
        fake = types.ModuleType("torchaudio")
        monkeypatch.setitem(sys.modules, "torchaudio", fake)
        dz._shim_torchaudio_legacy_api()
        assert fake.list_audio_backends() == ["soundfile"]
        assert fake.get_audio_backend() == "soundfile"
        assert fake.set_audio_backend("x") is None
        meta = fake.AudioMetaData(16000, 100, 1)
        assert (meta.sample_rate, meta.num_frames, meta.num_channels) == (16000, 100, 1)

    def test_leaves_existing_api_alone(self, monkeypatch):
        fake = types.ModuleType("torchaudio")
        fake.AudioMetaData = "real"
        fake.list_audio_backends = lambda: ["sox"]
        monkeypatch.setitem(sys.modules, "torchaudio", fake)
        dz._shim_torchaudio_legacy_api()
        assert fake.AudioMetaData == "real" and fake.list_audio_backends() == ["sox"]
