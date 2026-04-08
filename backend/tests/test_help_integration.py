"""Integration test: full Help Widget flow (TF-308)."""

# Fixtures help_db, help_client, admin_client are defined in conftest.py


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
