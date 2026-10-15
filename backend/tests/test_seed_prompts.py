"""
Tests for the Prompt seeding data (utils/seed_prompts.py)

seed_prompts() itself needs the Premium Prompt model and a live DB, so it
cannot run in Core (the public mirror has no premium/). These tests instead
parse the literal ``prompts_to_seed`` list out of utils/seed_prompts.py via
AST and validate the seed data without importing database/Premium code.
"""

import ast
import os


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
