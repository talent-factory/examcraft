"""Tests for the extended Tags API — visibility, archive/unarchive, merge,
ownership permissions, case-insensitive uniqueness and global-tag scoping."""

import pytest
from unittest.mock import Mock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from models.auth import Institution, User, UserStatus
from models.tag import Tag, QuestionTag
from models.tag_merge_log import TagMergeLog
from models.question_review import QuestionReview, ReviewStatus
from utils.auth_utils import get_current_user
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures (analogous to test_tags_api.py)
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
    """TestClient with tags, question_review routers included."""
    import api.tags as tags_module
    import api.question_review as question_review_module

    app.include_router(tags_module.router)
    app.include_router(question_review_module.router)

    def override_get_db():
        yield tags_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db: Session, suffix: str) -> Institution:
    inst = Institution(
        name=f"Iter2 Uni {suffix}",
        slug=f"iter2-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def make_user(db: Session, institution_id: int, suffix: str) -> User:
    user = User(
        email=f"iter2user{suffix}@test.com",
        first_name="Iter2",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def make_tag(
    db: Session, institution_id: int, name: str, scope: str = "institution"
) -> Tag:
    tag = Tag(
        name=name,
        institution_id=institution_id if scope == "institution" else None,
        scope=scope,
        usage_count=0,
        is_archived=False,
    )
    db.add(tag)
    db.flush()
    return tag


def make_question(db: Session, institution_id: int, created_by: int) -> QuestionReview:
    q = QuestionReview(
        question_text="Testfrage für Iteration 2?",
        question_type="open_ended",
        difficulty="medium",
        topic="Test",
        language="de",
        review_status=ReviewStatus.APPROVED.value,
        institution_id=institution_id,
        created_by=created_by,
    )
    db.add(q)
    db.flush()
    return q


# Fixtures are inherited from conftest.py (tags_db, tags_client)
# The tags_client fixture already includes tags_module.router and qr_module.router.


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListTagsExtended:
    def test_list_tags_excludes_archived_by_default(self, tags_db, tags_client):
        inst = make_institution(tags_db, "la1")
        user = make_user(tags_db, inst.id, "la1")
        make_tag(tags_db, inst.id, "aktiv")
        archived = make_tag(tags_db, inst.id, "archiviert")
        archived.is_archived = True
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "aktiv" in names
        assert "archiviert" not in names

    def test_list_tags_includes_archived_when_requested(self, tags_db, tags_client):
        inst = make_institution(tags_db, "la2")
        user = make_user(tags_db, inst.id, "la2")
        archived = make_tag(tags_db, inst.id, "archiviert2")
        archived.is_archived = True
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/tags?include_archived=true")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "archiviert2" in names

    def test_list_tags_includes_global_tags(self, tags_db, tags_client):
        inst = make_institution(tags_db, "la3")
        user = make_user(tags_db, inst.id, "la3")
        global_tag = make_tag(tags_db, inst.id, "globaltag3", scope="global")
        global_tag.institution_id = None
        make_tag(tags_db, inst.id, "insttag3")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "globaltag3" in names
        assert "insttag3" in names

    def test_list_tags_response_has_new_fields(self, tags_db, tags_client):
        inst = make_institution(tags_db, "la4")
        user = make_user(tags_db, inst.id, "la4")
        make_tag(tags_db, inst.id, "fieldtest")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        tag = next(t for t in resp.json() if t["name"] == "fieldtest")
        assert "scope" in tag
        assert "usage_count" in tag
        assert "is_archived" in tag
        assert tag["scope"] == "institution"
        assert tag["usage_count"] == 0
        assert tag["is_archived"] is False


class TestArchiveUnarchive:
    def test_archive_tag_success(self, tags_db, tags_client):
        inst = make_institution(tags_db, "ar1")
        user = make_user(tags_db, inst.id, "ar1")
        tag = make_tag(tags_db, inst.id, "zuarchivieren")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is True

    def test_unarchive_tag_success(self, tags_db, tags_client):
        inst = make_institution(tags_db, "ar2")
        user = make_user(tags_db, inst.id, "ar2")
        tag = make_tag(tags_db, inst.id, "wiederherstellen")
        tag.is_archived = True
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/unarchive")
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is False

    def test_unarchive_own_tag_as_non_admin(self, tags_db, tags_client):
        inst = make_institution(tags_db, "ar2b")
        user = make_user(tags_db, inst.id, "ar2b")
        tag = make_tag(tags_db, inst.id, "eigener-archiviert")
        tag.is_archived = True
        tag.created_by = user.id
        tags_db.commit()

        user.has_permission = Mock(return_value=False)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/unarchive")
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is False

    def test_unarchive_others_tag_as_non_admin_returns_403(self, tags_db, tags_client):
        inst = make_institution(tags_db, "ar2c")
        owner = make_user(tags_db, inst.id, "ar2c-owner")
        requester = make_user(tags_db, inst.id, "ar2c-req")
        tag = make_tag(tags_db, inst.id, "fremder-archiviert")
        tag.is_archived = True
        tag.created_by = owner.id
        tags_db.commit()

        requester.has_permission = Mock(return_value=False)
        tags_client.app.dependency_overrides[get_current_user] = lambda: requester

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/unarchive")
        assert resp.status_code == 403

    def test_archived_tag_not_assignable(self, tags_db, tags_client):
        inst = make_institution(tags_db, "ar3")
        user = make_user(tags_db, inst.id, "ar3")
        tag = make_tag(tags_db, inst.id, "archived_assign_test")
        tag.is_archived = True
        q = make_question(tags_db, inst.id, user.id)
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            f"/api/v1/questions/{q.id}/tags",
            json={"tag_ids": [tag.id]},
        )
        assert resp.status_code == 422


class TestRenameTag:
    def test_rename_tag_success(self, tags_db, tags_client):
        inst = make_institution(tags_db, "rn1")
        user = make_user(tags_db, inst.id, "rn1")
        tag = make_tag(tags_db, inst.id, "altername")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.patch(f"/api/v1/tags/{tag.id}", json={"name": "Neuer Name"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Neuer Name"

    def test_rename_to_existing_name_returns_409(self, tags_db, tags_client):
        inst = make_institution(tags_db, "rn2")
        user = make_user(tags_db, inst.id, "rn2")
        make_tag(tags_db, inst.id, "existing")
        tag = make_tag(tags_db, inst.id, "toberenamed")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.patch(f"/api/v1/tags/{tag.id}", json={"name": "existing"})
        assert resp.status_code == 409


class TestMergeTags:
    def test_merge_archives_sources_and_migrates_questions(self, tags_db, tags_client):
        inst = make_institution(tags_db, "mg1")
        user = make_user(tags_db, inst.id, "mg1")
        source1 = make_tag(tags_db, inst.id, "source1mg")
        source2 = make_tag(tags_db, inst.id, "source2mg")
        target = make_tag(tags_db, inst.id, "targetmg")
        q1 = make_question(tags_db, inst.id, user.id)
        q2 = make_question(tags_db, inst.id, user.id)
        tags_db.add(QuestionTag(question_id=q1.id, tag_id=source1.id))
        tags_db.add(QuestionTag(question_id=q2.id, tag_id=source2.id))
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            "/api/v1/tags/merge",
            json={"source_ids": [source1.id, source2.id], "target_id": target.id},
        )
        assert resp.status_code == 200

        tags_db.refresh(source1)
        tags_db.refresh(source2)
        assert source1.is_archived is True
        assert source2.is_archived is True

        target_qt_count = (
            tags_db.query(QuestionTag).filter(QuestionTag.tag_id == target.id).count()
        )
        assert target_qt_count == 2

        logs = (
            tags_db.query(TagMergeLog)
            .filter(TagMergeLog.target_tag_id == target.id)
            .all()
        )
        assert len(logs) == 2
        assert sum(lg.questions_migrated for lg in logs) == 2
        # Both source_tag_ids are present individually in the audit trail
        assert {lg.source_tag_id for lg in logs} == {source1.id, source2.id}

    def test_merge_with_target_as_source_returns_422(self, tags_db, tags_client):
        inst = make_institution(tags_db, "mg2")
        user = make_user(tags_db, inst.id, "mg2")
        tag = make_tag(tags_db, inst.id, "self_merge_test")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            "/api/v1/tags/merge",
            json={"source_ids": [tag.id], "target_id": tag.id},
        )
        assert resp.status_code == 422


class TestUsageCount:
    def test_usage_count_incremented_on_assignment(self, tags_db, tags_client):
        inst = make_institution(tags_db, "uc1")
        user = make_user(tags_db, inst.id, "uc1")
        tag = make_tag(tags_db, inst.id, "counttest")
        q = make_question(tags_db, inst.id, user.id)
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        tags_client.post(f"/api/v1/questions/{q.id}/tags", json={"tag_ids": [tag.id]})
        # usage_count is computed live from QuestionTag — queried via the API
        resp = tags_client.get("/api/v1/tags")
        found = next(t for t in resp.json() if t["id"] == tag.id)
        assert found["usage_count"] == 1

    def test_usage_count_decremented_on_removal(self, tags_db, tags_client):
        inst = make_institution(tags_db, "uc2")
        user = make_user(tags_db, inst.id, "uc2")
        tag = make_tag(tags_db, inst.id, "decrementtest")
        q = make_question(tags_db, inst.id, user.id)
        tags_db.add(QuestionTag(question_id=q.id, tag_id=tag.id))
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        tags_client.delete(f"/api/v1/questions/{q.id}/tags/{tag.id}")
        resp = tags_client.get("/api/v1/tags")
        found = next(t for t in resp.json() if t["id"] == tag.id)
        assert found["usage_count"] == 0


class TestIsOwnField:
    def test_list_tags_returns_is_own_true_for_creator(self, tags_db, tags_client):
        inst = make_institution(tags_db, "own1")
        user = make_user(tags_db, inst.id, "own1")
        tag = make_tag(tags_db, inst.id, "eigener-tag")
        tag.created_by = user.id
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        found = next(t for t in resp.json() if t["name"] == "eigener-tag")
        assert found["is_own"] is True

    def test_list_tags_returns_is_own_false_for_other_user(self, tags_db, tags_client):
        inst = make_institution(tags_db, "own2")
        creator = make_user(tags_db, inst.id, "own2a")
        other = make_user(tags_db, inst.id, "own2b")
        tag = make_tag(tags_db, inst.id, "fremder-tag")
        tag.created_by = creator.id
        tags_db.commit()

        other.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: other

        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        found = next(t for t in resp.json() if t["name"] == "fremder-tag")
        assert found["is_own"] is False


class TestOwnTagPermissions:
    def test_non_admin_can_rename_own_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "perm1")
        user = make_user(tags_db, inst.id, "perm1")
        tag = make_tag(tags_db, inst.id, "umbenenn-mich")
        tag.created_by = user.id
        tags_db.commit()

        user.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.patch(f"/api/v1/tags/{tag.id}", json={"name": "umbenannt"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "umbenannt"

    def test_non_admin_cannot_rename_foreign_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "perm2")
        creator = make_user(tags_db, inst.id, "perm2a")
        other = make_user(tags_db, inst.id, "perm2b")
        tag = make_tag(tags_db, inst.id, "fremder-tag-rename")
        tag.created_by = creator.id
        tags_db.commit()

        other.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: other

        resp = tags_client.patch(f"/api/v1/tags/{tag.id}", json={"name": "gehackt"})
        assert resp.status_code == 403

    def test_non_admin_can_archive_own_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "perm3")
        user = make_user(tags_db, inst.id, "perm3")
        tag = make_tag(tags_db, inst.id, "archivier-mich")
        tag.created_by = user.id
        tags_db.commit()

        user.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/archive")
        assert resp.status_code == 200
        assert resp.json()["is_archived"] is True

    def test_non_admin_cannot_archive_foreign_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "perm4")
        creator = make_user(tags_db, inst.id, "perm4a")
        other = make_user(tags_db, inst.id, "perm4b")
        tag = make_tag(tags_db, inst.id, "fremder-archiv")
        tag.created_by = creator.id
        tags_db.commit()

        other.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: other

        resp = tags_client.post(f"/api/v1/tags/{tag.id}/archive")
        assert resp.status_code == 403


class TestDeleteTag:
    def test_admin_can_delete_archived_tag_with_no_usage(self, tags_db, tags_client):
        inst = make_institution(tags_db, "del1")
        user = make_user(tags_db, inst.id, "del1")
        tag = make_tag(tags_db, inst.id, "loeschbar")
        tag.is_archived = True
        tag.usage_count = 0
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 204
        assert tags_db.query(Tag).filter(Tag.id == tag.id).first() is None

    def test_cannot_delete_tag_with_usage(self, tags_db, tags_client):
        inst = make_institution(tags_db, "del2")
        user = make_user(tags_db, inst.id, "del2")
        tag = make_tag(tags_db, inst.id, "in-use")
        tag.is_archived = True
        question = make_question(tags_db, inst.id, user.id)
        tags_db.flush()
        tags_db.add(QuestionTag(question_id=question.id, tag_id=tag.id))
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 422

    def test_cannot_delete_active_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "del3")
        user = make_user(tags_db, inst.id, "del3")
        tag = make_tag(tags_db, inst.id, "aktiv-tag")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 422

    def test_non_admin_can_delete_own_archived_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "del4")
        user = make_user(tags_db, inst.id, "del4")
        tag = make_tag(tags_db, inst.id, "eigener-loeschbar")
        tag.created_by = user.id
        tag.is_archived = True
        tag.usage_count = 0
        tags_db.commit()

        user.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 204

    def test_non_admin_cannot_delete_foreign_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "del5")
        creator = make_user(tags_db, inst.id, "del5a")
        other = make_user(tags_db, inst.id, "del5b")
        tag = make_tag(tags_db, inst.id, "fremder-loeschbar")
        tag.created_by = creator.id
        tag.is_archived = True
        tag.usage_count = 0
        tags_db.commit()

        other.has_permission = Mock(side_effect=lambda p: p == "create_questions")
        tags_client.app.dependency_overrides[get_current_user] = lambda: other

        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 403


class TestCaseInsensitivity:
    def test_create_tag_case_insensitive_returns_same_id(self, tags_db, tags_client):
        """POST 'Python' followed by 'PYTHON' returns the same tag (case-insensitive, case-preserving)."""
        inst = make_institution(tags_db, "ci1")
        user = make_user(tags_db, inst.id, "ci1")
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        first = tags_client.post("/api/v1/tags", json={"name": "Python"})
        second = tags_client.post("/api/v1/tags", json={"name": "PYTHON"})

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]
        # Original casing of the FIRST entry is preserved
        assert first.json()["name"] == "Python"
        assert second.json()["name"] == "Python"


class TestGlobalTagPermissions:
    def test_non_superuser_cannot_create_global_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "gp1")
        user = make_user(tags_db, inst.id, "gp1")
        user.is_superuser = False
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            "/api/v1/tags",
            json={"name": "globaler-tag-nogo", "scope": "global"},
        )
        assert resp.status_code == 403

    def test_superuser_can_create_global_tag(self, tags_db, tags_client):
        inst = make_institution(tags_db, "gp2")
        user = make_user(tags_db, inst.id, "gp2")
        user.is_superuser = True
        tags_db.commit()

        user.has_permission = Mock(return_value=True)
        tags_client.app.dependency_overrides[get_current_user] = lambda: user

        resp = tags_client.post(
            "/api/v1/tags",
            json={"name": "globaler-tag-ok", "scope": "global"},
        )
        assert resp.status_code == 200
        assert resp.json()["scope"] == "global"
        assert resp.json()["institution_id"] is None
