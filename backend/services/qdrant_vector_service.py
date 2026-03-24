"""
Qdrant Vector Service (Core Package Placeholder)

This is a placeholder for the Core package.
Full Qdrant integration is available in the Premium package.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SearchResult:
    """Result from a similarity search (Placeholder)"""

    chunk_id: str
    document_id: int
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    chunk_index: int
