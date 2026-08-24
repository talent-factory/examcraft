"""Tests for tag_ids in create_question_review."""

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.auth import Institution, User, UserStatus
from models.question_review import QuestionReview
from models.tag import Tag, QuestionTag
from utils.auth_utils import get_current_user
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def qct_db(test_engine):
    from sqlalchemy.orm import sessionmaker

    Session_ = sessionmaker(bind=test_engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture()
def qct_client(qct_db: Session):
    import api.question_review as qr_module

    app.include_router(qr_module.router)

    def override_get_db():
        yield qct_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix):
    inst = Institution(
        name=f"QCT Uni {suffix}",
        slug=f"qct-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def make_user(db, institution_id, suffix):
    user = User(
        email=f"qctuser{suffix}@test.com",
        first_name="QCT",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def make_tag(db, institution_id, name, scope="institution", archived=False):
    tag = Tag(
        name=name,
        institution_id=institution_id if scope == "institution" else None,
        scope=scope,
        usage_count=0,
        is_archived=archived,
    )
    db.add(tag)
    db.flush()
    return tag


QUESTION_PAYLOAD = {
    "question_text": "Was ist eine abstrakte Klasse in Python?",
    "question_type": "open_ended",
    "difficulty": "medium",
    "topic": "Python OOP",
    "language": "de",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCreateQuestionWithTags:
    def test_create_with_valid_tag_ids_assigns_tags(self, qct_db, qct_client):
        inst = make_institution(qct_db, "c1")
        user = make_user(qct_db, inst.id, "c1")
        tag1 = make_tag(qct_db, inst.id, "python")
        tag2 = make_tag(qct_db, inst.id, "oop")
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [tag1.id, tag2.id]},
        )
        assert resp.status_code == 201
        returned_tag_ids = [t["id"] for t in resp.json()["tags"]]
        assert tag1.id in returned_tag_ids
        assert tag2.id in returned_tag_ids

    def test_create_with_valid_tag_id_creates_question_tag_row(
        self, qct_db, qct_client
    ):
        inst = make_institution(qct_db, "c2")
        user = make_user(qct_db, inst.id, "c2")
        tag = make_tag(qct_db, inst.id, "algorithmen")
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [tag.id]},
        )

        assert resp.status_code == 201
        assert (
            qct_db.query(QuestionTag).filter(QuestionTag.tag_id == tag.id).count() == 1
        )

    def test_create_without_tag_ids_creates_question_normally(self, qct_db, qct_client):
        inst = make_institution(qct_db, "c3")
        user = make_user(qct_db, inst.id, "c3")
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = qct_client.post("/api/v1/questions/review", json=QUESTION_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["tags"] == []

    def test_create_with_archived_tag_id_returns_422(self, qct_db, qct_client):
        inst = make_institution(qct_db, "c4")
        user = make_user(qct_db, inst.id, "c4")
        tag = make_tag(qct_db, inst.id, "archiviert", archived=True)
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [tag.id]},
        )
        assert resp.status_code == 422

    def test_create_with_archived_tag_rolls_back_question(self, qct_db, qct_client):
        """Regression guard: invalid tag validation must NOT persist a question."""
        inst = make_institution(qct_db, "c4r")
        user = make_user(qct_db, inst.id, "c4r")
        tag = make_tag(qct_db, inst.id, "archiviert-rollback", archived=True)
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        before = qct_db.query(QuestionReview).count()
        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [tag.id]},
        )
        assert resp.status_code == 422
        qct_db.expire_all()
        assert qct_db.query(QuestionReview).count() == before

    def test_create_with_foreign_institution_tag_returns_422(self, qct_db, qct_client):
        """Cross-tenant enumeration: foreign tag IDs return the same 422 as unknown ones."""
        inst_a = make_institution(qct_db, "c5a")
        inst_b = make_institution(qct_db, "c5b")
        user_a = make_user(qct_db, inst_a.id, "c5a")
        foreign_tag = make_tag(qct_db, inst_b.id, "fremder-tag")
        qct_db.commit()

        user_a.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user_a

        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [foreign_tag.id]},
        )
        assert resp.status_code == 422
        # Response must not reflect back the foreign ID
        assert str(foreign_tag.id) not in resp.text

    def test_create_with_foreign_tag_rolls_back_question(self, qct_db, qct_client):
        inst_a = make_institution(qct_db, "c5ar")
        inst_b = make_institution(qct_db, "c5br")
        user_a = make_user(qct_db, inst_a.id, "c5ar")
        foreign_tag = make_tag(qct_db, inst_b.id, "fremder-tag-r")
        qct_db.commit()

        user_a.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user_a

        before = qct_db.query(QuestionReview).count()
        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [foreign_tag.id]},
        )
        assert resp.status_code == 422
        qct_db.expire_all()
        assert qct_db.query(QuestionReview).count() == before

    def test_create_with_nonexistent_tag_id_returns_422(self, qct_db, qct_client):
        inst = make_institution(qct_db, "c6")
        user = make_user(qct_db, inst.id, "c6")
        qct_db.commit()

        user.has_permission = Mock(return_value=True)
        qct_client.app.dependency_overrides[get_current_user] = lambda: user

        before = qct_db.query(QuestionReview).count()
        resp = qct_client.post(
            "/api/v1/questions/review",
            json={**QUESTION_PAYLOAD, "tag_ids": [99999]},
        )
        assert resp.status_code == 422
        qct_db.expire_all()
        assert qct_db.query(QuestionReview).count() == before
