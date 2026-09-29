"""
Structured RAG generation errors with stable codes (TF-358).

Analogous to :mod:`services.document_errors`: instead of interpreting raw
English error texts by substring, the exceptions carry a stable,
machine-readable ``code``. The WebSocket endpoint (`api/v1/websocket.py`)
maps this code to a safe, actionable user message and an API error
code — robust against localization or rewording of the raw message.

Important cross-tier architecture note: this file lives in ``core/``
(not ``premium/``), so BOTH processes can import it — the Celery worker
(`premium/.../rag_service.py` raises the exception) AND the API process
(`core/.../websocket.py` reads it from the Celery result). Celery can
only faithfully reconstruct the exception type if the class is
importable in both processes; otherwise it degrades to a generic
exception (only the message survives). The WebSocket mapper therefore
also keeps a substring fallback.

Codes are stable snake_case identifiers — never localize them, never
silently reinterpret them. Extend with new codes additively.
"""

from typing import Any, Dict, NamedTuple

from services.translation_service import DEFAULT_LOCALE, t

# ---------------------------------------------------------------------------
# Stable, machine-readable error codes. Extend additively; never reinterpret.
# ---------------------------------------------------------------------------

NO_CONTEXT = "no_context"
"""RAG retrieval returned no usable context for (at least) one question
or the whole topic — the selected documents are too short / not
indexed."""

UNKNOWN_QUESTION_TYPE = "unknown_question_type"
"""Requested question type has no template / is not supported."""


class RAGGenerationError(ValueError):
    """ValueError subclass carrying a stable ``code`` (+ optional ``details``).

    Inherits from ``ValueError`` so existing ``except ValueError`` / tests
    (`pytest.raises(ValueError, ...)`) still work unchanged.

    Args:
        message: Human-readable (English) message — goes into logs/result.
        **details: Optional structured diagnostics (e.g. ``question_type=...``).
    """

    code: str = "rag_generation_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.details: Dict[str, Any] = dict(details)


class NoContextError(RAGGenerationError):
    """No usable RAG context for question generation."""

    code = NO_CONTEXT


class UnknownQuestionTypeError(RAGGenerationError):
    """Unsupported question type."""

    code = UNKNOWN_QUESTION_TYPE


# ---------------------------------------------------------------------------
# TF-608: shared mapper task exception → safe user message.
#
# Lives here (instead of locally in a single endpoint) so both the
# WebSocket stream (`api/v1/websocket.py`) and the REST recovery
# endpoint (`GET /rag/tasks/{id}/result`, `api/rag_exams.py`) use the
# exact same TF-358 sanitization. One of the two spots previously
# returned ``str(exception)`` raw to the client — exactly the leak this
# mapper is meant to prevent.
#
# TF-967: the mapper returns an API error code (ADR 0005) next to the
# German text. The code is the locale key; the frontend renders it in the
# user's language, and the German text only remains as ``error`` for
# clients that do not know the code yet. These are public API codes and
# deliberately differ from the internal exception codes above
# (``NO_CONTEXT`` → ``TASK_NO_CONTEXT``).
# ---------------------------------------------------------------------------

TASK_FAILED = "rag_task_failed"
"""Generic fallback for unknown task errors. Deliberately uninformative to
the user, to avoid leaking internal details/PII."""

TASK_NO_CONTEXT = "rag_task_no_context"
TASK_UNKNOWN_QUESTION_TYPE = "rag_task_unknown_question_type"

# Raised by the WebSocket stream itself, not mapped from a task exception.
TASK_STATUS_UNAVAILABLE = "rag_task_status_unavailable"
TASK_PENDING_TIMEOUT = "rag_task_pending_timeout"
TASK_STREAM_ERROR = "rag_task_stream_error"


class UserFacingTaskError(NamedTuple):
    """API error code plus its German text, the latter for the ``error`` field."""

    code: str
    message: str


def user_facing_task_error(raw_info: Any) -> UserFacingTaskError:
    """Map a (technical) task exception to a safe, actionable user message
    (TF-358) and its error code (TF-967).

    The real error must be logged server-side by the caller — it is
    NOT passed through to the user here. Only explicitly known error
    classes get a concrete message; everything else falls back to
    ``TASK_FAILED``, so no internal details or personal data reach the
    client. Callers detect that fallback by the code, not by the text.

    Matching is primarily via the stable ``code`` of the RAG errors
    above — robust against rewording/localization. The substring
    fallback kicks in if Celery lost the exception type during
    serialization and only the raw message survives.
    """
    code = getattr(raw_info, "code", None)
    text = str(raw_info or "").lower()

    if (
        code == NO_CONTEXT
        or "no context available" in text
        or "no relevant context found" in text
    ):
        api_code = TASK_NO_CONTEXT
    elif code == UNKNOWN_QUESTION_TYPE or "unknown question type" in text:
        api_code = TASK_UNKNOWN_QUESTION_TYPE
    else:
        api_code = TASK_FAILED

    return UserFacingTaskError(api_code, t(api_code, DEFAULT_LOCALE))
