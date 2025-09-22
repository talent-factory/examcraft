"""
API Integration Tests für Document Endpoints
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from io import BytesIO

from main import app
from models.document import DocumentStatus


class TestDocumentAPI:
    """Test Suite für Document API Endpoints"""
    
    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test Health Check Endpoint"""
        response = client.get("/api/v1/documents/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert data["service"] == "Document Upload Service"
        assert "supported_formats" in data
        assert "max_file_size_mb" in data
        assert len(data["supported_formats"]) == 5
    
    @patch('api.documents.document_service.upload_document')
    def test_upload_document_success(self, mock_upload, client):
        """Test erfolgreicher Document Upload"""
        # Mock Document Response
        mock_document = Mock()
        mock_document.id = 123
        mock_document.filename = "test_123.txt"
        mock_document.status = DocumentStatus.UPLOADED
        mock_upload.return_value = mock_document
        
        # Erstelle Test-Datei
        test_content = b"Test document content for API testing"
        files = {"file": ("test.txt", BytesIO(test_content), "text/plain")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["document_id"] == 123
        assert data["filename"] == "test_123.txt"
        assert data["status"] == "uploaded"
        assert data["message"] == "Document uploaded successfully"
    
    @patch('api.documents.document_service.upload_document')
    def test_upload_document_failure(self, mock_upload, client):
        """Test fehlgeschlagener Document Upload"""
        from fastapi import HTTPException
        mock_upload.side_effect = HTTPException(status_code=400, detail="Invalid file format")
        
        test_content = b"Invalid content"
        files = {"file": ("test.xyz", BytesIO(test_content), "application/unknown")}
        
        response = client.post("/api/v1/documents/upload", files=files)
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid file format" in data["detail"]
    
    @patch('api.documents.document_service.get_documents_by_user')
    def test_list_documents_success(self, mock_get_docs, client):
        """Test erfolgreiche Dokument-Auflistung"""
        # Mock Documents
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {
            "id": 1,
            "filename": "doc1.txt",
            "original_filename": "document1.txt",
            "file_size": 1000,
            "mime_type": "text/plain",
            "status": "uploaded",
            "user_id": "demo_user",
            "metadata": None,
            "content_preview": None,
            "vector_collection": "doc_123",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": None,
            "processed_at": None
        }
        
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {
            "id": 2,
            "filename": "doc2.pdf",
            "original_filename": "document2.pdf",
            "file_size": 2000,
            "mime_type": "application/pdf", 
            "status": "processed",
            "user_id": "demo_user",
            "metadata": {"pages": 5},
            "content_preview": "PDF content preview...",
            "vector_collection": "doc_456",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:01:00",
            "processed_at": "2023-01-01T00:01:00"
        }
        
        mock_get_docs.return_value = [mock_doc1, mock_doc2]
        
        response = client.get("/api/v1/documents/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["documents"]) == 2
        assert data["documents"][0]["id"] == 1
        assert data["documents"][1]["id"] == 2
    
    @patch('api.documents.document_service.get_documents_by_user')
    def test_list_documents_with_status_filter(self, mock_get_docs, client):
        """Test Dokument-Auflistung mit Status-Filter"""
        mock_get_docs.return_value = []
        
        response = client.get("/api/v1/documents/?status=processed")
        
        assert response.status_code == 200
        mock_get_docs.assert_called_once()
        
        # Prüfe dass Status-Filter korrekt übergeben wurde
        call_args = mock_get_docs.call_args
        assert call_args[1]['status'] == DocumentStatus.PROCESSED
    
    def test_list_documents_invalid_status(self, client):
        """Test Dokument-Auflistung mit ungültigem Status"""
        response = client.get("/api/v1/documents/?status=invalid_status")
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid status" in data["detail"]
    
    @patch('api.documents.document_service.get_document_by_id')
    def test_get_document_success(self, mock_get_doc, client):
        """Test erfolgreiche Dokument-Abfrage"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_document.to_dict.return_value = {
            "id": 123,
            "filename": "test.txt",
            "original_filename": "test_original.txt",
            "file_size": 1000,
            "mime_type": "text/plain",
            "status": "uploaded",
            "user_id": "demo_user",
            "metadata": None,
            "content_preview": None,
            "vector_collection": "doc_123",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": None,
            "processed_at": None
        }
        mock_get_doc.return_value = mock_document
        
        response = client.get("/api/v1/documents/123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 123
        assert data["filename"] == "test.txt"
    
    @patch('api.documents.document_service.get_document_by_id')
    def test_get_document_not_found(self, mock_get_doc, client):
        """Test Dokument nicht gefunden"""
        mock_get_doc.return_value = None
        
        response = client.get("/api/v1/documents/999")
        
        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"
    
    @patch('api.documents.document_service.delete_document')
    @patch('api.documents.document_service.get_document_by_id')
    def test_delete_document_success(self, mock_get_doc, mock_delete, client):
        """Test erfolgreiche Dokument-Löschung"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_get_doc.return_value = mock_document
        mock_delete.return_value = True
        
        response = client.delete("/api/v1/documents/123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document deleted successfully"
        assert data["document_id"] == 123
    
    @patch('api.documents.document_service.delete_document')
    @patch('api.documents.document_service.get_document_by_id')
    def test_delete_document_failure(self, mock_get_doc, mock_delete, client):
        """Test fehlgeschlagene Dokument-Löschung"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_get_doc.return_value = mock_document
        mock_delete.return_value = False
        
        response = client.delete("/api/v1/documents/123")
        
        assert response.status_code == 500
        data = response.json()
        assert "Failed to delete document" in data["detail"]
    
    @patch('api.documents.document_service.process_document_content')
    @patch('api.documents.document_service.get_document_by_id')
    def test_process_document_success(self, mock_get_doc, mock_process, client):
        """Test erfolgreiche Dokument-Verarbeitung"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_get_doc.return_value = mock_document
        
        mock_processed_doc = Mock()
        mock_process.return_value = mock_processed_doc
        
        # Mock document_service.docling_service.get_document_summary
        with patch('api.documents.document_service.docling_service') as mock_docling:
            mock_docling.get_document_summary.return_value = {
                "document_id": 123,
                "total_chunks": 5,
                "processing_time": 0.5
            }
            
            response = client.post("/api/v1/documents/123/process")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document processed successfully"
        assert data["document_id"] == 123
        assert "processing_summary" in data
    
    @patch('api.documents.document_service.process_document_content')
    @patch('api.documents.document_service.get_document_by_id')
    def test_process_document_failure(self, mock_get_doc, mock_process, client):
        """Test fehlgeschlagene Dokument-Verarbeitung"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_get_doc.return_value = mock_document
        mock_process.return_value = None
        
        response = client.post("/api/v1/documents/123/process")
        
        assert response.status_code == 500
        data = response.json()
        assert "Document processing failed" in data["detail"]
    
    @patch('api.documents.document_service.get_document_chunks')
    @patch('api.documents.document_service.get_document_by_id')
    def test_get_document_chunks_success(self, mock_get_doc, mock_get_chunks, client):
        """Test erfolgreiche Chunk-Abfrage"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_document.status = DocumentStatus.PROCESSED
        mock_get_doc.return_value = mock_document
        
        mock_chunks = [
            {"chunk_index": 0, "content": "First chunk"},
            {"chunk_index": 1, "content": "Second chunk"}
        ]
        mock_get_chunks.return_value = mock_chunks
        
        response = client.get("/api/v1/documents/123/chunks")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == 123
        assert data["total_chunks"] == 2
        assert len(data["chunks"]) == 2
        assert data["chunks"][0]["content"] == "First chunk"
    
    @patch('api.documents.document_service.get_document_by_id')
    def test_get_document_chunks_not_processed(self, mock_get_doc, client):
        """Test Chunk-Abfrage für nicht verarbeitetes Dokument"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_document.status = DocumentStatus.UPLOADED
        mock_get_doc.return_value = mock_document
        
        response = client.get("/api/v1/documents/123/chunks")
        
        assert response.status_code == 400
        data = response.json()
        assert "Document not processed yet" in data["detail"]
    
    @patch('api.documents.document_service.get_document_by_id')
    def test_get_document_status(self, mock_get_doc, client):
        """Test Dokument-Status Abfrage"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_document.status = DocumentStatus.PROCESSED
        mock_document.created_at.isoformat.return_value = "2023-01-01T00:00:00"
        mock_document.processed_at.isoformat.return_value = "2023-01-01T00:01:00"
        mock_document.doc_metadata = {"test": "data"}
        mock_get_doc.return_value = mock_document
        
        response = client.get("/api/v1/documents/123/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == 123
        assert data["status"] == "processed"
        assert data["created_at"] == "2023-01-01T00:00:00"
        assert data["processed_at"] == "2023-01-01T00:01:00"
        assert data["metadata"] == {"test": "data"}
