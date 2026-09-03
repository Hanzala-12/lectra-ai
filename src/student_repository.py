"""
Student Repository — local/mock persistence for the Student entity.

Mirrors lecture_repository.py's design exactly: one JSON file per student
under data/students/ (git-ignored, same as data/lectures/). Deliberately
simple/local — the plan is to swap this for a real backend (e.g. Supabase)
later without changing student_repository's public interface, the same way
lecture_repository.py's own docstring already describes for lectures.

Passwords are never stored in plaintext — see auth_utils.py.
"""

import os
import json
import time
import uuid
import threading
from typing import List, Dict, Optional, Any

from auth_utils import hash_password, verify_password

_LOCK = threading.Lock()


class UsernameTakenError(Exception):
    pass


class StudentRepository:
    def __init__(self, data_dir: Optional[str] = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data", "students")
        self.data_dir = os.path.abspath(data_dir)
        os.makedirs(self.data_dir, exist_ok=True)

    def _path(self, student_id: str) -> str:
        # guard against path traversal
        safe = os.path.basename(student_id)
        return os.path.join(self.data_dir, f"{safe}.json")

    def _write(self, record: Dict[str, Any]) -> None:
        with _LOCK:
            with open(self._path(record["id"]), "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)

    def create(
        self, username: str, password: str, name: Optional[str] = None
    ) -> Dict[str, Any]:
        username = (username or "").strip()
        if not username or not password:
            raise ValueError("username and password are required")
        if self.get_by_username(username) is not None:
            raise UsernameTakenError(f"Username '{username}' is already taken")

        student_id = uuid.uuid4().hex[:12]
        record = {
            "id": student_id,
            "username": username,
            "name": name or username,
            "password_hash": hash_password(password),
            "created_at": time.time(),
        }
        self._write(record)
        return record

    def get(self, student_id: str) -> Optional[Dict[str, Any]]:
        path = self._path(student_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        username_lower = (username or "").strip().lower()
        if not username_lower:
            return None
        for record in self.list_raw():
            if record.get("username", "").lower() == username_lower:
                return record
        return None

    def list_raw(self) -> List[Dict[str, Any]]:
        """Full records, including password_hash - internal use only."""
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

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Return the student record if username+password match, else None."""
        record = self.get_by_username(username)
        if record is None:
            return None
        if not verify_password(password, record.get("password_hash", "")):
            return None
        return record

    @staticmethod
    def public(record: Dict[str, Any]) -> Dict[str, Any]:
        """Strip password_hash before this ever goes back over the API."""
        return {
            "id": record["id"],
            "username": record["username"],
            "name": record.get("name", record["username"]),
            "created_at": record.get("created_at"),
        }


_default_repo: Optional[StudentRepository] = None


def get_repository() -> StudentRepository:
    global _default_repo
    if _default_repo is None:
        _default_repo = StudentRepository()
    return _default_repo
