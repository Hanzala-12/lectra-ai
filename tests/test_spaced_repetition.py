"""
Spaced repetition (SM-2) tests. Pure algorithm, no network/DB — attempts are
plain dicts shaped like Lecture.quiz_attempts entries.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spaced_repetition import compute_review_state, describe

DAY = 86400


def _attempt(score, graded_at):
    return {"score": score, "graded_at": graded_at}


def test_empty_attempts_returns_no_review_date():
    state = compute_review_state([])
    assert state["attempts_considered"] == 0
    assert state["next_review_at"] is None
    assert state["repetition_count"] == 0
    assert state["interval_days"] == 0


def test_single_perfect_attempt():
    state = compute_review_state([_attempt(100, 1000)])
    assert state["repetition_count"] == 1
    assert state["interval_days"] == 1
    assert state["ease_factor"] == 2.6
    assert state["next_review_at"] == 1000 + 1 * DAY
    assert state["quality_history"] == [5]


def test_two_perfect_attempts():
    state = compute_review_state([_attempt(100, 1000), _attempt(100, 2000)])
    assert state["repetition_count"] == 2
    assert state["interval_days"] == 6
    assert state["ease_factor"] == 2.7
    assert state["next_review_at"] == 2000 + 6 * DAY


def test_three_perfect_attempts():
    state = compute_review_state(
        [_attempt(100, 1000), _attempt(100, 2000), _attempt(100, 3000)]
    )
    assert state["repetition_count"] == 3
    # SM-2: interval = round(previous_interval * ease_factor_before_this_update)
    # = round(6 * 2.7) = 16
    assert state["interval_days"] == 16
    assert state["ease_factor"] == 2.8
    assert state["next_review_at"] == 3000 + 16 * DAY


def test_failed_attempt_resets_repetition_but_not_fully_ease_factor():
    state = compute_review_state(
        [_attempt(100, 1000), _attempt(100, 2000), _attempt(40, 3000)]
    )
    assert state["repetition_count"] == 0  # quality 2 < 3 -> reset
    assert state["interval_days"] == 1  # back to reviewing tomorrow
    # ease_factor decreased from the pre-failure 2.7, but wasn't reset to 2.5
    assert state["ease_factor"] < 2.7
    assert state["ease_factor"] > 1.3


def test_ease_factor_clamped_at_minimum():
    attempts = [_attempt(0, i * 1000) for i in range(1, 10)]
    state = compute_review_state(attempts)
    assert state["ease_factor"] == 1.3


def test_attempts_are_sorted_chronologically_regardless_of_input_order():
    chronological = compute_review_state(
        [_attempt(100, 1000), _attempt(100, 2000), _attempt(40, 3000)]
    )
    scrambled = compute_review_state(
        [_attempt(40, 3000), _attempt(100, 1000), _attempt(100, 2000)]
    )
    assert scrambled == chronological


def test_describe_no_attempts():
    msg = describe(compute_review_state([]))
    assert "No quiz attempts yet" in msg


def test_describe_with_review_date():
    msg = describe(compute_review_state([_attempt(100, 1000), _attempt(100, 2000)]))
    assert "6 days" in msg
    assert "2 successful reviews" in msg


def test_describe_singular_day_and_review():
    msg = describe(compute_review_state([_attempt(100, 1000)]))
    assert "1 day " in msg or msg.strip().endswith("1 day")
    assert "1 successful review " in msg or "1 successful review)" in msg
