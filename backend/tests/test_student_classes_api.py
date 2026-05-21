"""API tests for /api/v1/student-classes/* (TF-336 Subarea A).

Covers CRUD, member management, multi-tenancy, and idempotent
class-name conflicts.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.student import Student, StudentClass, StudentClassMembership
from utils.auth_utils import get_current_user, get_current_active_user


def _make_institution(db: Session, slug: str = "tf336-classes") -> Institution:
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


def _make_user(
    db: Session,
    institution_id: int,
    *,
    email: str = "admin@test.ch",
    is_superuser: bool = True,
) -> User:
    user = User(
        email=email,
        first_name="Test",
        last_name="Admin",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def _make_student(
    db: Session,
    institution_id: int,
    *,
    external_id: str,
    display_name: str | None = None,
) -> Student:
    student = Student(
        institution_id=institution_id,
        external_id=external_id,
        display_name=display_name,
    )
    db.add(student)
    db.flush()
    return student


def _client(test_db: Session, user: User) -> TestClient:
    import api.student_classes as student_classes_module

    if student_classes_module.router not in app.router.routes:
        app.include_router(student_classes_module.router)

    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_and_list_classes(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "INF-23a"
    assert body["member_count"] == 0

    listing = client.get("/api/v1/student-classes")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "INF-23a"


def test_create_class_rejects_duplicate_name_in_institution(
    test_db: Session,
) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    first = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    assert first.status_code == 201
    dup = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    assert dup.status_code == 409


def test_create_class_strips_whitespace(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post("/api/v1/student-classes", json={"name": "  INF-23a "})
    assert resp.status_code == 201
    assert resp.json()["name"] == "INF-23a"


def test_create_class_rejects_empty_name(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    resp = client.post("/api/v1/student-classes", json={"name": ""})
    assert resp.status_code == 422


def test_update_class_rename(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    class_id = created.json()["id"]

    resp = client.patch(f"/api/v1/student-classes/{class_id}", json={"name": "INF-23b"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "INF-23b"


def test_delete_class_cascades_memberships(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    test_db.commit()
    client = _client(test_db, user)

    created = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    class_id = created.json()["id"]
    add = client.post(
        f"/api/v1/student-classes/{class_id}/members",
        json={"student_id": student.id},
    )
    assert add.status_code == 201

    resp = client.delete(f"/api/v1/student-classes/{class_id}")
    assert resp.status_code == 204

    # Student survives the cascade; only the membership is gone.
    assert (
        test_db.query(Student).filter(Student.id == student.id).one_or_none()
        is not None
    )
    assert (
        test_db.query(StudentClassMembership)
        .filter(StudentClassMembership.class_id == class_id)
        .count()
        == 0
    )


# ---------------------------------------------------------------------------
# Members
# ---------------------------------------------------------------------------


def test_add_and_remove_member(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    student = _make_student(
        test_db, inst.id, external_id="anna@example.org", display_name="Anna B."
    )
    test_db.commit()
    client = _client(test_db, user)

    created = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    class_id = created.json()["id"]

    add = client.post(
        f"/api/v1/student-classes/{class_id}/members",
        json={"student_id": student.id},
    )
    assert add.status_code == 201
    assert add.json()["external_id"] == "anna@example.org"

    detail = client.get(f"/api/v1/student-classes/{class_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["member_count"] == 1
    assert payload["members"][0]["external_id"] == "anna@example.org"

    remove = client.delete(f"/api/v1/student-classes/{class_id}/members/{student.id}")
    assert remove.status_code == 204

    detail2 = client.get(f"/api/v1/student-classes/{class_id}")
    assert detail2.json()["member_count"] == 0


def test_add_duplicate_member_returns_conflict(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    student = _make_student(test_db, inst.id, external_id="anna@example.org")
    test_db.commit()
    client = _client(test_db, user)

    created = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    class_id = created.json()["id"]
    first = client.post(
        f"/api/v1/student-classes/{class_id}/members",
        json={"student_id": student.id},
    )
    assert first.status_code == 201
    dup = client.post(
        f"/api/v1/student-classes/{class_id}/members",
        json={"student_id": student.id},
    )
    assert dup.status_code == 409


def test_remove_unknown_member_returns_404(test_db: Session) -> None:
    inst = _make_institution(test_db)
    user = _make_user(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    created = client.post("/api/v1/student-classes", json={"name": "INF-23a"})
    class_id = created.json()["id"]
    resp = client.delete(f"/api/v1/student-classes/{class_id}/members/9999")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Multi-Tenancy
# ---------------------------------------------------------------------------


def test_multi_tenancy_get_returns_404_for_other_institution(
    test_db: Session,
) -> None:
    inst_a = _make_institution(test_db, slug="tf336-classes-a")
    inst_b = _make_institution(test_db, slug="tf336-classes-b")
    user_b = _make_user(test_db, inst_b.id, email="userb@test.ch")

    foreign_class = StudentClass(institution_id=inst_a.id, name="Geheim")
    test_db.add(foreign_class)
    test_db.commit()

    client = _client(test_db, user_b)
    resp = client.get(f"/api/v1/student-classes/{foreign_class.id}")
    assert resp.status_code == 404


def test_multi_tenancy_member_add_uses_user_institution(
    test_db: Session,
) -> None:
    inst_a = _make_institution(test_db, slug="tf336-classes-a2")
    inst_b = _make_institution(test_db, slug="tf336-classes-b2")
    user_a = _make_user(test_db, inst_a.id, email="usera@test.ch")
    foreign_student = _make_student(
        test_db, inst_b.id, external_id="foreign@example.org"
    )
    test_db.commit()

    client = _client(test_db, user_a)
    created = client.post("/api/v1/student-classes", json={"name": "Klasse A"})
    class_id = created.json()["id"]

    # Ein Studi aus Institution B darf nicht in Klasse A eingeordnet werden.
    resp = client.post(
        f"/api/v1/student-classes/{class_id}/members",
        json={"student_id": foreign_student.id},
    )
    assert resp.status_code == 404
