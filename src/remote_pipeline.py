"""
Remote GPU pipeline client — offloads the heavy audio-processing stages to a
Kaggle-notebook-hosted worker reached over a "tunnel" (see gpu_tunnel/),
instead of running LectraAIPipeline locally on CPU.

Drop-in for LectraAIPipeline: same .process(...) signature, same return dict
shape (see src/pipeline.py's `results = {...}` near the end of process()), so
backend.py's call site doesn't need to know which one it has. Raises on any
failure — the caller (backend.py's initialize_pipeline()) is what decides to
fall back to a local LectraAIPipeline; this class never falls back to local
itself, so a genuinely broken tunnel doesn't fail silently.
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

# The tunnel only ever receives/returns raw audio — video remux isn't
# implemented on the worker side. Callers should fall back to local
# processing for these rather than get a confusing remote error.
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}


class RemoteGpuPipeline:
    """See module docstring. Construct one per tunnel URL/token; cheap, holds
    no persistent connection (each .process() call is a single POST)."""

    def __init__(self, tunnel_url: str, token: str, timeout_seconds: int = 1800):
        self.base_url = tunnel_url.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds
        # Set by backend.py's initialize_pipeline() before each request —
        # mirrors how it configures a local LectraAIPipeline's pipeline.asr /
        # pipeline.config["diarization"]["enabled"] instead. Not accepted as
        # process() call args because process_audio()'s call to .process()
        # is shared with LectraAIPipeline, whose signature doesn't take them.
        self.whisper_model = "turbo"
        self.enable_diarization = True

    def health_check(self) -> bool:
        """Quick reachability probe (used by /api/health's gpu_tunnel field).
        Never raises — any failure just means "not reachable right now"."""
        try:
            r = requests.get(
                f"{self.base_url}/health",
                headers={"X-Tunnel-Token": self.token},
                timeout=10,
            )
            return r.status_code == 200
        except requests.RequestException:
            return False

    def process(
        self,
        input_path: str,
        output_dir: str = "outputs",
        save_transcript: bool = True,
        transcript_format: str = "txt",
    ) -> Dict[str, Any]:
        """Same contract as LectraAIPipeline.process(). Raises
        requests.RequestException / RuntimeError / ValueError on any failure
        — no local fallback here, that's the caller's job."""
        ext = Path(input_path).suffix.lower()
        if ext in VIDEO_EXTENSIONS:
            raise ValueError(
                f"GPU tunnel doesn't support video ({ext}) yet — audio only"
            )

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Sending {input_path} to GPU tunnel at {self.base_url}")
        with open(input_path, "rb") as f:
            resp = requests.post(
                f"{self.base_url}/process",
                headers={"X-Tunnel-Token": self.token},
                files={"file": (os.path.basename(input_path), f)},
                data={
                    "whisper_model": self.whisper_model,
                    "enable_diarization": str(self.enable_diarization),
                    "transcript_format": transcript_format,
                },
                timeout=self.timeout_seconds,
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"GPU tunnel returned {resp.status_code}: {resp.text[:500]}"
            )

        payload = resp.json()

        input_name = Path(input_path).stem
        audio_output_path = output_dir / f"{input_name}_cleaned.wav"
        audio_output_path.write_bytes(base64.b64decode(payload["audio_base64"]))

        logger.info(
            f"GPU tunnel finished (remote processing time: "
            f"{payload.get('processing_time', 0):.1f}s)"
        )

        return {
            "input_path": input_path,
            "is_video": False,
            "audio_output_path": str(audio_output_path),
            "video_output_path": None,
            "transcript": payload.get("transcript", {}),
            "diarization": payload.get("diarization", []),
            "duration_original": payload.get("duration_original", 0.0),
            "duration_processed": payload.get("duration_processed", 0.0),
            "speech_segments": payload.get("speech_segments", 0),
            "processing_time": payload.get("processing_time", 0.0),
            "from_cache": False,
        }


def build_pipeline_from_env():
    """Returns a RemoteGpuPipeline if GPU_TUNNEL_URL is set, else None. Used
    by backend.py's initialize_pipeline() to decide local vs. remote."""
    tunnel_url = os.getenv("GPU_TUNNEL_URL")
    if not tunnel_url:
        return None
    token = os.getenv("GPU_TUNNEL_TOKEN", "")
    return RemoteGpuPipeline(tunnel_url=tunnel_url, token=token)
