"""
Document Processor Factory
Dynamic selection between PyMuPDF and legacy processor
"""

import os
import shutil
import logging
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .pymupdf_processor import PyMuPDFProcessor
    from .legacy_processor import LegacyProcessor

logger = logging.getLogger(__name__)


class UnknownProcessorTypeError(ValueError):
    """Raised when ``DOCUMENT_PROCESSOR_TYPE`` is set to an unrecognised value.

    A dedicated ``ValueError`` subclass so ``_init_document_processor`` can
    fail-fast on a genuine processor misconfiguration *without* also catching
    unrelated ``ValueError``s — e.g. a bad numeric env var such as ``OCR_DPI``
    bubbling up from a processor constructor, which previously got misreported
    as "Invalid DOCUMENT_PROCESSOR_TYPE" (TF-368 follow-up).
    """


class DocumentProcessorFactory:
    """
    Factory for dynamic processor selection

    Environment Variables:
    - DOCUMENT_PROCESSOR_TYPE: "pymupdf" (default), "legacy", or "auto"

    Default: PyMuPDF (fast and efficient)
    - PyMuPDF: fast PDF processing with fitz
    - Legacy: pypdf + python-docx (deprecated)
    """

    @staticmethod
    def create_processor() -> Union["PyMuPDFProcessor", "LegacyProcessor"]:
        """
        Create a document processor based on configuration

        Returns:
            PyMuPDFProcessor (default) or LegacyProcessor
        """
        processor_type = os.getenv("DOCUMENT_PROCESSOR_TYPE", "pymupdf").lower().strip()

        logger.info(f"Creating document processor (type: {processor_type})")

        # PyMuPDF (default - fast and efficient)
        if processor_type == "pymupdf":
            try:
                from .pymupdf_processor import PyMuPDFProcessor

                logger.info("Using PyMuPDFProcessor (fast PDF processing)")
                return PyMuPDFProcessor()
            except ImportError as e:
                logger.error(
                    f"PyMuPDF explicitly requested but not available: {e}. "
                    "Install with: pip install PyMuPDF"
                )
                raise ImportError(
                    "PyMuPDF processor requested but dependencies not installed. "
                    "Install with: pip install PyMuPDF"
                ) from e

        # Legacy explicitly requested (deprecated)
        if processor_type == "legacy":
            logger.warning(
                "Legacy processor is deprecated. Consider using PyMuPDF instead."
            )
            from .legacy_processor import LegacyProcessor

            logger.info("Using LegacyProcessor (explicitly requested, deprecated)")
            return LegacyProcessor()

        # Auto-detection (tries PyMuPDF, then legacy)
        if processor_type == "auto":
            # Try PyMuPDF first
            try:
                from .pymupdf_processor import PyMuPDFProcessor

                logger.info("Using PyMuPDFProcessor (auto-detected)")
                return PyMuPDFProcessor()
            except ImportError:
                pass

            # Fallback: Legacy
            logger.warning(
                "Using LegacyProcessor (fallback). "
                "Install PyMuPDF for better performance: pip install PyMuPDF"
            )
            from .legacy_processor import LegacyProcessor

            return LegacyProcessor()

        # Unknown type
        raise UnknownProcessorTypeError(
            f"Unknown processor type: {processor_type}. "
            "Valid options: 'pymupdf' (default), 'legacy', 'auto'"
        )


def is_ocr_available() -> bool:
    """True if PyMuPDF OCR is actually usable.

    Checks three conditions instead of just the env var — otherwise OCR
    would report itself as available (``TESSDATA_PREFIX`` is unconditionally
    set in the image) even though Tesseract isn't installed at all, and
    ``get_textpage_ocr`` would only blow up at runtime instead of falling
    back cleanly to ``unavailable``:

    1. ``TESSDATA_PREFIX`` is set (PyMuPDF requires this),
    2. the ``tesseract`` binary is on PATH,
    3. at least one configured language pack (``<lang>.traineddata``) exists
       in the tessdata directory.
    """
    prefix = os.environ.get("TESSDATA_PREFIX")
    if not prefix:
        return False
    if shutil.which("tesseract") is None:
        return False
    primary_lang = os.getenv("OCR_LANGUAGE", "deu+eng").split("+")[0]
    return os.path.isfile(os.path.join(prefix, f"{primary_lang}.traineddata"))


def create_ocr_processor() -> "PyMuPDFProcessor":
    """Create a PyMuPDF processor with Tesseract OCR enabled (TF-360)."""
    from .pymupdf_processor import PyMuPDFProcessor

    return PyMuPDFProcessor(enable_ocr=True)


def _init_document_processor() -> Union["PyMuPDFProcessor", "LegacyProcessor"]:
    """Create the global processor instance at import time (TF-368).

    Behavior on error:

    * **Misconfiguration** (``UnknownProcessorTypeError`` from
      ``create_processor`` — an invalid ``DOCUMENT_PROCESSOR_TYPE``):
      fail-fast. We do *not* silently degrade to a deprecated processor;
      instead we let boot abort with the original error, so the
      misconfiguration is operator-visible and debuggable instead of
      going unnoticed. Other ``ValueError``s (e.g. a malformed numeric
      ``OCR_DPI``) do *not* count as a type misconfiguration and fall
      into the resilience fallback.
    * **Runtime/import errors** (e.g. PyMuPDF not installed): resilience
      remains acceptable — we fall back to PyMuPDF, then legacy. Unlike
      before (``logger.warning``), the downgrade is now logged at
      ``ERROR`` *with the original exception type*, so a degraded worker
      doesn't get lost in a single warning line.
    """
    try:
        processor = DocumentProcessorFactory.create_processor()
        logger.info(f"Document processor initialized: {type(processor).__name__}")
        return processor
    except UnknownProcessorTypeError:
        # Misconfiguration (unknown DOCUMENT_PROCESSOR_TYPE). Never silently
        # degrade to a deprecated processor — re-raise so the boot fails loud.
        # Scoped to the dedicated subclass so an unrelated ValueError from a
        # processor constructor (bad OCR_DPI etc.) is NOT misreported here.
        logger.error(
            "Invalid DOCUMENT_PROCESSOR_TYPE — refusing to start with a "
            "silently degraded processor. Set it to 'pymupdf', 'legacy', "
            "or 'auto'."
        )
        raise
    except Exception as e:
        # Genuine runtime failure (e.g. PyMuPDF dependency missing, or a bad
        # processor-constructor env var). Resilient fallback is acceptable, but
        # surface it at ERROR with the original exception type so the
        # degradation is operator-visible.
        logger.error(
            "Failed to initialize configured document processor "
            "(%s: %s); attempting fallback.",
            type(e).__name__,
            e,
        )
        try:
            from .pymupdf_processor import PyMuPDFProcessor

            logger.error(
                "Document processor degraded to PyMuPDFProcessor fallback after %s.",
                type(e).__name__,
            )
            return PyMuPDFProcessor()
        except Exception as fallback_exc:
            # Broadened from ImportError: if the PyMuPDF fallback itself fails
            # for *any* reason (not just a missing import), still degrade to
            # Legacy rather than aborting boot — the documented "resilient
            # fallback" contract. Logged loud with both exception types.
            from .legacy_processor import LegacyProcessor

            logger.error(
                "Document processor degraded to deprecated LegacyProcessor "
                "(final fallback) after %s / %s.",
                type(e).__name__,
                type(fallback_exc).__name__,
            )
            return LegacyProcessor()


# Global Processor Instance
# Created on first import
document_processor = _init_document_processor()
