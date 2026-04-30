"""
PyMuPDF Document Processor
Schnelle und effiziente PDF-Verarbeitung mit PyMuPDF (fitz)
"""

import logging
import time
from typing import Dict, Iterable, List, Any, Tuple
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from docx.oxml.ns import qn
import markdown
import re

from services.docling_service import DocumentChunk, ProcessedDocument
from services.document_errors import (
    BINARY_CONTENT,
    EMPTY_DOCUMENT,
    LEGACY_DOC_FORMAT,
    UNSUPPORTED_FORMAT,
    DocumentProcessingError,
)

logger = logging.getLogger(__name__)


def _looks_like_text(content: str, threshold: float = 0.85) -> bool:
    """Return True when ``content`` looks like real text.

    Used to reject binary blobs that decoded successfully via Latin-1
    (which maps every byte 0–255 to a code point and therefore never
    raises). Real text is mostly printable plus tabs/newlines; binary
    is mostly control characters and high-bit noise.
    """
    if not content:
        return True  # empty content is handled by the upstream 0-chunk guard
    printable = sum(1 for c in content if c.isprintable() or c in "\t\n\r")
    return printable / len(content) >= threshold


def _iter_docx_text_blocks(doc) -> Iterable[str]:
    """Yield all visible text blocks in a python-docx Document.

    `doc.paragraphs` only walks the top-level body; tables, nested tables,
    headers, footers and text-frames are skipped. We iterate every `<w:t>`
    element in the document body instead, then add headers/footers from each
    section explicitly (those live outside the body XML tree).
    """

    seen_ids = set()

    body = doc.element.body
    for t_elem in body.iter(qn("w:t")):
        text = t_elem.text
        if text and text.strip():
            yield text

    for section in doc.sections:
        for hdr_ftr in (section.header, section.footer):
            for paragraph in hdr_ftr.paragraphs:
                # `Paragraph` elements may repeat across sections that share
                # a header part; dedupe on the underlying lxml element id.
                pid = id(paragraph._p)
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                if paragraph.text.strip():
                    yield paragraph.text


class PyMuPDFProcessor:
    """
    Modern Document Processor basierend auf PyMuPDF

    Features:
    - Schnelle PDF-Verarbeitung mit PyMuPDF (fitz)
    - Text-Extraktion mit Layout-Awareness
    - Metadaten-Extraktion (Autor, Titel, Creation Date)
    - Multi-Format-Support (PDF, DOCX, TXT, Markdown)
    - Optimiert für Performance und Geschwindigkeit
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize PyMuPDF Processor

        Args:
            chunk_size: Maximale Anzahl Wörter pro Chunk
            chunk_overlap: Überlappung zwischen Chunks in Wörtern
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_types = {
            "application/pdf": self._process_pdf,
            "application/msword": self._process_doc,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": self._process_docx,
            "text/plain": self._process_text,
            "text/markdown": self._process_markdown,
        }

        logger.info("PyMuPDFProcessor initialized (fast PDF processing)")

    async def process_document(
        self, document_id: int, file_path: str, filename: str, mime_type: str
    ) -> ProcessedDocument:
        """
        Verarbeite Dokument mit PyMuPDF

        Args:
            document_id: ID des Dokuments in der Datenbank
            file_path: Pfad zur Datei
            filename: Originaler Dateiname
            mime_type: MIME-Type der Datei

        Returns:
            ProcessedDocument mit erweiterten Metadaten
        """
        start_time = time.time()

        try:
            if mime_type not in self.supported_types:
                raise DocumentProcessingError(
                    UNSUPPORTED_FORMAT,
                    f"Unsupported MIME type: {mime_type}",
                    filename=filename,
                    mime_type=mime_type,
                )

            logger.info(f"Processing document with PyMuPDF: {filename}")

            # Verarbeite Dokument basierend auf MIME-Type
            processor = self.supported_types[mime_type]
            raw_text, doc_metadata = await processor(file_path, filename)

            # Erstelle Text-Chunks
            chunks = self._create_chunks(raw_text)

            # Berechne Verarbeitungszeit
            processing_time = time.time() - start_time

            # Erweitere Metadaten
            doc_metadata["processing_method"] = "pymupdf"
            doc_metadata["processor_type"] = "PyMuPDF"

            # Erstelle ProcessedDocument
            processed_doc = ProcessedDocument(
                document_id=document_id,
                filename=filename,
                mime_type=mime_type,
                total_pages=doc_metadata.get("pages"),
                total_chunks=len(chunks),
                chunks=chunks,
                metadata=doc_metadata,
                processing_time=processing_time,
            )

            logger.info(
                f"PyMuPDF processing completed: {filename} "
                f"({len(chunks)} chunks, {processing_time:.2f}s)"
            )

            return processed_doc

        except Exception as e:
            logger.error(f"PyMuPDF processing failed for {filename}: {str(e)}")
            raise

    async def _process_pdf(
        self, file_path: str, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Verarbeite PDF-Datei mit PyMuPDF (sehr schnell)

        Args:
            file_path: Pfad zur PDF-Datei
            filename: Originaler Dateiname für Fallback-Titel

        Returns:
            Tuple (full_text, metadata)
        """
        try:
            text_content = []
            metadata = {}

            # Öffne PDF mit PyMuPDF
            doc = fitz.open(file_path)

            # Extrahiere Metadaten
            pdf_metadata = doc.metadata
            if pdf_metadata:
                # Titel (mit Fallback auf Filename)
                title = pdf_metadata.get("title", "").strip()
                if not title:
                    title = filename.rsplit(".", 1)[0] if "." in filename else filename
                metadata["title"] = title

                # Autor
                author = pdf_metadata.get("author", "").strip()
                metadata["author"] = author

                # Subject
                subject = pdf_metadata.get("subject", "").strip()
                if subject:
                    metadata["subject"] = subject

                # Keywords
                keywords = pdf_metadata.get("keywords", "").strip()
                if keywords:
                    metadata["keywords"] = keywords

                # Creation Date
                creation_date = pdf_metadata.get("creationDate", "").strip()
                if creation_date:
                    # PyMuPDF Format: D:20240101120000+01'00'
                    try:
                        # Entferne 'D:' Präfix
                        date_str = creation_date.replace("D:", "")
                        # Extrahiere YYYYMMDD
                        if len(date_str) >= 8:
                            year = date_str[0:4]
                            month = date_str[4:6]
                            day = date_str[6:8]
                            metadata["creation_date"] = f"{year}-{month}-{day}"
                    except Exception as e:
                        logger.debug(f"Failed to parse PDF creation date: {e}")

            # Anzahl Seiten
            metadata["pages"] = doc.page_count

            # Extrahiere Text von allen Seiten
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    page_text = page.get_text("text")  # Plain text extraction

                    if page_text.strip():
                        text_content.append(f"[Seite {page_num + 1}]\n{page_text}")
                except Exception as e:
                    logger.warning(
                        f"Could not extract text from page {page_num + 1}: {str(e)}"
                    )
                    continue

            # Schließe PDF
            doc.close()

            # Extrahiere Headings aus Text (einfache Heuristik)
            full_text = "\n\n".join(text_content)
            sections = self._extract_headings_from_text(full_text)
            if sections:
                metadata["sections"] = sections[:30]  # Max 30 Headings
                metadata["section_count"] = len(sections[:30])

            # Defaults falls Metadaten fehlen
            if "title" not in metadata or not metadata["title"]:
                metadata["title"] = (
                    filename.rsplit(".", 1)[0] if "." in filename else filename
                )
            if "author" not in metadata:
                metadata["author"] = ""

            return full_text, metadata

        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            raise

    def _extract_headings_from_text(self, text: str) -> List[str]:
        """
        Extrahiere potentielle Überschriften aus Text

        Heuristik:
        - Zeilen mit <= 100 Zeichen
        - Endet nicht mit Punkt
        - Beginnt mit Großbuchstabe oder Nummer
        - Hat mindestens 3 Wörter

        Args:
            text: Vollständiger Text

        Returns:
            Liste von Überschriften
        """
        headings = []
        lines = text.split("\n")

        for line in lines:
            line = line.strip()

            # Filtere zu lange Zeilen
            if len(line) > 100 or len(line) < 10:
                continue

            # Filtere Zeilen die mit Punkt enden (normale Sätze)
            if line.endswith("."):
                continue

            # Muss mit Großbuchstabe oder Nummer beginnen
            if not (line[0].isupper() or line[0].isdigit()):
                continue

            # Muss mindestens 3 Wörter haben
            words = line.split()
            if len(words) < 3:
                continue

            # Filtere Zeilen mit vielen Sonderzeichen
            special_char_count = sum(1 for c in line if c in "()[]{}|\\/@#$%^&*+=~`")
            if special_char_count > 3:
                continue

            headings.append(line)

        return headings

    async def _process_docx(
        self, file_path: str, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Verarbeite DOCX-Datei (Body + Tabellen + Header/Footer)."""
        try:
            doc = DocxDocument(file_path)

            text_content = list(_iter_docx_text_blocks(doc))

            title = doc.core_properties.title or ""
            if not title:
                title = filename.rsplit(".", 1)[0] if "." in filename else filename

            metadata = {
                "title": title,
                "author": doc.core_properties.author or "",
                "subject": doc.core_properties.subject or "",
                "created": doc.core_properties.created.isoformat()
                if doc.core_properties.created
                else None,
                "modified": doc.core_properties.modified.isoformat()
                if doc.core_properties.modified
                else None,
                "paragraphs": len(doc.paragraphs),
                "text_blocks": len(text_content),
            }

            full_text = "\n\n".join(text_content)

            if not full_text.strip():
                raise DocumentProcessingError(
                    EMPTY_DOCUMENT,
                    f"No extractable text found in DOCX '{filename}' "
                    "(document is empty or contains only images/objects)",
                    filename=filename,
                )

            return full_text, metadata

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"DOCX processing failed: {str(e)}")
            raise

    async def _process_doc(
        self, file_path: str, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Verarbeite DOC-Datei (Legacy CFB/OLE2 Format).

        `.doc` is a binary OLE2 compound file. Without `antiword`,
        `libreoffice --headless` or a CFB parser, we cannot reliably extract
        text. The previous implementation decoded raw bytes as UTF-8 with
        `errors='ignore'`, producing garbage that silently embedded as
        nonsense vectors. We now refuse the file with a clear error so the
        document is marked ERROR and the user knows to convert to DOCX.
        """
        with open(file_path, "rb") as fh:
            header = fh.read(8)

        if header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
            raise DocumentProcessingError(
                LEGACY_DOC_FORMAT,
                f"Legacy .doc format detected for '{filename}'. "
                "Reliable text extraction requires conversion. "
                "Please save the document as .docx and re-upload.",
                filename=filename,
            )

        # Some `.doc` files in the wild are actually mislabeled RTF or text.
        # Try a best-effort decode and refuse if no meaningful text remains.
        with open(file_path, "rb") as fh:
            raw = fh.read()
        text_content = raw.decode("utf-8", errors="ignore")
        # Strip control bytes that survived decode
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text_content)
        if len(cleaned.strip()) < 50:
            raise DocumentProcessingError(
                EMPTY_DOCUMENT,
                f"No extractable text found in legacy .doc '{filename}'. "
                "Please save the document as .docx and re-upload.",
                filename=filename,
            )

        metadata = {
            "title": filename.rsplit(".", 1)[0] if "." in filename else filename,
            "format": "DOC (Legacy)",
            "note": "Best-effort text extraction; converting to DOCX is recommended.",
        }
        return cleaned, metadata

    async def _process_text(
        self, file_path: str, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Verarbeite Text-Datei mit Encoding-Fallback (UTF-8 → Latin-1)."""
        try:
            content, encoding = self._read_text_with_fallback(file_path)
        except Exception as e:
            logger.error(f"Text processing failed: {str(e)}")
            raise

        metadata = {
            "title": filename.rsplit(".", 1)[0] if "." in filename else filename,
            "lines": len(content.split("\n")),
            "words": len(content.split()),
            "characters": len(content),
            "encoding": encoding,
        }
        return content, metadata

    async def _process_markdown(
        self, file_path: str, filename: str
    ) -> Tuple[str, Dict[str, Any]]:
        """Verarbeite Markdown-Datei mit Encoding-Fallback (UTF-8 → Latin-1)."""
        try:
            md_content, encoding = self._read_text_with_fallback(file_path)

            # Konvertiere Markdown zu HTML und extrahiere Plain Text
            html = markdown.markdown(md_content)
            plain_text = re.sub("<[^<]+?>", "", html)

            # Extrahiere Headings aus Markdown
            sections = []
            heading_pattern = r"^(#+)\s+(.+)$"
            matches = re.finditer(heading_pattern, md_content, re.MULTILINE)

            for match in matches:
                title = match.group(2).strip()
                if len(title) > 200:  # Filtere zu lange Headings
                    continue
                sections.append(title)

            metadata = {
                "title": filename.rsplit(".", 1)[0] if "." in filename else filename,
                "format": "Markdown",
                "encoding": encoding,
                "sections": sections[:30] if sections else [],
                "section_count": len(sections[:30]) if sections else 0,
                "html_length": len(html),
                "plain_text_length": len(plain_text),
            }

            return plain_text, metadata

        except Exception as e:
            logger.error(f"Markdown processing failed: {str(e)}")
            raise

    @staticmethod
    def _read_text_with_fallback(file_path: str) -> Tuple[str, str]:
        """Read a text file as UTF-8, falling back to Latin-1.

        Returns ``(content, encoding)`` so callers can record the encoding
        in metadata for diagnostics. Latin-1 decodes any byte sequence —
        including binary files renamed with a text extension — so when
        the fallback fires we additionally check the printable-character
        ratio and refuse mojibake. Failures of the fallback ``open()``
        itself are wrapped to preserve the file path in the error.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read(), "utf-8"
        except UnicodeDecodeError:
            pass

        try:
            with open(file_path, "r", encoding="latin-1") as file:
                content = file.read()
        except OSError as e:
            raise OSError(f"Latin-1 fallback read failed for {file_path}: {e}") from e

        if not _looks_like_text(content):
            raise DocumentProcessingError(
                BINARY_CONTENT,
                f"File {file_path} does not appear to be a text file "
                "(low printable-character ratio after Latin-1 fallback). "
                "Likely binary content with a misleading extension.",
            )

        logger.warning(f"File {file_path} is not valid UTF-8; decoded as Latin-1")
        return content, "latin-1"

    def _create_chunks(self, text: str) -> List[DocumentChunk]:
        """Erstelle Text-Chunks für RAG-Processing"""
        if not text or not text.strip():
            return []

        chunks = []
        words = text.split()

        if len(words) <= self.chunk_size:
            chunks.append(
                DocumentChunk(
                    content=text, chunk_index=0, metadata={"word_count": len(words)}
                )
            )
            return chunks

        start = 0
        chunk_index = 0

        while start < len(words):
            end = min(start + self.chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunks.append(
                DocumentChunk(
                    content=chunk_text,
                    chunk_index=chunk_index,
                    metadata={
                        "word_count": len(chunk_words),
                        "start_word": start,
                        "end_word": end,
                    },
                )
            )

            start = end - self.chunk_overlap
            chunk_index += 1

            if start >= len(words) - self.chunk_overlap:
                break

        return chunks
