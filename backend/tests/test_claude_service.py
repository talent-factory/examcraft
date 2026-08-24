"""
Tests für Claude Service (TF-440: Gateway-only, Legacy-Direktpfad entfernt).

Wire-Format-/Retry-/Fallback-spezifische Tests leben jetzt ausschliesslich
in test_claude_service_gateway.py (der Gateway-Pfad selbst) bzw.
gateway_generator.py's eigener Suite. Diese Datei deckt nur noch das, was
ClaudeService selbst noch tut: demo_mode-Gating, Prompt-Building,
Usage-Stats-Shape.
"""

import os
from unittest.mock import patch

import pytest

from services.claude_service import ClaudeService


class TestClaudeService:
    """Test Suite für Claude Service"""

    @pytest.fixture
    def claude_service(self):
        """Claude Service Fixture mit aktivem Gateway (nicht im Demo-Mode)."""
        with patch.dict(
            os.environ,
            {"LLM_GATEWAY_URL": "http://gw:4000", "CLAUDE_DEMO_MODE": "false"},
        ):
            return ClaudeService()

    @pytest.fixture
    def demo_claude_service(self):
        """Claude Service Fixture im Demo Mode (kein Gateway konfiguriert)."""
        with patch.dict(
            os.environ, {"LLM_GATEWAY_URL": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            return ClaudeService()

    def test_initialization_with_gateway(self, claude_service):
        """Test korrekte Initialisierung mit aktivem Gateway"""
        from services import llm_gateway

        assert claude_service.model == llm_gateway.ALIAS_GENERATION
        assert not claude_service.demo_mode

    def test_initialization_demo_mode(self, demo_claude_service):
        """Test Initialisierung im Demo Mode (kein LLM_GATEWAY_URL)"""
        assert demo_claude_service.demo_mode

    def test_usage_stats(self, claude_service):
        """Usage-Stats-Shape bleibt für den Dev-Debug-Endpoint stabil.

        Token-/Kosten-Tracking läuft seit TF-439 zentral am Gateway
        (LiteLLM) — ClaudeService selbst zählt nichts mehr mit.
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
        """Demo Mode lehnt Question-Generation hart ab — see claude_service.py.

        Historisch produzierte Demo Mode Mock-Fragen; das wurde entfernt, um
        versehentliche Prod-Nutzung ohne konfigurierten Gateway zu verhindern.
        """
        with pytest.raises(RuntimeError, match="Claude generation is not configured"):
            await demo_claude_service.generate_questions(
                topic="Python", difficulty="medium", question_count=3
            )

    @pytest.mark.asyncio
    async def test_generate_questions_propagates_gateway_errors(
        self, claude_service, monkeypatch
    ):
        """API-/Modell-Fehler aus dem Gateway propagieren, statt in einen
        stillen Demo-Fallback zu laufen (TF-440: ersetzt den alten
        _make_api_request_with_retry-Propagations-Test)."""
        import services.gateway_generator as gg

        async def boom(_prompt):
            raise RuntimeError("Gateway Error")

        monkeypatch.setattr(gg, "generate_questions_via_gateway", boom)

        with pytest.raises(RuntimeError, match="Gateway Error"):
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
        with patch.dict(
            os.environ, {"LLM_GATEWAY_URL": "", "CLAUDE_DEMO_MODE": "true"}
        ):
            service = ClaudeService()

            # Question-Generation wird hart abgelehnt
            with pytest.raises(
                RuntimeError, match="Claude generation is not configured"
            ):
                await service.generate_questions(
                    topic="Machine Learning", difficulty="hard", question_count=3
                )

            # Stats bleiben abrufbar und markieren den Demo-Mode korrekt
            stats = service.get_usage_stats()
            assert stats["demo_mode"]
            assert stats["total_cost"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
