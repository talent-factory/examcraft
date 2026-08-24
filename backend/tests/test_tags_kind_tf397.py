"""TF-397: Tests for the `kind` dimension of the Tags API.

Covers:
- `kind` filter on GET /api/v1/tags (default 'content' excludes prompt tags).
- Uniqueness per (scope, kind, lower(name)) — a 'content' tag and a
  'prompt' tag with the same name can coexist.
- Relaxed RBAC: 'prompt' tags need 'prompt:create' instead of superuser; the
  existing superuser requirement for global 'content' tags remains in place.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func
from sqlalchemy.orm import Session
from unittest.mock import Mock

from main import app
from models.auth import Institution, User, UserStatus
from models.tag import Tag
from utils.tag_normalize import normalize_prompt_tag_name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_user(
    institution_id: int,
    user_id: int,
    *,
    is_superuser: bool = False,
    permissions: tuple = (),
) -> Mock:
    """Mock user with explicitly controlled is_superuser and permission set."""
    user = Mock()
    user.id = user_id
    user.institution_id = institution_id
    user.is_superuser = is_superuser
    perms = set(permissions)
    user.has_permission = Mock(side_effect=lambda p: is_superuser or p in perms)
    user.status = UserStatus.ACTIVE.value
    user.roles = []
    return user


def make_institution(db: Session, suffix: str) -> Institution:
    inst = Institution(
        name=f"Kind Uni {suffix}",
        slug=f"kind-uni-{suffix}",
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
        email=f"kinduser{suffix}@test.com",
        first_name="Kind",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_tag(
    db: Session,
    name: str,
    *,
    scope: str = "global",
    kind: str = "content",
    institution_id=None,
) -> Tag:
    tag = Tag(name=name, scope=scope, kind=kind, institution_id=institution_id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


# ---------------------------------------------------------------------------
# Fixtures (mirror test_tags_api.py)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tags_db(test_engine):
    """Committable session that cleans up every Tag row it created.

    These tests intentionally create *global* tags (committed), which are
    visible across institutions. Without cleanup they would leak into the
    shared session-scoped engine and break other test modules' invariants
    (e.g. "new institution sees no tags"). We snapshot the max tag id at
    setup and delete anything created during the test on teardown.
    """
    from sqlalchemy.orm import sessionmaker

    TestSession = sessionmaker(bind=test_engine)
    session = TestSession()
    max_id_before = session.query(func.max(Tag.id)).scalar() or 0
    yield session
    session.rollback()
    session.query(Tag).filter(Tag.id > max_id_before).delete(synchronize_session=False)
    session.commit()
    session.close()


@pytest.fixture()
def tags_client(tags_db: Session):
    import api.tags as tags_module
    from database import get_db

    app.include_router(tags_module.router)

    def override_get_db():
        yield tags_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# normalization (mirrored by the tf397 migration backfill)
# ---------------------------------------------------------------------------


class TestNormalizePromptTagName:
    def test_collapses_separator_variants(self) -> None:
        assert normalize_prompt_tag_name("Single Choice") == "single_choice"
        assert normalize_prompt_tag_name("single-choice") == "single_choice"
        assert normalize_prompt_tag_name("single_choice") == "single_choice"
        assert normalize_prompt_tag_name("  Open   Ended ") == "open_ended"

    def test_empty_and_whitespace_only_yield_empty(self) -> None:
        # get_or_create_prompt_tags relies on "" being falsy to skip the tag.
        assert normalize_prompt_tag_name("") == ""
        assert normalize_prompt_tag_name("   ") == ""

    def test_pure_separators_collapse_to_single_underscore(self) -> None:
        # Documents the actual (non-empty) result: a separator-only name is NOT
        # skipped — it normalizes to "_". Mirrors the SQL backfill, which only
        # btrims whitespace before collapsing [-\s]+ to "_".
        assert normalize_prompt_tag_name("---") == "_"
        assert normalize_prompt_tag_name(" - - ") == "_"

    def test_case_folding(self) -> None:
        assert normalize_prompt_tag_name("DEFAULT") == "default"
        assert normalize_prompt_tag_name("MixedCase") == "mixedcase"

    def test_unicode_is_lowercased(self) -> None:
        assert normalize_prompt_tag_name("Çà") == "çà"


# ---------------------------------------------------------------------------
# kind filter
# ---------------------------------------------------------------------------


class TestKindFilter:
    def test_default_kind_excludes_prompt_tags(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "kf1")
        user_db = make_user(tags_db, inst.id, "kf1")
        make_tag(tags_db, "content-kf1", scope="global", kind="content")
        make_tag(tags_db, "prompt-kf1", scope="global", kind="prompt")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id
        )

        # Default → content only
        resp = tags_client.get("/api/v1/tags")
        assert resp.status_code == 200
        names = [t["name"] for t in resp.json()]
        assert "content-kf1" in names
        assert "prompt-kf1" not in names

    def test_kind_prompt_returns_prompt_tags_only(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "kf2")
        user_db = make_user(tags_db, inst.id, "kf2")
        make_tag(tags_db, "content-kf2", scope="global", kind="content")
        make_tag(tags_db, "prompt-kf2", scope="global", kind="prompt")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id
        )

        resp = tags_client.get("/api/v1/tags", params={"kind": "prompt"})
        assert resp.status_code == 200
        payload = resp.json()
        names = [t["name"] for t in payload]
        # only prompt-kind visible; other tests create additional prompt tags,
        # so check specifically rather than comparing the whole list for equality.
        assert "prompt-kf2" in names
        assert "content-kf2" not in names
        assert all(t["kind"] == "prompt" for t in payload)


# ---------------------------------------------------------------------------
# uniqueness per (scope, kind, lower(name))
# ---------------------------------------------------------------------------


class TestKindUniqueness:
    def test_content_and_prompt_same_name_coexist(self, tags_db: Session) -> None:
        """A global 'content' `default` and a global 'prompt' `default`
        may coexist (namespace separation via kind)."""
        make_tag(tags_db, "coexist-default", scope="global", kind="content")
        make_tag(tags_db, "coexist-default", scope="global", kind="prompt")

        rows = (
            tags_db.query(Tag)
            .filter(Tag.scope == "global", Tag.name == "coexist-default")
            .all()
        )
        kinds = sorted(r.kind for r in rows)
        assert kinds == ["content", "prompt"]


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------


class TestPromptTagRBAC:
    def test_prompt_tag_create_allowed_with_prompt_create_permission(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        """A non-superuser with 'prompt:create' may create a global prompt tag."""
        inst = make_institution(tags_db, "rbac1")
        user_db = make_user(tags_db, inst.id, "rbac1")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=False, permissions=("prompt:create",)
        )

        resp = tags_client.post(
            "/api/v1/tags",
            json={"name": "single_choice", "scope": "global", "kind": "prompt"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["kind"] == "prompt"
        assert data["scope"] == "global"

    def test_prompt_tag_create_denied_without_prompt_create_permission(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "rbac2")
        user_db = make_user(tags_db, inst.id, "rbac2")

        from utils.auth_utils import get_current_user

        # User has create_questions, but NOT prompt:create.
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=False, permissions=("create_questions",)
        )

        resp = tags_client.post(
            "/api/v1/tags",
            json={"name": "blocked", "scope": "global", "kind": "prompt"},
        )
        assert resp.status_code == 403

    def test_content_global_tag_still_requires_superuser(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        """Existing rule unchanged: global content tags require superuser only."""
        inst = make_institution(tags_db, "rbac3")
        user_db = make_user(tags_db, inst.id, "rbac3")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=False, permissions=("create_questions",)
        )

        resp = tags_client.post(
            "/api/v1/tags",
            json={"name": "global-content", "scope": "global", "kind": "content"},
        )
        assert resp.status_code == 403


class TestPromptTagWriteRBAC:
    """TF-397: delete is blocked for prompt tags (premium prompt_tags can't be
    inspected from core); the creator may manage their own global prompt tags."""

    def test_delete_prompt_tag_blocked(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "del1")
        user_db = make_user(tags_db, inst.id, "del1")
        tag = make_tag(tags_db, "delete-me-prompt", scope="global", kind="prompt")

        from utils.auth_utils import get_current_user

        # Even a superuser is blocked — core cannot check prompt_tags usage.
        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=True
        )
        resp = tags_client.delete(f"/api/v1/tags/{tag.id}")
        assert resp.status_code == 422

    def test_creator_can_archive_own_global_prompt_tag(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "arc1")
        user_db = make_user(tags_db, inst.id, "arc1")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=False, permissions=("prompt:create",)
        )
        created = tags_client.post(
            "/api/v1/tags",
            json={"name": "own-prompt-tag", "scope": "global", "kind": "prompt"},
        )
        assert created.status_code == 200, created.text
        tag_id = created.json()["id"]

        resp = tags_client.post(f"/api/v1/tags/{tag_id}/archive")
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_archived"] is True

    def test_non_creator_cannot_archive_global_prompt_tag(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "arc2")
        other = make_user(tags_db, inst.id, "arc2other")
        # created_by is None → not the actor → no creator exception applies.
        tag = make_tag(tags_db, "someone-elses-prompt", scope="global", kind="prompt")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, other.id, is_superuser=False, permissions=("prompt:create",)
        )
        resp = tags_client.post(f"/api/v1/tags/{tag.id}/archive")
        assert resp.status_code == 403


class TestRenameKindAwareness:
    """TF-397: rename's duplicate pre-check is scoped by kind, so a name held
    only by a different-kind tag in the same scope is not a false conflict."""

    def test_rename_prompt_tag_onto_content_name_no_false_409(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "ren1")
        user_db = make_user(tags_db, inst.id, "ren1")
        # A *content* tag already holds the target name in the global scope.
        make_tag(tags_db, "shared_label", scope="global", kind="content")
        prompt_tag = make_tag(tags_db, "orig_prompt", scope="global", kind="prompt")

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=True
        )
        resp = tags_client.patch(
            f"/api/v1/tags/{prompt_tag.id}", json={"name": "shared_label"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["name"] == "shared_label"
        assert resp.json()["kind"] == "prompt"


class TestMergeKindGuard:
    """TF-397: merge only reassigns QuestionTag links and can't migrate the
    premium prompt_tags join, so prompt-kind tags are blocked from merge."""

    def test_merge_blocks_prompt_kind(
        self, tags_db: Session, tags_client: TestClient
    ) -> None:
        inst = make_institution(tags_db, "mrg1")
        user_db = make_user(tags_db, inst.id, "mrg1")
        target = make_tag(tags_db, "merge_target", scope="global", kind="content")
        prompt_source = make_tag(
            tags_db, "merge_prompt_src", scope="global", kind="prompt"
        )

        from utils.auth_utils import get_current_user

        app.dependency_overrides[get_current_user] = lambda: _make_mock_user(
            inst.id, user_db.id, is_superuser=True
        )
        resp = tags_client.post(
            "/api/v1/tags/merge",
            json={"target_id": target.id, "source_ids": [prompt_source.id]},
        )
        assert resp.status_code == 422, resp.text
