"""
Vector Service Factory für ExamCraft AI
Ermöglicht dynamische Auswahl zwischen verschiedenen Vector Database Implementierungen
"""

import os
import logging
from typing import Union

logger = logging.getLogger(__name__)


def create_vector_service() -> Union['QdrantVectorService', 'VectorService', 'VectorService']:
    """
    Factory function für Vector Service basierend auf Environment Variables
    
    Environment Variables:
    - VECTOR_SERVICE_TYPE: "qdrant", "chromadb", oder "mock" (default: "qdrant")
    - QDRANT_URL: URL für Qdrant Service (default: "http://localhost:6333")
    
    Returns:
        Vector Service Instanz
    """
    service_type = os.getenv("VECTOR_SERVICE_TYPE", "qdrant").lower()
    
    if service_type == "qdrant":
        try:
            from services.qdrant_vector_service import QdrantVectorService
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            embedding_provider = os.getenv("EMBEDDING_PROVIDER", "openai")  # "openai" or "sentence-transformers"
            embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")  # OpenAI default

            service = QdrantVectorService(
                qdrant_url=qdrant_url,
                embedding_provider=embedding_provider,
                embedding_model=embedding_model
            )
            logger.info(f"Using QdrantVectorService at {qdrant_url} with {embedding_provider} provider")
            return service
        except ImportError as e:
            logger.warning(f"Failed to import QdrantVectorService: {e}")
            logger.info("Falling back to ChromaDB service")
            service_type = "chromadb"
    
    if service_type == "chromadb":
        try:
            from services.vector_service import VectorService
            service = VectorService()
            logger.info("Using ChromaDB VectorService")
            return service
        except ImportError as e:
            logger.warning(f"Failed to import ChromaDB VectorService: {e}")
            logger.info("Falling back to Mock service")
            service_type = "mock"
    
    if service_type == "mock":
        try:
            from services.vector_service_mock import VectorService
            service = VectorService()
            logger.info("Using Mock VectorService")
            return service
        except ImportError as e:
            logger.error(f"Failed to import Mock VectorService: {e}")
            raise RuntimeError("No vector service implementation available")
    
    # Fallback für unbekannte Service Types
    logger.warning(f"Unknown vector service type: {service_type}, falling back to mock")
    from services.vector_service_mock import VectorService
    return VectorService()


# Globale Service Instanz
vector_service = create_vector_service()


def get_vector_service():
    """
    Dependency injection function für FastAPI
    
    Returns:
        Vector Service Instanz
    """
    return vector_service


def get_service_info() -> dict:
    """
    Hole Informationen über den aktuell verwendeten Vector Service
    
    Returns:
        Dictionary mit Service-Informationen
    """
    service_type = os.getenv("VECTOR_SERVICE_TYPE", "qdrant").lower()
    
    info = {
        "service_type": service_type,
        "service_class": vector_service.__class__.__name__,
        "service_module": vector_service.__class__.__module__
    }
    
    # Füge spezifische Informationen hinzu
    if hasattr(vector_service, 'qdrant_url'):
        info["qdrant_url"] = vector_service.qdrant_url
    elif hasattr(vector_service, 'persist_directory'):
        info["persist_directory"] = vector_service.persist_directory
    
    if hasattr(vector_service, 'embedding_model_name'):
        info["embedding_model"] = vector_service.embedding_model_name
    
    if hasattr(vector_service, 'collection_name'):
        info["collection_name"] = vector_service.collection_name
    
    return info
