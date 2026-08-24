"""
Structured RAG generation errors with stable codes (TF-358).

Analogous to :mod:`services.document_errors`: instead of interpreting raw
English error texts by substring, the exceptions carry a stable,
machine-readable ``code``. The WebSocket endpoint (`api/v1/websocket.py`)
maps this code to a safe, actionable German user message — robust
against localization or rewording of the raw message.

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

from typing import Any, Dict

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
# ---------------------------------------------------------------------------

GENERIC_TASK_ERROR = "Verarbeitung fehlgeschlagen. Bitte erneut versuchen."
"""Generic fallback message for unknown task errors. Deliberately
uninformative to the user, to avoid leaking internal details/PII."""


def user_facing_task_error(raw_info: Any) -> str:
    """Map a (technical) task exception to a safe, actionable German
    user message (TF-358).

    The real error must be logged server-side by the caller — it is
    NOT passed through to the user here. Only explicitly known error
    classes get a concrete message; everything else falls back to a
    generic message, so no internal details or personal data reach the
    client.

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
        return (
            "Die ausgewählten Dokumente enthalten zu wenig durchsuchbaren "
            "Inhalt für die Fragengenerierung. Bitte zusätzliche oder "
            "umfangreichere Dokumente auswählen oder die Anzahl der Fragen "
            "reduzieren."
        )

    if code == UNKNOWN_QUESTION_TYPE or "unknown question type" in text:
        return (
            "Der gewählte Fragetyp wird nicht unterstützt. Bitte einen anderen "
            "Fragetyp auswählen."
        )

    return GENERIC_TASK_ERROR
