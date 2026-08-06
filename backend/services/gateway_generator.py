# core/backend/services/gateway_generator.py
"""Fragengenerierung über den LLM-Gateway mit typisiertem Output (TF-439).

Ersetzt das brüchige Regex-/JSON-Parsing aus
``claude_service._parse_claude_response`` durch PydanticAI ``output_type``.
Wird nur betreten, wenn ``llm_gateway.gateway_enabled()`` True ist; der
Legacy-httpx-Pfad in ``ClaudeService`` bleibt für den Rollback erhalten.
"""

from __future__ import annotations

import logging
from typing import List, NoReturn, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError

from services import llm_gateway
from services.claude_service import ModelUnavailableError

logger = logging.getLogger(__name__)


class GeneratedQuestion(BaseModel):
    """Eine generierte Prüfungsfrage (entspricht dem bisherigen JSON-Shape)."""

    id: str
    type: str
    question: str
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[str] = None
    topic: Optional[str] = None


class GeneratedQuestions(BaseModel):
    questions: List[GeneratedQuestion] = Field(default_factory=list)


def _build_agent(output_type):
    """Agent gegen den Gateway-Generierungs-Alias bauen.

    TF-593: nutzt ``gateway_generation_timeout()`` (120 s) statt des
    generischen 30-s-``gateway_timeout()`` — lange Custom-Prompts (z. B.
    Freitextfragen mit Musterlösung + Bewertungsraster + Kompetenz-
    Zuordnung) brauchen regelmässig mehr als 30 s und liefen sonst in
    Timeout → interner Retry → Celery-Task-Retry, sichtbar als
    minutenlanges Hängen bei "Context geladen" im Fortschrittsbalken.
    """
    model = llm_gateway.make_pydantic_model(
        llm_gateway.ALIAS_GENERATION, timeout=llm_gateway.gateway_generation_timeout()
    )
    return Agent(model, output_type=output_type)


def _reraise_classified(exc: ModelHTTPError) -> NoReturn:
    """TF-438: 4xx (ausser 429) ⇒ permanent; sonst transient durchreichen."""
    if llm_gateway.is_permanent_status(exc.status_code):
        raise ModelUnavailableError(
            f"Gateway-Modell '{llm_gateway.ALIAS_GENERATION}' lieferte "
            f"{exc.status_code}: {exc}"
        ) from exc
    raise exc


async def generate_questions_via_gateway(prompt: str) -> list[dict]:
    """Typisierte Generierung; Rückgabe als Liste von Dicts (wie Legacy)."""
    agent = _build_agent(GeneratedQuestions)
    try:
        result = await agent.run(prompt)
    except ModelHTTPError as exc:
        _reraise_classified(exc)
    return [q.model_dump() for q in result.output.questions]


async def generate_raw_via_gateway(prompt: str) -> str:
    """Plaintext-Lauf für Custom-Prompts (Markdown-Fallback bleibt erhalten)."""
    agent = _build_agent(str)
    try:
        result = await agent.run(prompt)
    except ModelHTTPError as exc:
        _reraise_classified(exc)
    return result.output
