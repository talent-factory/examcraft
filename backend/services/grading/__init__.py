"""Grading strategies.

* ``DeterministicGrader`` — ``multiple_choice`` + ``true_false``
  (pure functions, kein LLM).
* ``LlmGrader`` — ``open_ended``, Anthropic Claude mit Prompt-Caching.

Beide liefern Outcome-Dataclasses, die der ``GradingService`` 1:1 in
``Grade``-Records persistiert.
"""

from services.grading.deterministic_grader import (
    DeterministicGrader,
    GradeOutcome,
)
from services.grading.llm_grader import (
    LlmGradeOutcome,
    LlmGrader,
    OpenEndedGrade,
)


__all__ = [
    "DeterministicGrader",
    "GradeOutcome",
    "LlmGradeOutcome",
    "LlmGrader",
    "OpenEndedGrade",
]
