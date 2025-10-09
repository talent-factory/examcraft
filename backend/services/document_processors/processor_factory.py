"""
Document Processor Factory
Dynamische Auswahl zwischen Docling und Legacy Processor
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)


class DocumentProcessorFactory:
    """
    Factory für dynamische Processor-Auswahl
    
    Environment Variables:
    - DOCUMENT_PROCESSOR_TYPE: "docling", "legacy", or "auto" (default)
    
    Auto-Detection:
    - Versucht Docling zu verwenden
    - Fällt auf Legacy zurück wenn Docling nicht verfügbar
    """
    
    @staticmethod
    def create_processor() -> Union['DoclingProcessor', 'LegacyProcessor']:
        """
        Erstelle Document Processor basierend auf Konfiguration

        Returns:
            DoclingProcessor oder LegacyProcessor
        """
        processor_type = os.getenv("DOCUMENT_PROCESSOR_TYPE", "auto").lower().strip()
        
        logger.info(f"Creating document processor (type: {processor_type})")
        
        # Explizit Docling angefordert
        if processor_type == "docling":
            try:
                from .docling_processor import DoclingProcessor
                logger.info("Using DoclingProcessor (explicitly requested)")
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
        
        # Explizit Legacy angefordert
        if processor_type == "legacy":
            from .legacy_processor import LegacyProcessor
            logger.info("Using LegacyProcessor (explicitly requested)")
            return LegacyProcessor()
        
        # Auto-Detection (Standard)
        if processor_type == "auto":
            try:
                from .docling_processor import DoclingProcessor
                logger.info("Using DoclingProcessor (auto-detected)")
                return DoclingProcessor()
            except ImportError as e:
                logger.warning(
                    f"Docling not available ({e}), falling back to LegacyProcessor. "
                    "For better document processing, install: "
                    "pip install docling docling-core docling-ibm-models"
                )
                from .legacy_processor import LegacyProcessor
                return LegacyProcessor()
        
        # Unbekannter Typ
        raise ValueError(
            f"Unknown processor type: {processor_type}. "
            "Valid options: 'docling', 'legacy', 'auto'"
        )


# Global Processor Instance
# Wird beim ersten Import erstellt
try:
    document_processor = DocumentProcessorFactory.create_processor()
    logger.info(f"Document processor initialized: {type(document_processor).__name__}")
except Exception as e:
    logger.error(f"Failed to initialize document processor: {e}")
    # Fallback auf Legacy
    from .legacy_processor import LegacyProcessor
    document_processor = LegacyProcessor()
    logger.warning("Using LegacyProcessor as fallback")

