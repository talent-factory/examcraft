"""
Coverage gaps in services/claude_service.py not exercised by
test_claude_service.py (demo mode / prompt building) or
test_claude_service_gateway.py (custom_prompt gateway path):
the default (non-custom-prompt) generate_exam_async flow, the
custom_prompt + demo_mode rejection, and the module-level
get_claude_service() singleton / startup validation no-gateway branch.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

import services.claude_service as cs
from services.claude_service import ClaudeService


@pytest.fixture
def claude_service():
    with patch.dict(
        os.environ,
        {"LLM_GATEWAY_URL": "http://gw:4000", "CLAUDE_DEMO_MODE": "false"},
    ):
        return ClaudeService()


class TestGenerateExamAsyncDefaultFlow:
    @pytest.mark.asyncio
    async def test_default_flow_without_context(self, claude_service, monkeypatch):
        async def fake_generate_questions_via_gateway(_prompt):
            return [{"id": "q1", "question": "Was ist Python?"}]

        monkeypatch.setattr(
            "services.gateway_generator.generate_questions_via_gateway",
            fake_generate_questions_via_gateway,
        )

        result = await claude_service.generate_exam_async(
            {"topic": "Python", "difficulty": "easy", "question_count": 1}
        )

        assert result["topic"] == "Python"
        assert result["difficulty"] == "easy"
        assert result["question_count"] == 1
        assert result["context_used"] is False
        assert result["questions"] == [{"id": "q1", "question": "Was ist Python?"}]

    @pytest.mark.asyncio
    async def test_default_flow_with_context_enhances_topic(
        self, claude_service, monkeypatch
    ):
        captured_prompt = {}

        async def fake_generate_questions_via_gateway(prompt):
            captured_prompt["value"] = prompt
            return [{"id": "q1"}]

        monkeypatch.setattr(
            "services.gateway_generator.generate_questions_via_gateway",
            fake_generate_questions_via_gateway,
        )

        result = await claude_service.generate_exam_async(
            {
                "topic": "Python",
                "context": "Nur Grundlagen behandeln",
                "question_count": 2,
            }
        )

        assert result["context_used"] is True
        assert "Nur Grundlagen behandeln" in captured_prompt["value"]

    @pytest.mark.asyncio
    async def test_default_flow_propagates_and_logs_exceptions(
        self, claude_service, monkeypatch
    ):
        async def boom(_prompt):
            raise RuntimeError("Gateway kaputt")

        monkeypatch.setattr(
            "services.gateway_generator.generate_questions_via_gateway", boom
        )

        with pytest.raises(RuntimeError, match="Gateway kaputt"):
            await claude_service.generate_exam_async({"topic": "Python"})


class TestGenerateExamAsyncCustomPromptDemoMode:
    @pytest.mark.asyncio
    async def test_custom_prompt_rejected_in_demo_mode(self):
        with patch.dict(
            os.environ, {"LLM_GATEWAY_URL": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            service = ClaudeService()

        with pytest.raises(RuntimeError, match="not configured"):
            await service.generate_exam_async(
                {"topic": "Python", "custom_prompt": "Custom template"}
            )


class TestGetClaudeService:
    def test_returns_singleton_instance(self, monkeypatch):
        monkeypatch.setattr(cs, "_claude_service_instance", None)

        first = cs.get_claude_service()
        second = cs.get_claude_service()

        assert isinstance(first, ClaudeService)
        assert first is second


class TestValidateClaudeModelOnStartupNoGateway:
    @pytest.mark.asyncio
    async def test_returns_early_when_gateway_disabled(self, monkeypatch):
        monkeypatch.setattr(cs.llm_gateway, "gateway_enabled", lambda: False)
        # Both branches return None, so patch the logger (not caplog, which
        # is unreliable under full-suite propagation) to prove the
        # no-gateway branch, not just any code path, actually ran.
        mock_logger = MagicMock()
        monkeypatch.setattr(cs, "logger", mock_logger)

        result = await cs.validate_claude_model_on_startup()

        assert result is None
        mock_logger.warning.assert_called_once()
        assert "LLM_GATEWAY_URL" in mock_logger.warning.call_args[0][0]
