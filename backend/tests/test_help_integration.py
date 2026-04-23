"""Integration test: full Help Widget flow (TF-308)."""

# Fixtures help_db, help_client, admin_client are defined in conftest.py

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.help_service import HelpService


@pytest.mark.asyncio
async def test_low_confidence_retries_with_sonnet():
    """answer_question retries with model='sonnet' when first call returns confidence < 0.6."""
    mock_db = MagicMock()
    service = HelpService(mock_db)

    high_score_chunk = {
        "content": "Some helpful documentation content.",
        "source_file": "docs/help.md",
        "section": "Getting Started",
        "language": "de",
        "score": 0.85,
    }

    first_result = {
        "answer": "Weak answer",
        "confidence": 0.4,
        "sources": [],
        "docs_links": [],
    }
    second_result = {
        "answer": "Strong answer",
        "confidence": 0.85,
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
            new=AsyncMock(side_effect=[first_result, second_result]),
        ) as mock_call,
    ):
        result = await service.answer_question(
            question="Wie exportiere ich eine Prüfung?",
            user_role="teacher",
            user_tier="starter",
            route="/exams",
        )

    assert mock_call.call_count == 2
    # Second call must have model="sonnet"
    _, second_kwargs = mock_call.call_args_list[1]
    assert second_kwargs.get("model") == "sonnet"
    assert result["confidence"] == 0.85


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
