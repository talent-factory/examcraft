"""
Prompts API Endpoints

API for semantic search and management of the Prompt Knowledge Base.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from services.prompt_vector_service import PromptVectorService
from services.prompt_service import PromptService
from database import get_db
from sqlalchemy.orm import Session
from models.prompt import Prompt, PromptTemplate

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


class TemplateVariablesResponse(BaseModel):
    """Response model for template variable extraction"""

    prompt_id: str
    variables: List[str] = Field(description="List of template variable names")
    prompt_content_preview: str = Field(description="First 200 chars of prompt content")


class PromptRenderRequest(BaseModel):
    """Request model for rendering a prompt with variables"""

    prompt_id: Optional[str] = Field(None, description="Prompt ID to render (optional if content provided)")
    prompt_content: Optional[str] = Field(None, description="Prompt content to render (optional if prompt_id provided)")
    variables: Dict[str, Any] = Field(description="Variable values for template rendering")
    strict: bool = Field(False, description="If True, raise error on undefined variables")


class PromptRenderResponse(BaseModel):
    """Response model for rendered prompt"""

    rendered_content: str = Field(description="Rendered prompt text")
    variables_used: List[str] = Field(description="List of variables that were rendered")


def get_vector_service() -> PromptVectorService:
    """Dependency injection for PromptVectorService"""
    return PromptVectorService()


def get_prompt_service(db: Session = Depends(get_db)) -> PromptService:
    """Dependency injection for PromptService"""
    return PromptService(db)


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


# CRUD Endpoints for Prompts

@router.get("", response_model=List[dict])
async def list_prompts(
    category: Optional[str] = None,
    use_case: Optional[str] = None,
    is_active: Optional[bool] = None,
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    List all prompts with optional filters.

    Query Parameters:
    - category: Filter by category (system_prompt, user_prompt, few_shot_example, template)
    - use_case: Filter by use case
    - is_active: Filter by active status
    """
    try:
        prompts = prompt_service.list_prompts(
            category=category,
            use_case=use_case,
            is_active=is_active
        )

        # Convert to dict for JSON serialization
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "content": p.content,
                "description": p.description,
                "category": p.category,
                "tags": p.tags or [],
                "use_case": p.use_case,
                "version": p.version,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                "usage_count": p.usage_count or 0,
                "tokens_estimated": p.tokens_estimated,
                "parent_id": str(p.parent_id) if p.parent_id else None
            }
            for p in prompts
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list prompts: {str(e)}")


@router.get("/templates", response_model=List[dict])
async def list_templates(
    db: Session = Depends(get_db)
):
    """
    List all prompt templates.
    """
    try:
        templates = db.query(PromptTemplate).filter(PromptTemplate.is_active == True).all()

        return [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "template_content": t.template,
                "variables": list(t.variables.keys()) if t.variables else [],
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None
            }
            for t in templates
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list templates: {str(e)}")


@router.get("/{prompt_id}", response_model=dict)
async def get_prompt(
    prompt_id: str,
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Get a single prompt by ID.
    """
    try:
        prompt = prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        return {
            "id": str(prompt.id),
            "name": prompt.name,
            "content": prompt.content,
            "description": prompt.description,
            "category": prompt.category,
            "tags": prompt.tags or [],
            "use_case": prompt.use_case,
            "version": prompt.version,
            "is_active": prompt.is_active,
            "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
            "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
            "usage_count": prompt.usage_count or 0,
            "tokens_estimated": prompt.tokens_estimated,
            "parent_id": str(prompt.parent_id) if prompt.parent_id else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt: {str(e)}")


@router.get("/{prompt_id}/variables", response_model=TemplateVariablesResponse)
async def extract_template_variables(
    prompt_id: str,
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Extract template variables from a prompt's content.

    Returns a list of variable names found in the prompt using Jinja2 syntax.

    Example:
    - Prompt content: "Generate {{count}} questions about {{topic}}"
    - Returns: ["count", "topic"]
    """
    try:
        prompt = prompt_service.get_prompt_by_id(prompt_id)
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        variables = prompt_service.extract_template_variables(prompt.content)

        return TemplateVariablesResponse(
            prompt_id=str(prompt.id),
            variables=variables,
            prompt_content_preview=prompt.content[:200] + ("..." if len(prompt.content) > 200 else "")
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract variables: {str(e)}"
        )


@router.post("/render-preview", response_model=PromptRenderResponse)
async def render_prompt_preview(
    request: PromptRenderRequest,
    prompt_service: PromptService = Depends(get_prompt_service)
):
    """
    Render a prompt with given variables for preview.

    Can render either:
    1. An existing prompt by ID (provide prompt_id)
    2. Custom prompt content (provide prompt_content)

    Example request:
    ```json
    {
      "prompt_id": "uuid-here",
      "variables": {
        "count": 5,
        "topic": "Python Programming",
        "difficulty": "medium"
      },
      "strict": false
    }
    ```

    Returns the rendered prompt text with variables replaced.
    """
    try:
        # Validate request
        if not request.prompt_id and not request.prompt_content:
            raise HTTPException(
                status_code=400,
                detail="Either prompt_id or prompt_content must be provided"
            )

        # Get prompt content
        if request.prompt_id:
            prompt = prompt_service.get_prompt_by_id(request.prompt_id)
            if not prompt:
                raise HTTPException(status_code=404, detail="Prompt not found")
            prompt_content = prompt.content
        else:
            prompt_content = request.prompt_content

        # Extract variables for response
        variables_in_template = prompt_service.extract_template_variables(prompt_content)

        # Render prompt
        rendered = prompt_service.render_prompt_with_jinja2(
            prompt_content,
            request.variables,
            strict=request.strict
        )

        return PromptRenderResponse(
            rendered_content=rendered,
            variables_used=variables_in_template
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to render prompt: {str(e)}"
        )

