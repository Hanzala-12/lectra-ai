"""
Study API tests — /api/library, /api/lecture CRUD, and the LLM-backed generators
(notes/quiz/schedule/evaluation/chat).

Isolation, the FakeLLM stand-in, and the `auth` fixture (a signed-up throwaway
student + auth headers) all come from conftest.py.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))  # tests/ itself, for `import conftest`

import lecture_repository
from conftest import client, AuthedStudent


def _lecture(auth: AuthedStudent):
    """A real lecture record, owned by the given authed student."""
    return lecture_repository.get_repository().create(
        title="Test Lecture",
        transcript_text=(
            "Photosynthesis converts light energy into chemical energy stored "
            "in glucose, using carbon dioxide and water as inputs."
        ),
        student_id=auth.student_id,
    )


# ----------------------------------------------------------------- library / CRUD


def test_llm_status_configured():
    """Not student-scoped — no auth needed."""
    r = client.get("/api/llm-status")
    assert r.status_code == 200
    assert r.json() == {"configured": True, "model": "fake-model"}


def test_library_requires_auth():
    r = client.get("/api/library")
    assert r.status_code == 401


def test_library_empty(auth):
    r = client.get("/api/library", headers=auth.headers)
    assert r.status_code == 200
    assert r.json() == {"lectures": []}


def test_create_and_get_lecture(auth):
    r = client.post(
        "/api/lecture",
        json={"title": "My Lecture", "transcript": "Some text."},
        headers=auth.headers,
    )
    assert r.status_code == 200
    lecture_id = r.json()["id"]

    r2 = client.get(f"/api/lecture/{lecture_id}", headers=auth.headers)
    assert r2.status_code == 200
    assert r2.json()["transcript_text"] == "Some text."
    assert r2.json()["quiz_attempts"] == []


def test_get_missing_lecture_404(auth):
    r = client.get("/api/lecture/does-not-exist", headers=auth.headers)
    assert r.status_code == 404


def test_cannot_see_another_students_lecture(auth):
    """The core multi-tenancy guarantee: a lecture that exists, but belongs to
    someone else, 404s exactly like a nonexistent one — no existence-leaking."""
    owner = auth
    lec = _lecture(owner)

    # a second, different student
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}

    assert (
        client.get(f"/api/lecture/{lec['id']}", headers=owner.headers).status_code
        == 200
    )
    assert (
        client.get(f"/api/lecture/{lec['id']}", headers=other_headers).status_code
        == 404
    )
    assert client.get("/api/library", headers=other_headers).json() == {"lectures": []}


def test_delete_lecture(auth):
    lec = _lecture(auth)
    r = client.delete(f"/api/lecture/{lec['id']}", headers=auth.headers)
    assert r.status_code == 200
    assert r.json()["deleted"] is True
    assert (
        client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).status_code == 404
    )


def test_delete_missing_lecture_404(auth):
    r = client.delete("/api/lecture/does-not-exist", headers=auth.headers)
    assert r.status_code == 404


def test_library_lists_created_lecture(auth):
    lec = _lecture(auth)
    r = client.get("/api/library", headers=auth.headers)
    ids = [l["id"] for l in r.json()["lectures"]]
    assert lec["id"] in ids


# ----------------------------------------------------------------- generators


def test_generate_notes(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)
    assert r.status_code == 200
    assert r.json()["cached"] is False
    assert "fake LLM answer" in r.json()["notes"]

    r2 = client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)
    assert r2.json()["cached"] is True


def test_generate_notes_refresh_bypasses_cache(auth):
    lec = _lecture(auth)
    client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)
    r = client.post(
        f"/api/lecture/{lec['id']}/notes?refresh=true", headers=auth.headers
    )
    assert r.json()["cached"] is False


def _correct_and_wrong_answer_ids(quiz_question):
    """Question/Answer are real entities now (own ids) — pull the actual
    generated answer_ids out of a quiz question instead of assuming index 0."""
    correct = next(a["answer_id"] for a in quiz_question["answers"] if a["is_correct"])
    wrong = next(
        a["answer_id"] for a in quiz_question["answers"] if not a["is_correct"]
    )
    return correct, wrong


def test_generate_quiz(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    )
    assert r.status_code == 200
    quiz = r.json()["quiz"]
    assert len(quiz) == 1
    assert quiz[0]["question_id"]
    answers = quiz[0]["answers"]
    assert [a["text"] for a in answers] == ["Glucose", "Salt", "Iron", "Sand"]
    assert sum(1 for a in answers if a["is_correct"]) == 1
    assert all(a["answer_id"] for a in answers)


def test_grade_quiz_without_quiz_400(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": ["whatever"]},
        headers=auth.headers,
    )
    assert r.status_code == 400


def test_grade_quiz_persists_attempt(auth):
    """Regression test for the fix: grading used to compute a score and throw it away."""
    lec = _lecture(auth)
    quiz = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()["quiz"]
    correct_id, _ = _correct_and_wrong_answer_ids(quiz[0])

    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [correct_id]},
        headers=auth.headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 100.0
    assert body["correct"] == 1
    assert body["total"] == 1
    assert body["breakdown"][0]["your_answer_id"] == correct_id
    assert body["breakdown"][0]["correct_answer_id"] == correct_id

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert len(rec["quiz_attempts"]) == 1
    assert rec["quiz_attempts"][0]["score"] == 100.0
    assert rec["quiz_attempts"][0]["answers"] == [correct_id]
    assert rec["quiz_attempts"][0]["student_id"] == auth.student_id
    assert "graded_at" in rec["quiz_attempts"][0]

    lib = client.get("/api/library", headers=auth.headers).json()["lectures"]
    entry = next(l for l in lib if l["id"] == lec["id"])
    assert entry["quiz_attempts"] == 1
    assert entry["best_score"] == 100.0


def test_grade_quiz_wrong_answer_scores_zero(auth):
    lec = _lecture(auth)
    quiz = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()["quiz"]
    _, wrong_id = _correct_and_wrong_answer_ids(quiz[0])
    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [wrong_id]},
        headers=auth.headers,
    )
    assert r.json()["score"] == 0.0
    assert r.json()["breakdown"][0]["is_correct"] is False


def test_grade_quiz_unanswered_question_scores_wrong(auth):
    """A null/missing answer_id must never accidentally match a correct one."""
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    )
    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [None]},
        headers=auth.headers,
    )
    assert r.json()["score"] == 0.0


def test_multiple_quiz_attempts_accumulate(auth):
    lec = _lecture(auth)
    quiz = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()["quiz"]
    correct_id, wrong_id = _correct_and_wrong_answer_ids(quiz[0])
    client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [correct_id]},
        headers=auth.headers,
    )  # 100%
    client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [wrong_id]},
        headers=auth.headers,
    )  # 0%

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert len(rec["quiz_attempts"]) == 2

    lib = client.get("/api/library", headers=auth.headers).json()["lectures"]
    entry = next(l for l in lib if l["id"] == lec["id"])
    assert entry["quiz_attempts"] == 2
    assert entry["best_score"] == 100.0  # best of [100, 0]


def test_generate_schedule(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/schedule", json={"days": 3}, headers=auth.headers
    )
    assert r.status_code == 200
    assert r.json()["schedule"]["plan"][0]["day"] == 1


def test_generate_evaluation(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/evaluate", headers=auth.headers)
    assert r.status_code == 200
    assert r.json()["evaluation"]["main_topics"] == ["Photosynthesis"]


def test_chat(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/chat",
        json={"question": "What is it?"},
        headers=auth.headers,
    )
    assert r.status_code == 200
    assert "fake LLM answer" in r.json()["answer"]
    assert "sources" in r.json()

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert len(rec["chat_history"]) == 1
    assert rec["chat_history"][0]["question"] == "What is it?"


def test_generators_404_on_missing_lecture(auth):
    assert (
        client.post("/api/lecture/nope/notes", headers=auth.headers).status_code == 404
    )
    assert (
        client.post("/api/lecture/nope/quiz", headers=auth.headers).status_code == 404
    )
    assert (
        client.post("/api/lecture/nope/evaluate", headers=auth.headers).status_code
        == 404
    )
    assert (
        client.post(
            "/api/lecture/nope/chat", json={"question": "hi"}, headers=auth.headers
        ).status_code
        == 404
    )


def test_generators_require_auth():
    assert client.post("/api/lecture/nope/notes").status_code == 401
    assert client.post("/api/lecture/nope/quiz").status_code == 401
    assert client.post("/api/lecture/nope/evaluate").status_code == 401
    assert (
        client.post("/api/lecture/nope/chat", json={"question": "hi"}).status_code
        == 401
    )


# ----------------------------------------------------------------- LLM-not-configured path


def test_llm_not_configured_returns_503(auth, monkeypatch):
    import study_api

    class NotConfiguredLLM:
        def is_configured(self):
            return False

    monkeypatch.setattr(study_api, "get_llm", lambda: NotConfiguredLLM())

    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)
    assert r.status_code == 503
    assert "OPENROUTER_API_KEY" in r.json()["detail"]

    r2 = client.get("/api/llm-status")
    assert r2.json()["configured"] is False
    assert r2.json()["model"] is None
