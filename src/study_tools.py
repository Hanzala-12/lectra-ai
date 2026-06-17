"""
Study Tools — the "NLP & LLM" generators in the architecture:
Notes, Quiz Generation, Personalize Schedule, and Evaluation/Analysis.

Each function turns a lecture transcript into a study artifact using the LLM
client. Structured outputs (quiz, schedule, evaluation) are returned as parsed
JSON; notes are returned as Markdown.
"""

import logging
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
def generate_notes(transcript: str, llm) -> str:
    """Return Markdown study notes (summary, key points, definitions, takeaways)."""
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
    return llm.complete(prompt, system=system, max_tokens=1800, temperature=0.3)


# ---------------------------------------------------------------- QUIZ
def generate_quiz(transcript: str, llm, num_questions: int = 5) -> List[Dict[str, Any]]:
    """Return a list of MCQs: {question, options[4], answer_index, explanation}."""
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
        clean.append(
            {
                "question": q["question"],
                "options": opts,
                "answer_index": idx,
                "explanation": q.get("explanation", ""),
            }
        )
    return clean


# ------------------------------------------------------------ SCHEDULE
def generate_schedule(transcript: str, llm, days: int = 7) -> Dict[str, Any]:
    """Return a personalized spaced-repetition study plan as JSON."""
    system = (
        "You are a study-planning assistant. Build a realistic, motivating study "
        "schedule using spaced repetition. Output ONLY valid JSON."
    )
    prompt = (
        f"Based on the lecture's topics, create a {days}-day study plan. Return JSON:\n"
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
    quiz: List[Dict[str, Any]], answers: List[int], llm=None
) -> Dict[str, Any]:
    """Grade submitted answers against the stored quiz (no LLM needed)."""
    total = len(quiz)
    correct = 0
    breakdown = []
    for i, q in enumerate(quiz):
        given = answers[i] if i < len(answers) else None
        is_correct = given == q.get("answer_index")
        correct += 1 if is_correct else 0
        breakdown.append(
            {
                "question": q.get("question"),
                "your_answer": given,
                "correct_answer": q.get("answer_index"),
                "is_correct": is_correct,
                "explanation": q.get("explanation", ""),
            }
        )
    score = round(100 * correct / total, 1) if total else 0.0
    return {"score": score, "correct": correct, "total": total, "breakdown": breakdown}
