"""Tests für Help Widget API (TF-308)."""

from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

# Fixtures help_db, help_client, admin_client are defined in conftest.py


class TestHelpStatus:
    def test_returns_available_modes(self, help_client):
        response = help_client.get("/api/v1/help/status")
        assert response.status_code == 200
        data = response.json()
        assert "modes" in data
        assert data["modes"]["onboarding"] is True
        assert data["modes"]["context"] is True
        assert isinstance(data["modes"]["chat"], bool)


class TestHelpOnboarding:
    def test_get_status_new_user(self, help_client):
        response = help_client.get("/api/v1/help/onboarding/status")
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 0
        assert data["completed_steps"] == []
        assert data["completed"] is False

    def test_complete_step(self, help_client):
        response = help_client.put("/api/v1/help/onboarding/step", json={"step": 0})
        assert response.status_code == 200
        data = response.json()
        assert 0 in data["completed_steps"]
        assert data["current_step"] == 1

    def test_teacher_tour_not_completed_at_step_6(self, help_client):
        """Step 6 (Prompt-Bibliothek) should advance to current_step=7 but NOT mark as completed (max=8)."""
        response = help_client.put("/api/v1/help/onboarding/step", json={"step": 6})
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 7
        assert data["completed"] is False

    def test_teacher_tour_completed_at_step_7(self, help_client):
        """Step 7 is the last step — current_step=8 == max_steps → completed=True."""
        response = help_client.put("/api/v1/help/onboarding/step", json={"step": 7})
        assert response.status_code == 200
        data = response.json()
        assert data["current_step"] == 8
        assert data["completed"] is True


class TestContextHints:
    def test_returns_null_when_no_match(self, help_client):
        response = help_client.get("/api/v1/help/context/nonexistent/route")
        assert response.status_code == 200
        data = response.json()
        assert data["hint_text"] is None

    def test_returns_hint_for_matching_route(self, help_client, help_db):
        from models.help import HelpContextHint

        hint = HelpContextHint(
            route_pattern="/documents/upload",
            role="teacher",
            hint_text_de="Test-Hinweis",
            hint_text_en="Test hint",
            priority=10,
            active=True,
        )
        help_db.add(hint)
        help_db.commit()

        response = help_client.get("/api/v1/help/context/documents/upload")
        assert response.status_code == 200
        data = response.json()
        assert data["hint_text"] is not None


class TestHelpMessage:
    def test_requires_auth(self):
        from main import app

        client = TestClient(app)
        response = client.post("/api/v1/help/message", json={"question": "Test?"})
        assert response.status_code in [401, 403]

    def test_returns_answer(self, help_client):
        mock_result = {
            "answer": "Du kannst PDFs über den Upload-Tab hochladen.",
            "confidence": 0.85,
            "sources": [],
            "docs_links": [],
            "escalate": False,
            "from_cache": False,
        }
        with patch(
            "services.help_service.HelpService.answer_question",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = help_client.post(
                "/api/v1/help/message",
                json={"question": "Wie lade ich ein PDF hoch?", "route": "/documents"},
            )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["confidence"] > 0


class TestFeedback:
    def test_submit_feedback(self, help_client):
        response = help_client.post(
            "/api/v1/help/feedback",
            json={
                "question": "Wie exportiere ich?",
                "rating": "down",
                "route": "/exam/export",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "offen"
        assert "id" in data

    def test_invalid_rating_rejected(self, help_client):
        response = help_client.post(
            "/api/v1/help/feedback",
            json={"question": "Test", "rating": "invalid"},
        )
        assert response.status_code == 422


class TestAdminEndpoints:
    def test_feedback_queue_requires_admin(self, help_client):
        response = help_client.get("/api/v1/help/admin/feedback-queue")
        assert response.status_code == 403

    def test_feedback_queue_for_admin(self, admin_client, help_db):
        from models.help import HelpFeedback

        fb = HelpFeedback(question="Test?", rating="down", status="offen")
        help_db.add(fb)
        help_db.commit()

        response = admin_client.get("/api/v1/help/admin/feedback-queue")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["total"] >= 1

    def test_metrics_for_admin(self, admin_client):
        response = admin_client.get("/api/v1/help/admin/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "total_questions" in data
        assert "positive_feedback_pct" in data


class TestSkipOnboardingStep:
    def test_skip_adds_to_skipped_not_completed(self, help_client, help_db):
        """Skipping a step writes to skipped_steps, NOT completed_steps."""
        from models.help import HelpOnboardingProgress

        help_db.query(HelpOnboardingProgress).filter_by(user_id=999).delete()
        help_db.commit()

        response = help_client.put("/api/v1/help/onboarding/skip", json={"step": 2})
        assert response.status_code == 200
        data = response.json()
        assert 2 in data["skipped_steps"]
        assert 2 not in data["completed_steps"]
        assert data["current_step"] == 3

    def test_skip_advances_current_step(self, help_client, help_db):
        """Skipping multiple steps each advance current_step by 1."""
        from models.help import HelpOnboardingProgress

        help_db.query(HelpOnboardingProgress).filter_by(user_id=999).delete()
        help_db.commit()

        help_client.put("/api/v1/help/onboarding/skip", json={"step": 1})
        response = help_client.put("/api/v1/help/onboarding/skip", json={"step": 2})
        data = response.json()
        assert data["current_step"] == 3
        assert data["skipped_steps"] == [1, 2]

    def test_skip_sets_completed_at_when_max_steps_reached(self, help_client, help_db):
        """Skipping the last step (7 for teacher) marks tour as completed."""
        from models.help import HelpOnboardingProgress

        help_db.query(HelpOnboardingProgress).filter_by(user_id=999).delete()
        help_db.commit()

        response = help_client.put("/api/v1/help/onboarding/skip", json={"step": 7})
        data = response.json()
        assert data["completed"] is True

    def test_complete_step_removes_from_skipped(self, help_client, help_db):
        """Completing a previously-skipped step moves it from skipped to completed."""
        from models.help import HelpOnboardingProgress

        help_db.query(HelpOnboardingProgress).filter_by(user_id=999).delete()
        help_db.commit()

        # First skip step 2
        help_client.put("/api/v1/help/onboarding/skip", json={"step": 2})
        # Then complete it (catch-up)
        response = help_client.put("/api/v1/help/onboarding/step", json={"step": 2})
        data = response.json()
        assert 2 in data["completed_steps"]
        assert 2 not in data["skipped_steps"]


class TestSeedHints:
    def test_prompts_hint_visible_to_teacher_after_seed(self, help_client, help_db):
        """After seeding, teacher (role=teacher) gets a hint for /prompts."""
        from utils.seed_help_hints import seed_help_hints
        from models.help import HelpContextHint

        # Clean slate
        help_db.query(HelpContextHint).delete()
        help_db.commit()

        seed_help_hints(help_db)

        response = help_client.get("/api/v1/help/context/prompts")
        assert response.status_code == 200
        data = response.json()
        assert data["hint_text"] is not None

    def test_seed_upserts_role_on_existing_hint(self, help_db):
        """seed_help_hints updates role=admin -> None on existing /prompts hint."""
        from utils.seed_help_hints import seed_help_hints
        from models.help import HelpContextHint

        # Seed a wrong version
        old = HelpContextHint(
            route_pattern="/prompts",
            role="admin",
            hint_text_de="alt",
            hint_text_en="old",
            priority=10,
            active=True,
        )
        help_db.add(old)
        help_db.commit()

        seed_help_hints(help_db)
        help_db.expire(old)

        updated = (
            help_db.query(HelpContextHint).filter_by(route_pattern="/prompts").first()
        )
        assert updated.role is None

    def test_seed_idempotent(self, help_db):
        """Running seed twice does not create duplicate hints."""
        from utils.seed_help_hints import seed_help_hints
        from models.help import HelpContextHint

        help_db.query(HelpContextHint).delete()
        help_db.commit()

        seed_help_hints(help_db)
        seed_help_hints(help_db)

        count = help_db.query(HelpContextHint).count()
        from utils.seed_help_hints import DEFAULT_HINTS

        assert count == len(DEFAULT_HINTS)


class TestDocsLinksUrlConversion:
    def test_docs_links_converted_to_urls(self, help_client):
        """ChatBot response docs_links should contain full URLs, not file paths."""
        mock_result = {
            "answer": "Du kannst Dokumente hochladen.",
            "confidence": 0.9,
            "sources": [
                {
                    "file": "core/docs-site/docs/user-guide/documents.md",
                    "section": "Upload",
                    "url": "https://docs.examcraft.ch/user-guide/documents/",
                }
            ],
            "docs_links": ["https://docs.examcraft.ch/user-guide/documents/"],
            "escalate": False,
            "from_cache": False,
        }
        with patch(
            "services.help_service.HelpService.answer_question",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = help_client.post(
                "/api/v1/help/message",
                json={
                    "question": "Wie lade ich Dokumente hoch?",
                    "route": "/documents",
                },
            )
        assert response.status_code == 200
        data = response.json()
        # Verify URLs are full https:// URLs, not file paths
        for link in data.get("docs_links", []):
            assert link.startswith("https://"), f"Expected URL, got: {link}"
        # Verify sources have url field
        for source in data.get("sources", []):
            if "url" in source:
                assert source["url"].startswith("https://")
