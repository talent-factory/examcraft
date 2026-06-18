"""
Tests für Claude Service - Rate Limiting, Retry Logic, Cost Tracking
"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, Mock, patch
import os

import httpx

from services.claude_service import ClaudeService, ModelUnavailableError


@pytest.fixture(autouse=True)
def _reset_active_model_override():
    """TF-438: the active-model override is process-global; reset it around each
    test so a promotion in one test never leaks into the next."""
    import services.claude_service as cs

    cs._active_model_override = None
    yield
    cs._active_model_override = None


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
    async def test_generate_questions_demo_mode_rejects(self, demo_claude_service):
        """Demo Mode lehnt Question-Generation hart ab — see claude_service.py:208.

        Historisch produzierte Demo Mode Mock-Fragen; das wurde entfernt, um
        versehentliche Prod-Nutzung ohne ANTHROPIC_API_KEY zu verhindern.
        """
        with pytest.raises(RuntimeError, match="Claude API is not configured"):
            await demo_claude_service.generate_questions(
                topic="Python", difficulty="medium", question_count=3
            )

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
    async def test_api_failure_propagates_exception(self, claude_service):
        """Test that API errors propagate instead of falling back to demo questions"""
        with patch.object(
            claude_service,
            "_make_api_request_with_retry",
            side_effect=Exception("API Error"),
        ):
            with pytest.raises(Exception, match="API Error"):
                await claude_service.generate_questions("Python", "medium", 1)

    def test_build_prompt_german(self, claude_service):
        """Test Prompt Building für deutsche Sprache"""
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
        """Test Prompt Building für englische Sprache"""
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
    """Integration Tests für Claude Service"""

    @pytest.mark.asyncio
    async def test_full_workflow_demo_mode_rejects_generation(self):
        """Demo Mode Workflow: Stats sind abrufbar, aber Generation wird abgelehnt."""
        with patch.dict(os.environ, {"CLAUDE_DEMO_MODE": "true"}):
            service = ClaudeService()

            # Question-Generation wird hart abgelehnt
            with pytest.raises(RuntimeError, match="Claude API is not configured"):
                await service.generate_questions(
                    topic="Machine Learning", difficulty="hard", question_count=3
                )

            # Stats bleiben abrufbar und markieren den Demo-Mode korrekt
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


def _resp(status_code, json_data=None, text="", headers=None):
    """Build a mock httpx.Response (sync .json(), like the real client)."""
    r = Mock()
    r.status_code = status_code
    r.json = Mock(return_value=json_data or {})
    r.text = text
    r.headers = headers or {}
    return r


def _client_mock(post_side_effect=None, get_side_effect=None):
    """Build a mock httpx.AsyncClient usable as an async context manager whose
    .post/.get are awaitable (AsyncMock) and honour side_effect lists."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    client.post = AsyncMock(side_effect=post_side_effect)
    client.get = AsyncMock(side_effect=get_side_effect)
    return client


_OK_BODY = {"usage": {"input_tokens": 10, "output_tokens": 5}}


class TestClaudeServiceModelFallback:
    """TF-438: curated fallback chain + startup Models-API validation."""

    @pytest.fixture
    def service_with_chain(self):
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "test-api-key",
                "CLAUDE_MODEL": "model-primary",
                "CLAUDE_MODEL_FALLBACK": "model-fallback-1,model-fallback-2",
                "CLAUDE_MAX_RETRIES": "2",
                "CLAUDE_RETRY_DELAY": "0",
                "CLAUDE_DEMO_MODE": "false",
            },
        ):
            svc = ClaudeService()
            svc.request_timestamps = []
            return svc

    # --- chain construction -------------------------------------------------

    def test_model_chain_dedup_and_strip(self):
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "k",
                "CLAUDE_MODEL": "a",
                "CLAUDE_MODEL_FALLBACK": "b, c ,a",
                "CLAUDE_DEMO_MODE": "false",
            },
        ):
            svc = ClaudeService()
        assert svc.model == "a"
        # whitespace stripped, primary not duplicated even if repeated in list
        assert svc.model_chain == ["a", "b", "c"]

    # --- runtime fallback (_make_api_request_with_retry) --------------------

    @pytest.mark.asyncio
    async def test_fallback_on_404_uses_next_model(self, service_with_chain):
        svc = service_with_chain
        posts = [_resp(404, text="not_found_error"), _resp(200, _OK_BODY)]
        client = _client_mock(post_side_effect=posts)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context") as mock_alert,
        ):
            result = await svc._make_api_request_with_retry(
                {"model": "model-primary", "messages": []}
            )
        assert result == _OK_BODY
        # working fallback promoted for subsequent requests
        assert svc.model == "model-fallback-1"
        # one call per model — a 404 must NOT consume same-model retries
        assert client.post.await_count == 2
        mock_alert.assert_called_once()
        # the fallback request carried the new model in its payload
        assert client.post.await_args_list[1].kwargs["json"]["model"] == (
            "model-fallback-1"
        )

    @pytest.mark.asyncio
    async def test_chain_exhaustion_raises_model_unavailable(self, service_with_chain):
        svc = service_with_chain
        posts = [_resp(404, text="not_found_error") for _ in range(3)]
        client = _client_mock(post_side_effect=posts)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context") as mock_alert,
        ):
            with pytest.raises(ModelUnavailableError):
                await svc._make_api_request_with_retry(
                    {"model": "model-primary", "messages": []}
                )
        assert client.post.await_count == 3  # one per model, no looping
        assert mock_alert.call_count == 3  # alert per retired model
        # final alert signals an exhausted chain
        assert mock_alert.call_args_list[-1].kwargs["extra_context"]["next_model"] is (
            None
        )

    @pytest.mark.asyncio
    async def test_transient_error_retries_same_model_no_fallback(
        self, service_with_chain
    ):
        svc = service_with_chain  # CLAUDE_MAX_RETRIES=2
        posts = [_resp(500, text="boom"), _resp(500, text="boom")]
        client = _client_mock(post_side_effect=posts)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            with pytest.raises(Exception) as exc_info:
                await svc._make_api_request_with_retry(
                    {"model": "model-primary", "messages": []}
                )
        # a 5xx is transient: retried on the SAME model, not a fallback trigger
        assert not isinstance(exc_info.value, ModelUnavailableError)
        assert client.post.await_count == 2  # max_retries on the same model
        assert svc.model == "model-primary"  # unchanged

    @pytest.mark.asyncio
    async def test_404_then_transient_does_not_advance_or_escalate(
        self, service_with_chain
    ):
        svc = service_with_chain  # max_retries=2; chain: primary, fb-1, fb-2
        # primary 404 -> switch to fb-1; fb-1 returns 5xx twice (transient).
        posts = [
            _resp(404, text="not_found_error"),
            _resp(500, text="boom"),
            _resp(500, text="boom"),
        ]
        client = _client_mock(post_side_effect=posts)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context"),
            patch("asyncio.sleep", new=AsyncMock()),
        ):
            with pytest.raises(Exception) as exc_info:
                await svc._make_api_request_with_retry(
                    {"model": "model-primary", "messages": []}
                )
        # A transient on a fallback is re-raised (retryable upstream), NOT
        # escalated to ModelUnavailableError and NOT advanced to model-fallback-2.
        assert not isinstance(exc_info.value, ModelUnavailableError)
        assert client.post.await_count == 3  # primary 404 + 2 retries on fb-1
        assert svc.model == "model-primary"  # no 200 success -> no promotion

    @pytest.mark.asyncio
    async def test_runtime_fallback_persists_for_new_instances(
        self, service_with_chain
    ):
        svc = service_with_chain
        posts = [_resp(404, text="not_found_error"), _resp(200, _OK_BODY)]
        client = _client_mock(post_side_effect=posts)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context"),
        ):
            await svc._make_api_request_with_retry(
                {"model": "model-primary", "messages": []}
            )
        # A freshly constructed instance (RAGService builds one per task) starts
        # from the promoted model, not the retired primary — no env change.
        with patch.dict(
            os.environ,
            {
                "ANTHROPIC_API_KEY": "k",
                "CLAUDE_MODEL": "model-primary",
                "CLAUDE_MODEL_FALLBACK": "model-fallback-1",
                "CLAUDE_DEMO_MODE": "false",
            },
        ):
            fresh = ClaudeService()
        assert fresh.model == "model-fallback-1"

    # --- startup validation (validate_active_model) -------------------------

    @pytest.mark.asyncio
    async def test_validate_switches_on_retired_primary(self, service_with_chain):
        svc = service_with_chain
        gets = [_resp(404), _resp(200)]  # primary retired, first fallback live
        client = _client_mock(get_side_effect=gets)
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context") as mock_alert,
        ):
            active = await svc.validate_active_model()
        assert active == "model-fallback-1"
        assert svc.model == "model-fallback-1"
        assert client.get.await_count == 2
        mock_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_all_retired_keeps_model_and_alerts(
        self, service_with_chain
    ):
        svc = service_with_chain
        client = _client_mock(get_side_effect=[_resp(404), _resp(404), _resp(404)])
        with (
            patch("httpx.AsyncClient", return_value=client),
            patch("config.sentry.capture_message_with_context") as mock_alert,
        ):
            active = await svc.validate_active_model()
        # keep configured model so the per-request path raises ModelUnavailableError
        assert active == "model-primary"
        assert mock_alert.call_count == 3

    @pytest.mark.asyncio
    async def test_validate_indeterminate_fails_open(self, service_with_chain):
        svc = service_with_chain
        client = _client_mock(get_side_effect=httpx.ConnectError("unreachable"))
        with patch("httpx.AsyncClient", return_value=client):
            active = await svc.validate_active_model()
        assert active == "model-primary"  # fail-open: assume available
        assert svc.model == "model-primary"

    @pytest.mark.asyncio
    async def test_validate_unexpected_status_fails_open(self, service_with_chain):
        svc = service_with_chain
        # A non-200/non-404 Models-API status (e.g. 500/403) is indeterminate:
        # fail open on the first candidate, keep the configured model, do not
        # cascade the chain as retired.
        client = _client_mock(get_side_effect=[_resp(500)])
        with patch("httpx.AsyncClient", return_value=client):
            active = await svc.validate_active_model()
        assert active == "model-primary"
        assert svc.model == "model-primary"
        assert client.get.await_count == 1  # first indeterminate short-circuits

    @pytest.mark.asyncio
    async def test_validate_skipped_in_demo_mode(self):
        with patch.dict(
            os.environ,
            {"ANTHROPIC_API_KEY": "", "CLAUDE_DEMO_MODE": "true"},
        ):
            svc = ClaudeService()
        with patch("httpx.AsyncClient") as mock_client:
            active = await svc.validate_active_model()
        assert active == svc.model
        mock_client.assert_not_called()  # no Models-API call in demo mode


if __name__ == "__main__":
    pytest.main([__file__])
