"""
Unit Tests für Vector Service Mock
"""

import pytest
import tempfile
import os
import json
from unittest.mock import Mock, patch, AsyncMock

from services.vector_service_mock import VectorService, SearchResult, EmbeddingStats
from services.docling_service import ProcessedDocument, DocumentChunk


class TestVectorService:
    """Test Suite für Vector Service Mock"""
    
    @pytest.fixture
    def temp_vector_dir(self):
        """Temporäres Vector Directory für Tests"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def vector_service(self, temp_vector_dir):
        """Vector Service Instanz für Tests"""
        return VectorService(
            persist_directory=temp_vector_dir,
            embedding_model="test-model",
            collection_name="test_collection"
        )
    
    @pytest.fixture
    def sample_processed_doc(self):
        """Sample ProcessedDocument für Tests"""
        chunks = [
            DocumentChunk(
                content="Dies ist der erste Test-Chunk mit wichtigen Informationen.",
                chunk_index=0,
                page_number=1,
                metadata={"test": "chunk1"}
            ),
            DocumentChunk(
                content="Der zweite Chunk enthält weitere relevante Daten für Tests.",
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
    
    def test_init(self, temp_vector_dir):
        """Test Vector Service Initialisierung"""
        service = VectorService(
            persist_directory=temp_vector_dir,
            embedding_model="custom-model",
            collection_name="custom_collection"
        )
        
        assert service.persist_directory == temp_vector_dir
        assert service.embedding_model_name == "custom-model"
        assert service.collection_name == "custom_collection"
        assert os.path.exists(temp_vector_dir)
        assert hasattr(service, '_storage')
        assert service._storage == {"chunks": {}, "documents": {}}
    
    def test_load_save_storage(self, vector_service):
        """Test Storage Load/Save Funktionalität"""
        # Füge Test-Daten hinzu
        test_data = {
            "chunks": {"test_chunk": {"content": "test"}},
            "documents": {"test_doc": {"id": 1}}
        }
        
        vector_service._storage = test_data
        vector_service._save_storage()
        
        # Erstelle neue Instanz und prüfe ob Daten geladen werden
        new_service = VectorService(
            persist_directory=vector_service.persist_directory,
            collection_name="test"
        )
        
        assert new_service._storage == test_data
    
    def test_get_or_create_collection(self, vector_service):
        """Test Collection Management"""
        # Default Collection
        collection = vector_service.get_or_create_collection()
        assert collection["name"] == "test_collection"
        
        # Custom Collection
        custom_collection = vector_service.get_or_create_collection("custom")
        assert custom_collection["name"] == "custom"
    
    @pytest.mark.asyncio
    async def test_create_embeddings(self, vector_service):
        """Test Embedding-Erstellung"""
        texts = [
            "Test text one",
            "Another test text",
            "Third test content"
        ]
        
        embeddings = await vector_service.create_embeddings(texts)
        
        assert len(embeddings) == 3
        assert len(embeddings[0]) == 384  # Embedding dimension
        assert all(isinstance(emb, list) for emb in embeddings)
        assert all(len(emb) == 384 for emb in embeddings)
        
        # Test konsistente Embeddings für gleichen Text
        embeddings2 = await vector_service.create_embeddings(["Test text one"])
        assert embeddings[0] == embeddings2[0]
    
    @pytest.mark.asyncio
    async def test_create_embeddings_empty(self, vector_service):
        """Test Embedding-Erstellung mit leerer Liste"""
        embeddings = await vector_service.create_embeddings([])
        assert embeddings == []
    
    @pytest.mark.asyncio
    async def test_add_document_chunks(self, vector_service, sample_processed_doc):
        """Test Document Chunks hinzufügen"""
        stats = await vector_service.add_document_chunks(sample_processed_doc)
        
        # Prüfe Statistiken
        assert isinstance(stats, EmbeddingStats)
        assert stats.total_chunks == 2
        assert stats.embedding_dimension == 384
        assert stats.model_name == "test-model"
        assert stats.processing_time > 0
        
        # Prüfe Storage
        assert len(vector_service._storage["chunks"]) == 2
        assert len(vector_service._storage["documents"]) == 1
        
        # Prüfe Chunk-Daten
        chunk1_id = "doc_123_chunk_0"
        assert chunk1_id in vector_service._storage["chunks"]
        
        chunk_data = vector_service._storage["chunks"][chunk1_id]
        assert chunk_data["document_id"] == 123
        assert chunk_data["content"] == "Dies ist der erste Test-Chunk mit wichtigen Informationen."
        assert chunk_data["chunk_index"] == 0
        assert len(chunk_data["embedding"]) == 384
        
        # Prüfe Document-Daten
        doc_data = vector_service._storage["documents"]["123"]
        assert doc_data["document_id"] == 123
        assert doc_data["filename"] == "test_document.txt"
        assert doc_data["total_chunks"] == 2
    
    def test_calculate_similarity(self, vector_service):
        """Test Similarity-Berechnung"""
        embedding1 = [1.0, 0.0, 0.0]
        embedding2 = [1.0, 0.0, 0.0]  # Identisch
        embedding3 = [0.0, 1.0, 0.0]  # Orthogonal
        embedding4 = [0.5, 0.5, 0.0]  # Ähnlich
        
        # Identische Embeddings
        similarity = vector_service._calculate_similarity(embedding1, embedding2)
        assert similarity == 1.0
        
        # Orthogonale Embeddings
        similarity = vector_service._calculate_similarity(embedding1, embedding3)
        assert similarity == 0.0
        
        # Ähnliche Embeddings
        similarity = vector_service._calculate_similarity(embedding1, embedding4)
        assert 0.0 < similarity < 1.0
        
        # Zero-Norm Handling
        zero_embedding = [0.0, 0.0, 0.0]
        similarity = vector_service._calculate_similarity(embedding1, zero_embedding)
        assert similarity == 0.0
    
    @pytest.mark.asyncio
    async def test_similarity_search(self, vector_service, sample_processed_doc):
        """Test Similarity Search"""
        # Erst Dokument hinzufügen
        await vector_service.add_document_chunks(sample_processed_doc)
        
        # Similarity Search durchführen
        results = await vector_service.similarity_search(
            query="Test-Chunk wichtigen Informationen",
            n_results=5
        )
        
        assert len(results) == 2  # Beide Chunks sollten gefunden werden
        assert all(isinstance(result, SearchResult) for result in results)
        
        # Results sollten sortiert sein (höchste Similarity zuerst)
        assert results[0].similarity_score >= results[1].similarity_score
        
        # Prüfe Result-Struktur
        first_result = results[0]
        assert first_result.document_id == 123
        assert first_result.similarity_score > 0
        assert isinstance(first_result.metadata, dict)
        assert first_result.chunk_index in [0, 1]
        
        # Mindestens ein Result sollte relevanten Content haben
        all_content = " ".join([r.content for r in results])
        assert "Test-Chunk" in all_content or "wichtigen" in all_content or "Informationen" in all_content
    
    @pytest.mark.asyncio
    async def test_similarity_search_with_document_filter(self, vector_service, sample_processed_doc):
        """Test Similarity Search mit Document-Filter"""
        await vector_service.add_document_chunks(sample_processed_doc)
        
        # Search mit korrekter Document ID
        results = await vector_service.similarity_search(
            query="Test",
            document_ids=[123],
            n_results=5
        )
        assert len(results) == 2
        
        # Search mit falscher Document ID
        results = await vector_service.similarity_search(
            query="Test",
            document_ids=[999],
            n_results=5
        )
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_get_document_chunks(self, vector_service, sample_processed_doc):
        """Test Document Chunks abrufen"""
        await vector_service.add_document_chunks(sample_processed_doc)
        
        results = await vector_service.get_document_chunks(123)
        
        assert len(results) == 2
        assert all(isinstance(result, SearchResult) for result in results)
        assert all(result.document_id == 123 for result in results)
        assert all(result.similarity_score == 1.0 for result in results)
        
        # Prüfe Sortierung nach chunk_index
        assert results[0].chunk_index == 0
        assert results[1].chunk_index == 1
        
        # Test mit nicht-existierender Document ID
        results = await vector_service.get_document_chunks(999)
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_delete_document_chunks(self, vector_service, sample_processed_doc):
        """Test Document Chunks löschen"""
        await vector_service.add_document_chunks(sample_processed_doc)
        
        # Prüfe dass Chunks existieren
        assert len(vector_service._storage["chunks"]) == 2
        assert len(vector_service._storage["documents"]) == 1
        
        # Lösche Chunks
        deleted_count = await vector_service.delete_document_chunks(123)
        
        assert deleted_count == 2
        assert len(vector_service._storage["chunks"]) == 0
        assert len(vector_service._storage["documents"]) == 0
        
        # Test mit nicht-existierender Document ID
        deleted_count = await vector_service.delete_document_chunks(999)
        assert deleted_count == 0
    
    def test_get_collection_stats_empty(self, vector_service):
        """Test Collection Statistiken (leer)"""
        stats = vector_service.get_collection_stats()
        
        assert stats["collection_name"] == "test_collection"
        assert stats["total_chunks"] == 0
        assert stats["total_documents"] == 0
        assert stats["embedding_model"] == "test-model"
        assert stats["persist_directory"] == vector_service.persist_directory
        assert "sample_document_id" not in stats
        assert "sample_filename" not in stats
    
    @pytest.mark.asyncio
    async def test_get_collection_stats_with_data(self, vector_service, sample_processed_doc):
        """Test Collection Statistiken (mit Daten)"""
        await vector_service.add_document_chunks(sample_processed_doc)
        
        stats = vector_service.get_collection_stats()
        
        assert stats["collection_name"] == "test_collection"
        assert stats["total_chunks"] == 2
        assert stats["total_documents"] == 1
        assert stats["sample_document_id"] == 123
        assert stats["sample_filename"] == "test_document.txt"
    
    def test_reset_collection(self, vector_service, sample_processed_doc):
        """Test Collection Reset"""
        # Füge Daten hinzu
        import asyncio
        asyncio.run(vector_service.add_document_chunks(sample_processed_doc))
        
        assert len(vector_service._storage["chunks"]) == 2
        assert len(vector_service._storage["documents"]) == 1
        
        # Reset Collection
        result = vector_service.reset_collection()
        
        assert result is True
        assert len(vector_service._storage["chunks"]) == 0
        assert len(vector_service._storage["documents"]) == 0
    
    def test_custom_collection_name(self, vector_service):
        """Test mit Custom Collection Name"""
        stats = vector_service.get_collection_stats("custom_collection")
        assert stats["collection_name"] == "custom_collection"
        
        result = vector_service.reset_collection("custom_collection")
        assert result is True


class TestSearchResult:
    """Test Suite für SearchResult Dataclass"""
    
    def test_search_result_creation(self):
        """Test SearchResult Erstellung"""
        result = SearchResult(
            chunk_id="test_chunk_1",
            document_id=123,
            content="Test content",
            similarity_score=0.85,
            metadata={"test": "data"},
            chunk_index=0
        )
        
        assert result.chunk_id == "test_chunk_1"
        assert result.document_id == 123
        assert result.content == "Test content"
        assert result.similarity_score == 0.85
        assert result.metadata == {"test": "data"}
        assert result.chunk_index == 0


class TestEmbeddingStats:
    """Test Suite für EmbeddingStats Dataclass"""
    
    def test_embedding_stats_creation(self):
        """Test EmbeddingStats Erstellung"""
        stats = EmbeddingStats(
            total_chunks=10,
            embedding_dimension=384,
            model_name="test-model",
            processing_time=1.5
        )
        
        assert stats.total_chunks == 10
        assert stats.embedding_dimension == 384
        assert stats.model_name == "test-model"
        assert stats.processing_time == 1.5
