"""
Vector Service Factory (Core Package Placeholder)

This is a placeholder for the Core package.
Full vector search functionality is available in the Premium package.
"""

from typing import Optional


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

    def close(self):
        """No-op for placeholder"""
        pass


# Singleton instance
_vector_service: Optional[VectorServicePlaceholder] = None


def get_vector_service() -> VectorServicePlaceholder:
    """
    Get the vector service instance (placeholder in Core package)

    Returns:
        VectorServicePlaceholder: Placeholder service that raises NotImplementedError
    """
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorServicePlaceholder()
    return _vector_service


# Alias for backward compatibility
vector_service = get_vector_service()
