"""
Prompts API Endpoints

API for semantic search and management of the Prompt Knowledge Base.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, Field

from services.prompt_vector_service import PromptVectorService
from database import get_db
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/v1/prompts", tags=["prompts"])


class PromptSearchRequest(BaseModel):
    """Request model for semantic prompt search"""

    query: str = Field(
        ..., min_length=3, description="Natural language search query"
    )
    category: Optional[str] = Field(None, description="Filter by category")
    use_case: Optional[str] = Field(None, description="Filter by use case")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(5, ge=1, le=20, description="Max number of results")
    score_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity score"
    )


class PromptSearchResult(BaseModel):
    """Response model for prompt search results"""

    prompt_id: str
    name: str
    category: str
    use_case: Optional[str]
    tags: List[str]
    content_preview: str
    version: int
    similarity_score: float


class CollectionStats(BaseModel):
    """Response model for collection statistics"""

    vectors_count: Optional[int] = None
    points_count: Optional[int] = None
    status: Optional[str] = None
    error: Optional[str] = None


def get_vector_service() -> PromptVectorService:
    """Dependency injection for PromptVectorService"""
    return PromptVectorService()


@router.post("/search", response_model=List[PromptSearchResult])
async def search_prompts(
    request: PromptSearchRequest, vector_service: PromptVectorService = Depends(get_vector_service)
):
    """
    Semantic search over Prompt Knowledge Base.

    Example queries:
    - "Find a prompt for generating multiple choice questions"
    - "Prompt for chatbot with document context"
    - "System prompt for Bloom Taxonomy Level 4"

    Returns prompts ranked by semantic similarity to the query.
    """
    try:
        results = await vector_service.search_prompts(
            query=request.query,
            category=request.category,
            use_case=request.use_case,
            tags=request.tags,
            limit=request.limit,
            score_threshold=request.score_threshold,
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/stats", response_model=CollectionStats)
async def get_collection_stats(
    vector_service: PromptVectorService = Depends(get_vector_service)
):
    """
    Get statistics about the Qdrant collection.

    Returns:
    - vectors_count: Number of vectors in collection
    - points_count: Number of points in collection
    - status: Collection status
    """
    stats = await vector_service.get_collection_stats()
    return stats

