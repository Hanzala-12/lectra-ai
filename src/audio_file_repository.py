"""
AudioFile Repository — the AudioFile entity as a real, independently-
addressable top-level record instead of a field embedded on the Lecture
record.

One JSON file per lecture's audio-file bundle (original/cleaned/each
speaker track, produced together by one processing run) under
data/audio_files/. A lecture has exactly one of these today (audio isn't
regenerated the way notes/quiz/schedule are) - if that ever changes, this
already supports multiple records per lecture via list_for_lecture().
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

_LOCK = threading.Lock()


class AudioFileRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__), "..", "data", "audio_files"
            )
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, record_id: str) -> str:
        safe = os.path.basename(record_id)  # guard against path traversal
        return os.path.join(self.data_dir, f"{safe}.json")

    def create(
        self,
        lecture_id: str,
        session_id: Optional[str],
        files: List[Dict],
    ) -> Dict[str, Any]:
        record_id = uuid.uuid4().hex[:12]
        record = {
            "id": record_id,
            "lecture_id": lecture_id,
            "session_id": session_id,
            "files": files,  # [{audio_id, kind, file_path, duration}]
            "created_at": time.time(),
        }
        with _LOCK:
            with open(self._path(record_id), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    def list_for_lecture(self, lecture_id: str) -> List[Dict[str, Any]]:
        items = []
        for name in os.listdir(self.data_dir):
            if not name.endswith(".json"):
                continue
            try:
                with open(
                    os.path.join(self.data_dir, name), "r", encoding="utf-8"
                ) as f:
                    r = json.load(f)
                if r.get("lecture_id") == lecture_id:
                    items.append(r)
            except Exception:
                continue
        items.sort(key=lambda r: r.get("created_at") or 0, reverse=True)
        return items

    def get_for_lecture(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        items = self.list_for_lecture(lecture_id)
        return items[0] if items else None


_default_repo: Optional[AudioFileRepository] = None


def get_repository() -> AudioFileRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = AudioFileRepository()
    return _default_repo
