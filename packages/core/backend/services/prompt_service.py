"""
Placeholder for PromptService (Core Package)

This is a minimal placeholder to allow Premium RAG Service imports.
The actual implementation is in packages/premium/backend/services/prompt_service.py
"""

from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class PromptService:
    """
    Placeholder for PromptService.

    In Core deployment mode, this provides minimal functionality.
    In Full deployment mode, this is replaced by the Premium implementation.
    """

    def __init__(self, db: Session):
        """Initialize placeholder PromptService"""
        self.db = db
        logger.warning(
            "Using PromptService placeholder (Premium features not available)"
        )

    def get_prompt_by_id(self, prompt_id: str):
        """Placeholder: Get prompt by ID"""
        logger.warning("PromptService.get_prompt_by_id called on placeholder")
        return None

    def get_prompt_for_use_case(
        self,
        use_case: str,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ):
        """Placeholder: Get prompt for use case"""
        logger.warning(
            f"PromptService.get_prompt_for_use_case called on placeholder: {use_case}"
        )
        return None

    def render_prompt_by_id(
        self, prompt_id: str, variables: Dict[str, Any], strict: bool = False
    ) -> str:
        """Placeholder: Render prompt by ID"""
        logger.warning("PromptService.render_prompt_by_id called on placeholder")
        raise NotImplementedError("PromptService not available in Core mode")

    def render_prompt_with_jinja2(
        self, prompt_content: str, variables: Dict[str, Any], strict: bool = False
    ) -> str:
        """Placeholder: Render prompt with Jinja2"""
        logger.warning("PromptService.render_prompt_with_jinja2 called on placeholder")
        raise NotImplementedError("PromptService not available in Core mode")

    def log_prompt_usage(self, prompt, use_case: str):
        """Placeholder: Log prompt usage"""
        logger.warning("PromptService.log_prompt_usage called on placeholder")
        pass

    def extract_template_variables(self, prompt_content: str) -> List[str]:
        """Placeholder: Extract template variables"""
        logger.warning("PromptService.extract_template_variables called on placeholder")
        return []
