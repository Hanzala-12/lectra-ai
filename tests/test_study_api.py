"""
Study API tests — /api/library, /api/lecture CRUD, and the LLM-backed generators
(notes/quiz/schedule/evaluation/chat).

The LLM client is mocked (FakeLLM below) so these run fast, fully offline, and
without needing real OpenRouter credits — they test our routing/validation/
persistence logic, not OpenRouter's actual model quality. The lecture repository
is pointed at a temp directory per test so nothing here touches the real
data/lectures/ directory.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from backend import app
import lecture_repository
import study_api

client = TestClient(app)


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
def isolated_repo(tmp_path, monkeypatch):
    """Point the lecture repository singleton at a temp dir for every test here."""
    repo = lecture_repository.LectureRepository(data_dir=str(tmp_path))
    monkeypatch.setattr(lecture_repository, "_default_repo", repo)
    yield repo


@pytest.fixture(autouse=True)
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(study_api, "get_llm", lambda: fake)
    yield fake


@pytest.fixture
def lecture(isolated_repo):
    """A real lecture record via the actual repository (repo itself isn't mocked)."""
    return isolated_repo.create(
        title="Test Lecture",
        transcript_text=(
            "Photosynthesis converts light energy into chemical energy stored "
            "in glucose, using carbon dioxide and water as inputs."
        ),
    )


# ----------------------------------------------------------------- library / CRUD


def test_llm_status_configured():
    r = client.get("/api/llm-status")
    assert r.status_code == 200
    assert r.json() == {"configured": True, "model": "fake-model"}


def test_library_empty():
    r = client.get("/api/library")
    assert r.status_code == 200
    assert r.json() == {"lectures": []}


def test_create_and_get_lecture():
    r = client.post(
        "/api/lecture", json={"title": "My Lecture", "transcript": "Some text."}
    )
    assert r.status_code == 200
    lecture_id = r.json()["id"]

    r2 = client.get(f"/api/lecture/{lecture_id}")
    assert r2.status_code == 200
    assert r2.json()["transcript_text"] == "Some text."
    # new field from the quiz-persistence fix should exist from creation
    assert r2.json()["quiz_attempts"] == []


def test_get_missing_lecture_404():
    r = client.get("/api/lecture/does-not-exist")
    assert r.status_code == 404


def test_delete_lecture(lecture):
    r = client.delete(f"/api/lecture/{lecture['id']}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert client.get(f"/api/lecture/{lecture['id']}").status_code == 404


def test_delete_missing_lecture_404():
    r = client.delete("/api/lecture/does-not-exist")
    assert r.status_code == 404


def test_library_lists_created_lecture(lecture):
    r = client.get("/api/library")
    ids = [l["id"] for l in r.json()["lectures"]]
    assert lecture["id"] in ids


# ----------------------------------------------------------------- generators


def test_generate_notes(lecture):
    r = client.post(f"/api/lecture/{lecture['id']}/notes")
    assert r.status_code == 200
    assert r.json()["cached"] is False
    assert "fake LLM answer" in r.json()["notes"]

    r2 = client.post(f"/api/lecture/{lecture['id']}/notes")
    assert r2.json()["cached"] is True


def test_generate_notes_refresh_bypasses_cache(lecture):
    client.post(f"/api/lecture/{lecture['id']}/notes")
    r = client.post(f"/api/lecture/{lecture['id']}/notes?refresh=true")
    assert r.json()["cached"] is False


def test_generate_quiz(lecture):
    r = client.post(f"/api/lecture/{lecture['id']}/quiz", json={"num_questions": 1})
    assert r.status_code == 200
    quiz = r.json()["quiz"]
    assert len(quiz) == 1
    assert quiz[0]["answer_index"] == 0
    assert quiz[0]["options"] == ["Glucose", "Salt", "Iron", "Sand"]


def test_grade_quiz_without_quiz_400(lecture):
    r = client.post(f"/api/lecture/{lecture['id']}/quiz/grade", json={"answers": [0]})
    assert r.status_code == 400


def test_grade_quiz_persists_attempt(lecture):
    """Regression test for the fix: grading used to compute a score and throw it away."""
    client.post(f"/api/lecture/{lecture['id']}/quiz", json={"num_questions": 1})

    r = client.post(f"/api/lecture/{lecture['id']}/quiz/grade", json={"answers": [0]})
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 100.0
    assert body["correct"] == 1
    assert body["total"] == 1

    rec = client.get(f"/api/lecture/{lecture['id']}").json()
    assert len(rec["quiz_attempts"]) == 1
    assert rec["quiz_attempts"][0]["score"] == 100.0
    assert rec["quiz_attempts"][0]["answers"] == [0]
    assert "graded_at" in rec["quiz_attempts"][0]

    lib = client.get("/api/library").json()["lectures"]
    entry = next(l for l in lib if l["id"] == lecture["id"])
    assert entry["quiz_attempts"] == 1
    assert entry["best_score"] == 100.0


def test_grade_quiz_wrong_answer_scores_zero(lecture):
    client.post(f"/api/lecture/{lecture['id']}/quiz", json={"num_questions": 1})
    r = client.post(f"/api/lecture/{lecture['id']}/quiz/grade", json={"answers": [3]})
    assert r.json()["score"] == 0.0
    assert r.json()["breakdown"][0]["is_correct"] is False


def test_multiple_quiz_attempts_accumulate(lecture):
    client.post(f"/api/lecture/{lecture['id']}/quiz", json={"num_questions": 1})
    client.post(
        f"/api/lecture/{lecture['id']}/quiz/grade", json={"answers": [0]}
    )  # 100%
    client.post(f"/api/lecture/{lecture['id']}/quiz/grade", json={"answers": [1]})  # 0%

    rec = client.get(f"/api/lecture/{lecture['id']}").json()
    assert len(rec["quiz_attempts"]) == 2

    lib = client.get("/api/library").json()["lectures"]
    entry = next(l for l in lib if l["id"] == lecture["id"])
    assert entry["quiz_attempts"] == 2
    assert entry["best_score"] == 100.0  # best of [100, 0]


def test_generate_schedule(lecture):
    r = client.post(f"/api/lecture/{lecture['id']}/schedule", json={"days": 3})
    assert r.status_code == 200
    assert r.json()["schedule"]["plan"][0]["day"] == 1


def test_generate_evaluation(lecture):
    r = client.post(f"/api/lecture/{lecture['id']}/evaluate")
    assert r.status_code == 200
    assert r.json()["evaluation"]["main_topics"] == ["Photosynthesis"]


def test_chat(lecture):
    r = client.post(
        f"/api/lecture/{lecture['id']}/chat", json={"question": "What is it?"}
    )
    assert r.status_code == 200
    assert "fake LLM answer" in r.json()["answer"]
    assert "sources" in r.json()

    rec = client.get(f"/api/lecture/{lecture['id']}").json()
    assert len(rec["chat_history"]) == 1
    assert rec["chat_history"][0]["question"] == "What is it?"


def test_generators_404_on_missing_lecture():
    assert client.post("/api/lecture/nope/notes").status_code == 404
    assert client.post("/api/lecture/nope/quiz").status_code == 404
    assert client.post("/api/lecture/nope/evaluate").status_code == 404
    assert (
        client.post("/api/lecture/nope/chat", json={"question": "hi"}).status_code
        == 404
    )


# ----------------------------------------------------------------- LLM-not-configured path


def test_llm_not_configured_returns_503(lecture, monkeypatch):
    class NotConfiguredLLM:
        def is_configured(self):
            return False

    monkeypatch.setattr(study_api, "get_llm", lambda: NotConfiguredLLM())

    r = client.post(f"/api/lecture/{lecture['id']}/notes")
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]

    r2 = client.get("/api/llm-status")
    assert r2.json()["configured"] is False
    assert r2.json()["model"] is None
