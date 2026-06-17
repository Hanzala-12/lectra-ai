"""
Lecture Repository — the "Lecture repository + Storage" box in the architecture.

Simple, dependency-free file storage: each processed lecture is one JSON record
holding the transcript, diarization, and any generated artifacts (notes, quiz,
schedule, evaluation). Swap for a real DB later without changing callers.
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

_LOCK = threading.Lock()


class LectureRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "lectures")
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, lecture_id: str) -> str:
        # guard against path traversal
        safe = os.path.basename(lecture_id)
        return os.path.join(self.data_dir, f"{safe}.json")

    def create(
        self,
        title: str,
        transcript_text: str = "",
        transcript_segments: Optional[List[Dict]] = None,
        diarization: Optional[List[Dict]] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        lecture_id = uuid.uuid4().hex[:12]
        record = {
            "id": lecture_id,
            "title": title or f"Lecture {lecture_id}",
            "created_at": time.time(),
            "transcript_text": transcript_text or "",
            "transcript_segments": transcript_segments or [],
            "diarization": diarization or [],
            "metadata": metadata or {},
            # generated artifacts (filled on demand)
            "notes": None,
            "quiz": None,
            "schedule": None,
            "evaluation": None,
            "chat_history": [],
        }
        self._write(record)
        return record

    def _write(self, record: Dict[str, Any]) -> None:
        with _LOCK:
            with open(self._path(record["id"]), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

    def get(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(lecture_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update(self, lecture_id: str, **fields) -> Optional[Dict[str, Any]]:
        record = self.get(lecture_id)
        if record is None:
            return None
        record.update(fields)
        self._write(record)
        return record

    def list(self) -> List[Dict[str, Any]]:
        items = []
        for name in os.listdir(self.data_dir):
            if not name.endswith(".json"):
                continue
            try:
                with open(
                    os.path.join(self.data_dir, name), "r", encoding="utf-8"
                ) as f:
                    r = json.load(f)
                # lightweight summary for the library view
                items.append(
                    {
                        "id": r.get("id"),
                        "title": r.get("title"),
                        "created_at": r.get("created_at"),
                        "duration": r.get("metadata", {}).get("duration_processed"),
                        "has_notes": r.get("notes") is not None,
                        "has_quiz": r.get("quiz") is not None,
                        "has_schedule": r.get("schedule") is not None,
                        "has_evaluation": r.get("evaluation") is not None,
                        "word_count": len((r.get("transcript_text") or "").split()),
                    }
                )
            except Exception:
                continue
        items.sort(key=lambda x: x.get("created_at") or 0, reverse=True)
        return items

    def delete(self, lecture_id: str) -> bool:
        path = self._path(lecture_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False


_default_repo: Optional[LectureRepository] = None


def get_repository() -> LectureRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = LectureRepository()
    return _default_repo
