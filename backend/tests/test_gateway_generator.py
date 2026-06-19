"""Tests für den Gateway-Generierungspfad (TF-439).

Verifiziert den typisierten PydanticAI-Output, die 4xx→ModelUnavailableError-
Klassifizierung und die Transient-Weitergabe bei 5xx.
"""

import pytest
from services import gateway_generator as gg
from services.claude_service import ModelUnavailableError


@pytest.fixture(autouse=True)
def _gateway_env(monkeypatch):
    """Der Gateway-Pfad braucht URL + Virtual Key (Client-Konstruktion fail-fast)."""
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-x")


class _FakeResult:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_typed_generation_returns_dicts(monkeypatch):
    qs = gg.GeneratedQuestions(
        questions=[
            gg.GeneratedQuestion(
                id="q1",
                type="single_choice",
                question="Was ist `x`?",
                options=["a", "b", "c", "d"],
                correct_answer="a",
                explanation="weil `a`",
                difficulty="medium",
                topic="T",
            )
        ]
    )

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult(qs)

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_questions_via_gateway("prompt")
    assert isinstance(out, list) and out[0]["id"] == "q1"
    assert out[0]["type"] == "single_choice"


@pytest.mark.asyncio
async def test_4xx_maps_to_model_unavailable(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=404, model_name="examcraft/generation", body="no"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelUnavailableError):
        await gg.generate_questions_via_gateway("prompt")


@pytest.mark.asyncio
async def test_5xx_propagates_as_transient(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=503, model_name="examcraft/generation", body="busy"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelHTTPError):
        await gg.generate_questions_via_gateway("prompt")


@pytest.mark.asyncio
async def test_raw_generation_returns_string(monkeypatch):
    """generate_raw_via_gateway gibt den rohen Output-String zurück."""

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult("# Rohe Markdown-Ausgabe")

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_raw_via_gateway("prompt")
    assert out == "# Rohe Markdown-Ausgabe"


@pytest.mark.asyncio
async def test_raw_4xx_maps_to_model_unavailable(monkeypatch):
    """4xx im Roh-Pfad wird wie im getypten Pfad als ModelUnavailableError klassifiziert."""
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=404, model_name="examcraft/generation", body="no"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelUnavailableError):
        await gg.generate_raw_via_gateway("prompt")
