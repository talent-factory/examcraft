"""
Unit Tests for PromptService

Tests for dynamic prompt management functionality.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from models.prompt import Prompt, PromptTemplate, PromptUsageLog
from services.prompt_service import PromptService
from database import Base


@pytest.fixture(scope="module")
def test_db():
    """Create test database with PostgreSQL-like features"""
    # Use PostgreSQL for testing (requires running postgres container)
    # For CI/CD, you might want to use a test database
    from database import SessionLocal

    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def prompt_service(test_db):
    """Create PromptService instance"""
    return PromptService(test_db)


@pytest.fixture
def sample_prompt(test_db):
    """Create a sample prompt for testing"""
    prompt = Prompt(
        name=f"test_prompt_{uuid.uuid4().hex[:8]}",
        content="Test prompt content with {variable}",
        description="Test prompt",
        category="system_prompt",
        use_case="testing",
        tags=["test", "sample"],
        version=1,
        is_active=True,
    )
    test_db.add(prompt)
    test_db.commit()
    test_db.refresh(prompt)
    return prompt


@pytest.fixture
def sample_template(test_db):
    """Create a sample template for testing"""
    template = PromptTemplate(
        name=f"test_template_{uuid.uuid4().hex[:8]}",
        template="Hello {name}, your score is {score}",
        variables={"name": "string", "score": "int"},
        description="Test template",
        category="question_generation",  # Use valid category
        is_active=True,
    )
    test_db.add(template)
    test_db.commit()
    test_db.refresh(template)
    return template


class TestPromptServiceBasicOperations:
    """Tests for basic CRUD operations"""

    def test_get_prompt_by_name(self, prompt_service, sample_prompt):
        """Test retrieving prompt by name"""
        result = prompt_service.get_prompt_by_name(sample_prompt.name)

        assert result is not None
        assert result.id == sample_prompt.id
        assert result.name == sample_prompt.name
        assert result.version == 1

    def test_get_prompt_by_name_with_version(self, prompt_service, sample_prompt):
        """Test retrieving specific version"""
        result = prompt_service.get_prompt_by_name(sample_prompt.name, version=1)

        assert result is not None
        assert result.version == 1

    def test_get_prompt_by_name_nonexistent(self, prompt_service):
        """Test retrieving non-existent prompt"""
        result = prompt_service.get_prompt_by_name("nonexistent_prompt")

        assert result is None

    def test_get_prompt_for_use_case(self, prompt_service, sample_prompt):
        """Test retrieving prompt by use case"""
        result = prompt_service.get_prompt_for_use_case("testing")

        assert result is not None
        assert result.use_case == "testing"

    def test_get_prompt_for_use_case_with_category(
        self, prompt_service, sample_prompt
    ):
        """Test retrieving prompt by use case and category"""
        result = prompt_service.get_prompt_for_use_case(
            "testing", category="system_prompt"
        )

        assert result is not None
        assert result.category == "system_prompt"

    def test_get_prompt_for_use_case_with_tags(self, prompt_service, sample_prompt):
        """Test retrieving prompt by use case and tags"""
        result = prompt_service.get_prompt_for_use_case("testing", tags=["test"])

        assert result is not None
        assert "test" in result.tags


class TestPromptServiceTemplateRendering:
    """Tests for template rendering"""

    def test_render_prompt_template(self, prompt_service, sample_template):
        """Test basic template rendering"""
        result = prompt_service.render_prompt_template(
            sample_template.name, {"name": "Alice", "score": 95}
        )

        assert result == "Hello Alice, your score is 95"

    def test_render_prompt_template_nonexistent(self, prompt_service):
        """Test rendering non-existent template"""
        with pytest.raises(ValueError, match="not found"):
            prompt_service.render_prompt_template(
                "nonexistent_template", {"name": "Bob"}
            )


class TestPromptServiceVersioning:
    """Tests for prompt versioning"""

    def test_create_prompt_version(self, prompt_service, sample_prompt):
        """Test creating new version of prompt"""
        new_version = prompt_service.create_prompt_version(
            sample_prompt, "Updated content", "Version 2 with improvements"
        )

        assert new_version.id != sample_prompt.id
        assert new_version.name == f"{sample_prompt.name}_v2"  # Name includes version
        assert new_version.version == 2
        assert new_version.parent_id == sample_prompt.id
        assert new_version.is_active is False
        assert new_version.content == "Updated content"

    def test_activate_prompt_version(self, prompt_service, sample_prompt, test_db):
        """Test activating a prompt version"""
        # Create version 2
        v2 = prompt_service.create_prompt_version(sample_prompt, "Version 2 content")

        # Activate version 2
        prompt_service.activate_prompt_version(v2)

        # Refresh from DB
        test_db.refresh(sample_prompt)
        test_db.refresh(v2)

        assert sample_prompt.is_active is False
        assert v2.is_active is True

    def test_get_prompt_versions(self, prompt_service, sample_prompt):
        """Test retrieving all versions of a prompt"""
        # Create additional versions
        v2 = prompt_service.create_prompt_version(sample_prompt, "Version 2")
        v3 = prompt_service.create_prompt_version(sample_prompt, "Version 3")

        versions = prompt_service.get_prompt_versions(str(sample_prompt.id))

        assert len(versions) >= 3
        assert versions[0].version >= versions[1].version  # Descending order


class TestPromptServiceUsageLogging:
    """Tests for usage logging and statistics"""

    def test_log_prompt_usage_success(self, prompt_service, sample_prompt, test_db):
        """Test logging successful prompt usage"""
        initial_count = sample_prompt.usage_count or 0

        prompt_service.log_prompt_usage(
            prompt=sample_prompt,
            use_case="testing",
            tokens_used=150,
            latency_ms=250,
            success=True,
            context_data={"test": "data"},
        )

        test_db.refresh(sample_prompt)

        assert sample_prompt.usage_count == initial_count + 1
        assert sample_prompt.last_used_at is not None

        # Check log was created
        logs = (
            test_db.query(PromptUsageLog)
            .filter(PromptUsageLog.prompt_id == sample_prompt.id)
            .all()
        )
        assert len(logs) > 0
        latest_log = logs[-1]
        assert latest_log.tokens_used == 150
        assert latest_log.latency_ms == 250
        assert latest_log.success is True

    def test_log_prompt_usage_failure(self, prompt_service, sample_prompt):
        """Test logging failed prompt usage"""
        prompt_service.log_prompt_usage(
            prompt=sample_prompt,
            use_case="testing",
            success=False,
            error_message="Test error",
        )

        # Verify log exists
        logs = (
            prompt_service.db.query(PromptUsageLog)
            .filter(PromptUsageLog.prompt_id == sample_prompt.id)
            .all()
        )
        failed_logs = [log for log in logs if not log.success]
        assert len(failed_logs) > 0
        assert failed_logs[-1].error_message == "Test error"

    def test_get_usage_statistics(self, prompt_service, sample_prompt):
        """Test retrieving usage statistics"""
        # Create some usage logs
        for i in range(5):
            prompt_service.log_prompt_usage(
                prompt=sample_prompt,
                use_case="testing",
                tokens_used=100 + i * 10,
                latency_ms=200 + i * 20,
                success=i < 4,  # 4 successful, 1 failed
            )

        stats = prompt_service.get_usage_statistics(sample_prompt, days=30)

        assert stats["total_uses"] >= 5
        assert stats["successful_uses"] >= 4
        assert stats["failed_uses"] >= 1
        assert 0 < stats["success_rate"] <= 1
        assert stats["avg_tokens_per_use"] > 0
        assert stats["avg_latency_ms"] > 0


class TestPromptServiceEdgeCases:
    """Tests for edge cases and error handling"""

    def test_get_prompt_inactive_version(self, prompt_service, sample_prompt, test_db):
        """Test that inactive prompts are not returned by default"""
        # Deactivate the prompt
        sample_prompt.is_active = False
        test_db.commit()

        result = prompt_service.get_prompt_by_name(sample_prompt.name)

        assert result is None

    def test_get_prompt_for_use_case_no_active(
        self, prompt_service, sample_prompt, test_db
    ):
        """Test use case query with no active prompts"""
        # Deactivate all prompts for this use case
        test_db.query(Prompt).filter(Prompt.use_case == "testing").update(
            {"is_active": False}
        )
        test_db.commit()

        result = prompt_service.get_prompt_for_use_case("testing")

        assert result is None

    def test_usage_statistics_no_logs(self, prompt_service, test_db):
        """Test statistics for prompt with no usage logs"""
        new_prompt = Prompt(
            name=f"unused_prompt_{uuid.uuid4().hex[:8]}",
            content="Unused",
            category="system_prompt",
            use_case="testing",
            version=1,
            is_active=True,
        )
        test_db.add(new_prompt)
        test_db.commit()

        stats = prompt_service.get_usage_statistics(new_prompt)

        assert stats["total_uses"] == 0
        assert stats["success_rate"] == 0
        assert stats["avg_tokens_per_use"] == 0

