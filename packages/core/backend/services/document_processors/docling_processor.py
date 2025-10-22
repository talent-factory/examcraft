"""
IBM Docling Processor
Modern Document Processing mit erweiterten Features
"""

import logging
import time
from typing import Dict, List, Any, Tuple
from pathlib import Path
from datetime import datetime

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None

# Try to import TableFormatMode from different locations (API changed in newer versions)
try:
    from docling_core.types.doc import ImageRefMode, TableFormatMode
except ImportError:
    try:
        from docling_core.types.doc import ImageRefMode
        from docling_core.types.doc.table import TableFormatMode
    except ImportError:
        # Fallback: Define TableFormatMode locally if not available
        class TableFormatMode:
            ACCURATE = "accurate"
            FAST = "fast"

        class ImageRefMode:
            PLACEHOLDER = "placeholder"
            EMBEDDED = "embedded"

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
        # OCR deaktiviert für schnellere Verarbeitung (nur Text-PDFs)
        self.pipeline_options = PdfPipelineOptions()
        self.pipeline_options.do_ocr = False  # Deaktiviert OCR (verhindert Model-Download)
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

            # Extrahiere Metadaten (mit filename als Fallback für title, markdown für sections, und file_path für PDF-Metadaten)
            metadata = self._extract_metadata(result.document, filename=filename, markdown=markdown_content, file_path=file_path)
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
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extrahiere PDF-Metadaten mit pypdf (Author, Creation Date, etc.)

        Args:
            file_path: Pfad zur PDF-Datei

        Returns:
            Dictionary mit PDF-Metadaten
        """
        pdf_metadata = {}

        if not PdfReader or not file_path.lower().endswith('.pdf'):
            return pdf_metadata

        try:
            reader = PdfReader(file_path)

            # Extrahiere Metadaten aus PDF
            if reader.metadata:
                # Author
                author = reader.metadata.get('/Author', '')
                if author:
                    pdf_metadata['author'] = author

                # Creation Date
                creation_date = reader.metadata.get('/CreationDate', None)
                if creation_date:
                    try:
                        # PDF dates sind im Format: D:YYYYMMDDHHmmSSOHH'mm'
                        # Konvertiere zu ISO format
                        if isinstance(creation_date, str):
                            # Entferne 'D:' Präfix
                            date_str = creation_date.replace('D:', '')
                            # Extrahiere YYYYMMDD
                            if len(date_str) >= 8:
                                year = date_str[0:4]
                                month = date_str[4:6]
                                day = date_str[6:8]
                                pdf_metadata['creation_date'] = f"{year}-{month}-{day}"
                    except Exception as e:
                        logger.debug(f"Failed to parse PDF creation date: {e}")

                # Subject
                subject = reader.metadata.get('/Subject', '')
                if subject:
                    pdf_metadata['subject'] = subject

                # Keywords
                keywords = reader.metadata.get('/Keywords', '')
                if keywords:
                    pdf_metadata['keywords'] = keywords

        except Exception as e:
            logger.debug(f"Failed to extract PDF metadata: {e}")

        return pdf_metadata

    def _extract_metadata(self, document, filename: str = None, markdown: str = None, file_path: str = None) -> Dict[str, Any]:
        """
        Erweiterte Metadaten-Extraktion mit Fallbacks

        Args:
            document: Docling Document Objekt
            filename: Original filename as fallback for title
            markdown: Markdown content for extracting sections/headings
            file_path: Path to file for PDF metadata extraction

        Returns:
            Dictionary mit Metadaten
        """
        import re

        metadata = {}

        try:
            # ===== TITEL =====
            title = getattr(document, 'title', '')
            if not title and filename:
                title = filename.rsplit('.', 1)[0] if '.' in filename else filename
            metadata['title'] = title

            # ===== PDF-METADATEN (Author, Creation Date) =====
            pdf_metadata = {}
            if file_path:
                pdf_metadata = self._extract_pdf_metadata(file_path)

            # ===== AUTOR =====
            # Versuche verschiedene Quellen für Author (PDF > Docling > Default)
            author = pdf_metadata.get('author', '')
            if not author:
                author = getattr(document, 'author', '')
            if not author and hasattr(document, 'metadata'):
                author = document.metadata.get('author', '') if isinstance(document.metadata, dict) else ''
            metadata['author'] = author

            # ===== CREATION DATE =====
            # Versuche verschiedene Quellen für Creation Date (PDF > Docling > Default)
            creation_date = pdf_metadata.get('creation_date', None)
            if not creation_date:
                creation_date = getattr(document, 'creation_date', None)
            if not creation_date and hasattr(document, 'metadata'):
                creation_date = document.metadata.get('creation_date') if isinstance(document.metadata, dict) else None
            metadata['creation_date'] = creation_date.isoformat() if creation_date and hasattr(creation_date, 'isoformat') else creation_date

            # ===== SEITEN =====
            metadata['pages'] = len(document.pages) if hasattr(document, 'pages') else 1

            # ===== TABELLEN =====
            metadata['has_tables'] = len(document.tables) > 0 if hasattr(document, 'tables') else False
            metadata['table_count'] = len(document.tables) if hasattr(document, 'tables') else 0

            # ===== BILDER =====
            metadata['has_images'] = len(document.images) > 0 if hasattr(document, 'images') else False
            metadata['image_count'] = len(document.images) if hasattr(document, 'images') else 0

            # ===== SEKTIONEN / HEADINGS MIT HIERARCHIE =====
            sections = []
            sections_with_hierarchy = []

            # Versuche Sektionen aus document.sections zu extrahieren
            if hasattr(document, 'sections') and document.sections:
                sections = [
                    getattr(section, 'title', f'Section {idx}')
                    for idx, section in enumerate(document.sections)
                    if getattr(section, 'title', None)
                ]

            # Fallback: Extrahiere Headings aus Markdown mit Hierarchie
            if not sections and markdown:
                # Finde alle Headings mit ihrem Level (# Heading 1, ## Heading 2, etc.)
                heading_pattern = r'^(#+)\s+(.+)$'
                matches = re.finditer(heading_pattern, markdown, re.MULTILINE)

                for match in matches:
                    level = len(match.group(1))  # Anzahl der # = Level
                    title = match.group(2)

                    # Filtere lange Headings (> 200 Zeichen) und Tabellen-Headings
                    if len(title) > 200 or title.count('|') > 5:
                        continue

                    sections_with_hierarchy.append({
                        'title': title,
                        'level': level
                    })
                    sections.append(title)

                # Nimm nur die ersten 30 Headings
                sections = sections[:30]
                sections_with_hierarchy = sections_with_hierarchy[:30]

            metadata['sections'] = sections
            metadata['section_count'] = len(sections)

            # Speichere auch die Hierarchie-Informationen
            if sections_with_hierarchy:
                metadata['sections_hierarchy'] = sections_with_hierarchy

        except Exception as e:
            logger.warning(f"Metadata extraction partially failed: {e}")
            # Setze Defaults wenn etwas fehlschlägt
            metadata.setdefault('title', filename.rsplit('.', 1)[0] if filename and '.' in filename else filename or 'Unknown')
            metadata.setdefault('author', '')
            metadata.setdefault('creation_date', None)
            metadata.setdefault('pages', 1)
            metadata.setdefault('has_tables', False)
            metadata.setdefault('table_count', 0)
            metadata.setdefault('has_images', False)
            metadata.setdefault('image_count', 0)
            metadata.setdefault('sections', [])
            metadata.setdefault('section_count', 0)

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

