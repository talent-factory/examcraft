"""
Vector Service Factory für ExamCraft AI
Versucht Premium-Service zu nutzen, falls verfügbar.
Fällt auf Placeholder zurück, wenn Premium nicht installiert.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


class VectorServicePlaceholder:
    """
    Placeholder Vector Service for Core Package

    Raises NotImplementedError for all vector operations.
    Premium package provides full ChromaDB/Qdrant integration.
    """

    def __init__(self):
        self.service_type = "placeholder"

    async def add_document(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package. "
            "Please upgrade to use document embedding and semantic search."
        )

    async def add_document_chunks(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package. "
            "Please upgrade to use document embedding and semantic search."
        )

    async def search(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package. "
            "Please upgrade to use semantic search functionality."
        )

    async def delete_document(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package."
        )

    async def get_collection_info(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package."
        )

    async def get_document_chunks(self, *args, **kwargs):
        raise NotImplementedError(
            "Vector search is only available in the Premium package."
        )

    def close(self):
        """No-op for placeholder"""
        pass


# Singleton instance
_vector_service: Optional[Any] = None


def get_vector_service():
    """
    Get the vector service instance.
    Tries to use Premium package service first, falls back to placeholder.

    Returns:
        Vector service instance (Premium or Placeholder)
    """
    global _vector_service
    if _vector_service is not None:
        return _vector_service

    # Try to import Premium vector service
    try:
        from premium.services.vector_service_factory import (
            get_vector_service as get_premium_vector_service,
        )

        _vector_service = get_premium_vector_service()
        logger.info(f"Using Premium vector service: {type(_vector_service).__name__}")
        return _vector_service
    except ImportError as e:
        logger.warning(f"Premium vector service not available: {e}")

    # Fallback to placeholder
    logger.info("Using placeholder vector service (Premium not available)")
    _vector_service = VectorServicePlaceholder()
    return _vector_service


# Alias for backward compatibility
vector_service = get_vector_service()
