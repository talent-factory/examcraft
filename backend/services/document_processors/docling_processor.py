"""
IBM Docling Processor
Modern Document Processing mit erweiterten Features
"""

import logging
import time
from typing import Dict, List, Any, Tuple
from pathlib import Path

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.doc import ImageRefMode, TableFormatMode

from services.docling_service import DocumentChunk, ProcessedDocument

logger = logging.getLogger(__name__)


class DoclingProcessor:
    """
    Modern Document Processor basierend auf IBM Docling
    
    Features:
    - Advanced PDF-Layout-Erkennung
    - Tabellen-Extraktion mit Strukturerhaltung
    - Multi-Format-Support (PDF, DOCX, PPTX, XLSX, Images)
    - OCR für gescannte Dokumente
    - Metadaten-Enrichment
    """
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize Docling Processor
        
        Args:
            chunk_size: Maximale Anzahl Wörter pro Chunk
            chunk_overlap: Überlappung zwischen Chunks in Wörtern
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Konfiguriere Docling Pipeline
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = True
        self.pipeline_options.do_table_structure = True
        self.pipeline_options.table_structure_options.mode = TableFormatMode.ACCURATE
        
        # Initialize DocumentConverter
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=self.pipeline_options
                )
            }
        )
        
        logger.info("DoclingProcessor initialized with advanced features")
    
    async def process_document(
        self,
        document_id: int,
        file_path: str,
        filename: str,
        mime_type: str
    ) -> ProcessedDocument:
        """
        Verarbeite Dokument mit Docling
        
        Args:
            document_id: ID des Dokuments in der Datenbank
            file_path: Pfad zur Datei
            filename: Originaler Dateiname
            mime_type: MIME-Type der Datei
            
        Returns:
            ProcessedDocument mit erweiterten Metadaten und Strukturinformationen
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing document with Docling: {filename}")
            
            # Convert Document
            result = self.converter.convert(file_path)
            
            # Extrahiere strukturierte Inhalte
            markdown_content = result.document.export_to_markdown()
            
            # Extrahiere Tabellen
            tables = self._extract_tables(result.document)
            
            # Extrahiere Metadaten
            metadata = self._extract_metadata(result.document)
            metadata['tables'] = tables
            metadata['processing_method'] = 'docling'
            metadata['docling_version'] = '2.23.0'
            
            # Erstelle Chunks mit Layout-Awareness
            chunks = self._create_semantic_chunks(
                result.document,
                markdown_content,
                metadata
            )
            
            processing_time = time.time() - start_time
            
            processed_doc = ProcessedDocument(
                document_id=document_id,
                filename=filename,
                mime_type=mime_type,
                total_pages=metadata.get('pages', 1),
                total_chunks=len(chunks),
                chunks=chunks,
                metadata=metadata,
                processing_time=processing_time
            )
            
            logger.info(
                f"Docling processing completed: {filename} "
                f"({len(chunks)} chunks, {len(tables)} tables, {processing_time:.2f}s)"
            )
            
            return processed_doc
            
        except Exception as e:
            logger.error(f"Docling processing failed for {filename}: {str(e)}")
            raise
    
    def _extract_tables(self, document) -> List[Dict[str, Any]]:
        """
        Extrahiere Tabellen mit Struktur
        
        Args:
            document: Docling Document Objekt
            
        Returns:
            Liste von Tabellen-Dictionaries
        """
        tables = []
        
        try:
            for idx, table in enumerate(document.tables):
                table_data = {
                    'index': idx,
                    'title': getattr(table, 'title', f'Table {idx + 1}'),
                    'location': {
                        'page': getattr(table, 'page_number', None),
                    },
                    'row_count': len(table.data) if hasattr(table, 'data') else 0,
                }
                
                # Versuche DataFrame-Export
                try:
                    df = table.export_to_dataframe()
                    table_data['data'] = df.to_dict('records')
                    table_data['columns'] = df.columns.tolist()
                except Exception as e:
                    logger.warning(f"Could not export table {idx} to DataFrame: {e}")
                    table_data['data'] = []
                    table_data['columns'] = []
                
                tables.append(table_data)
                
        except Exception as e:
            logger.warning(f"Table extraction failed: {e}")
        
        return tables
    
    def _extract_metadata(self, document) -> Dict[str, Any]:
        """
        Erweiterte Metadaten-Extraktion
        
        Args:
            document: Docling Document Objekt
            
        Returns:
            Dictionary mit Metadaten
        """
        metadata = {}
        
        try:
            # Basis-Metadaten
            metadata['title'] = getattr(document, 'title', '')
            metadata['author'] = getattr(document, 'author', '')
            metadata['creation_date'] = getattr(document, 'creation_date', None)
            
            # Struktur-Informationen
            metadata['pages'] = len(document.pages) if hasattr(document, 'pages') else 1
            metadata['has_tables'] = len(document.tables) > 0 if hasattr(document, 'tables') else False
            metadata['table_count'] = len(document.tables) if hasattr(document, 'tables') else 0
            metadata['has_images'] = len(document.images) > 0 if hasattr(document, 'images') else False
            metadata['image_count'] = len(document.images) if hasattr(document, 'images') else 0
            
            # Sektionen
            if hasattr(document, 'sections'):
                metadata['sections'] = [
                    getattr(section, 'title', f'Section {idx}')
                    for idx, section in enumerate(document.sections)
                ]
                metadata['section_count'] = len(document.sections)
            else:
                metadata['sections'] = []
                metadata['section_count'] = 0
            
        except Exception as e:
            logger.warning(f"Metadata extraction partially failed: {e}")
        
        return metadata
    
    def _create_semantic_chunks(
        self,
        document,
        markdown: str,
        metadata: Dict[str, Any]
    ) -> List[DocumentChunk]:
        """
        Erstelle semantisch sinnvolle Chunks basierend auf Dokumentstruktur
        
        - Respektiert Sektionen/Kapitel
        - Behält Tabellen zusammen
        - Optimiert für RAG-Queries
        
        Args:
            document: Docling Document Objekt
            markdown: Markdown-Export des Dokuments
            metadata: Dokument-Metadaten
            
        Returns:
            Liste von DocumentChunk Objekten
        """
        chunks = []
        
        try:
            # Versuche Chunking basierend auf Sektionen
            if hasattr(document, 'sections') and len(document.sections) > 0:
                for section in document.sections:
                    try:
                        section_content = section.export_to_markdown()
                        
                        chunk = DocumentChunk(
                            content=section_content,
                            chunk_index=len(chunks),
                            page_number=getattr(section, 'page_number', None),
                            metadata={
                                'section_title': getattr(section, 'title', ''),
                                'section_level': getattr(section, 'level', 0),
                                'has_tables': bool(getattr(section, 'tables', [])),
                                'word_count': len(section_content.split())
                            }
                        )
                        chunks.append(chunk)
                    except Exception as e:
                        logger.warning(f"Could not process section: {e}")
                        continue
            
            # Fallback: Einfaches Chunking wenn keine Sektionen
            if not chunks:
                chunks = self._create_simple_chunks(markdown)
                
        except Exception as e:
            logger.warning(f"Semantic chunking failed, using simple chunking: {e}")
            chunks = self._create_simple_chunks(markdown)
        
        return chunks if chunks else self._create_simple_chunks(markdown)
    
    def _create_simple_chunks(self, text: str) -> List[DocumentChunk]:
        """
        Fallback: Einfaches Chunking basierend auf Wortanzahl
        
        Args:
            text: Vollständiger Text
            
        Returns:
            Liste von DocumentChunk Objekten
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        words = text.split()
        
        if len(words) <= self.chunk_size:
            chunks.append(DocumentChunk(
                content=text,
                chunk_index=0,
                metadata={'word_count': len(words)}
            ))
            return chunks
        
        start = 0
        chunk_index = 0
        
        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = ' '.join(chunk_words)
            
            chunks.append(DocumentChunk(
                content=chunk_text,
                chunk_index=chunk_index,
                metadata={
                    'word_count': len(chunk_words),
                    'start_word': start,
                    'end_word': end
                }
            ))
            
            start = end - self.chunk_overlap
            chunk_index += 1
            
            if start >= len(words) - self.chunk_overlap:
                break
        
        return chunks

