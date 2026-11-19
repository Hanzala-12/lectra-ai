"""Flow tests for LectraAIPipeline.process() with every heavy model replaced by
a fake: covers ASR / diarization attachment, optional DSP stages, video merge,
caching and batch processing without needing model weights."""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

import numpy as np
import pytest
import yaml

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pipeline as pipeline_module  # noqa: E402
from pipeline import (
    LectraAIPipeline,
    _load_optional_class,
    compute_adaptive_thresholds,
)  # noqa: E402

SR = 16000


def _speech_like(seconds=4.0, sr=SR):
    t = np.arange(int(seconds * sr)) / sr
    y = sum(np.sin(2 * np.pi * 150 * k * t) / k for k in range(1, 8))
    y *= 0.6 + 0.4 * np.sin(2 * np.pi * 3 * t)
    return (0.3 * y / np.max(np.abs(y))).astype(np.float32)


@pytest.fixture
def make_pipeline(tmp_path):
    def build(enable_cache=False, config_overrides=None, config_path=None):
        cfg = LectraAIPipeline._get_default_config(None)
        cfg["asr"]["skip"] = False
        for k, v in (config_overrides or {}).items():
            cfg[k] = v
        path = config_path or tmp_path / "cfg.yaml"
        if not config_path:
            path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        with patch("pipeline.DeepFilterProcessor") as dfn, patch(
            "pipeline.ASRProcessor"
        ), patch("pipeline.SpeakerDiarization") as dia:
            dfn.return_value = MagicMock()
            dia.return_value = MagicMock()
            p = LectraAIPipeline(str(path), enable_cache=enable_cache)
        # Fake the heavy parts and mark the optional-module init as done so the
        # test fully controls which optional stages run.
        p._custom_modules_initialized = True
        p.profiler = p.quality_metrics = p.spectral_restoration = None
        p.adaptive_router = p.target_voice_isolator = p.speaker_confidence_gate = None
        p.deepfilter = MagicMock(sample_rate=SR, atten_lim_db=30.0)
        p.deepfilter.process_audio_native = lambda x: x
        return p

    return build


def _arrange(p, audio=None, sr=SR, is_video=False, segments=None, diarization=None):
    audio = _speech_like() if audio is None else audio
    p.media_loader = MagicMock()
    p.media_loader.load_media.return_value = (audio, sr, is_video)
    p.vad_processor = MagicMock(min_speech_duration_ms=250, frame_duration_ms=30)
    p.vad_processor.trim_silence.return_value = (
        audio,
        (
            segments
            if segments is not None
            else [(int(0.5 * sr), len(audio) - int(0.5 * sr))]
        ),
    )
    if p.diarization is not None:
        p.diarization.diarize.return_value = diarization or []
        p.diarization.get_speaker_statistics.return_value = {"SPEAKER_00": 1.0}
    return audio


def _fake_asr(text=" hello world"):
    asr = MagicMock()
    asr.transcribe.return_value = {
        "text": text,
        "segments": [{"start": 1.0, "end": 3.0, "text": text, "avg_logprob": -0.1}],
    }
    asr.combine_with_diarization.side_effect = lambda t, d: [
        {"start": 1.0, "end": 3.0, "text": t["text"], "speaker": d[0]["speaker"]}
    ]
    return asr


DIA = [{"start": 0.5, "end": 3.5, "speaker": "SPEAKER_00"}]


class TestHelpers:
    def test_default_config_when_file_missing(self, tmp_path):
        with patch("pipeline.DeepFilterProcessor"), patch(
            "pipeline.SpeakerDiarization"
        ):
            p = LectraAIPipeline(str(tmp_path / "missing.yaml"), enable_cache=False)
        assert p.config["audio"]["sample_rate"] == 16000 and p.cache is None

    def test_optional_class_missing_module_returns_none(self):
        assert _load_optional_class("definitely_not_a_module", "Nope") is None

    def test_optional_class_found(self):
        assert _load_optional_class("voice_beautify", "VoiceBeautifier") is not None

    def test_adaptive_thresholds_for_silence_and_speech(self):
        quiet = compute_adaptive_thresholds(np.zeros(SR * 2, dtype=np.float32))
        speech = compute_adaptive_thresholds(_speech_like(6.0))
        for t in (quiet, speech):
            assert {
                "silence_threshold",
                "min_segment_ms",
                "merge_gap_ms",
                "tail_pad_ms",
            } <= set(t)
        assert (
            80 <= speech["min_segment_ms"] <= 250
            and 150 <= speech["merge_gap_ms"] <= 500
        )

    def test_merge_segments_clips_and_merges(self, make_pipeline):
        p = make_pipeline()
        assert p._merge_segments([], 100) == []
        merged = p._merge_segments(
            [(-5, 10), (12, 20), (50, 500), (30, 30)], 100, max_gap_samples=5
        )
        assert merged == [(0, 20), (50, 100)]


class TestProcessFlow:
    def test_full_flow_with_asr_and_speaker_labels(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p, diarization=DIA)
        p.asr = _fake_asr()
        res = p.process("lecture.wav", str(tmp_path / "out"), save_transcript=True)
        assert res["from_cache"] is False and res["is_video"] is False
        assert res["transcript"]["text"] == "[SPEAKER_00]  hello world"
        assert res["diarization"] == DIA and res["speech_segments"] >= 1
        assert res["duration_original"] == pytest.approx(4.0)
        p.asr.save_transcript.assert_called_once()
        p.media_loader.save_audio.assert_called_once()
        assert not (tmp_path / "out" / "lecture_temp.wav").exists()

    def test_asr_is_lazily_created_when_missing(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p)
        assert p.asr is None
        fake = _fake_asr()
        with patch("pipeline.ASRProcessor", return_value=fake) as cls:
            res = p.process("a.wav", str(tmp_path), save_transcript=False)
        cls.assert_called_once()
        assert (
            res["transcript"]["text"] == " hello world"
        )  # no diarization -> unlabelled
        fake.save_transcript.assert_not_called()

    def test_asr_skip_returns_empty_transcript(self, make_pipeline, tmp_path):
        p = make_pipeline()
        p.config["asr"]["skip"] = True
        _arrange(p)
        res = p.process("a.wav", str(tmp_path))
        assert res["transcript"] == {"text": "", "segments": []}

    def test_diarization_failure_falls_back_to_vad(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p)
        p.diarization.diarize.side_effect = RuntimeError("pyannote down")
        p.asr = _fake_asr()
        res = p.process("a.wav", str(tmp_path))
        assert res["diarization"] == []
        p.vad_processor.trim_silence.assert_called_once()

    def test_diarization_disabled(self, make_pipeline, tmp_path):
        p = make_pipeline(
            config_overrides={
                "diarization": {"enabled": False, "min_speakers": 1, "max_speakers": 2}
            }
        )
        assert p.diarization is None
        _arrange(p)
        p.asr = _fake_asr()
        assert p.process("a.wav", str(tmp_path))["diarization"] == []

    def test_long_audio_uses_chunked_deepfilter_path(self, make_pipeline, tmp_path):
        p = make_pipeline()
        p.deepfilter.sample_rate = 48000
        sr = 48000
        audio = (0.1 * np.sin(2 * np.pi * 220 * np.arange(sr * 70) / sr)).astype(
            np.float32
        )
        _arrange(p, audio=audio, sr=sr, segments=[(0, len(audio))])
        calls = []
        p.deepfilter.process_audio_native = lambda x: calls.append(len(x)) or x
        p.config["asr"]["skip"] = True
        res = p.process("long.wav", str(tmp_path))
        assert len(calls) > 1
        assert res["duration_processed"] == pytest.approx(70.0)


class TestOptionalStages:
    def test_all_enhancement_stages_run(self, make_pipeline, tmp_path):
        p = make_pipeline()
        audio = _arrange(p, diarization=DIA)
        p.asr = _fake_asr()
        p.neural_enhancer = MagicMock()
        p.neural_enhancer.enhance.side_effect = lambda a: a[
            :-100
        ]  # shorter -> padded back
        p.dry_wet_mix, p.dry_mix_hpf_hz = 0.3, 300.0
        p.low_band_denoise_enabled = True
        p.spectral_restoration = MagicMock()
        p.spectral_restoration.adaptive_restoration.side_effect = (
            lambda o, e, strength: e
        )
        p.beautifier = MagicMock()
        p.beautifier.process.side_effect = lambda a, s: (a, 24000)
        p.profiler = MagicMock()
        p.profiler.profile_audio.return_value = {"snr": 12}
        p.profiler.format_profile.return_value = "profile"
        p.quality_metrics = MagicMock()
        p.quality_metrics.comprehensive_evaluation.return_value = {"pesq": 3.0}
        p.quality_metrics.format_results.return_value = "metrics"
        p.adaptive_router = MagicMock()
        p.adaptive_router.route_processing.return_value = (
            np.zeros(len(audio), dtype=np.float32),
            "deepfilternet_required",
        )

        res = p.process("a.wav", str(tmp_path))
        assert res["audio_profile"] == {"snr": 12}
        assert res["processing_method"] == "deepfilternet_required"
        assert res["quality_metrics"] == {"pesq": 3.0}
        p.neural_enhancer.enhance.assert_called_once()
        assert (
            p.media_loader.save_audio.call_args.args[1] == 24000
        )  # beautify sample rate

    def test_plain_dry_wet_mix_without_hpf(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p)
        p.config["asr"]["skip"] = True
        p.dry_wet_mix, p.dry_mix_hpf_hz = 0.5, 0.0
        assert p.process("a.wav", str(tmp_path))["speech_segments"] >= 1

    def test_router_handling_audio_skips_deepfilter(self, make_pipeline, tmp_path):
        p = make_pipeline()
        audio = _arrange(p)
        p.config["asr"]["skip"] = True
        p.profiler = MagicMock()
        p.profiler.profile_audio.return_value = {"snr": 30}
        p.adaptive_router = MagicMock()
        p.adaptive_router.route_processing.return_value = (
            audio.copy(),
            "spectral_gate",
        )
        p.deepfilter.process_audio_native = Mock(
            side_effect=AssertionError("must not run")
        )
        res = p.process("a.wav", str(tmp_path))
        assert res["processing_method"] == "spectral_gate"

    def test_every_optional_stage_failure_is_survivable(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p)
        p.config["asr"]["skip"] = True
        boom = Mock(side_effect=RuntimeError("stage failed"))
        p.profiler = MagicMock(profile_audio=boom)
        p.neural_enhancer = MagicMock(enhance=boom)
        p.spectral_restoration = MagicMock(adaptive_restoration=boom)
        p.beautifier = MagicMock(process=boom)
        p.quality_metrics = MagicMock(comprehensive_evaluation=boom)
        p.target_voice_isolator = MagicMock(process=boom)
        p.speaker_confidence_gate = MagicMock(compute_gain_curve=boom)
        p.diarization.diarize_with_embeddings.return_value = (
            DIA,
            {"SPEAKER_00": np.zeros(4)},
        )
        res = p.process("a.wav", str(tmp_path))
        assert res["audio_output_path"].endswith("a_cleaned.wav")
        assert "audio_profile" not in res and "quality_metrics" not in res

    def test_router_exception_falls_back_to_deepfilter(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p)
        p.config["asr"]["skip"] = True
        p.profiler = MagicMock()
        p.profiler.profile_audio.return_value = {"snr": 5}
        p.adaptive_router = MagicMock()
        p.adaptive_router.route_processing.side_effect = RuntimeError("router bug")
        assert p.process("a.wav", str(tmp_path))["speech_segments"] >= 1

    def test_speaker_gain_curve_is_applied(self, make_pipeline, tmp_path):
        p = make_pipeline()
        audio = _arrange(p, diarization=DIA)
        p.config["asr"]["skip"] = True
        p.speaker_confidence_gate = MagicMock()
        p.speaker_confidence_gate.compute_gain_curve.return_value = np.full(
            len(audio), 0.5, dtype=np.float32
        )
        p.diarization.diarize_with_embeddings.return_value = (
            DIA,
            {"SPEAKER_00": np.zeros(4)},
        )
        p.process("a.wav", str(tmp_path))
        saved = p.media_loader.save_audio.call_args.args[0]
        assert saved.shape == audio.shape

    def test_target_voice_isolator_receives_embeddings(self, make_pipeline, tmp_path):
        p = make_pipeline()
        audio = _arrange(p, diarization=DIA)
        p.config["asr"]["skip"] = True
        p.target_voice_isolator = MagicMock()
        p.target_voice_isolator.process.side_effect = lambda a, sr, d, e: a
        p.diarization.diarize_with_embeddings.return_value = (
            DIA,
            {"SPEAKER_00": np.zeros(4)},
        )
        p.process("a.wav", str(tmp_path))
        p.target_voice_isolator.process.assert_called_once()


class TestVideoAndCache:
    def test_video_audio_is_merged_back(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p, is_video=True)
        p.config["asr"]["skip"] = True
        res = p.process("clip.mp4", str(tmp_path))
        p.media_loader.merge_audio_to_video.assert_called_once()
        assert res["is_video"] is True and res["video_output_path"].endswith(
            "clip_cleaned.mp4"
        )

    def test_video_merge_failure_is_logged_not_raised(self, make_pipeline, tmp_path):
        p = make_pipeline()
        _arrange(p, is_video=True)
        p.config["asr"]["skip"] = True
        p.media_loader.merge_audio_to_video.side_effect = RuntimeError("ffmpeg missing")
        assert p.process("clip.mp4", str(tmp_path))["is_video"] is True

    def test_second_run_is_served_from_cache(
        self, make_pipeline, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "lecture.wav"
        src.write_bytes(b"input-audio")
        p = make_pipeline(enable_cache=True)
        _arrange(p)
        p.config["asr"]["skip"] = True

        def fake_save(audio, sr, path, **kw):
            open(path, "wb").write(b"cleaned")

        p.media_loader.save_audio.side_effect = fake_save
        first = p.process(str(src), str(tmp_path / "o1"))
        assert first["from_cache"] is False
        second = p.process(str(src), str(tmp_path / "o2"))
        assert second["from_cache"] is True
        assert open(second["audio_output_path"], "rb").read() == b"cleaned"
        assert p.media_loader.load_media.call_count == 1

    def test_cache_write_failure_does_not_fail_the_request(
        self, make_pipeline, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "l.wav"
        src.write_bytes(b"x")
        p = make_pipeline(enable_cache=True)
        _arrange(p)
        p.config["asr"]["skip"] = True
        p.cache = MagicMock()
        p.cache.get.return_value = None
        p.cache.set.side_effect = OSError("disk full")
        assert p.process(str(src), str(tmp_path / "o"))["from_cache"] is False


class TestBatch:
    def test_continues_after_failure(self, make_pipeline):
        p = make_pipeline()
        p.process = Mock(side_effect=[{"ok": 1}, RuntimeError("bad file"), {"ok": 3}])
        results, failed = p.process_batch(["a", "b", "c"])
        assert len(results) == 2 and failed == [("b", "bad file")]

    def test_can_stop_on_first_error(self, make_pipeline):
        p = make_pipeline()
        p.process = Mock(side_effect=RuntimeError("bad file"))
        with pytest.raises(RuntimeError):
            p.process_batch(["a", "b"], continue_on_error=False)
        assert p.process.call_count == 1
