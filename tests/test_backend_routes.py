"""Backend route tests with a fake audio pipeline.

Exercises /api/process, /api/process-lecture, the GPU-tunnel fallback, pipeline
initialisation, model status, metrics and start-up seeding — without loading any
ML model or touching the real data/ and outputs/ folders (conftest isolates the
repositories; backend.__file__ is redirected to a temp folder for outputs/).
"""

import io
import os
import sys
import types
import wave

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

import backend
from backend import ProcessingConfig, app

client = TestClient(app)


def _wav_bytes(seconds=2.0, sr=16000):
    buf = io.BytesIO()
    sf.write(buf, np.zeros(int(seconds * sr), dtype=np.float32), sr, format="WAV")
    return buf.getvalue()


class FakePipeline:
    """Stand-in for LectraAIPipeline: writes a cleaned wav and returns a result."""

    def __init__(self, diarization=True, fail=False):
        self.diarization = diarization
        self.fail = fail
        self.calls = 0

    def process(self, input_path, output_dir, save_transcript, transcript_format):
        self.calls += 1
        if self.fail:
            raise RuntimeError("pipeline exploded")
        out = os.path.join(output_dir, "cleaned.wav")
        sf.write(out, np.zeros(32000, dtype=np.float32), 16000)
        result = {
            "audio_output_path": out,
            "transcript": {
                "text": "hello world",
                "segments": [
                    {
                        "start": 0.0,
                        "end": 1.0,
                        "text": " hello",
                        "speaker": "SPEAKER_00",
                        "asr_confidence": 0.9,
                        "speaker_confidence": 1.0,
                    },
                    {
                        "start": 1.0,
                        "end": 2.0,
                        "text": " world",
                        "speaker": "SPEAKER_01",
                    },
                ],
            },
            "duration_original": 2.0,
            "duration_processed": 2.0,
            "speech_segments": 2,
            "is_video": False,
        }
        if self.diarization:
            result["diarization"] = [
                {"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"},
                {"start": 1.0, "end": 2.0, "speaker": "SPEAKER_01"},
                {"start": 2.0, "end": 2.0, "speaker": "SPEAKER_01"},  # empty, skipped
            ]
        return result


@pytest.fixture
def outputs_dir(tmp_path, monkeypatch):
    """Redirect backend's outputs/ folder to a temp dir."""
    monkeypatch.setattr(backend, "__file__", str(tmp_path / "backend.py"))
    return tmp_path / "outputs"


@pytest.fixture
def fake_pipe(monkeypatch):
    pipe = FakePipeline()
    monkeypatch.setattr(backend, "initialize_pipeline", lambda config: pipe)
    return pipe


def _upload(auth, name="lecture.wav", data=None, path="/api/process", **form):
    return client.post(
        path,
        files={"file": (name, data if data is not None else _wav_bytes(), "audio/wav")},
        data={"whisper_model": "base", **form},
        headers=auth.headers,
    )


# --------------------------------------------------------------- /api/process
class TestProcessAudio:
    def test_success_returns_urls_segments_and_speaker_audio(
        self, auth, fake_pipe, outputs_dir
    ):
        r = _upload(auth)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["success"] is True and body["transcript"] == "hello world"
        assert body["audio_url"] == "/api/download/cleaned_lecture.wav"
        assert body["original_audio_url"] == "/api/download/original_lecture.wav"
        assert body["transcript_segments"][0]["text"] == "hello"
        assert body["transcript_segments"][1]["asr_confidence"] is None
        assert set(body["speaker_audio"]) == {"SPEAKER_00", "SPEAKER_01"}
        for name in (
            "cleaned_lecture.wav",
            "original_lecture.wav",
            "transcript_lecture.txt",
            "speaker_SPEAKER_00_lecture.wav",
        ):
            assert (outputs_dir / name).exists(), name

    def test_files_are_downloadable_through_the_api(self, auth, fake_pipe, outputs_dir):
        _upload(auth)
        r = client.get("/api/download/transcript_lecture.txt")
        assert r.status_code == 200 and r.text == "hello world"

    def test_no_diarization_means_no_speaker_audio(
        self, auth, monkeypatch, outputs_dir
    ):
        monkeypatch.setattr(
            backend, "initialize_pipeline", lambda c: FakePipeline(diarization=False)
        )
        body = _upload(auth).json()
        assert body["speaker_audio"] == {} and body["diarization"] == []

    def test_string_transcript_is_supported(self, auth, monkeypatch, outputs_dir):
        pipe = FakePipeline()
        orig = pipe.process

        def process(*a, **k):
            res = orig(*a, **k)
            res["transcript"] = "plain string transcript"
            return res

        pipe.process = process
        monkeypatch.setattr(backend, "initialize_pipeline", lambda c: pipe)
        body = _upload(auth).json()
        assert body["transcript"] == "plain string transcript"
        assert body["transcript_segments"] == []

    def test_pipeline_failure_returns_json_500(self, auth, monkeypatch, outputs_dir):
        monkeypatch.setattr(
            backend, "initialize_pipeline", lambda c: FakePipeline(fail=True)
        )
        r = _upload(auth)
        assert r.status_code == 500
        assert r.json() == {"success": False, "error": "pipeline exploded"}

    def test_rejects_oversized_upload(self, auth, fake_pipe, outputs_dir, monkeypatch):
        monkeypatch.setattr(backend, "MAX_FILE_SIZE_MB", 0)
        assert _upload(auth).status_code == 413

    def test_rejects_invalid_model_name(self, auth, outputs_dir):
        r = _upload(auth, whisper_model="gigantic")
        assert r.status_code == 500 and "Model must be one of" in r.json()["error"]

    def test_requires_login(self, fake_pipe):
        r = client.post(
            "/api/process", files={"file": ("a.wav", _wav_bytes(), "audio/wav")}
        )
        assert r.status_code == 401


# --------------------------------------------------- GPU tunnel fallback path
class TestTunnelFallback:
    def test_remote_failure_falls_back_to_local_pipeline(
        self, auth, monkeypatch, outputs_dir
    ):
        from remote_pipeline import RemoteGpuPipeline

        remote = RemoteGpuPipeline.__new__(RemoteGpuPipeline)
        remote.process = lambda **kw: (_ for _ in ()).throw(
            ConnectionError("tunnel down")
        )
        local = FakePipeline()
        built = []
        monkeypatch.setattr(backend, "initialize_pipeline", lambda c: remote)
        monkeypatch.setattr(
            backend, "_build_local_pipeline", lambda: built.append(1) or local
        )
        monkeypatch.setattr(backend, "_configure_local_pipeline", lambda p, c: None)
        monkeypatch.setattr(backend, "_local_fallback_pipeline", None)

        assert _upload(auth).status_code == 200
        assert (
            _upload(auth).status_code == 200
        )  # second request reuses the cached fallback
        assert local.calls == 2 and built == [1]


# ----------------------------------------------------------- /api/process-lecture
class TestProcessLecture:
    def test_creates_lecture_session_and_audio_records(
        self, auth, fake_pipe, outputs_dir
    ):
        r = _upload(auth, path="/api/process-lecture", title="Biology 101")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["title"] == "Biology 101"
        assert body["lecture_id"] and body["session_id"]
        kinds = {f["kind"] for f in body["audio_files"]}
        assert {"original", "cleaned", "speaker:SPEAKER_00"} <= kinds

        lecture = client.get(f"/api/lecture/{body['lecture_id']}", headers=auth.headers)
        assert lecture.status_code == 200
        assert lecture.json()["title"] == "Biology 101"

    def test_default_title_is_file_stem(self, auth, fake_pipe, outputs_dir):
        body = _upload(auth, name="week3.wav", path="/api/process-lecture").json()
        assert body["title"] == "week3"

    def test_processing_error_is_passed_through_without_storing(
        self, auth, monkeypatch, outputs_dir
    ):
        monkeypatch.setattr(
            backend, "initialize_pipeline", lambda c: FakePipeline(fail=True)
        )
        r = _upload(auth, path="/api/process-lecture")
        assert r.status_code == 500
        library = client.get("/api/library", headers=auth.headers).json()
        assert library == [] or library.get("lectures", []) == []

    def test_storage_failure_still_returns_processing_result(
        self, auth, fake_pipe, outputs_dir, monkeypatch
    ):
        import lecture_repository

        monkeypatch.setattr(
            lecture_repository.get_repository().__class__,
            "create",
            lambda self, **kw: (_ for _ in ()).throw(OSError("disk full")),
        )
        r = _upload(auth, path="/api/process-lecture")
        assert r.status_code == 200 and "lecture_id" not in r.json()


# ------------------------------------------------------------ pipeline set-up
class FakeASR:
    def __init__(self, model_size="base"):
        self.model_size = model_size
        self.model = object()


class FakeLocal:
    def __init__(self, asr_skip=False, asr=None):
        self.config = {
            "asr": {"skip": asr_skip, "language": "en"},
            "diarization": {"enabled": True},
        }
        self.asr = asr
        self.diarization = object()


class TestConfigurePipeline:
    def test_reloads_asr_only_when_model_changes(self, monkeypatch):
        created = []

        class StubASR(FakeASR):
            def __init__(self, **kw):
                created.append(kw)
                super().__init__(kw["model_size"])

        monkeypatch.setitem(
            sys.modules, "asr_processor", types.SimpleNamespace(ASRProcessor=StubASR)
        )
        pipe = FakeLocal(asr=FakeASR("tiny"))
        backend._configure_local_pipeline(pipe, ProcessingConfig(whisper_model="base"))
        assert len(created) == 1 and created[0]["model_size"] == "base"
        backend._configure_local_pipeline(pipe, ProcessingConfig(whisper_model="base"))
        assert len(created) == 1  # same model: no reload

    def test_turbo_alias_is_normalised(self, monkeypatch):
        created = []
        monkeypatch.setitem(
            sys.modules,
            "asr_processor",
            types.SimpleNamespace(ASRProcessor=lambda **kw: created.append(kw)),
        )
        pipe = FakeLocal(asr=FakeASR("large-v3-turbo"))
        backend._configure_local_pipeline(pipe, ProcessingConfig(whisper_model="turbo"))
        assert created == []

    def test_asr_skip_and_diarization_toggle(self):
        pipe = FakeLocal(asr_skip=True)
        backend._configure_local_pipeline(
            pipe, ProcessingConfig(enable_diarization=False)
        )
        assert pipe.asr is None and pipe.diarization is None
        assert pipe.config["diarization"]["enabled"] is False


class TestInitializePipeline:
    def test_builds_local_pipeline_once(self, monkeypatch):
        import remote_pipeline

        local = FakeLocal(asr=FakeASR("base"))
        built = []
        monkeypatch.setattr(backend, "pipeline", None)
        monkeypatch.setattr(remote_pipeline, "build_pipeline_from_env", lambda: None)
        monkeypatch.setattr(
            backend, "_build_local_pipeline", lambda: built.append(1) or local
        )
        cfg = ProcessingConfig(whisper_model="base", enable_diarization=False)
        assert backend.initialize_pipeline(cfg) is local
        assert backend.initialize_pipeline(cfg) is local
        assert built == [1] and local.config["diarization"]["enabled"] is False

    def test_uses_remote_pipeline_when_tunnel_configured(self, monkeypatch):
        import remote_pipeline
        from remote_pipeline import RemoteGpuPipeline

        remote = RemoteGpuPipeline.__new__(RemoteGpuPipeline)
        remote.base_url = "https://example.invalid"
        monkeypatch.setattr(backend, "pipeline", None)
        monkeypatch.setattr(remote_pipeline, "build_pipeline_from_env", lambda: remote)
        got = backend.initialize_pipeline(
            ProcessingConfig(whisper_model="small", enable_diarization=False)
        )
        assert got is remote
        assert remote.whisper_model == "small" and remote.enable_diarization is False

    def test_build_local_pipeline_reads_cache_flag(self, monkeypatch):
        seen = {}

        class Stub:
            def __init__(self, cfg, enable_cache):
                seen.update(cfg=cfg, enable_cache=enable_cache)

        monkeypatch.setattr(backend, "LectraAIPipeline", Stub)
        backend._build_local_pipeline()
        assert seen["cfg"] == "config.yaml" and isinstance(seen["enable_cache"], bool)


# ------------------------------------------------------------ status endpoints
class TestStatusEndpoints:
    def test_model_status_with_live_models(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        pipe = types.SimpleNamespace(
            asr=types.SimpleNamespace(model=object()),
            diarization=types.SimpleNamespace(pipeline=object()),
        )
        monkeypatch.setattr(backend, "pipeline", pipe)
        data = client.get("/api/model-status").json()
        assert data["models"]["whisper"]["ready"] is True
        assert data["models"]["whisper"]["progress"] == 100
        assert (
            data["models"]["pyannote"]["ready"] is True
            and data["models"]["pyannote"]["progress"] == 100
        )

    def test_model_status_from_files_on_disk(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        turbo = tmp_path / "models" / "large-v3-turbo"
        turbo.mkdir(parents=True)
        (turbo / "config.json").write_text("{}")
        (turbo / "model.bin").write_bytes(b"x" * 5_000_000)
        pyannote = tmp_path / "models" / "pyannote"
        pyannote.mkdir()
        (pyannote / "w.bin").write_bytes(b"x" * 2048)
        monkeypatch.setattr(backend, "pipeline", None)
        data = client.get("/api/model-status").json()
        assert data["models"]["whisper"]["ready"] is True
        assert 0 < data["models"]["whisper"]["progress"] < 5
        assert data["models"]["pyannote"]["ready"] is False

    def test_model_status_uses_hf_snapshot_folder(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        snap = (
            tmp_path
            / "models"
            / "models--Systran--faster-whisper-large-v3-turbo"
            / "snapshots"
            / "abc"
        )
        snap.mkdir(parents=True)
        (snap / "config.json").write_text("{}")
        monkeypatch.setattr(backend, "pipeline", None)
        assert (
            client.get("/api/model-status").json()["models"]["whisper"]["ready"] is True
        )

    def test_model_status_nothing_downloaded(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(backend, "pipeline", None)
        data = client.get("/api/model-status").json()
        assert (
            data["models"]["whisper"]["ready"] is False
            and data["models"]["whisper"]["progress"] == 0
        )
        assert data["all_ready"] is False

    def test_metrics_available_and_unavailable(self, monkeypatch):
        monkeypatch.setattr(backend, "METRICS_AVAILABLE", True)
        assert client.get("/metrics").status_code == 200
        monkeypatch.setattr(backend, "METRICS_AVAILABLE", False)
        assert client.get("/metrics").status_code == 501

    def test_download_missing_file_is_404(self):
        assert client.get("/api/download/definitely-not-there.wav").status_code == 404


# ------------------------------------------------------------ start-up / seeding
class TestStartup:
    def test_seed_creates_demo_student_once(self, monkeypatch):
        import student_repository

        monkeypatch.setenv("SEED_STUDENT_USERNAME", "demo_user")
        monkeypatch.setenv("SEED_STUDENT_PASSWORD", "Demo#Pass123")
        backend._seed_demo_student()
        repo = student_repository.get_repository()
        assert len(repo.list_raw()) == 1
        backend._seed_demo_student()  # idempotent
        assert len(repo.list_raw()) == 1

    def test_seed_skipped_without_env(self, monkeypatch):
        import student_repository

        monkeypatch.delenv("SEED_STUDENT_USERNAME", raising=False)
        monkeypatch.delenv("SEED_STUDENT_PASSWORD", raising=False)
        backend._seed_demo_student()
        assert student_repository.get_repository().list_raw() == []

    def test_seed_never_raises(self, monkeypatch):
        import student_repository

        monkeypatch.setattr(
            student_repository,
            "get_repository",
            lambda: (_ for _ in ()).throw(RuntimeError("db down")),
        )
        backend._seed_demo_student()

    @pytest.mark.parametrize("prewarm_fails", [False, True])
    def test_lifespan_survives_prewarm_failure(self, monkeypatch, prewarm_fails):
        called = []

        def init(config):
            called.append(config)
            if prewarm_fails:
                raise RuntimeError("model download failed")

        monkeypatch.setattr(backend, "initialize_pipeline", init)
        monkeypatch.setattr(backend, "_seed_demo_student", lambda: None)
        with TestClient(app) as c:
            assert c.get("/api/health").status_code == 200
        assert len(called) == 1


class TestProcessingConfig:
    def test_defaults(self):
        cfg = ProcessingConfig()
        assert (cfg.whisper_model, cfg.enable_diarization, cfg.transcript_format) == (
            "turbo",
            True,
            "txt",
        )

    @pytest.mark.parametrize(
        "kw", [{"whisper_model": "huge"}, {"transcript_format": "docx"}]
    )
    def test_invalid_values_rejected(self, kw):
        with pytest.raises(ValueError):
            ProcessingConfig(**kw)
