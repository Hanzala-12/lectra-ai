"""
Basic unit tests for voice cleaning pipeline
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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
    """Initialize pipeline with config"""
    config_path = Path(__file__).parent.parent / "config.yaml"
    return VoiceCleaningPipeline(str(config_path))

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
    pipeline = VoiceCleaningPipeline(str(config_path))
    
    assert 'audio' in pipeline.config
    assert 'vad' in pipeline.config
    assert 'asr' in pipeline.config
    assert pipeline.config['audio']['sample_rate'] == 16000

def test_vad_initialization(pipeline):
    """Test VAD processor initializes"""
    assert pipeline.vad is not None
    assert pipeline.vad.aggressiveness in [0, 1, 2, 3]

def test_asr_initialization(pipeline):
    """Test ASR processor initializes"""
    assert pipeline.asr is not None
    assert pipeline.asr.model is not None

# Add more tests as needed
