"""
Tests für Claude Service - Rate Limiting, Retry Logic, Cost Tracking
"""

import pytest
import time
from unittest.mock import Mock, patch
import os
from services.claude_service import ClaudeService


class TestClaudeService:
    """Test Suite für Claude Service"""

    @pytest.fixture
    def claude_service(self):
        """Claude Service Fixture mit Mock API Key"""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-api-key",
                "CLAUDE_MODEL": "claude-3-sonnet-20240229",
                "CLAUDE_MAX_RPM": "10",
                "CLAUDE_MAX_TOKENS": "2000",
                "CLAUDE_MAX_RETRIES": "2",
                "CLAUDE_RETRY_DELAY": "0.1",
                "CLAUDE_DEMO_MODE": "false",
            },
        ):
            service = ClaudeService()
            # Reset tracking für jeden Test
            service.request_timestamps = []
            service.total_cost = 0.0
            service.total_input_tokens = 0
            service.total_output_tokens = 0
            return service

    @pytest.fixture
    def demo_claude_service(self):
        """Claude Service Fixture im Demo Mode"""
        with patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            return ClaudeService()

    def test_initialization_with_api_key(self, claude_service):
        """Test korrekte Initialisierung mit API Key"""
        assert claude_service.api_key == "test-api-key"
        assert claude_service.model == "claude-3-sonnet-20240229"
        assert claude_service.max_requests_per_minute == 10
        assert claude_service.max_tokens_per_request == 2000
        assert claude_service.max_retries == 2
        assert claude_service.retry_delay == 0.1
        assert not claude_service.demo_mode

    def test_initialization_demo_mode(self, demo_claude_service):
        """Test Initialisierung im Demo Mode"""
        assert demo_claude_service.demo_mode
        assert not demo_claude_service.api_key

    def test_rate_limit_check_empty(self, claude_service):
        """Test Rate Limit Check mit leerer Historie"""
        assert claude_service._check_rate_limit()

    def test_rate_limit_check_within_limit(self, claude_service):
        """Test Rate Limit Check innerhalb des Limits"""
        # Füge 5 Requests hinzu (Limit ist 10)
        for _ in range(5):
            claude_service._add_request_timestamp()

        assert claude_service._check_rate_limit()
        assert len(claude_service.request_timestamps) == 5

    def test_rate_limit_check_at_limit(self, claude_service):
        """Test Rate Limit Check am Limit"""
        # Füge 10 Requests hinzu (Limit ist 10)
        for _ in range(10):
            claude_service._add_request_timestamp()

        assert not claude_service._check_rate_limit()

    def test_rate_limit_cleanup_old_timestamps(self, claude_service):
        """Test Cleanup alter Timestamps"""
        # Füge alte Timestamps hinzu (älter als 60 Sekunden)
        old_time = time.time() - 70
        claude_service.request_timestamps = [old_time, old_time, old_time]

        # Check sollte alte Timestamps entfernen
        assert claude_service._check_rate_limit()
        assert len(claude_service.request_timestamps) == 0

    def test_cost_calculation(self, claude_service):
        """Test Kostenberechnung"""
        input_tokens = 1000
        output_tokens = 500

        cost = claude_service._calculate_cost(input_tokens, output_tokens)

        expected_cost = (1000 * 0.003 / 1000) + (500 * 0.015 / 1000)
        assert cost == expected_cost
        assert claude_service.total_input_tokens == 1000
        assert claude_service.total_output_tokens == 500
        assert claude_service.total_cost == expected_cost

    def test_usage_stats(self, claude_service):
        """Test Usage Statistics"""
        # Simuliere einige API Calls
        claude_service._calculate_cost(1000, 500)
        claude_service._add_request_timestamp()

        stats = claude_service.get_usage_stats()

        assert stats["total_input_tokens"] == 1000
        assert stats["total_output_tokens"] == 500
        assert stats["total_cost"] > 0
        assert stats["requests_last_minute"] == 1
        assert not stats["demo_mode"]

    @pytest.mark.asyncio
    async def test_generate_questions_demo_mode(self, demo_claude_service):
        """Test Fragen-Generierung im Demo Mode"""
        questions = await demo_claude_service.generate_questions(
            topic="Python", difficulty="medium", question_count=3
        )

        assert len(questions) == 3
        assert all("id" in q for q in questions)
        assert all("question" in q for q in questions)
        assert all("type" in q for q in questions)

    @pytest.mark.asyncio
    async def test_api_request_with_retry_success(self, claude_service):
        """Test erfolgreichen API Request"""
        mock_response = {
            "content": [{"text": "Mock response"}],
            "usage": {"input_tokens": 100, "output_tokens": 50},
        }

        with patch.object(
            claude_service, "_make_api_request_with_retry", return_value=mock_response
        ):
            with patch.object(
                claude_service,
                "_parse_claude_response",
                return_value=[{"id": 1, "question": "Test"}],
            ):
                questions = await claude_service.generate_questions(
                    "Python", "medium", 1
                )

                assert len(questions) == 1
                assert questions[0]["question"] == "Test"

    @pytest.mark.asyncio
    async def test_api_request_retry_on_failure(self, claude_service):
        """Test Retry Logic bei API Fehlern"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock Response mit 500 Error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            with pytest.raises(Exception):
                await claude_service._make_api_request_with_retry({"test": "payload"})

    @pytest.mark.asyncio
    async def test_api_request_rate_limit_handling(self, claude_service):
        """Test Rate Limit Handling"""
        with patch("httpx.AsyncClient") as mock_client:
            # Mock Response mit 429 Rate Limit
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.headers = {"retry-after": "1"}

            mock_client.return_value.__aenter__.return_value.post.return_value = (
                mock_response
            )

            with patch("asyncio.sleep") as mock_sleep:
                with pytest.raises(Exception):
                    await claude_service._make_api_request_with_retry(
                        {"test": "payload"}
                    )

                # Verify sleep was called for rate limit
                mock_sleep.assert_called()

    @pytest.mark.asyncio
    async def test_fallback_to_demo_on_api_failure(self, claude_service):
        """Test Fallback zu Demo Mode bei API Fehlern"""
        with patch.object(
            claude_service,
            "_make_api_request_with_retry",
            side_effect=Exception("API Error"),
        ):
            with patch.object(
                claude_service,
                "_generate_demo_questions",
                return_value=[{"id": 1, "question": "Demo"}],
            ):
                questions = await claude_service.generate_questions(
                    "Python", "medium", 1
                )

                assert len(questions) == 1
                assert questions[0]["question"] == "Demo"

    def test_build_prompt_german(self, claude_service):
        """Test Prompt Building für deutsche Sprache"""
        prompt = claude_service._build_prompt(
            topic="Python",
            difficulty="medium",
            question_count=3,
            question_types=["multiple_choice"],
            language="de",
        )

        assert "Python" in prompt
        assert "auf Deutsch" in prompt
        assert "mittel" in prompt
        assert "3" in prompt

    def test_build_prompt_english(self, claude_service):
        """Test Prompt Building für englische Sprache"""
        prompt = claude_service._build_prompt(
            topic="Python",
            difficulty="medium",
            question_count=3,
            question_types=["multiple_choice"],
            language="en",
        )

        assert "Python" in prompt
        assert "in English" in prompt
        assert "medium" in prompt
        assert "3" in prompt


class TestClaudeServiceIntegration:
    """Integration Tests für Claude Service"""

    @pytest.mark.asyncio
    async def test_full_workflow_demo_mode(self):
        """Test kompletter Workflow im Demo Mode"""
        with patch.dict(os.environ, {"CLAUDE_DEMO_MODE": "true"}):
            service = ClaudeService()

            # Test Fragen-Generierung
            # Demo mode generates at most 3 questions
            questions = await service.generate_questions(
                topic="Machine Learning", difficulty="hard", question_count=3
            )

            assert len(questions) == 3
            assert all(isinstance(q, dict) for q in questions)

            # Test Usage Stats
            stats = service.get_usage_stats()
            assert stats["demo_mode"]
            assert stats["total_cost"] == 0.0

    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test Rate Limiting Integration"""
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-key",
                "CLAUDE_MAX_RPM": "2",  # Sehr niedriges Limit für Test
                "CLAUDE_DEMO_MODE": "false",
            },
        ):
            service = ClaudeService()

            # Fülle Rate Limit
            service.request_timestamps = [time.time()] * 2

            # Nächster Request sollte warten müssen
            assert not service._check_rate_limit()


if __name__ == "__main__":
    pytest.main([__file__])
