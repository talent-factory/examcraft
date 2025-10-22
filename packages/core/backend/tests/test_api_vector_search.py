"""
API Integration Tests für Vector Search Endpoints
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient

from main import app
from services.qdrant_vector_service import SearchResult  # Use Qdrant types


class TestVectorSearchAPI:
    """Test Suite für Vector Search API Endpoints"""

    @pytest.fixture
    def client(self):
        """FastAPI Test Client"""
        return TestClient(app)

    @pytest.fixture
    def mock_vector_service(self):
        """Mock Vector Service für Tests"""
        return Mock()

    @pytest.fixture
    def sample_search_results(self):
        """Sample Search Results für Tests"""
        return [
            SearchResult(
                chunk_id="doc_1_chunk_0",
                document_id=1,
                content="Test content about ExamCraft AI system",
                similarity_score=0.85,
                metadata={
                    "document_id": 1,
                    "filename": "test.txt",
                    "chunk_index": 0,
                    "word_count": 6,
                },
                chunk_index=0,
            ),
            SearchResult(
                chunk_id="doc_1_chunk_1",
                document_id=1,
                content="Additional information about vector search",
                similarity_score=0.72,
                metadata={
                    "document_id": 1,
                    "filename": "test.txt",
                    "chunk_index": 1,
                    "word_count": 5,
                },
                chunk_index=1,
            ),
        ]

    def test_vector_search_health_success(self, client):
        """Test Vector Search Health Check (Success)"""
        with patch("api.vector_search.vector_service") as mock_service:
            with patch("api.vector_search.get_service_info") as mock_get_service_info:
                mock_service.get_collection_stats.return_value = {
                    "collection_name": "test_collection",
                    "total_chunks": 10,
                    "embedding_model": "test-model",
                    "qdrant_url": "http://test:6333",
                }
                mock_service._embedding_model = None
                mock_get_service_info.return_value = {
                    "service_type": "qdrant",
                    "service_class": "QdrantVectorService",
                }

                response = client.get("/api/v1/search/health")

                assert response.status_code == 200
                data = response.json()

                assert data["status"] == "healthy"
                assert data["service"] == "Vector Search Service"
                assert data["service_type"] == "qdrant"
                assert data["service_class"] == "QdrantVectorService"
                assert data["collection_name"] == "test_collection"
                assert data["total_chunks"] == 10
                assert data["embedding_model"] == "test-model"
                assert data["model_loaded"] is False
                assert data["qdrant_url"] == "http://test:6333"

    def test_vector_search_health_failure(self, client):
        """Test Vector Search Health Check (Failure)"""
        with patch("api.vector_search.vector_service") as mock_service:
            mock_service.get_collection_stats.side_effect = Exception(
                "Service unavailable"
            )

            response = client.get("/api/v1/search/health")

            assert (
                response.status_code == 200
            )  # Health endpoint returns 200 even on errors
            data = response.json()

            assert data["status"] == "unhealthy"
            assert data["service"] == "Vector Search Service"
            assert "Service unavailable" in data["error"]

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_similarity_search_success(
        self, mock_doc_service, mock_vector_service, client, sample_search_results
    ):
        """Test erfolgreiche Similarity Search"""
        # Mock Vector Service
        mock_vector_service.similarity_search = AsyncMock(
            return_value=sample_search_results
        )

        # Mock Document Service
        mock_document = Mock()
        mock_document.original_filename = "test_document.txt"
        mock_doc_service.get_document_by_id.return_value = mock_document

        # Test Request
        search_data = {"query": "ExamCraft AI", "n_results": 2}

        response = client.post("/api/v1/search/similarity", json=search_data)

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "ExamCraft AI"
        assert data["total_results"] == 2
        assert len(data["results"]) == 2
        assert "search_time_ms" in data

        # Prüfe ersten Result
        first_result = data["results"][0]
        assert first_result["chunk_id"] == "doc_1_chunk_0"
        assert first_result["document_id"] == 1
        assert first_result["content"] == "Test content about ExamCraft AI system"
        assert first_result["similarity_score"] == 0.85
        assert first_result["chunk_index"] == 0
        assert first_result["filename"] == "test_document.txt"

        # Verify service calls
        mock_vector_service.similarity_search.assert_called_once_with(
            query="ExamCraft AI", n_results=2, document_ids=None
        )

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_similarity_search_with_document_filter(
        self, mock_doc_service, mock_vector_service, client
    ):
        """Test Similarity Search mit Document Filter"""
        mock_vector_service.similarity_search = AsyncMock(return_value=[])

        search_data = {"query": "test query", "n_results": 5, "document_ids": [1, 2, 3]}

        response = client.post("/api/v1/search/similarity", json=search_data)

        assert response.status_code == 200

        mock_vector_service.similarity_search.assert_called_once_with(
            query="test query", n_results=5, document_ids=[1, 2, 3]
        )

    def test_similarity_search_invalid_query(self, client):
        """Test Similarity Search mit ungültiger Query"""
        # Leere Query
        response = client.post("/api/v1/search/similarity", json={"query": ""})
        assert response.status_code == 422  # Validation Error

        # Zu lange Query
        long_query = "x" * 1001
        response = client.post("/api/v1/search/similarity", json={"query": long_query})
        assert response.status_code == 422

        # Ungültige n_results
        response = client.post(
            "/api/v1/search/similarity", json={"query": "test", "n_results": 0}
        )
        assert response.status_code == 422

        response = client.post(
            "/api/v1/search/similarity", json={"query": "test", "n_results": 51}
        )
        assert response.status_code == 422

    @patch("api.vector_search.vector_service")
    def test_similarity_search_service_error(self, mock_vector_service, client):
        """Test Similarity Search Service Error"""
        mock_vector_service.similarity_search = AsyncMock(
            side_effect=Exception("Vector search failed")
        )

        search_data = {"query": "test query"}
        response = client.post("/api/v1/search/similarity", json=search_data)

        assert response.status_code == 500
        data = response.json()
        assert "Search failed" in data["detail"]

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_get_document_vector_chunks_success(
        self, mock_doc_service, mock_vector_service, client, sample_search_results
    ):
        """Test erfolgreiche Document Vector Chunks Abfrage"""
        # Mock Document Service
        mock_document = Mock()
        mock_document.original_filename = "test_document.txt"
        mock_doc_service.get_document_by_id.return_value = mock_document

        # Mock Vector Service
        mock_vector_service.get_document_chunks = AsyncMock(
            return_value=sample_search_results
        )

        response = client.get("/api/v1/search/document/1/chunks")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        assert data[0]["document_id"] == 1
        assert data[0]["filename"] == "test_document.txt"

        mock_vector_service.get_document_chunks.assert_called_once_with(1)

    @patch("api.vector_search.document_service")
    def test_get_document_vector_chunks_not_found(self, mock_doc_service, client):
        """Test Document Vector Chunks - Document nicht gefunden"""
        mock_doc_service.get_document_by_id.return_value = None

        response = client.get("/api/v1/search/document/999/chunks")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_get_document_vector_chunks_service_error(
        self, mock_doc_service, mock_vector_service, client
    ):
        """Test Document Vector Chunks Service Error"""
        mock_document = Mock()
        mock_doc_service.get_document_by_id.return_value = mock_document
        mock_vector_service.get_document_chunks = AsyncMock(
            side_effect=Exception("Vector service error")
        )

        response = client.get("/api/v1/search/document/1/chunks")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to retrieve chunks" in data["detail"]

    @patch("api.vector_search.vector_service")
    def test_get_vector_database_stats_success(self, mock_vector_service, client):
        """Test erfolgreiche Vector Database Stats"""
        mock_stats = {
            "collection_name": "examcraft_documents",
            "total_chunks": 25,
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "persist_directory": "./chroma_db",
            "sample_document_id": 5,
            "sample_filename": "sample.pdf",
        }
        mock_vector_service.get_collection_stats.return_value = mock_stats

        response = client.get("/api/v1/search/stats")

        assert response.status_code == 200
        data = response.json()

        assert data["collection_name"] == "examcraft_documents"
        assert data["total_chunks"] == 25
        assert data["embedding_model"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert data["persist_directory"] == "./chroma_db"
        assert data["sample_document_id"] == 5
        assert data["sample_filename"] == "sample.pdf"

    @patch("api.vector_search.vector_service")
    def test_get_vector_database_stats_error(self, mock_vector_service, client):
        """Test Vector Database Stats Error"""
        mock_vector_service.get_collection_stats.side_effect = Exception(
            "Stats unavailable"
        )

        response = client.get("/api/v1/search/stats")

        assert response.status_code == 500
        data = response.json()
        assert "Failed to get stats" in data["detail"]

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_delete_document_vectors_success(
        self, mock_doc_service, mock_vector_service, client
    ):
        """Test erfolgreiche Vector Löschung"""
        # Mock Document Service
        mock_document = Mock()
        mock_document.doc_metadata = {"embedding_model": "test", "total_chunks": 5}
        mock_document.vector_collection = "doc_123"
        mock_doc_service.get_document_by_id.return_value = mock_document

        # Mock Database Session
        mock_db = Mock()

        # Mock Vector Service
        mock_vector_service.delete_document_chunks = AsyncMock(return_value=3)

        with patch("api.vector_search.get_db") as mock_get_db:
            mock_get_db.return_value = mock_db

            response = client.delete("/api/v1/search/document/123/vectors")

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Document vectors deleted successfully"
        assert data["document_id"] == 123
        assert data["deleted_chunks"] == 3

        # Verify vector collection was cleared
        assert mock_document.vector_collection is None
        mock_db.commit.assert_called_once()

    @patch("api.vector_search.document_service")
    def test_delete_document_vectors_not_found(self, mock_doc_service, client):
        """Test Vector Löschung - Document nicht gefunden"""
        mock_doc_service.get_document_by_id.return_value = None

        response = client.delete("/api/v1/search/document/999/vectors")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_reindex_document_vectors_success(
        self, mock_doc_service, mock_vector_service, client
    ):
        """Test erfolgreiche Document Reindexing"""
        # Mock Document Service
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        from models.document import DocumentStatus

        mock_document.status = DocumentStatus.PROCESSED
        mock_doc_service.get_document_by_id.return_value = mock_document

        mock_processing_result = {
            "document_id": 123,
            "docling_processing": {"total_chunks": 5},
            "vector_embeddings": {"total_chunks": 5, "embedding_dimension": 384},
        }
        mock_doc_service.process_document_with_vectors = AsyncMock(
            return_value=mock_processing_result
        )

        # Mock Vector Service
        mock_vector_service.delete_document_chunks = AsyncMock(return_value=3)

        with patch("api.vector_search.get_db") as mock_get_db:
            mock_get_db.return_value = Mock()

            response = client.post("/api/v1/search/reindex/123")

        assert response.status_code == 200
        data = response.json()

        assert data["message"] == "Document reindexed successfully"
        assert data["document_id"] == 123
        assert "processing_stats" in data

    @patch("api.vector_search.document_service")
    def test_reindex_document_not_found(self, mock_doc_service, client):
        """Test Reindexing - Document nicht gefunden"""
        mock_doc_service.get_document_by_id.return_value = None

        response = client.post("/api/v1/search/reindex/999")

        assert response.status_code == 404
        data = response.json()
        assert data["detail"] == "Document not found"

    @patch("api.vector_search.document_service")
    def test_reindex_document_not_processed(self, mock_doc_service, client):
        """Test Reindexing - Document nicht verarbeitet"""
        mock_document = Mock()
        from models.document import DocumentStatus

        mock_document.status = DocumentStatus.UPLOADED
        mock_doc_service.get_document_by_id.return_value = mock_document

        with patch("api.vector_search.get_db") as mock_get_db:
            mock_get_db.return_value = Mock()

            response = client.post("/api/v1/search/reindex/123")

        assert response.status_code == 400
        data = response.json()
        assert "Document must be processed before reindexing" in data["detail"]

    @patch("api.vector_search.vector_service")
    @patch("api.vector_search.document_service")
    def test_reindex_document_processing_failed(
        self, mock_doc_service, mock_vector_service, client
    ):
        """Test Reindexing - Processing fehlgeschlagen"""
        mock_document = Mock()
        mock_document.user_id = "demo_user"
        from models.document import DocumentStatus

        mock_document.status = DocumentStatus.PROCESSED
        mock_doc_service.get_document_by_id.return_value = mock_document
        mock_doc_service.process_document_with_vectors = AsyncMock(return_value=None)

        mock_vector_service.delete_document_chunks = AsyncMock(return_value=0)

        with patch("api.vector_search.get_db") as mock_get_db:
            mock_get_db.return_value = Mock()

            response = client.post("/api/v1/search/reindex/123")

        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Reindexing failed"

    def test_get_vector_service_info_success(self, client):
        """Test Vector Service Info Endpoint (Success)"""
        with patch("api.vector_search.get_service_info") as mock_get_service_info:
            with patch("api.vector_search.vector_service") as mock_service:
                mock_get_service_info.return_value = {
                    "service_type": "qdrant",
                    "service_class": "QdrantVectorService",
                    "service_module": "services.qdrant_vector_service",
                    "qdrant_url": "http://localhost:6333",
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "collection_name": "examcraft_documents",
                }
                mock_service.get_collection_stats.return_value = {
                    "collection_name": "examcraft_documents",
                    "total_chunks": 25,
                    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                    "qdrant_url": "http://localhost:6333",
                }

                response = client.get("/api/v1/search/service-info")

                assert response.status_code == 200
                data = response.json()

                assert "service_info" in data
                assert "collection_stats" in data
                assert "features" in data

                service_info = data["service_info"]
                assert service_info["service_type"] == "qdrant"
                assert service_info["service_class"] == "QdrantVectorService"
                assert service_info["qdrant_url"] == "http://localhost:6333"

                features = data["features"]
                assert features["async_operations"] is True
                assert features["similarity_search"] is True
                assert features["document_filtering"] is True

    def test_get_vector_service_info_error(self, client):
        """Test Vector Service Info Endpoint (Error)"""
        with patch("api.vector_search.get_service_info") as mock_get_service_info:
            with patch("api.vector_search.vector_service") as mock_service:
                mock_get_service_info.return_value = {"service_type": "qdrant"}
                mock_service.get_collection_stats.side_effect = Exception(
                    "Service unavailable"
                )

                response = client.get("/api/v1/search/service-info")

                assert (
                    response.status_code == 200
                )  # Endpoint returns 200 even on errors
                data = response.json()

                assert "error" in data
                assert "service_info" in data
                assert "Service unavailable" in data["error"]


class TestVectorSearchModels:
    """Test Suite für Vector Search Pydantic Models"""

    def test_search_query_model_valid(self):
        """Test SearchQuery Model Validation (Valid)"""
        from api.vector_search import SearchQuery

        # Minimale gültige Query
        query = SearchQuery(query="test")
        assert query.query == "test"
        assert query.n_results == 5  # Default
        assert query.document_ids is None  # Default

        # Vollständige Query
        query = SearchQuery(
            query="ExamCraft AI system", n_results=10, document_ids=[1, 2, 3]
        )
        assert query.query == "ExamCraft AI system"
        assert query.n_results == 10
        assert query.document_ids == [1, 2, 3]

    def test_search_query_model_invalid(self):
        """Test SearchQuery Model Validation (Invalid)"""
        from api.vector_search import SearchQuery
        from pydantic import ValidationError

        # Leere Query
        with pytest.raises(ValidationError):
            SearchQuery(query="")

        # Zu lange Query
        with pytest.raises(ValidationError):
            SearchQuery(query="x" * 1001)

        # Ungültige n_results
        with pytest.raises(ValidationError):
            SearchQuery(query="test", n_results=0)

        with pytest.raises(ValidationError):
            SearchQuery(query="test", n_results=51)

    def test_search_result_response_model(self):
        """Test SearchResultResponse Model"""
        from api.vector_search import SearchResultResponse

        result = SearchResultResponse(
            chunk_id="doc_1_chunk_0",
            document_id=1,
            content="Test content",
            similarity_score=0.85,
            metadata={"test": "data"},
            chunk_index=0,
            filename="test.txt",
        )

        assert result.chunk_id == "doc_1_chunk_0"
        assert result.document_id == 1
        assert result.content == "Test content"
        assert result.similarity_score == 0.85
        assert result.metadata == {"test": "data"}
        assert result.chunk_index == 0
        assert result.filename == "test.txt"

    def test_search_response_model(self):
        """Test SearchResponse Model"""
        from api.vector_search import SearchResponse, SearchResultResponse

        results = [
            SearchResultResponse(
                chunk_id="test_1",
                document_id=1,
                content="content",
                similarity_score=0.8,
                metadata={},
                chunk_index=0,
            )
        ]

        response = SearchResponse(
            query="test query", total_results=1, results=results, search_time_ms=150.5
        )

        assert response.query == "test query"
        assert response.total_results == 1
        assert len(response.results) == 1
        assert response.search_time_ms == 150.5

    def test_vector_stats_response_model(self):
        """Test VectorStatsResponse Model"""
        from api.vector_search import VectorStatsResponse

        stats = VectorStatsResponse(
            collection_name="test_collection",
            total_chunks=100,
            embedding_model="test-model",
            persist_directory="./test_db",
            sample_document_id=5,
            sample_filename="sample.txt",
        )

        assert stats.collection_name == "test_collection"
        assert stats.total_chunks == 100
        assert stats.embedding_model == "test-model"
        assert stats.persist_directory == "./test_db"
        assert stats.sample_document_id == 5
        assert stats.sample_filename == "sample.txt"
