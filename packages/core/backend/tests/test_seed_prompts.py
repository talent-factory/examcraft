"""
Tests for Prompt Seeding Utility
Tests idempotent seeding, duplicate handling, and data integrity
"""

import pytest
from sqlalchemy.orm import Session
import sys
import os

# Add utils to path for import
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from utils.seed_prompts import seed_prompts, DEFAULT_PROMPTS


class TestSeedPrompts:
    """Test suite for Prompt seeding utility"""

    def test_seed_prompts_creates_5_prompts(self, db: Session):
        """Test that seed script creates exactly 5 default prompts"""
        # Arrange: Empty database
        # (Assuming fresh test database)

        # Act
        created, skipped = seed_prompts(db)

        # Assert
        assert created == 5
        assert skipped == 0

        # Verify prompts exist in database
        from models.prompt import Prompt

        prompts = db.query(Prompt).all()
        assert len(prompts) == 5

    def test_seed_prompts_is_idempotent(self, db: Session):
        """Test that running seed script multiple times doesn't create duplicates"""
        # Arrange: Run seed once
        created_first, skipped_first = seed_prompts(db)
        assert created_first == 5
        assert skipped_first == 0

        # Act: Run seed again
        created_second, skipped_second = seed_prompts(db)

        # Assert: No new prompts created
        assert created_second == 0
        assert skipped_second == 5

        # Verify still only 5 prompts in database
        from models.prompt import Prompt

        prompts = db.query(Prompt).all()
        assert len(prompts) == 5

    def test_seed_prompts_skips_existing(self, db: Session):
        """Test that seed script skips prompts that already exist"""
        # Arrange: Manually create 2 prompts
        from models.prompt import Prompt

        existing_prompts = [
            Prompt(
                name="system_prompt_question_generation_bloom",
                category="system",
                use_case="question_generation",
                content="Existing prompt content",
                version="1.0.0",
                is_active=True,
            ),
            Prompt(
                name="default_prompt_multiple_choice",
                category="default",
                use_case="question_generation",
                content="Existing MC prompt",
                version="1.0.0",
                is_active=True,
            ),
        ]

        for prompt in existing_prompts:
            db.add(prompt)
        db.commit()

        # Act: Run seed
        created, skipped = seed_prompts(db)

        # Assert: Only 3 new prompts created, 2 skipped
        assert created == 3
        assert skipped == 2

        # Verify total of 5 prompts
        prompts = db.query(Prompt).all()
        assert len(prompts) == 5

    def test_seed_prompts_preserves_existing_content(self, db: Session):
        """Test that seed script doesn't overwrite existing prompt content"""
        # Arrange: Create prompt with custom content
        from models.prompt import Prompt

        custom_content = "This is my custom prompt content that should not be overwritten"
        existing_prompt = Prompt(
            name="system_prompt_question_generation_bloom",
            category="system",
            use_case="question_generation",
            content=custom_content,
            version="2.0.0",  # Custom version
            is_active=True,
        )
        db.add(existing_prompt)
        db.commit()

        # Act: Run seed
        created, skipped = seed_prompts(db)

        # Assert: Prompt was skipped
        assert skipped >= 1

        # Verify content was NOT overwritten
        prompt = (
            db.query(Prompt)
            .filter(Prompt.name == "system_prompt_question_generation_bloom")
            .first()
        )
        assert prompt.content == custom_content
        assert prompt.version == "2.0.0"

    def test_seed_prompts_creates_correct_categories(self, db: Session):
        """Test that seeded prompts have correct categories"""
        # Act
        seed_prompts(db)

        # Assert
        from models.prompt import Prompt

        system_prompts = db.query(Prompt).filter(Prompt.category == "system").all()
        default_prompts = db.query(Prompt).filter(Prompt.category == "default").all()

        assert len(system_prompts) == 2  # question_generation_bloom, chatbot_document_qa
        assert len(default_prompts) == 3  # multiple_choice, open_ended, true_false

    def test_seed_prompts_creates_correct_use_cases(self, db: Session):
        """Test that seeded prompts have correct use cases"""
        # Act
        seed_prompts(db)

        # Assert
        from models.prompt import Prompt

        question_gen_prompts = (
            db.query(Prompt).filter(Prompt.use_case == "question_generation").all()
        )
        chatbot_prompts = (
            db.query(Prompt).filter(Prompt.use_case == "document_chatbot").all()
        )

        assert len(question_gen_prompts) == 4  # bloom, mc, open, true_false
        assert len(chatbot_prompts) == 1  # chatbot_document_qa

    def test_seed_prompts_sets_all_active(self, db: Session):
        """Test that all seeded prompts are marked as active"""
        # Act
        seed_prompts(db)

        # Assert
        from models.prompt import Prompt

        prompts = db.query(Prompt).all()
        assert all(prompt.is_active for prompt in prompts)

    def test_seed_prompts_has_valid_content(self, db: Session):
        """Test that all seeded prompts have non-empty content"""
        # Act
        seed_prompts(db)

        # Assert
        from models.prompt import Prompt

        prompts = db.query(Prompt).all()
        for prompt in prompts:
            assert prompt.content is not None
            assert len(prompt.content) > 0
            assert isinstance(prompt.content, str)

    def test_seed_prompts_has_valid_versions(self, db: Session):
        """Test that all seeded prompts have valid version strings"""
        # Act
        seed_prompts(db)

        # Assert
        from models.prompt import Prompt

        prompts = db.query(Prompt).all()
        for prompt in prompts:
            assert prompt.version is not None
            assert prompt.version == "1.0.0"

    def test_seed_prompts_handles_database_error(self, db: Session, monkeypatch):
        """Test that seed script handles database errors gracefully"""
        # Arrange: Mock db.commit to raise exception
        def mock_commit():
            raise Exception("Database connection lost")

        monkeypatch.setattr(db, "commit", mock_commit)

        # Act & Assert: Should raise exception
        with pytest.raises(Exception) as exc_info:
            seed_prompts(db)

        assert "Database connection lost" in str(exc_info.value)

    def test_default_prompts_constant_has_5_entries(self):
        """Test that DEFAULT_PROMPTS constant has exactly 5 entries"""
        assert len(DEFAULT_PROMPTS) == 5

    def test_default_prompts_have_required_fields(self):
        """Test that all default prompts have required fields"""
        required_fields = ["name", "category", "use_case", "content", "version", "is_active"]

        for prompt_data in DEFAULT_PROMPTS:
            for field in required_fields:
                assert field in prompt_data, f"Missing field '{field}' in prompt"
                assert prompt_data[field] is not None, f"Field '{field}' is None"

    def test_default_prompts_have_unique_names(self):
        """Test that all default prompts have unique names"""
        names = [prompt["name"] for prompt in DEFAULT_PROMPTS]
        assert len(names) == len(set(names)), "Duplicate prompt names found"

    def test_default_prompts_content_not_empty(self):
        """Test that all default prompts have non-empty content"""
        for prompt_data in DEFAULT_PROMPTS:
            assert len(prompt_data["content"]) > 0
            assert isinstance(prompt_data["content"], str)

    def test_seed_prompts_returns_correct_counts(self, db: Session):
        """Test that seed_prompts returns accurate created/skipped counts"""
        # Arrange: Create 2 prompts manually
        from models.prompt import Prompt

        for i in range(2):
            prompt = Prompt(
                name=DEFAULT_PROMPTS[i]["name"],
                category=DEFAULT_PROMPTS[i]["category"],
                use_case=DEFAULT_PROMPTS[i]["use_case"],
                content="Existing content",
                version="1.0.0",
                is_active=True,
            )
            db.add(prompt)
        db.commit()

        # Act
        created, skipped = seed_prompts(db)

        # Assert
        assert created == 3  # 5 total - 2 existing
        assert skipped == 2
        assert created + skipped == 5


# ==================== Fixtures ====================


@pytest.fixture
def db():
    """Create test database session"""
    from database import SessionLocal, engine, Base

    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create session
    session = SessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)

