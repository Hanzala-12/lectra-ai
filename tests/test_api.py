"""
API endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend import app

client = TestClient(app)

def test_root_endpoint():
    """Test API root"""
    response = client.get("/")
    assert response.status_code == 200
    assert "name" in response.json()
    assert response.json()["status"] == "running"

def test_health_endpoint():
    """Test health check"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "gpu_available" in data
    assert "version" in data
    assert "timestamp" in data

def test_models_endpoint():
    """Test models list endpoint"""
    response = client.get("/api/models")
    assert response.status_code == 200
    data = response.json()
    assert "whisper_models" in data
    assert "transcript_formats" in data
    assert len(data["whisper_models"]) > 0

def test_invalid_file_type():
    """Test uploading invalid file type"""
    response = client.post(
        "/api/process",
        files={"file": ("test.txt", b"not an audio file", "text/plain")},
        data={"whisper_model": "base"}
    )
    assert response.status_code == 400

def test_invalid_whisper_model():
    """Test invalid model name"""
    # This would need a valid audio file
    # Skipping actual file processing in unit tests
    pass

# Add more API tests
