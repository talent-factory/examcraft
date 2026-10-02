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

import logging
import os
import threading

import httpx

from services.llm_pii import AsyncRedactingTransport, RedactingTransport

logger = logging.getLogger(__name__)


# Logische Aliase (siehe Gateway-config.yaml + Virtual-Key-Allowlist).
ALIAS_GENERATION = "examcraft/generation"
ALIAS_GRADING = "examcraft/grading"
ALIAS_EMBEDDING = "tf/embedding-small"
ALIAS_CHAT = "examcraft/chat"
ALIAS_WIZARD = "examcraft/wizard"

# TF-941 (Epic 3, portfolio assessment): dedicated alias instead of reusing
# ALIAS_GRADING -- classification (many small file->phase calls per
# assessment) and the holistic criteria grading (Epic 4, few but expensive
# calls) have different cost/quality requirements and should be routable
# independently on the gateway.
ALIAS_PORTFOLIO_CLASSIFICATION = "examcraft/portfolio-classification"

# Epic 4 (portfolio assessment, grading engine): its own alias instead of
# reusing ALIAS_GRADING or ALIAS_PORTFOLIO_CLASSIFICATION -- the holistic
# criteria grading (few but expensive calls, large prompt context) has
# different cost/quality requirements than both regular free-text grading
# and the many small classification calls, and should be routable
# independently on the gateway.
ALIAS_PORTFOLIO_GRADING = "examcraft/portfolio-grading"

# Every alias above must be in the Virtual Key's model scope; otherwise the
# gateway answers 403 key_model_access_denied (TF-999). Checked at startup by
# ``log_key_alias_scope``.
REQUIRED_ALIASES = (
    ALIAS_GENERATION,
    ALIAS_GRADING,
    ALIAS_EMBEDDING,
    ALIAS_CHAT,
    ALIAS_WIZARD,
    ALIAS_PORTFOLIO_CLASSIFICATION,
    ALIAS_PORTFOLIO_GRADING,
)

# LiteLLM: an empty model list or this wildcard means "all models allowed".
_UNRESTRICTED_SCOPE = "all-proxy-models"

_last_key_scope: dict = {"status": "pending", "missing_aliases": []}


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


def gateway_portfolio_grading_timeout() -> float:
    """Request timeout (seconds) specifically for portfolio grading (Epic 4).

    Grading prompts can be up to 300'000 characters (MAX_CHARS_PER_PHASE_PROMPT)
    plus up to 12'000 output tokens -- much larger than the short
    classification/grading calls that gateway_timeout()/
    gateway_generation_timeout() are calibrated for. Without its own,
    larger time budget a large phase could never be graded successfully: a
    timeout marks the phase as failed, and a resume attempt hits exactly
    the same timeout again.

    PR review (Epic 4): worst case per phase is 2 sequential calls (the
    task's own semantic-validation retry, portfolio_grading_tasks.py) at
    this timeout each = 600 s, NOT the request-level timeout alone -- TWO
    separate retry knobs at the one call site that uses this timeout must
    both be pinned to 0, or either one silently multiplies that figure:
    ``make_pydantic_model(..., max_retries=0)`` (OpenAI SDK's own
    client-level retry, default 2, i.e. up to 3x per request) AND
    ``Agent(..., output_retries=0)`` (pydantic-ai's own retry-on-invalid-
    output, default 1, i.e. up to 2x per call). _GRADING_TIME_BUDGET_SECONDS
    (portfolio_grading_tasks.py) must stay low enough that budget + 600 s
    leaves a safe margin under Celery's task_soft_time_limit (3300 s,
    celery_app.py).
    """
    return float(os.getenv("LLM_GATEWAY_PORTFOLIO_GRADING_TIMEOUT", "300.0"))


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


def _network_transport() -> httpx.BaseTransport:
    """Real network layer below the redacting transport (patched in tests)."""
    return httpx.HTTPTransport()


def _async_network_transport() -> httpx.AsyncBaseTransport:
    """Async counterpart of ``_network_transport``."""
    return httpx.AsyncHTTPTransport()


def make_openai_client():
    """OpenAI-SDK-Client gegen den Gateway (Grading + Embeddings).

    Setzt ein Default-Timeout (``gateway_timeout``), damit kein Call-Site
    auf dem ~600-s-SDK-Default einen Celery-Worker blockiert; engere
    Per-Call-Overrides (z. B. Grading) bleiben möglich.

    Every request passes ``RedactingTransport`` (TF-749): e-mail addresses
    and AHV numbers are removed from prompts and embedding inputs before
    they leave ExamCraft.
    """
    from openai import DefaultHttpxClient, OpenAI

    return OpenAI(
        base_url=gateway_base_url(),
        api_key=_require_gateway_key(),
        timeout=gateway_timeout(),
        http_client=DefaultHttpxClient(
            transport=RedactingTransport(_network_transport())
        ),
    )


def make_pydantic_model(
    alias: str, timeout: float | None = None, max_retries: int | None = None
):
    """PydanticAI-Modell gegen den Gateway (Generierung, Chatbot, Wizard).

    Der Provider erhält einen ``AsyncOpenAI``-Client mit Default-Timeout,
    damit auch Generierung/Chat/Wizard nicht unbegrenzt auf einem
    hängenden Gateway warten (TF-439 „Fix 2", einheitlich für alle Pfade).

    ``timeout`` überschreibt ``gateway_timeout()`` für Call-Sites mit
    abweichendem Zeitbudget (TF-593: Fragengenerierung braucht bei langen
    Custom-Prompts mehr als die 30-s-Default-Schranke).

    ``max_retries`` überschreibt den OpenAI-SDK-Default (2, d. h. bis zu 3x
    pro Request) für Call-Sites, deren eigenes Zeitbudget einen
    ungebremsten Client-Retry nicht verträgt (PR review, Epic 4: siehe
    ``gateway_portfolio_grading_timeout``'s Docstring für die Rechnung).
    ``None`` behält den SDK-Default bei, um bestehende Call-Sites
    unverändert zu lassen.

    Requests pass ``AsyncRedactingTransport`` (TF-749), as in
    ``make_openai_client``.
    """
    from openai import AsyncOpenAI, DefaultAsyncHttpxClient
    from pydantic_ai.models.openai import OpenAIChatModel
    from pydantic_ai.providers.openai import OpenAIProvider

    client_kwargs = {
        "base_url": gateway_base_url(),
        "api_key": _require_gateway_key(),
        "timeout": timeout if timeout is not None else gateway_timeout(),
        "http_client": DefaultAsyncHttpxClient(
            transport=AsyncRedactingTransport(_async_network_transport())
        ),
    }
    if max_retries is not None:
        client_kwargs["max_retries"] = max_retries
    client = AsyncOpenAI(**client_kwargs)
    return OpenAIChatModel(alias, provider=OpenAIProvider(openai_client=client))


def _key_scope_result(status: str, missing: list[str] | None = None) -> dict:
    return {"status": status, "missing_aliases": missing or []}


def check_key_alias_scope(
    *, timeout: float = 5.0, transport: httpx.BaseTransport | None = None
) -> dict:
    """Compare ``REQUIRED_ALIASES`` against the Virtual Key's scope (TF-999).

    Reads ``GET /key/info`` with the key itself (read-only, no master key
    needed). Never raises: an unreachable gateway yields ``unreachable`` so
    the caller can continue (fail-open, like the TF-438 startup hook).
    ``transport`` exists for tests (``httpx.MockTransport``).
    """
    if not gateway_enabled() or not gateway_api_key():
        return _key_scope_result("not_configured")

    root = gateway_base_url().removesuffix("/v1")
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.get(
                f"{root}/key/info",
                headers={"Authorization": f"Bearer {gateway_api_key()}"},
            )
    except httpx.HTTPError:
        return _key_scope_result("unreachable")

    if response.status_code >= 500 or response.status_code == 429:
        return _key_scope_result("unreachable")
    if response.status_code in (401, 403):
        return _key_scope_result("key_rejected")
    try:
        response.raise_for_status()
        models = response.json()["info"].get("models") or []
    except (httpx.HTTPError, ValueError, KeyError, TypeError, AttributeError):
        return _key_scope_result("unknown")

    if not models or _UNRESTRICTED_SCOPE in models:
        return _key_scope_result("ok")
    missing = [alias for alias in REQUIRED_ALIASES if alias not in models]
    return _key_scope_result("missing_aliases" if missing else "ok", missing)


def log_key_alias_scope(**kwargs) -> dict:
    """Startup hook: run ``check_key_alias_scope``, log and cache the result.

    Missing aliases or a rejected key are logged as errors (the affected
    features fail with 403/401 on every call); an unreachable gateway only
    warns. The cached result is reported by ``/api/v1/health``.
    """
    global _last_key_scope
    result = check_key_alias_scope(**kwargs)
    _last_key_scope = result

    status = result["status"]
    if status == "missing_aliases":
        logger.error(
            "LLM gateway key lacks aliases %s — calls to them fail with 403 "
            "key_model_access_denied. Extend the Virtual Key's scope via "
            "/key/update (TF-999).",
            ", ".join(result["missing_aliases"]),
        )
    elif status == "key_rejected":
        logger.error(
            "LLM gateway rejected LLM_GATEWAY_API_KEY on /key/info — all "
            "LLM calls will fail (TF-999)."
        )
    elif status in ("unreachable", "unknown"):
        logger.warning(
            "LLM gateway key scope check skipped (%s) — aliases not verified (TF-999).",
            status,
        )
    elif status == "ok":
        logger.info("LLM gateway key scope covers all ExamCraft aliases")
    return result


def last_key_alias_scope() -> dict:
    """Result of the last ``log_key_alias_scope`` run (``pending`` before)."""
    return dict(_last_key_scope)


def start_key_alias_scope_check() -> threading.Thread:
    """Run ``log_key_alias_scope`` in a daemon thread.

    Startup must not wait for the gateway: with an unreachable gateway the
    check would otherwise hold the FastAPI lifespan / worker boot for the
    full timeout.
    """
    thread = threading.Thread(
        target=log_key_alias_scope, name="llm-gateway-key-scope", daemon=True
    )
    thread.start()
    return thread
