# core/backend/tests/test_activity_api.py
"""Tests for the paginated activity endpoint.

Covers:
* Happy path with limit/offset.
* Pagination math (no overlap between pages, total stays stable,
  edges: limit=0/101, offset>total).
* scope=own restricts to current user; scope=institution widens but
  never crosses tenants and rejects users without an institution.
* Type filter (single + multi) and unknown-type → 422.
* Limit cap (200 → 422 from Pydantic ge/le).
* Action mapping for every entry of TYPE_TO_ACTION (round-trip).
* Empty result for a fresh user.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import AuditLog, Institution, User, UserStatus
from utils.auth_utils import get_current_active_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(test_db: Session, name: str) -> Institution:
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


def make_user(test_db: Session, institution_id: int, email: str) -> User:
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


def make_audit(
    test_db: Session,
    user_id: int,
    action: str,
    *,
    resource_id: str = "1",
    title_field: str = "title",
    title_value: str = "Eintrag",
) -> AuditLog:
    """Insert an AuditLog with the title-shaped JSON the activity endpoint
    expects.

    ``additional_data`` carries the title under whichever key is
    appropriate for the action — ``original_filename`` for documents,
    ``topic`` for questions, ``title`` for exams. The fixture uses a
    single ``title_field`` parameter so callers can be explicit.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type="test",
        resource_id=resource_id,
        status="success",
        additional_data=json.dumps({title_field: title_value}),
    )
    test_db.add(log)
    test_db.flush()
    return log


def make_activity_client(test_db: Session, user_id: int) -> TestClient:
    """TestClient with the activity router registered and DI overridden.

    Mirrors the pattern used in test_dashboard_api.py — register the
    router directly to skip the full lifespan, then override the auth
    + db dependencies. FastAPI deduplicates identical routes, so this
    is safe to call repeatedly across tests.
    """
    import api.activity as activity_module

    user = test_db.get(User, user_id)
    app.include_router(activity_module.router)
    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: test_db
    return TestClient(app, raise_server_exceptions=True)


@pytest.fixture
def activity_user(test_db: Session):
    inst = make_institution(test_db, "ActivityInst")
    user = make_user(test_db, inst.id, "act@test.ch")
    test_db.commit()
    return inst, user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActivityHappyPath:
    def test_empty_user_returns_zero(self, test_db: Session, activity_user):
        """Brand-new user without events → empty list, total=0."""
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity")
            assert resp.status_code == 200
            data = resp.json()
            assert data["items"] == []
            assert data["total"] == 0
            assert data["limit"] == 25
            assert data["offset"] == 0
        finally:
            app.dependency_overrides.clear()

    def test_pagination_no_overlap(self, test_db: Session, activity_user):
        """offset=0 vs offset=25 returns disjoint id sets, total stays."""
        _, user = activity_user
        for i in range(40):
            make_audit(
                test_db,
                user.id,
                "create_document",
                resource_id=str(i),
                title_field="original_filename",
                title_value=f"doc{i:02d}.pdf",
            )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            page1 = client.get("/api/v1/activity?limit=25&offset=0").json()
            page2 = client.get("/api/v1/activity?limit=25&offset=25").json()

            assert page1["total"] == 40
            assert page2["total"] == 40
            assert len(page1["items"]) == 25
            # Tail page brings just the remaining 15.
            assert len(page2["items"]) == 15

            ids1 = {item["id"] for item in page1["items"]}
            ids2 = {item["id"] for item in page2["items"]}
            assert ids1.isdisjoint(ids2)
        finally:
            app.dependency_overrides.clear()

    def test_sorted_desc_by_created_at(self, test_db: Session, activity_user):
        """Newest first — newer rows appear before older ones."""
        _, user = activity_user
        for i in range(5):
            make_audit(
                test_db,
                user.id,
                "create_exam",
                resource_id=str(i),
                title_field="title",
                title_value=f"Exam {i}",
            )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity").json()
            timestamps = [item["timestamp"] for item in data["items"]]
            assert timestamps == sorted(timestamps, reverse=True)
        finally:
            app.dependency_overrides.clear()


class TestActivityScope:
    def test_scope_own_isolates_users_in_same_institution(self, test_db: Session):
        """User A doesn't see User B's events even within the same tenant."""
        inst = make_institution(test_db, "SameInst")
        user_a = make_user(test_db, inst.id, "a@test.ch")
        user_b = make_user(test_db, inst.id, "b@test.ch")
        make_audit(
            test_db,
            user_b.id,
            "create_document",
            title_field="original_filename",
            title_value="b-only.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user_a.id)
        try:
            data = client.get("/api/v1/activity?scope=own").json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.clear()

    def test_scope_own_omits_actor_user_id(self, test_db: Session, activity_user):
        """scope=own must NOT ship actor_user_id over the wire — the
        caller already knows who they are. Pinning this so a regression
        flipping the include_actor flag surfaces in CI."""
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            "create_document",
            title_field="original_filename",
            title_value="own.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity?scope=own").json()
            assert data["total"] == 1
            assert data["items"][0]["actor_user_id"] is None
        finally:
            app.dependency_overrides.clear()

    def test_scope_institution_widens_within_tenant(self, test_db: Session):
        """User A sees User B's events when scope=institution."""
        inst = make_institution(test_db, "WidenInst")
        user_a = make_user(test_db, inst.id, "a@test.ch")
        user_b = make_user(test_db, inst.id, "b@test.ch")
        make_audit(
            test_db,
            user_b.id,
            "create_document",
            title_field="original_filename",
            title_value="from-b.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user_a.id)
        try:
            data = client.get("/api/v1/activity?scope=institution").json()
            assert data["total"] == 1
            assert data["items"][0]["title"] == "from-b.pdf"
            # Cross-user view exposes the actor id so the frontend can
            # show "von User #X".
            assert data["items"][0]["actor_user_id"] == user_b.id
        finally:
            app.dependency_overrides.clear()

    def test_scope_institution_never_leaks_other_tenants(self, test_db: Session):
        """Events from a foreign institution must not appear under any scope."""
        inst_a = make_institution(test_db, "TenantA")
        inst_b = make_institution(test_db, "TenantB")
        user_a = make_user(test_db, inst_a.id, "a@test.ch")
        user_b = make_user(test_db, inst_b.id, "b@test.ch")
        make_audit(
            test_db,
            user_b.id,
            "create_document",
            title_field="original_filename",
            title_value="leak.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user_a.id)
        try:
            data = client.get("/api/v1/activity?scope=institution").json()
            assert data["total"] == 0
            assert data["items"] == []
        finally:
            app.dependency_overrides.clear()

    def test_scope_institution_open_to_any_role(self, test_db: Session):
        """scope=institution is intentionally NOT RBAC-gated. Any
        authenticated user (including a freshly registered Lehrperson
        with no admin role) gets cross-user visibility within their
        institution. Pinning this so a future change adding a role gate
        surfaces in CI rather than silently breaking the dashboard.

        The role here is irrelevant — what matters is that the call
        returns 200, not 403.
        """
        inst = make_institution(test_db, "OpenScopeInst")
        viewer = make_user(test_db, inst.id, "viewer@open.ch")
        actor = make_user(test_db, inst.id, "actor@open.ch")
        make_audit(
            test_db,
            actor.id,
            "create_exam",
            title_field="title",
            title_value="visible-to-colleagues",
        )
        test_db.commit()

        client = make_activity_client(test_db, viewer.id)
        try:
            resp = client.get("/api/v1/activity?scope=institution")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert data["items"][0]["title"] == "visible-to-colleagues"
        finally:
            app.dependency_overrides.clear()

    def test_scope_institution_rejects_user_without_institution(self, test_db: Session):
        """Defence-in-depth: even though User.institution_id is NOT
        NULL today, a caller without an institution must not be able
        to widen the query — otherwise the JOIN would match every
        other unassigned user across tenants. Returns 403."""
        import api.activity as activity_module

        inst = make_institution(test_db, "GuardInst")
        user = make_user(test_db, inst.id, "guard@open.ch")
        test_db.commit()

        # Detach + mutate so autoflush during the route call doesn't
        # trip the NOT NULL constraint that we're defending around.
        test_db.expunge(user)
        user.institution_id = None  # type: ignore[assignment]

        app.include_router(activity_module.router)
        app.dependency_overrides[get_current_active_user] = lambda: user
        app.dependency_overrides[get_db] = lambda: test_db
        client = TestClient(app, raise_server_exceptions=True)
        try:
            resp = client.get("/api/v1/activity?scope=institution")
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.clear()


class TestActivityTypeFilter:
    def test_filter_single_type(self, test_db: Session, activity_user):
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            "create_document",
            title_field="original_filename",
            title_value="doc.pdf",
        )
        make_audit(
            test_db, user.id, "create_exam", title_field="title", title_value="Exam"
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity?types=document_uploaded").json()
            assert data["total"] == 1
            assert {item["type"] for item in data["items"]} == {"document_uploaded"}
        finally:
            app.dependency_overrides.clear()

    def test_filter_multiple_types(self, test_db: Session, activity_user):
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            "approve_question",
            title_field="topic",
            title_value="Mathe",
        )
        make_audit(
            test_db,
            user.id,
            "reject_question",
            title_field="topic",
            title_value="Physik",
        )
        make_audit(
            test_db, user.id, "create_exam", title_field="title", title_value="Exam"
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get(
                "/api/v1/activity?types=question_approved,question_rejected"
            ).json()
            assert data["total"] == 2
            types = {item["type"] for item in data["items"]}
            assert types == {"question_approved", "question_rejected"}
        finally:
            app.dependency_overrides.clear()

    def test_unknown_type_returns_422(self, test_db: Session, activity_user):
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity?types=does_not_exist")
            assert resp.status_code == 422
            body = resp.json()
            # FastAPI wraps the HTTPException's structured detail in `detail`.
            assert body["detail"]["unknown_types"] == ["does_not_exist"]
            assert "supported_types" in body["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_empty_types_csv_treated_as_no_filter(
        self, test_db: Session, activity_user
    ):
        """``?types=`` (empty value) is forgiving — same result as no filter."""
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            "create_document",
            title_field="original_filename",
            title_value="doc.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity?types=").json()
            assert data["total"] == 1
        finally:
            app.dependency_overrides.clear()


class TestActivityActionMapping:
    def test_create_question_maps_to_questions_generated(
        self, test_db: Session, activity_user
    ):
        """The audit row uses ``create_question``; the API exposes
        ``questions_generated``. Without this remap the activity
        endpoint and the dashboard widget would diverge from the
        frontend's ACTIVITY_ICONS keys."""
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            "create_question",
            resource_id="task-uuid-xyz",
            title_field="topic",
            title_value="RAG",
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity").json()
            assert data["total"] == 1
            assert data["items"][0]["type"] == "questions_generated"
            assert data["items"][0]["title"] == "RAG"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.parametrize(
        "activity_type, action, title_field, title_value",
        [
            ("document_uploaded", "create_document", "original_filename", "doc.pdf"),
            ("document_deleted", "delete_document", "original_filename", "gone.pdf"),
            ("questions_generated", "create_question", "topic", "RAG"),
            ("question_approved", "approve_question", "topic", "Mathe"),
            ("question_rejected", "reject_question", "topic", "Physik"),
            ("exam_created", "create_exam", "title", "Final"),
            ("exam_deleted", "delete_exam", "title", "Old Final"),
        ],
    )
    def test_every_action_round_trips(
        self,
        test_db: Session,
        activity_user,
        activity_type,
        action,
        title_field,
        title_value,
    ):
        """Round-trip for every TYPE_TO_ACTION entry: filtering by the
        activity-type returns the audit row written under the mapped
        action, with the title resolved from the right JSON key. A
        typo in the mapping or the title-keys table fails the test."""
        _, user = activity_user
        make_audit(
            test_db,
            user.id,
            action,
            title_field=title_field,
            title_value=title_value,
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get(f"/api/v1/activity?types={activity_type}").json()
            assert data["total"] == 1
            assert data["items"][0]["type"] == activity_type
            assert data["items"][0]["title"] == title_value
        finally:
            app.dependency_overrides.clear()


class TestActivityValidation:
    def test_limit_cap_returns_422(self, test_db: Session, activity_user):
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity?limit=200")
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_limit_one_over_max_returns_422(self, test_db: Session, activity_user):
        """Pin the upper bound exactly at 100 — limit=101 must 422."""
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity?limit=101")
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_limit_max_100_is_accepted(self, test_db: Session, activity_user):
        """The frontend exposes 100 in the page-size selector; pin that
        the upper bound stays at 100 so a Pydantic-tightening regression
        (e.g. le=50) doesn't 422 production traffic."""
        _, user = activity_user
        for i in range(150):
            make_audit(
                test_db,
                user.id,
                "create_document",
                resource_id=str(i),
                title_field="original_filename",
                title_value=f"doc{i:03d}.pdf",
            )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity?limit=100").json()
            assert data["total"] == 150
            assert len(data["items"]) == 100
            assert data["limit"] == 100
            assert data["has_more"] is True
        finally:
            app.dependency_overrides.clear()

    def test_limit_zero_returns_422(self, test_db: Session, activity_user):
        """Pin the lower bound: limit=0 must 422 (Pydantic ge=1)."""
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity?limit=0")
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_negative_offset_returns_422(self, test_db: Session, activity_user):
        _, user = activity_user
        client = make_activity_client(test_db, user.id)
        try:
            resp = client.get("/api/v1/activity?offset=-1")
            assert resp.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_offset_past_total_returns_empty_with_total_intact(
        self, test_db: Session, activity_user
    ):
        """offset > total → items=[] but total stays so the frontend
        can recover from a stale deep link instead of 500-ing."""
        _, user = activity_user
        for i in range(3):
            make_audit(
                test_db,
                user.id,
                "create_document",
                resource_id=str(i),
                title_field="original_filename",
                title_value=f"doc{i}.pdf",
            )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity?offset=99").json()
            assert data["total"] == 3
            assert data["items"] == []
            assert data["offset"] == 99
        finally:
            app.dependency_overrides.clear()

    def test_unsupported_action_excluded_from_implicit_filter(
        self, test_db: Session, activity_user
    ):
        """An audit row whose action isn't one of the 7 supported types
        (e.g. ``login``) must not leak through the no-filter path —
        the frontend would render it without an icon or label."""
        _, user = activity_user
        make_audit(
            test_db, user.id, "login", title_field="ip_address", title_value="127.0.0.1"
        )
        make_audit(
            test_db,
            user.id,
            "create_document",
            title_field="original_filename",
            title_value="doc.pdf",
        )
        test_db.commit()

        client = make_activity_client(test_db, user.id)
        try:
            data = client.get("/api/v1/activity").json()
            # Only the create_document row counts.
            assert data["total"] == 1
            assert data["items"][0]["type"] == "document_uploaded"
        finally:
            app.dependency_overrides.clear()
