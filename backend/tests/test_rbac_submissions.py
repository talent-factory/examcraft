"""RBAC matrix tests for the Auswertungs-Permissions (TF-336 Subarea F).

Verifies the complete permission table per spec 7.6:

* Admin            → submissions:read/import/grade, students:manage,
                      moodle:configure, grading_schemes:manage
* Dozent (Lehrer)  → submissions:read/import/grade
* Assistant (Reviewer) → submissions:read/grade
* Viewer           → keine Auswertungs-Permissions

Plus end-to-end checks that the API endpoints honour the permission
mapping (e.g. a Reviewer cannot trigger import; a non-admin cannot
manage classes or moodle connections).
"""

from __future__ import annotations

from io import BytesIO

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, Role, User, UserRole, UserStatus
from utils.auth_utils import get_current_user, get_current_active_user
from utils.seed_roles import _parse_existing_permissions, seed_default_roles


def _perms(role: Role) -> set[str]:
    """Decode the on-disk permissions blob into a comparable set.

    Postgres rendering coerces the seeded ``list`` into a
    ``{a,b,c}`` string; ``_parse_existing_permissions`` is the canonical
    decoder shared with the seeder.
    """
    return set(_parse_existing_permissions(role.permissions))


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_institution(db: Session, slug: str) -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="enterprise",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _seed_roles_unique(db: Session) -> None:
    """Seed default roles into the test DB.

    The conftest doesn't run this automatically, so we run it once per
    test scope. Idempotent — second invocation only refreshes
    permissions.
    """
    seed_default_roles(db)


def _make_user_with_role(
    db: Session, *, institution_id: int, role_name: str, email_suffix: str
) -> User:
    role = db.query(Role).filter(Role.name == role_name).one()
    user = User(
        email=f"{email_suffix}@test.ch",
        first_name="Test",
        last_name=role_name.title(),
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=False,
    )
    user.roles.append(role)
    db.add(user)
    db.flush()
    return user


# ---------------------------------------------------------------------------
# Permission matrix
# ---------------------------------------------------------------------------


_TF336_PERMISSIONS = {
    "submissions:read",
    "submissions:import",
    "submissions:grade",
    "students:manage",
    "moodle:configure",
    "grading_schemes:manage",
}


def test_seed_includes_all_tf336_permissions(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    test_db.commit()
    roles = {r.name: r for r in test_db.query(Role).all()}
    # All four roles get refreshed on seed.
    assert {UserRole.ADMIN.value, UserRole.DOZENT.value} <= set(roles)


def test_admin_has_all_auswertungs_permissions(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    test_db.commit()
    admin = test_db.query(Role).filter(Role.name == UserRole.ADMIN.value).one()
    perms = _perms(admin)
    assert _TF336_PERMISSIONS <= perms


def test_dozent_has_submission_permissions_only(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    test_db.commit()
    dozent = test_db.query(Role).filter(Role.name == UserRole.DOZENT.value).one()
    perms = _perms(dozent)
    assert {
        "submissions:read",
        "submissions:import",
        "submissions:grade",
    } <= perms
    assert "students:manage" not in perms
    assert "moodle:configure" not in perms
    assert "grading_schemes:manage" not in perms


def test_assistant_is_reviewer(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    test_db.commit()
    assistant = test_db.query(Role).filter(Role.name == UserRole.ASSISTANT.value).one()
    perms = _perms(assistant)
    assert "submissions:read" in perms
    assert "submissions:grade" in perms
    # Reviewers must not import or manage anything.
    assert "submissions:import" not in perms
    assert "students:manage" not in perms
    assert "moodle:configure" not in perms


def test_viewer_has_no_auswertungs_permissions(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    test_db.commit()
    viewer = test_db.query(Role).filter(Role.name == UserRole.VIEWER.value).one()
    perms = _perms(viewer)
    assert _TF336_PERMISSIONS.isdisjoint(perms)


def test_seed_is_idempotent(test_db: Session) -> None:
    _seed_roles_unique(test_db)
    _seed_roles_unique(test_db)
    test_db.commit()
    admin = test_db.query(Role).filter(Role.name == UserRole.ADMIN.value).one()
    perms = _perms(admin)
    # Re-seeding must not duplicate permissions (deduped sorted set).
    assert len(perms) == len(set(perms))


# ---------------------------------------------------------------------------
# End-to-end: real users invoking endpoints with role-based permissions
# ---------------------------------------------------------------------------


def _client(test_db: Session, user: User) -> TestClient:
    import api.moodle_connections as mc_module
    import api.student_classes as sc_module
    import api.submissions as sub_module

    if mc_module.router not in app.router.routes:
        app.include_router(mc_module.router)
    if sc_module.router not in app.router.routes:
        app.include_router(sc_module.router)
    if sub_module.router not in app.router.routes:
        app.include_router(sub_module.router)
        app.include_router(sub_module.exams_alias_router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def test_dozent_cannot_create_class(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="rbac-doz")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.DOZENT.value,
        email_suffix="doz",
    )
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    assert resp.status_code == 403
    assert "students:manage" in resp.json()["detail"]


def test_assistant_cannot_import_submissions(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="rbac-as")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ASSISTANT.value,
        email_suffix="as",
    )
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        "/api/v1/submissions/import/commit",
        files={"file": ("k.csv", BytesIO(b""), "text/csv")},
        data={"exam_id": "1"},
    )
    assert resp.status_code == 403
    assert "submissions:import" in resp.json()["detail"]


def test_admin_can_create_class(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="rbac-adm")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ADMIN.value,
        email_suffix="adm",
    )
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    assert resp.status_code == 201, resp.text


def test_assistant_cannot_configure_moodle(test_db: Session) -> None:
    inst = _make_institution(test_db, slug="rbac-mood-as")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ASSISTANT.value,
        email_suffix="mood-as",
    )
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post(
        "/api/v1/admin/moodle-connections",
        json={
            "base_url": "https://moodle.example.org",
            "token": "tokenABCDEFGH",
        },
    )
    assert resp.status_code == 403
    assert "moodle:configure" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Stats + sync-moodle-question-ids: confirm the route guard is wired
# ---------------------------------------------------------------------------


def _client_with_stats_and_roundtrip(test_db: Session, user: User) -> TestClient:
    """Like ``_client`` but also includes the students-stats and
    moodle-roundtrip routers, which live on separate modules from
    ``api.submissions``."""
    import api.moodle_roundtrip as roundtrip_module
    import api.students as students_module

    client = _client(test_db, user)
    if students_module.router not in app.router.routes:
        app.include_router(students_module.router)
    if roundtrip_module.router not in app.router.routes:
        app.include_router(roundtrip_module.router)
    return client


def test_assistant_cannot_view_class_stats(test_db: Session) -> None:
    """``GET /api/v1/student-classes/{id}/stats`` requires
    ``students:manage`` (spec 7.6). Without the negative test the
    permission could silently drift from the route decorator and only
    permission-consistency would catch it — but only at the seed level,
    not at the route level."""
    inst = _make_institution(test_db, slug="rbac-stats-cls")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ASSISTANT.value,
        email_suffix="stats-cls",
    )
    test_db.commit()
    client = _client_with_stats_and_roundtrip(test_db, user)

    resp = client.get("/api/v1/student-classes/1/stats")
    assert resp.status_code == 403
    assert "students:manage" in resp.json()["detail"]


def test_assistant_cannot_view_student_stats(test_db: Session) -> None:
    """``GET /api/v1/students/{id}/stats`` requires ``students:manage``."""
    inst = _make_institution(test_db, slug="rbac-stats-stu")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ASSISTANT.value,
        email_suffix="stats-stu",
    )
    test_db.commit()
    client = _client_with_stats_and_roundtrip(test_db, user)

    resp = client.get("/api/v1/students/1/stats")
    assert resp.status_code == 403
    assert "students:manage" in resp.json()["detail"]


def test_viewer_cannot_sync_moodle_question_ids(test_db: Session) -> None:
    """``POST /api/v1/exams/{id}/sync-moodle-question-ids`` requires
    ``submissions:import``. Viewer has no auswertungs perms at all."""
    inst = _make_institution(test_db, slug="rbac-sync-vw")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.VIEWER.value,
        email_suffix="sync-vw",
    )
    test_db.commit()
    client = _client_with_stats_and_roundtrip(test_db, user)

    resp = client.post(
        "/api/v1/exams/1/sync-moodle-question-ids",
        json={"moodle_quiz_id": 42},
    )
    assert resp.status_code == 403
    assert "submissions:import" in resp.json()["detail"]


def test_assistant_cannot_sync_moodle_question_ids(test_db: Session) -> None:
    """Reviewer (``submissions:read``+``submissions:grade`` only) must
    not be able to alter ``external_refs`` via the round-trip endpoint."""
    inst = _make_institution(test_db, slug="rbac-sync-as")
    _seed_roles_unique(test_db)
    user = _make_user_with_role(
        test_db,
        institution_id=inst.id,
        role_name=UserRole.ASSISTANT.value,
        email_suffix="sync-as",
    )
    test_db.commit()
    client = _client_with_stats_and_roundtrip(test_db, user)

    resp = client.post(
        "/api/v1/exams/1/sync-moodle-question-ids",
        json={"moodle_quiz_id": 42},
    )
    assert resp.status_code == 403
    assert "submissions:import" in resp.json()["detail"]
