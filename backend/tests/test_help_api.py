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
        assert data["i18n_key"] is None

    def test_returns_hint_for_matching_route(self, help_client, help_db):
        from models.help import HelpContextHint

        # Ein Muster, das mit keinem gesäten kollidiert: der Abgleich ist ein
        # Präfix-Test, "/documents/upload" trifft also auch den echten
        # "/documents"-Hinweis — je nach Reihenfolge gewann mal der, mal dieser.
        hint = HelpContextHint(
            route_pattern="/zzz-test-route",
            role="teacher",
            i18n_key="help.hints.test",
            priority=10,
            active=True,
        )
        help_db.add(hint)
        help_db.commit()

        response = help_client.get("/api/v1/help/context/zzz-test-route")
        assert response.status_code == 200
        data = response.json()
        assert data["i18n_key"] == "help.hints.test"

    def test_response_carries_no_text(self, help_client, help_db):
        """The API must not ship hint prose in any language.

        The four hint_text_* columns made this the only help surface whose
        language the server decided, so it was the only one that did not
        follow the language switcher (TF-625/TF-670).
        """
        from models.help import HelpContextHint

        help_db.add(
            HelpContextHint(
                route_pattern="/exams/compose",
                role="teacher",
                i18n_key="help.hints.examsCompose",
                priority=5,
                active=True,
            )
        )
        help_db.commit()

        data = help_client.get("/api/v1/help/context/exams/compose").json()
        assert set(data.keys()) == {"i18n_key", "hint_id"}


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


class TestOnboardingTracks:
    """Optional deep-dive tracks (TF-625)."""

    TRACK = "/api/v1/help/onboarding/track/auswertungen/step"

    @staticmethod
    def _reset(help_db):
        from models.help import HelpOnboardingProgress

        help_db.query(HelpOnboardingProgress).filter_by(user_id=999).delete()
        help_db.commit()

    def test_status_exposes_empty_track_progress_for_new_user(self, help_client):
        response = help_client.get("/api/v1/help/onboarding/status")
        assert response.status_code == 200
        assert response.json()["track_progress"] == {}

    def test_track_step_records_progress(self, help_client, help_db):
        self._reset(help_db)

        response = help_client.put(self.TRACK, json={"step": 0, "total_steps": 3})
        assert response.status_code == 200
        track = response.json()["track_progress"]["auswertungen"]
        assert track["completed_steps"] == [0]
        assert track["current_step"] == 1
        assert track["completed"] is False

    def test_track_completes_at_last_step(self, help_client, help_db):
        self._reset(help_db)

        help_client.put(self.TRACK, json={"step": 0, "total_steps": 3})
        help_client.put(self.TRACK, json={"step": 1, "total_steps": 3})
        response = help_client.put(self.TRACK, json={"step": 2, "total_steps": 3})

        track = response.json()["track_progress"]["auswertungen"]
        assert track["current_step"] == 3
        assert track["completed"] is True

    def test_track_step_does_not_touch_core_tour(self, help_client, help_db):
        """The heart of the chosen design: a deep dive must neither advance the
        core tour nor mark it complete."""
        self._reset(help_db)

        # Core tour sits at step 1 of 8
        help_client.put("/api/v1/help/onboarding/step", json={"step": 0})

        # Run a whole deep dive end to end
        for step in range(3):
            help_client.put(self.TRACK, json={"step": step, "total_steps": 3})

        data = help_client.get("/api/v1/help/onboarding/status").json()
        assert data["current_step"] == 1
        assert data["completed"] is False
        assert data["completed_steps"] == [0]
        assert data["track_progress"]["auswertungen"]["completed"] is True

    def test_skipped_track_step_lands_in_skipped_not_completed(
        self, help_client, help_db
    ):
        self._reset(help_db)

        response = help_client.put(
            self.TRACK, json={"step": 1, "total_steps": 3, "skipped": True}
        )
        track = response.json()["track_progress"]["auswertungen"]
        assert track["skipped_steps"] == [1]
        assert track["completed_steps"] == []
        assert track["current_step"] == 2

    def test_catch_up_moves_step_from_skipped_to_completed(self, help_client, help_db):
        self._reset(help_db)

        help_client.put(self.TRACK, json={"step": 1, "total_steps": 3, "skipped": True})
        response = help_client.put(self.TRACK, json={"step": 1, "total_steps": 3})

        track = response.json()["track_progress"]["auswertungen"]
        assert track["completed_steps"] == [1]
        assert track["skipped_steps"] == []

    def test_replaying_earlier_step_does_not_rewind_track(self, help_client, help_db):
        """Replaying an earlier step must not rewind progress."""
        self._reset(help_db)

        help_client.put(self.TRACK, json={"step": 2, "total_steps": 3})
        response = help_client.put(self.TRACK, json={"step": 0, "total_steps": 3})

        track = response.json()["track_progress"]["auswertungen"]
        assert track["current_step"] == 3
        assert track["completed"] is True

    def test_tracks_are_independent(self, help_client, help_db):
        self._reset(help_db)

        help_client.put(self.TRACK, json={"step": 0, "total_steps": 3})
        help_client.put(
            "/api/v1/help/onboarding/track/exam-composer/step",
            json={"step": 0, "total_steps": 1},
        )

        tracks = help_client.get("/api/v1/help/onboarding/status").json()[
            "track_progress"
        ]
        assert tracks["auswertungen"]["completed"] is False
        assert tracks["exam-composer"]["completed"] is True

    def test_fully_skipped_track_is_not_marked_complete(self, help_client, help_db):
        """A track nobody ever saw must not report itself as done.

        Found manually: the three analytics steps anchored on table elements
        that only render once data exists. On an empty account every step fell
        through the skip path, yet the widget showed the track with a tick —
        the TF-604 failure mode one level down.
        """
        self._reset(help_db)

        for step in range(3):
            help_client.put(
                self.TRACK, json={"step": step, "total_steps": 3, "skipped": True}
            )

        track = help_client.get("/api/v1/help/onboarding/status").json()[
            "track_progress"
        ]["auswertungen"]
        assert track["skipped_steps"] == [0, 1, 2]
        assert track["completed"] is False

    def test_partially_skipped_track_still_completes(self, help_client, help_db):
        """One genuinely shown step is enough — the user did see something."""
        self._reset(help_db)

        help_client.put(self.TRACK, json={"step": 0, "total_steps": 3, "skipped": True})
        help_client.put(self.TRACK, json={"step": 1, "total_steps": 3})
        response = help_client.put(
            self.TRACK, json={"step": 2, "total_steps": 3, "skipped": True}
        )

        track = response.json()["track_progress"]["auswertungen"]
        assert track["completed"] is True

    def test_catch_up_after_full_skip_completes_the_track(self, help_client, help_db):
        """Re-running a fully skipped track once the anchors work marks it done."""
        self._reset(help_db)

        for step in range(3):
            help_client.put(
                self.TRACK, json={"step": step, "total_steps": 3, "skipped": True}
            )
        for step in range(3):
            response = help_client.put(
                self.TRACK, json={"step": step, "total_steps": 3}
            )

        track = response.json()["track_progress"]["auswertungen"]
        assert track["skipped_steps"] == []
        assert track["completed"] is True

    def test_rejects_invalid_track_id(self, help_client, help_db):
        self._reset(help_db)

        response = help_client.put(
            "/api/v1/help/onboarding/track/Not_A_Valid_ID/step",
            json={"step": 0, "total_steps": 1},
        )
        assert response.status_code == 422

    def test_rejects_step_beyond_total(self, help_client, help_db):
        self._reset(help_db)

        response = help_client.put(self.TRACK, json={"step": 3, "total_steps": 3})
        assert response.status_code == 422

    def test_caps_number_of_tracks(self, help_client, help_db):
        """Prevent unbounded growth of the JSON column via invented track ids."""
        from api.v1.help import MAX_TRACKS_PER_USER

        self._reset(help_db)

        for i in range(MAX_TRACKS_PER_USER):
            response = help_client.put(
                f"/api/v1/help/onboarding/track/track-{i}/step",
                json={"step": 0, "total_steps": 1},
            )
            assert response.status_code == 200

        response = help_client.put(
            "/api/v1/help/onboarding/track/one-too-many/step",
            json={"step": 0, "total_steps": 1},
        )
        assert response.status_code == 422

        # A track already known stays writable even when the cap is reached
        response = help_client.put(
            "/api/v1/help/onboarding/track/track-0/step",
            json={"step": 0, "total_steps": 1},
        )
        assert response.status_code == 200


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
        assert data["i18n_key"] == "help.hints.prompts"

    def test_seed_upserts_role_on_existing_hint(self, help_db):
        """seed_help_hints updates role=admin -> None on existing /prompts hint."""
        from utils.seed_help_hints import seed_help_hints
        from models.help import HelpContextHint

        # Seed a wrong version
        old = HelpContextHint(
            route_pattern="/prompts",
            role="admin",
            i18n_key="help.hints.stale",
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

    def test_seed_commits_a_delete_only_run(self, help_db):
        """A run that only removes obsolete rows (created==updated==0) still commits.

        Regression guard for the exact bug the function's own comment warns
        about: `removed` must be part of the `created > 0 or updated > 0 or
        removed > 0` condition, or a delete-only run commits nothing and the
        DELETE is rolled back when the session closes.
        """
        from utils.seed_help_hints import seed_help_hints, DEFAULT_HINTS
        from models.help import HelpContextHint

        help_db.query(HelpContextHint).delete()
        help_db.commit()

        # First run creates all current hints — nothing left to create/update
        # on the run under test.
        seed_help_hints(help_db)

        # Insert a row for an obsolete pattern directly, bypassing the seed,
        # so the next run's only work is the delete.
        obsolete = HelpContextHint(
            route_pattern="/documents/upload",
            role="teacher",
            i18n_key="help.hints.stale",
            priority=1,
            active=True,
        )
        help_db.add(obsolete)
        help_db.commit()
        obsolete_id = obsolete.id

        result = seed_help_hints(help_db)

        assert result == 0  # created + updated, i.e. neither fired

        # A plain re-query here would pass even on the buggy version: the
        # DELETE already ran against this transaction regardless of whether
        # `db.commit()` was reached, so it's invisible to this session either
        # way. The only thing that distinguishes "committed" from "rolled
        # back at session close" is surviving an explicit rollback: on the
        # bug, `db.commit()` is never called, `db.rollback()` reverts the
        # DELETE, and the obsolete row reappears.
        help_db.rollback()

        remaining = help_db.get(HelpContextHint, obsolete_id)
        assert remaining is None, (
            "obsolete row reappeared after rollback — the delete-only run "
            "did not commit"
        )

        count = help_db.query(HelpContextHint).count()
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
