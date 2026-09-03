"""
Quiz Repository — Quiz (with its nested Question/Answer entities) as a real,
independently-addressable, versioned top-level entity, instead of a single
`quiz` field embedded on the Lecture record.

One JSON file per generated quiz under data/quizzes/. Regenerating a quiz now
creates a NEW record (real history - every past quiz a student took is still
there) instead of silently overwriting the previous one.
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

_LOCK = threading.Lock()


class QuizRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "quizzes")
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, quiz_id: str) -> str:
        safe = os.path.basename(quiz_id)  # guard against path traversal
        return os.path.join(self.data_dir, f"{safe}.json")

    def create(
        self, lecture_id: str, student_id: str, questions: List[Dict]
    ) -> Dict[str, Any]:
        quiz_id = uuid.uuid4().hex[:12]
        record = {
            "id": quiz_id,
            "lecture_id": lecture_id,
            "student_id": student_id,
            "questions": questions,
            "created_at": time.time(),
        }
        with _LOCK:
            with open(self._path(quiz_id), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    def get(self, quiz_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(quiz_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

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

    def get_latest_for_lecture(self, lecture_id: str) -> Optional[Dict[str, Any]]:
        items = self.list_for_lecture(lecture_id)
        return items[0] if items else None


_default_repo: Optional[QuizRepository] = None


def get_repository() -> QuizRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = QuizRepository()
    return _default_repo
