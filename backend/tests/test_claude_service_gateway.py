# core/backend/tests/test_claude_service_gateway.py
"""Wiring tests for the gateway delegation in ClaudeService (TF-439).

The leaf functions in ``gateway_generator`` are tested separately; here the
production *switch* is checked: that ClaudeService actually branches into
the gateway path (instead of legacy httpx) when the gateway is active, and
that error classification (permanent vs. transient) is passed through
correctly.
"""

import pytest

import services.gateway_generator as gg
from services import claude_service as cs
from services.claude_service import ClaudeService, ModelUnavailableError


def _enable_gateway(monkeypatch):
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-x")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_DEMO_MODE", raising=False)


# ---------------------------------------------------------------------------
# C1: demo_mode must not block the gateway path
# ---------------------------------------------------------------------------


def test_demo_mode_false_when_gateway_enabled_without_key(monkeypatch):
    """Gateway on + no ANTHROPIC_API_KEY ⇒ NOT demo mode (otherwise generation raises)."""
    _enable_gateway(monkeypatch)
    assert ClaudeService().demo_mode is False


def test_demo_mode_true_when_no_key_and_no_gateway(monkeypatch):
    monkeypatch.delenv("LLM_GATEWAY_URL", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_DEMO_MODE", raising=False)
    assert ClaudeService().demo_mode is True


# ---------------------------------------------------------------------------
# generate_questions: delegation to the gateway
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_questions_delegates_to_gateway(monkeypatch):
    _enable_gateway(monkeypatch)
    seen = {}

    async def fake_gateway(prompt):
        seen["prompt"] = prompt
        return [{"id": "q1", "type": "single_choice"}]

    monkeypatch.setattr(gg, "generate_questions_via_gateway", fake_gateway)

    service = ClaudeService()

    # TF-440: the legacy httpx path no longer exists — there is only the
    # gateway branch now, no assertion needed anymore that it is "not called".
    out = await service.generate_questions(topic="Loops", question_count=1)

    assert out == [{"id": "q1", "type": "single_choice"}]
    assert "Loops" in seen["prompt"]  # the built prompt is passed through


# ---------------------------------------------------------------------------
# generate_exam_async (custom_prompt): typed → raw fallback + error reraise
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_custom_prompt_typed_success(monkeypatch):
    _enable_gateway(monkeypatch)

    async def typed_ok(prompt):
        return [{"id": "q1", "type": "open_ended"}]

    async def raw_boom(prompt):
        raise AssertionError("raw-Fallback darf bei Erfolg nicht laufen")

    monkeypatch.setattr(gg, "generate_questions_via_gateway", typed_ok)
    monkeypatch.setattr(gg, "generate_raw_via_gateway", raw_boom)

    result = await ClaudeService().generate_exam_async(
        {"topic": "T", "custom_prompt": "Mein Template"}
    )
    assert result["questions"] == [{"id": "q1", "type": "open_ended"}]
    assert result["custom_prompt_used"] is True


@pytest.mark.asyncio
async def test_custom_prompt_typed_failure_falls_back_to_raw(monkeypatch):
    _enable_gateway(monkeypatch)

    async def typed_fail(prompt):
        raise ValueError("Schema-Verstoss im typisierten Output")

    async def raw_ok(prompt):
        return "# Rohe Markdown-Antwort"

    monkeypatch.setattr(gg, "generate_questions_via_gateway", typed_fail)
    monkeypatch.setattr(gg, "generate_raw_via_gateway", raw_ok)

    result = await ClaudeService().generate_exam_async(
        {"topic": "T", "custom_prompt": "Mein Template"}
    )
    assert result["questions"] == [
        {"question": "# Rohe Markdown-Antwort", "type": "markdown", "raw_output": True}
    ]


@pytest.mark.asyncio
async def test_custom_prompt_model_unavailable_is_reraised(monkeypatch):
    """Permanent (4xx) ⇒ ModelUnavailableError fail-fast, NO raw fallback."""
    _enable_gateway(monkeypatch)

    async def typed_permanent(prompt):
        raise ModelUnavailableError("examcraft/generation 404")

    async def raw_boom(prompt):
        raise AssertionError("raw-Fallback darf bei permanentem Fehler nicht laufen")

    monkeypatch.setattr(gg, "generate_questions_via_gateway", typed_permanent)
    monkeypatch.setattr(gg, "generate_raw_via_gateway", raw_boom)

    with pytest.raises(ModelUnavailableError):
        await ClaudeService().generate_exam_async({"topic": "T", "custom_prompt": "X"})


@pytest.mark.asyncio
async def test_custom_prompt_transient_http_error_is_reraised(monkeypatch):
    """I3: a transient 5xx (ModelHTTPError) is passed through, NOT masked into raw."""
    from pydantic_ai.exceptions import ModelHTTPError

    _enable_gateway(monkeypatch)

    async def typed_transient(prompt):
        raise ModelHTTPError(
            status_code=503, model_name="examcraft/generation", body="busy"
        )

    async def raw_boom(prompt):
        raise AssertionError("raw-Fallback darf bei transientem 5xx nicht laufen")

    monkeypatch.setattr(gg, "generate_questions_via_gateway", typed_transient)
    monkeypatch.setattr(gg, "generate_raw_via_gateway", raw_boom)

    with pytest.raises(ModelHTTPError):
        await ClaudeService().generate_exam_async({"topic": "T", "custom_prompt": "X"})


# ---------------------------------------------------------------------------
# validate_claude_model_on_startup: skip when gateway is active
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_validation_skipped_when_gateway_enabled(monkeypatch):
    _enable_gateway(monkeypatch)
    # Disable the upstream skip switch so the gateway branch takes effect.
    monkeypatch.delenv("CLAUDE_SKIP_MODEL_VALIDATION", raising=False)

    def boom():
        raise AssertionError("get_claude_service darf bei aktivem Gateway nicht laufen")

    monkeypatch.setattr(cs, "get_claude_service", boom)

    # No raise, no network call.
    await cs.validate_claude_model_on_startup()
