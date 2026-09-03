"""
Shared pytest fixtures for the FastAPI test suite.

- isolated_repos (autouse): points the lecture/student/session file-backed
  repositories at fresh temp directories for every test, so nothing here
  ever touches real data/lectures, data/students, or data/sessions.json.
- fake_llm (autouse): replaces study_api's LLM client with a deterministic
  stand-in — no network/credits needed to test routing/validation/persistence.
- auth: signs up a fresh throwaway student via the real signup endpoint and
  returns headers + student_id for tests that need a logged-in session.
"""

import os
import sys
from dataclasses import dataclass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from backend import app
import lecture_repository
import student_repository
import session_store
import study_api

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_repos(tmp_path, monkeypatch):
    monkeypatch.setattr(
        lecture_repository,
        "_default_repo",
        lecture_repository.LectureRepository(data_dir=str(tmp_path / "lectures")),
    )
    monkeypatch.setattr(
        student_repository,
        "_default_repo",
        student_repository.StudentRepository(data_dir=str(tmp_path / "students")),
    )
    monkeypatch.setattr(
        session_store,
        "_default_store",
        session_store.SessionStore(path=str(tmp_path / "sessions.json")),
    )
    yield


class FakeLLM:
    """Stand-in for llm_client.LLMClient — deterministic canned output, no network."""

    model = "fake-model"

    def is_configured(self):
        return True

    def complete(self, prompt, system=None, **kwargs):
        return "This is a fake LLM answer."

    def complete_json(self, prompt, system=None, **kwargs):
        # Route on a phrase unique to each study_tools prompt (careful:
        # "questions" alone is NOT unique — evaluate()'s JSON schema also
        # contains "comprehension_questions").
        if "multiple-choice" in prompt:
            return {
                "questions": [
                    {
                        "question": "What does photosynthesis produce?",
                        "options": ["Glucose", "Salt", "Iron", "Sand"],
                        "answer_index": 0,
                        "explanation": "Photosynthesis produces glucose and oxygen.",
                    }
                ]
            }
        if "study plan" in prompt:
            return {
                "plan": [
                    {
                        "day": 1,
                        "focus": "Intro",
                        "tasks": ["Read notes"],
                        "est_minutes": 30,
                    }
                ],
                "tips": ["Review daily"],
            }
        # evaluate_lecture's prompt
        return {
            "main_topics": ["Photosynthesis"],
            "difficulty": "beginner",
            "estimated_study_minutes": 30,
            "prerequisites": [],
            "comprehension_questions": ["What is photosynthesis?"],
            "summary": "A summary.",
        }


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(study_api, "get_llm", lambda: fake)
    yield fake


@dataclass
class AuthedStudent:
    headers: dict
    student_id: str
    username: str
    token: str


@pytest.fixture
def auth(isolated_repos) -> AuthedStudent:
    """Sign up a fresh throwaway student via the real /api/auth/signup route."""
    username = f"test_{os.urandom(4).hex()}"
    r = client.post(
        "/api/auth/signup", json={"username": username, "password": "testpass123"}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    return AuthedStudent(
        headers={"Authorization": f"Bearer {body['token']}"},
        student_id=body["student"]["id"],
        username=username,
        token=body["token"],
    )
