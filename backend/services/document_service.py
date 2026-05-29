"""
Document Service für ExamCraft AI
Verwaltet File Upload, Validierung und Speicherung
Supports both local filesystem and S3-compatible storage
"""

import os
import uuid
import tempfile
import aiofiles
import magic
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models.document import Document, DocumentStatus
from services.docling_service import DoclingService, ProcessedDocument
from services.document_errors import (
    EMPTY_DOCUMENT,
    VECTORIZATION_FAILED,
    DocumentProcessingError,
    classify_error,
)
from services.vector_service_factory import get_vector_service
from services.storage_service import storage_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = upload_dir
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.supported_formats = {
            "application/pdf": ".pdf",
            "application/msword": ".doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
            "text/markdown": ".md",
        }

        # Check if S3 storage is configured
        self.use_s3 = storage_service.is_configured
        if self.use_s3:
            logger.info("Using S3 storage for document uploads")
        else:
            logger.info("Using local filesystem storage for document uploads")
            # Erstelle Upload-Verzeichnis nur wenn lokaler Storage verwendet wird
            os.makedirs(upload_dir, exist_ok=True)

        # Initialisiere Docling Service
        self.docling_service = DoclingService()

    async def upload_document(
        self,
        file: UploadFile,
        user_id: Optional[int] = None,
        db: Optional[Session] = None,
    ) -> Document:
        """
        Upload und speichere Dokument

        Args:
            file: FastAPI UploadFile Objekt
            user_id: Optional User ID für Zuordnung (Integer)
            db: Database Session

        Returns:
            Document: Erstelltes Document Objekt

        Raises:
            HTTPException: Bei Validierungsfehlern
        """
        file_path = None
        object_key = None

        try:
            # 1. File Validation
            await self._validate_file(file)

            # 2. Generate unique filename
            file_extension = self._get_file_extension(file.filename)
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # 3. Read file content
            content = await file.read()
            await file.seek(0)

            # 4. Detect MIME type from content
            actual_mime_type = self._detect_mime_type_from_bytes(content, file.filename)

            if self.use_s3:
                # S3 Storage: Upload to S3
                object_key = f"uploads/{unique_filename}"
                storage_service.upload_file(
                    file_data=content,
                    object_key=object_key,
                    content_type=actual_mime_type,
                )
                # Store S3 object key as file_path
                file_path = object_key
                logger.info(f"File uploaded to S3: {object_key}")
            else:
                # Local Storage: Save to disk
                file_path = os.path.join(self.upload_dir, unique_filename)
                await self._save_file_to_disk(file, file_path)
                logger.info(f"File saved locally: {file_path}")

            # 5. Create database entry
            document = Document(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file.size or len(content),
                mime_type=actual_mime_type,
                status=DocumentStatus.UPLOADED,
                user_id=user_id,
                vector_collection=f"doc_{uuid.uuid4().hex[:8]}",
            )

            if db:
                db.add(document)
                db.commit()
                db.refresh(document)

            logger.info(f"Document uploaded successfully: {document.id}")
            return document

        except Exception as e:
            logger.error(f"Document upload failed: {str(e)}")
            # Cleanup on failure
            if self.use_s3 and object_key:
                try:
                    storage_service.delete_file(object_key)
                except Exception:
                    pass
            elif file_path and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    async def _validate_file(self, file: UploadFile) -> None:
        """Validiere hochgeladene Datei"""

        # Check file size
        if file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {self.max_file_size // (1024 * 1024)}MB",
            )

        # Check filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")

        # Check file extension
        if not self._is_supported_format(file.filename):
            supported_exts = list(self.supported_formats.values())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format. Supported: {', '.join(supported_exts)}",
            )

        # Check content type if provided
        if file.content_type and file.content_type not in self.supported_formats:
            logger.warning(
                f"Content-Type mismatch: {file.content_type} for {file.filename}"
            )

    def _is_supported_format(self, filename: str) -> bool:
        """Prüfe ob Dateiformat unterstützt wird"""
        if not filename:
            return False

        extension = self._get_file_extension(filename)
        return extension.lower() in self.supported_formats.values()

    def _get_file_extension(self, filename: str) -> str:
        """Extrahiere Dateierweiterung"""
        if not filename:
            return ""
        return os.path.splitext(filename)[1].lower()

    async def _save_file_to_disk(self, file: UploadFile, file_path: str) -> None:
        """Speichere Datei auf Festplatte"""
        try:
            async with aiofiles.open(file_path, "wb") as f:
                content = await file.read()
                await f.write(content)

            # Reset file pointer for potential further processing
            await file.seek(0)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to save file: {str(e)}"
            )

    def _detect_mime_type(self, file_path: str) -> str:
        """Erkenne MIME-Type der gespeicherten Datei"""
        try:
            mime_type = magic.from_file(file_path, mime=True)
            return mime_type
        except Exception as e:
            logger.warning(f"Could not detect MIME type for {file_path}: {str(e)}")
            # Fallback based on extension
            extension = self._get_file_extension(file_path)
            for mime, ext in self.supported_formats.items():
                if ext == extension:
                    return mime
            return "application/octet-stream"

    def _detect_mime_type_from_bytes(self, content: bytes, filename: str) -> str:
        """Erkenne MIME-Type aus Datei-Bytes.

        The file extension is authoritative when it maps to one of our
        ``supported_formats``. ``magic.from_buffer`` reads only the leading
        bytes and frequently disagrees with the extension in ways that break
        downstream processing:

        * ``.docx`` is reported as ``application/zip`` on older libmagic
          versions (OOXML is a ZIP archive under the hood).
        * ``.doc`` is reported as ``application/x-ole-storage``.
        * ``.md`` is reported as ``text/plain`` because Markdown is
          syntactically plain text — but routing it through ``_process_text``
          loses the markdown-specific path (heading extraction, syntax
          stripping).

        **Tradeoff:** trusting the extension means a renamed file (e.g. a
        PDF saved as ``.docx``) is routed to the wrong processor. The
        downstream parsers will reject malformed input loudly, and the
        text processors apply a printable-character check to refuse
        binaries renamed to ``.txt``/``.md``. Mismatches are logged at
        INFO level so admins can correlate downstream failures.

        For unrecognised extensions we still fall back to whatever libmagic
        returned so the upstream validation can produce a useful error.
        """
        try:
            detected = magic.from_buffer(content, mime=True)
        except Exception as e:
            logger.warning(f"Could not detect MIME type from buffer: {str(e)}")
            detected = None

        extension_mime = self._mime_for_extension(filename)
        if extension_mime is not None:
            if detected and detected != extension_mime:
                logger.info(
                    f"libmagic returned {detected!r} for {filename!r}; "
                    f"using extension-derived MIME {extension_mime!r}"
                )
            return extension_mime

        if detected and detected in self.supported_formats:
            return detected

        return detected or "application/octet-stream"

    def _mime_for_extension(self, filename: str) -> Optional[str]:
        """Return the supported MIME for ``filename``'s extension, if any."""
        extension = self._get_file_extension(filename)
        if not extension:
            return None
        for mime, ext in self.supported_formats.items():
            if ext == extension:
                return mime
        return None

    def get_document_by_id(self, document_id: int, db: Session) -> Optional[Document]:
        """Hole Dokument nach ID"""
        return db.query(Document).filter(Document.id == document_id).first()

    def update_document_status(
        self,
        document_id: int,
        status: DocumentStatus,
        db: Session,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Document]:
        """Aktualisiere Dokument Status"""
        document = self.get_document_by_id(document_id, db)
        if not document:
            return None

        document.status = status

        if metadata:
            document.doc_metadata = metadata

        if status == DocumentStatus.PROCESSED:
            document.processed_at = datetime.utcnow()

        db.commit()
        db.refresh(document)

        return document

    def delete_document(self, document_id: int, db: Session) -> bool:
        """Lösche Dokument und Datei"""
        document = self.get_document_by_id(document_id, db)
        if not document:
            return False

        try:
            # Delete file from storage
            if self.use_s3 and document.file_path.startswith("uploads/"):
                # S3 Storage: Delete from S3
                try:
                    storage_service.delete_file(document.file_path)
                    logger.info(f"Deleted file from S3: {document.file_path}")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete S3 file {document.file_path}: {e}"
                    )
            elif os.path.exists(document.file_path):
                # Local Storage: Delete from disk
                os.remove(document.file_path)
                logger.info(f"Deleted file from disk: {document.file_path}")

            # Delete from database
            db.delete(document)
            db.commit()

            logger.info(f"Document deleted: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            db.rollback()
            return False

    def _get_local_file_path(self, document: Document) -> str:
        """
        Get local file path for processing. Downloads from S3 if needed.

        Args:
            document: Document model instance

        Returns:
            Local file path (either original or temp file from S3)
        """
        if self.use_s3 and document.file_path.startswith("uploads/"):
            # Download from S3 to temp file
            logger.info(f"Downloading from S3 for processing: {document.file_path}")
            file_data = storage_service.download_file(document.file_path)

            # Get file extension
            ext = self._get_file_extension(document.original_filename)

            # Create temp file with proper extension
            temp_file = tempfile.NamedTemporaryFile(
                suffix=ext, delete=False, prefix="examcraft_"
            )
            temp_file.write(file_data)
            temp_file.close()

            logger.info(f"Downloaded S3 file to temp: {temp_file.name}")
            return temp_file.name
        else:
            # Local file - return as-is
            return document.file_path

    def _cleanup_temp_file(self, file_path: str, document: Document) -> None:
        """Cleanup temp file if it was created for S3 download"""
        if self.use_s3 and document.file_path.startswith("uploads/"):
            # This was a temp file from S3 download
            if os.path.exists(file_path) and file_path.startswith(
                tempfile.gettempdir()
            ):
                try:
                    os.unlink(file_path)
                    logger.debug(f"Cleaned up temp file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {file_path}: {e}")

    async def process_document_content(
        self,
        document_id: int,
        db: Optional[Session] = None,
        processor: Optional[Any] = None,
    ) -> Optional[ProcessedDocument]:
        """
        Verarbeite Dokumenteninhalt mit Docling Service

        Args:
            document_id: ID des zu verarbeitenden Dokuments
            db: Database Session (optional - erstellt neue Session wenn nicht vorhanden)
            processor: Optionaler Prozessor-Override (z. B. PyMuPDF mit OCR);
                fällt auf den konfigurierten Default-Service zurück

        Returns:
            ProcessedDocument oder None bei Fehlern
        """
        # Erstelle neue Session wenn nicht vorhanden (für Background Tasks)
        from database import SessionLocal

        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False

        local_file_path = None
        document = None

        try:
            document = self.get_document_by_id(document_id, db)
            if not document:
                logger.error(f"Document {document_id} not found")
                return None

            # Setze Status auf Processing
            document.status = DocumentStatus.PROCESSING
            db.commit()

            # Get local file path (downloads from S3 if needed)
            local_file_path = self._get_local_file_path(document)

            # Prozessor-Override für die OCR-Eskalation (TF-360): wenn ein
            # expliziter Prozessor übergeben wird (PyMuPDF mit OCR), diesen
            # nutzen, sonst den konfigurierten Default-Service (PyMuPDF).
            active_processor = processor or self.docling_service
            processed_doc = await active_processor.process_document(
                document_id=document.id,
                file_path=local_file_path,
                filename=document.original_filename,
                mime_type=document.mime_type,
            )

            # Reject empty extractions early — otherwise the document would
            # be marked PROCESSED but vectorization would silently fail at
            # the Qdrant upsert step, leaving has_vectors=False with no
            # explanation visible to the user.
            if not processed_doc.chunks:
                raise DocumentProcessingError(
                    EMPTY_DOCUMENT,
                    f"No extractable text in document '{document.original_filename}'.",
                    filename=document.original_filename,
                )

            first_chunk = processed_doc.chunks[0].content
            # Entferne NUL-Zeichen die PostgreSQL nicht unterstützt
            clean_chunk = first_chunk.replace("\x00", "").replace("\0", "")
            content_preview = (
                clean_chunk[:200] + "..." if len(clean_chunk) > 200 else clean_chunk
            )

            # Aktualisiere Dokument mit verarbeiteten Daten
            document.status = DocumentStatus.PROCESSED
            document.doc_metadata = processed_doc.metadata
            document.content_preview = content_preview
            document.processed_at = datetime.utcnow()

            db.commit()
            db.refresh(document)

            logger.info(
                f"Document {document_id} processed successfully with {processed_doc.total_chunks} chunks"
            )
            return processed_doc

        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {str(e)}")

            # Setze Status auf Error mit strukturiertem Code, damit die UI den
            # Fehler lokalisiert anzeigen kann statt nur die englische Raw-Message.
            error_code, error_details = classify_error(e)
            document = self.get_document_by_id(document_id, db)
            if document:
                document.status = DocumentStatus.ERROR
                document.doc_metadata = {
                    "error": str(e),
                    "error_code": error_code,
                    "error_details": error_details,
                    "processing_failed_at": datetime.utcnow().isoformat(),
                }
                db.commit()

            return None
        finally:
            # Cleanup temp file if S3 was used
            if local_file_path and document:
                self._cleanup_temp_file(local_file_path, document)
            if close_db:
                db.close()

    async def process_document_with_vectors(
        self,
        document_id: int,
        db: Optional[Session] = None,
        processor: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Verarbeite Dokument UND erstelle Vector Embeddings (prozessor-agnostisch)

        Args:
            document_id: ID des zu verarbeitenden Dokuments
            db: Database Session (optional - erstellt neue Session wenn nicht vorhanden)
            processor: Optionaler Prozessor-Override (z. B. PyMuPDF mit OCR);
                fällt auf den konfigurierten Default-Prozessor zurück
                (siehe process_document_content).

        Returns:
            Dictionary mit Processing- und Embedding-Statistiken
        """
        # Erstelle neue Session wenn nicht vorhanden (für Background Tasks)
        from database import SessionLocal

        if db is None:
            db = SessionLocal()
            close_db = True
        else:
            close_db = False

        processed_doc = None
        try:
            # Erst normale Dokumentenverarbeitung (ggf. mit OCR-Prozessor)
            processed_doc = await self.process_document_content(
                document_id, db, processor=processor
            )

            if not processed_doc:
                logger.error(f"Document processing failed for {document_id}")
                return None

            # Erstelle Vector Embeddings
            logger.info(f"Creating vector embeddings for document {document_id}")
            vector_service = get_vector_service()
            embedding_stats = await vector_service.add_document_chunks(processed_doc)

            # Aktualisiere Dokument mit Vector Collection Info
            info: Dict[str, Any] = {}
            document = self.get_document_by_id(document_id, db)
            if document:
                # Setze Vector Collection Name
                document.vector_collection = f"doc_{document_id}"

                # Setze has_vectors Flag
                document.has_vectors = True

                # Erweitere Metadaten um Embedding-Info
                if not document.doc_metadata:
                    document.doc_metadata = {}

                # Update metadata (SQLAlchemy JSON field requires special handling)
                document.doc_metadata["embedding_model"] = embedding_stats.model_name
                document.doc_metadata["embedding_dimension"] = (
                    embedding_stats.embedding_dimension
                )
                document.doc_metadata["total_chunks"] = embedding_stats.total_chunks
                document.doc_metadata["embedding_processing_time"] = (
                    embedding_stats.processing_time
                )
                document.doc_metadata["vector_created_at"] = (
                    datetime.utcnow().isoformat()
                )

                # Mark as modified for SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(document, "doc_metadata")

                # Qualitäts-Verdict berechnen und in processing_info ablegen
                # (separate Spalte von doc_metadata; keine Migration nötig).
                from services.quality_assessor import (
                    assess_quality,
                    compute_quality_stats,
                )

                stats = compute_quality_stats(processed_doc, document.file_size or 0)
                verdict = assess_quality(stats)

                info = dict(document.processing_info or {})
                info["quality"] = {
                    "ok": verdict.ok,
                    "reason": verdict.reason,
                    "signals": verdict.signals,
                }
                chain = list(info.get("processor_chain", []))
                chain.append(processed_doc.metadata.get("processing_method", "unknown"))
                info["processor_chain"] = chain
                info["processed_with_ocr"] = bool(
                    processed_doc.metadata.get("ocr_enabled", False)
                ) or info.get("processed_with_ocr", False)
                document.processing_info = info
                flag_modified(document, "processing_info")

                db.commit()
                db.refresh(document)

            # Dokument zwischen Embedding und Reload verschwunden: sauberes None
            # statt KeyError auf info["quality"] (TF-360 Review-Fix).
            if document is None:
                logger.error(
                    f"Document {document_id} disappeared after embedding; aborting"
                )
                return None

            logger.info(f"Vector embeddings created for document {document_id}")

            return {
                "document_id": document_id,
                "quality": info["quality"],
                "extraction": {
                    "total_chunks": processed_doc.total_chunks,
                    "processing_time": processed_doc.processing_time,
                    "total_pages": processed_doc.total_pages,
                },
                "vector_embeddings": {
                    "total_chunks": embedding_stats.total_chunks,
                    "embedding_dimension": embedding_stats.embedding_dimension,
                    "model_name": embedding_stats.model_name,
                    "processing_time": embedding_stats.processing_time,
                },
            }

        except Exception as e:
            logger.error(
                f"Vector embedding creation failed for {document_id}: {str(e)}"
            )

            # Mark the document as ERROR so the UI does not display it as
            # "Verarbeitet" without vectors. Surface a structured error code
            # so the frontend can render a localised, actionable message —
            # if the underlying processor already attached a code we keep
            # it; otherwise we treat it as a vectorisation failure.
            inner_code, inner_details = classify_error(e)
            if inner_code == "unknown_error":
                inner_code = VECTORIZATION_FAILED
            document = self.get_document_by_id(document_id, db)
            if document is not None:
                document.status = DocumentStatus.ERROR
                metadata = dict(document.doc_metadata or {})
                metadata["vector_embedding_error"] = str(e)
                metadata["error_code"] = inner_code
                metadata["error_details"] = inner_details
                document.doc_metadata = metadata
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(document, "doc_metadata")
                db.commit()

            extraction_stats = (
                {
                    "total_chunks": processed_doc.total_chunks,
                    "processing_time": processed_doc.processing_time,
                    "total_pages": processed_doc.total_pages,
                }
                if processed_doc is not None
                else {"error": "processing_failed_before_vectorization"}
            )
            return {
                "document_id": document_id,
                "extraction": extraction_stats,
                "vector_embeddings": {"error": str(e)},
            }
        finally:
            if close_db:
                db.close()

    async def get_document_chunks(
        self, document_id: int, db: Session
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Hole verarbeitete Chunks eines Dokuments aus dem Vector Store

        Args:
            document_id: ID des Dokuments
            db: Database Session

        Returns:
            Liste der Chunks oder None
        """
        document = self.get_document_by_id(document_id, db)
        if not document or document.status != DocumentStatus.PROCESSED:
            return None

        local_file_path = None

        try:
            # Hole Chunks aus Vector Store (Qdrant)
            vector_service = get_vector_service()

            # Check if vector service has get_document_chunks method
            if not hasattr(vector_service, "get_document_chunks"):
                logger.warning(
                    "Vector service does not support get_document_chunks, falling back to re-processing"
                )
                # Fallback: Verarbeite Dokument erneut um Chunks zu erhalten
                # Get local file path (downloads from S3 if needed)
                local_file_path = self._get_local_file_path(document)

                processed_doc = await self.docling_service.process_document(
                    document_id=document.id,
                    file_path=local_file_path,
                    filename=document.original_filename,
                    mime_type=document.mime_type,
                )

                # Konvertiere Chunks zu Dictionary Format
                chunks_data = []
                for chunk in processed_doc.chunks:
                    chunks_data.append(
                        {
                            "chunk_index": chunk.chunk_index,
                            "content": chunk.content,
                            "page_number": chunk.page_number,
                            "metadata": chunk.metadata,
                        }
                    )
                return chunks_data

            # Hole Chunks aus Vector Store
            search_results = await vector_service.get_document_chunks(document_id)

            if not search_results:
                logger.warning(
                    f"No chunks found in vector store for document {document_id}"
                )
                return []

            # Sortiere nach chunk_index
            search_results.sort(
                key=lambda x: x.chunk_index if hasattr(x, "chunk_index") else 0
            )

            # Konvertiere SearchResult zu Dictionary Format
            chunks_data = []
            for result in search_results:
                chunk_data = {
                    "chunk_index": result.chunk_index
                    if hasattr(result, "chunk_index")
                    else 0,
                    "content": result.content,
                    "page_number": result.metadata.get("page_number")
                    if hasattr(result, "metadata") and result.metadata
                    else None,
                    "metadata": result.metadata if hasattr(result, "metadata") else {},
                }
                chunks_data.append(chunk_data)

            return chunks_data

        except Exception as e:
            logger.error(f"Failed to get document chunks for {document_id}: {str(e)}")
            return None
        finally:
            # Cleanup temp file if S3 was used
            if local_file_path and document:
                self._cleanup_temp_file(local_file_path, document)

    async def get_full_document_content(
        self, document_id: int, db: Session
    ) -> Optional[str]:
        """
        Hole vollständigen Dokumenteninhalt für Content Preview

        Args:
            document_id: ID des Dokuments
            db: Database Session

        Returns:
            Vollständiger Dokumenteninhalt als String oder None
        """
        document = self.get_document_by_id(document_id, db)
        if not document:
            return None

        local_file_path = None

        try:
            # Spezialbehandlung für Chat-Exports
            if (
                document.doc_metadata
                and document.doc_metadata.get("source") == "chat_export"
            ):
                # Vollständiger Content ist in doc_metadata gespeichert
                full_content = document.doc_metadata.get("full_content")
                if full_content:
                    return full_content
                # Fallback auf content_preview wenn full_content nicht vorhanden
                return document.content_preview or "Chat-Content nicht verfügbar"

            # Wenn Dokument noch nicht verarbeitet wurde, verarbeite es zuerst
            if document.status == DocumentStatus.UPLOADED:
                processed_doc = await self.process_document_content(document_id, db)
                if not processed_doc:
                    return None
            elif document.status == DocumentStatus.PROCESSING:
                # Dokument wird gerade verarbeitet, warte kurz und prüfe erneut
                return None
            elif document.status == DocumentStatus.ERROR:
                # Dokument konnte nicht verarbeitet werden
                return None

            # Get local file path (downloads from S3 if needed)
            local_file_path = self._get_local_file_path(document)

            # Verarbeite Dokument um vollständigen Inhalt zu erhalten
            processed_doc = await self.docling_service.process_document(
                document_id=document.id,
                file_path=local_file_path,
                filename=document.original_filename,
                mime_type=document.mime_type,
            )

            if not processed_doc or not processed_doc.chunks:
                return None

            # Kombiniere alle Chunks zu vollständigem Inhalt
            full_content = []
            for chunk in processed_doc.chunks:
                # Entferne NUL-Zeichen die PostgreSQL nicht unterstützt
                clean_content = chunk.content.replace("\x00", "").replace("\0", "")
                full_content.append(clean_content)

            return "\n\n".join(full_content)

        except Exception as e:
            logger.error(
                f"Failed to get full document content for {document_id}: {str(e)}"
            )
            return None
        finally:
            # Cleanup temp file if S3 was used
            if local_file_path and document:
                self._cleanup_temp_file(local_file_path, document)


# Globale Service Instanz
document_service = DocumentService()
