"""Unit tests for ASRProcessor (faster-whisper wrapper) using a fake model."""

import json
import sys
import types
from types import SimpleNamespace as NS

import numpy as np
import pytest

from src.asr_processor import ASRProcessor


def _fake_whisper_module(model_factory):
    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = model_factory
    return mod


class FakeModel:
    calls = []

    def __init__(self, size, **kwargs):
        FakeModel.calls.append((size, kwargs))
        self.size = size

    def transcribe(self, path, **kwargs):
        words = [NS(word=" hello", start=0.0, end=0.5, probability=0.9)]
        segs = [
            NS(
                id=0,
                start=0.0,
                end=2.0,
                text=" hello there",
                avg_logprob=-0.2,
                words=words,
            ),
            NS(id=1, start=2.0, end=3.5, text=" general", avg_logprob=-0.5, words=None),
        ]
        return iter(segs), NS(language="en", language_probability=0.99)


@pytest.fixture
def asr(monkeypatch):
    FakeModel.calls = []
    monkeypatch.setitem(sys.modules, "faster_whisper", _fake_whisper_module(FakeModel))
    return ASRProcessor(model_size="tiny", device="cpu")


class TestInitAndLoad:
    def test_turbo_alias_and_cpu_float16_downgrade(self, monkeypatch):
        monkeypatch.setitem(
            sys.modules, "faster_whisper", _fake_whisper_module(FakeModel)
        )
        p = ASRProcessor(model_size="turbo", device="cpu", compute_type="float16")
        assert p.model_size == "large-v3-turbo" and p.compute_type == "int8"

    def test_device_autodetect_uses_torch(self, monkeypatch):
        import torch

        monkeypatch.setitem(
            sys.modules, "faster_whisper", _fake_whisper_module(FakeModel)
        )
        monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
        assert ASRProcessor(device=None).device == "cpu"

    def test_oom_falls_back_to_base_model(self, monkeypatch):
        attempts = []

        def factory(size, **kw):
            attempts.append(size)
            if size != "base":
                raise MemoryError("out of memory")
            return FakeModel(size, **kw)

        monkeypatch.setitem(
            sys.modules, "faster_whisper", _fake_whisper_module(factory)
        )
        p = ASRProcessor(model_size="large-v3", device="cpu")
        assert attempts == ["large-v3", "base"] and p.model_size == "base"

    def test_unrecoverable_load_error_propagates(self, monkeypatch):
        def factory(size, **kw):
            raise ValueError("bad model")

        monkeypatch.setitem(
            sys.modules, "faster_whisper", _fake_whisper_module(factory)
        )
        with pytest.raises(ValueError):
            ASRProcessor(device="cpu")


class TestTranscribe:
    def test_builds_whisper_compatible_dict(self, asr):
        res = asr.transcribe("any.wav")
        assert "hello there" in res["text"] and "general" in res["text"]
        assert len(res["segments"]) == 2
        first = res["segments"][0]
        assert first["avg_logprob"] == -0.2
        assert (
            first["words"][0]["word"] == " hello"
            and first["words"][0]["probability"] == 0.9
        )
        assert "words" not in res["segments"][1]
        assert res["language"] == "en"

    def test_word_timestamps_off(self, asr):
        res = asr.transcribe("any.wav", word_timestamps=False)
        assert all("words" not in s for s in res["segments"])

    def test_errors_return_empty_result(self, asr):
        asr.model.transcribe = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("x"))
        assert asr.transcribe("any.wav") == {"text": "", "segments": []}

    def test_transcribe_array_cleans_temp_file(self, asr):
        seen = {}
        orig = asr.transcribe

        def spy(path, **kw):
            import os

            seen["path"] = path
            seen["existed"] = os.path.exists(path)
            return orig(path, **kw)

        asr.transcribe = spy
        res = asr.transcribe_array(np.zeros(1600, dtype=np.float32), 16000)
        import os

        assert seen["existed"] and not os.path.exists(seen["path"])
        assert res["segments"]


RESULT = {
    "text": "hello there general",
    "segments": [
        {"start": 0.0, "end": 2.5, "text": " hello there "},
        {"start": 3725.25, "end": 3726.0, "text": " general"},
    ],
}


class TestFormatting:
    def test_format_with_and_without_timestamps(self, asr):
        with_ts = asr.format_transcript(RESULT)
        assert with_ts.splitlines()[0] == "[0.00s - 2.50s] hello there"
        assert (
            asr.format_transcript(RESULT, include_timestamps=False)
            == "hello there\ngeneral"
        )

    def test_format_without_segments_returns_text(self, asr):
        assert asr.format_transcript({"text": "plain"}) == "plain"
        assert asr.format_transcript({}) == ""

    @pytest.mark.parametrize(
        "fmt,expected", [("srt", "01:02:05,250"), ("vtt", "01:02:05.250")]
    )
    def test_timestamp_formats(self, asr, fmt, expected):
        assert asr._format_timestamp(3725.25, fmt) == expected


class TestSaveTranscript:
    def test_txt_plain(self, asr, tmp_path):
        out = tmp_path / "t.txt"
        asr.save_transcript(RESULT, str(out))
        assert "[0.00s - 2.50s] hello there" in out.read_text(encoding="utf-8")

    def test_txt_with_diarization(self, asr, tmp_path):
        out = tmp_path / "t.txt"
        dia = [
            {"start": 0, "end": 3, "speaker": "SPEAKER_00"},
            {"start": 3700, "end": 3800, "speaker": "SPEAKER_01"},
        ]
        asr.save_transcript(RESULT, str(out), diarization=dia)
        lines = out.read_text(encoding="utf-8").splitlines()
        assert lines == ["[SPEAKER_00]  hello there ", "[SPEAKER_01]  general"]

    def test_json(self, asr, tmp_path):
        out = tmp_path / "t.json"
        asr.save_transcript(RESULT, str(out), format="json")
        assert (
            json.loads(out.read_text(encoding="utf-8"))["text"] == "hello there general"
        )

    def test_srt(self, asr, tmp_path):
        out = tmp_path / "t.srt"
        asr.save_transcript(RESULT, str(out), format="srt")
        text = out.read_text(encoding="utf-8")
        assert text.startswith("1\n00:00:00,000 --> 00:00:02,500\nhello there")
        assert "2\n01:02:05,250 --> 01:02:06,000\ngeneral" in text

    def test_vtt(self, asr, tmp_path):
        out = tmp_path / "t.vtt"
        asr.save_transcript(RESULT, str(out), format="vtt")
        text = out.read_text(encoding="utf-8")
        assert text.startswith("WEBVTT")
        assert "00:00:00.000 --> 00:00:02.500" in text
