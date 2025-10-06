"""
Unit Tests für Qdrant Vector Service
"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, AsyncMock, MagicMock

from services.qdrant_vector_service import QdrantVectorService, SearchResult, EmbeddingStats
from services.docling_service import ProcessedDocument, DocumentChunk


class TestQdrantVectorService:
    """Test Suite für Qdrant Vector Service"""
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant Client für Tests"""
        with patch('services.qdrant_vector_service.QdrantClient') as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def mock_sentence_transformer(self):
        """Mock Sentence Transformer für Tests"""
        with patch('services.qdrant_vector_service.SentenceTransformer') as mock_transformer_class:
            mock_transformer = Mock()
            mock_transformer.encode.return_value = [[0.1, 0.2, 0.3] * 128]  # 384 dimensions
            mock_transformer_class.return_value = mock_transformer
            yield mock_transformer
    
    @pytest.fixture
    def qdrant_service(self, mock_qdrant_client):
        """Qdrant Vector Service Instanz für Tests"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', True):
            with patch('services.qdrant_vector_service.SENTENCE_TRANSFORMERS_AVAILABLE', True):
                service = QdrantVectorService(
                    qdrant_url="http://test:6333",
                    embedding_model="test-model",
                    collection_name="test_collection"
                )
                return service
    
    @pytest.fixture
    def sample_processed_doc(self):
        """Sample ProcessedDocument für Tests"""
        chunks = [
            DocumentChunk(
                content="Dies ist der erste Test-Chunk mit wichtigen Informationen über Qdrant.",
                chunk_index=0,
                page_number=1,
                metadata={"test": "chunk1"}
            ),
            DocumentChunk(
                content="Der zweite Chunk enthält weitere relevante Daten für Qdrant Tests.",
                chunk_index=1,
                page_number=1,
                metadata={"test": "chunk2"}
            )
        ]
        
        return ProcessedDocument(
            document_id=123,
            filename="test_document.txt",
            mime_type="text/plain",
            total_pages=1,
            total_chunks=2,
            chunks=chunks,
            metadata={"test_doc": "metadata"},
            processing_time=0.1
        )
    
    def test_init_with_qdrant_available(self, mock_qdrant_client):
        """Test Qdrant Service Initialisierung mit verfügbarem Qdrant"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', True):
            service = QdrantVectorService(
                qdrant_url="http://test:6333",
                embedding_model="custom-model",
                collection_name="custom_collection"
            )
            
            assert service.qdrant_url == "http://test:6333"
            assert service.embedding_model_name == "custom-model"
            assert service.collection_name == "custom_collection"
            assert service.client is not None
    
    def test_init_without_qdrant_available(self):
        """Test Qdrant Service Initialisierung ohne verfügbares Qdrant"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', False):
            service = QdrantVectorService()
            
            assert service.client is None
            assert service.qdrant_url == "http://localhost:6333"
    
    def test_get_or_create_collection_new(self, qdrant_service, mock_qdrant_client):
        """Test Collection-Erstellung (neue Collection)"""
        # Mock: Collection existiert nicht
        mock_collections = Mock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        collection_name = qdrant_service.get_or_create_collection("new_collection")
        
        assert collection_name == "new_collection"
        mock_qdrant_client.create_collection.assert_called_once()
    
    def test_get_or_create_collection_existing(self, qdrant_service, mock_qdrant_client):
        """Test Collection-Erstellung (existierende Collection)"""
        # Mock: Collection existiert bereits
        mock_collection = Mock()
        mock_collection.name = "existing_collection"
        mock_collections = Mock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections
        
        collection_name = qdrant_service.get_or_create_collection("existing_collection")
        
        assert collection_name == "existing_collection"
        mock_qdrant_client.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_embeddings_with_model(self, qdrant_service, mock_sentence_transformer):
        """Test Embedding-Erstellung mit verfügbarem Model"""
        texts = ["Test text one", "Another test text"]
        
        # Mock das embedding_model property
        with patch.object(qdrant_service, 'embedding_model', mock_sentence_transformer):
            embeddings = await qdrant_service.create_embeddings(texts)
            
            assert len(embeddings) == 2
            mock_sentence_transformer.encode.assert_called_once_with(texts)
    
    @pytest.mark.asyncio
    async def test_create_embeddings_without_model(self, qdrant_service):
        """Test Embedding-Erstellung ohne verfügbares Model (Fallback)"""
        texts = ["Test text one", "Another test text"]
        
        # Mock das embedding_model property als None
        with patch.object(qdrant_service, 'embedding_model', None):
            embeddings = await qdrant_service.create_embeddings(texts)
            
            assert len(embeddings) == 2
            assert len(embeddings[0]) == 384  # Mock embedding dimension
    
    @pytest.mark.asyncio
    async def test_create_embeddings_empty_list(self, qdrant_service):
        """Test Embedding-Erstellung mit leerer Liste"""
        embeddings = await qdrant_service.create_embeddings([])
        assert len(embeddings) == 0
    
    @pytest.mark.asyncio
    async def test_add_document_chunks_success(self, qdrant_service, sample_processed_doc, mock_qdrant_client):
        """Test Document Chunks hinzufügen (erfolgreich)"""
        # Mock embeddings
        mock_embeddings = [[0.1, 0.2] * 192, [0.3, 0.4] * 192]  # 384 dimensions each
        
        with patch.object(qdrant_service, 'create_embeddings', return_value=mock_embeddings):
            with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
                stats = await qdrant_service.add_document_chunks(sample_processed_doc)
                
                # Prüfe Statistiken
                assert isinstance(stats, EmbeddingStats)
                assert stats.total_chunks == 2
                assert stats.embedding_dimension == 384
                assert stats.model_name == "test-model"
                assert stats.processing_time > 0
                
                # Prüfe Qdrant upsert call
                mock_qdrant_client.upsert.assert_called_once()
                call_args = mock_qdrant_client.upsert.call_args
                assert call_args[1]["collection_name"] == "test_collection"
                assert len(call_args[1]["points"]) == 2
    
    @pytest.mark.asyncio
    async def test_add_document_chunks_without_client(self, sample_processed_doc):
        """Test Document Chunks hinzufügen ohne Qdrant Client"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', False):
            service = QdrantVectorService()
            
            stats = await service.add_document_chunks(sample_processed_doc)
            
            # Sollte Fallback-Statistiken zurückgeben
            assert isinstance(stats, EmbeddingStats)
            assert stats.total_chunks == 2
            assert stats.embedding_dimension == 384
    
    @pytest.mark.asyncio
    async def test_similarity_search_success(self, qdrant_service, mock_qdrant_client):
        """Test erfolgreiche Similarity Search"""
        # Mock search results
        mock_result = Mock()
        mock_result.id = "doc_123_chunk_0"
        mock_result.score = 0.85
        mock_result.payload = {
            "document_id": 123,
            "content": "Test content",
            "chunk_index": 0,
            "filename": "test.txt"
        }
        mock_qdrant_client.search.return_value = [mock_result]
        
        # Mock embeddings
        mock_embeddings = [[0.1, 0.2] * 192]  # 384 dimensions
        
        with patch.object(qdrant_service, 'create_embeddings', return_value=mock_embeddings):
            with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
                results = await qdrant_service.similarity_search("test query", n_results=5)
                
                assert len(results) == 1
                assert isinstance(results[0], SearchResult)
                assert results[0].chunk_id == "doc_123_chunk_0"
                assert results[0].document_id == 123
                assert results[0].similarity_score == 0.85
                assert results[0].content == "Test content"
    
    @pytest.mark.asyncio
    async def test_similarity_search_with_document_filter(self, qdrant_service, mock_qdrant_client):
        """Test Similarity Search mit Document Filter"""
        mock_qdrant_client.search.return_value = []
        mock_embeddings = [[0.1, 0.2] * 192]
        
        with patch.object(qdrant_service, 'create_embeddings', return_value=mock_embeddings):
            with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
                await qdrant_service.similarity_search(
                    "test query", 
                    document_ids=[123, 456]
                )
                
                # Prüfe dass Filter verwendet wurde
                call_args = mock_qdrant_client.search.call_args
                assert call_args[1]["query_filter"] is not None
    
    @pytest.mark.asyncio
    async def test_similarity_search_without_client(self):
        """Test Similarity Search ohne Qdrant Client"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', False):
            service = QdrantVectorService()
            
            results = await service.similarity_search("test query")
            
            assert results == []
    
    @pytest.mark.asyncio
    async def test_get_document_chunks_success(self, qdrant_service, mock_qdrant_client):
        """Test Document Chunks abrufen (erfolgreich)"""
        # Mock scroll results
        mock_point = Mock()
        mock_point.id = "doc_123_chunk_0"
        mock_point.payload = {
            "document_id": 123,
            "content": "Test content",
            "chunk_index": 0,
            "filename": "test.txt"
        }
        mock_qdrant_client.scroll.return_value = ([mock_point], None)
        
        with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
            results = await qdrant_service.get_document_chunks(123)
            
            assert len(results) == 1
            assert isinstance(results[0], SearchResult)
            assert results[0].document_id == 123
            assert results[0].similarity_score == 1.0  # Direct query
    
    @pytest.mark.asyncio
    async def test_delete_document_chunks_success(self, qdrant_service, mock_qdrant_client):
        """Test Document Chunks löschen (erfolgreich)"""
        # Mock count result
        mock_count_result = Mock()
        mock_count_result.count = 3
        mock_qdrant_client.count.return_value = mock_count_result
        
        with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
            deleted_count = await qdrant_service.delete_document_chunks(123)
            
            assert deleted_count == 3
            mock_qdrant_client.delete.assert_called_once()
    
    def test_get_collection_stats_success(self, qdrant_service, mock_qdrant_client):
        """Test Collection Statistiken abrufen (erfolgreich)"""
        # Mock collection info
        mock_collection_info = Mock()
        mock_collection_info.points_count = 10
        mock_qdrant_client.get_collection.return_value = mock_collection_info
        
        # Mock scroll for sample data
        mock_point = Mock()
        mock_point.payload = {"document_id": 123, "filename": "test.txt"}
        mock_qdrant_client.scroll.return_value = ([mock_point], None)
        
        with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
            stats = qdrant_service.get_collection_stats()
            
            assert stats["collection_name"] == "test_collection"
            assert stats["total_chunks"] == 10
            assert stats["embedding_model"] == "test-model"
            assert stats["qdrant_url"] == "http://test:6333"
            assert stats["sample_document_id"] == 123
            assert stats["sample_filename"] == "test.txt"
    
    def test_get_collection_stats_without_client(self):
        """Test Collection Statistiken ohne Qdrant Client"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', False):
            service = QdrantVectorService()
            
            stats = service.get_collection_stats()
            
            assert stats["total_chunks"] == 0
            assert "qdrant_url" in stats
    
    def test_reset_collection_success(self, qdrant_service, mock_qdrant_client):
        """Test Collection Reset (erfolgreich)"""
        with patch.object(qdrant_service, 'get_or_create_collection', return_value="test_collection"):
            result = qdrant_service.reset_collection()
            
            assert result is True
            mock_qdrant_client.delete_collection.assert_called_once()
    
    def test_reset_collection_without_client(self):
        """Test Collection Reset ohne Qdrant Client"""
        with patch('services.qdrant_vector_service.QDRANT_AVAILABLE', False):
            service = QdrantVectorService()
            
            result = service.reset_collection()
            
            assert result is False
