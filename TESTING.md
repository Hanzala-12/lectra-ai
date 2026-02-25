# Voice Cleaning Pipeline - Testing Guide

## Running Tests

### Install Test Dependencies
```powershell
pip install -r requirements-dev.txt
```

### Run All Tests
```powershell
pytest
```

### Run with Coverage
```powershell
pytest --cov=src --cov=backend --cov-report=html
```

This generates a coverage report in `htmlcov/index.html`

### Run Specific Tests
```powershell
# Test pipeline only
pytest tests/test_pipeline.py

# Test API only
pytest tests/test_api.py

# Run specific test function
pytest tests/test_api.py::test_health_endpoint
```

### Run with Verbose Output
```powershell
pytest -v
```

## Test Structure

```
tests/
├── __init__.py          # Test configuration
├── test_pipeline.py     # Pipeline unit tests
├── test_api.py          # API endpoint tests
└── conftest.py          # Shared fixtures (future)
```

## Writing Tests

### Example Unit Test
```python
def test_vad_processor():
    """Test VAD processes audio correctly"""
    vad = VADProcessor()
    audio = np.random.randn(16000)  # 1 second
    result = vad.process(audio, 16000)
    assert result is not None
```

### Example API Test
```python
def test_process_endpoint():
    """Test processing endpoint"""
    with open("test_audio.wav", "rb") as f:
        response = client.post(
            "/api/process",
            files={"file": ("test.wav", f, "audio/wav")},
            data={"whisper_model": "tiny"}
        )
    assert response.status_code == 200
```

## Code Quality

### Format Code
```powershell
black src/ backend.py tests/
```

### Lint Code
```powershell
flake8 src/ backend.py tests/
```

### Type Check
```powershell
mypy src/ backend.py
```

## Continuous Integration

Tests run automatically on:
- Push to main/develop branches
- Pull requests

See `.github/workflows/ci.yml` for CI configuration.
