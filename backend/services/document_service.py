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
