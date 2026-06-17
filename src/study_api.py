"""
Study API — FastAPI router for the LLM/RAG half of the system.

Exposes the lecture repository, Notes/Quiz/Schedule/Evaluation generators, and a
RAG-grounded chatbot. Included into backend.py with two lines:

    from study_api import router as study_router
    app.include_router(study_router)

Every LLM-backed route degrades gracefully: if OPENROUTER_API_KEY is not set it
returns HTTP 503 with a clear message instead of crashing.
"""

import logging
from typing import List, Optional, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from llm_client import get_llm, LLMNotConfigured
from lecture_repository import get_repository
from rag_engine import RagEngine, build_context
import study_tools

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


class GradeRequest(BaseModel):
    answers: List[int]


class ChatRequest(BaseModel):
    question: str
    top_k: int = 4


# ----------------------------------------------------------------- helpers
def _lecture_or_404(lecture_id: str):
    rec = get_repository().get(lecture_id)
    if rec is None:
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


# ----------------------------------------------------------------- status
@router.get("/llm-status")
async def llm_status():
    llm = get_llm()
    return {
        "configured": llm.is_configured(),
        "model": llm.model if llm.is_configured() else None,
    }


# ----------------------------------------------------------------- library / CRUD
@router.get("/library")
async def library():
    return {"lectures": get_repository().list()}


@router.post("/lecture")
async def create_lecture(body: CreateLecture):
    """Create a lecture from raw transcript text (e.g. for testing without audio)."""
    rec = get_repository().create(
        title=body.title,
        transcript_text=body.transcript,
        transcript_segments=body.transcript_segments or [],
    )
    return {"id": rec["id"], "title": rec["title"]}


@router.get("/lecture/{lecture_id}")
async def get_lecture(lecture_id: str):
    return _lecture_or_404(lecture_id)


@router.delete("/lecture/{lecture_id}")
async def delete_lecture(lecture_id: str):
    ok = get_repository().delete(lecture_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return {"deleted": True}


# ----------------------------------------------------------------- generators
@router.post("/lecture/{lecture_id}/notes")
async def make_notes(lecture_id: str, refresh: bool = False):
    rec = _lecture_or_404(lecture_id)
    if rec.get("notes") and not refresh:
        return {"notes": rec["notes"], "cached": True}
    llm = _require_llm()
    notes = _run_llm(study_tools.generate_notes, rec["transcript_text"], llm)
    get_repository().update(lecture_id, notes=notes)
    return {"notes": notes, "cached": False}


@router.post("/lecture/{lecture_id}/quiz")
async def make_quiz(
    lecture_id: str, body: QuizRequest = QuizRequest(), refresh: bool = False
):
    rec = _lecture_or_404(lecture_id)
    if rec.get("quiz") and not refresh:
        return {"quiz": rec["quiz"], "cached": True}
    llm = _require_llm()
    quiz = _run_llm(
        study_tools.generate_quiz, rec["transcript_text"], llm, body.num_questions
    )
    get_repository().update(lecture_id, quiz=quiz)
    return {"quiz": quiz, "cached": False}


@router.post("/lecture/{lecture_id}/quiz/grade")
async def grade(lecture_id: str, body: GradeRequest):
    rec = _lecture_or_404(lecture_id)
    if not rec.get("quiz"):
        raise HTTPException(
            status_code=400, detail="No quiz generated for this lecture yet"
        )
    return study_tools.grade_quiz(rec["quiz"], body.answers)


@router.post("/lecture/{lecture_id}/schedule")
async def make_schedule(
    lecture_id: str, body: ScheduleRequest = ScheduleRequest(), refresh: bool = False
):
    rec = _lecture_or_404(lecture_id)
    if rec.get("schedule") and not refresh:
        return {"schedule": rec["schedule"], "cached": True}
    llm = _require_llm()
    schedule = _run_llm(
        study_tools.generate_schedule, rec["transcript_text"], llm, body.days
    )
    get_repository().update(lecture_id, schedule=schedule)
    return {"schedule": schedule, "cached": False}


@router.post("/lecture/{lecture_id}/evaluate")
async def evaluate(lecture_id: str, refresh: bool = False):
    rec = _lecture_or_404(lecture_id)
    if rec.get("evaluation") and not refresh:
        return {"evaluation": rec["evaluation"], "cached": True}
    llm = _require_llm()
    evaluation = _run_llm(study_tools.evaluate_lecture, rec["transcript_text"], llm)
    get_repository().update(lecture_id, evaluation=evaluation)
    return {"evaluation": evaluation, "cached": False}


# ----------------------------------------------------------------- RAG chat
@router.post("/lecture/{lecture_id}/chat")
async def chat(lecture_id: str, body: ChatRequest):
    rec = _lecture_or_404(lecture_id)
    llm = _require_llm()

    engine = RagEngine.from_transcript(rec["transcript_text"])
    passages = engine.retrieve(body.question, k=body.top_k)
    context = build_context(passages)

    system = (
        "You are a helpful study assistant answering questions about a specific "
        "lecture. Answer ONLY using the provided context passages. If the answer "
        "is not in the context, say you couldn't find it in this lecture."
    )
    prompt = (
        f"Context from the lecture:\n{context}\n\n"
        f"Question: {body.question}\n\nAnswer:"
    )
    answer = _run_llm(
        llm.complete, prompt, system=system, max_tokens=800, temperature=0.3
    )

    # persist a short chat history
    history = rec.get("chat_history", [])
    history.append({"question": body.question, "answer": answer})
    get_repository().update(lecture_id, chat_history=history[-50:])

    return {
        "answer": answer,
        "sources": [
            {"text": p["text"][:300], "score": round(p["score"], 3)} for p in passages
        ],
    }
