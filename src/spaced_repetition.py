"""
Spaced Repetition — a real SM-2 (SuperMemo-2) scheduler, applied at lecture
granularity: each lecture's own quiz-attempt history (Lecture.quiz_attempts,
see study_api.py::grade()) stands in for a single "card"'s review history,
since the current data model tracks whole-quiz scores over time rather than
individual question-level history — building true per-question SM-2 would
need a different schema (per-question attempt history) than what exists.

This replaces the previous approach, where the "schedule" feature's day plan
was entirely LLM-improvised and asked to "use spaced repetition" in the
prompt with no actual algorithm or real data behind it. The interval below
is computed the exact way Anki/SuperMemo compute it, from real quiz scores —
see generate_schedule() in study_tools.py for how the LLM plan now anchors
to this instead of inventing a day count from nothing.

Deliberately stateless: SM-2's (repetition_count, ease_factor, interval) is a
deterministic fold over the ordered attempt history, so nothing needs to be
persisted separately — recomputing from quiz_attempts is always correct and
stays in sync automatically as new attempts come in, and a plan generated
last week never shows a stale review date.
"""

import time
from typing import Any, Dict, List, Optional

MIN_EASE_FACTOR = 1.3
DEFAULT_EASE_FACTOR = 2.5
SECONDS_PER_DAY = 86400


def _quality_from_score(score: float) -> int:
    """Map a 0-100 quiz score onto SM-2's 0-5 recall-quality scale."""
    return max(0, min(5, round(score / 100 * 5)))


def compute_review_state(attempts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Fold a lecture's quiz_attempts (any order) through the standard SM-2
    algorithm and return the resulting schedule state. Empty input is a
    valid, common case (no quiz taken yet) — returns a state with no next
    review date rather than raising."""
    repetition_count = 0
    ease_factor = DEFAULT_EASE_FACTOR
    interval_days = 0
    last_graded_at: Optional[float] = None
    quality_history: List[int] = []

    ordered = sorted(attempts, key=lambda a: a.get("graded_at") or 0)
    for attempt in ordered:
        quality = _quality_from_score(attempt.get("score", 0))
        quality_history.append(quality)
        last_graded_at = attempt.get("graded_at", last_graded_at)

        if quality < 3:
            # Failed recall — SM-2 resets the repetition count and goes back
            # to reviewing tomorrow, but does NOT reset ease_factor (one bad
            # attempt shouldn't erase how easy the material has been overall).
            repetition_count = 0
            interval_days = 1
        else:
            if repetition_count == 0:
                interval_days = 1
            elif repetition_count == 1:
                interval_days = 6
            else:
                interval_days = round(interval_days * ease_factor)
            repetition_count += 1

        ease_factor = max(
            MIN_EASE_FACTOR,
            ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
        )

    next_review_at = (
        (last_graded_at + interval_days * SECONDS_PER_DAY)
        if last_graded_at is not None
        else None
    )

    return {
        "attempts_considered": len(ordered),
        "repetition_count": repetition_count,
        "ease_factor": round(ease_factor, 2),
        "interval_days": interval_days,
        "last_graded_at": last_graded_at,
        "next_review_at": next_review_at,
        "quality_history": quality_history,
    }


def describe(review_state: Dict[str, Any]) -> str:
    """One human-readable line, e.g. for an LLM prompt or a UI caption."""
    if review_state["attempts_considered"] == 0:
        return "No quiz attempts yet, so no spaced-repetition review date."
    days = review_state["interval_days"]
    when = time.strftime("%Y-%m-%d", time.localtime(review_state["next_review_at"]))
    unit = "day" if days == 1 else "days"
    return (
        f"Next spaced-repetition review: {when} ({days} {unit} from the last "
        f"quiz attempt, after {review_state['repetition_count']} successful "
        f"review{'s' if review_state['repetition_count'] != 1 else ''} in a row)."
    )
