"""
study_tools.py — regression coverage for LLM-response-shape normalization.

Not covered by test_study_api.py's integration tests (those go through the
shared FakeLLM fixture, which always returns the well-formed shape) - this
targets study_tools functions directly with a purpose-built stub LLM, so a
specific malformed-but-valid-JSON response can be simulated precisely.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import study_tools  # noqa: E402


class _StubLLM:
    """Bare-minimum llm-shaped object: complete_json() returns whatever
    canned value the test hands it, regardless of the prompt."""

    def __init__(self, complete_json_return):
        self._value = complete_json_return

    def complete_json(self, prompt, system=None, **kwargs):
        return self._value


def test_generate_schedule_normalizes_bare_list_response():
    """Reproduces a real live failure: a model occasionally returns the
    plan array directly instead of the requested {"plan": [...], "tips":
    [...]} wrapper. complete_json() only validates that the response
    parses as JSON, not that it matches the requested shape, so this
    reached make_schedule() and crashed with AttributeError: 'list' object
    has no attribute 'get' (study_api.py's `generated.get("plan", [])`).
    generate_schedule() must normalize this itself so every caller can
    trust its documented Dict[str, Any] return type."""
    bare_list = [
        {"day": 1, "focus": "Intro", "tasks": ["Read notes"], "est_minutes": 30},
        {"day": 2, "focus": "Practice", "tasks": ["Do exercises"], "est_minutes": 45},
    ]
    llm = _StubLLM(bare_list)

    result = study_tools.generate_schedule("Some transcript text.", llm, days=2)

    assert isinstance(result, dict)
    assert result["plan"] == bare_list
    assert result["tips"] == []


def test_generate_schedule_passes_through_well_formed_response():
    """The normal case: a model that already returns the requested wrapper
    shape is passed through unchanged, not double-wrapped or mangled."""
    well_formed = {
        "plan": [
            {"day": 1, "focus": "Intro", "tasks": ["Read notes"], "est_minutes": 30}
        ],
        "tips": ["Review daily"],
    }
    llm = _StubLLM(well_formed)

    result = study_tools.generate_schedule("Some transcript text.", llm, days=1)

    assert result == well_formed
