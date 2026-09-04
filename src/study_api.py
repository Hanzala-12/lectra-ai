"""
Study API — FastAPI router for the LLM/RAG half of the system.

Exposes the lecture repository, Notes/Quiz/Schedule/Evaluation generators, and a
RAG-grounded chatbot. Included into backend.py with two lines:

    from study_api import router as study_router
    app.include_router(study_router)

Every LLM-backed route degrades gracefully: if OPENROUTER_API_KEY is not set it
returns HTTP 503 with a clear message instead of crashing.

All /lecture* routes require a logged-in student (see auth_api.py) and are
scoped to that student's own lectures — a lecture belonging to another student
(or a legacy record created before auth existed) 404s exactly like a
nonexistent one, rather than leaking whether it exists.

Quiz and StudyPlan are real, independently-addressable, versioned top-level
entities (quiz_repository.py / study_plan_repository.py) — regenerating either
creates a new record instead of overwriting the previous one. get_lecture()
and library() merge the latest of each back into the response so the API
shape callers already rely on (lecture.quiz / lecture.schedule) is unchanged;
storage underneath is what changed.
"""

import json
import logging
import time
import uuid
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from llm_client import get_llm, LLMNotConfigured
from lecture_repository import get_repository
from rag_engine import RagEngine, build_context
from auth_api import get_current_student
import quiz_repository
import study_plan_repository
import audio_file_repository
import study_tools
import spaced_repetition

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["study"])


# ----------------------------------------------------------------- models
class CreateLecture(BaseModel):
    title: str
    transcript: str
    transcript_segments: Optional[List[dict]] = None


class QuizRequest(BaseModel):
    num_questions: int = 5


class ScheduleRequest(BaseModel):
    days: int = 7
    available_time: Optional[str] = None  # StudyPlan.available_time — e.g. "1 hour/day"
    learning_goals: Optional[str] = None  # StudyPlan.learning_goals — free text


class GradeRequest(BaseModel):
    answers: List[Optional[str]]  # submitted answer_id per question, by position
    quiz_id: Optional[str] = (
        None  # which quiz version to grade against; defaults to latest
    )


class ChatRequest(BaseModel):
    question: str
    top_k: int = 4


class RenameSpeakersRequest(BaseModel):
    names: dict  # raw diarization label -> chosen display name, e.g. {"SPEAKER_00": "Professor"}


# ----------------------------------------------------------------- helpers
def _lecture_or_404(lecture_id: str, student_id: str):
    """Fetch a lecture, scoped to its owner. A lecture that exists but belongs
    to someone else 404s the same as one that doesn't exist at all — no
    existence-leaking via a 403."""
    rec = get_repository().get(lecture_id)
    if rec is None or rec.get("student_id") != student_id:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return rec


def _require_llm():
    llm = get_llm()
    if not llm.is_configured():
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Add OPENROUTER_API_KEY to your .env to enable "
            "notes, quiz, schedule, evaluation, and chat.",
        )
    return llm


def _run_llm(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except LLMNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise HTTPException(status_code=502, detail=f"LLM generation failed: {e}")


def _enrich_lecture(rec: dict) -> dict:
    """Merge the latest normalized Quiz/StudyPlan/AudioFile records into a
    lecture dict for API responses, falling back to whatever's embedded on
    the lecture record itself (legacy records created before this
    normalization). Never mutates the stored record."""
    rec = dict(rec)
    lecture_id = rec["id"]

    latest_quiz = quiz_repository.get_repository().get_latest_for_lecture(lecture_id)
    if latest_quiz:
        rec["quiz"] = latest_quiz["questions"]
        rec["quiz_id"] = latest_quiz["id"]
    else:
        rec.setdefault("quiz_id", None)

    latest_plan = study_plan_repository.get_repository().get_latest_for_lecture(
        lecture_id
    )
    if latest_plan:
        rec["schedule"] = latest_plan

    audio_rec = audio_file_repository.get_repository().get_for_lecture(lecture_id)
    if audio_rec:
        rec["audio_files"] = audio_rec["files"]
    else:
        rec.setdefault("audio_files", [])

    rec.setdefault("speaker_names", {})  # records created before this field existed

    # Real SM-2 state computed fresh from actual quiz history every time —
    # never persisted, so it's always in sync with the latest attempt (see
    # spaced_repetition.py for why recomputing is correct and cheap).
    rec["review_state"] = spaced_repetition.compute_review_state(
        rec.get("quiz_attempts") or []
    )

    return rec


# ----------------------------------------------------------------- status
@router.get("/llm-status")
async def llm_status():
    """Not student-scoped — this is system-wide config info, not lecture data."""
    llm = get_llm()
    return {
        "configured": llm.is_configured(),
        "model": llm.model if llm.is_configured() else None,
    }


# ----------------------------------------------------------------- library / CRUD
@router.get("/library")
async def library(student_id: str = Depends(get_current_student)):
    lectures = get_repository().list(student_id=student_id)
    for entry in lectures:
        has_quiz = quiz_repository.get_repository().get_latest_for_lecture(entry["id"])
        has_plan = study_plan_repository.get_repository().get_latest_for_lecture(
            entry["id"]
        )
        # `or` keeps legacy records (created before this normalization, whose
        # has_quiz/has_schedule already came from the embedded field) working.
        entry["has_quiz"] = bool(has_quiz) or entry.get("has_quiz", False)
        entry["has_schedule"] = bool(has_plan) or entry.get("has_schedule", False)
    return {"lectures": lectures}


@router.post("/lecture")
async def create_lecture(
    body: CreateLecture, student_id: str = Depends(get_current_student)
):
    """Create a lecture from raw transcript text (e.g. for testing without audio)."""
    rec = get_repository().create(
        title=body.title,
        transcript_text=body.transcript,
        transcript_segments=body.transcript_segments or [],
        student_id=student_id,
    )
    return {"id": rec["id"], "title": rec["title"]}


@router.get("/lecture/{lecture_id}")
async def get_lecture(lecture_id: str, student_id: str = Depends(get_current_student)):
    return _enrich_lecture(_lecture_or_404(lecture_id, student_id))


@router.put("/lecture/{lecture_id}/speakers")
async def rename_speakers(
    lecture_id: str,
    body: RenameSpeakersRequest,
    student_id: str = Depends(get_current_student),
):
    """Save student-chosen display names for diarization labels (SPEAKER_00
    -> "Professor"). Presentation-only — see the comment on
    Lecture.speaker_names in lecture_repository.py."""
    _lecture_or_404(lecture_id, student_id)
    clean = {
        str(label).strip(): str(name).strip()
        for label, name in (body.names or {}).items()
        if str(label).strip() and str(name).strip()
    }
    rec = get_repository().update(lecture_id, speaker_names=clean)
    return {"speaker_names": rec.get("speaker_names", {})}


@router.delete("/lecture/{lecture_id}")
async def delete_lecture(
    lecture_id: str, student_id: str = Depends(get_current_student)
):
    _lecture_or_404(lecture_id, student_id)  # 404 if missing OR not yours
    ok = get_repository().delete(lecture_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return {"deleted": True}


# ----------------------------------------------------------------- generators
@router.post("/lecture/{lecture_id}/notes")
async def make_notes(
    lecture_id: str,
    refresh: bool = False,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)
    if rec.get("notes") and not refresh:
        return {"notes": rec["notes"], "cached": True}
    llm = _require_llm()
    notes = _run_llm(study_tools.generate_notes, rec["transcript_text"], llm)
    get_repository().update(lecture_id, notes=notes)
    return {"notes": notes, "cached": False}


@router.post("/lecture/{lecture_id}/notes/stream")
async def make_notes_stream(
    lecture_id: str,
    refresh: bool = False,
    student_id: str = Depends(get_current_student),
):
    """Same behavior and caching as POST .../notes, but a freshly-generated
    set of notes arrives incrementally. An already-cached set (refresh=false,
    notes exist) streams back as a single immediate chunk, so the client's
    handling code doesn't need two separate code paths for cached vs. fresh."""
    rec = _lecture_or_404(lecture_id, student_id)

    if rec.get("notes") and not refresh:
        cached = rec["notes"]

        def cached_stream():
            yield _sse({"delta": cached})
            yield _sse({"done": True, "cached": True})

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    llm = _require_llm()

    def event_stream():
        chunks: List[str] = []
        try:
            for delta in study_tools.generate_notes_stream(rec["transcript_text"], llm):
                chunks.append(delta)
                yield _sse({"delta": delta})
        except Exception as e:
            logger.error(f"Notes stream failed: {e}")
            yield _sse({"error": str(e)})
            return
        notes = "".join(chunks)
        get_repository().update(lecture_id, notes=notes)
        yield _sse({"done": True, "cached": False})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/lecture/{lecture_id}/quiz")
async def make_quiz(
    lecture_id: str,
    body: QuizRequest = QuizRequest(),
    refresh: bool = False,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)
    existing = quiz_repository.get_repository().get_latest_for_lecture(lecture_id)
    if existing and not refresh:
        return {
            "quiz": existing["questions"],
            "quiz_id": existing["id"],
            "cached": True,
        }
    llm = _require_llm()
    questions = _run_llm(
        study_tools.generate_quiz, rec["transcript_text"], llm, body.num_questions
    )
    new_quiz = quiz_repository.get_repository().create(
        lecture_id, student_id, questions
    )
    return {"quiz": new_quiz["questions"], "quiz_id": new_quiz["id"], "cached": False}


@router.post("/lecture/{lecture_id}/quiz/grade")
async def grade(
    lecture_id: str,
    body: GradeRequest,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)

    if body.quiz_id:
        quiz_rec = quiz_repository.get_repository().get(body.quiz_id)
        if quiz_rec is None or quiz_rec.get("lecture_id") != lecture_id:
            raise HTTPException(status_code=404, detail="Quiz not found")
    else:
        quiz_rec = quiz_repository.get_repository().get_latest_for_lecture(lecture_id)

    if quiz_rec is None:
        raise HTTPException(
            status_code=400, detail="No quiz generated for this lecture yet"
        )

    result = study_tools.grade_quiz(quiz_rec["questions"], body.answers)

    # QuizResult: a real result_id, a reference to exactly which quiz version
    # was attempted, and the per-question feedback persisted (previously only
    # score/answers/timestamp were kept — the "why" was computed and thrown
    # away on every request).
    result_id = uuid.uuid4().hex[:12]
    attempts = list(rec.get("quiz_attempts") or [])
    attempts.append(
        {
            "result_id": result_id,
            "quiz_id": quiz_rec["id"],
            "student_id": student_id,
            "graded_at": time.time(),
            "answers": body.answers,
            "score": result["score"],
            "correct": result["correct"],
            "total": result["total"],
            "feedback": result["breakdown"],
        }
    )
    get_repository().update(lecture_id, quiz_attempts=attempts[-20:])

    result["result_id"] = result_id
    return result


@router.get("/lecture/{lecture_id}/review-schedule")
async def review_schedule(
    lecture_id: str, student_id: str = Depends(get_current_student)
):
    """The real SM-2 spaced-repetition state on its own, with no LLM call and
    no side effects — for surfaces that just want "when is this due" (e.g. a
    library/dashboard badge) without generating or touching a study plan."""
    rec = _lecture_or_404(lecture_id, student_id)
    return spaced_repetition.compute_review_state(rec.get("quiz_attempts") or [])


@router.post("/lecture/{lecture_id}/schedule")
async def make_schedule(
    lecture_id: str,
    body: ScheduleRequest = ScheduleRequest(),
    refresh: bool = False,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)
    # Recomputed every call (not persisted on the plan) so it's never stale —
    # see spaced_repetition.py.
    review_state = spaced_repetition.compute_review_state(
        rec.get("quiz_attempts") or []
    )
    existing = study_plan_repository.get_repository().get_latest_for_lecture(lecture_id)
    if existing and not refresh:
        return {"schedule": existing, "review_state": review_state, "cached": True}
    llm = _require_llm()
    generated = _run_llm(
        study_tools.generate_schedule,
        rec["transcript_text"],
        llm,
        body.days,
        body.available_time,
        body.learning_goals,
        review_state,
    )
    new_plan = study_plan_repository.get_repository().create(
        lecture_id=lecture_id,
        student_id=student_id,
        plan=generated.get("plan", []),
        tips=generated.get("tips", []),
        available_time=body.available_time,
        learning_goals=body.learning_goals,
    )
    return {"schedule": new_plan, "review_state": review_state, "cached": False}


@router.post("/lecture/{lecture_id}/evaluate")
async def evaluate(
    lecture_id: str,
    refresh: bool = False,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)
    if rec.get("evaluation") and not refresh:
        return {"evaluation": rec["evaluation"], "cached": True}
    llm = _require_llm()
    evaluation = _run_llm(study_tools.evaluate_lecture, rec["transcript_text"], llm)
    get_repository().update(lecture_id, evaluation=evaluation)
    return {"evaluation": evaluation, "cached": False}


# ----------------------------------------------------------------- RAG chat
def _chat_messages_and_sources(rec: dict, question: str, top_k: int):
    """Shared between the blocking and streaming chat routes so the two
    prompts can't drift apart."""
    engine = RagEngine.from_transcript(rec["transcript_text"])
    passages = engine.retrieve(question, k=top_k)
    context = build_context(passages)
    system = (
        "You are a helpful study assistant answering questions about a specific "
        "lecture. Answer ONLY using the provided context passages. If the answer "
        "is not in the context, say you couldn't find it in this lecture."
    )
    prompt = f"Context from the lecture:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]
    sources = [
        {"text": p["text"][:300], "score": round(p["score"], 3)} for p in passages
    ]
    return messages, sources


@router.post("/lecture/{lecture_id}/chat")
async def chat(
    lecture_id: str,
    body: ChatRequest,
    student_id: str = Depends(get_current_student),
):
    rec = _lecture_or_404(lecture_id, student_id)
    llm = _require_llm()

    messages, sources = _chat_messages_and_sources(rec, body.question, body.top_k)
    answer = _run_llm(llm.chat, messages, max_tokens=800, temperature=0.3)

    # persist a short chat history
    history = rec.get("chat_history", [])
    history.append({"question": body.question, "answer": answer})
    get_repository().update(lecture_id, chat_history=history[-50:])

    return {"answer": answer, "sources": sources}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event)}\n\n"


@router.post("/lecture/{lecture_id}/chat/stream")
async def chat_stream(
    lecture_id: str,
    body: ChatRequest,
    student_id: str = Depends(get_current_student),
):
    """Same behavior and persistence as POST .../chat, but the answer arrives
    as it's generated instead of all at once. Auth, ownership, and RAG
    retrieval all happen before the stream opens — only token generation
    itself is streamed."""
    rec = _lecture_or_404(lecture_id, student_id)
    llm = _require_llm()
    messages, sources = _chat_messages_and_sources(rec, body.question, body.top_k)

    def event_stream():
        chunks: List[str] = []
        try:
            for delta in llm.chat_stream(messages, max_tokens=800, temperature=0.3):
                chunks.append(delta)
                yield _sse({"delta": delta})
        except Exception as e:
            logger.error(f"Chat stream failed: {e}")
            yield _sse({"error": str(e)})
            return
        answer = "".join(chunks)
        history = rec.get("chat_history", [])
        history.append({"question": body.question, "answer": answer})
        get_repository().update(lecture_id, chat_history=history[-50:])
        yield _sse({"done": True, "sources": sources})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
