"""
Service for dynamic Prompt Management.

Combines PostgreSQL for structured queries and Qdrant for semantic search.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime
import uuid

from models.prompt import Prompt, PromptTemplate, PromptUsageLog
from services.prompt_vector_service import PromptVectorService


class PromptService:
    """
    Service for dynamic prompt management.
    Combines PostgreSQL for structured queries and Qdrant for semantic search.
    """

    def __init__(self, db: Session):
        self.db = db
        self.vector_service = PromptVectorService()

    def list_prompts(
        self,
        category: Optional[str] = None,
        use_case: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Prompt]:
        """
        List all prompts with optional filters.

        Args:
            category: Filter by category
            use_case: Filter by use case
            is_active: Filter by active status

        Returns:
            List of Prompt objects
        """
        query = self.db.query(Prompt)

        if category:
            query = query.filter(Prompt.category == category)
        if use_case:
            query = query.filter(Prompt.use_case == use_case)
        if is_active is not None:
            query = query.filter(Prompt.is_active == is_active)

        return query.order_by(desc(Prompt.created_at)).all()

    def get_prompt_by_id(self, prompt_id: str) -> Optional[Prompt]:
        """
        Get a single prompt by ID.

        Args:
            prompt_id: Prompt UUID

        Returns:
            Prompt object or None
        """
        return self.db.query(Prompt).filter(Prompt.id == prompt_id).first()

    def get_prompt_by_name(
        self, name: str, version: Optional[int] = None
    ) -> Optional[Prompt]:
        """
        Load prompt by name (and optional version).

        Args:
            name: Unique prompt name
            version: Optional version number (default: latest active)

        Returns:
            Prompt Model or None
        """
        query = self.db.query(Prompt).filter(Prompt.name == name)

        if version:
            query = query.filter(Prompt.version == version)
        else:
            # Latest active version
            query = query.filter(Prompt.is_active == True).order_by(
                desc(Prompt.version)
            )

        return query.first()

    def get_prompt_for_use_case(
        self,
        use_case: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Prompt]:
        """
        Find best prompt for given use case.

        Args:
            use_case: Use Case Identifier
            category: Optional category filter
            tags: Optional tag filter

        Returns:
            Best matching Prompt
        """
        query = self.db.query(Prompt).filter(
            and_(Prompt.use_case == use_case, Prompt.is_active == True)
        )

        if category:
            query = query.filter(Prompt.category == category)

        if tags:
            # PostgreSQL Array overlap operator
            from sqlalchemy.dialects.postgresql import ARRAY
            from sqlalchemy import cast, String

            for tag in tags:
                query = query.filter(Prompt.tags.any(tag))

        # Order by usage_count (popular prompts first) then by version
        query = query.order_by(desc(Prompt.usage_count), desc(Prompt.version))

        return query.first()

    async def search_prompts_semantically(
        self, query: str, use_case: Optional[str] = None, limit: int = 5
    ) -> List[Prompt]:
        """
        Semantic search over prompts with Qdrant.

        Args:
            query: Natural language description
            use_case: Optional use case filter
            limit: Max results

        Returns:
            List of Prompts sorted by relevance
        """
        # Semantic search via Qdrant
        results = await self.vector_service.search_prompts(
            query=query, use_case=use_case, limit=limit
        )

        # Load full Prompts from PostgreSQL
        prompt_ids = [uuid.UUID(r["prompt_id"]) for r in results]
        prompts = self.db.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()

        # Sort by Qdrant relevance score
        prompt_map = {str(p.id): p for p in prompts}
        sorted_prompts = [
            prompt_map[r["prompt_id"]] for r in results if r["prompt_id"] in prompt_map
        ]

        return sorted_prompts

    def render_prompt_template(
        self, template_name: str, variables: Dict[str, Any]
    ) -> str:
        """
        Render prompt template with given variables.

        Args:
            template_name: Name of the template
            variables: Dictionary with values for placeholders

        Returns:
            Rendered prompt text
        """
        template = (
            self.db.query(PromptTemplate)
            .filter(
                and_(
                    PromptTemplate.name == template_name,
                    PromptTemplate.is_active == True,
                )
            )
            .first()
        )

        if not template:
            raise ValueError(f"Template '{template_name}' not found")

        # Simple template rendering (for complex cases: Jinja2)
        rendered = template.template
        for key, value in variables.items():
            rendered = rendered.replace(f"{{{key}}}", str(value))

        return rendered

    def log_prompt_usage(
        self,
        prompt: Prompt,
        use_case: str,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        context_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """
        Log prompt usage for analytics.

        Args:
            prompt: Used prompt
            use_case: Context of usage
            tokens_used: Number of tokens used
            latency_ms: Request latency
            success: Whether successful
            error_message: Optional error message
            context_data: Additional metadata
            user_id: User identifier
            session_id: Session identifier
        """
        log = PromptUsageLog(
            prompt_id=prompt.id,
            prompt_version=prompt.version,
            use_case=use_case,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            context_data=context_data,
            user_id=user_id,
            session_id=session_id,
        )

        self.db.add(log)

        # Update prompt usage stats
        prompt.usage_count = (prompt.usage_count or 0) + 1
        prompt.last_used_at = datetime.utcnow()

        self.db.commit()

    def create_prompt_version(
        self,
        base_prompt: Prompt,
        new_content: str,
        description: Optional[str] = None,
    ) -> Prompt:
        """
        Create new version of existing prompt.

        Args:
            base_prompt: Base prompt (can be any version in the family)
            new_content: New prompt content
            description: Optional description of changes

        Returns:
            New prompt version
        """
        # Find the root prompt (base of the version family)
        root_id = base_prompt.parent_id if base_prompt.parent_id else base_prompt.id
        root_prompt = self.db.query(Prompt).filter(Prompt.id == root_id).first()

        # Find highest version number in this family
        max_version = self.db.query(func.max(Prompt.version)).filter(
            or_(Prompt.id == root_id, Prompt.parent_id == root_id)
        ).scalar() or 0

        new_version_number = max_version + 1

        # Use root prompt name as base for versioned name
        base_name = root_prompt.name if root_prompt else base_prompt.name
        new_name = f"{base_name}_v{new_version_number}"

        new_version = Prompt(
            name=new_name,
            content=new_content,
            description=description or base_prompt.description,
            category=base_prompt.category,
            tags=base_prompt.tags,
            use_case=base_prompt.use_case,
            version=new_version_number,
            parent_id=root_id,  # Always point to root
            is_active=False,  # Must be manually activated
        )

        self.db.add(new_version)
        self.db.commit()

        return new_version

    def activate_prompt_version(self, prompt: Prompt) -> None:
        """
        Activate a prompt version and deactivate all other versions in the same family.

        Args:
            prompt: Prompt to activate
        """
        # Find the root prompt (either this prompt or its parent)
        root_id = prompt.parent_id if prompt.parent_id else prompt.id

        # Deactivate all versions in this family
        self.db.query(Prompt).filter(
            and_(
                or_(Prompt.id == root_id, Prompt.parent_id == root_id),
                Prompt.id != prompt.id
            )
        ).update({"is_active": False}, synchronize_session=False)

        # Activate this version
        prompt.is_active = True

        self.db.commit()

    def get_prompt_versions(self, prompt_id: str) -> List[Prompt]:
        """
        Get all versions of a prompt.

        Args:
            prompt_id: ID of any prompt in the version family

        Returns:
            List of all versions sorted by version number (descending)
        """
        # Get the prompt
        prompt = self.db.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            return []

        # Find the root ID (either this prompt or its parent)
        root_id = prompt.parent_id if prompt.parent_id else prompt.id

        # Find all prompts in this family (root + all children)
        versions = (
            self.db.query(Prompt)
            .filter(or_(Prompt.id == root_id, Prompt.parent_id == root_id))
            .order_by(desc(Prompt.version))
            .all()
        )

        return versions

    def get_usage_statistics(
        self, prompt: Prompt, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a prompt.

        Args:
            prompt: Prompt to get stats for
            days: Number of days to look back

        Returns:
            Dictionary with usage statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days)

        logs = (
            self.db.query(PromptUsageLog)
            .filter(
                and_(
                    PromptUsageLog.prompt_id == prompt.id,
                    PromptUsageLog.timestamp >= cutoff_date,
                )
            )
            .all()
        )

        total_uses = len(logs)
        successful_uses = sum(1 for log in logs if log.success)
        failed_uses = total_uses - successful_uses

        total_tokens = sum(log.tokens_used or 0 for log in logs)
        avg_tokens = total_tokens / total_uses if total_uses > 0 else 0

        latencies = [log.latency_ms for log in logs if log.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        return {
            "total_uses": total_uses,
            "successful_uses": successful_uses,
            "failed_uses": failed_uses,
            "success_rate": successful_uses / total_uses if total_uses > 0 else 0,
            "total_tokens": total_tokens,
            "avg_tokens_per_use": avg_tokens,
            "avg_latency_ms": avg_latency,
            "period_days": days,
        }

