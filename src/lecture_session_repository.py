"""
LectureSession Repository — the "Student attends LectureSession -> generates
Transcript" part of the ERD, previously entirely missing.

One JSON file per session under data/lecture_sessions/ (mirrors lecture_
repository.py / student_repository.py's pattern). A session is created each
time a student successfully processes a lecture recording — start_time is
when the upload began, end_time is derived from the cleaned audio's own
duration. Deliberately not a full "live classroom" session model (there's no
live-recording feature in this app) — it's the record of "this student
engaged with this lecture, starting at this time, for this long."
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

_LOCK = threading.Lock()


class LectureSessionRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__), "..", "data", "lecture_sessions"
            )
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        safe = os.path.basename(session_id)  # guard against path traversal
        return os.path.join(self.data_dir, f"{safe}.json")

    def create(
        self,
        student_id: str,
        lecture_id: str,
        start_time: float,
        duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        session_id = uuid.uuid4().hex[:12]
        record = {
            "id": session_id,
            "student_id": student_id,
            "lecture_id": lecture_id,
            "start_time": start_time,
            "end_time": (start_time + duration_seconds) if duration_seconds else None,
            "created_at": time.time(),
        }
        with _LOCK:
            with open(self._path(session_id), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _all(self) -> List[Dict[str, Any]]:
        items = []
        for name in os.listdir(self.data_dir):
            if not name.endswith(".json"):
                continue
            try:
                with open(
                    os.path.join(self.data_dir, name), "r", encoding="utf-8"
                ) as f:
                    items.append(json.load(f))
            except Exception:
                continue
        return items

    def list_for_student(self, student_id: str) -> List[Dict[str, Any]]:
        items = [r for r in self._all() if r.get("student_id") == student_id]
        items.sort(key=lambda r: r.get("start_time") or 0, reverse=True)
        return items

    def list_for_lecture(self, lecture_id: str) -> List[Dict[str, Any]]:
        items = [r for r in self._all() if r.get("lecture_id") == lecture_id]
        items.sort(key=lambda r: r.get("start_time") or 0, reverse=True)
        return items


_default_repo: Optional[LectureSessionRepository] = None


def get_repository() -> LectureSessionRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = LectureSessionRepository()
    return _default_repo
