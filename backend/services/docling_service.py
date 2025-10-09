"""
Docling Service für ExamCraft AI
Strukturierte Dokumentenverarbeitung und Text-Extraktion
Modernisiert mit IBM Docling Integration und Legacy Fallback
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class DocumentChunk:
    """Repräsentiert einen Text-Chunk aus einem Dokument"""
    content: str
    page_number: Optional[int] = None
    chunk_index: int = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class ProcessedDocument:
    """Repräsentiert ein verarbeitetes Dokument"""
    document_id: int
    filename: str
    mime_type: str
    total_pages: Optional[int]
    total_chunks: int
    chunks: List[DocumentChunk]
    metadata: Dict[str, Any]
    processing_time: float

class DoclingService:
    """
    Modernisierter Service für strukturierte Dokumentenverarbeitung

    Verwendet:
    - IBM Docling für erweiterte Features (Tabellen, Layout, OCR)
    - Legacy Processor als Fallback (PyPDF, python-docx)

    Processor-Auswahl via Environment Variable:
    - DOCUMENT_PROCESSOR_TYPE=docling (Standard, wenn verfügbar)
    - DOCUMENT_PROCESSOR_TYPE=legacy (Fallback)
    - DOCUMENT_PROCESSOR_TYPE=auto (Auto-Detection)
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize DoclingService

        Args:
            chunk_size: Maximale Anzahl Wörter pro Chunk
            chunk_overlap: Überlappung zwischen Chunks in Wörtern
        """
        from services.document_processors.processor_factory import document_processor

        self.processor = document_processor
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        logger.info(
            f"DoclingService initialized with {type(self.processor).__name__} "
            f"(chunk_size={chunk_size}, overlap={chunk_overlap})"
        )
    
    async def process_document(
        self,
        document_id: int,
        file_path: str,
        filename: str,
        mime_type: str
    ) -> ProcessedDocument:
        """
        Verarbeite Dokument und extrahiere strukturierte Inhalte

        Delegiert Processing an den konfigurierten Processor (Docling oder Legacy)

        Args:
            document_id: ID des Dokuments in der Datenbank
            file_path: Pfad zur Datei
            filename: Originaler Dateiname
            mime_type: MIME-Type der Datei

        Returns:
            ProcessedDocument mit Chunks und Metadaten
        """
        try:
            logger.info(
                f"Processing document: {filename} "
                f"(processor: {type(self.processor).__name__})"
            )

            # Delegiere an Processor
            return await self.processor.process_document(
                document_id=document_id,
                file_path=file_path,
                filename=filename,
                mime_type=mime_type
            )

        except Exception as e:
            logger.error(f"Document processing failed for {filename}: {str(e)}")
            raise

    def get_document_summary(self, processed_doc: ProcessedDocument) -> Dict[str, Any]:
        """
        Erstelle eine Zusammenfassung des verarbeiteten Dokuments
        
        Args:
            processed_doc: Verarbeitetes Dokument
            
        Returns:
            Dictionary mit Zusammenfassungsinformationen
        """
        total_words = sum(len(chunk.content.split()) for chunk in processed_doc.chunks)
        total_chars = sum(len(chunk.content) for chunk in processed_doc.chunks)
        
        return {
            'document_id': processed_doc.document_id,
            'filename': processed_doc.filename,
            'mime_type': processed_doc.mime_type,
            'total_pages': processed_doc.total_pages,
            'total_chunks': processed_doc.total_chunks,
            'total_words': total_words,
            'total_characters': total_chars,
            'processing_time': processed_doc.processing_time,
            'avg_chunk_size': total_words // processed_doc.total_chunks if processed_doc.total_chunks > 0 else 0,
            'metadata': processed_doc.metadata
        }
