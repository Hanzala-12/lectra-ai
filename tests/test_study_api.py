"""
Study API tests — /api/library, /api/lecture CRUD, and the LLM-backed generators
(notes/quiz/schedule/evaluation/chat).

Isolation, the FakeLLM stand-in, and the `auth` fixture (a signed-up throwaway
student + auth headers) all come from conftest.py.
"""

import json
import os
import sys
from typing import List

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


def test_lecture_audio_files_defaults_empty(auth):
    """AudioFile is a real top-level entity now (audio_file_repository.py), no
    longer embedded on the Lecture record — a lecture with none yet still gets
    a predictable empty list back rather than a missing key."""
    lec = _lecture(auth)
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["audio_files"] == []


def test_lecture_merges_latest_audio_files(auth):
    import audio_file_repository

    lec = _lecture(auth)
    files = [
        {"audio_id": "a1", "kind": "cleaned", "file_path": "/x.wav", "duration": 12.0}
    ]
    audio_file_repository.get_repository().create(
        lecture_id=lec["id"], session_id="sess1", files=files
    )
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["audio_files"] == files


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


# ----------------------------------------------------------------- speaker renaming


def test_lecture_speaker_names_defaults_empty(auth):
    lec = _lecture(auth)
    r = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers)
    assert r.json()["speaker_names"] == {}


def test_rename_speakers_persists(auth):
    lec = _lecture(auth)
    r = client.put(
        f"/api/lecture/{lec['id']}/speakers",
        json={"names": {"SPEAKER_00": "Professor", "SPEAKER_01": "Student A"}},
        headers=auth.headers,
    )
    assert r.status_code == 200
    assert r.json()["speaker_names"] == {
        "SPEAKER_00": "Professor",
        "SPEAKER_01": "Student A",
    }

    # persisted — a fresh GET reflects it too
    r2 = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers)
    assert r2.json()["speaker_names"] == {
        "SPEAKER_00": "Professor",
        "SPEAKER_01": "Student A",
    }


def test_rename_speakers_drops_blank_entries(auth):
    """Whitespace-only names (e.g. a cleared input field) are dropped rather
    than persisted as a blank label."""
    lec = _lecture(auth)
    r = client.put(
        f"/api/lecture/{lec['id']}/speakers",
        json={"names": {"SPEAKER_00": "Professor", "SPEAKER_01": "   "}},
        headers=auth.headers,
    )
    assert r.json()["speaker_names"] == {"SPEAKER_00": "Professor"}


def test_rename_speakers_overwrites_previous_mapping(auth):
    """A second save fully replaces the map rather than merging — matches how
    the frontend always sends the complete current set of names."""
    lec = _lecture(auth)
    client.put(
        f"/api/lecture/{lec['id']}/speakers",
        json={"names": {"SPEAKER_00": "Professor"}},
        headers=auth.headers,
    )
    r = client.put(
        f"/api/lecture/{lec['id']}/speakers",
        json={"names": {"SPEAKER_00": "Dr. Smith"}},
        headers=auth.headers,
    )
    assert r.json()["speaker_names"] == {"SPEAKER_00": "Dr. Smith"}


def test_rename_speakers_404_for_missing_lecture(auth):
    r = client.put(
        "/api/lecture/does-not-exist/speakers",
        json={"names": {"SPEAKER_00": "Professor"}},
        headers=auth.headers,
    )
    assert r.status_code == 404


def test_rename_speakers_404_for_another_students_lecture(auth):
    lec = _lecture(auth)
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}

    r2 = client.put(
        f"/api/lecture/{lec['id']}/speakers",
        json={"names": {"SPEAKER_00": "Professor"}},
        headers=other_headers,
    )
    assert r2.status_code == 404


# ----------------------------------------------------------------- reference notes


def test_lecture_reference_notes_defaults_empty(auth):
    lec = _lecture(auth)
    r = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers)
    assert r.json()["reference_notes"] == []


def test_add_reference_note(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Remember: chlorophyll absorbs red and blue light."},
        headers=auth.headers,
    )
    assert r.status_code == 200
    notes = r.json()["reference_notes"]
    assert len(notes) == 1
    assert notes[0]["text"] == "Remember: chlorophyll absorbs red and blue light."
    assert notes[0]["id"]
    assert notes[0]["created_at"]

    # persisted
    r2 = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers)
    assert len(r2.json()["reference_notes"]) == 1


def test_add_reference_note_rejects_blank(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "   "},
        headers=auth.headers,
    )
    assert r.status_code == 400


def test_add_reference_note_rejects_too_long(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "x" * 4001},
        headers=auth.headers,
    )
    assert r.status_code == 400


def test_add_reference_note_appends_not_overwrites(auth):
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "First note"},
        headers=auth.headers,
    )
    r = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Second note"},
        headers=auth.headers,
    )
    texts = [n["text"] for n in r.json()["reference_notes"]]
    assert texts == ["First note", "Second note"]


def test_delete_reference_note(auth):
    lec = _lecture(auth)
    add = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Delete me"},
        headers=auth.headers,
    )
    note_id = add.json()["reference_notes"][0]["id"]

    r = client.delete(
        f"/api/lecture/{lec['id']}/reference-notes/{note_id}", headers=auth.headers
    )
    assert r.status_code == 200
    assert r.json()["reference_notes"] == []


def test_delete_reference_note_leaves_others(auth):
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Keep me"},
        headers=auth.headers,
    )
    add2 = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Remove me"},
        headers=auth.headers,
    )
    note_id = add2.json()["reference_notes"][1]["id"]

    r = client.delete(
        f"/api/lecture/{lec['id']}/reference-notes/{note_id}", headers=auth.headers
    )
    remaining = [n["text"] for n in r.json()["reference_notes"]]
    assert remaining == ["Keep me"]


def test_reference_notes_404_for_another_students_lecture(auth):
    lec = _lecture(auth)
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}

    r2 = client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={"text": "Sneaky note"},
        headers=other_headers,
    )
    assert r2.status_code == 404


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


def test_quiz_id_stable_until_refresh(auth):
    """Quiz is a real, versioned top-level entity now (quiz_repository.py) — the
    same quiz_id comes back from a cached (non-refresh) call, and a NEW quiz_id
    is minted only when explicitly refreshed."""
    lec = _lecture(auth)
    first = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()
    again = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()
    assert first["quiz_id"] == again["quiz_id"]
    assert again["cached"] is True

    refreshed = client.post(
        f"/api/lecture/{lec['id']}/quiz?refresh=true",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()
    assert refreshed["quiz_id"] != first["quiz_id"]
    assert refreshed["cached"] is False

    # GET lecture merges in the latest (refreshed) quiz version
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["quiz_id"] == refreshed["quiz_id"]


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
    # QuizResult now has its own dedicated result_id (previously only
    # score/answers/timestamp were kept).
    assert body["result_id"]

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert len(rec["quiz_attempts"]) == 1
    attempt = rec["quiz_attempts"][0]
    assert attempt["score"] == 100.0
    assert attempt["answers"] == [correct_id]
    assert attempt["student_id"] == auth.student_id
    assert "graded_at" in attempt
    assert attempt["result_id"] == body["result_id"]
    assert attempt["quiz_id"] == rec["quiz_id"]
    # per-question feedback (the "why") is now persisted, not just computed
    # and thrown away on every request.
    assert attempt["feedback"] == body["breakdown"]
    assert attempt["feedback"][0]["correct_answer_id"] == correct_id

    lib = client.get("/api/library", headers=auth.headers).json()["lectures"]
    entry = next(l for l in lib if l["id"] == lec["id"])
    assert entry["quiz_attempts"] == 1
    assert entry["best_score"] == 100.0


def test_grade_against_specific_older_quiz_version(auth):
    """Grading always defaults to the latest quiz, but an explicit quiz_id lets a
    student grade against the exact version they actually attempted, even after
    a newer one has been generated."""
    lec = _lecture(auth)
    v1 = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()
    v1_correct, _ = _correct_and_wrong_answer_ids(v1["quiz"][0])

    v2 = client.post(
        f"/api/lecture/{lec['id']}/quiz?refresh=true",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()
    assert v2["quiz_id"] != v1["quiz_id"]

    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [v1_correct], "quiz_id": v1["quiz_id"]},
        headers=auth.headers,
    )
    assert r.status_code == 200
    assert r.json()["score"] == 100.0

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["quiz_attempts"][-1]["quiz_id"] == v1["quiz_id"]


def test_grade_against_unknown_quiz_id_404(auth):
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    )
    r = client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": ["x"], "quiz_id": "does-not-exist"},
        headers=auth.headers,
    )
    assert r.status_code == 404


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


def test_generate_schedule_stores_available_time_and_goals(auth):
    """StudyPlan.available_time / StudyPlan.learning_goals — real inputs, persisted
    on the normalized top-level StudyPlan record (study_plan_repository.py)."""
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/schedule",
        json={
            "days": 3,
            "available_time": "1 hour/day",
            "learning_goals": "ace the exam",
        },
        headers=auth.headers,
    )
    assert r.status_code == 200
    schedule = r.json()["schedule"]
    assert schedule["available_time"] == "1 hour/day"
    assert schedule["learning_goals"] == "ace the exam"
    assert schedule["id"]


def test_regenerate_schedule_creates_new_plan_version(auth):
    """StudyPlan is a real, versioned top-level entity now — refreshing creates a
    new record instead of overwriting the previous one."""
    lec = _lecture(auth)
    first = client.post(
        f"/api/lecture/{lec['id']}/schedule", json={"days": 3}, headers=auth.headers
    ).json()["schedule"]
    second = client.post(
        f"/api/lecture/{lec['id']}/schedule?refresh=true",
        json={"days": 5},
        headers=auth.headers,
    ).json()["schedule"]
    assert first["id"] != second["id"]

    # GET lecture merges in the latest (second) plan
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["schedule"]["id"] == second["id"]


def test_lecture_review_state_defaults_empty(auth):
    lec = _lecture(auth)
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["review_state"]["attempts_considered"] == 0
    assert rec["review_state"]["next_review_at"] is None


def test_lecture_review_state_after_quiz_attempt(auth):
    """The real SM-2 state (spaced_repetition.py), computed from an actual
    graded quiz attempt — not the LLM-improvised schedule."""
    lec = _lecture(auth)
    quiz = client.post(
        f"/api/lecture/{lec['id']}/quiz",
        json={"num_questions": 1},
        headers=auth.headers,
    ).json()["quiz"]
    correct_id, _ = _correct_and_wrong_answer_ids(quiz[0])
    client.post(
        f"/api/lecture/{lec['id']}/quiz/grade",
        json={"answers": [correct_id]},
        headers=auth.headers,
    )

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    state = rec["review_state"]
    assert state["attempts_considered"] == 1
    assert state["repetition_count"] == 1
    assert state["interval_days"] == 1
    assert state["next_review_at"] is not None


def test_review_schedule_endpoint(auth):
    """Standalone endpoint — same computation, no LLM call, no side effects."""
    lec = _lecture(auth)
    r = client.get(f"/api/lecture/{lec['id']}/review-schedule", headers=auth.headers)
    assert r.status_code == 200
    assert r.json()["attempts_considered"] == 0


def test_review_schedule_endpoint_404_for_missing_lecture(auth):
    r = client.get("/api/lecture/does-not-exist/review-schedule", headers=auth.headers)
    assert r.status_code == 404


def test_review_schedule_endpoint_404_for_another_students_lecture(auth):
    lec = _lecture(auth)
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r2 = client.get(f"/api/lecture/{lec['id']}/review-schedule", headers=other_headers)
    assert r2.status_code == 404


def test_schedule_response_includes_review_state(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/schedule", json={"days": 3}, headers=auth.headers
    )
    assert "review_state" in r.json()
    assert r.json()["review_state"]["attempts_considered"] == 0


def test_schedule_response_includes_review_state_when_cached(auth):
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/schedule", json={"days": 3}, headers=auth.headers
    )
    r = client.post(
        f"/api/lecture/{lec['id']}/schedule", json={"days": 3}, headers=auth.headers
    )
    assert r.json()["cached"] is True
    assert "review_state" in r.json()


def test_generate_evaluation(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/evaluate", headers=auth.headers)
    assert r.status_code == 200
    assert r.json()["evaluation"]["main_topics"] == ["Photosynthesis"]


# ----------------------------------------------------------------- audio recap


def test_generate_recap(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/recap", headers=auth.headers)
    assert r.status_code == 200
    body = r.json()
    assert "fake LLM answer" in body["script"]
    assert body["audio_url"] == f"/api/download/recap_{lec['id']}.wav"
    assert body["cached"] is False

    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["recap_script"] == body["script"]
    assert rec["recap_audio_url"] == body["audio_url"]


def test_recap_defaults_to_none(auth):
    lec = _lecture(auth)
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert rec["recap_script"] is None
    assert rec["recap_audio_url"] is None


def test_recap_is_cached(auth):
    lec = _lecture(auth)
    client.post(f"/api/lecture/{lec['id']}/recap", headers=auth.headers)
    r = client.post(f"/api/lecture/{lec['id']}/recap", headers=auth.headers)
    assert r.json()["cached"] is True


def test_recap_refresh_regenerates_both_script_and_audio(auth):
    lec = _lecture(auth)
    first = client.post(f"/api/lecture/{lec['id']}/recap", headers=auth.headers).json()
    second = client.post(
        f"/api/lecture/{lec['id']}/recap?refresh=true", headers=auth.headers
    ).json()
    assert second["cached"] is False
    # same script content (FakeLLM is deterministic) but genuinely regenerated
    assert second["script"] == first["script"]


def test_recap_503_when_tts_unavailable(auth, monkeypatch):
    import tts_engine

    monkeypatch.setattr(tts_engine, "is_available", lambda: False)
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/recap", headers=auth.headers)
    assert r.status_code == 503
    assert "piper" in r.json()["detail"].lower()


def test_recap_404_for_missing_lecture(auth):
    r = client.post("/api/lecture/does-not-exist/recap", headers=auth.headers)
    assert r.status_code == 404


def test_recap_404_for_another_students_lecture(auth):
    lec = _lecture(auth)
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r2 = client.post(f"/api/lecture/{lec['id']}/recap", headers=other_headers)
    assert r2.status_code == 404


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


def test_chat_retrieval_includes_reference_notes(auth):
    """A reference note the student added is retrievable by the chatbot
    alongside the transcript, tagged so it's distinguishable from transcript
    prose in the prompt the LLM actually sees. Uses a nonsense term that
    can't appear in the (photosynthesis) transcript, so a match in the
    returned sources can only have come from the note."""
    lec = _lecture(auth)
    client.post(
        f"/api/lecture/{lec['id']}/reference-notes",
        json={
            "text": "Zorblatt constant equals forty-two in this course's convention."
        },
        headers=auth.headers,
    )

    r = client.post(
        f"/api/lecture/{lec['id']}/chat",
        json={"question": "What is the Zorblatt constant?", "top_k": 4},
        headers=auth.headers,
    )
    assert r.status_code == 200
    sources_text = " ".join(s["text"] for s in r.json()["sources"])
    assert "Zorblatt constant equals forty-two" in sources_text
    assert "[Student's own reference note]" in sources_text


def _parse_sse(text: str) -> List[dict]:
    """Parse a `data: {...}\\n\\n`-formatted SSE body into a list of events."""
    events = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("data: "):
            events.append(json.loads(line[len("data: ") :]))
    return events


def test_chat_stream(auth):
    lec = _lecture(auth)
    r = client.post(
        f"/api/lecture/{lec['id']}/chat/stream",
        json={"question": "What is it?"},
        headers=auth.headers,
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")

    events = _parse_sse(r.text)
    deltas = [e["delta"] for e in events if "delta" in e]
    final = [e for e in events if e.get("done")]

    # Delivered as more than one chunk (FakeLLM.chat_stream yields word-by-
    # word) — the actual point of streaming, not just a differently-shaped
    # single blob.
    assert len(deltas) > 1
    assert "fake LLM answer" in "".join(deltas)
    assert len(final) == 1
    assert "sources" in final[0]

    # Persisted exactly like the non-streaming endpoint
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert len(rec["chat_history"]) == 1
    assert rec["chat_history"][0]["question"] == "What is it?"
    assert "fake LLM answer" in rec["chat_history"][0]["answer"]


def test_chat_stream_requires_auth(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/chat/stream", json={"question": "hi"})
    assert r.status_code == 401


def test_chat_stream_404_for_another_students_lecture(auth):
    lec = _lecture(auth)
    r = client.post(
        "/api/auth/signup",
        json={"username": f"other_{lec['id']}", "password": "testpass123"},
    )
    other_headers = {"Authorization": f"Bearer {r.json()['token']}"}
    r2 = client.post(
        f"/api/lecture/{lec['id']}/chat/stream",
        json={"question": "hi"},
        headers=other_headers,
    )
    assert r2.status_code == 404


def test_generate_notes_stream(auth):
    lec = _lecture(auth)
    r = client.post(f"/api/lecture/{lec['id']}/notes/stream", headers=auth.headers)
    assert r.status_code == 200

    events = _parse_sse(r.text)
    deltas = [e["delta"] for e in events if "delta" in e]
    final = [e for e in events if e.get("done")]

    assert len(deltas) > 1
    assert "fake LLM answer" in "".join(deltas)
    assert final == [{"done": True, "cached": False}]

    # Persisted, same field the non-streaming route writes to
    rec = client.get(f"/api/lecture/{lec['id']}", headers=auth.headers).json()
    assert "fake LLM answer" in rec["notes"]


def test_generate_notes_stream_serves_cache_as_single_chunk(auth):
    lec = _lecture(auth)
    # Prime the cache via the non-streaming route first
    client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)

    r = client.post(f"/api/lecture/{lec['id']}/notes/stream", headers=auth.headers)
    events = _parse_sse(r.text)
    deltas = [e["delta"] for e in events if "delta" in e]
    final = [e for e in events if e.get("done")]

    assert len(deltas) == 1  # cached notes come back as one chunk, not re-split
    assert "fake LLM answer" in deltas[0]
    assert final == [{"done": True, "cached": True}]


def test_generate_notes_stream_refresh_bypasses_cache(auth):
    lec = _lecture(auth)
    client.post(f"/api/lecture/{lec['id']}/notes", headers=auth.headers)

    r = client.post(
        f"/api/lecture/{lec['id']}/notes/stream?refresh=true", headers=auth.headers
    )
    events = _parse_sse(r.text)
    final = [e for e in events if e.get("done")]
    assert final == [{"done": True, "cached": False}]


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
