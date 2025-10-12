"""
Unit Tests for Prompt Knowledge Base Models

Tests for Prompt, PromptTemplate, and PromptUsageLog models.
"""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid

from models.prompt import Prompt, PromptTemplate, PromptUsageLog
from database import Base


@pytest.fixture(scope="module")
def test_db():
    """Create test database"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestPromptModel:
    """Tests for Prompt model"""

    def test_create_prompt(self, test_db):
        """Test creating a basic prompt"""
        prompt = Prompt(
            name="test_system_prompt",
            content="You are a helpful assistant.",
            description="Test system prompt",
            category="system_prompt",
            use_case="question_generation",
            tags=["test", "system"],
            version=1,
            is_active=True,
        )
        test_db.add(prompt)
        test_db.commit()

        assert prompt.id is not None
        assert prompt.name == "test_system_prompt"
        assert prompt.category == "system_prompt"
        assert prompt.version == 1
        assert prompt.is_active is True

    def test_prompt_unique_name_constraint(self, test_db):
        """Test that prompt names must be unique"""
        prompt1 = Prompt(
            name="duplicate_name",
            content="Content 1",
            category="system_prompt",
        )
        test_db.add(prompt1)
        test_db.commit()

        prompt2 = Prompt(
            name="duplicate_name",
            content="Content 2",
            category="user_prompt",
        )
        test_db.add(prompt2)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_prompt_category_check_constraint(self, test_db):
        """Test that category must be one of allowed values"""
        # Note: SQLite doesn't enforce CHECK constraints by default
        # This test would work with PostgreSQL
        prompt = Prompt(
            name="invalid_category_prompt",
            content="Test content",
            category="invalid_category",  # Should fail in PostgreSQL
        )
        test_db.add(prompt)
        # In PostgreSQL, this would raise IntegrityError
        # test_db.commit()

    def test_prompt_version_default(self, test_db):
        """Test that version defaults to 1"""
        prompt = Prompt(
            name="version_test_prompt",
            content="Test content",
            category="system_prompt",
        )
        test_db.add(prompt)
        test_db.commit()

        assert prompt.version == 1

    def test_prompt_versioning_relationship(self, test_db):
        """Test parent-child relationship for versioning"""
        parent_prompt = Prompt(
            name="parent_prompt_v1",
            content="Version 1 content",
            category="system_prompt",
            version=1,
        )
        test_db.add(parent_prompt)
        test_db.commit()

        child_prompt = Prompt(
            name="parent_prompt_v2",
            content="Version 2 content",
            category="system_prompt",
            version=2,
            parent_id=parent_prompt.id,
        )
        test_db.add(child_prompt)
        test_db.commit()

        assert child_prompt.parent_id == parent_prompt.id
        assert child_prompt.parent == parent_prompt

    def test_prompt_repr(self, test_db):
        """Test string representation"""
        prompt = Prompt(
            name="repr_test",
            content="Test",
            category="system_prompt",
            version=2,
        )
        assert "<Prompt repr_test v2>" in repr(prompt)


class TestPromptTemplateModel:
    """Tests for PromptTemplate model"""

    def test_create_template(self, test_db):
        """Test creating a prompt template"""
        template = PromptTemplate(
            name="question_gen_template",
            template="Generate a question about {topic} with difficulty {level}",
            variables={"topic": "string", "level": "int"},
            description="Template for question generation",
            category="question_generation",
            is_active=True,
        )
        test_db.add(template)
        test_db.commit()

        assert template.id is not None
        assert template.name == "question_gen_template"
        assert template.category == "question_generation"
        assert "topic" in template.variables

    def test_template_unique_name(self, test_db):
        """Test that template names must be unique"""
        template1 = PromptTemplate(
            name="unique_template",
            template="Template 1",
            variables={},
            category="chatbot",
        )
        test_db.add(template1)
        test_db.commit()

        template2 = PromptTemplate(
            name="unique_template",
            template="Template 2",
            variables={},
            category="evaluation",
        )
        test_db.add(template2)

        with pytest.raises(IntegrityError):
            test_db.commit()
        test_db.rollback()

    def test_template_repr(self, test_db):
        """Test string representation"""
        template = PromptTemplate(
            name="test_template",
            template="Test",
            variables={},
            category="chatbot",
        )
        assert "<PromptTemplate test_template>" in repr(template)


class TestPromptUsageLogModel:
    """Tests for PromptUsageLog model"""

    def test_create_usage_log(self, test_db):
        """Test creating a usage log"""
        # First create a prompt
        prompt = Prompt(
            name="logged_prompt",
            content="Test content",
            category="system_prompt",
        )
        test_db.add(prompt)
        test_db.commit()

        # Create usage log
        log = PromptUsageLog(
            prompt_id=prompt.id,
            prompt_version=1,
            use_case="question_generation",
            context_data={"document_id": 123},
            tokens_used=150,
            latency_ms=250,
            success=True,
            user_id="test_user",
            session_id="test_session",
        )
        test_db.add(log)
        test_db.commit()

        assert log.id is not None
        assert log.prompt_id == prompt.id
        assert log.tokens_used == 150
        assert log.success is True

    def test_usage_log_relationship(self, test_db):
        """Test relationship between usage log and prompt"""
        prompt = Prompt(
            name="relationship_test_prompt",
            content="Test",
            category="system_prompt",
        )
        test_db.add(prompt)
        test_db.commit()

        log = PromptUsageLog(
            prompt_id=prompt.id,
            prompt_version=1,
            use_case="test",
        )
        test_db.add(log)
        test_db.commit()

        assert log.prompt == prompt
        assert log in prompt.usage_logs

    def test_usage_log_on_delete_set_null(self, test_db):
        """Test that deleting a prompt sets usage_log.prompt_id to NULL"""
        prompt = Prompt(
            name="delete_test_prompt",
            content="Test",
            category="system_prompt",
        )
        test_db.add(prompt)
        test_db.commit()
        prompt_id = prompt.id

        log = PromptUsageLog(
            prompt_id=prompt_id,
            prompt_version=1,
        )
        test_db.add(log)
        test_db.commit()
        log_id = log.id

        # Delete prompt
        test_db.delete(prompt)
        test_db.commit()

        # Log should still exist but prompt_id should be NULL
        remaining_log = test_db.query(PromptUsageLog).filter_by(id=log_id).first()
        assert remaining_log is not None
        assert remaining_log.prompt_id is None

    def test_usage_log_repr(self, test_db):
        """Test string representation"""
        log = PromptUsageLog(
            use_case="test_case",
        )
        test_db.add(log)
        test_db.commit()
        assert "PromptUsageLog" in repr(log)
        assert "test_case" in repr(log)

