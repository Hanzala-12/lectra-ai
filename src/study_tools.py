"""
Study Tools — the "NLP & LLM" generators in the architecture:
Notes, Quiz Generation, Personalize Schedule, and Evaluation/Analysis.

Each function turns a lecture transcript into a study artifact using the LLM
client. Structured outputs (quiz, schedule, evaluation) are returned as parsed
JSON; notes are returned as Markdown.
"""

import logging
import uuid
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Keep prompts within a safe context budget; very long lectures are truncated.
MAX_TRANSCRIPT_CHARS = 14000


def _prep(transcript: str) -> str:
    transcript = (transcript or "").strip()
    if len(transcript) > MAX_TRANSCRIPT_CHARS:
        head = transcript[: int(MAX_TRANSCRIPT_CHARS * 0.7)]
        tail = transcript[-int(MAX_TRANSCRIPT_CHARS * 0.3) :]
        return head + "\n...\n[transcript truncated]\n...\n" + tail
    return transcript


# ---------------------------------------------------------------- NOTES
def _notes_messages(transcript: str) -> List[Dict[str, str]]:
    system = (
        "You are an expert study assistant. Produce clear, well-structured study "
        "notes in Markdown from a lecture transcript. Be accurate and concise; do "
        "not invent facts that are not in the transcript."
    )
    prompt = (
        "Create study notes from this lecture transcript. Use this structure:\n"
        "## Summary (3-4 sentences)\n"
        "## Key Points (bullet list)\n"
        "## Key Terms & Definitions\n"
        "## Takeaways / What to Remember\n\n"
        f"TRANSCRIPT:\n{_prep(transcript)}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]


def generate_notes(transcript: str, llm) -> str:
    """Return Markdown study notes (summary, key points, definitions, takeaways)."""
    return llm.chat(_notes_messages(transcript), max_tokens=1800, temperature=0.3)


def generate_notes_stream(transcript: str, llm):
    """Same prompt as generate_notes(), yielded token-by-token instead of
    returned all at once."""
    yield from llm.chat_stream(
        _notes_messages(transcript), max_tokens=1800, temperature=0.3
    )


# ---------------------------------------------------------------- QUIZ
def generate_quiz(transcript: str, llm, num_questions: int = 5) -> List[Dict[str, Any]]:
    """Return a list of MCQs, each Question owning its own Answer rows:
    {question_id, question, answers: [{answer_id, text, is_correct}], explanation}.

    The LLM is asked for the simpler options[]/answer_index shape (models are
    more reliable at that than inventing unique ids) — this function does the
    restructuring into real, individually-addressable Question/Answer entities
    as a deterministic post-processing step, not something we trust the model
    to get right.
    """
    system = (
        "You are a quiz generator. Create multiple-choice questions strictly based "
        "on the transcript. Output ONLY valid JSON."
    )
    prompt = (
        f"From the transcript, write {num_questions} multiple-choice questions that "
        "test understanding. Return JSON of the form:\n"
        '{"questions":[{"question":"...","options":["A","B","C","D"],'
        '"answer_index":0,"explanation":"..."}]}\n\n'
        f"TRANSCRIPT:\n{_prep(transcript)}"
    )
    data = llm.complete_json(prompt, system=system, max_tokens=2000)
    questions = data.get("questions", data) if isinstance(data, dict) else data
    # normalize / validate
    clean = []
    for q in questions or []:
        opts = q.get("options") or []
        if not q.get("question") or len(opts) < 2:
            continue
        idx = q.get("answer_index", 0)
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            idx = 0
        idx = max(0, min(idx, len(opts) - 1))
        answers = [
            {
                "answer_id": f"a{i}_{uuid.uuid4().hex[:6]}",
                "text": opt,
                "is_correct": i == idx,
            }
            for i, opt in enumerate(opts)
        ]
        clean.append(
            {
                "question_id": f"q_{uuid.uuid4().hex[:8]}",
                "question": q["question"],
                "answers": answers,
                "explanation": q.get("explanation", ""),
            }
        )
    return clean


# ------------------------------------------------------------ SCHEDULE (StudyPlan)
def generate_schedule(
    transcript: str,
    llm,
    days: int = 7,
    available_time: Optional[str] = None,
    learning_goals: Optional[str] = None,
    review_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a personalized study plan as JSON.

    available_time / learning_goals are real student-provided inputs (the
    ERD's StudyPlan.available_time / StudyPlan.learning_goals) — when given,
    the plan is built around them instead of being a generic N-day schedule.

    review_state, if given, is a spaced_repetition.compute_review_state()
    result — a real SM-2 schedule computed from this lecture's actual quiz
    score history, not the LLM's own guess. When present, the plan is asked
    to build toward that real review date instead of inventing its own
    "spaced repetition" framing with nothing behind it.
    """
    system = (
        "You are a study-planning assistant. Build a realistic, motivating study "
        "schedule. Output ONLY valid JSON."
    )
    constraints = ""
    if available_time:
        constraints += f"\nThe student's available study time: {available_time}. Size each day's tasks to fit this."
    if learning_goals:
        constraints += f"\nThe student's learning goals: {learning_goals}. Prioritize the plan around achieving these."
    if review_state and review_state.get("attempts_considered", 0) > 0:
        from spaced_repetition import describe as _describe_review

        constraints += (
            f"\nSpaced-repetition schedule computed from this student's real quiz "
            f"history: {_describe_review(review_state)} Build the plan's final day "
            f"around preparing for that review, rather than proposing your own "
            f"unrelated spacing."
        )
    prompt = (
        f"Based on the lecture's topics, create a {days}-day study plan.{constraints}\n"
        "Return JSON:\n"
        '{"plan":[{"day":1,"focus":"...","tasks":["..."],"est_minutes":30}],'
        '"tips":["..."]}\n\n'
        f"TRANSCRIPT:\n{_prep(transcript)}"
    )
    return llm.complete_json(prompt, system=system, max_tokens=1500)


# ---------------------------------------------------------- EVALUATION
def evaluate_lecture(transcript: str, llm) -> Dict[str, Any]:
    """Lecture analysis: topics, difficulty, est. study time, comprehension checks."""
    system = (
        "You are an academic analyst. Analyze the lecture transcript. "
        "Output ONLY valid JSON."
    )
    prompt = (
        "Analyze this lecture and return JSON:\n"
        '{"main_topics":["..."],"difficulty":"beginner|intermediate|advanced",'
        '"estimated_study_minutes":60,"prerequisites":["..."],'
        '"comprehension_questions":["..."],"summary":"..."}\n\n'
        f"TRANSCRIPT:\n{_prep(transcript)}"
    )
    return llm.complete_json(prompt, system=system, max_tokens=1500)


def grade_quiz(
    quiz: List[Dict[str, Any]], answers: List[Optional[str]], llm=None
) -> Dict[str, Any]:
    """Grade submitted answers against the stored quiz (no LLM needed).

    answers is a list of submitted answer_ids (one per question, by position),
    matched against each Question's own Answer rows — not indices into an
    options array, now that Question/Answer are real, independently-id'd
    entities (see generate_quiz())."""
    total = len(quiz)
    correct = 0
    breakdown = []
    for i, q in enumerate(quiz):
        given_id = answers[i] if i < len(answers) else None
        correct_answer = next(
            (a for a in q.get("answers", []) if a.get("is_correct")), None
        )
        correct_id = correct_answer.get("answer_id") if correct_answer else None
        is_correct = given_id is not None and given_id == correct_id
        correct += 1 if is_correct else 0
        breakdown.append(
            {
                "question": q.get("question"),
                "your_answer_id": given_id,
                "correct_answer_id": correct_id,
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            }
        )
    score = round(100 * correct / total, 1) if total else 0.0
    return {"score": score, "correct": correct, "total": total, "breakdown": breakdown}
