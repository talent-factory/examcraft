# core/backend/tests/test_dashboard_api.py
"""Tests für Dashboard API (TF-319)"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.auth import Institution, User, UserStatus
from models.document import Document, DocumentStatus
from models.question_review import QuestionReview, ReviewStatus
from models.exam import Exam
from utils.auth_utils import get_current_active_user
from database import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_institution(test_db: Session, name: str = "Test Inst") -> Institution:
    inst = Institution(
        name=name,
        slug=name.lower().replace(" ", "-"),
        domain=f"{name.lower().replace(' ', '')}.ch",
        subscription_tier="free",
        max_users=10,
        max_documents=100,
        max_questions_per_month=500,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def make_user(test_db: Session, institution_id: int, email: str = "u@test.ch") -> User:
    user = User(
        email=email,
        first_name="Test",
        last_name="User",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()
    return user


def make_document(test_db: Session, institution_id: int, user_id: int, filename: str = "doc.pdf") -> Document:
    doc = Document(
        filename=filename,
        original_filename=filename,
        file_path=f"/tmp/{filename}",
        file_size=1024,
        mime_type="application/pdf",
        institution_id=institution_id,
        user_id=user_id,
    )
    test_db.add(doc)
    test_db.flush()
    return doc


def make_question(test_db: Session, institution_id: int, user_id: int,
                  status: str = ReviewStatus.PENDING.value, topic: str = "Mathe") -> QuestionReview:
    q = QuestionReview(
        question_text="Was ist 2+2?",
        question_type="open_ended",
        difficulty="easy",
        topic=topic,
        language="de",
        review_status=status,
        institution_id=institution_id,
        created_by=user_id,
    )
    test_db.add(q)
    test_db.flush()
    return q


def make_exam(test_db: Session, institution_id: int, user_id: int, title: str = "Prüfung 1") -> Exam:
    exam = Exam(
        title=title,
        institution_id=institution_id,
        created_by=user_id,
    )
    test_db.add(exam)
    test_db.flush()
    return exam


def make_dashboard_client(test_db: Session, institution_id: int, user_id: int):
    """TestClient mit übergebener DB-Session und User-Override.

    Registriert den Dashboard-Router direkt (ohne lifespan), analog zu
    test_exam_api.py – FastAPI dedupliziert identische Routen.
    """
    import api.dashboard as dashboard_module
    from models.auth import User as UserModel

    mock_user = test_db.get(UserModel, user_id)

    # Register router directly – avoids triggering the full lifespan
    app.include_router(dashboard_module.router)

    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: test_db
    client = TestClient(app, raise_server_exceptions=True)
    return client


# ---------------------------------------------------------------------------
# Stats Tests
# ---------------------------------------------------------------------------

class TestDashboardStats:

    def test_stats_returns_zeros_for_empty_institution(self, test_db: Session):
        """Leere Institution → alle Werte 0."""
        inst = make_institution(test_db, "Empty Inst")
        user = make_user(test_db, inst.id, "empty@test.ch")
        test_db.commit()

        client = make_dashboard_client(test_db, inst.id, user.id)
        try:
            resp = client.get("/api/dashboard/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["generated_questions"] == 0
            assert data["documents"] == 0
            assert data["validated_questions"] == 0
            assert data["exams"] == 0
        finally:
            app.dependency_overrides.clear()

    def test_stats_counts_own_institution_only(self, test_db: Session):
        """Counts sind institution-weit, nicht global."""
        inst_a = make_institution(test_db, "Inst A")
        inst_b = make_institution(test_db, "Inst B")
        user_a = make_user(test_db, inst_a.id, "a@test.ch")
        user_b = make_user(test_db, inst_b.id, "b@test.ch")

        # inst_a: 2 docs, 3 questions (1 approved), 1 exam
        make_document(test_db, inst_a.id, user_a.id, "a1.pdf")
        make_document(test_db, inst_a.id, user_a.id, "a2.pdf")
        make_question(test_db, inst_a.id, user_a.id, ReviewStatus.APPROVED.value)
        make_question(test_db, inst_a.id, user_a.id, ReviewStatus.PENDING.value)
        make_question(test_db, inst_a.id, user_a.id, ReviewStatus.PENDING.value)
        make_exam(test_db, inst_a.id, user_a.id)

        # inst_b: 5 docs (sollten für user_a nicht sichtbar sein)
        for i in range(5):
            make_document(test_db, inst_b.id, user_b.id, f"b{i}.pdf")

        test_db.commit()

        client = make_dashboard_client(test_db, inst_a.id, user_a.id)
        try:
            resp = client.get("/api/dashboard/stats")
            assert resp.status_code == 200
            data = resp.json()
            assert data["documents"] == 2
            assert data["generated_questions"] == 3
            assert data["validated_questions"] == 1
            assert data["exams"] == 1
        finally:
            app.dependency_overrides.clear()

    def test_stats_requires_auth(self):
        """Unauthentifizierter Request → 401."""
        import api.dashboard as dashboard_module

        app.dependency_overrides.clear()
        # Register router directly – no lifespan, no external services needed
        app.include_router(dashboard_module.router)
        unauthenticated = TestClient(app, raise_server_exceptions=True)
        resp = unauthenticated.get("/api/dashboard/stats")
        assert resp.status_code == 401


class TestDashboardActivity:

    def test_activity_empty(self, test_db: Session):
        """Keine Daten → leere Liste."""
        inst = make_institution(test_db, "Empty Act")
        user = make_user(test_db, inst.id, "emptyact@test.ch")
        test_db.commit()

        client = make_dashboard_client(test_db, inst.id, user.id)
        try:
            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            data = resp.json()
            assert data["activities"] == []
        finally:
            app.dependency_overrides.clear()

    def test_activity_returns_max_10(self, test_db: Session):
        """Mehr als 10 Datensätze → nur 10 werden zurückgegeben."""
        inst = make_institution(test_db, "Many Act")
        user = make_user(test_db, inst.id, "manyact@test.ch")

        for i in range(15):
            make_document(test_db, inst.id, user.id, f"doc{i}.pdf")
        test_db.commit()

        client = make_dashboard_client(test_db, inst.id, user.id)
        try:
            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["activities"]) == 10
        finally:
            app.dependency_overrides.clear()

    def test_activity_types_present(self, test_db: Session):
        """Alle vier Aktivitätstypen werden korrekt zurückgegeben."""
        inst = make_institution(test_db, "Types Act")
        user = make_user(test_db, inst.id, "types@test.ch")
        make_document(test_db, inst.id, user.id, "file.pdf")
        make_question(test_db, inst.id, user.id, ReviewStatus.PENDING.value, "Physik")
        make_question(test_db, inst.id, user.id, ReviewStatus.APPROVED.value, "Chemie")
        make_exam(test_db, inst.id, user.id, "Final Exam")
        test_db.commit()

        client = make_dashboard_client(test_db, inst.id, user.id)
        try:
            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            data = resp.json()
            types = {a["type"] for a in data["activities"]}
            assert "document_uploaded" in types
            assert "questions_generated" in types
            assert "question_approved" in types
            assert "exam_created" in types
        finally:
            app.dependency_overrides.clear()

    def test_activity_sorted_by_timestamp_desc(self, test_db: Session):
        """Aktivitäten sind absteigend nach timestamp sortiert."""
        inst = make_institution(test_db, "Sort Act")
        user = make_user(test_db, inst.id, "sort@test.ch")
        make_document(test_db, inst.id, user.id, "first.pdf")
        make_document(test_db, inst.id, user.id, "second.pdf")
        test_db.commit()

        client = make_dashboard_client(test_db, inst.id, user.id)
        try:
            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            data = resp.json()
            timestamps = [a["timestamp"] for a in data["activities"]]
            assert timestamps == sorted(timestamps, reverse=True)
        finally:
            app.dependency_overrides.clear()

    def test_activity_isolates_institution(self, test_db: Session):
        """Activities einer anderen Institution sind nicht sichtbar."""
        inst_a = make_institution(test_db, "ActA")
        inst_b = make_institution(test_db, "ActB")
        user_a = make_user(test_db, inst_a.id, "acta@test.ch")
        user_b = make_user(test_db, inst_b.id, "actb@test.ch")

        make_document(test_db, inst_b.id, user_b.id, "b_doc.pdf")
        test_db.commit()

        client = make_dashboard_client(test_db, inst_a.id, user_a.id)
        try:
            resp = client.get("/api/dashboard/activity")
            assert resp.status_code == 200
            assert resp.json()["activities"] == []
        finally:
            app.dependency_overrides.clear()
