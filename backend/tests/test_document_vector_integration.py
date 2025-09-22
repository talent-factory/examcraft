"""
Integration Tests für Document + Vector Processing
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from io import BytesIO

from main import app
from services.document_service import DocumentService
from services.vector_service_mock import VectorService
from models.document import Document, DocumentStatus


class TestDocumentVectorIntegration:
    """Integration Tests für Document + Vector Processing"""
    
    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        return TestClient(app)
    
    @pytest.fixture
    def temp_upload_dir(self):
        """Temporäres Upload Directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def temp_vector_dir(self):
        """Temporäres Vector Directory"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def document_service(self, temp_upload_dir):
        """Document Service für Tests"""
        return DocumentService(upload_dir=temp_upload_dir)
    
    @pytest.fixture
    def vector_service(self, temp_vector_dir):
        """Vector Service für Tests"""
        return VectorService(persist_directory=temp_vector_dir)
    
    @pytest.fixture
    def mock_db(self):
        """Mock Database Session"""
        return Mock()
    
    @pytest.fixture
    def sample_document(self, temp_upload_dir):
        """Sample Document für Tests"""
        # Erstelle Test-Datei
        test_file = os.path.join(temp_upload_dir, "test_doc.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Dies ist ein Test-Dokument für Integration Tests.\n")
            f.write("Es enthält wichtige Informationen über ExamCraft AI.\n")
            f.write("Vector Search und RAG-Funktionen werden getestet.")
        
        # Mock Document
        document = Mock(spec=Document)
        document.id = 123
        document.filename = "test_123.txt"
        document.original_filename = "test_document.txt"
        document.file_path = test_file
        document.mime_type = "text/plain"
        document.status = DocumentStatus.UPLOADED
        document.user_id = "test_user"
        document.doc_metadata = None
        document.vector_collection = None
        
        return document
    
    @pytest.mark.asyncio
    async def test_process_document_with_vectors_success(self, document_service, sample_document, mock_db):
        """Test erfolgreiche Document + Vector Processing"""
        
        with patch.object(document_service, 'get_document_by_id', return_value=sample_document), \
             patch.object(document_service, 'docling_service') as mock_docling, \
             patch('services.document_service.vector_service') as mock_vector_service:
            
            # Mock Docling Processing
            from services.docling_service import ProcessedDocument, DocumentChunk
            
            chunks = [
                DocumentChunk(
                    content="Dies ist ein Test-Dokument für Integration Tests.",
                    chunk_index=0,
                    page_number=1
                ),
                DocumentChunk(
                    content="Es enthält wichtige Informationen über ExamCraft AI.",
                    chunk_index=1,
                    page_number=1
                )
            ]
            
            processed_doc = ProcessedDocument(
                document_id=123,
                filename="test_document.txt",
                mime_type="text/plain",
                total_pages=1,
                total_chunks=2,
                chunks=chunks,
                metadata={"test": "metadata"},
                processing_time=0.1
            )
            
            mock_docling.process_document = AsyncMock(return_value=processed_doc)
            
            # Mock Vector Service
            from services.vector_service_mock import EmbeddingStats
            embedding_stats = EmbeddingStats(
                total_chunks=2,
                embedding_dimension=384,
                model_name="test-model",
                processing_time=0.2
            )
            mock_vector_service.add_document_chunks = AsyncMock(return_value=embedding_stats)
            
            # Test Processing
            result = await document_service.process_document_with_vectors(123, mock_db)
            
            # Assertions
            assert result is not None
            assert result["document_id"] == 123
            assert "docling_processing" in result
            assert "vector_embeddings" in result
            
            # Docling Processing Stats
            docling_stats = result["docling_processing"]
            assert docling_stats["total_chunks"] == 2
            assert docling_stats["processing_time"] == 0.1
            
            # Vector Embedding Stats
            vector_stats = result["vector_embeddings"]
            assert vector_stats["total_chunks"] == 2
            assert vector_stats["embedding_dimension"] == 384
            assert vector_stats["model_name"] == "test-model"
            assert vector_stats["processing_time"] == 0.2
            
            # Verify Database Updates
            assert sample_document.vector_collection == "doc_123"
            assert sample_document.doc_metadata is not None
            assert "embedding_model" in sample_document.doc_metadata
            assert "total_chunks" in sample_document.doc_metadata
            
            mock_db.commit.assert_called()
            mock_db.refresh.assert_called()
    
    @pytest.mark.asyncio
    async def test_process_document_with_vectors_docling_failure(self, document_service, sample_document, mock_db):
        """Test Vector Processing bei Docling Failure"""
        
        with patch.object(document_service, 'get_document_by_id', return_value=sample_document), \
             patch.object(document_service, 'process_document_content', return_value=None):
            
            result = await document_service.process_document_with_vectors(123, mock_db)
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_process_document_with_vectors_embedding_failure(self, document_service, sample_document, mock_db):
        """Test Vector Processing bei Embedding Failure"""
        
        with patch.object(document_service, 'get_document_by_id', return_value=sample_document), \
             patch.object(document_service, 'docling_service') as mock_docling, \
             patch('services.document_service.vector_service') as mock_vector_service:
            
            # Mock successful Docling Processing
            from services.docling_service import ProcessedDocument, DocumentChunk
            
            chunks = [DocumentChunk(content="Test content", chunk_index=0)]
            processed_doc = ProcessedDocument(
                document_id=123,
                filename="test.txt",
                mime_type="text/plain",
                total_pages=1,
                total_chunks=1,
                chunks=chunks,
                metadata={},
                processing_time=0.1
            )
            
            mock_docling.process_document = AsyncMock(return_value=processed_doc)
            
            # Mock Vector Service Failure
            mock_vector_service.add_document_chunks = AsyncMock(side_effect=Exception("Vector service failed"))
            
            result = await document_service.process_document_with_vectors(123, mock_db)
            
            # Should return partial result with error
            assert result is not None
            assert result["document_id"] == 123
            assert "docling_processing" in result
            assert "vector_embeddings" in result
            assert "error" in result["vector_embeddings"]
            assert "Vector service failed" in result["vector_embeddings"]["error"]
            
            # Document should have error metadata
            assert "vector_embedding_error" in sample_document.doc_metadata
    
    @patch('api.documents.document_service')
    def test_api_process_document_with_vectors_enabled(self, mock_doc_service, client):
        """Test API Document Processing mit Vector Embeddings"""
        
        # Mock Document
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_doc_service.get_document_by_id.return_value = mock_document
        
        # Mock Processing Result
        processing_result = {
            "document_id": 123,
            "docling_processing": {
                "total_chunks": 3,
                "processing_time": 0.5
            },
            "vector_embeddings": {
                "total_chunks": 3,
                "embedding_dimension": 384,
                "model_name": "test-model",
                "processing_time": 0.3
            }
        }
        mock_doc_service.process_document_with_vectors = AsyncMock(return_value=processing_result)
        
        response = client.post("/api/v1/documents/123/process?create_vectors=true")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Document processed successfully with vector embeddings"
        assert data["document_id"] == 123
        assert "processing_stats" in data
        
        # Verify service was called with vectors enabled
        mock_doc_service.process_document_with_vectors.assert_called_once_with(123, mock_doc_service.get_document_by_id.return_value.__class__)
    
    @patch('api.documents.document_service')
    def test_api_process_document_without_vectors(self, mock_doc_service, client):
        """Test API Document Processing ohne Vector Embeddings"""
        
        # Mock Document
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_doc_service.get_document_by_id.return_value = mock_document
        
        # Mock Docling Processing
        from services.docling_service import ProcessedDocument, DocumentChunk
        processed_doc = ProcessedDocument(
            document_id=123,
            filename="test.txt",
            mime_type="text/plain",
            total_pages=1,
            total_chunks=1,
            chunks=[DocumentChunk(content="Test", chunk_index=0)],
            metadata={},
            processing_time=0.1
        )
        mock_doc_service.process_document_content = AsyncMock(return_value=processed_doc)
        mock_doc_service.docling_service.get_document_summary.return_value = {
            "document_id": 123,
            "total_chunks": 1
        }
        
        response = client.post("/api/v1/documents/123/process?create_vectors=false")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Document processed successfully"
        assert data["document_id"] == 123
        assert "processing_summary" in data
        
        # Verify only Docling processing was called
        mock_doc_service.process_document_content.assert_called_once()
        mock_doc_service.process_document_with_vectors.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_full_workflow_integration(self, client):
        """Test vollständiger Workflow: Upload → Process → Search"""
        
        # Step 1: Upload Document
        test_content = b"ExamCraft AI ist ein intelligentes System fuer Pruefungserstellung. Es verwendet Vector Search und RAG-Technologien."
        files = {"file": ("integration_test.txt", BytesIO(test_content), "text/plain")}
        
        upload_response = client.post("/api/v1/documents/upload", files=files)
        assert upload_response.status_code == 200
        
        upload_data = upload_response.json()
        document_id = upload_data["document_id"]
        
        # Step 2: Process Document with Vectors
        process_response = client.post(f"/api/v1/documents/{document_id}/process?create_vectors=true")
        assert process_response.status_code == 200
        
        process_data = process_response.json()
        assert "processing_stats" in process_data
        
        # Step 3: Verify Vector Search
        search_data = {
            "query": "ExamCraft AI System",
            "n_results": 5
        }
        search_response = client.post("/api/v1/search/similarity", json=search_data)
        assert search_response.status_code == 200
        
        search_results = search_response.json()
        assert search_results["total_results"] > 0
        assert search_results["results"][0]["document_id"] == document_id
        
        # Step 4: Get Document Vector Chunks
        chunks_response = client.get(f"/api/v1/search/document/{document_id}/chunks")
        assert chunks_response.status_code == 200
        
        chunks_data = chunks_response.json()
        assert len(chunks_data) > 0
        assert chunks_data[0]["document_id"] == document_id
        
        # Step 5: Check Vector Stats
        stats_response = client.get("/api/v1/search/stats")
        assert stats_response.status_code == 200
        
        stats_data = stats_response.json()
        assert stats_data["total_chunks"] > 0
    
    def test_error_handling_document_not_found(self, client):
        """Test Error Handling bei nicht existierendem Dokument"""
        
        # Process non-existent document
        response = client.post("/api/v1/documents/99999/process")
        assert response.status_code == 404
        
        # Search chunks for non-existent document
        response = client.get("/api/v1/search/document/99999/chunks")
        assert response.status_code == 404
        
        # Delete vectors for non-existent document
        response = client.delete("/api/v1/search/document/99999/vectors")
        assert response.status_code == 404
    
    @patch('api.documents.document_service')
    def test_error_handling_processing_failure(self, mock_doc_service, client):
        """Test Error Handling bei Processing Failure"""
        
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        mock_doc_service.get_document_by_id.return_value = mock_document
        mock_doc_service.process_document_with_vectors = AsyncMock(return_value=None)
        
        response = client.post("/api/v1/documents/123/process?create_vectors=true")
        
        assert response.status_code == 500
        data = response.json()
        assert "Document processing failed" in data["detail"]
    
    @patch('api.vector_search.vector_service')
    def test_error_handling_vector_service_failure(self, mock_vector_service, client):
        """Test Error Handling bei Vector Service Failure"""
        
        mock_vector_service.similarity_search = AsyncMock(side_effect=Exception("Vector service unavailable"))
        
        search_data = {"query": "test query"}
        response = client.post("/api/v1/search/similarity", json=search_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "Search failed" in data["detail"]


class TestDocumentServiceVectorMethods:
    """Test Suite für erweiterte DocumentService Vector-Methoden"""
    
    @pytest.fixture
    def document_service(self):
        """Document Service für Tests"""
        return DocumentService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock Database Session"""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_process_document_with_vectors_document_not_found(self, document_service, mock_db):
        """Test process_document_with_vectors mit nicht existierendem Dokument"""
        
        with patch.object(document_service, 'get_document_by_id', return_value=None):
            result = await document_service.process_document_with_vectors(999, mock_db)
            assert result is None
    
    @pytest.mark.asyncio
    async def test_process_document_with_vectors_metadata_update(self, document_service, mock_db):
        """Test Metadaten-Update bei Vector Processing"""
        
        # Mock Document
        mock_document = Mock()
        mock_document.id = 123
        mock_document.doc_metadata = {"existing": "data"}
        mock_document.vector_collection = None
        
        with patch.object(document_service, 'get_document_by_id', return_value=mock_document), \
             patch.object(document_service, 'process_document_content') as mock_process, \
             patch('services.document_service.vector_service') as mock_vector_service:
            
            # Mock Docling Processing
            from services.docling_service import ProcessedDocument, DocumentChunk
            processed_doc = ProcessedDocument(
                document_id=123,
                filename="test.txt",
                mime_type="text/plain",
                total_pages=1,
                total_chunks=1,
                chunks=[DocumentChunk(content="Test", chunk_index=0)],
                metadata={"doc": "metadata"},
                processing_time=0.1
            )
            mock_process.return_value = processed_doc
            
            # Mock Vector Service
            from services.vector_service_mock import EmbeddingStats
            embedding_stats = EmbeddingStats(
                total_chunks=1,
                embedding_dimension=384,
                model_name="test-model",
                processing_time=0.2
            )
            mock_vector_service.add_document_chunks = AsyncMock(return_value=embedding_stats)
            
            result = await document_service.process_document_with_vectors(123, mock_db)
            
            # Verify metadata was updated correctly
            assert mock_document.vector_collection == "doc_123"
            assert mock_document.doc_metadata["existing"] == "data"  # Existing data preserved
            assert mock_document.doc_metadata["embedding_model"] == "test-model"
            assert mock_document.doc_metadata["total_chunks"] == 1
            assert mock_document.doc_metadata["embedding_dimension"] == 384
            assert "vector_created_at" in mock_document.doc_metadata
