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


def test_target_voice_isolation_is_invoked_when_enabled(pipeline, tmp_path):
    """When a target_voice_isolator is present, STEP 2 must fetch
    embeddings alongside diarization (diarize_with_embeddings, not the
    plain diarize()) and STEP 2.5 must feed both into isolator.process(),
    using ITS return value as the audio DeepFilterNet actually sees -
    proves the wiring, not just that the module exists in isolation."""
    audio = np.random.randn(96000).astype(np.float32)
    pipeline.config["asr"]["skip"] = True
    # STEP 3 applies its own independent HPF to whatever lands in a speech
    # segment - unrelated to this test's concern (STEP 2.5's wiring), so
    # disable it to keep the isolator's output comparable byte-for-byte.
    pipeline.config["high_pass_filter"]["enabled"] = False

    pipeline.media_loader.load_media = Mock(return_value=(audio, 48000, False))
    pipeline.media_loader.save_audio = Mock()
    pipeline.vad_processor.trim_silence = Mock(return_value=(audio, [(0, len(audio))]))

    diarization_segments = [
        {"start": 0.5, "end": 1.5, "speaker": "SPEAKER_00"},
        {"start": 1.0, "end": 1.2, "speaker": "SPEAKER_01"},
    ]
    speaker_embeddings = {
        "SPEAKER_00": np.array([1, 0]),
        "SPEAKER_01": np.array([0, 1]),
    }
    pipeline.diarization.diarize_with_embeddings = Mock(
        return_value=(diarization_segments, speaker_embeddings)
    )
    pipeline.diarization.diarize = Mock(
        side_effect=AssertionError(
            "plain diarize() should not be called when an isolator is active"
        )
    )
    pipeline.diarization.get_speaker_statistics = Mock(
        return_value={"SPEAKER_00": 1.0, "SPEAKER_01": 0.2}
    )

    isolated_audio = audio * 0.5  # distinguishable stand-in for isolator output
    mock_isolator = MagicMock()
    mock_isolator.process = Mock(return_value=isolated_audio)
    # Bypass the real _initialize_custom_modules() (which would otherwise
    # set this back to None, since config.yaml's target_voice_isolation is
    # disabled by default) so this test exercises STEP 2/2.5's wiring
    # directly rather than needing to fake an enabled config + GPU.
    pipeline._custom_modules_initialized = True
    pipeline.target_voice_isolator = mock_isolator
    pipeline.speaker_confidence_gate = None

    pipeline.deepfilter.sample_rate = 48000
    pipeline.deepfilter.process_audio_native = Mock(side_effect=lambda segment: segment)

    result = pipeline.process(
        input_path="sample.wav",
        output_dir=str(tmp_path),
        save_transcript=False,
    )

    assert result["audio_output_path"]
    mock_isolator.process.assert_called_once()
    called_sr, called_diarization, called_embeddings = (
        mock_isolator.process.call_args.args[1:]
    )
    assert called_sr == 48000
    assert called_diarization == diarization_segments
    # dict values are numpy arrays - compare key-by-key, not via dict == (a
    # bare `==` on numpy-valued dicts raises on the ambiguous array truth value)
    assert set(called_embeddings.keys()) == set(speaker_embeddings.keys())
    for key in speaker_embeddings:
        np.testing.assert_array_equal(called_embeddings[key], speaker_embeddings[key])

    # DeepFilterNet must have received the ISOLATOR's output within the
    # speech-segment region STEP 3's zero-background mask preserves (0.5s-
    # 1.5s -> samples 24000-72000 @ 48kHz); outside diarized speech, STEP 3
    # zeroes everything regardless of what STEP 2.5 produced - same
    # masking every other stage already gets, unrelated to this feature.
    processed_segment = pipeline.deepfilter.process_audio_native.call_args.args[0]
    np.testing.assert_array_equal(
        processed_segment[24000:72000], isolated_audio[24000:72000]
    )
    assert np.all(processed_segment[:24000] == 0)


def test_speaker_confidence_gate_triggers_embeddings_fetch(pipeline, tmp_path):
    """When ONLY a speaker_confidence_gate is present (target_voice_isolator
    is None - the realistic deployment, since this gate is CPU-friendly and
    target_voice_isolation is GPU-gated), STEP 2 must still fetch embeddings
    alongside diarization (diarize_with_embeddings, not the plain diarize()).
    Regression test for a real bug found during design: the STEP 2
    conditional originally only checked target_voice_isolator, so a
    gate-only deployment would silently get zero speaker_embeddings and the
    gate would have nothing to compare against - a no-op that looks like
    it's running."""
    audio = np.random.randn(96000).astype(np.float32)
    pipeline.config["asr"]["skip"] = True
    pipeline.config["high_pass_filter"]["enabled"] = False

    pipeline.media_loader.load_media = Mock(return_value=(audio, 48000, False))
    pipeline.media_loader.save_audio = Mock()
    pipeline.vad_processor.trim_silence = Mock(return_value=(audio, [(0, len(audio))]))

    diarization_segments = [{"start": 0.0, "end": 2.0, "speaker": "SPEAKER_00"}]
    speaker_embeddings = {"SPEAKER_00": np.array([1, 0])}
    pipeline.diarization.diarize_with_embeddings = Mock(
        return_value=(diarization_segments, speaker_embeddings)
    )
    pipeline.diarization.diarize = Mock(
        side_effect=AssertionError(
            "plain diarize() should not be called when a speaker_confidence_gate is active"
        )
    )
    pipeline.diarization.get_speaker_statistics = Mock(return_value={"SPEAKER_00": 2.0})

    mock_gate = MagicMock()
    mock_gate.compute_gain_curve = Mock(
        return_value=np.ones(len(audio), dtype=np.float32)
    )
    # Same bypass pattern as the TVI wiring test above - exercise STEP 2's
    # wiring directly rather than needing to fake an enabled config + CPU
    # feasibility check.
    pipeline._custom_modules_initialized = True
    pipeline.target_voice_isolator = None
    pipeline.speaker_confidence_gate = mock_gate

    pipeline.deepfilter.sample_rate = 48000
    pipeline.deepfilter.process_audio_native = Mock(side_effect=lambda segment: segment)

    result = pipeline.process(
        input_path="sample.wav",
        output_dir=str(tmp_path),
        save_transcript=False,
    )

    assert result["audio_output_path"]
    pipeline.diarization.diarize_with_embeddings.assert_called_once()
    mock_gate.compute_gain_curve.assert_called_once()
    called_audio, called_sr, called_segments, called_diarization, called_embeddings = (
        mock_gate.compute_gain_curve.call_args.args
    )
    assert called_sr == 48000
    assert called_diarization == diarization_segments
    assert set(called_embeddings.keys()) == set(speaker_embeddings.keys())
    for key in speaker_embeddings:
        np.testing.assert_array_equal(called_embeddings[key], speaker_embeddings[key])


# Add more tests as needed
