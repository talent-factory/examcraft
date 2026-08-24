"""
Claude API Service for ExamCraft AI
Generates exam questions via the self-hosted LLM Gateway.

TF-440 (Phase 2): the legacy direct path (raw ``httpx`` against
``/v1/messages``, ``CLAUDE_MODEL_FALLBACK`` chain, Models API startup check)
was removed. The Gateway (LiteLLM) is the sole source of truth for
model routing — a retired model is fixed there via a config edit
instead of an app-side fallback chain here (TF-437/438).
"""

import logging
import os
from typing import Any, Dict, List

from services import llm_gateway

logger = logging.getLogger(__name__)


class ModelUnavailableError(Exception):
    """Raised when the Gateway classifies a model as permanently unavailable
    (4xx except 429) — TF-438/TF-440.

    A retired model is a *permanent* condition, so callers — in particular
    the Celery question-generation task — must treat this as non-retryable
    instead of looping indefinitely (TF-437 class).
    """


class ClaudeService:
    """Question generation via the LLM Gateway (logical alias
    ``examcraft/generation``, TF-439/440)."""

    def __init__(self):
        self.demo_mode = (not llm_gateway.gateway_enabled()) or os.getenv(
            "CLAUDE_DEMO_MODE", "false"
        ).lower() == "true"
        # Logical alias instead of a raw model ID — the Gateway resolves the
        # model. Informational only now (dev debug endpoint main.py:/claude/health).
        self.model = llm_gateway.ALIAS_GENERATION

        if self.demo_mode:
            logger.warning(
                "Claude generation running in DEMO MODE — LLM_GATEWAY_URL "
                "not configured or CLAUDE_DEMO_MODE=true"
            )
        else:
            logger.info(f"Claude API initialized via Gateway: model={self.model}")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Legacy shape for the dev-only debug endpoints
        (``/api/v1/claude/usage`` and ``/api/v1/claude/health``).
        Token/cost tracking has run centrally on the Gateway (LiteLLM)
        since TF-439; only zero placeholders remain here so the
        existing endpoint contract doesn't break.
        """
        return {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "requests_last_minute": 0,
            "demo_mode": self.demo_mode,
        }

    async def generate_questions(
        self,
        topic: str,
        difficulty: str = "medium",
        question_count: int = 5,
        question_types: List[str] = None,
        language: str = "de",
    ) -> List[Dict[str, Any]]:
        """
        Generate exam questions via the LLM-Gateway

        Args:
            topic: The subject/topic for the questions
            difficulty: easy, medium, or hard
            question_count: Number of questions to generate
            question_types: Types of questions (single_choice, open_ended, etc.)
            language: Language for questions (de, en)

        Returns:
            List of generated questions
        """

        if self.demo_mode:
            raise RuntimeError(
                "Claude generation is not configured (LLM_GATEWAY_URL missing "
                "or CLAUDE_DEMO_MODE=true). Cannot generate questions."
            )

        prompt = self._build_prompt(
            topic, difficulty, question_count, question_types, language
        )

        from services.gateway_generator import generate_questions_via_gateway

        return await generate_questions_via_gateway(prompt)

    async def generate_exam_async(self, exam_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate exam questions asynchronously for RAG integration

        Args:
            exam_request: Dictionary with exam parameters
                - topic: str
                - difficulty: str
                - question_count: int
                - question_types: List[str]
                - context: str (optional)
                - language: str
                - custom_prompt: str (optional) - Custom prompt template to use instead of default

        Returns:
            Dictionary with generated questions
        """
        try:
            topic = exam_request.get("topic", "")
            difficulty = exam_request.get("difficulty", "medium")
            question_count = exam_request.get("question_count", 1)
            question_types = exam_request.get("question_types", ["single_choice"])
            context = exam_request.get("context", "")
            language = exam_request.get("language", "de")
            custom_prompt = exam_request.get("custom_prompt")

            # Use custom prompt if provided (from Prompt Knowledge Base)
            if custom_prompt:
                logger.info(
                    f"Using custom prompt template ({len(custom_prompt)} chars)"
                )

                if self.demo_mode:
                    raise RuntimeError(
                        "Claude generation is not configured. Cannot generate questions."
                    )

                from pydantic_ai.exceptions import ModelHTTPError

                from services.gateway_generator import (
                    generate_questions_via_gateway,
                    generate_raw_via_gateway,
                )

                try:
                    questions = await generate_questions_via_gateway(custom_prompt)
                # Pass through transport/model errors (TF-438 classification):
                # ModelUnavailableError = permanent (fail-fast),
                # ModelHTTPError = transient (retryable). Only a genuine
                # typed-output/parsing failure may fall back to raw Markdown —
                # otherwise the fallback masks a 5xx blip.
                except (ModelUnavailableError, ModelHTTPError):
                    raise
                except Exception as e:  # typed output failed
                    logger.warning(
                        f"Gateway typed parse failed, returning raw Markdown: {e}"
                    )
                    content = await generate_raw_via_gateway(custom_prompt)
                    questions = [
                        {
                            "question": content,
                            "type": "markdown",
                            "raw_output": True,
                        }
                    ]

                return {
                    "questions": questions,
                    "topic": topic,
                    "difficulty": difficulty,
                    "question_count": len(questions),
                    "context_used": bool(context),
                    "custom_prompt_used": True,
                }

            # Default flow: Build enhanced prompt with context
            if context:
                enhanced_topic = f"{topic}\n\nKontext:\n{context}"
            else:
                enhanced_topic = topic

            # Generate questions using existing method
            questions = await self.generate_questions(
                topic=enhanced_topic,
                difficulty=difficulty,
                question_count=question_count,
                question_types=question_types,
                language=language,
            )

            return {
                "questions": questions,
                "topic": topic,
                "difficulty": difficulty,
                "question_count": len(questions),
                "context_used": bool(context),
            }

        except Exception as e:
            logger.error(f"Exam generation failed: {e}", exc_info=True)
            raise

    def _build_prompt(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        question_types: List[str],
        language: str,
    ) -> str:
        """Build the prompt sent to the Gateway"""

        lang_instruction = "auf Deutsch" if language == "de" else "in English"
        difficulty_map = {
            "easy": "einfach" if language == "de" else "easy",
            "medium": "mittel" if language == "de" else "medium",
            "hard": "schwer" if language == "de" else "hard",
        }

        prompt = f"""
Erstelle {question_count} Prüfungsfragen zum Thema "{topic}" {lang_instruction}.

Anforderungen:
- Schwierigkeitsgrad: {difficulty_map.get(difficulty, difficulty)}
- Mischung aus Multiple-Choice und offenen Fragen
- Jede Frage soll lehrreich und praxisbezogen sein
- Für Multiple-Choice: 4 Antwortoptionen mit einer korrekten Antwort
- Für offene Fragen: Klare Fragestellung mit Bewertungskriterien

WICHTIG für Code-Formatierung:
- Code-Elemente (Funktionsnamen, Variablen, Klassen, Code-Snippets) MÜSSEN in Backticks gesetzt werden
- Beispiel: `self._distribute_elements(arr)` statt self._distribute_elements(arr)
- Dies gilt für Fragen, Optionen und Erklärungen

Format als JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "single_choice",
      "question": "Fragetext hier (Code in `backticks`)",
      "options": ["Option A (Code in `backticks`)", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A (Code in `backticks`)",
      "explanation": "Erklärung warum diese Antwort korrekt ist (Code in `backticks`)",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }},
    {{
      "id": "q2",
      "type": "open_ended",
      "question": "Offene Fragestellung hier",
      "options": null,
      "correct_answer": null,
      "explanation": "Bewertungskriterien und Musterlösung",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }}
  ]
}}

Wichtig: Antworte nur mit dem JSON, keine zusätzlichen Erklärungen.
"""
        return prompt


_claude_service_instance = None


def get_claude_service() -> "ClaudeService":
    global _claude_service_instance
    if _claude_service_instance is None:
        _claude_service_instance = ClaudeService()
    return _claude_service_instance


async def validate_claude_model_on_startup() -> None:
    """Startup hook, wired into the FastAPI lifespan and Celery worker boot.

    TF-440: the legacy Models API validation chain (curated fallback chain,
    ``GET /v1/models/{id}``) was removed — the Gateway (LiteLLM) has its
    own health/fallback mechanics. A retired model is fixed there via a
    one-line config edit instead of an app-side chain here (TF-437/438).
    Remains as a lean no-op hook for the existing call sites and never
    crashes startup.
    """
    if not llm_gateway.gateway_enabled():
        logger.warning(
            "Claude model startup validation skipped: LLM_GATEWAY_URL not "
            "configured (demo mode)"
        )
        return

    logger.info(
        "Claude model startup validation skipped (Gateway aktiv; Gateway "
        "besitzt eigene Health/Fallback) — TF-440"
    )
