"""LLM-basierter Grader für offene Fragen (Spec 6.3).

Bewertet ``open_ended`` Antworten über den self-hosted LLM-Gateway und
liefert ein strukturiertes ``LlmGradeOutcome`` zurück, das die
``GradingService`` 1:1 in den ``Grade``-Datensatz übernimmt.

Architektur-Entscheidungen:

* **Gateway (OpenAI-Wire) statt Anthropic SDK direkt.** TF-440: der
  frühere Anthropic-Direktpfad (eigener SDK-Import, Anthropic-natives
  ``messages.create``) wurde entfernt — der Gateway ist die einzige
  Quelle für Modell-Routing. Cache-Control auf System- und User-Blöcken
  bleibt möglich: LiteLLM leitet ``cache_control``-Felder aus dem
  OpenAI-Wire-Format als Anthropic-Header durch.
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
* **Demo-Mode.** Ohne konfigurierten Gateway (``LLM_GATEWAY_URL``)
  läuft der Grader im Stub-Modus (Confidence 0.0, Rationale-Hinweis).
  Das hält Tests und Setups ohne Gateway-Zugang grün, ohne dass die
  Lehrperson ein leises 0-Resultat bekommt.

.. note::
   ``Institution.llm_model_for_grading`` (Enterprise-Tier-Override):
   die TF-439-Migration ``tf439_grade_logical`` hat alle zum Zeitpunkt
   ihrer Ausführung bestehenden rohen Modell-IDs bereits auf den
   logischen Alias ``'examcraft/grading'`` normalisiert (siehe
   ``alembic/versions/2026_06_19_tf439_grading_model_logical.py``), und
   es gibt derzeit keinen App-Schreibpfad (kein Admin-Endpoint, kein
   Pydantic-Schema) für dieses Feld. Ein zukünftiger roher Wert (z. B.
   via Direkt-DB-Zugriff) würde unverändert an den Gateway durchgereicht
   und dort scheitern, falls er nicht in der Virtual-Key-Allowlist steht
   — ``grading_service._resolve_llm_grader`` loggt diesen Fall seit
   TF-440 laut, statt ihn erst als kryptische Gateway-Ablehnung sichtbar
   werden zu lassen.
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
    """Gateway-basierter Bewerter für offene Fragen (TF-440)."""

    PROMPT_ID = GRADING_OPEN_ENDED_PROMPT_ID

    def __init__(self, *, client=None, model: str | None = None) -> None:
        # ``client`` ist ein optionaler injizierter OpenAI-SDK-Client
        # (Test-Naht — siehe test_grading_service_llm.py::_stub_gateway_client).
        self._client = client
        from services import llm_gateway

        # Fix 1: Kein expliziter model-Override → logischen Alias wählen,
        # damit rohe Modell-IDs nie die Gateway-Allowlist treffen (TF-439).
        self.model = model if model is not None else llm_gateway.ALIAS_GRADING
        # Demo-Mode nur, wenn weder Client injiziert noch Gateway konfiguriert.
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
        """Bewerte eine offene Antwort. Wirft nie — Fehler → 0-Punkte-Stub."""
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
        """Holt den injizierten Test-Client oder erstellt den OpenAI-SDK-
        Client gegen den Gateway.

        Modulattribut-Zugriff (``llm_gateway.make_openai_client``) statt
        direktem Funktionsaufruf, damit Tests via monkeypatch greifen.
        """
        if self._client is not None:
            return self._client
        from services import llm_gateway

        return llm_gateway.make_openai_client()

    def _call_gateway(self, question_block: str, student_block: str) -> OpenEndedGrade:
        """Sendet den Grading-Call über den LiteLLM-Gateway (OpenAI-Wire).

        Prompt-Caching wird via ``cache_control``-Felder in den Content-
        Parts transportiert; LiteLLM leitet sie als Anthropic-Header durch.
        System- und Fragen-Block sind statisch pro Frage (Cache-Kandidaten);
        der Studi-Block variiert und trägt deshalb kein ``cache_control``.
        """
        client = self._client_or_create()
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

        # TF-440: Gateway ist der einzige Pfad — kein Anthropic-Direkt-Zweig mehr.
        return self._call_gateway(question_block, student_block)

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
