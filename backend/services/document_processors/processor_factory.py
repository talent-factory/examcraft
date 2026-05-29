"""
Document Processor Factory
Dynamische Auswahl zwischen PyMuPDF, Docling und Legacy Processor
"""

import os
import shutil
import logging
from typing import Union, TYPE_CHECKING

if TYPE_CHECKING:
    from .pymupdf_processor import PyMuPDFProcessor
    from .docling_processor import DoclingProcessor
    from .legacy_processor import LegacyProcessor

logger = logging.getLogger(__name__)


class DocumentProcessorFactory:
    """
    Factory für dynamische Processor-Auswahl

    Environment Variables:
    - DOCUMENT_PROCESSOR_TYPE: "pymupdf" (default), "docling", "legacy", or "auto"

    Default: PyMuPDF (fast and efficient)
    - PyMuPDF: Schnelle PDF-Verarbeitung mit fitz
    - Docling: IBM Docling (deprecated, langsam)
    - Legacy: pypdf + python-docx (deprecated)
    """

    @staticmethod
    def create_processor() -> Union[
        "PyMuPDFProcessor", "DoclingProcessor", "LegacyProcessor"
    ]:
        """
        Erstelle Document Processor basierend auf Konfiguration

        Returns:
            PyMuPDFProcessor (default), DoclingProcessor oder LegacyProcessor
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

        # Explizit Docling angefordert (deprecated)
        if processor_type == "docling":
            logger.warning(
                "Docling processor is deprecated due to performance issues. "
                "Consider using PyMuPDF instead."
            )
            try:
                from .docling_processor import DoclingProcessor

                logger.info("Using DoclingProcessor (explicitly requested, deprecated)")
                return DoclingProcessor()
            except ImportError as e:
                logger.error(
                    f"Docling explicitly requested but not available: {e}. "
                    "Install with: pip install docling docling-core docling-ibm-models"
                )
                raise ImportError(
                    "Docling processor requested but dependencies not installed. "
                    "Install with: pip install docling docling-core docling-ibm-models"
                ) from e

        # Explizit Legacy angefordert (deprecated)
        if processor_type == "legacy":
            logger.warning(
                "Legacy processor is deprecated. Consider using PyMuPDF instead."
            )
            from .legacy_processor import LegacyProcessor

            logger.info("Using LegacyProcessor (explicitly requested, deprecated)")
            return LegacyProcessor()

        # Auto-Detection (versucht PyMuPDF, dann Docling, dann Legacy)
        if processor_type == "auto":
            # Versuche PyMuPDF zuerst
            try:
                from .pymupdf_processor import PyMuPDFProcessor

                logger.info("Using PyMuPDFProcessor (auto-detected)")
                return PyMuPDFProcessor()
            except ImportError:
                pass

            # Fallback: Docling
            try:
                from .docling_processor import DoclingProcessor

                logger.warning(
                    "Using DoclingProcessor (auto-detected). "
                    "Install PyMuPDF for better performance: pip install PyMuPDF"
                )
                return DoclingProcessor()
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
        raise ValueError(
            f"Unknown processor type: {processor_type}. "
            "Valid options: 'pymupdf' (default), 'docling', 'legacy', 'auto'"
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


# Global Processor Instance
# Wird beim ersten Import erstellt
try:
    document_processor = DocumentProcessorFactory.create_processor()
    logger.info(f"Document processor initialized: {type(document_processor).__name__}")
except Exception as e:
    logger.error(f"Failed to initialize document processor: {e}")
    # Fallback auf PyMuPDF, dann Legacy
    try:
        from .pymupdf_processor import PyMuPDFProcessor

        document_processor = PyMuPDFProcessor()
        logger.warning("Using PyMuPDFProcessor as fallback")
    except ImportError:
        from .legacy_processor import LegacyProcessor

        document_processor = LegacyProcessor()
        logger.warning("Using LegacyProcessor as final fallback")
