"""
API endpoint tests
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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


def test_process_requires_auth():
    """/api/process now requires a logged-in student"""
    response = client.post(
        "/api/process",
        files={"file": ("test.txt", b"not an audio file", "text/plain")},
        data={"whisper_model": "base"},
    )
    assert response.status_code == 401


def test_invalid_file_type():
    """Test uploading invalid file type (logged in — the 401 case is covered
    by test_process_requires_auth above)."""
    signup = client.post(
        "/api/auth/signup",
        json={"username": "filetype_tester", "password": "Test#Pass123"},
    )
    headers = {"Authorization": f"Bearer {signup.json()['token']}"}

    response = client.post(
        "/api/process",
        files={"file": ("test.txt", b"not an audio file", "text/plain")},
        data={"whisper_model": "base"},
        headers=headers,
    )
    assert response.status_code == 400


def test_invalid_whisper_model():
    """Test invalid model name"""
    # This would need a valid audio file
    # Skipping actual file processing in unit tests
    pass


# Add more API tests


@pytest.mark.parametrize(
    "name",
    [
        "..%2Fconfig.yaml",
        "..%5Cconfig.yaml",  # Windows separator - was served before the fix
        "..%5C..%5C.env",
        "%2e%2e%5cconfig.yaml",
        "C%3A%5CWindows%5Cwin.ini",
    ],
)
def test_download_blocks_path_traversal(name):
    """/api/download must never serve files from outside outputs/."""
    response = client.get(f"/api/download/{name}")
    assert response.status_code in (400, 404)


def test_download_serves_file_inside_outputs():
    outputs = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(outputs, exist_ok=True)
    fname = "qa_regression_probe.txt"
    path = os.path.join(outputs, fname)
    with open(path, "w", encoding="utf-8") as f:
        f.write("probe")
    try:
        response = client.get(f"/api/download/{fname}")
        assert response.status_code == 200
        assert response.content == b"probe"
    finally:
        os.remove(path)
