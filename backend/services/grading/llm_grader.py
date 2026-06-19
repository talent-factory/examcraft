"""LLM-basierter Grader für offene Fragen (Spec 6.3).

Bewertet ``open_ended`` Antworten via Anthropic Claude und liefert ein
strukturiertes ``LlmGradeOutcome`` zurück, das die ``GradingService``
1:1 in den ``Grade``-Datensatz übernimmt.

Architektur-Entscheidungen:

* **Anthropic SDK direkt statt PydanticAI.** Cache-Control auf
  System- und User-Blöcken ist mit dem Anthropic-Native-API genau
  einen Parameter; PydanticAI würde einen weiteren Layer einziehen,
  der für genau einen Use-Case nicht gerechtfertigt ist. Strukturiertes
  Output-Parsing ist via ``OpenEndedGrade.model_validate_json`` trivial.
* **Prompt-Caching.** Der pro-Frage statische Block (System-Prompt +
  Frage + Musterlösung + Erklärung + Bewertungsregeln) trägt
  ``cache_control: ephemeral``; nur die Studi-Antwort ist variabel.
  Erwarteter Effekt ab dem 2. Studi pro Prüfung: deutlich reduzierte
  Token-Kosten (Grading-Spec §6.3 — Zielwert ``cache-hit-rate > 80%``,
  Prod-Canary-Metrik, noch zu verifizieren; nicht die TF-439-Spec).
* **Strict Schema.** Die Modell-Antwort wird mit Pydantic validiert.
  Bei Schema-Verletzung fällt der Grader auf einen 0-Punkte-Stub mit
  ``confidence=0.0`` zurück, sodass die Lehrperson das Item garantiert
  in der Review-Queue sieht. Ein Schema-Fail darf nie eine ganze
  Submission scheitern lassen.
* **Demo-Mode.** Ohne ``ANTHROPIC_API_KEY`` läuft der Grader im
  Stub-Modus (Confidence 0.0, Rationale-Hinweis). Das hält Tests und
  Free-Tier-Setups grün, ohne dass die Lehrperson ein leises 0-Resultat
  bekommt.
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


# Default-Modell folgt dem aktuellen Projektstandard. Pro Institution
# ist eine Override-Mechanik in Phase 4 vorgesehen (Spec 6.3); hier
# bleibt es eine ENV-Override.
_DEFAULT_MODEL = (
    os.getenv("CLAUDE_GRADING_MODEL")
    or os.getenv("CLAUDE_MODEL")
    or "claude-sonnet-4-5"
)
_DEFAULT_MAX_TOKENS = int(os.getenv("CLAUDE_GRADING_MAX_TOKENS", "1024"))
_DEFAULT_TIMEOUT_S = float(os.getenv("CLAUDE_GRADING_TIMEOUT", "30.0"))


class OpenEndedGrade(BaseModel):
    """Strukturiertes Output-Schema (Spec 6.3)."""

    points_awarded: float = Field(ge=0)
    confidence: float = Field(ge=0, le=1)
    rationale: str
    matched_aspects: list[str] = Field(default_factory=list)
    missing_aspects: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class LlmGradeOutcome:
    """Was der ``GradingService`` zum Persistieren erwartet.

    ``is_correct`` bleibt ``None`` für offene Fragen — die Lehrperson
    übernimmt diese Bewertung in der Review-Queue. Erst die Status-
    Transition auf ``approved``/``manual_override`` zählt als reviewed.
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
    """Anthropic-basierter Bewerter für offene Fragen."""

    PROMPT_ID = GRADING_OPEN_ENDED_PROMPT_ID

    def __init__(self, *, client=None, model: str | None = None) -> None:
        self._client = client
        api_key = os.getenv("ANTHROPIC_API_KEY")
        from services import llm_gateway

        # Gateway-Pfad hat Vorrang vor dem Anthropic-Direkt-Pfad.
        self._gateway = client is None and llm_gateway.gateway_enabled()

        # Fix 1: Kein expliziter model-Override → logischen Alias wählen,
        # damit rohe Modell-IDs nie die Gateway-Allowlist treffen (TF-439).
        if model is not None:
            self.model = model
        elif self._gateway:
            self.model = llm_gateway.ALIAS_GRADING
        else:
            self.model = _DEFAULT_MODEL
        # Demo-Mode nur, wenn weder Client, noch Gateway, noch API-Key vorhanden.
        self.demo_mode = client is None and not self._gateway and not api_key
        if self.demo_mode:
            logger.warning(
                "LlmGrader: ANTHROPIC_API_KEY nicht gesetzt — offene "
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
        """Bewerte eine offene Antwort. Wirft nie — Fehler → 0-Punkte-Stub."""
        if self.demo_mode:
            return self._stub(
                points_max=points_max,
                rationale=(
                    "ANTHROPIC_API_KEY nicht konfiguriert — automatische "
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

        # Clamp gegen Modell-Halluzinationen — Pydantic prüft ge=0,
        # nicht "≤ points_max". Ein Modell-Vorschlag von 12/10 wird auf
        # 10 begrenzt; der Verstoss landet im Log, damit eine Drift in
        # der Prompt-Qualität sichtbar bleibt.
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
        if self._client is not None:
            return self._client
        # Lazy import: anthropic ist eine schwere Dep; Tests, die einen
        # Stub-Client injizieren, wollen den Import nicht erzwingen.
        from anthropic import Anthropic

        self._client = Anthropic(timeout=_DEFAULT_TIMEOUT_S)
        return self._client

    def _client_or_create_gateway(self):
        """Holt oder erstellt den OpenAI-SDK-Client gegen den Gateway.

        Modulattribut-Zugriff (``llm_gateway.make_openai_client``) statt
        direktem Funktionsaufruf, damit Tests via monkeypatch greifen.
        """
        from services import llm_gateway

        return llm_gateway.make_openai_client()

    def _call_gateway(self, question_block: str, student_block: str) -> OpenEndedGrade:
        """Sendet den Grading-Call über den LiteLLM-Gateway (OpenAI-Wire).

        Prompt-Caching wird via ``cache_control``-Felder in den Content-
        Parts transportiert; LiteLLM leitet sie als Anthropic-Header durch.
        System- und Fragen-Block sind statisch pro Frage (Cache-Kandidaten);
        der Studi-Block variiert und trägt deshalb kein ``cache_control``.
        """
        client = self._client_or_create_gateway()
        # Fix 2: Grading-Timeout explizit setzen — make_openai_client() setzt
        # kein Timeout (OpenAI-SDK-Default ~600 s würde Celery-Worker blockieren).
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

        # Zweig: Gateway (OpenAI-Wire) statt Anthropic-Direkt
        if self._gateway:
            return self._call_gateway(question_block, student_block)

        client = self._client_or_create()
        response = client.messages.create(
            model=self.model,
            max_tokens=_DEFAULT_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
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
                }
            ],
        )

        text = self._extract_text(response)
        return self._parse_response(text)

    @staticmethod
    def _extract_text(response) -> str:
        """Hol den ersten Text-Block aus der Antwort.

        Anthropic kann in seltenen Fällen mehrere Content-Blöcke liefern
        (etwa wenn das Modell mit ``thinking``-Steps arbeitet); wir
        nehmen den ersten ``text``-Typ-Block. Verfehlt, wenn die Antwort
        keine Text-Blöcke enthält — der Caller fängt das ab.
        """
        for block in getattr(response, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                return getattr(block, "text", "") or ""
        raise ValueError("Anthropic-Antwort enthielt keinen Text-Block")

    @staticmethod
    def _parse_response(text: str) -> OpenEndedGrade:
        """Parse JSON; toleriert ``{ ... }``-Blöcke umrahmt von Markdown.

        Das Modell wird im Prompt explizit angewiesen, *nur* JSON zu
        liefern. Trotzdem extrahieren wir defensiv den ersten ``{...}``-
        Block, damit ein gelegentliches ```` ```json ```` -Wrapping nicht
        gleich den ganzen Grading-Lauf scheitern lässt.
        """
        stripped = (text or "").strip()
        if not stripped:
            raise ValueError("Leere Modell-Antwort")
        # Trim Markdown-Code-Blöcke — strip fence lines, not characters.
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
