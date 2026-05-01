"""Deterministic grading for multiple_choice + true_false.

Pure functions, no DB dependency. Returns a ``GradeOutcome``;
persistence is the ``GradingService``'s job.

* **multiple_choice**: case-insensitive comparison after normalising
  Moodle's optional letter prefix. Real Moodle exports emit
  ``"B) Bern"`` while the question bank stores the canonical text
  (``"Bern"``); we strip the leading ``A-Z[).:]`` prefix from either
  side before comparing. Multi-correct answers must use a stable
  canonical form (e.g. sorted comma list) on both sides —
  substring/permutation matching is intentionally not done here.
* **true_false**: normalisation across DE/EN synonym tokens
  (``wahr``/``true``/``richtig``/``ja`` ↔ ``falsch``/``false``/
  ``nein``). Locales beyond DE/EN are not recognised — unknown tokens
  resolve to ``is_correct=False`` and 0 points (definite BOOL, no
  tri-state). A non-recognised ``correct_answer`` is logged loudly
  because that's a question-bank bug, not a student error.

Status defaults to ``proposed``; reviewers move it to ``approved`` or
``manual_override`` via the UI.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass


logger = logging.getLogger(__name__)


_TRUE_TOKENS: frozenset[str] = frozenset(
    {
        "wahr",
        "true",
        "richtig",
        "ja",
        "yes",
        "1",
        "stimmt",
        "korrekt",
        "t",
    }
)

_FALSE_TOKENS: frozenset[str] = frozenset(
    {
        "falsch",
        "false",
        "nein",
        "no",
        "0",
        "unzutreffend",
        "f",
    }
)


@dataclass(frozen=True)
class GradeOutcome:
    """Reines Bewertungs-Ergebnis (DB-unabhängig)."""

    points_awarded: float
    points_max: float
    is_correct: bool | None
    status: str = "proposed"


class DeterministicGrader:
    """Bewerter für ``multiple_choice`` + ``true_false``."""

    def grade(
        self,
        *,
        question_type: str,
        given_answer: str | None,
        correct_answer: str | None,
        points_max: float,
    ) -> GradeOutcome:
        """Bewerte eine einzelne Antwort.

        Args:
            question_type: ``multiple_choice`` oder ``true_false``.
            given_answer: Antwort der Studierenden (kann None/leer sein).
            correct_answer: Musterlösung (kann None sein → automatisch
                falsch).
            points_max: Maximalpunktzahl der Frage.

        Returns:
            ``GradeOutcome`` mit ``status='proposed'``.

        Raises:
            ValueError: bei unbekanntem ``question_type``.
        """
        if question_type == "multiple_choice":
            is_correct = self._mc_match(given_answer, correct_answer)
        elif question_type == "true_false":
            is_correct = self._tf_match(given_answer, correct_answer)
        else:
            raise ValueError(
                f"DeterministicGrader unterstützt question_type "
                f"'{question_type}' nicht — nutze LlmGrader oder Stub."
            )

        return GradeOutcome(
            points_awarded=points_max if is_correct else 0.0,
            points_max=points_max,
            is_correct=is_correct,
        )

    @staticmethod
    def stub_for_open_ended(*, points_max: float) -> GradeOutcome:
        """Placeholder for open-ended answers when no LLM grader is wired.

        Returns 0 points and ``is_correct=None`` (the sentinel
        ``GradingService._compute_grade_status`` reads as
        "needs review"), so a submission with an open question always
        ends up in ``pending_review`` until reviewed manually or by an
        LLM grader.
        """
        return GradeOutcome(
            points_awarded=0.0,
            points_max=points_max,
            is_correct=None,
            status="proposed",
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    # Strips a leading single-letter Moodle prefix like "A) ", "B. ",
    # "(C) ", "[D] ". Anchored so it never eats real content beyond the
    # marker. Single-character options (e.g. correct_answer="A") survive
    # because the regex requires at least one separator and one
    # subsequent character.
    _LETTER_PREFIX_REGEX = re.compile(r"^[\(\[]?\s*[A-Za-z]\s*[\)\]\.\:]\s+(?=\S)")

    @staticmethod
    def _normalise(value: str | None) -> str:
        return (value or "").strip().lower()

    @classmethod
    def _strip_letter_prefix(cls, value: str) -> str:
        return cls._LETTER_PREFIX_REGEX.sub("", value, count=1)

    @classmethod
    def _mc_match(cls, given_answer: str | None, correct_answer: str | None) -> bool:
        given = cls._normalise(given_answer)
        correct = cls._normalise(correct_answer)
        if not given or not correct:
            return False
        if given == correct:
            return True
        # Tolerate Moodle's letter-prefix on either side. Strip-equality
        # only fires when stripping actually changed the value, so a
        # bare letter like ``correct="a"`` won't accidentally match a
        # different bare letter.
        given_stripped = cls._strip_letter_prefix(given)
        correct_stripped = cls._strip_letter_prefix(correct)
        if given_stripped != given or correct_stripped != correct:
            return given_stripped == correct_stripped
        return False

    @classmethod
    def _tf_match(cls, given_answer: str | None, correct_answer: str | None) -> bool:
        given_bool = cls._to_bool(given_answer)
        correct_bool = cls._to_bool(correct_answer)
        if correct_bool is None and correct_answer:
            # Question-bank bug — every student auto-fails this question
            # otherwise. Make it visible in the import logs so the author
            # can fix the canonical answer.
            logger.warning(
                "DeterministicGrader: true_false correct_answer %r not in "
                "DE/EN token set — every student will be graded wrong",
                correct_answer,
            )
        if given_bool is None or correct_bool is None:
            return False
        return given_bool == correct_bool

    @classmethod
    def _to_bool(cls, value: str | None) -> bool | None:
        token = cls._normalise(value)
        if not token:
            return None
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False
        return None
