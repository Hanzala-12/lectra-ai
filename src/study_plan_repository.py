"""
StudyPlan Repository — StudyPlan as a real, independently-addressable,
versioned top-level entity (plan_id, student_id, lecture_id, available_time,
learning_goals - the ERD's exact fields), instead of a single `schedule`
field embedded on the Lecture record.

One JSON file per generated plan under data/study_plans/. Regenerating a
plan creates a NEW record instead of overwriting the previous one.
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

_LOCK = threading.Lock()


class StudyPlanRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(
                os.path.dirname(__file__), "..", "data", "study_plans"
            )
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, plan_id: str) -> str:
        safe = os.path.basename(plan_id)  # guard against path traversal
        return os.path.join(self.data_dir, f"{safe}.json")

    def create(
        self,
        lecture_id: str,
        student_id: str,
        plan: List[Dict],
        tips: List[str],
        available_time: Optional[str] = None,
        learning_goals: Optional[str] = None,
    ) -> Dict[str, Any]:
        plan_id = uuid.uuid4().hex[:12]
        record = {
            "id": plan_id,
            "lecture_id": lecture_id,
            "student_id": student_id,
            "available_time": available_time,
            "learning_goals": learning_goals,
            "plan": plan,
            "tips": tips,
            "created_at": time.time(),
        }
        with _LOCK:
            with open(self._path(plan_id), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
        return record

    def get(self, plan_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(plan_id)
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


_default_repo: Optional[StudyPlanRepository] = None


def get_repository() -> StudyPlanRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = StudyPlanRepository()
    return _default_repo
