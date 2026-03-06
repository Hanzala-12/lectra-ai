"""
Basic unit tests for voice cleaning pipeline
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import VoiceCleaningPipeline


@pytest.fixture
def sample_audio():
    """Generate 1-second sample audio at 16kHz"""
    sample_rate = 16000
    duration = 1.0
    # Generate white noise
    samples = np.random.randn(int(sample_rate * duration)).astype(np.float32)
    return samples, sample_rate


@pytest.fixture
def pipeline():
    """Initialize pipeline with config and mocked models"""
    config_path = Path(__file__).parent.parent / "config.yaml"

    # Mock the heavy model components
    with patch(
        "src.deepfilter_processor.DeepFilterProcessor"
    ) as mock_deepfilter, patch(
        "src.asr_processor.ASRProcessor"
    ) as mock_asr, patch(
        "src.diarization.DiarizationProcessor"
    ) as mock_diarization:

        # Configure mocks
        mock_deepfilter.return_value = MagicMock()
        mock_asr.return_value = MagicMock()
        mock_diarization.return_value = MagicMock()

        pipeline = VoiceCleaningPipeline(str(config_path))
        return pipeline


def test_pipeline_initialization(pipeline):
    """Test pipeline initializes correctly"""
    assert pipeline is not None
    assert pipeline.media_loader is not None
    assert pipeline.vad is not None
    assert pipeline.deepfilter is not None
    assert pipeline.asr is not None


def test_config_loading():
    """Test configuration loads correctly"""
    config_path = Path(__file__).parent.parent / "config.yaml"

    with patch(
        "src.deepfilter_processor.DeepFilterProcessor"
    ) as mock_deepfilter, patch(
        "src.asr_processor.ASRProcessor"
    ) as mock_asr, patch(
        "src.diarization.DiarizationProcessor"
    ) as mock_diarization:

        mock_deepfilter.return_value = MagicMock()
        mock_asr.return_value = MagicMock()
        mock_diarization.return_value = MagicMock()

        pipeline = VoiceCleaningPipeline(str(config_path))

        assert "audio" in pipeline.config
        assert "vad" in pipeline.config
        assert "asr" in pipeline.config
        assert pipeline.config["audio"]["sample_rate"] == 16000


def test_vad_initialization(pipeline):
    """Test VAD processor initializes"""
    assert pipeline.vad is not None
    assert pipeline.vad.aggressiveness in [0, 1, 2, 3]


def test_asr_initialization(pipeline):
    """Test ASR processor initializes"""
    assert pipeline.asr is not None


# Add more tests as needed
