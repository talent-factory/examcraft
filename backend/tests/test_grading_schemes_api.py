"""API tests for ``/api/v1/grading-schemes/*`` (TF-335).

Covers list, CRUD, RBAC (``grading_schemes:manage``), system-vs-
institution scoping, and the in-use guard on delete.

Pattern mirrors ``test_submissions_api.py``: a helper builds an
isolated institution + user per test, the TestClient overrides
``get_db``/``get_current_user``, and the test inspects HTTP responses
end-to-end against the real DB.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, Role, User, UserStatus
from models.exam import Exam
from models.grading_scheme import GradingScheme
from utils.auth_utils import get_current_user, get_current_active_user


@pytest.fixture(autouse=True)
def _clear_overrides_after_each_test():
    """Reset FastAPI dependency overrides so the rag_api / other test
    suites don't observe our test-scoped DB sessions or users.
    """
    yield
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Fixtures-Helper
# ---------------------------------------------------------------------------


def _make_institution(db: Session, slug: str = "tf335") -> Institution:
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


def _make_user_with_perms(
    db: Session,
    institution_id: int,
    *,
    permissions: list[str],
    email: str = "admin@test.ch",
    is_superuser: bool = False,
) -> User:
    role = Role(
        name=f"role_{email}",
        display_name="Test Role",
        permissions=permissions,
        is_system_role=False,
    )
    db.add(role)
    db.flush()

    user = User(
        email=email,
        first_name="Test",
        last_name="Admin",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


def _make_swiss_system_scheme(db: Session) -> GradingScheme:
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


def _client(test_db: Session, user: User) -> TestClient:
    """TestClient with DB and current-user overrides."""
    import api.grading_schemes as grading_schemes_module

    if grading_schemes_module.router not in app.router.routes:
        app.include_router(grading_schemes_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def _custom_config() -> dict:
    return {
        "type": "stepped",
        "steps": [
            {"min_pct": 80, "grade_label": "Sehr gut", "is_passing": True},
            {"min_pct": 50, "grade_label": "Genügend", "is_passing": True},
            {"min_pct": 0, "grade_label": "Ungenügend", "is_passing": False},
        ],
    }


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


def test_list_returns_system_and_own_institution_schemes(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    swiss = _make_swiss_system_scheme(test_db)

    own = GradingScheme(
        institution_id=inst.id,
        name="Eigene Skala",
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
    test_db.add(own)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get("/api/v1/grading-schemes")
    assert response.status_code == 200, response.text

    schemes = response.json()["schemes"]
    ids = {s["id"] for s in schemes}
    assert swiss.id in ids
    assert own.id in ids
    # System schemes show is_system_scheme=True
    swiss_dict = next(s for s in schemes if s["id"] == swiss.id)
    assert swiss_dict["is_system_scheme"] is True
    assert swiss_dict["institution_id"] is None


def test_list_excludes_other_institution_schemes(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="tf335-a")
    inst_b = _make_institution(test_db, slug="tf335-b")
    user_a = _make_user_with_perms(
        test_db, inst_a.id, permissions=["grading_schemes:manage"], email="a@test.ch"
    )

    foreign = GradingScheme(
        institution_id=inst_b.id,
        name="Tenant B Custom",
        display_format="numeric",
        config={
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 0,
            "max_grade": 10,
        },
    )
    test_db.add(foreign)
    test_db.commit()

    client = _client(test_db, user_a)
    response = client.get("/api/v1/grading-schemes")
    assert response.status_code == 200
    ids = {s["id"] for s in response.json()["schemes"]}
    assert foreign.id not in ids


def test_list_include_system_false_only_returns_own(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    _make_swiss_system_scheme(test_db)
    test_db.commit()

    client = _client(test_db, user)
    response = client.get("/api/v1/grading-schemes?include_system=false")
    assert response.status_code == 200
    assert all(s["institution_id"] == inst.id for s in response.json()["schemes"])


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_persists_institution_scheme(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/grading-schemes",
        json={
            "name": "Custom Pass-Fail",
            "display_format": "pass_fail",
            "config": _custom_config(),
            "is_default_for_institution": False,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["institution_id"] == inst.id
    assert body["is_system_scheme"] is False
    assert body["name"] == "Custom Pass-Fail"


def test_create_rejects_invalid_config_with_422(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/grading-schemes",
        json={
            "name": "Broken",
            "display_format": "numeric",
            "config": {"type": "exponential"},
        },
    )
    assert response.status_code == 422


def test_create_promote_to_default_demotes_previous(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    previous_default = GradingScheme(
        institution_id=inst.id,
        name="Previous Default",
        display_format="numeric",
        config=_custom_config(),
        is_default_for_institution=True,
    )
    test_db.add(previous_default)
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/grading-schemes",
        json={
            "name": "New Default",
            "display_format": "pass_fail",
            "config": _custom_config(),
            "is_default_for_institution": True,
        },
    )
    assert response.status_code == 201, response.text

    test_db.refresh(previous_default)
    assert previous_default.is_default_for_institution is False


def test_create_without_perm_returns_403(test_db: Session) -> None:
    inst = _make_institution(test_db)
    # User without grading_schemes:manage but with submissions:read
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["submissions:read"], email="reader@test.ch"
    )
    test_db.commit()

    client = _client(test_db, user)
    response = client.post(
        "/api/v1/grading-schemes",
        json={
            "name": "Unauthorized",
            "display_format": "numeric",
            "config": _custom_config(),
        },
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Update
# ---------------------------------------------------------------------------


def test_update_system_scheme_returns_403(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    swiss = _make_swiss_system_scheme(test_db)
    test_db.commit()

    client = _client(test_db, user)
    response = client.patch(
        f"/api/v1/grading-schemes/{swiss.id}",
        json={"name": "Hacked"},
    )
    assert response.status_code == 403


def test_update_own_institution_scheme_succeeds(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    own = GradingScheme(
        institution_id=inst.id,
        name="Original",
        display_format="numeric",
        config=_custom_config(),
    )
    test_db.add(own)
    test_db.commit()

    client = _client(test_db, user)
    response = client.patch(
        f"/api/v1/grading-schemes/{own.id}",
        json={"name": "Renamed"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == "Renamed"


def test_update_promote_to_default_demotes_previous(test_db: Session) -> None:
    """PATCH path counterpart to the existing CREATE test.

    The fix for the SQLAlchemy flush-order bug requires the demote to
    happen first; this test would catch a regression where the promote
    races and trips ``uq_grading_schemes_default_per_institution``.
    """
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    previous_default = GradingScheme(
        institution_id=inst.id,
        name="Previous Default",
        display_format="numeric",
        config=_custom_config(),
        is_default_for_institution=True,
    )
    new_candidate = GradingScheme(
        institution_id=inst.id,
        name="New Candidate",
        display_format="pass_fail",
        config=_custom_config(),
        is_default_for_institution=False,
    )
    test_db.add_all([previous_default, new_candidate])
    test_db.commit()

    client = _client(test_db, user)
    response = client.patch(
        f"/api/v1/grading-schemes/{new_candidate.id}",
        json={"is_default_for_institution": True},
    )
    assert response.status_code == 200, response.text

    test_db.refresh(previous_default)
    test_db.refresh(new_candidate)
    assert previous_default.is_default_for_institution is False
    assert new_candidate.is_default_for_institution is True


def test_update_cross_tenant_returns_404(test_db: Session) -> None:
    inst_a = _make_institution(test_db, slug="tf335-a")
    inst_b = _make_institution(test_db, slug="tf335-b")
    user_a = _make_user_with_perms(
        test_db, inst_a.id, permissions=["grading_schemes:manage"], email="a@test.ch"
    )
    foreign = GradingScheme(
        institution_id=inst_b.id,
        name="Foreign",
        display_format="numeric",
        config=_custom_config(),
    )
    test_db.add(foreign)
    test_db.commit()

    client = _client(test_db, user_a)
    response = client.patch(
        f"/api/v1/grading-schemes/{foreign.id}", json={"name": "Hacked"}
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


def test_delete_unused_scheme_succeeds(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    own = GradingScheme(
        institution_id=inst.id,
        name="To Delete",
        display_format="numeric",
        config=_custom_config(),
    )
    test_db.add(own)
    test_db.commit()
    scheme_id = own.id

    client = _client(test_db, user)
    response = client.delete(f"/api/v1/grading-schemes/{scheme_id}")
    assert response.status_code == 204
    assert (
        test_db.query(GradingScheme).filter(GradingScheme.id == scheme_id).one_or_none()
        is None
    )


def test_delete_in_use_scheme_returns_409(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    scheme = GradingScheme(
        institution_id=inst.id,
        name="In Use",
        display_format="numeric",
        config=_custom_config(),
    )
    test_db.add(scheme)
    test_db.flush()

    exam = Exam(
        title="Referenziert",
        passing_percentage=50.0,
        total_points=10.0,
        status="draft",
        language="de",
        institution_id=inst.id,
        grading_scheme_id=scheme.id,
    )
    test_db.add(exam)
    test_db.commit()

    client = _client(test_db, user)
    response = client.delete(f"/api/v1/grading-schemes/{scheme.id}")
    assert response.status_code == 409
    assert "referenziert" in response.json()["detail"].lower()


def test_delete_system_scheme_returns_403(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    swiss = _make_swiss_system_scheme(test_db)
    test_db.commit()

    client = _client(test_db, user)
    response = client.delete(f"/api/v1/grading-schemes/{swiss.id}")
    assert response.status_code == 403


def test_delete_institution_default_returns_409(test_db: Session) -> None:
    """A scheme set as institution-default is also held by ``Institution.
    default_grading_scheme_id`` — deleting it would silently strand the
    institution. The endpoint must surface a 409 with a useful message,
    not a 500 from the FK RESTRICT.
    """
    inst = _make_institution(test_db)
    user = _make_user_with_perms(
        test_db, inst.id, permissions=["grading_schemes:manage"]
    )
    scheme = GradingScheme(
        institution_id=inst.id,
        name="Inst Default",
        display_format="numeric",
        config=_custom_config(),
        is_default_for_institution=True,
    )
    test_db.add(scheme)
    test_db.flush()
    inst.default_grading_scheme_id = scheme.id
    test_db.commit()

    client = _client(test_db, user)
    response = client.delete(f"/api/v1/grading-schemes/{scheme.id}")
    assert response.status_code == 409
    assert "default" in response.json()["detail"].lower()
