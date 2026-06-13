"""
Basic unit tests for Lectra AI pipeline
"""

import pytest
import numpy as np
from pathlib import Path
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pipeline import LectraAIPipeline


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

    # Mock the heavy model components at the location where pipeline imports them
    with patch("pipeline.DeepFilterProcessor") as mock_deepfilter, patch(
        "pipeline.ASRProcessor"
    ) as mock_asr, patch("pipeline.SpeakerDiarization") as mock_diarization:

        # Configure mocks
        mock_deepfilter.return_value = MagicMock()
        mock_asr.return_value = MagicMock()
        mock_diarization.return_value = MagicMock()

        pipeline = LectraAIPipeline(str(config_path))
        return pipeline


def test_pipeline_initialization(pipeline):
    """Test pipeline initializes correctly"""
    assert pipeline is not None
    assert pipeline.media_loader is not None
    assert pipeline.vad_processor is not None
    assert pipeline.deepfilter is not None
    # ASR is lazy-loaded
    # Diarization may be None if disabled


def test_config_loading():
    """Test configuration loads correctly"""
    config_path = Path(__file__).parent.parent / "config.yaml"

    with patch("pipeline.DeepFilterProcessor") as mock_deepfilter, patch(
        "pipeline.ASRProcessor"
    ) as mock_asr, patch("pipeline.SpeakerDiarization") as mock_diarization:

        mock_deepfilter.return_value = MagicMock()
        mock_asr.return_value = MagicMock()
        mock_diarization.return_value = MagicMock()

        pipeline = LectraAIPipeline(str(config_path))

        assert "audio" in pipeline.config
        assert "vad" in pipeline.config
        assert "asr" in pipeline.config
        assert pipeline.config["audio"]["sample_rate"] == 16000


def test_vad_initialization(pipeline):
    """Test VAD processor initializes"""
    assert pipeline.vad_processor is not None
    assert hasattr(pipeline.vad_processor, "trim_silence")


def test_asr_initialization(pipeline):
    """Test ASR processor can be initialized (lazy-loaded)"""
    # ASR is lazy-loaded, so it starts as None
    # This test just ensures pipeline has the attribute
    assert hasattr(pipeline, "asr")


def test_deepfilter_full_audio_mode(pipeline, tmp_path):
    audio = np.random.randn(96000).astype(np.float32)
    pipeline.config["asr"]["skip"] = True

    pipeline.media_loader.load_media = Mock(return_value=(audio, 48000, False))
    pipeline.media_loader.save_audio = Mock()
    pipeline.vad_processor.trim_silence = Mock(return_value=(audio, [(0, len(audio))]))
    pipeline.diarization.diarize = Mock(
        return_value=[{"start": 0.5, "end": 1.5, "speaker": "SPEAKER_00"}]
    )
    pipeline.diarization.get_speaker_statistics = Mock(return_value={"SPEAKER_00": 1})
    pipeline.deepfilter.sample_rate = 48000
    pipeline.deepfilter.process_audio_native = Mock(side_effect=lambda segment: segment)

    result = pipeline.process(
        input_path="sample.wav",
        output_dir=str(tmp_path),
        save_transcript=False,
    )

    assert result["audio_output_path"]
    assert pipeline.deepfilter.process_audio_native.call_count == 1
    processed_segment = pipeline.deepfilter.process_audio_native.call_args.args[0]
    assert len(processed_segment) == len(audio)
    assert pipeline.config["deepfilternet"]["atten_lim_db"] == 30


# Add more tests as needed
