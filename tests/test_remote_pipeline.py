"""
Tests for the GPU-tunnel remote pipeline client (src/remote_pipeline.py) and
its wiring into backend.py's initialize_pipeline().

The tunnel's actual heavy work happens on Kaggle (gpu_tunnel/worker_app.py),
so these tests only cover the local side: request/response shape, error
handling (must raise, not swallow, so backend.py's caller can fall back to
local CPU processing), and the local<->remote pipeline-selection wiring.
Matches this project's existing convention of not exercising the real,
heavy LectraAIPipeline in the fast test subset (see how tests/test_study_api.py
creates lectures via lecture_repository.create() directly instead of going
through /api/process — the real pipeline is out of scope here too).
"""

import base64

import pytest
import requests
from unittest.mock import Mock, patch

from remote_pipeline import RemoteGpuPipeline, build_pipeline_from_env, VIDEO_EXTENSIONS


# ----------------------------------------------------------------- fixtures


@pytest.fixture
def client_pipeline():
    return RemoteGpuPipeline(
        tunnel_url="https://fake-tunnel.trycloudflare.com/",
        token="secret-token",
        timeout_seconds=5,
    )


def _fake_response(status_code=200, json_body=None, text=""):
    r = Mock()
    r.status_code = status_code
    r.json.return_value = json_body or {}
    r.text = text
    return r


# ----------------------------------------------------------------- process()


def test_process_returns_lectraai_shaped_result(client_pipeline, tmp_path):
    """process_audio()/process_lecture() read audio_output_path, transcript,
    diarization, duration_original, duration_processed, speech_segments,
    is_video off the result — confirm every one of those is present and
    correctly populated, matching LectraAIPipeline.process()'s own shape
    (src/pipeline.py's `results = {...}`)."""
    audio_bytes = b"fake wav bytes"
    payload = {
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "transcript": {"text": "hello world", "segments": [{"text": "hello world"}]},
        "diarization": [{"start": 0.0, "end": 1.0, "speaker": "SPEAKER_00"}],
        "duration_original": 12.5,
        "duration_processed": 12.0,
        "speech_segments": 3,
        "processing_time": 4.2,
    }
    input_file = tmp_path / "lecture.mp3"
    input_file.write_bytes(b"not really audio")

    with patch(
        "remote_pipeline.requests.post", return_value=_fake_response(200, payload)
    ) as mock_post:
        result = client_pipeline.process(
            input_path=str(input_file), output_dir=str(tmp_path / "out")
        )

    assert mock_post.called
    assert result["transcript"] == payload["transcript"]
    assert result["diarization"] == payload["diarization"]
    assert result["duration_original"] == 12.5
    assert result["duration_processed"] == 12.0
    assert result["speech_segments"] == 3
    assert result["is_video"] is False
    assert result["video_output_path"] is None
    assert result["from_cache"] is False

    # audio_output_path must be a real file on disk with the decoded bytes —
    # process_audio() does open(result["audio_output_path"], "rb").read()
    written = open(result["audio_output_path"], "rb").read()
    assert written == audio_bytes


def test_process_sends_token_and_settings(client_pipeline, tmp_path):
    client_pipeline.whisper_model = "small"
    client_pipeline.enable_diarization = False
    input_file = tmp_path / "lecture.wav"
    input_file.write_bytes(b"x")

    payload = {"audio_base64": base64.b64encode(b"y").decode("ascii")}
    with patch(
        "remote_pipeline.requests.post", return_value=_fake_response(200, payload)
    ) as mock_post:
        client_pipeline.process(input_path=str(input_file), output_dir=str(tmp_path))

    _, kwargs = mock_post.call_args
    assert kwargs["headers"]["X-Tunnel-Token"] == "secret-token"
    assert kwargs["data"]["whisper_model"] == "small"
    assert kwargs["data"]["enable_diarization"] == "False"
    assert kwargs["timeout"] == 5


def test_process_rejects_video_without_a_network_call(client_pipeline, tmp_path):
    input_file = tmp_path / "lecture.mp4"
    input_file.write_bytes(b"x")
    assert input_file.suffix.lower() in VIDEO_EXTENSIONS

    with patch("remote_pipeline.requests.post") as mock_post:
        with pytest.raises(ValueError, match="video"):
            client_pipeline.process(
                input_path=str(input_file), output_dir=str(tmp_path)
            )
    mock_post.assert_not_called()


def test_process_raises_on_non_200(client_pipeline, tmp_path):
    """Must raise, not return something falsy-but-truthy — backend.py's
    process_audio() relies on an exception to trigger its local fallback."""
    input_file = tmp_path / "lecture.wav"
    input_file.write_bytes(b"x")

    with patch(
        "remote_pipeline.requests.post",
        return_value=_fake_response(500, text="worker crashed"),
    ):
        with pytest.raises(RuntimeError, match="500"):
            client_pipeline.process(
                input_path=str(input_file), output_dir=str(tmp_path)
            )


def test_process_propagates_connection_errors(client_pipeline, tmp_path):
    """A dead/unreachable tunnel (session ended, network blip) must raise,
    not be swallowed — same contract as the non-200 case above."""
    input_file = tmp_path / "lecture.wav"
    input_file.write_bytes(b"x")

    with patch(
        "remote_pipeline.requests.post",
        side_effect=requests.exceptions.ConnectionError("no route to host"),
    ):
        with pytest.raises(requests.exceptions.ConnectionError):
            client_pipeline.process(
                input_path=str(input_file), output_dir=str(tmp_path)
            )


# ------------------------------------------------------------- health_check


def test_health_check_true_on_200(client_pipeline):
    with patch("remote_pipeline.requests.get", return_value=_fake_response(200)):
        assert client_pipeline.health_check() is True


def test_health_check_false_on_bad_status(client_pipeline):
    with patch("remote_pipeline.requests.get", return_value=_fake_response(401)):
        assert client_pipeline.health_check() is False


def test_health_check_false_on_connection_error(client_pipeline):
    """Unlike process(), health_check() must NOT raise — /api/health calls
    it directly and a network hiccup there shouldn't break the health route."""
    with patch(
        "remote_pipeline.requests.get",
        side_effect=requests.exceptions.ConnectionError("unreachable"),
    ):
        assert client_pipeline.health_check() is False


# ------------------------------------------------------- build_pipeline_from_env


def test_build_pipeline_from_env_none_when_unset(monkeypatch):
    monkeypatch.delenv("GPU_TUNNEL_URL", raising=False)
    assert build_pipeline_from_env() is None


def test_build_pipeline_from_env_builds_when_set(monkeypatch):
    monkeypatch.setenv("GPU_TUNNEL_URL", "https://example.trycloudflare.com")
    monkeypatch.setenv("GPU_TUNNEL_TOKEN", "abc123")
    pipe = build_pipeline_from_env()
    assert isinstance(pipe, RemoteGpuPipeline)
    assert pipe.base_url == "https://example.trycloudflare.com"
    assert pipe.token == "abc123"


# --------------------------------------------------- backend.py wiring (light)


def test_initialize_pipeline_picks_remote_when_configured(monkeypatch):
    """Confirm backend.py's initialize_pipeline() actually returns a
    RemoteGpuPipeline (not the real local LectraAIPipeline, which would
    require loading real models) when GPU_TUNNEL_URL is set — this is the
    one line that decides local vs. remote for every request."""
    monkeypatch.setenv("GPU_TUNNEL_URL", "https://example.trycloudflare.com")
    monkeypatch.setenv("GPU_TUNNEL_TOKEN", "abc123")

    import backend

    original_pipeline = backend.pipeline
    backend.pipeline = None
    try:
        config = backend.ProcessingConfig(
            whisper_model="turbo", enable_diarization=True, transcript_format="txt"
        )
        result = backend.initialize_pipeline(config)
        assert isinstance(result, RemoteGpuPipeline)
        assert result.whisper_model == "turbo"
        assert result.enable_diarization is True
    finally:
        backend.pipeline = original_pipeline  # don't leak state into other tests
