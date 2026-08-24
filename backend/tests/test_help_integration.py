"""Integration test: full Help Widget flow (TF-308)."""

# Fixtures help_db, help_client, admin_client are defined in conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.help_service import HelpService


@pytest.mark.asyncio
async def test_call_claude_uses_gateway(monkeypatch):
    """_call_claude() geht über den LLM-Gateway (ALIAS_CHAT), nicht über den
    entfernten Anthropic-Direktpfad (TF-440). Nutzt PydanticAI TestModel als
    Stub-Modell, damit kein echter Gateway-Call nötig ist."""
    from pydantic_ai.models.test import TestModel

    import services.llm_gateway as gw

    seen: dict = {}

    def fake_make(alias, **_kwargs):
        seen["alias"] = alias
        return TestModel(
            custom_output_text=(
                '{"answer": "Du kannst PDFs im Upload-Tab hochladen.", '
                '"confidence": 0.9, "docs_links": []}'
            )
        )

    monkeypatch.setattr(gw, "make_pydantic_model", fake_make)

    service = HelpService(MagicMock())
    result = await service._call_claude(
        question="Wie lade ich ein PDF hoch?",
        chunks=[
            {
                "content": "PDFs koennen im Upload-Tab hochgeladen werden.",
                "source_file": "docs/upload.md",
                "section": "Upload",
                "language": "de",
                "score": 0.9,
            }
        ],
        user_role="teacher",
        user_tier="starter",
        route="/documents",
        history=None,
        locale="de",
    )

    assert seen["alias"] == gw.ALIAS_CHAT
    assert result["answer"] == "Du kannst PDFs im Upload-Tab hochladen."
    assert result["confidence"] == 0.9


@pytest.mark.asyncio
async def test_call_claude_folds_history_into_prompt(monkeypatch):
    """TF-440: die neue History-Folding-Logik in _call_claude war bisher
    ungetestet (der einzige Gateway-Test übergibt history=None). Deckt ab:
    dict- UND objekt-förmige History-Einträge, [-10:]-Trunkierung, korrekte
    User:/Assistant:-Label-Reihenfolge."""
    import types

    from pydantic_ai import Agent
    from pydantic_ai.models.test import TestModel

    import services.llm_gateway as gw

    monkeypatch.setattr(
        gw,
        "make_pydantic_model",
        lambda alias, **_kwargs: TestModel(
            custom_output_text='{"answer": "ok", "confidence": 0.9, "docs_links": []}'
        ),
    )

    captured: dict = {}
    original_run = Agent.run

    async def spy_run(self, user_prompt=None, **kwargs):
        captured["user_prompt"] = user_prompt
        return await original_run(self, user_prompt=user_prompt, **kwargs)

    monkeypatch.setattr(Agent, "run", spy_run)

    service = HelpService(MagicMock())
    # 11 Einträge: der älteste ("alte Frage 0") muss durch [-10:] wegfallen.
    history = [{"role": "user", "content": f"alte Frage {i}"} for i in range(9)]
    history.append(types.SimpleNamespace(role="assistant", content="objekt-antwort"))
    history.append({"role": "user", "content": "neueste Frage"})

    await service._call_claude(
        question="Aktuelle Frage?",
        chunks=[
            {
                "content": "doc",
                "source_file": "f.md",
                "section": "s",
                "language": "de",
                "score": 0.9,
            }
        ],
        user_role="teacher",
        user_tier="starter",
        route="/x",
        history=history,
        locale="de",
    )

    prompt = captured["user_prompt"]
    assert "Conversation history:" in prompt
    assert "alte Frage 0" not in prompt  # durch [-10:] getrimmt
    assert "alte Frage 1" in prompt
    assert "Assistant: objekt-antwort" in prompt  # objekt-förmiger Eintrag
    assert "User: neueste Frage" in prompt
    assert prompt.index("Assistant: objekt-antwort") < prompt.index(
        "User: neueste Frage"
    )


@pytest.mark.asyncio
async def test_low_confidence_does_not_retry():
    """TF-440: answer_question no longer retries on low confidence.

    Vor der Gateway-Migration lief der Retry auf einem stärkeren Modell
    (haiku -> sonnet). Seit ALIAS_CHAT die einzige Modellquelle ist, würde
    ein Retry denselben Alias mit demselben Prompt nochmal aufrufen — reine
    Kostenverdopplung ohne Nutzen. _call_claude wird deshalb bei jeder
    Confidence nur noch einmal aufgerufen; die Escalate-Markierung
    (confidence < 0.5) bleibt unverändert bestehen.
    """
    mock_db = MagicMock()
    service = HelpService(mock_db)

    high_score_chunk = {
        "content": "Some helpful documentation content.",
        "source_file": "docs/help.md",
        "section": "Getting Started",
        "language": "de",
        "score": 0.85,
    }

    low_confidence_result = {
        "answer": "Weak answer",
        "confidence": 0.4,
        "sources": [],
        "docs_links": [],
    }

    with (
        patch.object(service, "_try_faq_cache", new=AsyncMock(return_value=None)),
        patch.object(
            service, "_search_docs", new=AsyncMock(return_value=[high_score_chunk])
        ),
        patch.object(
            service,
            "_call_claude",
            new=AsyncMock(return_value=low_confidence_result),
        ) as mock_call,
    ):
        result = await service.answer_question(
            question="Wie exportiere ich eine Prüfung?",
            user_role="teacher",
            user_tier="starter",
            route="/exams",
        )

    mock_call.assert_awaited_once()
    assert result["confidence"] == 0.4
    assert result["escalate"] is True


@pytest.mark.asyncio
async def test_low_score_docs_returns_escalate_true():
    """answer_question returns escalate=True and confidence=0.0 when all chunks score < 0.3."""
    mock_db = MagicMock()
    service = HelpService(mock_db)

    low_score_chunk = {
        "content": "Unrelated content.",
        "source_file": "docs/other.md",
        "section": "Other",
        "language": "de",
        "score": 0.1,
    }

    with (
        patch.object(service, "_try_faq_cache", new=AsyncMock(return_value=None)),
        patch.object(
            service, "_search_docs", new=AsyncMock(return_value=[low_score_chunk])
        ),
    ):
        result = await service.answer_question(
            question="Was ist die Antwort auf alles?",
            user_role="student",
            user_tier="free",
            route="/dashboard",
        )

    assert result["escalate"] is True
    assert result["confidence"] == 0.0


def test_full_help_flow(help_client, help_db, admin_client):
    """Status -> Onboarding -> Context -> Feedback -> Admin queue."""
    # Cleanup: remove any existing onboarding progress for test user (id=999)
    from models.help import HelpOnboardingProgress

    help_db.query(HelpOnboardingProgress).filter(
        HelpOnboardingProgress.user_id == 999
    ).delete()
    help_db.commit()

    # 1. Status (public)
    r = help_client.get("/api/v1/help/status")
    assert r.status_code == 200
    data = r.json()
    assert "modes" in data
    assert data["modes"]["onboarding"] is True

    # 2. Onboarding status (new user, no entry yet)
    r = help_client.get("/api/v1/help/onboarding/status")
    assert r.status_code == 200
    assert r.json()["current_step"] == 0
    assert r.json()["completed"] is False

    # 3. Complete step 0
    r = help_client.put("/api/v1/help/onboarding/step", json={"step": 0})
    assert r.status_code == 200
    assert 0 in r.json()["completed_steps"]
    assert r.json()["current_step"] == 1

    # 4. Context hint (no hints seeded for test DB -> null)
    r = help_client.get("/api/v1/help/context/documents%2Fupload")
    assert r.status_code == 200

    # 5. Submit feedback
    r = help_client.post(
        "/api/v1/help/feedback",
        json={
            "question": "Wie lade ich ein PDF hoch?",
            "rating": "up",
            "route": "/documents",
        },
    )
    assert r.status_code == 200
    feedback_id = r.json()["id"]
    assert feedback_id is not None

    # 6. Admin: feedback queue
    r = admin_client.get("/api/v1/help/admin/feedback-queue")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
