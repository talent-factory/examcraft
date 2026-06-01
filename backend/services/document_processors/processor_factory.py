"""
Document Processor Factory
Dynamische Auswahl zwischen PyMuPDF und Legacy Processor
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
    Factory für dynamische Processor-Auswahl

    Environment Variables:
    - DOCUMENT_PROCESSOR_TYPE: "pymupdf" (default), "legacy", or "auto"

    Default: PyMuPDF (fast and efficient)
    - PyMuPDF: Schnelle PDF-Verarbeitung mit fitz
    - Legacy: pypdf + python-docx (deprecated)
    """

    @staticmethod
    def create_processor() -> Union["PyMuPDFProcessor", "LegacyProcessor"]:
        """
        Erstelle Document Processor basierend auf Konfiguration

        Returns:
            PyMuPDFProcessor (default) oder LegacyProcessor
        """
        processor_type = os.getenv("DOCUMENT_PROCESSOR_TYPE", "pymupdf").lower().strip()

        logger.info(f"Creating document processor (type: {processor_type})")

        # PyMuPDF (Standard - schnell und effizient)
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

        # Explizit Legacy angefordert (deprecated)
        if processor_type == "legacy":
            logger.warning(
                "Legacy processor is deprecated. Consider using PyMuPDF instead."
            )
            from .legacy_processor import LegacyProcessor

            logger.info("Using LegacyProcessor (explicitly requested, deprecated)")
            return LegacyProcessor()

        # Auto-Detection (versucht PyMuPDF, dann Legacy)
        if processor_type == "auto":
            # Versuche PyMuPDF zuerst
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

        # Unbekannter Typ
        raise UnknownProcessorTypeError(
            f"Unknown processor type: {processor_type}. "
            "Valid options: 'pymupdf' (default), 'legacy', 'auto'"
        )


def is_ocr_available() -> bool:
    """True, wenn PyMuPDF-OCR tatsächlich nutzbar ist.

    Prüft drei Bedingungen, statt nur die Env-Var — sonst meldete OCR sich
    als verfügbar (``TESSDATA_PREFIX`` wird im Image unbedingt gesetzt),
    obwohl Tesseract gar nicht installiert ist, und ``get_textpage_ocr``
    würde erst zur Laufzeit krachen statt sauber auf ``unavailable`` zu fallen:

    1. ``TESSDATA_PREFIX`` ist gesetzt (PyMuPDF verlangt das),
    2. das ``tesseract``-Binary ist im PATH,
    3. mindestens ein konfiguriertes Sprachpaket (``<lang>.traineddata``) liegt
       im tessdata-Verzeichnis.
    """
    prefix = os.environ.get("TESSDATA_PREFIX")
    if not prefix:
        return False
    if shutil.which("tesseract") is None:
        return False
    primary_lang = os.getenv("OCR_LANGUAGE", "deu+eng").split("+")[0]
    return os.path.isfile(os.path.join(prefix, f"{primary_lang}.traineddata"))


def create_ocr_processor() -> "PyMuPDFProcessor":
    """Erzeuge einen PyMuPDF-Prozessor mit aktiviertem Tesseract-OCR (TF-360)."""
    from .pymupdf_processor import PyMuPDFProcessor

    return PyMuPDFProcessor(enable_ocr=True)


def _init_document_processor() -> Union["PyMuPDFProcessor", "LegacyProcessor"]:
    """Erzeuge die globale Processor-Instanz beim Import (TF-368).

    Verhalten bei Fehlern:

    * **Fehlkonfiguration** (``UnknownProcessorTypeError`` aus
      ``create_processor`` — ein ungültiges ``DOCUMENT_PROCESSOR_TYPE``):
      fail-fast. Wir degradieren *nicht* still auf einen deprecateten
      Processor, sondern lassen den Boot mit dem Original-Fehler abbrechen,
      damit die Fehlkonfiguration operator-sichtbar und debuggbar ist statt
      unbemerkt. Andere ``ValueError`` (z. B. ein kaputtes numerisches
      ``OCR_DPI``) zählen *nicht* als Typ-Fehlkonfiguration und laufen in den
      Resilienz-Fallback.
    * **Laufzeit-/Import-Fehler** (z. B. PyMuPDF nicht installiert): Resilienz
      bleibt akzeptabel — wir fallen auf PyMuPDF, dann Legacy zurück. Anders
      als bisher (``logger.warning``) wird der Downgrade aber auf ``ERROR``
      *mit dem Original-Exception-Typ* geloggt, sodass ein degradierter
      Worker nicht in einer einzelnen Warnzeile untergeht.
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
# Wird beim ersten Import erstellt
document_processor = _init_document_processor()
