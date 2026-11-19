"""Unit tests for MediaLoader (audio loading, saving, video handling)."""

from unittest import mock

import numpy as np
import pytest
import soundfile as sf

from src import media_loader
from src.media_loader import MediaLoader


@pytest.fixture
def wav_file(tmp_path):
    sr = 22050
    t = np.arange(sr) / sr
    path = tmp_path / "tone.wav"
    sf.write(str(path), 0.3 * np.sin(2 * np.pi * 440 * t), sr)
    return str(path)


class TestLoadMedia:
    def test_loads_and_resamples_audio(self, wav_file):
        audio, sr, is_video = MediaLoader(target_sr=16000).load_media(wav_file)
        assert sr == 16000 and is_video is False
        assert audio.ndim == 1 and abs(len(audio) - 16000) <= 2

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MediaLoader().load_media(str(tmp_path / "nope.wav"))

    def test_unsupported_extension(self, tmp_path):
        p = tmp_path / "doc.txt"
        p.write_text("hi")
        with pytest.raises(ValueError, match="Unsupported"):
            MediaLoader().load_media(str(p))

    def test_corrupt_audio_raises(self, tmp_path):
        p = tmp_path / "broken.wav"
        p.write_bytes(b"this is not audio")
        with pytest.raises(Exception):
            MediaLoader().load_media(str(p))

    def test_video_routes_to_extractor(self, tmp_path):
        p = tmp_path / "clip.mp4"
        p.write_bytes(b"x")
        loader = MediaLoader()
        with mock.patch.object(
            loader, "_extract_audio_from_video", return_value=(np.zeros(10), 16000)
        ) as m:
            audio, sr, is_video = loader.load_media(str(p))
        m.assert_called_once()
        assert is_video is True and sr == 16000


class TestVideoExtraction:
    def test_requires_moviepy(self, monkeypatch):
        monkeypatch.setattr(media_loader, "VideoFileClip", None)
        with pytest.raises(ImportError, match="moviepy"):
            MediaLoader()._extract_audio_from_video("x.mp4")

    def test_video_without_audio_track(self, monkeypatch):
        clip = mock.MagicMock()
        clip.audio = None
        monkeypatch.setattr(media_loader, "VideoFileClip", lambda p: clip)
        with pytest.raises(ValueError, match="no audio"):
            MediaLoader()._extract_audio_from_video("x.mp4")

    def test_extracts_audio_and_cleans_temp_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        sr = 16000

        def fake_write(path, **kwargs):
            sf.write(path, 0.2 * np.sin(2 * np.pi * 300 * np.arange(sr) / sr), sr)

        clip = mock.MagicMock()
        clip.audio.write_audiofile.side_effect = fake_write
        monkeypatch.setattr(media_loader, "VideoFileClip", lambda p: clip)
        audio, out_sr = MediaLoader()._extract_audio_from_video("x.mp4")
        assert out_sr == sr and len(audio) > 0
        assert not (tmp_path / "temp_extracted_audio.wav").exists()
        clip.close.assert_called_once()


class TestSaveAudio:
    @pytest.mark.parametrize("bit_depth,subtype", [(16, "PCM_16"), (24, "PCM_24")])
    def test_save_wav(self, tmp_path, bit_depth, subtype):
        out = tmp_path / "nested" / "out.wav"
        MediaLoader().save_audio(
            np.zeros(1600, dtype=np.float32), 16000, str(out), bit_depth=bit_depth
        )
        assert sf.info(str(out)).subtype == subtype

    def test_save_other_format_goes_through_pydub(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        seg = mock.MagicMock()
        fake = mock.MagicMock()
        fake.from_wav.return_value = seg
        monkeypatch.setattr(media_loader, "AudioSegment", fake)
        MediaLoader().save_audio(
            np.zeros(1600, dtype=np.float32),
            16000,
            str(tmp_path / "o.mp3"),
            format="mp3",
        )
        seg.export.assert_called_once()
        assert not (tmp_path / "temp_output.wav").exists()


class TestMergeAudioToVideo:
    def test_merge_success_and_failure(self):
        fake_moviepy = mock.MagicMock()
        with mock.patch.dict(
            "sys.modules",
            {"moviepy": fake_moviepy, "moviepy.editor": fake_moviepy.editor},
        ):
            MediaLoader().merge_audio_to_video("v.mp4", "a.wav", "out.mp4")
            fake_moviepy.editor.VideoFileClip.return_value.set_audio.assert_called_once()
            fake_moviepy.editor.VideoFileClip.side_effect = RuntimeError("boom")
            with pytest.raises(RuntimeError):
                MediaLoader().merge_audio_to_video("v.mp4", "a.wav", "out.mp4")
