"""
Strukturierte Document-Processing-Fehler mit stabilen Codes (TF-331).

Background: ``process_document_content`` and the vector-embedding pipeline
catch arbitrary exceptions and persist the raw English message in
``metadata.error``. The UI then has only that single string to render — no
i18n, no actionable hint, no programmatic error handling.

By raising :class:`DocumentProcessingError` with a stable ``code`` (and
optional ``details`` like the offending filename), the upstream catch-block
captures both the human-readable message (for logs / support) AND the
machine-readable code (for the frontend's localisation lookup).

Codes are stable, snake_case identifiers — never localise them, never
break compatibility silently. New codes are additive; deprecated codes
must keep their meaning.
"""

from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Error codes — stable, machine-readable identifiers used by the frontend
# i18n lookup. Add new codes by appending; never repurpose an existing one.
# ---------------------------------------------------------------------------

LEGACY_DOC_FORMAT = "legacy_doc_format"
"""Legacy Word .doc (CFB/OLE2) — needs conversion to .docx."""

EMPTY_DOCUMENT = "empty_document"
"""Document parsed but contained no extractable text (image-only PDF, empty
DOCX, whitespace-only .txt/.md)."""

BINARY_CONTENT = "binary_content"
"""Text-extension file (.txt/.md) whose bytes don't look like text — likely
a binary blob renamed with a misleading extension."""

UNSUPPORTED_FORMAT = "unsupported_format"
"""MIME type / extension not in the supported allowlist."""

VECTORIZATION_FAILED = "vectorization_failed"
"""Document was extracted successfully but the vector embedding step
failed (Qdrant unavailable, dimension mismatch, …)."""

FILE_CORRUPT = "file_corrupt"
"""File could not be opened or parsed — likely corrupt upload."""

OCR_ENGINE_FAILURE = "ocr_engine_failure"
"""Tesseract OCR engine failed at runtime (binary/tessdata missing or
misconfigured, language pack absent, version mismatch). Distinct from
``empty_document`` so the operator sees the real cause (TF-360)."""

UNKNOWN_ERROR = "unknown_error"
"""Catch-all fallback when no other code applies. The frontend renders the
raw error string for these so the user still sees *something*."""


class DocumentProcessingError(ValueError):
    """ValueError subclass that carries a stable error code + diagnostic details.

    Subclassing ``ValueError`` keeps backward compatibility — existing
    ``except ValueError`` and ``pytest.raises(ValueError, match=...)``
    callsites work unchanged.

    Args:
        code: One of the module-level constants (``LEGACY_DOC_FORMAT``, …).
        message: Human-readable English message — goes into logs and into
            ``metadata.error`` as a fallback.
        **details: Arbitrary structured diagnostics (e.g. ``filename=...``).
            Frontend may surface these in tooltips for support diagnosis.
    """

    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.details: Dict[str, Any] = dict(details)


def classify_error(exc: BaseException) -> tuple[str, Dict[str, Any]]:
    """Return ``(code, details)`` for any exception, defaulting to UNKNOWN_ERROR.

    Used by ``process_document_content`` so it doesn't have to ``isinstance``
    everywhere — generic exceptions get the fallback code transparently.
    """
    if isinstance(exc, DocumentProcessingError):
        return exc.code, exc.details
    return UNKNOWN_ERROR, {}


def known_codes() -> tuple[str, ...]:
    """Return all known error codes — used by tests to assert exhaustiveness."""
    return (
        LEGACY_DOC_FORMAT,
        EMPTY_DOCUMENT,
        BINARY_CONTENT,
        UNSUPPORTED_FORMAT,
        VECTORIZATION_FAILED,
        FILE_CORRUPT,
        OCR_ENGINE_FAILURE,
        UNKNOWN_ERROR,
    )


def safe_filename_detail(filename: Optional[str]) -> Dict[str, Any]:
    """Build a ``{filename: ...}`` details dict only when filename is truthy.

    Avoids cluttering metadata with empty strings or None.
    """
    return {"filename": filename} if filename else {}
