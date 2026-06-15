"""API tests for the institution-default grading scheme (TF-431).

The Note-resolver (``services/grading_scheme_resolver.resolve_scheme_config``)
falls back to ``Institution.default_grading_scheme_id`` when an exam has no
explicit scheme. Until TF-431 that column had no API/UI and could only be set
via a raw DB write. These tests cover the admin PATCH/POST ``/institutions``
endpoints now exposing the field, including the validation that

* a system scheme (``institution_id IS NULL``) is always assignable,
* a scheme owned by a *different* institution is rejected with 422,
* an explicit ``null`` clears the default, and
* omitting the field leaves the existing default untouched.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.grading_scheme import GradingScheme
from utils.auth_utils import get_current_active_user, get_current_user


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _institution(db: Session, slug: str = "tf431") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _superuser(db: Session, institution_id: int, email: str = "su@tf431.ch") -> User:
    user = User(
        email=email,
        first_name="Su",
        last_name="Peruser",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
    )
    db.add(user)
    db.flush()
    return user


def _swiss_system_scheme(db: Session) -> GradingScheme:
    scheme = GradingScheme(
        institution_id=None,
        name="Swiss 1.0–6.0",
        display_format="numeric",
        config={
            "type": "linear_segments",
            "round_to": 0.1,
            "pass_grade_label": "4.0",
            "segments": [
                {"from_pct": 0, "to_pct": 50, "from_grade": 1.0, "to_grade": 4.0},
                {"from_pct": 50, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
            ],
        },
        is_default_for_institution=False,
    )
    db.add(scheme)
    db.flush()
    return scheme


def _institution_scheme(db: Session, institution_id: int) -> GradingScheme:
    scheme = GradingScheme(
        institution_id=institution_id,
        name="Fremd-Skala",
        display_format="pass_fail",
        config={
            "type": "stepped",
            "steps": [
                {"min_pct": 60, "grade_label": "Pass", "is_passing": True},
                {"min_pct": 0, "grade_label": "Fail", "is_passing": False},
            ],
        },
        is_default_for_institution=False,
    )
    db.add(scheme)
    db.flush()
    return scheme


def _client(db: Session, user: User) -> TestClient:
    # Core routers are only registered inside the FastAPI lifespan, which a
    # bare TestClient (no ``with``) does not trigger — mirror the pattern in
    # ``test_grading_schemes_api`` and include the admin router explicitly.
    import api.admin as admin_module

    if admin_module.router not in app.router.routes:
        app.include_router(admin_module.router)

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def test_update_sets_system_scheme_as_default(test_db: Session) -> None:
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    swiss = _swiss_system_scheme(test_db)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"default_grading_scheme_id": swiss.id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["default_grading_scheme_id"] == swiss.id

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id == swiss.id


def test_update_clears_default_with_explicit_null(test_db: Session) -> None:
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    swiss = _swiss_system_scheme(test_db)
    inst.default_grading_scheme_id = swiss.id
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"default_grading_scheme_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["default_grading_scheme_id"] is None

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id is None


def test_update_rejects_other_institution_scheme(test_db: Session) -> None:
    inst = _institution(test_db, slug="tf431-a")
    other = _institution(test_db, slug="tf431-b")
    su = _superuser(test_db, inst.id)
    foreign = _institution_scheme(test_db, other.id)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"default_grading_scheme_id": foreign.id},
    )
    assert resp.status_code == 422, resp.text

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id is None


def test_update_omitting_field_leaves_default_unchanged(test_db: Session) -> None:
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    swiss = _swiss_system_scheme(test_db)
    inst.default_grading_scheme_id = swiss.id
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"name": "Umbenannt"},
    )
    assert resp.status_code == 200, resp.text

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id == swiss.id


def test_create_with_system_default_scheme(test_db: Session) -> None:
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    swiss = _swiss_system_scheme(test_db)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.post(
        "/api/admin/institutions",
        json={
            "name": "Neu TF431",
            "domain": "neu-tf431.ch",
            "subscription_tier": "free",
            "default_grading_scheme_id": swiss.id,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["default_grading_scheme_id"] == swiss.id


def test_create_rejects_other_institution_scheme(test_db: Session) -> None:
    """A brand-new institution owns no schemes, so any institution-scoped id
    is invalid on create — pins the validate-before-write rule so the
    cross-tenant invariant can't regress if the validation order changes."""
    inst = _institution(test_db, slug="tf431-create-a")
    other = _institution(test_db, slug="tf431-create-b")
    su = _superuser(test_db, inst.id)
    foreign = _institution_scheme(test_db, other.id)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.post(
        "/api/admin/institutions",
        json={
            "name": "Neu Foreign TF431",
            "domain": "neu-foreign-tf431.ch",
            "subscription_tier": "free",
            "default_grading_scheme_id": foreign.id,
        },
    )
    assert resp.status_code == 422, resp.text

    # And no half-written institution leaked despite the rejection.
    leaked = (
        test_db.query(Institution)
        .filter(Institution.domain == "neu-foreign-tf431.ch")
        .one_or_none()
    )
    assert leaked is None


def test_update_accepts_own_institution_scheme(test_db: Session) -> None:
    """The positive institution-scoped path: an institution may use its OWN
    scheme as default (the ``== institution_id`` branch of the validator)."""
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    own = _institution_scheme(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"default_grading_scheme_id": own.id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["default_grading_scheme_id"] == own.id

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id == own.id


def test_update_rejects_nonexistent_scheme(test_db: Session) -> None:
    """A non-existent scheme id (stale client state, deleted scheme) is a
    clean 422, not a 500 — covers the ``scheme is None`` validator branch."""
    inst = _institution(test_db)
    su = _superuser(test_db, inst.id)
    test_db.commit()

    client = _client(test_db, su)
    resp = client.patch(
        f"/api/admin/institutions/{inst.id}",
        json={"default_grading_scheme_id": 999999},
    )
    assert resp.status_code == 422, resp.text

    test_db.refresh(inst)
    assert inst.default_grading_scheme_id is None
