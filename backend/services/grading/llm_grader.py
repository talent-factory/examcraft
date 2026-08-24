"""LLM-based grader for open-ended questions (Spec 6.3).

Grades ``open_ended`` answers via the self-hosted LLM Gateway and returns
a structured ``LlmGradeOutcome`` that ``GradingService`` copies 1:1 into
the ``Grade`` record.

Architecture decisions:

* **Gateway (OpenAI wire) instead of the Anthropic SDK directly.**
  TF-440: the former direct Anthropic path (own SDK import, Anthropic-
  native ``messages.create``) was removed — the Gateway is the sole
  source of truth for model routing. Cache control on system and user
  blocks remains possible: LiteLLM passes ``cache_control`` fields from
  the OpenAI wire format through as Anthropic headers.
* **Prompt caching.** The per-question static block (system prompt +
  question + model answer + explanation + grading rules) carries
  ``cache_control: ephemeral``; only the student's answer is variable.
  Expected effect from the 2nd student per exam onward: significantly
  reduced token costs (grading spec §6.3 — target ``cache-hit-rate >
  80%``, a prod canary metric, still to be verified; not the TF-439
  spec).
* **Strict schema.** The model's response is validated with Pydantic.
  On a schema violation, the grader falls back to a 0-point stub with
  ``confidence=0.0``, so the teacher is guaranteed to see the item in
  the review queue. A schema failure must never fail an entire
  submission.
* **Demo mode.** Without a configured Gateway (``LLM_GATEWAY_URL``),
  the grader runs in stub mode (confidence 0.0, rationale note). This
  keeps tests and setups without Gateway access green, without giving
  the teacher a silent 0 result.

.. note::
   ``Institution.llm_model_for_grading`` (enterprise tier override):
   the TF-439 migration ``tf439_grade_logical`` already normalized all
   raw model IDs that existed at the time it ran to the logical alias
   ``'examcraft/grading'`` (see
   ``alembic/versions/2026_06_19_tf439_grading_model_logical.py``), and
   there is currently no app write path (no admin endpoint, no Pydantic
   schema) for this field. A future raw value (e.g. via direct DB
   access) would be passed through to the Gateway unchanged and would
   fail there if it isn't on the virtual key allowlist —
   ``grading_service._resolve_llm_grader`` has logged this case loudly
   since TF-440, instead of it only surfacing as a cryptic Gateway
   rejection.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

from pydantic import BaseModel, Field, ValidationError

from services.grading.grading_prompts import (
    GRADING_OPEN_ENDED_PROMPT_ID,
    SYSTEM_PROMPT,
    build_question_context_block,
    build_student_answer_block,
)


logger = logging.getLogger(__name__)


_DEFAULT_MAX_TOKENS = int(os.getenv("CLAUDE_GRADING_MAX_TOKENS", "1024"))
_DEFAULT_TIMEOUT_S = float(os.getenv("CLAUDE_GRADING_TIMEOUT", "30.0"))


class OpenEndedGrade(BaseModel):
    """Structured output schema (Spec 6.3)."""

    points_awarded: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    rationale: str
    matched_aspects: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class LlmGradeOutcome:
    """What ``GradingService`` expects for persisting.

    ``is_correct`` stays ``None`` for open-ended questions — the teacher
    makes that call in the review queue. Only the status transition to
    ``approved``/``manual_override`` counts as reviewed.
    """

    points_awarded: float
    points_max: float
    confidence: float
    rationale: str
    matched_aspects: list[str]
    missing_aspects: list[str]
    is_correct: None = None
    status: str = "proposed"


class LlmGrader:
    """Gateway-based grader for open-ended questions (TF-440)."""

    PROMPT_ID = GRADING_OPEN_ENDED_PROMPT_ID

    def __init__(self, *, client=None, model: str | None = None) -> None:
        # ``client`` is an optional injected OpenAI SDK client
        # (test seam — see test_grading_service_llm.py::_stub_gateway_client).
        self._client = client
        from services import llm_gateway

        # Fix 1: no explicit model override → pick the logical alias, so raw
        # model IDs never hit the Gateway allowlist (TF-439).
        self.model = model if model is not None else llm_gateway.ALIAS_GRADING
        # Demo mode only when neither a client is injected nor a Gateway is
        # configured.
        self.demo_mode = client is None and not llm_gateway.gateway_enabled()
        if self.demo_mode:
            logger.warning(
                "LlmGrader: LLM_GATEWAY_URL nicht gesetzt — offene "
                "Fragen werden als 0-Punkte-Stub gegradet (Review nötig)."
            )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def grade(
        self,
        *,
        question_text: str,
        correct_answer: str,
        given_answer: str | None,
        points_max: float,
        explanation: str | None = None,
        difficulty: str | None = None,
        bloom_level: str | None = None,
    ) -> LlmGradeOutcome:
        """Grade an open-ended answer. Never raises — errors → 0-point stub."""
        if self.demo_mode:
            return self._stub(
                points_max=points_max,
                rationale=(
                    "LLM_GATEWAY_URL nicht konfiguriert — automatische "
                    "Bewertung übersprungen, bitte manuell bewerten."
                ),
            )

        if not (correct_answer or "").strip():
            return self._stub(
                points_max=points_max,
                rationale=(
                    "Keine Musterlösung hinterlegt — automatische "
                    "Bewertung nicht möglich, bitte manuell bewerten."
                ),
            )

        try:
            grade = self._call_model(
                question_text=question_text,
                correct_answer=correct_answer,
                given_answer=given_answer,
                points_max=points_max,
                explanation=explanation,
                difficulty=difficulty,
                bloom_level=bloom_level,
            )
        except Exception as exc:  # noqa: BLE001 — fail soft, see module docstring
            logger.exception(
                "LlmGrader: Modell-Call fehlgeschlagen (%s) — Stub-Outcome",
                type(exc).__name__,
            )
            return self._stub(
                points_max=points_max,
                rationale=(
                    f"Automatische Bewertung fehlgeschlagen "
                    f"({type(exc).__name__}). Bitte manuell bewerten."
                ),
            )

        # Clamp against model hallucinations — Pydantic only checks ge=0,
        # not "≤ points_max". A model suggestion of 12/10 gets capped at
        # 10; the violation is logged so a drift in prompt quality stays
        # visible.
        clamped_points = max(0.0, min(grade.points_awarded, points_max))
        if clamped_points != grade.points_awarded:
            logger.warning(
                "LlmGrader: Modell-Vorschlag %.2f überschreitet Maximum %.2f — clamp.",
                grade.points_awarded,
                points_max,
            )

        return LlmGradeOutcome(
            points_awarded=clamped_points,
            points_max=points_max,
            confidence=grade.confidence,
            rationale=grade.rationale,
            matched_aspects=list(grade.matched_aspects),
            missing_aspects=list(grade.missing_aspects),
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _client_or_create(self):
        """Returns the injected test client or creates the OpenAI SDK
        client against the Gateway.

        Uses module-attribute access (``llm_gateway.make_openai_client``)
        instead of a direct function call, so tests can hook in via
        monkeypatch.
        """
        if self._client is not None:
            return self._client
        from services import llm_gateway

        return llm_gateway.make_openai_client()

    def _call_gateway(self, question_block: str, student_block: str) -> OpenEndedGrade:
        """Sends the grading call via the LiteLLM Gateway (OpenAI wire).

        Prompt caching is carried via ``cache_control`` fields on the
        content parts; LiteLLM passes them through as Anthropic headers.
        The system and question blocks are static per question (cache
        candidates); the student block varies and therefore carries no
        ``cache_control``.
        """
        client = self._client_or_create()
        # Fix 2: set the grading timeout explicitly — make_openai_client()
        # sets no timeout (the OpenAI SDK default of ~600s would block the
        # Celery worker).
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=_DEFAULT_MAX_TOKENS,
            timeout=_DEFAULT_TIMEOUT_S,
            messages=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": question_block,
                            "cache_control": {"type": "ephemeral"},
                        },
                        {"type": "text", "text": student_block},
                    ],
                },
            ],
        )
        choices = getattr(response, "choices", None) or []
        if not choices:
            raise ValueError("Gateway-Antwort enthielt keine Choices")
        text = getattr(choices[0].message, "content", "") or ""
        return self._parse_response(text)

    def _call_model(
        self,
        *,
        question_text: str,
        correct_answer: str,
        given_answer: str | None,
        points_max: float,
        explanation: str | None,
        difficulty: str | None,
        bloom_level: str | None,
    ) -> OpenEndedGrade:
        question_block = build_question_context_block(
            question_text=question_text,
            correct_answer=correct_answer,
            explanation=explanation,
            points_max=points_max,
            difficulty=difficulty,
            bloom_level=bloom_level,
        )
        student_block = build_student_answer_block(given_answer)

        # TF-440: the Gateway is the only path — no more direct Anthropic branch.
        return self._call_gateway(question_block, student_block)

    @staticmethod
    def _parse_response(text: str) -> OpenEndedGrade:
        """Parse JSON; tolerates ``{ ... }`` blocks wrapped in Markdown.

        The model is explicitly instructed in the prompt to return *only*
        JSON. Even so, we defensively extract the first ``{...}`` block,
        so that an occasional ```` ```json ```` wrapping doesn't fail the
        whole grading run.
        """
        stripped = (text or "").strip()
        if not stripped:
            raise ValueError("Leere Modell-Antwort")
        # Trim Markdown code blocks — strip fence lines, not characters.
        # str.strip("`") removes any backtick from both ends of the string,
        # which corrupts content that legitimately contains backticks (e.g.
        # rationale: "matches `key criterion`"). Instead, drop the opening
        # fence line (```json or ```) and the closing fence line (```).
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            inner = lines[1:]
            if inner and inner[-1].strip() == "```":
                inner = inner[:-1]
            stripped = "\n".join(inner).strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].lstrip()
        first_brace = stripped.find("{")
        last_brace = stripped.rfind("}")
        if first_brace == -1 or last_brace <= first_brace:
            raise ValueError(
                f"Kein JSON-Objekt in Modell-Antwort gefunden: {stripped[:120]!r}"
            )
        payload = stripped[first_brace : last_brace + 1]
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Modell-Antwort ist kein valides JSON: {exc}") from exc
        try:
            return OpenEndedGrade.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Modell-Antwort verstösst gegen Schema: {exc}") from exc

    @staticmethod
    def _stub(*, points_max: float, rationale: str) -> LlmGradeOutcome:
        return LlmGradeOutcome(
            points_awarded=0.0,
            points_max=points_max,
            confidence=0.0,
            rationale=rationale,
            matched_aspects=[],
            missing_aspects=[],
        )
