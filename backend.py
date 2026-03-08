"""
FastAPI Backend Server for Voice Cleaning Pipeline
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional
from contextlib import asynccontextmanager
import uvicorn
import os
import sys
import tempfile
import shutil
from pathlib import Path
import logging
import time
import torch
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add bundled ffmpeg to PATH so pydub can find it
try:
    import imageio_ffmpeg

    _ffmpeg_dir = str(Path(imageio_ffmpeg.get_ffmpeg_exe()).parent)
    os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST  # type: ignore

    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pipeline import VoiceCleaningPipeline  # type: ignore

# Setup structured logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global pipeline instance
pipeline = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events"""
    # Startup
    logger.info("Server startup: pre-warming pipeline (loading models into memory)...")
    try:
        config = ProcessingConfig()
        initialize_pipeline(config)
        logger.info("Pipeline pre-warmed successfully — ready to process requests")
    except Exception as e:
        logger.error(f"Pipeline pre-warm failed: {e} — will retry on first request")

    yield

    # Shutdown (if needed)
    logger.info("Server shutdown")


app = FastAPI(
    title="Voice Cleaning API",
    version="1.0.0",
    description="AI-powered voice cleaning with DeepFilterNet and Whisper",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".flac",
    ".aac",
    ".ogg",
    ".mp4",
    ".avi",
    ".mkv",
    ".mov",
    ".webm",
}


class ProcessingConfig(BaseModel):
    whisper_model: str = "turbo"
    enable_diarization: bool = True
    transcript_format: str = "txt"

    @field_validator("whisper_model")
    @classmethod
    def validate_model(cls, v):
        allowed = ["tiny", "base", "small", "medium", "large", "large-v3", "turbo"]
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}")
        return v

    @field_validator("transcript_format")
    @classmethod
    def validate_format(cls, v):
        allowed = ["txt", "srt", "vtt", "json"]
        if v not in allowed:
            raise ValueError(f"Format must be one of {allowed}")
        return v


def initialize_pipeline(config: ProcessingConfig):
    """Initialize pipeline with configuration"""
    global pipeline

    if pipeline is None:
        import yaml as _yaml

        with open("config.yaml") as _f:
            _cfg = _yaml.safe_load(_f)
        _cache_enabled = _cfg.get("cache", {}).get("enabled", False)
        pipeline = VoiceCleaningPipeline("config.yaml", enable_cache=_cache_enabled)

    # Skip ASR initialisation entirely when asr.skip is true
    asr_skip = pipeline.config.get("asr", {}).get("skip", False)
    if not asr_skip:
        current_model = pipeline.asr.model_size if pipeline.asr is not None else None
        if current_model != config.whisper_model:
            logger.info(
                f"Loading faster-whisper '{config.whisper_model}' (was '{current_model}')"
            )
            from asr_processor import ASRProcessor  # type: ignore

            pipeline.asr = ASRProcessor(
                model_size=config.whisper_model,
                language=pipeline.config["asr"].get("language"),
                device="cpu",
                compute_type="int8",
            )

    pipeline.config["diarization"]["enabled"] = config.enable_diarization
    if not config.enable_diarization:
        pipeline.diarization = None

    return pipeline


@app.get("/")
async def root():
    """API root endpoint"""
    return {"name": "Voice Cleaning API", "version": "1.0.0", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint with system status"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": pipeline is not None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_device": (
            torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
        ),
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None,
    }


@app.get("/api/models")
async def get_available_models():
    """Get available faster-whisper models"""
    return {
        "whisper_models": [
            {"value": "tiny", "label": "Tiny (39MB) - Fastest", "size": "39MB"},
            {"value": "base", "label": "Base (74MB) - Fast", "size": "74MB"},
            {"value": "small", "label": "Small (244MB) - Good", "size": "244MB"},
            {"value": "medium", "label": "Medium (769MB) - Better", "size": "769MB"},
            {"value": "large", "label": "Large (1.5GB) - Best", "size": "1.5GB"},
            {
                "value": "large-v3",
                "label": "Large-v3 (1.5GB) - Latest",
                "size": "1.5GB",
            },
            {
                "value": "turbo",
                "label": "Turbo (809MB) - Optimized (Recommended)",
                "size": "809MB",
            },
        ],
        "transcript_formats": ["txt", "srt", "vtt", "json"],
    }


@app.get("/api/model-status")
async def get_model_status():
    """Check download status of all required models"""
    models_dir = Path("./models")

    # faster-whisper models are stored in CTranslate2 format
    # Check for turbo model directory (faster-whisper format)
    turbo_path = models_dir / "large-v3-turbo"
    whisper_ready = turbo_path.exists() and (turbo_path / "config.json").exists()

    # Estimate size if available
    if whisper_ready:
        whisper_size = sum(
            f.stat().st_size for f in turbo_path.rglob("*") if f.is_file()
        )
        WHISPER_EXPECTED = 850_000_000  # ~850 MB for turbo model
        whisper_pct = min(100, round(whisper_size / WHISPER_EXPECTED * 100, 1))
    else:
        whisper_size = 0
        whisper_pct = 0
        WHISPER_EXPECTED = 850_000_000

    # DeepFilterNet3 - auto-downloaded to venv cache
    deepfilter_ready = False
    try:
        from df.enhance import init_df

        deepfilter_ready = True
    except Exception:
        deepfilter_ready = False

    # Pyannote diarization model
    pyannote_dir = models_dir / "pyannote"
    PYANNOTE_EXPECTED = 300_000_000  # ~300 MB minimum
    pyannote_size = (
        sum(f.stat().st_size for f in pyannote_dir.rglob("*") if f.is_file())
        if pyannote_dir.exists()
        else 0
    )
    pyannote_ready = pyannote_size >= PYANNOTE_EXPECTED

    def fmt_mb(b):
        return f"{round(b / 1024 / 1024, 1)} MB"

    return {
        "models": {
            "whisper": {
                "name": "faster-whisper Turbo",
                "description": "Speech recognition (~850 MB)",
                "ready": whisper_ready,
                "progress": whisper_pct,
                "downloaded": fmt_mb(whisper_size),
                "total": fmt_mb(WHISPER_EXPECTED),
            },
            "deepfilternet": {
                "name": "DeepFilterNet3",
                "description": "Noise reduction (~50 MB)",
                "ready": deepfilter_ready,
                "progress": 100 if deepfilter_ready else 0,
                "downloaded": "~50 MB" if deepfilter_ready else "0 MB",
                "total": "~50 MB",
            },
            "pyannote": {
                "name": "Pyannote Diarization 3.1",
                "description": "Speaker detection (~700 MB)",
                "ready": pyannote_ready,
                "progress": min(100, round(pyannote_size / PYANNOTE_EXPECTED * 100, 1)),
                "downloaded": fmt_mb(pyannote_size),
                "total": "~700 MB",
            },
        },
        "all_ready": whisper_ready and deepfilter_ready,
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not METRICS_AVAILABLE:
        raise HTTPException(
            status_code=501, detail="Metrics not available. Install prometheus_client."
        )

    from fastapi.responses import Response

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - Status: {response.status_code} - Duration: {duration:.2f}s"
    )

    return response


@app.post("/api/process")
async def process_audio(
    file: UploadFile = File(...),
    whisper_model: str = "base",
    enable_diarization: bool = True,
    transcript_format: str = "txt",
):
    """Process uploaded audio/video file"""

    start_time = time.time()

    try:
        # Validate file
        validate_file(file)

        # Read file once, check size, save to temp path
        file_size = 0
        temp_dir = tempfile.mkdtemp()
        input_path = os.path.join(temp_dir, file.filename)
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(input_path, "wb") as out_f:
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB",
                    )
                out_f.write(chunk)

        logger.info(
            f"Processing file: {file.filename} ({file_size / 1024 / 1024:.2f}MB) with model: {whisper_model}"
        )

        # Initialize pipeline
        config = ProcessingConfig(
            whisper_model=whisper_model,
            enable_diarization=enable_diarization,
            transcript_format=transcript_format,
        )
        pipe = initialize_pipeline(config)

        # Process file
        output_dir = os.path.join(temp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)

        result = pipe.process(
            input_path=input_path,
            output_dir=output_dir,
            save_transcript=True,
            transcript_format=transcript_format,
        )

        # Read output files
        audio_output = result["audio_output_path"]
        with open(audio_output, "rb") as f:
            audio_data = f.read()

        # Save to outputs folder
        final_output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(final_output_dir, exist_ok=True)

        # Save original audio (before cleaning) so the frontend can compare
        original_ext = Path(file.filename).suffix.lower() or ".wav"
        original_filename = f"original_{Path(file.filename).stem}{original_ext}"
        final_original_path = os.path.join(final_output_dir, original_filename)
        shutil.copy2(input_path, final_original_path)

        output_filename = f"cleaned_{Path(file.filename).stem}.wav"
        final_audio_path = os.path.join(final_output_dir, output_filename)

        with open(final_audio_path, "wb") as f:
            f.write(audio_data)

        # Read transcript if available
        transcript_data = result.get("transcript", {})
        transcript_text = (
            transcript_data.get("text", "")
            if isinstance(transcript_data, dict)
            else str(transcript_data)
        )
        transcript_segments = (
            transcript_data.get("segments", [])
            if isinstance(transcript_data, dict)
            else []
        )

        # Save transcript txt file to outputs folder
        transcript_filename = f"transcript_{Path(file.filename).stem}.txt"
        final_transcript_path = os.path.join(final_output_dir, transcript_filename)
        with open(final_transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)

        # Generate per-speaker audio clips when diarization succeeded
        diarization_data = result.get("diarization", [])
        speaker_audio_urls = {}
        if diarization_data:
            try:
                import soundfile as sf
                import numpy as np

                cleaned_audio, sr = sf.read(final_audio_path)
                speakers = list(
                    {seg["speaker"] for seg in diarization_data if "speaker" in seg}
                )
                for spk in speakers:
                    segs = [s for s in diarization_data if s.get("speaker") == spk]
                    chunks = []
                    for s in segs:
                        s_start = int(s["start"] * sr)
                        s_end = int(s["end"] * sr)
                        if s_end > s_start:
                            chunks.append(cleaned_audio[s_start:s_end])
                    if chunks:
                        spk_audio = np.concatenate(chunks)
                        safe_spk = spk.replace(" ", "_").replace("/", "_")
                        spk_filename = (
                            f"speaker_{safe_spk}_{Path(file.filename).stem}.wav"
                        )
                        spk_path = os.path.join(final_output_dir, spk_filename)
                        sf.write(spk_path, spk_audio, sr)
                        speaker_audio_urls[spk] = f"/api/download/{spk_filename}"
            except Exception as spk_err:
                logger.warning(f"Could not generate speaker audio: {spk_err}")

        # Cleanup temp directory
        shutil.rmtree(temp_dir)

        return {
            "success": True,
            "original_audio_url": f"/api/download/{original_filename}",
            "audio_url": f"/api/download/{output_filename}",
            "transcript": transcript_text,
            "transcript_url": f"/api/download/{transcript_filename}",
            "transcript_segments": [
                {
                    "start": round(s.get("start", 0), 2),
                    "end": round(s.get("end", 0), 2),
                    "text": s.get("text", "").strip(),
                    "speaker": s.get("speaker", None),
                }
                for s in transcript_segments
            ],
            "duration_original": result.get("duration_original", 0.0),
            "duration_processed": result.get("duration_processed", 0.0),
            "speech_segments": result.get("speech_segments", 0),
            "is_video": result.get("is_video", False),
            "diarization": diarization_data,
            "speaker_audio": speaker_audio_urls,
        }

    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download processed file"""
    file_path = os.path.join(os.path.dirname(__file__), "outputs", filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    suffix = Path(filename).suffix.lower()
    media_type_map = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".flac": "audio/flac",
        ".txt": "text/plain; charset=utf-8",
        ".srt": "text/plain; charset=utf-8",
        ".vtt": "text/vtt",
        ".json": "application/json",
        ".mp4": "video/mp4",
    }
    media_type = media_type_map.get(suffix, "application/octet-stream")

    return FileResponse(path=file_path, media_type=media_type, filename=filename)


if __name__ == "__main__":
    print("Starting Voice Cleaning API Server...")
    print("Server running at: http://localhost:8000")
    print("API Docs: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/api/health")
    print("\nMake sure to start the React frontend on port 3000!")

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
