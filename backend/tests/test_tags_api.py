"""Tests für die Tags API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import Mock

from main import app
from models.auth import Institution, User, UserStatus
from models.tag import Tag


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_mock_user(institution_id: int, user_id: int) -> Mock:
    user = Mock()
    user.id = user_id
    user.institution_id = institution_id
    user.has_permission = Mock(return_value=True)
    user.status = UserStatus.ACTIVE.value
    user.roles = []
    return user


def make_institution(db: Session, suffix: str) -> Institution:
    inst = Institution(
        name=f"Test Uni {suffix}",
        slug=f"test-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.commit()
    db.refresh(inst)
    return inst


def make_user(db: Session, institution_id: int, suffix: str) -> User:
    user = User(
        email=f"taguser{suffix}@test.com",
        first_name="Tag",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_tag(db: Session, institution_id: int, name: str) -> Tag:
    tag = Tag(name=name, institution_id=institution_id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def tags_db(test_engine):
    """Plain committable session (no wrapping transaction)."""
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    yield session
    session.close()


@pytest.fixture()
def tags_client(tags_db: Session):
    """TestClient without lifespan; tags, question_review and exams routers included directly."""
    import api.tags as tags_module
    import api.question_review as question_review_module
    import api.exams as exams_api

    from database import get_db

    # include_router is idempotent in this test setup; the routers are already
    # registered via main.py but we call them here to guarantee the routes exist
    # even when tests run in isolation.
    app.include_router(tags_module.router)
    app.include_router(question_review_module.router)
    app.include_router(exams_api.router)

    def override_get_db():
        yield tags_db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListTags:
    def test_list_tags_returns_institution_tags_only(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst_a = make_institution(tags_db, "lsta")
        inst_b = make_institution(tags_db, "lstb")
        user_a_db = make_user(tags_db, inst_a.id, "lsta")
        make_tag(tags_db, inst_a.id, "python")
        make_tag(tags_db, inst_a.id, "java")
        make_tag(tags_db, inst_b.id, "other-institution")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst_a.id, user_a_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.get("/api/v1/tags")

        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "python" in names
        assert "java" in names
        assert "other-institution" not in names

    def test_list_tags_empty_for_new_institution(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "empty")
        user_db = make_user(tags_db, inst.id, "empty")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.get("/api/v1/tags")

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_tags_sorted_alphabetically(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "sort")
        user_db = make_user(tags_db, inst.id, "sort")
        make_tag(tags_db, inst.id, "Zebra")
        make_tag(tags_db, inst.id, "alpha")
        make_tag(tags_db, inst.id, "Mitte")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.get("/api/v1/tags")

        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert names == sorted(names, key=str.lower)


class TestCreateTag:
    def test_create_tag_success(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "crt")
        user_db = make_user(tags_db, inst.id, "crt")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.post("/api/v1/tags", json={"name": "Neuer Tag"})

        assert resp.status_code == 200
        data = resp.json()
        assert (
            data["name"] == "Neuer Tag"
        )  # Original-Schreibweise erhalten (case-preserving)
        assert data["institution_id"] == inst.id
        assert "id" in data

    def test_create_tag_duplicate_returns_existing_tag(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        """create_tag ist idempotent — Duplikat gibt bestehenden Tag zurück (200)."""
        inst = make_institution(tags_db, "dup")
        user_db = make_user(tags_db, inst.id, "dup")
        existing = make_tag(tags_db, inst.id, "duplikat")
        tags_db.commit()

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.post("/api/v1/tags", json={"name": "Duplikat"})

        assert resp.status_code == 200
        assert resp.json()["id"] == existing.id

    def test_create_tag_name_too_long_returns_422(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "lng")
        user_db = make_user(tags_db, inst.id, "lng")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.post("/api/v1/tags", json={"name": "x" * 51})

        assert resp.status_code == 422

    def test_create_tag_strips_name(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        """Leerzeichen werden entfernt, Schreibweise wird erhalten (case-preserving)."""
        inst = make_institution(tags_db, "strip")
        user_db = make_user(tags_db, inst.id, "strip")

        from utils.auth_utils import get_current_user

        mock_user = _make_mock_user(inst.id, user_db.id)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.post("/api/v1/tags", json={"name": "  Python  "})

        assert resp.status_code == 200
        assert resp.json()["name"] == "Python"  # Strip OK, Schreibweise erhalten

    def test_create_tag_without_permission_returns_403(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "noperm")
        user_db = make_user(tags_db, inst.id, "noperm")

        from utils.auth_utils import get_current_user

        # Viewer role: has_permission always returns False
        mock_user = _make_mock_user(inst.id, user_db.id)
        mock_user.has_permission = Mock(return_value=False)
        app.dependency_overrides[get_current_user] = lambda: mock_user

        resp = tags_client.post("/api/v1/tags", json={"name": "verboten"})

        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Question-Tag Endpunkte
# ---------------------------------------------------------------------------


from models.question_review import QuestionReview, ReviewStatus  # noqa: E402


def make_question(
    test_db: Session, institution_id: int, created_by: int
) -> QuestionReview:
    q = QuestionReview(
        question_text="Was ist eine Klasse in Python?",
        question_type="open_ended",
        difficulty="medium",
        topic="Python",
        language="de",
        review_status=ReviewStatus.APPROVED.value,
        institution_id=institution_id,
        created_by=created_by,
    )
    test_db.add(q)
    test_db.flush()
    return q


class TestQuestionTagEndpoints:
    def test_set_question_tags_success(self, tags_db, tags_client):
        inst = make_institution(tags_db, "qt1")
        user = make_user(tags_db, inst.id, "qt1")
        question = make_question(tags_db, inst.id, user.id)
        tag1 = make_tag(tags_db, inst.id, "python")
        tag2 = make_tag(tags_db, inst.id, "oop")
        tags_db.commit()

        # Override auth mit User der edit_questions hat
        from utils.auth_utils import get_current_user

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            f"/api/v1/questions/{question.id}/tags",
            json={"tag_ids": [tag1.id, tag2.id]},
        )
        assert resp.status_code == 200
        tag_ids_returned = [t["id"] for t in resp.json()["tags"]]
        assert tag1.id in tag_ids_returned
        assert tag2.id in tag_ids_returned

    def test_set_question_tags_replaces_existing(self, tags_db, tags_client):
        inst = make_institution(tags_db, "qt2")
        user = make_user(tags_db, inst.id, "qt2")
        question = make_question(tags_db, inst.id, user.id)
        tag_old = make_tag(tags_db, inst.id, "old")
        tag_new = make_tag(tags_db, inst.id, "new")
        tags_db.commit()

        from utils.auth_utils import get_current_user

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        tags_client.post(
            f"/api/v1/questions/{question.id}/tags", json={"tag_ids": [tag_old.id]}
        )
        resp = tags_client.post(
            f"/api/v1/questions/{question.id}/tags", json={"tag_ids": [tag_new.id]}
        )

        assert resp.status_code == 200
        tag_ids_returned = [t["id"] for t in resp.json()["tags"]]
        assert tag_new.id in tag_ids_returned
        assert tag_old.id not in tag_ids_returned

    def test_remove_question_tag_success(self, tags_db, tags_client):
        inst = make_institution(tags_db, "qt3")
        user = make_user(tags_db, inst.id, "qt3")
        question = make_question(tags_db, inst.id, user.id)
        tag = make_tag(tags_db, inst.id, "remove-me")
        tags_db.commit()

        from utils.auth_utils import get_current_user

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        tags_client.post(
            f"/api/v1/questions/{question.id}/tags", json={"tag_ids": [tag.id]}
        )
        resp = tags_client.delete(f"/api/v1/questions/{question.id}/tags/{tag.id}")

        assert resp.status_code == 200
        tag_ids_returned = [t["id"] for t in resp.json()["tags"]]
        assert tag.id not in tag_ids_returned

    def test_set_tags_foreign_institution_tag_rejected(self, tags_db, tags_client):
        # Cross-tenant enumeration is intentionally hidden: unknown and foreign
        # tag IDs both surface as a uniform 422 without echoing the IDs back.
        # See _assign_tags_to_question in api/question_review.py.
        inst_a = make_institution(tags_db, "qta")
        inst_b = make_institution(tags_db, "qtb")
        user_a = make_user(tags_db, inst_a.id, "qta")
        question = make_question(tags_db, inst_a.id, user_a.id)
        foreign_tag = make_tag(tags_db, inst_b.id, "foreign")
        tags_db.commit()

        from utils.auth_utils import get_current_user

        user_a.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user_a

        resp = tags_client.post(
            f"/api/v1/questions/{question.id}/tags",
            json={"tag_ids": [foreign_tag.id]},
        )
        assert resp.status_code == 422
        assert str(foreign_tag.id) not in resp.text  # no enumeration

    def test_set_nonexistent_tag_id_returns_422(self, tags_db, tags_client):
        # Cross-tenant enumeration prevention: missing IDs return 422 too.
        inst = make_institution(tags_db, "qt404")
        user = make_user(tags_db, inst.id, "qt404")
        question = make_question(tags_db, inst.id, user.id)
        tags_db.commit()

        from utils.auth_utils import get_current_user
        from unittest.mock import Mock

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            f"/api/v1/questions/{question.id}/tags",
            json={"tag_ids": [99999]},  # ID existiert nicht
        )
        assert resp.status_code == 422


class TestApprovedQuestionsTagFilter:
    def test_filter_by_tag_id_returns_matching_questions(self, tags_db, tags_client):
        from models.tag import QuestionTag as QT
        from utils.auth_utils import get_current_user
        from unittest.mock import Mock

        inst = make_institution(tags_db, "aqf1")
        user = make_user(tags_db, inst.id, "aqf1")
        q_tagged = make_question(tags_db, inst.id, user.id)
        q_untagged = make_question(tags_db, inst.id, user.id)
        tag = make_tag(tags_db, inst.id, "filterme")
        tags_db.add(QT(question_id=q_tagged.id, tag_id=tag.id))
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get(f"/api/v1/exams/approved-questions?tag_ids={tag.id}")
        assert resp.status_code == 200
        returned_ids = [q["id"] for q in resp.json()["questions"]]
        assert q_tagged.id in returned_ids
        assert q_untagged.id not in returned_ids

    def test_filter_by_multiple_tag_ids_uses_or_logic(self, tags_db, tags_client):
        from models.tag import QuestionTag as QT
        from utils.auth_utils import get_current_user
        from unittest.mock import Mock

        inst = make_institution(tags_db, "aqf2")
        user = make_user(tags_db, inst.id, "aqf2")
        q1 = make_question(tags_db, inst.id, user.id)
        q2 = make_question(tags_db, inst.id, user.id)
        q_none = make_question(tags_db, inst.id, user.id)
        tag1 = make_tag(tags_db, inst.id, "tagone")
        tag2 = make_tag(tags_db, inst.id, "tagtwo")
        tags_db.add(QT(question_id=q1.id, tag_id=tag1.id))
        tags_db.add(QT(question_id=q2.id, tag_id=tag2.id))
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get(
            f"/api/v1/exams/approved-questions?tag_ids={tag1.id},{tag2.id}"
        )
        assert resp.status_code == 200
        returned_ids = [q["id"] for q in resp.json()["questions"]]
        assert q1.id in returned_ids
        assert q2.id in returned_ids
        assert q_none.id not in returned_ids

    def test_invalid_tag_ids_returns_422(self, tags_db, tags_client):
        from utils.auth_utils import get_current_user
        from unittest.mock import Mock

        inst = make_institution(tags_db, "aqf_inv")
        user = make_user(tags_db, inst.id, "aqf_inv")
        tags_db.commit()
        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/exams/approved-questions?tag_ids=abc,xyz")
        assert resp.status_code == 422
