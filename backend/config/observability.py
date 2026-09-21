"""
Observability Configuration for ExamCraft Backend (TF-865)

Replaces the retired Sentry integration (`config/sentry.py`) with
specula-client-python: OpenTelemetry traces (FastAPI + Celery) and
structured log forwarding to the shared Specula collector. Only enabled in
staging and production, like the Sentry setup it replaces.

Two consumers call into this module, each with their own service name:
- ``main.py`` (FastAPI process) -> ``init_observability()`` + ``instrument_app()``
- ``celery_app.py`` (worker process) -> ``init_worker_observability()``

Fail-open by design, on three independent axes:
- Package-fail-open: ``specula_client`` is a private, not-yet-on-PyPI package
  (see ``requirements.txt``'s comment on the git dependency) -- it is only
  installed when a ``GITHUB_TOKEN`` build secret is supplied (private/full
  builds; see ``Dockerfile``). A public/OSS build of ``core/`` has no access
  to that secret, so this module must import and this whole file's public API
  must work (as a no-op) even when ``specula_client`` itself isn't installed
  -- core/ must never hard-depend on proprietary code.
- Config-fail-open: ``specula_client.init_tracing()``/``instrument_fastapi_app()``
  already guarantee a missing/unreachable collector never prevents the
  calling process from starting (mirrors the old Sentry setup's own
  try/except-free reliance on the SDK being similarly forgiving).
- Call-fail-open: unlike the old setup, ``_init()``/``instrument_app()`` wrap
  their calls into ``specula_client`` in a broad ``try/except`` here. That
  package is a brand-new (v0.1.0, TF-852) internal dependency with no
  production track record yet -- an exception raised during init (bad
  endpoint URL, DNS failure, ...) must degrade to "observability disabled"
  and a loud log line, not take the whole API/worker process down with it.
"""

import logging
import os

from opentelemetry import trace

logger = logging.getLogger(__name__)

try:
    from specula_client import (
        SpeculaLogHandler,
        init_tracing,
        instrument_fastapi_app,
        scrub_pii,
    )

    SPECULA_CLIENT_AVAILABLE = True
except ImportError:
    # Expected on a public/OSS build without GITHUB_TOKEN access to the
    # private specula-client-python repo (see module docstring) -- not an
    # error, just "this build has no observability backend available".
    SPECULA_CLIENT_AVAILABLE = False
    SpeculaLogHandler = init_tracing = instrument_fastapi_app = scrub_pii = None

SERVICE_NAME_API = "examcraft-backend"
SERVICE_NAME_WORKER = "examcraft-celery"

# TF-758 carryover, kept explicit for readability/self-documentation: these
# three fields are already covered by specula_client's DEFAULT_DENYLIST via
# its "password" substring match (unlike the retired sentry_sdk EventScrubber,
# which matched key names exactly and therefore genuinely needed this
# extension -- see the retired config/sentry.py). Listing them here is
# defense-in-depth against DEFAULT_DENYLIST ever narrowing upstream, not a
# functional requirement today. Shared with middleware/observability_context.py
# so both call sites use the same list.
EXTRA_PII_DENYLIST = ["admin_password", "current_password", "new_password"]


def _otel_config() -> tuple[str | None, str | None]:
    return os.getenv("OTEL_EXPORTER_ENDPOINT"), os.getenv("SPECULA_TEAM_API_KEY")


def _attach_log_handler(service_name: str, environment: str, release: str) -> None:
    endpoint, team_api_key = _otel_config()
    handler = SpeculaLogHandler(
        endpoint=endpoint,
        team_api_key=team_api_key,
        service_name=service_name,
        deployment_environment=environment,
        release_tag=release,
    )
    # ERROR rather than INFO/WARNING: mirrors event_level=logging.ERROR from
    # the retired sentry_sdk LoggingIntegration setup (only ERROR+ was sent
    # there as a standalone event; INFO was attached to an event only as a
    # breadcrumb -- a concept SpeculaLogHandler doesn't have, since it
    # forwards every record individually).
    handler.setLevel(logging.ERROR)
    root_logger = logging.getLogger()
    # Guard against double-registration: _init() can run twice in the same
    # process (e.g. main.py imported under two different module identities,
    # see the TF-660 dual-module gotcha), which would otherwise duplicate
    # every forwarded ERROR record.
    if not any(isinstance(h, SpeculaLogHandler) for h in root_logger.handlers):
        root_logger.addHandler(handler)


def _init(service_name: str, *, instrument_celery: bool) -> None:
    """Initialize traces + log forwarding for one process (API or worker).

    Only initializes if both ``OTEL_EXPORTER_ENDPOINT`` and
    ``SPECULA_TEAM_API_KEY`` are set (``init_tracing()`` no-ops otherwise
    anyway; the loud log below exists so a misconfigured deploy is caught
    before it is missed silently -- see the "TF-359 carryover" note).
    """
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("APP_VERSION", "unknown")
    endpoint, team_api_key = _otel_config()

    if not (SPECULA_CLIENT_AVAILABLE and endpoint and team_api_key):
        # TF-359 carryover: surface a disabled-in-prod state loudly -- but
        # only for an actual misconfiguration (package installed, env vars
        # missing). A public/OSS build where specula_client was never
        # installed in the first place (package-fail-open, see module
        # docstring) is an expected, not a misconfigured, state and stays at
        # INFO regardless of environment. Under uvicorn/celery the root
        # logger sits at WARNING, so an INFO line would be invisible exactly
        # where a misconfigured OTEL_EXPORTER_ENDPOINT/SPECULA_TEAM_API_KEY
        # matters most.
        level = (
            logging.WARNING
            if SPECULA_CLIENT_AVAILABLE and environment in ("staging", "production")
            else logging.INFO
        )
        logging.log(
            level,
            f"[Observability] Disabled in {environment} "
            f"(specula_client_available={SPECULA_CLIENT_AVAILABLE}, "
            f"otel_exporter_endpoint_set={bool(endpoint)}, "
            f"specula_team_api_key_set={bool(team_api_key)})",
        )
        return

    try:
        init_tracing(
            service_name=service_name,
            otel_exporter_endpoint=endpoint,
            specula_team_api_key=team_api_key,
            # Performance Monitoring
            # Sample 100% of transactions in development, 10% in production
            sample_rate=1.0 if environment == "development" else 0.1,
            environment=environment,
            release=release,
            instrument_celery=instrument_celery,
        )
        _attach_log_handler(service_name, environment, release)
    except Exception:
        # Call-fail-open (see module docstring): a broken observability
        # dependency must never be the reason the API/worker process fails to
        # boot. logger.critical (not .exception, no live span/handler yet to
        # forward it) so this is still loud wherever stdout/stderr is
        # collected, even with observability itself down.
        logger.critical(
            f"[Observability] Failed to initialize for {environment} "
            f"(service={service_name}) -- continuing without tracing/log "
            "forwarding",
            exc_info=True,
        )
        return

    logger.info(
        f"[Observability] Initialized for {environment} with version {release} "
        f"(service={service_name})"
    )


def init_observability() -> None:
    """Initialize traces + log forwarding for the FastAPI process.

    Must be called before the ``FastAPI`` app is constructed (mirrors the
    retired ``init_sentry()`` call site in ``main.py``).
    """
    _init(SERVICE_NAME_API, instrument_celery=False)


def init_worker_observability() -> None:
    """Initialize traces + log forwarding + Celery instrumentation for the worker.

    Called from ``celery_app.py``'s ``celeryd_init`` signal handler -- the
    fork-safe entry point, before the prefork pool spawns children.
    """
    _init(SERVICE_NAME_WORKER, instrument_celery=True)


def instrument_app(app) -> None:
    """Instrument the constructed FastAPI app for request traces. No-op if disabled.

    Kept separate from ``init_observability()`` for the same reason
    ``specula_client.instrument_fastapi_app()`` is separate from
    ``init_tracing()``: it needs the already-constructed ``FastAPI`` instance.

    Explicitly gated on the same config as ``_init()`` (unlike relying solely
    on ``instrument_fastapi_app()``'s own no-op-when-unset contract, which is
    unverified from this repo -- see module docstring) so a disabled
    deployment never even attempts the call.
    """
    endpoint, team_api_key = _otel_config()
    if not (SPECULA_CLIENT_AVAILABLE and endpoint and team_api_key):
        return
    try:
        instrument_fastapi_app(
            app, otel_exporter_endpoint=endpoint, specula_team_api_key=team_api_key
        )
    except Exception:
        logger.critical(
            "[Observability] Failed to instrument FastAPI app -- continuing "
            "without request tracing",
            exc_info=True,
        )


def set_span_tag(key: str, value: object) -> None:
    """Attach a key/value attribute to the currently active OTel span.

    OTel equivalent of the retired ``sentry_sdk.set_tag()``. No-op outside an
    active span (e.g. tracing disabled, or no instrumented context such as a
    Celery task run without ``instrument_celery=True``): ``get_current_span()``
    then returns an ``INVALID_SPAN`` whose ``set_attribute()`` is a safe no-op.
    """
    try:
        str_value = str(value)
    except Exception:
        str_value = "<unrepresentable value>"
    trace.get_current_span().set_attribute(key, str_value)


def record_exception(
    exception: Exception,
    *,
    tags: dict | None = None,
    extra_context: dict | None = None,
) -> None:
    """Record an exception on the currently active OTel span.

    OTel equivalent of the retired ``capture_exception_with_context()``: no
    active span (see ``set_span_tag()``) means this is a safe no-op instead of
    raising.

    ``tags``/``extra_context`` are scrubbed through the same PII denylist as
    ``middleware/observability_context.py``'s request-context attributes --
    unlike the retired Sentry setup, where a single global
    ``EventScrubber(denylist=...)`` covered every field on every event
    regardless of call site, individual span attributes here are only ever as
    safe as the call site that set them. Scrubbing centrally in this function
    (rather than trusting every future caller to scrub before calling) keeps
    that guarantee.
    """
    span = trace.get_current_span()
    span.record_exception(exception)

    if not SPECULA_CLIENT_AVAILABLE:
        # Package-fail-open (see module docstring): no scrub_pii() to run
        # tags/extra_context through, and no exporter for them to reach
        # anyway (instrument_app()/_init() are no-ops too in this case) --
        # skip silently rather than warning on every call in what is an
        # expected state for a public/OSS build.
        return

    try:
        scrubbed_tags = scrub_pii(dict(tags or {}), extra_denylist=EXTRA_PII_DENYLIST)
        scrubbed_extra = scrub_pii(
            dict(extra_context or {}), extra_denylist=EXTRA_PII_DENYLIST
        )
    except (TypeError, ValueError):
        # scrub_pii() fails closed on an unsupported value type or a circular
        # reference (see specula_client.scrubbing); this helper must still be
        # a safe no-op for the caller, so drop the offending dict entirely
        # rather than either raising or (worse) falling back to the
        # unscrubbed original.
        logger.warning(
            "[Observability] record_exception(): tags/extra_context could "
            "not be scrubbed, dropping both instead of risking a PII leak",
            exc_info=True,
        )
        return

    for key, value in scrubbed_tags.items():
        set_span_tag(key, value)
    for key, value in scrubbed_extra.items():
        set_span_tag(f"extra.{key}", value)
