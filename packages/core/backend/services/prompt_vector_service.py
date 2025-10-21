"""
Prompt Vector Service

Service for semantic search over prompts using Qdrant and OpenAI Embeddings.
"""

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    Distance,
    VectorParams,
)
from openai import OpenAI
import os
import uuid
from datetime import datetime

from models.prompt import Prompt


class PromptVectorService:
    """
    Service for semantic search over prompts with Qdrant.
    Uses OpenAI Embeddings for vectorization.
    """

    def __init__(self):
        self.qdrant_client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY"),
        )
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.collection_name = os.getenv(
            "QDRANT_PROMPTS_COLLECTION", "prompts_knowledge_base"
        )
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions

    def _ensure_collection_exists(self):
        """Creates collection if it doesn't exist"""
        try:
            self.qdrant_client.get_collection(self.collection_name)
        except Exception as e:
            # Only create if collection doesn't exist (not other errors)
            if "not found" in str(e).lower() or "does not exist" in str(e).lower():
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
                )
            # If collection already exists, silently continue

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generates OpenAI embedding for given text.

        Args:
            text: Text to vectorize

        Returns:
            Embedding vector (1536 dimensions)
        """
        response = self.openai_client.embeddings.create(
            model=self.embedding_model, input=text
        )
        return response.data[0].embedding

    async def add_prompt_to_index(self, prompt: Prompt) -> str:
        """
        Adds prompt to Qdrant collection.

        Args:
            prompt: Prompt SQLAlchemy Model

        Returns:
            Qdrant Point ID
        """
        self._ensure_collection_exists()

        # Combine relevant fields for better semantics
        combined_text = f"""
        Name: {prompt.name}
        Description: {prompt.description or ''}
        Category: {prompt.category}
        Use Case: {prompt.use_case or ''}
        Tags: {', '.join(prompt.tags) if prompt.tags else ''}
        Content: {prompt.content}
        """.strip()

        # Generate embedding
        embedding = self._generate_embedding(combined_text)

        # Create Qdrant Point
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id,
            vector=embedding,
            payload={
                "prompt_id": str(prompt.id),
                "name": prompt.name,
                "category": prompt.category,
                "use_case": prompt.use_case,
                "tags": prompt.tags or [],
                "content_preview": prompt.content[:500] if prompt.content else "",
                "version": prompt.version,
                "is_active": prompt.is_active,
                "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
                "tokens_estimated": prompt.tokens_estimated,
            },
        )

        # Upsert to Qdrant
        self.qdrant_client.upsert(
            collection_name=self.collection_name, points=[point]
        )

        return point_id

    async def search_prompts(
        self,
        query: str,
        category: Optional[str] = None,
        use_case: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 5,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search over prompts.

        Args:
            query: Natural language search query
            category: Optional filter by category
            use_case: Optional filter by use case
            tags: Optional filter by tags
            limit: Max number of results
            score_threshold: Minimum similarity (0-1)

        Returns:
            List of prompts with similarity scores
        """
        self._ensure_collection_exists()

        # Generate query embedding
        query_embedding = self._generate_embedding(query)

        # Build Qdrant Filter
        filter_conditions = []

        # Only active prompts
        filter_conditions.append(
            FieldCondition(key="is_active", match=MatchValue(value=True))
        )

        if category:
            filter_conditions.append(
                FieldCondition(key="category", match=MatchValue(value=category))
            )

        if use_case:
            filter_conditions.append(
                FieldCondition(key="use_case", match=MatchValue(value=use_case))
            )

        # Search in Qdrant
        search_result = self.qdrant_client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=Filter(must=filter_conditions) if filter_conditions else None,
        )

        # Format results
        results = []
        for hit in search_result:
            results.append(
                {
                    "prompt_id": hit.payload["prompt_id"],
                    "name": hit.payload["name"],
                    "category": hit.payload["category"],
                    "use_case": hit.payload.get("use_case"),
                    "tags": hit.payload.get("tags", []),
                    "content_preview": hit.payload.get("content_preview"),
                    "version": hit.payload.get("version"),
                    "similarity_score": hit.score,
                    "qdrant_point_id": hit.id,
                }
            )

        return results

    async def update_prompt_embedding(
        self, prompt: Prompt, qdrant_point_id: str
    ) -> None:
        """
        Updates embedding of an existing prompt.

        Args:
            prompt: Updated Prompt Model
            qdrant_point_id: Existing Point ID in Qdrant
        """
        # Combine text
        combined_text = f"""
        Name: {prompt.name}
        Description: {prompt.description or ''}
        Category: {prompt.category}
        Use Case: {prompt.use_case or ''}
        Tags: {', '.join(prompt.tags) if prompt.tags else ''}
        Content: {prompt.content}
        """.strip()

        # Generate new embedding
        embedding = self._generate_embedding(combined_text)

        # Update in Qdrant
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                PointStruct(
                    id=qdrant_point_id,
                    vector=embedding,
                    payload={
                        "prompt_id": str(prompt.id),
                        "name": prompt.name,
                        "category": prompt.category,
                        "use_case": prompt.use_case,
                        "tags": prompt.tags or [],
                        "content_preview": prompt.content[:500] if prompt.content else "",
                        "version": prompt.version,
                        "is_active": prompt.is_active,
                        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
                        "tokens_estimated": prompt.tokens_estimated,
                    },
                )
            ],
        )

    async def delete_prompt_from_index(self, qdrant_point_id: str) -> None:
        """
        Removes prompt from Qdrant index.

        Args:
            qdrant_point_id: Point ID in Qdrant
        """
        self.qdrant_client.delete(
            collection_name=self.collection_name, points_selector=[qdrant_point_id]
        )

    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Returns statistics about the Qdrant collection.

        Returns:
            Collection stats (vector count, etc.)
        """
        try:
            collection_info = self.qdrant_client.get_collection(
                collection_name=self.collection_name
            )
            return {
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
            }
        except Exception as e:
            return {"error": str(e)}

