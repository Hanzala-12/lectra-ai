"""
FastAPI Backend Server for Voice Cleaning Pipeline
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, validator
from typing import Optional
import uvicorn
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
import asyncio
import logging
import time
import hashlib
import torch
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("prometheus_client not installed. Metrics endpoint disabled.")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline import VoiceCleaningPipeline

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Voice Cleaning API",
    version="1.0.0",
    description="AI-powered voice cleaning with DeepFilterNet and Whisper"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global pipeline instance
pipeline = None
processing_status = {}

# Configuration
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg', '.mp4', '.avi', '.mkv', '.mov', '.webm'}

class ProcessingConfig(BaseModel):
    whisper_model: str = "base"
    enable_diarization: bool = True
    transcript_format: str = "txt"
    
    @validator('whisper_model')
    def validate_model(cls, v):
        allowed = ['tiny', 'base', 'small', 'medium', 'large']
        if v not in allowed:
            raise ValueError(f"Model must be one of {allowed}")
        return v
    
    @validator('transcript_format')
    def validate_format(cls, v):
        allowed = ['txt', 'srt', 'vtt', 'json']
        if v not in allowed:
            raise ValueError(f"Format must be one of {allowed}")
        return v

def initialize_pipeline(config: ProcessingConfig):
    """Initialize pipeline with configuration"""
    global pipeline
    
    if pipeline is None:
        pipeline = VoiceCleaningPipeline("config.yaml", enable_cache=True)  # Enable caching
    
    # Update configuration
    pipeline.config['asr']['model'] = config.whisper_model
    pipeline.config['asr']['device'] = 'cpu'  # Force CPU for laptops
    pipeline.config['asr']['compute_type'] = 'int8'  # Use int8 for CPU optimization
    pipeline.config['diarization']['enabled'] = config.enable_diarization
    
    # Reinitialize ASR if model changed
    from asr_processor import ASRProcessor
    pipeline.asr = ASRProcessor(
        model_size=config.whisper_model,
        language=pipeline.config['asr'].get('language'),
        device='cpu',  # Force CPU
        compute_type='int8'  # Optimize for CPU
    )
    
    if not config.enable_diarization:
        pipeline.diarization = None
    
    return pipeline

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Voice Cleaning API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint with system status"""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "models_loaded": pipeline is not None,
        "gpu_available": torch.cuda.is_available(),
        "gpu_device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "cuda_version": torch.version.cuda if torch.cuda.is_available() else None
    }

@app.get("/api/models")
async def get_available_models():
    """Get available Whisper models"""
    return {
        "whisper_models": [
            {"value": "tiny", "label": "Tiny (39MB) - Fastest", "size": "39MB"},
            {"value": "base", "label": "Base (74MB) - Recommended", "size": "74MB"},
            {"value": "small", "label": "Small (244MB) - Good", "size": "244MB"},
            {"value": "medium", "label": "Medium (769MB) - Better", "size": "769MB"},
            {"value": "large", "label": "Large (1.5GB) - Best", "size": "1.5GB"}
        ],
        "transcript_formats": ["txt", "srt", "vtt", "json"]
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    if not METRICS_AVAILABLE:
        raise HTTPException(status_code=501, detail="Metrics not available. Install prometheus_client.")
    
    from fastapi.responses import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

def validate_file(file: UploadFile) -> None:
    """Validate uploaded file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
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
    transcript_format: str = "txt"
):
    """Process uploaded audio/video file"""
    
    start_time = time.time()
    
    try:
        # Validate file
        validate_file(file)
        
        # Check file size
        file_size = 0
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            chunk_size = 1024 * 1024  # 1MB chunks
            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
                    )
                temp_file.write(chunk)
        finally:
            temp_file.close()
        
        logger.info(f"Processing file: {file.filename} ({file_size / 1024 / 1024:.2f}MB) with model: {whisper_model}")
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Save uploaded file
        input_path = os.path.join(temp_dir, file.filename)
        with open(input_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Initialize pipeline
        config = ProcessingConfig(
            whisper_model=whisper_model,
            enable_diarization=enable_diarization,
            transcript_format=transcript_format
        )
        pipe = initialize_pipeline(config)
        
        # Process file
        output_dir = os.path.join(temp_dir, "outputs")
        os.makedirs(output_dir, exist_ok=True)
        
        result = pipe.process(
            input_path=input_path,
            output_dir=output_dir,
            save_transcript=True,
            transcript_format=transcript_format
        )
        
        # Read output files
        audio_output = result['audio_output_path']
        with open(audio_output, 'rb') as f:
            audio_data = f.read()
        
        # Save to outputs folder
        final_output_dir = os.path.join(os.path.dirname(__file__), "outputs")
        os.makedirs(final_output_dir, exist_ok=True)
        
        output_filename = f"cleaned_{Path(file.filename).stem}.wav"
        final_audio_path = os.path.join(final_output_dir, output_filename)
        
        with open(final_audio_path, 'wb') as f:
            f.write(audio_data)
        
        # Read transcript if available
        transcript_text = result['transcript'].get('text', '')
        
        # Cleanup temp directory
        shutil.rmtree(temp_dir)
        
        return {
            "success": True,
            "audio_url": f"/api/download/{output_filename}",
            "transcript": transcript_text,
            "duration_original": result['duration_original'],
            "duration_processed": result['duration_processed'],
            "speech_segments": result['speech_segments'],
            "is_video": result['is_video'],
            "diarization": result.get('diarization', [])
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download processed file"""
    file_path = os.path.join(os.path.dirname(__file__), "outputs", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=filename
    )

@app.websocket("/ws/process")
async def websocket_process(websocket: WebSocket):
    """WebSocket endpoint for real-time processing updates"""
    await websocket.accept()
    
    try:
        # Receive configuration
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        
        # Send status updates during processing
        await websocket.send_json({"status": "initialized", "progress": 0})
        await websocket.send_json({"status": "loading_models", "progress": 10})
        
        # Initialize pipeline
        pipe_config = ProcessingConfig(**config)
        pipe = initialize_pipeline(pipe_config)
        
        await websocket.send_json({"status": "models_loaded", "progress": 20})
        
        # Wait for file data
        # (This is simplified - in production you'd handle file upload via WS)
        
        await websocket.send_json({"status": "processing", "progress": 50})
        await websocket.send_json({"status": "completed", "progress": 100})
        
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        await websocket.send_json({"status": "error", "message": str(e)})

if __name__ == "__main__":
    print("🚀 Starting Voice Cleaning API Server...")
    print("📡 Server running at: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print("🎯 Health Check: http://localhost:8000/api/health")
    print("\n⚠️  Make sure to start the React frontend on port 3000!")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
