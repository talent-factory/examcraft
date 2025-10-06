"""
Unit Tests für Vector Service Factory
"""

import pytest
import os
from unittest.mock import Mock, patch

from services.vector_service_factory import create_vector_service, get_service_info


class TestVectorServiceFactory:
    """Test Suite für Vector Service Factory"""
    
    def test_create_vector_service_qdrant_default(self):
        """Test Vector Service Factory mit Qdrant (Default)"""
        with patch.dict(os.environ, {}, clear=True):  # Keine ENV vars
            with patch('services.vector_service_factory.QdrantVectorService') as mock_qdrant:
                mock_service = Mock()
                mock_qdrant.return_value = mock_service
                
                service = create_vector_service()
                
                assert service == mock_service
                mock_qdrant.assert_called_once_with(qdrant_url="http://localhost:6333")
    
    def test_create_vector_service_qdrant_explicit(self):
        """Test Vector Service Factory mit explizitem Qdrant"""
        with patch.dict(os.environ, {
            'VECTOR_SERVICE_TYPE': 'qdrant',
            'QDRANT_URL': 'http://custom:6333'
        }):
            with patch('services.vector_service_factory.QdrantVectorService') as mock_qdrant:
                mock_service = Mock()
                mock_qdrant.return_value = mock_service
                
                service = create_vector_service()
                
                assert service == mock_service
                mock_qdrant.assert_called_once_with(qdrant_url="http://custom:6333")
    
    def test_create_vector_service_chromadb(self):
        """Test Vector Service Factory mit ChromaDB"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'chromadb'}):
            with patch('services.vector_service_factory.VectorService') as mock_chromadb:
                mock_service = Mock()
                mock_chromadb.return_value = mock_service
                
                service = create_vector_service()
                
                assert service == mock_service
                mock_chromadb.assert_called_once()
    
    def test_create_vector_service_mock(self):
        """Test Vector Service Factory mit Mock Service"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'mock'}):
            with patch('services.vector_service_factory.VectorService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                service = create_vector_service()
                
                assert service == mock_service
                mock_service_class.assert_called_once()
    
    def test_create_vector_service_fallback_chromadb_to_mock(self):
        """Test Fallback von Qdrant zu ChromaDB zu Mock"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'qdrant'}):
            # Mock ImportError für Qdrant
            with patch('services.vector_service_factory.QdrantVectorService', side_effect=ImportError("Qdrant not available")):
                # Mock ImportError für ChromaDB
                with patch('services.vector_service_factory.VectorService', side_effect=ImportError("ChromaDB not available")):
                    # Mock erfolgreiche Mock Service Import
                    with patch('services.vector_service_factory.VectorService') as mock_service_class:
                        mock_service = Mock()
                        mock_service_class.return_value = mock_service
                        
                        service = create_vector_service()
                        
                        assert service == mock_service
    
    def test_create_vector_service_unknown_type_fallback(self):
        """Test Fallback bei unbekanntem Service Type"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'unknown_service'}):
            with patch('services.vector_service_factory.VectorService') as mock_service_class:
                mock_service = Mock()
                mock_service_class.return_value = mock_service
                
                service = create_vector_service()
                
                assert service == mock_service
    
    def test_get_service_info_qdrant(self):
        """Test Service Info für Qdrant Service"""
        mock_service = Mock()
        mock_service.__class__.__name__ = "QdrantVectorService"
        mock_service.__class__.__module__ = "services.qdrant_vector_service"
        mock_service.qdrant_url = "http://localhost:6333"
        mock_service.embedding_model_name = "test-model"
        mock_service.collection_name = "test_collection"
        
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'qdrant'}):
            with patch('services.vector_service_factory.vector_service', mock_service):
                info = get_service_info()
                
                assert info["service_type"] == "qdrant"
                assert info["service_class"] == "QdrantVectorService"
                assert info["service_module"] == "services.qdrant_vector_service"
                assert info["qdrant_url"] == "http://localhost:6333"
                assert info["embedding_model"] == "test-model"
                assert info["collection_name"] == "test_collection"
    
    def test_get_service_info_chromadb(self):
        """Test Service Info für ChromaDB Service"""
        mock_service = Mock()
        mock_service.__class__.__name__ = "VectorService"
        mock_service.__class__.__module__ = "services.vector_service"
        mock_service.persist_directory = "./chroma_db"
        mock_service.embedding_model_name = "test-model"
        mock_service.collection_name = "test_collection"
        
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'chromadb'}):
            with patch('services.vector_service_factory.vector_service', mock_service):
                info = get_service_info()
                
                assert info["service_type"] == "chromadb"
                assert info["service_class"] == "VectorService"
                assert info["service_module"] == "services.vector_service"
                assert info["persist_directory"] == "./chroma_db"
                assert info["embedding_model"] == "test-model"
                assert info["collection_name"] == "test_collection"
    
    def test_get_service_info_mock(self):
        """Test Service Info für Mock Service"""
        mock_service = Mock()
        mock_service.__class__.__name__ = "VectorService"
        mock_service.__class__.__module__ = "services.vector_service_mock"
        mock_service.persist_directory = "./mock_vector_db"
        mock_service.embedding_model_name = "mock-model"
        mock_service.collection_name = "test_collection"
        
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'mock'}):
            with patch('services.vector_service_factory.vector_service', mock_service):
                info = get_service_info()
                
                assert info["service_type"] == "mock"
                assert info["service_class"] == "VectorService"
                assert info["service_module"] == "services.vector_service_mock"
                assert info["persist_directory"] == "./mock_vector_db"
                assert info["embedding_model"] == "mock-model"
                assert info["collection_name"] == "test_collection"
    
    def test_get_service_info_minimal(self):
        """Test Service Info mit minimalen Attributen"""
        mock_service = Mock()
        mock_service.__class__.__name__ = "MinimalService"
        mock_service.__class__.__module__ = "services.minimal"
        # Keine zusätzlichen Attribute
        del mock_service.qdrant_url
        del mock_service.persist_directory
        del mock_service.embedding_model_name
        del mock_service.collection_name
        
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'minimal'}):
            with patch('services.vector_service_factory.vector_service', mock_service):
                info = get_service_info()
                
                assert info["service_type"] == "minimal"
                assert info["service_class"] == "MinimalService"
                assert info["service_module"] == "services.minimal"
                # Keine zusätzlichen Keys sollten vorhanden sein
                assert "qdrant_url" not in info
                assert "persist_directory" not in info
                assert "embedding_model" not in info
                assert "collection_name" not in info


class TestVectorServiceFactoryIntegration:
    """Integration Tests für Vector Service Factory"""
    
    def test_factory_creates_working_service(self):
        """Test dass Factory einen funktionierenden Service erstellt"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'mock'}):
            service = create_vector_service()
            
            # Service sollte grundlegende Methoden haben
            assert hasattr(service, 'get_collection_stats')
            assert hasattr(service, 'reset_collection')
            assert callable(service.get_collection_stats)
            assert callable(service.reset_collection)
    
    def test_get_vector_service_dependency_injection(self):
        """Test Dependency Injection Function"""
        from services.vector_service_factory import get_vector_service
        
        service = get_vector_service()
        
        # Sollte eine Service-Instanz zurückgeben
        assert service is not None
        assert hasattr(service, 'get_collection_stats')
    
    def test_service_info_matches_actual_service(self):
        """Test dass Service Info mit tatsächlichem Service übereinstimmt"""
        with patch.dict(os.environ, {'VECTOR_SERVICE_TYPE': 'mock'}):
            service = create_vector_service()
            info = get_service_info()
            
            # Service Info sollte mit tatsächlichem Service übereinstimmen
            assert info["service_class"] == service.__class__.__name__
            assert info["service_module"] == service.__class__.__module__
