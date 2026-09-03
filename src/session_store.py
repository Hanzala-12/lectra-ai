"""
Session token storage — a single JSON file mapping token -> {student_id,
created_at}. File-backed (not just in-memory) so a backend restart during
development doesn't silently log everyone out. Same "simple local file,
swap for something real later" philosophy as lecture_repository.py and
student_repository.py.
"""

import os
import json
import time
import threading
from typing import Dict, Optional, Any

from auth_utils import new_session_token

_LOCK = threading.Lock()

SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 14  # 14 days


class SessionStore:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(
                os.path.dirname(__file__), "..", "data", "sessions.json"
            )
        self.path = os.path.abspath(path)
        # Lazy — no file (and no parent dir) created until the first actual
        # write. Creating it eagerly here polluted otherwise-empty temp
        # directories in unrelated tests that happened to share a tmp_path.

    def _load(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save(self, data: Dict[str, Any]) -> None:
        with _LOCK:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def create(self, student_id: str) -> str:
        token = new_session_token()
        data = self._load()
        data[token] = {"student_id": student_id, "created_at": time.time()}
        self._save(data)
        return token

    def resolve(self, token: str) -> Optional[str]:
        """Return the student_id for a valid, non-expired token, else None."""
        if not token:
            return None
        data = self._load()
        entry = data.get(token)
        if entry is None:
            return None
        if time.time() - entry.get("created_at", 0) > SESSION_MAX_AGE_SECONDS:
            del data[token]
            self._save(data)
            return None
        return entry.get("student_id")

    def revoke(self, token: str) -> None:
        data = self._load()
        if token in data:
            del data[token]
            self._save(data)


_default_store: Optional[SessionStore] = None


def get_session_store() -> SessionStore:
    global _default_store
    if _default_store is None:
        _default_store = SessionStore()
    return _default_store
