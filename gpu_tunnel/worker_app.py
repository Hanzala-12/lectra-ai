"""
GPU tunnel worker — the FastAPI app that runs INSIDE the Kaggle notebook (see
kaggle_worker.ipynb). Reuses LectraAIPipeline completely unmodified; the only
job here is: receive a file over HTTP, run the existing pipeline, send the
result back as JSON. Not part of the main backend and never imported by it —
only ever run standalone by the notebook, on Kaggle's own GPU.

Talks to src/remote_pipeline.py's RemoteGpuPipeline on the other end of the
tunnel — keep the two in sync (request fields, response JSON shape) if either
changes.
"""

import base64
import logging
import os
import sys
import tempfile
import time
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile

# The notebook clones the whole repo and runs this file from wherever cwd
# happens to be — make src/ importable by path instead of assuming one.
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from pipeline import LectraAIPipeline  # noqa: E402
from asr_processor import ASRProcessor  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gpu_tunnel_worker")

TOKEN = os.environ.get("GPU_TUNNEL_TOKEN", "")
if not TOKEN:
    raise RuntimeError(
        "GPU_TUNNEL_TOKEN is not set - refusing to start with no shared "
        "secret (anyone who gets the tunnel URL could submit jobs to your "
        "Kaggle GPU quota). Set it via a Kaggle Secret before running this "
        "cell - see gpu_tunnel/README.md."
    )

app = FastAPI(title="Lectra AI - GPU tunnel worker")

_pipeline: LectraAIPipeline = None


def _get_pipeline() -> LectraAIPipeline:
    global _pipeline
    if _pipeline is None:
        logger.info("Loading LectraAIPipeline (first request - this takes a bit)")
        _pipeline = LectraAIPipeline(
            str(_REPO_ROOT / "config.yaml"), enable_cache=False
        )
    return _pipeline


async def verify_token(x_tunnel_token: str = Header(default="")) -> None:
    if x_tunnel_token != TOKEN:
        raise HTTPException(status_code=401, detail="Bad or missing X-Tunnel-Token")


@app.get("/health")
async def health(_: None = Depends(verify_token)):
    import torch

    return {
        "status": "healthy",
        "gpu": torch.cuda.is_available(),
        "gpu_device": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        ),
    }


@app.post("/process")
async def process(
    file: UploadFile = File(...),
    whisper_model: str = Form("turbo"),
    enable_diarization: str = Form("True"),
    transcript_format: str = Form("txt"),
    _: None = Depends(verify_token),
):
    pipe = _get_pipeline()

    # Same per-request whisper-model / diarization wiring backend.py's
    # _configure_local_pipeline() does for the local path — kept in sync by
    # hand since this file has no import relationship with backend.py.
    requested_model = "large-v3-turbo" if whisper_model == "turbo" else whisper_model
    current_model = pipe.asr.model_size if pipe.asr is not None else None
    if current_model != requested_model:
        logger.info(f"Loading faster-whisper '{whisper_model}' on cuda")
        pipe.asr = ASRProcessor(
            model_size=whisper_model, device="cuda", compute_type="float16"
        )

    diarize = enable_diarization.strip().lower() == "true"
    pipe.config["diarization"]["enabled"] = diarize
    if not diarize:
        pipe.diarization = None

    with tempfile.TemporaryDirectory() as tmp:
        input_path = os.path.join(tmp, file.filename or "input.wav")
        with open(input_path, "wb") as f:
            f.write(await file.read())

        logger.info(f"Processing {file.filename} ({whisper_model}, diarize={diarize})")
        start = time.time()
        try:
            result = pipe.process(
                input_path=input_path,
                output_dir=os.path.join(tmp, "out"),
                save_transcript=True,
                transcript_format=transcript_format,
            )
        except Exception as e:
            logger.exception("Pipeline failed")
            raise HTTPException(status_code=500, detail=str(e))
        elapsed = time.time() - start

        audio_bytes = Path(result["audio_output_path"]).read_bytes()

    logger.info(f"Done in {elapsed:.1f}s")
    return {
        "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
        "transcript": result.get("transcript", {}),
        "diarization": result.get("diarization", []),
        "duration_original": result.get("duration_original", 0.0),
        "duration_processed": result.get("duration_processed", 0.0),
        "speech_segments": result.get("speech_segments", 0),
        "processing_time": elapsed,
    }
