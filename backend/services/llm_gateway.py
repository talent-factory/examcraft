# core/backend/services/llm_gateway.py
"""Zentrale Anbindung an den self-hosted LLM-Gateway (LiteLLM, TF-439).

Einzige Quelle der Wahrheit für den globalen Rollback-Schalter
``LLM_GATEWAY_URL``: ist die Variable leer, laufen ALLE Call-Sites auf
dem Legacy-Provider-Direktpfad. Ist sie gesetzt, routen Generierung,
Grading, Embeddings, Chatbot und Wizard über den Gateway (OpenAI-Wire).

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
    wie im Grading-Pfad (TF-439 „Fix 2"); pro Call-Site überschreibbar.
    """
    return float(os.getenv("LLM_GATEWAY_TIMEOUT", "30.0"))


def _require_gateway_key() -> str:
    """Virtual Key oder fail-fast — kein leerer ``Bearer`` an den Gateway.

    Ein leerer Key liesse den OpenAI-SDK still ``Authorization: Bearer``
    senden (oder versehentlich ``OPENAI_API_KEY`` aus der Umgebung ziehen)
    und endete in einem verwirrenden 401. Lieber laut bei Konstruktion.
    """
    key = gateway_api_key()
    if not key:
        raise RuntimeError(
            "LLM_GATEWAY_URL ist gesetzt, aber LLM_GATEWAY_API_KEY fehlt — "
            "der Gateway erwartet einen Virtual Key (fail-fast statt 401)."
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


def make_pydantic_model(alias: str):
    """PydanticAI-Modell gegen den Gateway (Generierung, Chatbot, Wizard).

    Der Provider erhält einen ``AsyncOpenAI``-Client mit Default-Timeout,
    damit auch Generierung/Chat/Wizard nicht unbegrenzt auf einem
    hängenden Gateway warten (TF-439 „Fix 2", einheitlich für alle Pfade).
    """
    from openai import AsyncOpenAI
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    client = AsyncOpenAI(
        base_url=gateway_base_url(),
        api_key=_require_gateway_key(),
        timeout=gateway_timeout(),
    )
    return OpenAIChatModel(alias, provider=OpenAIProvider(openai_client=client))
