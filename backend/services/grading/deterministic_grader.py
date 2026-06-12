"""Deterministic grading for single_choice + multiple_choice + true_false.

Pure functions, no DB dependency. Returns a ``GradeOutcome``;
persistence is the ``GradingService``'s job.

* **single_choice** (single-answer, binary): case-insensitive comparison
  after normalising Moodle's optional letter prefix. Real Moodle exports
  emit ``"B) Bern"`` while the question bank stores the canonical text
  (``"Bern"``); we strip the leading ``A-Z[).:]`` prefix from either
  side before comparing. Full marks or zero — no partial credit.
* **multiple_choice** (multi-answer, fractional): Moodle-style partial
  credit. The correct set is stored as a JSON array string in
  ``correct_answer`` (e.g. ``'["A","C"]'``); the student answer is parsed
  the same way. For correct-set size ``k`` and total option count ``N``::

      positive = selected_correct / k
      negative = selected_wrong / (N - k)   (0 when N - k == 0)
      points   = max(0.0, positive - negative) * points_max

  Floored at 0 so over-selecting can never net positive points;
  ``is_correct`` is strict set equality. ``num_options`` (= N) must be
  passed by the caller — without it (or without a usable correct set) the
  answer scores 0 and is flagged needs-review (``is_correct=None`` →
  ``pending_review``) with a loud warning, so a misconfigured question
  never silently zeroes a student behind a ``fully_reviewed`` status.
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

import json
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
    """Bewerter für ``single_choice`` + ``multiple_choice`` + ``true_false``."""

    def grade(
        self,
        *,
        question_type: str,
        given_answer: str | None,
        correct_answer: str | None,
        points_max: float,
        num_options: int | None = None,
    ) -> GradeOutcome:
        """Bewerte eine einzelne Antwort.

        Args:
            question_type: ``single_choice``, ``multiple_choice`` oder
                ``true_false``.
            given_answer: Antwort der Studierenden (kann None/leer sein).
            correct_answer: Musterlösung (kann None sein → automatisch
                falsch).
            points_max: Maximalpunktzahl der Frage.
            num_options: Gesamtzahl der Antwortoptionen — nur für
                ``multiple_choice`` (Moodle-fractional) benötigt, sonst
                ignoriert.

        Returns:
            ``GradeOutcome`` mit ``status='proposed'``.

        Raises:
            ValueError: bei unbekanntem ``question_type``.
        """
        if question_type == "single_choice":
            is_correct = self._mc_match(given_answer, correct_answer)
        elif question_type == "multiple_choice":
            return self._grade_multiple_response(
                given_answer=given_answer,
                correct_answer=correct_answer,
                points_max=points_max,
                num_options=num_options,
            )
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
    def _parse_answer_set(cls, value: str | None) -> set[str]:
        """Parse a multi-answer value into a normalised set of tokens.

        Canonical form is a JSON array string (``'["A","C"]'``). Falls
        back to comma/semicolon-split for legacy/plain inputs. Each entry
        is normalised (trim + lowercase, Moodle letter-prefix stripped)
        so given and correct compare identically.
        """
        if not value or not value.strip():
            return set()
        raw = value.strip()
        items: list[str]
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            parsed = None
            if raw[:1] in ("[", "{"):
                # Value was clearly meant to be JSON but is malformed —
                # mirror _tf_match's loud warning rather than silently
                # mis-parsing it via the delimiter fallback below.
                logger.warning(
                    "DeterministicGrader: Mehrfachauswahl-Wert %r sieht wie "
                    "JSON aus, liess sich aber nicht parsen — Fallback auf "
                    "Trennzeichen-Split, Bewertung evtl. falsch.",
                    value,
                )
        if isinstance(parsed, list):
            items = [str(item) for item in parsed]
        else:
            items = re.split(r"[,;]", raw)
        tokens: set[str] = set()
        for item in items:
            token = cls._normalise(item)
            if not token:
                continue
            stripped = cls._strip_letter_prefix(token)
            tokens.add(stripped if stripped else token)
        return tokens

    @classmethod
    def _grade_multiple_response(
        cls,
        *,
        given_answer: str | None,
        correct_answer: str | None,
        points_max: float,
        num_options: int | None,
    ) -> GradeOutcome:
        """Moodle-style fractional grading for ``multiple_choice``.

        For correct-set size ``k`` and total option count ``N``::

            positive = selected_correct / k
            negative = selected_wrong / (N - k)   (0 if N - k == 0)
            fraction = max(0.0, positive - negative)
            points   = round(fraction * points_max, 4)

        Floored at 0 so over-selecting (e.g. picking everything) can
        never net positive points. ``is_correct`` is the strict set
        equality of the normalised given/correct sets.
        """
        correct_set = cls._parse_answer_set(correct_answer)
        given_set = cls._parse_answer_set(given_answer)
        k = len(correct_set)

        if k == 0 or num_options is None or num_options <= 0 or k > num_options:
            # Misconfigured question (no usable correct set, missing/invalid
            # option count, or more correct tokens than options). Return the
            # ``is_correct=None`` open-ended sentinel so _compute_grade_status
            # routes the answer to ``pending_review`` instead of silently
            # zeroing a possibly-correct student behind ``fully_reviewed``.
            logger.warning(
                "DeterministicGrader: multiple_choice ohne verwertbare "
                "correct_answer (%r) oder num_options (%r) — 0 Punkte, "
                "is_correct=None (pending_review).",
                correct_answer,
                num_options,
            )
            return GradeOutcome(
                points_awarded=0.0,
                points_max=points_max,
                is_correct=None,
            )

        wrong_total = num_options - k
        selected_correct = len(given_set & correct_set)
        selected_wrong = len(given_set - correct_set)

        positive = selected_correct / k
        negative = (selected_wrong / wrong_total) if wrong_total else 0.0
        fraction = max(0.0, positive - negative)
        points = round(fraction * points_max, 4)

        return GradeOutcome(
            points_awarded=points,
            points_max=points_max,
            is_correct=given_set == correct_set,
        )

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
