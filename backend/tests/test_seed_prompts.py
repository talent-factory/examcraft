"""
Tests for Prompt Seeding Utility
Tests idempotent seeding, duplicate handling, and data integrity

NOTE: These tests are currently SKIPPED because:
1. seed_prompts() requires Premium package models (Prompt model)
2. Premium package is not available in Core test environment
3. Tests would need Premium package integration to run

TODO: Re-enable when Premium package is integrated into test environment
"""

import pytest
import sys
import os

# Add utils to path for import
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

_PREMIUM_SKIP = pytest.mark.skip(
    reason="Premium package models not available in Core test environment"
)


@_PREMIUM_SKIP
class TestSeedPrompts:
    """Test suite for Prompt seeding utility (SKIPPED - requires Premium package)"""

    def test_seed_prompts_creates_5_prompts(self):
        """Test that seed script creates exactly 5 default prompts"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_is_idempotent(self):
        """Test that running seed script multiple times doesn't create duplicates"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_skips_existing(self):
        """Test that seed script skips prompts that already exist"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_preserves_existing_content(self):
        """Test that seed script doesn't overwrite existing prompt content"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_creates_correct_categories(self):
        """Test that seeded prompts have correct categories"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_creates_correct_use_cases(self):
        """Test that seeded prompts have correct use cases"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_sets_all_active(self):
        """Test that all seeded prompts are marked as active"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_has_valid_content(self):
        """Test that all seeded prompts have non-empty content"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_has_valid_versions(self):
        """Test that all seeded prompts have valid version strings"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_handles_database_error(self):
        """Test that seed script handles database errors gracefully"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_default_prompts_constant_has_5_entries(self):
        """Test that DEFAULT_PROMPTS constant has exactly 5 entries"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_default_prompts_have_required_fields(self):
        """Test that all default prompts have required fields"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_default_prompts_have_unique_names(self):
        """Test that all default prompts have unique names"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_default_prompts_content_not_empty(self):
        """Test that all default prompts have non-empty content"""
        # This test is skipped - requires Premium package Prompt model
        pass

    def test_seed_prompts_returns_correct_counts(self):
        """Test that seed_prompts returns accurate created/skipped counts"""
        # This test is skipped - requires Premium package Prompt model
        pass


# ---------------------------------------------------------------------------
# Static analysis of the seed data (runs in Core CI — no Premium DB needed)
#
# The class above is skipped because seed_prompts() needs the Premium Prompt
# model and a live DB. The tests below instead parse the literal
# ``prompts_to_seed`` list out of utils/seed_prompts.py via AST, so they
# validate the seed data itself without importing database/Premium code.
# ---------------------------------------------------------------------------

import ast  # noqa: E402


def _extract_seed_prompts():
    """Return the literal ``prompts_to_seed`` list from utils/seed_prompts.py.

    Parses the module source with ``ast`` and evaluates only the list literal
    assigned to ``prompts_to_seed`` inside ``seed_prompts``. This avoids
    importing ``database`` / the Premium ``Prompt`` model.
    """
    seed_path = os.path.join(
        os.path.dirname(__file__), "..", "utils", "seed_prompts.py"
    )
    with open(seed_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "prompts_to_seed" in targets:
                return ast.literal_eval(node.value)
    raise AssertionError("prompts_to_seed list not found in seed_prompts.py")


class TestSeedPromptsData:
    """Validate the static seed prompt definitions (Core-safe, not skipped)."""

    def test_single_and_multiple_choice_use_cases_present(self):
        prompts = _extract_seed_prompts()
        use_cases = {p["use_case"] for p in prompts}
        assert "question_generation_single_choice" in use_cases
        assert "question_generation_multiple_choice" in use_cases

    def test_multiple_choice_template_definition(self):
        prompts = _extract_seed_prompts()
        multi = next(
            (p for p in prompts if p["name"] == "default_prompt_multiple_choice"),
            None,
        )
        assert multi is not None, "default_prompt_multiple_choice template missing"
        assert multi["use_case"] == "question_generation_multiple_choice"
        assert "multiple_choice" in multi["tags"]
        assert multi["is_active"] is True
        # Vocabulary contract: multi prompt must emit correct_answers (array of
        # exact option strings), not a single correct_answer / letters.
        assert "correct_answers" in multi["content"]
        assert "correct_answer:" not in multi["content"]

    def test_seed_prompt_names_are_unique(self):
        prompts = _extract_seed_prompts()
        names = [p["name"] for p in prompts]
        assert len(names) == len(set(names))

    def test_default_templates_have_required_fields(self):
        prompts = _extract_seed_prompts()
        required = {"name", "content", "use_case", "tags", "is_active"}
        for prompt in prompts:
            assert required.issubset(prompt.keys()), prompt.get("name")
            assert prompt["content"].strip()
