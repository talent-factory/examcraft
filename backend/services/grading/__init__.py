"""Grading strategies.

Currently the DeterministicGrader covers ``multiple_choice`` +
``true_false``. ``open_ended`` answers are stubbed via
``DeterministicGrader.stub_for_open_ended`` and routed to a real LLM
grader once one is added under this package.
"""

from services.grading.deterministic_grader import (
    DeterministicGrader,
    GradeOutcome,
)

__all__ = ["DeterministicGrader", "GradeOutcome"]
