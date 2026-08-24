"""
Tests for Claude Service (TF-440: gateway-only, legacy direct path removed).

Wire-format/retry/fallback-specific tests now live exclusively in
test_claude_service_gateway.py (the gateway path itself) and
gateway_generator.py's own suite. This file only covers what ClaudeService
itself still does: demo_mode gating, prompt building, usage stats shape.
"""

import os
from unittest.mock import patch

import pytest

from services.claude_service import ClaudeService


class TestClaudeService:
    """Test suite for Claude Service"""

    @pytest.fixture
    def claude_service(self):
        """Claude Service fixture with an active gateway (not in demo mode)."""
        with patch.dict(
            os.environ,
            {"LLM_GATEWAY_URL": "http://gw:4000", "CLAUDE_DEMO_MODE": "false"},
        ):
            return ClaudeService()

    @pytest.fixture
    def demo_claude_service(self):
        """Claude Service fixture in demo mode (no gateway configured)."""
        with patch.dict(
            os.environ, {"LLM_GATEWAY_URL": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            return ClaudeService()

    def test_initialization_with_gateway(self, claude_service):
        """Test correct initialization with an active gateway"""
        from services import llm_gateway

        assert claude_service.model == llm_gateway.ALIAS_GENERATION
        assert not claude_service.demo_mode

    def test_initialization_demo_mode(self, demo_claude_service):
        """Test initialization in demo mode (no LLM_GATEWAY_URL)"""
        assert demo_claude_service.demo_mode

    def test_usage_stats(self, claude_service):
        """Usage stats shape stays stable for the dev debug endpoint.

        Token/cost tracking has run centrally at the gateway (LiteLLM) since
        TF-439 — ClaudeService itself no longer counts anything.
        """
        stats = claude_service.get_usage_stats()
        assert stats == {
            "total_cost": 0.0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "requests_last_minute": 0,
            "demo_mode": False,
        }

    @pytest.mark.asyncio
    async def test_generate_questions_demo_mode_rejects(self, demo_claude_service):
        """Demo mode hard-rejects question generation — see claude_service.py.

        Historically demo mode produced mock questions; that was removed to
        prevent accidental production use without a configured gateway.
        """
        with pytest.raises(RuntimeError, match="Claude generation is not configured"):
            await demo_claude_service.generate_questions(
                topic="Python", difficulty="medium", question_count=3
            )

    @pytest.mark.asyncio
    async def test_generate_questions_propagates_gateway_errors(
        self, claude_service, monkeypatch
    ):
        """API/model errors from the gateway propagate instead of falling
        into a silent demo fallback (TF-440: replaces the old
        _make_api_request_with_retry propagation test)."""
        import services.gateway_generator as gg

        async def boom(_prompt):
            raise RuntimeError("Gateway Error")

        monkeypatch.setattr(gg, "generate_questions_via_gateway", boom)

        with pytest.raises(RuntimeError, match="Gateway Error"):
            await claude_service.generate_questions("Python", "medium", 1)

    def test_build_prompt_german(self, claude_service):
        """Test prompt building for German language"""
        prompt = claude_service._build_prompt(
            topic="Python",
            difficulty="medium",
            question_count=3,
            question_types=["single_choice"],
            language="de",
        )

        assert "Python" in prompt
        assert "auf Deutsch" in prompt
        assert "mittel" in prompt
        assert "3" in prompt

    def test_build_prompt_english(self, claude_service):
        """Test prompt building for English language"""
        prompt = claude_service._build_prompt(
            topic="Python",
            difficulty="medium",
            question_count=3,
            question_types=["single_choice"],
            language="en",
        )

        assert "Python" in prompt
        assert "in English" in prompt
        assert "medium" in prompt
        assert "3" in prompt


class TestClaudeServiceIntegration:
    """Integration tests for Claude Service"""

    @pytest.mark.asyncio
    async def test_full_workflow_demo_mode_rejects_generation(self):
        """Demo mode workflow: stats are retrievable, but generation is rejected."""
        with patch.dict(
            os.environ, {"LLM_GATEWAY_URL": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            service = ClaudeService()

            # Question generation is hard-rejected
            with pytest.raises(
                RuntimeError, match="Claude generation is not configured"
            ):
                await service.generate_questions(
                    topic="Machine Learning", difficulty="hard", question_count=3
                )

            # Stats remain retrievable and correctly mark demo mode
            stats = service.get_usage_stats()
            assert stats["demo_mode"]
            assert stats["total_cost"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
