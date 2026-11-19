"""Unit tests for utils, the file cache and the lecture-session repository."""

import json

import numpy as np
import pytest

from src import utils
from src.cache_manager import FileCache
from src.lecture_session_repository import LectureSessionRepository


# --------------------------------------------------------------------- utils
class TestUtils:
    def test_get_audio_files_recursive_and_flat(self, tmp_path):
        (tmp_path / "a.wav").write_bytes(b"x")
        (tmp_path / "notes.txt").write_bytes(b"x")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.MP3".lower()).write_bytes(b"x")
        (sub / "c.mp4").write_bytes(b"x")

        recursive = utils.get_audio_files(str(tmp_path))
        flat = utils.get_audio_files(str(tmp_path), recursive=False)

        assert len(recursive) == 3
        assert all(not p.endswith(".txt") for p in recursive)
        assert len(flat) == 1 and flat[0].endswith("a.wav")

    @pytest.mark.parametrize(
        "seconds,expected",
        [
            (0, "00:00"),
            (59, "00:59"),
            (61, "01:01"),
            (3600, "01:00:00"),
            (3725, "01:02:05"),
        ],
    )
    def test_format_duration(self, seconds, expected):
        assert utils.format_duration(seconds) == expected

    def test_calculate_snr_known_ratio(self):
        signal = np.ones(1000)
        noise = np.ones(1000) * 0.1
        assert utils.calculate_snr(signal, noise) == pytest.approx(20.0, abs=1e-6)

    def test_calculate_snr_zero_noise_is_infinite(self):
        assert utils.calculate_snr(np.ones(10), np.zeros(10)) == float("inf")

    def test_create_directories(self, tmp_path):
        utils.create_directories(str(tmp_path))
        for d in ("uploads", "outputs", "temp", "models"):
            assert (tmp_path / d).is_dir()
        utils.create_directories(str(tmp_path))  # idempotent


# --------------------------------------------------------------------- cache
CONFIG = {
    "asr": {"model": "base", "compute_type": "int8"},
    "diarization": {"enabled": True},
    "audio": {"sample_rate": 16000},
}


@pytest.fixture
def cache_env(tmp_path):
    src = tmp_path / "in.wav"
    src.write_bytes(b"RIFF-input-audio")
    out = tmp_path / "out.wav"
    out.write_bytes(b"RIFF-cleaned-audio")
    transcript = tmp_path / "t.txt"
    transcript.write_text("hello world", encoding="utf-8")
    return FileCache(str(tmp_path / "cache")), str(src), str(out), str(transcript)


class TestFileCache:
    def test_miss_then_hit(self, cache_env):
        cache, src, out, transcript = cache_env
        assert cache.get(src, CONFIG) is None
        cache.set(src, CONFIG, {"duration": 1.5}, out, transcript)
        hit = cache.get(src, CONFIG)
        assert hit is not None
        assert hit["metadata"]["result"] == {"duration": 1.5}
        assert hit["metadata"]["input_file"] == "in.wav"
        assert hit["cache_path"] and hit["audio_path"].endswith("cleaned_audio.wav")

    def test_key_changes_with_relevant_config(self, cache_env):
        cache, src, *_ = cache_env
        other = {**CONFIG, "asr": {"model": "small", "compute_type": "int8"}}
        assert cache._generate_key(src, CONFIG) != cache._generate_key(src, other)

    def test_key_changes_with_file_content(self, cache_env, tmp_path):
        cache, src, *_ = cache_env
        first = cache._generate_key(src, CONFIG)
        (tmp_path / "in.wav").write_bytes(b"different")
        assert cache._generate_key(src, CONFIG) != first

    def test_corrupted_entry_is_a_miss(self, cache_env):
        cache, src, out, _ = cache_env
        cache.set(src, CONFIG, {}, out)
        key = cache._generate_key(src, CONFIG)
        (cache.cache_dir / key / "cleaned_audio.wav").unlink()
        assert cache.get(src, CONFIG) is None
        (cache.cache_dir / key / "metadata.json").unlink()
        assert cache.get(src, CONFIG) is None

    def test_set_without_transcript(self, cache_env):
        cache, src, out, _ = cache_env
        cache.set(src, CONFIG, {}, out, transcript_path="does-not-exist.txt")
        key = cache._generate_key(src, CONFIG)
        assert not (cache.cache_dir / key / "transcript.txt").exists()

    def test_stats_and_clear(self, cache_env):
        cache, src, out, transcript = cache_env
        assert cache.get_stats()["items"] == 0
        cache.set(src, CONFIG, {}, out, transcript)
        stats = cache.get_stats()
        assert stats["items"] == 1 and stats["size_mb"] > 0
        cache.clear()
        assert cache.get_stats()["items"] == 0

    def test_errors_never_raise(self, tmp_path):
        cache = FileCache(str(tmp_path / "c"))
        assert cache.get(str(tmp_path / "missing.wav"), CONFIG) is None
        cache.set(str(tmp_path / "missing.wav"), CONFIG, {}, "nope.wav")  # no exception


# ------------------------------------------------------ lecture sessions repo
class TestLectureSessionRepository:
    def test_create_get_and_end_time(self, tmp_path):
        repo = LectureSessionRepository(str(tmp_path))
        rec = repo.create("stu1", "lec1", start_time=100.0, duration_seconds=60.0)
        assert rec["end_time"] == 160.0
        assert repo.get(rec["id"])["lecture_id"] == "lec1"
        assert repo.get("unknown") is None

    def test_end_time_none_without_duration(self, tmp_path):
        repo = LectureSessionRepository(str(tmp_path))
        assert repo.create("s", "l", 1.0)["end_time"] is None

    def test_listing_filters_and_orders(self, tmp_path):
        repo = LectureSessionRepository(str(tmp_path))
        a = repo.create("s1", "l1", 10.0)
        b = repo.create("s1", "l2", 20.0)
        repo.create("s2", "l1", 30.0)
        assert [r["id"] for r in repo.list_for_student("s1")] == [b["id"], a["id"]]
        assert len(repo.list_for_lecture("l1")) == 2
        assert repo.list_for_student("nobody") == []

    def test_corrupt_and_foreign_files_are_ignored(self, tmp_path):
        repo = LectureSessionRepository(str(tmp_path))
        repo.create("s1", "l1", 1.0)
        (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
        (tmp_path / "readme.txt").write_text("x", encoding="utf-8")
        assert len(repo.list_for_student("s1")) == 1

    def test_session_id_cannot_traverse(self, tmp_path):
        repo = LectureSessionRepository(str(tmp_path / "sessions"))
        outside = tmp_path / "secret.json"
        outside.write_text(json.dumps({"x": 1}), encoding="utf-8")
        assert repo.get("../secret") is None
