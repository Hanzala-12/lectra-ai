"""
FastAPI Backend Server for Voice Cleaning Pipeline
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import os
import sys
import tempfile
import shutil
import json
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline import VoiceCleaningPipeline

app = FastAPI(title="Voice Cleaning API", version="1.0.0")

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

class ProcessingConfig(BaseModel):
    whisper_model: str = "base"
    enable_diarization: bool = True
    transcript_format: str = "txt"

def initialize_pipeline(config: ProcessingConfig):
    """Initialize pipeline with configuration"""
    global pipeline
    
    if pipeline is None:
        pipeline = VoiceCleaningPipeline("config.yaml")
    
    # Update configuration
    pipeline.config['asr']['model'] = config.whisper_model
    pipeline.config['diarization']['enabled'] = config.enable_diarization
    
    # Reinitialize ASR if model changed
    from asr_processor import ASRProcessor
    pipeline.asr = ASRProcessor(
        model_size=config.whisper_model,
        language=pipeline.config['asr'].get('language'),
        compute_type=pipeline.config['asr']['compute_type']
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
    """Health check endpoint"""
    return {"status": "healthy"}

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

@app.post("/api/process")
async def process_audio(
    file: UploadFile = File(...),
    whisper_model: str = "base",
    enable_diarization: bool = True,
    transcript_format: str = "txt"
):
    """Process uploaded audio/video file"""
    
    try:
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
