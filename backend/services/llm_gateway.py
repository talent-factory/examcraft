# core/backend/services/llm_gateway.py
"""Zentrale Anbindung an den self-hosted LLM-Gateway (LiteLLM, TF-439/440).

Der Gateway ist die einzige Quelle für Modell-Routing (TF-440: der frühere
Legacy-Provider-Direktpfad, der bei leerem ``LLM_GATEWAY_URL`` griff, wurde
aus allen Call-Sites entfernt). ``LLM_GATEWAY_URL`` ist jetzt Pflicht für
echten Betrieb — ist sie leer, laufen Generierung, Grading, Embeddings,
Chatbot und Wizard im jeweiligen ``demo_mode``/Fail-Fast statt in einem
Provider-Fallback.

Logische Aliase statt roher Modell-IDs: ein zurückgezogenes Modell wird
zum 1-Zeilen-Config-Edit am Gateway statt zum App-Incident (TF-437/438).
"""

from __future__ import annotations

import os


# Logische Aliase (siehe Gateway-config.yaml + Virtual-Key-Allowlist).
ALIAS_GENERATION = "examcraft/generation"
ALIAS_GRADING = "examcraft/grading"
ALIAS_EMBEDDING = "tf/embedding-small"
ALIAS_CHAT = "examcraft/chat"
ALIAS_WIZARD = "examcraft/wizard"


def gateway_enabled() -> bool:
    """True, wenn der Gateway-Pfad aktiv ist (Rollback = Variable leeren)."""
    return bool(os.getenv("LLM_GATEWAY_URL", "").strip())


def gateway_base_url() -> str:
    """Basis-URL inkl. ``/v1`` für OpenAI-kompatible Clients/Provider.

    Idempotent: endet ``LLM_GATEWAY_URL`` bereits auf ``/v1``, wird
    kein zweites ``/v1`` angehängt (Operator-Footgun-Schutz).
    """
    raw = os.getenv("LLM_GATEWAY_URL", "").strip().rstrip("/")
    if raw.endswith("/v1"):
        return raw
    return f"{raw}/v1"


def gateway_api_key() -> str:
    """Virtual Key des Projekts (Fly-Secret ``LLM_GATEWAY_API_KEY``)."""
    return os.getenv("LLM_GATEWAY_API_KEY", "").strip()


def gateway_timeout() -> float:
    """Request-Timeout (Sekunden) für alle Gateway-Clients.

    Ohne expliziten Wert blockiert der OpenAI-SDK-Default (~600 s) bei
    hängendem Gateway einen Celery-Worker. 30 s ist die gleiche Schranke
    wie im Grading-Pfad (TF-439 „Fix 2"); pro Call-Site überschreibbar
    (siehe ``make_pydantic_model``/``make_openai_client``'s ``timeout``-Param,
    z. B. ``gateway_generation_timeout`` für die Fragengenerierung).
    """
    return float(os.getenv("LLM_GATEWAY_TIMEOUT", "30.0"))


def gateway_generation_timeout() -> float:
    """Request-Timeout (Sekunden) speziell für die Fragengenerierung (TF-593).

    30 s (``gateway_timeout``) reicht für kurze Calls (Grading, Embeddings,
    Chat/Wizard-Turns), ist aber für lange, gut ausgearbeitete Custom-Prompts
    (z. B. Freitextfragen mit Musterlösung + Bewertungsraster + Kompetenz-
    Zuordnung, >20k Zeichen) zu knapp — Claude braucht dafür regelmässig
    länger, der Call timet aus, retryt intern und lässt danach den ganzen
    Celery-Task (bis zu 4× mit 30-300 s Backoff) neu anlaufen. 120 s deckt
    sich mit dem Timeout des Legacy-Direktpfads (``ClaudeService``) für
    exakt denselben Call.
    """
    return float(os.getenv("LLM_GATEWAY_GENERATION_TIMEOUT", "120.0"))


def _require_gateway_key() -> str:
    """Virtual Key oder fail-fast — kein leerer ``Bearer`` an den Gateway.

    Ein leerer Key liesse den OpenAI-SDK still ``Authorization: Bearer``
    senden (oder versehentlich ``OPENAI_API_KEY`` aus der Umgebung ziehen)
    und endete in einem verwirrenden 401. Lieber laut bei Konstruktion.
    """
    key = gateway_api_key()
    if not key:
        raise RuntimeError(
            "LLM_GATEWAY_API_KEY fehlt — der Gateway erwartet einen Virtual "
            "Key (fail-fast statt eines verwirrenden 401)."
        )
    return key


def is_permanent_status(status_code: int) -> bool:
    """TF-438-Klassifizierung: 4xx (ausser 429) ist permanent (kein Retry).

    Permanent => Caller wirft ``ModelUnavailableError`` und failt schnell,
    statt wie im TF-437-Incident endlos zu wiederholen. 429 sowie 5xx /
    Timeout / ConnError sind transient und bleiben retrybar.
    """
    return 400 <= status_code < 500 and status_code != 429


def make_openai_client():
    """OpenAI-SDK-Client gegen den Gateway (Grading + Embeddings).

    Setzt ein Default-Timeout (``gateway_timeout``), damit kein Call-Site
    auf dem ~600-s-SDK-Default einen Celery-Worker blockiert; engere
    Per-Call-Overrides (z. B. Grading) bleiben möglich.
    """
    from openai import OpenAI

    return OpenAI(
        base_url=gateway_base_url(),
        api_key=_require_gateway_key(),
        timeout=gateway_timeout(),
    )


def make_pydantic_model(alias: str, timeout: float | None = None):
    """PydanticAI-Modell gegen den Gateway (Generierung, Chatbot, Wizard).

    Der Provider erhält einen ``AsyncOpenAI``-Client mit Default-Timeout,
    damit auch Generierung/Chat/Wizard nicht unbegrenzt auf einem
    hängenden Gateway warten (TF-439 „Fix 2", einheitlich für alle Pfade).

    ``timeout`` überschreibt ``gateway_timeout()`` für Call-Sites mit
    abweichendem Zeitbudget (TF-593: Fragengenerierung braucht bei langen
    Custom-Prompts mehr als die 30-s-Default-Schranke).
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    client = AsyncOpenAI(
        base_url=gateway_base_url(),
        api_key=_require_gateway_key(),
        timeout=timeout if timeout is not None else gateway_timeout(),
    )
    return OpenAIChatModel(alias, provider=OpenAIProvider(openai_client=client))
