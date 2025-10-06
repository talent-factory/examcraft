"""
Document Service für ExamCraft AI
Verwaltet File Upload, Validierung und Speicherung
"""

import os
import uuid
import aiofiles
import magic
from typing import List, Optional, Dict, Any
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from models.document import Document, DocumentStatus
from services.docling_service import DoclingService, ProcessedDocument
from services.vector_service_factory import get_vector_service
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DocumentService:
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = upload_dir
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.supported_formats = {
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'text/plain': '.txt',
            'text/markdown': '.md'
        }
        
        # Erstelle Upload-Verzeichnis falls nicht vorhanden
        os.makedirs(upload_dir, exist_ok=True)
        
        # Initialisiere Docling Service
        self.docling_service = DoclingService()
        
    async def upload_document(
        self, 
        file: UploadFile, 
        user_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> Document:
        """
        Upload und speichere Dokument
        
        Args:
            file: FastAPI UploadFile Objekt
            user_id: Optional User ID für Zuordnung
            db: Database Session
            
        Returns:
            Document: Erstelltes Document Objekt
            
        Raises:
            HTTPException: Bei Validierungsfehlern
        """
        try:
            # 1. File Validation
            await self._validate_file(file)
            
            # 2. Generate unique filename
            file_extension = self._get_file_extension(file.filename)
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # 3. Save file to disk
            await self._save_file_to_disk(file, file_path)
            
            # 4. Detect actual MIME type
            actual_mime_type = self._detect_mime_type(file_path)
            
            # 5. Create database entry
            document = Document(
                filename=unique_filename,
                original_filename=file.filename,
                file_path=file_path,
                file_size=file.size or 0,
                mime_type=actual_mime_type,
                status=DocumentStatus.UPLOADED,
                user_id=user_id,
                vector_collection=f"doc_{uuid.uuid4().hex[:8]}"
            )
            
            if db:
                db.add(document)
                db.commit()
                db.refresh(document)
                
            logger.info(f"Document uploaded successfully: {document.id}")
            return document
            
        except Exception as e:
            logger.error(f"Document upload failed: {str(e)}")
            # Cleanup file if it was created
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    async def _validate_file(self, file: UploadFile) -> None:
        """Validiere hochgeladene Datei"""
        
        # Check file size
        if file.size and file.size > self.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File too large. Maximum size: {self.max_file_size // (1024*1024)}MB"
            )
        
        # Check filename
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        # Check file extension
        if not self._is_supported_format(file.filename):
            supported_exts = list(self.supported_formats.values())
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format. Supported: {', '.join(supported_exts)}"
            )
        
        # Check content type if provided
        if file.content_type and file.content_type not in self.supported_formats:
            logger.warning(f"Content-Type mismatch: {file.content_type} for {file.filename}")
    
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
            async with aiofiles.open(file_path, 'wb') as f:
                content = await file.read()
                await f.write(content)
                
            # Reset file pointer for potential further processing
            await file.seek(0)
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
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
    
    def get_document_by_id(self, document_id: int, db: Session) -> Optional[Document]:
        """Hole Dokument nach ID"""
        return db.query(Document).filter(Document.id == document_id).first()
    
    def get_documents_by_user(
        self, 
        user_id: str, 
        db: Session, 
        status: Optional[DocumentStatus] = None
    ) -> List[Document]:
        """Hole alle Dokumente eines Users"""
        query = db.query(Document).filter(Document.user_id == user_id)
        
        if status:
            query = query.filter(Document.status == status)
            
        return query.order_by(Document.created_at.desc()).all()
    
    def update_document_status(
        self, 
        document_id: int, 
        status: DocumentStatus, 
        db: Session,
        metadata: Optional[Dict[str, Any]] = None
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
            # Delete file from disk
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
                
            # Delete from database
            db.delete(document)
            db.commit()
            
            logger.info(f"Document deleted: {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {str(e)}")
            db.rollback()
            return False
    
    async def process_document_content(
        self, 
        document_id: int, 
        db: Session
    ) -> Optional[ProcessedDocument]:
        """
        Verarbeite Dokumenteninhalt mit Docling Service
        
        Args:
            document_id: ID des zu verarbeitenden Dokuments
            db: Database Session
            
        Returns:
            ProcessedDocument oder None bei Fehlern
        """
        document = self.get_document_by_id(document_id, db)
        if not document:
            logger.error(f"Document {document_id} not found")
            return None
        
        try:
            # Setze Status auf Processing
            document.status = DocumentStatus.PROCESSING
            db.commit()
            
            # Verarbeite Dokument mit Docling
            processed_doc = await self.docling_service.process_document(
                document_id=document.id,
                file_path=document.file_path,
                filename=document.original_filename,
                mime_type=document.mime_type
            )
            
            # Erstelle Content Preview (erste 200 Zeichen)
            if processed_doc.chunks:
                first_chunk = processed_doc.chunks[0].content
                # Entferne NUL-Zeichen die PostgreSQL nicht unterstützt
                clean_chunk = first_chunk.replace('\x00', '').replace('\0', '')
                content_preview = clean_chunk[:200] + "..." if len(clean_chunk) > 200 else clean_chunk
            else:
                content_preview = "No content extracted"
            
            # Aktualisiere Dokument mit verarbeiteten Daten
            document.status = DocumentStatus.PROCESSED
            document.doc_metadata = processed_doc.metadata
            document.content_preview = content_preview
            document.processed_at = datetime.utcnow()
            
            db.commit()
            db.refresh(document)
            
            logger.info(f"Document {document_id} processed successfully with {processed_doc.total_chunks} chunks")
            return processed_doc
            
        except Exception as e:
            logger.error(f"Document processing failed for {document_id}: {str(e)}")
            
            # Setze Status auf Error
            document.status = DocumentStatus.ERROR
            document.doc_metadata = {
                'error': str(e),
                'processing_failed_at': datetime.utcnow().isoformat()
            }
            db.commit()
            
            return None
    
    async def process_document_with_vectors(
        self, 
        document_id: int, 
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """
        Verarbeite Dokument mit Docling UND erstelle Vector Embeddings
        
        Args:
            document_id: ID des zu verarbeitenden Dokuments
            db: Database Session
            
        Returns:
            Dictionary mit Processing- und Embedding-Statistiken
        """
        # Erst normale Dokumentenverarbeitung
        processed_doc = await self.process_document_content(document_id, db)
        
        if not processed_doc:
            logger.error(f"Document processing failed for {document_id}")
            return None
        
        try:
            # Erstelle Vector Embeddings
            logger.info(f"Creating vector embeddings for document {document_id}")
            vector_service = get_vector_service()
            embedding_stats = await vector_service.add_document_chunks(processed_doc)
            
            # Aktualisiere Dokument mit Vector Collection Info
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
                document.doc_metadata['embedding_model'] = embedding_stats.model_name
                document.doc_metadata['embedding_dimension'] = embedding_stats.embedding_dimension
                document.doc_metadata['total_chunks'] = embedding_stats.total_chunks
                document.doc_metadata['embedding_processing_time'] = embedding_stats.processing_time
                document.doc_metadata['vector_created_at'] = datetime.utcnow().isoformat()
                
                # Mark as modified for SQLAlchemy
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(document, 'doc_metadata')
                
                db.commit()
                db.refresh(document)
            
            logger.info(f"Vector embeddings created for document {document_id}")
            
            return {
                'document_id': document_id,
                'docling_processing': {
                    'total_chunks': processed_doc.total_chunks,
                    'processing_time': processed_doc.processing_time,
                    'total_pages': processed_doc.total_pages
                },
                'vector_embeddings': {
                    'total_chunks': embedding_stats.total_chunks,
                    'embedding_dimension': embedding_stats.embedding_dimension,
                    'model_name': embedding_stats.model_name,
                    'processing_time': embedding_stats.processing_time
                }
            }
            
        except Exception as e:
            logger.error(f"Vector embedding creation failed for {document_id}: {str(e)}")
            
            # Dokument bleibt als PROCESSED (Docling war erfolgreich)
            # Aber Vector Embeddings sind fehlgeschlagen
            document = self.get_document_by_id(document_id, db)
            if document and document.doc_metadata:
                document.doc_metadata['vector_embedding_error'] = str(e)
                db.commit()
            
            return {
                'document_id': document_id,
                'docling_processing': {
                    'total_chunks': processed_doc.total_chunks,
                    'processing_time': processed_doc.processing_time,
                    'total_pages': processed_doc.total_pages
                },
                'vector_embeddings': {
                    'error': str(e)
                }
            }
    
    async def get_document_chunks(
        self,
        document_id: int,
        db: Session
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Hole verarbeitete Chunks eines Dokuments

        Args:
            document_id: ID des Dokuments
            db: Database Session

        Returns:
            Liste der Chunks oder None
        """
        document = self.get_document_by_id(document_id, db)
        if not document or document.status != DocumentStatus.PROCESSED:
            return None

        try:
            # Verarbeite Dokument erneut um Chunks zu erhalten
            # In einer späteren Version könnten Chunks in der DB gespeichert werden
            processed_doc = await self.docling_service.process_document(
                document_id=document.id,
                file_path=document.file_path,
                filename=document.original_filename,
                mime_type=document.mime_type
            )

            # Konvertiere Chunks zu Dictionary Format
            chunks_data = []
            for chunk in processed_doc.chunks:
                chunks_data.append({
                    'chunk_index': chunk.chunk_index,
                    'content': chunk.content,
                    'page_number': chunk.page_number,
                    'metadata': chunk.metadata
                })

            return chunks_data

        except Exception as e:
            logger.error(f"Failed to get document chunks for {document_id}: {str(e)}")
            return None

    async def get_full_document_content(
        self,
        document_id: int,
        db: Session
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

        try:
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

            # Verarbeite Dokument um vollständigen Inhalt zu erhalten
            processed_doc = await self.docling_service.process_document(
                document_id=document.id,
                file_path=document.file_path,
                filename=document.original_filename,
                mime_type=document.mime_type
            )

            if not processed_doc or not processed_doc.chunks:
                return None

            # Kombiniere alle Chunks zu vollständigem Inhalt
            full_content = []
            for chunk in processed_doc.chunks:
                # Entferne NUL-Zeichen die PostgreSQL nicht unterstützt
                clean_content = chunk.content.replace('\x00', '').replace('\0', '')
                full_content.append(clean_content)

            return '\n\n'.join(full_content)

        except Exception as e:
            logger.error(f"Failed to get full document content for {document_id}: {str(e)}")
            return None


# Globale Service Instanz
document_service = DocumentService()
