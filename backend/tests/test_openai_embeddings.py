"""
Unit Tests für OpenAI Embeddings Integration
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import numpy as np

from services.qdrant_vector_service import QdrantVectorService


class TestOpenAIEmbeddings:
    """Test Suite für OpenAI Embeddings Integration"""
    
    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI Client für Tests"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.data = [Mock(embedding=[0.1] * 1536)]  # 1536 dimensions for text-embedding-3-small
        mock_client.embeddings.create.return_value = mock_response
        return mock_client
    
    @pytest.fixture
    def mock_qdrant_client(self):
        """Mock Qdrant Client für Tests"""
        mock_client = Mock()
        mock_client.collection_exists.return_value = False
        return mock_client
    
    def test_openai_embeddings_initialization(self, mock_qdrant_client, mock_openai_client):
        """Test OpenAI Embeddings Initialisierung"""
        with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
            with patch('services.qdrant_vector_service.OpenAI', return_value=mock_openai_client):
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                    service = QdrantVectorService(
                        qdrant_url="http://test:6333",
                        embedding_provider="openai",
                        embedding_model="text-embedding-3-small",
                        collection_name="test_collection"
                    )
                    
                    assert service.embedding_provider == "openai"
                    assert service.embedding_model == "text-embedding-3-small"
                    assert service.embedding_dimension == 1536
    
    def test_openai_embeddings_generation(self, mock_qdrant_client, mock_openai_client):
        """Test OpenAI Embeddings Generierung"""
        with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
            with patch('services.qdrant_vector_service.OpenAI', return_value=mock_openai_client):
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                    service = QdrantVectorService(
                        qdrant_url="http://test:6333",
                        embedding_provider="openai",
                        embedding_model="text-embedding-3-small",
                        collection_name="test_collection"
                    )
                    
                    # Generate embedding
                    embedding = service._generate_embedding("Test text")
                    
                    # Verify OpenAI was called
                    mock_openai_client.embeddings.create.assert_called_once()
                    call_args = mock_openai_client.embeddings.create.call_args
                    assert call_args[1]['model'] == 'text-embedding-3-small'
                    assert call_args[1]['input'] == 'Test text'
                    
                    # Verify embedding dimensions
                    assert len(embedding) == 1536
    
    def test_openai_embeddings_fallback_to_mock(self, mock_qdrant_client):
        """Test Fallback zu Mock Embeddings wenn OpenAI nicht verfügbar"""
        with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
            with patch('services.qdrant_vector_service.OPENAI_AVAILABLE', False):
                service = QdrantVectorService(
                    qdrant_url="http://test:6333",
                    embedding_provider="openai",
                    embedding_model="text-embedding-3-small",
                    collection_name="test_collection"
                )
                
                # Should fall back to mock embeddings
                assert service.embedding_provider == "mock"
                assert service.embedding_dimension == 384  # Mock uses 384 dimensions
    
    def test_openai_embeddings_error_handling(self, mock_qdrant_client, mock_openai_client):
        """Test Error Handling bei OpenAI API Fehlern"""
        # Simulate OpenAI API error
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")
        
        with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
            with patch('services.qdrant_vector_service.OpenAI', return_value=mock_openai_client):
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                    service = QdrantVectorService(
                        qdrant_url="http://test:6333",
                        embedding_provider="openai",
                        embedding_model="text-embedding-3-small",
                        collection_name="test_collection"
                    )
                    
                    # Should fall back to mock embeddings on error
                    embedding = service._generate_embedding("Test text")
                    
                    # Verify fallback to mock (384 dimensions)
                    assert len(embedding) == 384
    
    def test_openai_embeddings_batch_processing(self, mock_qdrant_client, mock_openai_client):
        """Test Batch Processing mit OpenAI Embeddings"""
        # Mock batch response
        mock_response = Mock()
        mock_response.data = [
            Mock(embedding=[0.1] * 1536),
            Mock(embedding=[0.2] * 1536),
            Mock(embedding=[0.3] * 1536)
        ]
        mock_openai_client.embeddings.create.return_value = mock_response
        
        with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
            with patch('services.qdrant_vector_service.OpenAI', return_value=mock_openai_client):
                with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                    service = QdrantVectorService(
                        qdrant_url="http://test:6333",
                        embedding_provider="openai",
                        embedding_model="text-embedding-3-small",
                        collection_name="test_collection"
                    )
                    
                    # Generate embeddings for multiple texts
                    texts = ["Text 1", "Text 2", "Text 3"]
                    embeddings = [service._generate_embedding(text) for text in texts]
                    
                    # Verify all embeddings generated
                    assert len(embeddings) == 3
                    assert all(len(emb) == 1536 for emb in embeddings)
    
    def test_openai_embeddings_different_models(self, mock_qdrant_client, mock_openai_client):
        """Test verschiedene OpenAI Embedding Modelle"""
        models_and_dimensions = [
            ("text-embedding-3-small", 1536),
            ("text-embedding-3-large", 3072),
            ("text-embedding-ada-002", 1536)
        ]
        
        for model, expected_dim in models_and_dimensions:
            # Mock response with correct dimensions
            mock_response = Mock()
            mock_response.data = [Mock(embedding=[0.1] * expected_dim)]
            mock_openai_client.embeddings.create.return_value = mock_response
            
            with patch('services.qdrant_vector_service.QdrantClient', return_value=mock_qdrant_client):
                with patch('services.qdrant_vector_service.OpenAI', return_value=mock_openai_client):
                    with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                        service = QdrantVectorService(
                            qdrant_url="http://test:6333",
                            embedding_provider="openai",
                            embedding_model=model,
                            collection_name="test_collection"
                        )
                        
                        assert service.embedding_model == model
                        
                        # Generate embedding
                        embedding = service._generate_embedding("Test")
                        assert len(embedding) == expected_dim

