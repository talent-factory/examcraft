"""TF-643: Tests für Exam-Sichtbarkeit (private/team/institution)
+ Institutions-Admin-Bypass (``exams:read_all``).

Scope-Grenze (siehe utils/exam_visibility.py Modul-Docstring +
/grilling-Entscheidungen TF-643): Sichtbarkeit gilt für Exam-Browsing
(``list_exams``/``get_exam``) UND — ohne den ``exams:read_all``-Bypass — für
jede Exam-Mutation (update/update-grading-scheme/delete/archive/restore/
add-questions/update-question/remove-question/reorder/auto-fill/finalize/
unfinalize/export), da diese alle über ``_get_exam_or_404`` laufen.
Deliberately NICHT für ``submissions:grade``/``submissions:read`` (bleibt
institutionsflach über ``api.submissions._load_exam_for_user``, ebenso
``api.stats``/``api.grades``/``api.grade_export``) und NICHT gekoppelt an
``ExamStatus`` — Sichtbarkeit gilt uniform über DRAFT/FINALIZED/EXPORTED.
Diese drei Punkte haben je einen expliziten Regressions-Test unten.

PR-#193-Review-Nachlese (fix-all): zusätzlich Tests für den
Institutions-Drift-Fix in der Creator-Branch von ``is_exam_visible_for``
(``require_same_institution``), den SuperUser-Team-Sichtbarkeits-Bugfix
(Create- UND Update-Pfad), zwei DB-CHECK-Constraint-Regressionstests, den
No-op-403-Fix in ``_resolve_exam_visibility_update`` und einen
parametrisierten Test über alle 13 mutierenden Endpunkte.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from main import app
from models.auth import Institution, User, UserStatus, Role
from models.exam import Exam, ExamVisibility
from models.org_unit import OrgUnit, UserOrgUnit
from services.org_unit_service import delete_org_unit
from utils.auth_utils import get_current_user, get_current_active_user
from utils.exam_visibility import filter_exams_for_user, is_exam_visible_for
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def ev_db(test_engine):
    Session_ = sessionmaker(bind=test_engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture()
def ev_client(ev_db: Session):
    import api.exams as exams_module

    app.include_router(exams_module.router)

    def override_get_db():
        yield ev_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix="ev"):
    inst = Institution(
        name=f"EV Uni {suffix}",
        slug=f"ev-uni-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def make_user(db, institution_id, suffix, is_superuser=False):
    user = User(
        email=f"evuser{suffix}@test.com",
        first_name="EV",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def make_user_with_role(db, institution_id, suffix, perms):
    """Non-Superuser mit einer Rolle, die genau ``perms`` trägt.

    Rollenname mit ``tf643-`` genamespaced — ``Role.name`` ist global unique
    (CI-Gotcha, siehe TF-640-Nachlese), Kollision mit anderen Testdateien
    vermeiden.
    """
    user = make_user(db, institution_id, suffix)
    role = Role(
        name=f"tf643-role-{suffix}",
        display_name=f"TF-643 Role {suffix}",
        permissions=json.dumps(perms),
    )
    db.add(role)
    db.flush()
    user.roles.append(role)
    db.flush()
    return user


def make_org_unit(db, institution_id, suffix="ou", parent_org_unit_id=None):
    ou = OrgUnit(
        institution_id=institution_id,
        unit_type="team",
        name=f"Team {suffix}",
        parent_org_unit_id=parent_org_unit_id,
    )
    db.add(ou)
    db.flush()
    return ou


def add_membership(db, user_id, org_unit_id):
    db.add(UserOrgUnit(user_id=user_id, org_unit_id=org_unit_id))
    db.flush()


def make_exam(
    db,
    institution_id,
    created_by=None,
    visibility=ExamVisibility.INSTITUTION,
    org_unit_id=None,
    status="draft",
    suffix="e",
):
    exam = Exam(
        title=f"EV Exam {suffix}",
        course="C",
        status=status,
        language="de",
        institution_id=institution_id,
        created_by=created_by,
        visibility=visibility,
        org_unit_id=org_unit_id,
    )
    db.add(exam)
    db.flush()
    return exam


def login(client, user):
    """Override beide Auth-Dependencies auf denselben User."""
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_current_active_user] = lambda: user


# ---------------------------------------------------------------------------
# filter_exams_for_user / is_exam_visible_for — unit level
# ---------------------------------------------------------------------------


def test_filter_private_visible_only_to_creator(ev_db):
    inst = make_institution(ev_db, "p1")
    creator = make_user(ev_db, inst.id, "p1a")
    colleague = make_user(ev_db, inst.id, "p1b")
    e = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()

    visible_to_creator = filter_exams_for_user(ev_db.query(Exam), creator, ev_db).all()
    visible_to_colleague = filter_exams_for_user(
        ev_db.query(Exam), colleague, ev_db
    ).all()

    assert e in visible_to_creator
    assert e not in visible_to_colleague


def test_filter_institution_visible_to_institution_members_only(ev_db):
    inst = make_institution(ev_db, "i1")
    creator = make_user(ev_db, inst.id, "i1a")
    colleague = make_user(ev_db, inst.id, "i1b")
    outsider_inst = make_institution(ev_db, "i2")
    outsider = make_user(ev_db, outsider_inst.id, "i2a")
    e = make_exam(ev_db, inst.id, created_by=creator.id)
    ev_db.commit()

    assert e in filter_exams_for_user(ev_db.query(Exam), colleague, ev_db).all()
    assert e not in filter_exams_for_user(ev_db.query(Exam), outsider, ev_db).all()


def test_filter_team_visible_to_org_unit_members_only(ev_db):
    inst = make_institution(ev_db, "t1")
    ou = make_org_unit(ev_db, inst.id, "t1")
    other_ou = make_org_unit(ev_db, inst.id, "t1-other")
    creator = make_user(ev_db, inst.id, "t1a")
    teammate = make_user(ev_db, inst.id, "t1b")
    other_team_member = make_user(ev_db, inst.id, "t1c")
    add_membership(ev_db, creator.id, ou.id)
    add_membership(ev_db, teammate.id, ou.id)
    add_membership(ev_db, other_team_member.id, other_ou.id)
    e = make_exam(
        ev_db,
        inst.id,
        created_by=creator.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=ou.id,
    )
    ev_db.commit()

    assert e in filter_exams_for_user(ev_db.query(Exam), teammate, ev_db).all()
    assert (
        e
        not in filter_exams_for_user(ev_db.query(Exam), other_team_member, ev_db).all()
    )


def test_filter_team_visible_to_ancestor_org_unit_member(ev_db):
    """get_user_accessible_org_unit_ids is the union of DESCENDANT sets for
    every OrgUnit the user directly belongs to — a member of the parent
    Abteilung must see an exam scoped to a child team."""
    inst = make_institution(ev_db, "anc1")
    parent = make_org_unit(ev_db, inst.id, "anc1parent")
    child = make_org_unit(ev_db, inst.id, "anc1child", parent_org_unit_id=parent.id)
    creator = make_user(ev_db, inst.id, "anc1creator")
    ancestor_member = make_user(ev_db, inst.id, "anc1ancestor")
    add_membership(ev_db, ancestor_member.id, parent.id)
    e = make_exam(
        ev_db,
        inst.id,
        created_by=creator.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=child.id,
    )
    ev_db.commit()

    assert e in filter_exams_for_user(ev_db.query(Exam), ancestor_member, ev_db).all()
    assert is_exam_visible_for(ancestor_member, e, ev_db) is True


def test_filter_team_not_visible_to_sibling_org_unit_member(ev_db):
    """Inverse of the ancestor case: membership in a SIBLING subtree (same
    parent, different child) must not grant access."""
    inst = make_institution(ev_db, "sib1")
    parent = make_org_unit(ev_db, inst.id, "sib1parent")
    child_a = make_org_unit(ev_db, inst.id, "sib1a", parent_org_unit_id=parent.id)
    child_b = make_org_unit(ev_db, inst.id, "sib1b", parent_org_unit_id=parent.id)
    creator = make_user(ev_db, inst.id, "sib1creator")
    sibling_member = make_user(ev_db, inst.id, "sib1sibling")
    add_membership(ev_db, sibling_member.id, child_b.id)
    e = make_exam(
        ev_db,
        inst.id,
        created_by=creator.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=child_a.id,
    )
    ev_db.commit()

    assert (
        e not in filter_exams_for_user(ev_db.query(Exam), sibling_member, ev_db).all()
    )
    assert is_exam_visible_for(sibling_member, e, ev_db) is False


def test_filter_team_requires_institution_match_even_with_org_unit_membership(ev_db):
    """Bugfix-mirror (see question_visibility's identical test): an exam
    whose org_unit_id and institution_id have drifted apart must not leak to
    Org-Unit members of the OTHER institution — Org-Unit membership alone is
    not sufficient without an institution_id match."""
    inst_a = make_institution(ev_db, "ig1a")
    inst_b = make_institution(ev_db, "ig1b")
    ou = make_org_unit(ev_db, inst_a.id, "ig1")
    member = make_user(ev_db, inst_a.id, "ig1member")
    add_membership(ev_db, member.id, ou.id)
    drifted = make_exam(
        ev_db, inst_b.id, visibility=ExamVisibility.TEAM, org_unit_id=ou.id
    )
    ev_db.commit()

    assert drifted not in filter_exams_for_user(ev_db.query(Exam), member, ev_db).all()
    assert is_exam_visible_for(member, drifted, ev_db) is False


def test_filter_read_all_bypass_sees_private_and_team_within_institution(ev_db):
    inst = make_institution(ev_db, "r1")
    ou = make_org_unit(ev_db, inst.id, "r1")
    creator = make_user(ev_db, inst.id, "r1a")
    admin = make_user_with_role(ev_db, inst.id, "r1admin", ["exams:read_all"])
    priv = make_exam(
        ev_db,
        inst.id,
        created_by=creator.id,
        visibility=ExamVisibility.PRIVATE,
        suffix="r1priv",
    )
    team = make_exam(
        ev_db,
        inst.id,
        created_by=creator.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=ou.id,
        suffix="r1team",
    )
    ev_db.commit()

    visible = filter_exams_for_user(ev_db.query(Exam), admin, ev_db).all()
    assert priv in visible
    # admin is not a member of `ou` — only the bypass grants this.
    assert team in visible


def test_filter_read_all_bypass_never_crosses_institutions(ev_db):
    inst1 = make_institution(ev_db, "x1")
    inst2 = make_institution(ev_db, "x2")
    admin = make_user_with_role(ev_db, inst1.id, "x1admin", ["exams:read_all"])
    foreign = make_exam(ev_db, inst2.id)
    ev_db.commit()

    assert foreign not in filter_exams_for_user(ev_db.query(Exam), admin, ev_db).all()


def test_filter_superuser_bypasses_entirely(ev_db):
    inst = make_institution(ev_db, "s1")
    su = make_user(ev_db, inst.id, "s1su", is_superuser=True)
    e = make_exam(ev_db, inst.id, visibility=ExamVisibility.PRIVATE)
    ev_db.commit()

    assert e in filter_exams_for_user(ev_db.query(Exam), su, ev_db).all()


def test_is_exam_visible_for_matches_filter(ev_db):
    inst = make_institution(ev_db, "m1")
    creator = make_user(ev_db, inst.id, "m1a")
    colleague = make_user(ev_db, inst.id, "m1b")
    e = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()

    assert is_exam_visible_for(creator, e, ev_db) is True
    assert is_exam_visible_for(colleague, e, ev_db) is False


# ---------------------------------------------------------------------------
# Wired: Exam-Liste + Detail (HTTP) — list_exams / get_exam
# ---------------------------------------------------------------------------


def test_list_exams_hides_colleague_private_exam(ev_db, ev_client):
    inst = make_institution(ev_db, "l1")
    creator = make_user(ev_db, inst.id, "l1a")
    viewer = make_user_with_role(ev_db, inst.id, "l1b", ["create_exams"])
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    visible = make_exam(ev_db, inst.id, created_by=creator.id, suffix="pub")
    ev_db.commit()
    login(ev_client, viewer)

    resp = ev_client.get("/api/v1/exams/")
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exams"]}
    assert priv.id not in ids
    assert visible.id in ids


def test_list_exams_read_all_admin_sees_private(ev_db, ev_client):
    inst = make_institution(ev_db, "l2")
    creator = make_user(ev_db, inst.id, "l2a")
    admin = make_user_with_role(
        ev_db, inst.id, "l2admin", ["create_exams", "exams:read_all"]
    )
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, admin)

    resp = ev_client.get("/api/v1/exams/")
    assert resp.status_code == 200
    ids = {e["id"] for e in resp.json()["exams"]}
    assert priv.id in ids


def test_get_exam_hides_colleague_private_exam_with_404(ev_db, ev_client):
    """404, not 403 — a private exam must stay indistinguishable from a
    nonexistent one (no existence-leak), mirrors assert_document_visible_for
    / assert_question_visible_for."""
    inst = make_institution(ev_db, "g1")
    creator = make_user(ev_db, inst.id, "g1a")
    viewer = make_user_with_role(ev_db, inst.id, "g1b", ["create_exams"])
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, viewer)

    resp = ev_client.get(f"/api/v1/exams/{priv.id}")
    assert resp.status_code == 404


def test_get_exam_read_all_admin_sees_private(ev_db, ev_client):
    inst = make_institution(ev_db, "g2")
    creator = make_user(ev_db, inst.id, "g2a")
    admin = make_user_with_role(
        ev_db, inst.id, "g2admin", ["create_exams", "exams:read_all"]
    )
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, admin)

    resp = ev_client.get(f"/api/v1/exams/{priv.id}")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Read-only bypass guarantee (ADR-0004 / TF-640 gotcha) — the bypass must
# never grant mutation access
# ---------------------------------------------------------------------------


def test_read_all_admin_cannot_edit_others_private_exam(ev_db, ev_client):
    inst = make_institution(ev_db, "b1")
    creator = make_user(ev_db, inst.id, "b1a")
    admin = make_user_with_role(
        ev_db, inst.id, "b1admin", ["create_exams", "exams:read_all"]
    )
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, admin)

    resp = ev_client.put(
        f"/api/v1/exams/{priv.id}",
        json={"title": "Hijacked", "updated_at": priv.updated_at.isoformat()},
    )
    # 404, not 403 — same existence-leak guarantee as the read path; the
    # admin can list/see it (read bypass) but the write path re-checks
    # visibility with allow_read_all_bypass=False and must reject exactly as
    # if the exam didn't exist to them.
    assert resp.status_code == 404
    ev_db.refresh(priv)
    assert priv.title != "Hijacked"


def test_read_all_admin_cannot_delete_others_private_exam(ev_db, ev_client):
    inst = make_institution(ev_db, "b2")
    creator = make_user(ev_db, inst.id, "b2a")
    admin = make_user_with_role(
        ev_db, inst.id, "b2admin", ["create_exams", "exams:read_all", "delete_exams"]
    )
    priv = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, admin)

    resp = ev_client.delete(f"/api/v1/exams/{priv.id}")
    assert resp.status_code == 404
    assert ev_db.query(Exam).filter(Exam.id == priv.id).one_or_none() is not None


# --- Institution-drift boundary (PR #193 review fix) -----------------------
#
# is_exam_visible_for's creator branch alone doesn't imply institution
# match — unlike the read-all-bypass/TEAM/INSTITUTION branches. Without
# require_same_institution, an exam creator whose user.institution_id has
# drifted from exam.institution_id (e.g. an institution transfer that
# intentionally left exams behind — see
# services.user_institution_transfer_service with flags.exams=False) would
# keep full mutation rights on an exam that now belongs to a different
# institution. Reads must stay permissive across the drift (mirrors
# Document/Question); mutations must not.


def test_creator_institution_drift_can_still_read_but_not_mutate(ev_db, ev_client):
    inst_a = make_institution(ev_db, "drift1a")
    inst_b = make_institution(ev_db, "drift1b")
    creator = make_user_with_role(ev_db, inst_a.id, "drift1", ["create_exams"])
    e = make_exam(
        ev_db, inst_b.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, creator)

    # Read stays permissive across the drift.
    resp = ev_client.get(f"/api/v1/exams/{e.id}")
    assert resp.status_code == 200

    # Mutation must not — this is the fix.
    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"title": "Hijacked", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 404
    ev_db.refresh(e)
    assert e.title != "Hijacked"


# --- Bypass-exclusion across every gated mutation endpoint (PR #193 review
# fix — only update_exam/delete_exam had a dedicated test before) ----------

_MUTATION_ENDPOINTS = [
    ("PUT", "/api/v1/exams/{id}", {"updated_at": "2024-01-01T00:00:00+00:00"}),
    (
        "PATCH",
        "/api/v1/exams/{id}/grading-scheme",
        {"updated_at": "2024-01-01T00:00:00+00:00"},
    ),
    ("DELETE", "/api/v1/exams/{id}", None),
    ("POST", "/api/v1/exams/{id}/archive", {}),
    ("POST", "/api/v1/exams/{id}/restore", None),
    ("POST", "/api/v1/exams/{id}/questions", {"question_ids": [1]}),
    ("PUT", "/api/v1/exams/{id}/questions/1", {}),
    ("DELETE", "/api/v1/exams/{id}/questions/1", None),
    ("POST", "/api/v1/exams/{id}/reorder", {"order": []}),
    ("POST", "/api/v1/exams/{id}/auto-fill", {}),
    ("POST", "/api/v1/exams/{id}/finalize", None),
    ("POST", "/api/v1/exams/{id}/unfinalize", None),
    ("GET", "/api/v1/exams/{id}/export/md", None),
]


@pytest.mark.parametrize(
    "idx,method,path_template,body",
    [(i, m, p, b) for i, (m, p, b) in enumerate(_MUTATION_ENDPOINTS)],
    ids=[f"{m} {p}" for m, p, _ in _MUTATION_ENDPOINTS],
)
def test_read_all_bypass_excluded_from_every_mutation_endpoint(
    ev_db, ev_client, idx, method, path_template, body
):
    """Every one of the 13 call sites that pass
    ``allow_read_all_bypass=False`` to ``_get_exam_or_404`` must actually
    deny a same-institution ``exams:read_all`` admin on another user's
    PRIVATE exam (404, not the permission-layer 403 and not success). The
    visibility check is the first statement in every one of these handlers,
    so the bodies above only need to be schema-valid, not semantically
    valid — the 404 fires before any of it is used.

    ``idx`` namespaces every fixture per parametrize case — ``ev_db`` here
    commits directly (no savepoint rollback between cases like ``ea_db``),
    so a shared suffix across all 13 cases would collide on unique
    institution names/role names."""
    suffix = f"byp{idx}"
    inst = make_institution(ev_db, suffix)
    creator = make_user(ev_db, inst.id, f"{suffix}creator")
    admin = make_user_with_role(
        ev_db,
        inst.id,
        f"{suffix}admin",
        ["exams:read_all", "create_exams", "delete_exams"],
    )
    e = make_exam(
        ev_db, inst.id, created_by=creator.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()
    login(ev_client, admin)

    path = path_template.format(id=e.id)
    kwargs = {"json": body} if body is not None else {}
    resp = ev_client.request(method, path, **kwargs)

    assert resp.status_code == 404, (
        f"{method} {path} leaked the read-all bypass into a mutation: "
        f"expected 404, got {resp.status_code} ({resp.text[:200]})"
    )


def test_colleague_without_bypass_can_still_edit_institution_visible_exam(
    ev_db, ev_client
):
    """Regression guard: the pre-TF-643 status quo (any create_exams holder
    can edit any institution-visible exam) must survive for the default
    visibility — only PRIVATE/TEAM exams become newly restricted."""
    inst = make_institution(ev_db, "b3")
    creator = make_user(ev_db, inst.id, "b3a")
    colleague = make_user_with_role(ev_db, inst.id, "b3b", ["create_exams"])
    e = make_exam(ev_db, inst.id, created_by=creator.id)  # default INSTITUTION
    ev_db.commit()
    login(ev_client, colleague)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"title": "Edited by colleague", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Edited by colleague"


# ---------------------------------------------------------------------------
# Visibility set-path: POST / (create) and PUT /{id} (update)
# ---------------------------------------------------------------------------


def test_create_exam_defaults_to_institution_visibility(ev_db, ev_client):
    inst = make_institution(ev_db, "c1")
    creator = make_user_with_role(ev_db, inst.id, "c1a", ["create_exams"])
    login(ev_client, creator)

    resp = ev_client.post("/api/v1/exams/", json={"title": "New Exam"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "institution"
    assert body["org_unit_id"] is None


def test_create_exam_with_team_visibility(ev_db, ev_client):
    inst = make_institution(ev_db, "c2")
    ou = make_org_unit(ev_db, inst.id, "c2")
    creator = make_user_with_role(ev_db, inst.id, "c2a", ["create_exams"])
    add_membership(ev_db, creator.id, ou.id)
    ev_db.commit()
    login(ev_client, creator)

    resp = ev_client.post(
        "/api/v1/exams/",
        json={"title": "Team Exam", "visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_create_exam_team_visibility_requires_org_unit(ev_db, ev_client):
    inst = make_institution(ev_db, "c3")
    creator = make_user_with_role(ev_db, inst.id, "c3a", ["create_exams"])
    login(ev_client, creator)

    resp = ev_client.post(
        "/api/v1/exams/", json={"title": "Bad Team Exam", "visibility": "team"}
    )
    assert resp.status_code == 400


def test_create_exam_team_visibility_requires_own_org_unit_membership(ev_db, ev_client):
    inst = make_institution(ev_db, "c4")
    ou = make_org_unit(ev_db, inst.id, "c4")
    creator = make_user_with_role(ev_db, inst.id, "c4a", ["create_exams"])
    ev_db.commit()  # creator is NOT a member of ou
    login(ev_client, creator)

    resp = ev_client.post(
        "/api/v1/exams/",
        json={"title": "Foreign Team Exam", "visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 400


def test_create_exam_team_visibility_allows_superuser_without_membership(
    ev_db, ev_client
):
    """SuperUser bugfix (PR #193 review): the create path's org-unit
    membership check ran unconditionally, unlike the update path's
    equivalent guard — a superuser (typically no Org-Unit membership, often
    institution_id=None) got a spurious 400. Mirrors
    _resolve_exam_visibility_update's existing guard and TF-642's identical
    fix in question_review.py."""
    inst = make_institution(ev_db, "su1")
    ou = make_org_unit(ev_db, inst.id, "su1")
    su = make_user(ev_db, inst.id, "su1su", is_superuser=True)
    ev_db.commit()  # su is NOT a member of ou
    login(ev_client, su)

    resp = ev_client.post(
        "/api/v1/exams/",
        json={"title": "SU Team Exam", "visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_update_exam_visibility_allows_owner(ev_db, ev_client):
    inst = make_institution(ev_db, "u1")
    owner = make_user_with_role(ev_db, inst.id, "u1a", ["create_exams"])
    e = make_exam(ev_db, inst.id, created_by=owner.id)
    ev_db.commit()
    login(ev_client, owner)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"visibility": "private", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "private"


def test_update_exam_visibility_rejects_non_owner_non_superuser(ev_db, ev_client):
    """A colleague who can see (and, under the pre-existing institution-flat
    edit model, can otherwise edit) an INSTITUTION-visible exam must still
    not be able to change ITS visibility — only the owner or a SuperUser may
    (mirrors Document/TF-620)."""
    inst = make_institution(ev_db, "u2")
    owner = make_user(ev_db, inst.id, "u2a")
    colleague = make_user_with_role(ev_db, inst.id, "u2b", ["create_exams"])
    e = make_exam(ev_db, inst.id, created_by=owner.id)
    ev_db.commit()
    login(ev_client, colleague)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"visibility": "private", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 403
    ev_db.refresh(e)
    assert e.visibility == ExamVisibility.INSTITUTION


def test_update_exam_non_owner_sending_null_visibility_is_not_a_change(
    ev_db, ev_client
):
    """No-op-403 fix (PR #193 review): exclude_unset only proves the caller
    sent the "visibility" key, not that it changes anything — a client that
    serializes an unset optional field as an explicit `"visibility": null`
    resolves right back to the exam's current value. That must NOT trigger
    the owner-only 403 above; a non-owner colleague editing an unrelated
    field (title) on an INSTITUTION-visible exam must still succeed."""
    inst = make_institution(ev_db, "noop1")
    owner = make_user(ev_db, inst.id, "noop1owner")
    colleague = make_user_with_role(ev_db, inst.id, "noop1colleague", ["create_exams"])
    e = make_exam(ev_db, inst.id, created_by=owner.id)  # default INSTITUTION
    ev_db.commit()
    login(ev_client, colleague)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={
            "title": "Edited",
            "visibility": None,
            "updated_at": e.updated_at.isoformat(),
        },
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Edited"


def test_update_exam_rejects_team_visibility_without_membership(ev_db, ev_client):
    inst = make_institution(ev_db, "u3")
    ou = make_org_unit(ev_db, inst.id, "u3")
    owner = make_user_with_role(ev_db, inst.id, "u3a", ["create_exams"])
    e = make_exam(ev_db, inst.id, created_by=owner.id)
    ev_db.commit()
    login(ev_client, owner)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={
            "visibility": "team",
            "org_unit_id": ou.id,
            "updated_at": e.updated_at.isoformat(),
        },
    )
    assert resp.status_code == 400


def test_update_exam_visibility_allows_superuser_for_others_exam(ev_db, ev_client):
    inst = make_institution(ev_db, "u4")
    owner = make_user(ev_db, inst.id, "u4a")
    su = make_user(ev_db, inst.id, "u4su", is_superuser=True)
    e = make_exam(ev_db, inst.id, created_by=owner.id)
    ev_db.commit()
    login(ev_client, su)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"visibility": "private", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "private"


def test_update_exam_visibility_allows_superuser_to_set_team_without_membership(
    ev_db, ev_client
):
    """Same SuperUser bugfix as the create path — the update path's guard
    already existed in code but had no test exercising the actual team +
    non-member-superuser combination (only 'set to private' was covered
    above)."""
    inst = make_institution(ev_db, "su2")
    ou = make_org_unit(ev_db, inst.id, "su2")
    owner = make_user(ev_db, inst.id, "su2owner")
    su = make_user(ev_db, inst.id, "su2su", is_superuser=True)
    e = make_exam(ev_db, inst.id, created_by=owner.id)
    ev_db.commit()  # su is NOT a member of ou
    login(ev_client, su)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={
            "visibility": "team",
            "org_unit_id": ou.id,
            "updated_at": e.updated_at.isoformat(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_update_exam_clears_org_unit_id_when_leaving_team(ev_db, ev_client):
    inst = make_institution(ev_db, "u5")
    ou = make_org_unit(ev_db, inst.id, "u5")
    owner = make_user_with_role(ev_db, inst.id, "u5a", ["create_exams"])
    add_membership(ev_db, owner.id, ou.id)
    e = make_exam(
        ev_db,
        inst.id,
        created_by=owner.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=ou.id,
    )
    ev_db.commit()
    login(ev_client, owner)

    resp = ev_client.put(
        f"/api/v1/exams/{e.id}",
        json={"visibility": "institution", "updated_at": e.updated_at.isoformat()},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "institution"
    assert body["org_unit_id"] is None


# ---------------------------------------------------------------------------
# Deliberately NOT filtered — regression guards for the /grilling decisions
# ---------------------------------------------------------------------------


def test_submissions_grading_ignores_exam_visibility(ev_db):
    """A grader without owner/team access to a PRIVATE exam must still be
    able to load it for grading — the grading pipeline stays
    institution-flat, unaffected by ExamVisibility (/grilling TF-643)."""
    from api.submissions import _load_exam_for_user

    inst = make_institution(ev_db, "sub1")
    owner = make_user(ev_db, inst.id, "sub1a")
    grader = make_user(ev_db, inst.id, "sub1b")
    e = make_exam(
        ev_db, inst.id, created_by=owner.id, visibility=ExamVisibility.PRIVATE
    )
    ev_db.commit()

    loaded = _load_exam_for_user(db=ev_db, user=grader, exam_id=e.id)
    assert loaded.id == e.id


def test_exam_visibility_meaning_uniform_across_lifecycle(ev_db):
    """A PRIVATE exam stays hidden from a colleague regardless of
    DRAFT/FINALIZED/EXPORTED status — visibility isn't special-cased per
    lifecycle stage (/grilling TF-643)."""
    inst = make_institution(ev_db, "life1")
    owner = make_user(ev_db, inst.id, "life1a")
    colleague = make_user(ev_db, inst.id, "life1b")
    for status in ("draft", "finalized", "exported"):
        e = make_exam(
            ev_db,
            inst.id,
            created_by=owner.id,
            visibility=ExamVisibility.PRIVATE,
            status=status,
            suffix=f"life-{status}",
        )
        ev_db.commit()
        assert is_exam_visible_for(colleague, e, ev_db) is False


# ---------------------------------------------------------------------------
# Org-Unit deletion guard (TF-620/TF-641/TF-642 pattern extended to Exam)
# ---------------------------------------------------------------------------


def test_delete_org_unit_blocked_by_team_visible_exam(ev_db):
    inst = make_institution(ev_db, "ou1")
    ou = make_org_unit(ev_db, inst.id, "ou1")
    owner = make_user(ev_db, inst.id, "ou1a")
    make_exam(
        ev_db,
        inst.id,
        created_by=owner.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=ou.id,
    )
    ev_db.commit()

    with pytest.raises(ValueError, match="Prüfungen") as exc_info:
        delete_org_unit(ev_db, ou)
    # The exam-specific constraint-name branch must have fired, not the
    # generic 4-resource fallback message — both contain "Prüfungen" as a
    # substring (PR #193 review: match= alone can't distinguish them, so a
    # broken constraint-name detection for exams would pass silently).
    assert "Dokumente" not in str(exc_info.value)


# --- DB CHECK constraint regression tests (PR #193 review) ------------------
#
# ck_exams_team_visibility_requires_org_unit is reachable (unlike the
# institution constraint — see models/exam.py comment) and must reject a
# row that violates either direction of the biconditional, even when the
# application-layer 400 guards in _resolve_exam_visibility_for_create/
# _resolve_exam_visibility_update are bypassed (e.g. a raw ORM insert).
# Mirrors test_document_visibility.py's equivalent check-constraint test.


def test_db_check_constraint_blocks_team_visibility_without_org_unit(ev_db):
    inst = make_institution(ev_db, "ck1")
    ev_db.commit()

    bad = Exam(
        title="Bad Team Exam",
        course="C",
        status="draft",
        language="de",
        institution_id=inst.id,
        visibility=ExamVisibility.TEAM,
        org_unit_id=None,
    )
    ev_db.add(bad)
    with pytest.raises(IntegrityError):
        ev_db.flush()
    ev_db.rollback()


def test_db_check_constraint_blocks_org_unit_without_team_visibility(ev_db):
    inst = make_institution(ev_db, "ck2")
    ou = make_org_unit(ev_db, inst.id, "ck2")
    ev_db.commit()

    bad = Exam(
        title="Orphan Org-Unit Exam",
        course="C",
        status="draft",
        language="de",
        institution_id=inst.id,
        visibility=ExamVisibility.INSTITUTION,
        org_unit_id=ou.id,
    )
    ev_db.add(bad)
    with pytest.raises(IntegrityError):
        ev_db.flush()
    ev_db.rollback()
