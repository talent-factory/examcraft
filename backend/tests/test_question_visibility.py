"""TF-642: Tests für QuestionReview-Sichtbarkeit (private/team/institution)
+ Institutions-Admin-Bypass (``questions:read_all``).

Scope-Grenze (siehe utils/question_visibility.py Modul-Docstring +
/grilling-Entscheidungen TF-642): Sichtbarkeit gilt NUR für den Fragenpool
(``list_approved_questions`` / ``_build_candidate_query``-Auto-Fill) —
deliberately NICHT für die Review-Queue oder Mutation (edit/approve/reject/
archive/delete), die permission+institution-skopiert bleiben, und NICHT für
``get_approved_question`` (Detail-Vorschau bleibt absichtlich rein
tenant-skopiert, siehe deren eigenen Docstring). Die letzten drei Punkte
haben je einen expliziten Regressions-Test unten, damit das Verhalten nicht
versehentlich "korrigiert" wird.
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from main import app
from models.auth import Institution, User, UserStatus, Role
from models.exam import Exam
from models.org_unit import OrgUnit, UserOrgUnit
from models.question_review import (
    QuestionReview,
    QuestionReviewVisibility,
    ReviewHistory,
    ReviewStatus,
)
from services.org_unit_service import delete_org_unit
from utils.auth_utils import get_current_user, get_current_active_user
from utils.question_visibility import (
    filter_questions_for_user,
    is_question_visible_for,
)
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def qv_db(test_engine):
    Session_ = sessionmaker(bind=test_engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture()
def qv_client(qv_db: Session):
    import api.question_review as qr_module
    import api.exams as exams_module

    app.include_router(qr_module.router)
    app.include_router(exams_module.router)

    def override_get_db():
        yield qv_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix="qv"):
    inst = Institution(
        name=f"QV Uni {suffix}",
        slug=f"qv-uni-{suffix}",
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
        email=f"qvuser{suffix}@test.com",
        first_name="QV",
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

    Rollenname mit ``tf642-`` genamespaced — ``Role.name`` ist global unique
    (CI-Gotcha, siehe TF-640-Nachlese), Kollision mit anderen Testdateien
    vermeiden.
    """
    user = make_user(db, institution_id, suffix)
    role = Role(
        name=f"tf642-role-{suffix}",
        display_name=f"TF-642 Role {suffix}",
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


def make_exam(db, institution_id, created_by=None, status="draft", title="QV Exam"):
    exam = Exam(
        title=title,
        course="C",
        status=status,
        language="de",
        institution_id=institution_id,
        created_by=created_by,
    )
    db.add(exam)
    db.flush()
    return exam


def make_question(
    db,
    institution_id,
    created_by=None,
    visibility=QuestionReviewVisibility.INSTITUTION,
    org_unit_id=None,
    status=ReviewStatus.APPROVED.value,
    suffix="q",
):
    q = QuestionReview(
        question_text=f"Was ist {suffix}?",
        question_type="open_ended",
        difficulty="easy",
        topic=suffix,
        review_status=status,
        institution_id=institution_id,
        created_by=created_by,
        visibility=visibility,
        org_unit_id=org_unit_id,
    )
    db.add(q)
    db.flush()
    return q


def login(client, user):
    """Override beide Auth-Dependencies auf denselben User."""
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_current_active_user] = lambda: user


# ---------------------------------------------------------------------------
# filter_questions_for_user — unit level
# ---------------------------------------------------------------------------


def test_filter_private_visible_only_to_creator(qv_db):
    inst = make_institution(qv_db, "p1")
    creator = make_user(qv_db, inst.id, "p1a")
    colleague = make_user(qv_db, inst.id, "p1b")
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()

    visible_to_creator = filter_questions_for_user(
        qv_db.query(QuestionReview), creator, qv_db
    ).all()
    visible_to_colleague = filter_questions_for_user(
        qv_db.query(QuestionReview), colleague, qv_db
    ).all()

    assert q in visible_to_creator
    assert q not in visible_to_colleague


def test_filter_institution_visible_to_institution_members_only(qv_db):
    inst = make_institution(qv_db, "i1")
    creator = make_user(qv_db, inst.id, "i1a")
    colleague = make_user(qv_db, inst.id, "i1b")
    outsider_inst = make_institution(qv_db, "i2")
    outsider = make_user(qv_db, outsider_inst.id, "i2a")
    q = make_question(qv_db, inst.id, created_by=creator.id)
    qv_db.commit()

    assert (
        q
        in filter_questions_for_user(
            qv_db.query(QuestionReview), colleague, qv_db
        ).all()
    )
    assert (
        q
        not in filter_questions_for_user(
            qv_db.query(QuestionReview), outsider, qv_db
        ).all()
    )


def test_filter_team_visible_to_org_unit_members_only(qv_db):
    inst = make_institution(qv_db, "t1")
    ou = make_org_unit(qv_db, inst.id, "t1")
    other_ou = make_org_unit(qv_db, inst.id, "t1-other")
    creator = make_user(qv_db, inst.id, "t1a")
    teammate = make_user(qv_db, inst.id, "t1b")
    other_team_member = make_user(qv_db, inst.id, "t1c")
    add_membership(qv_db, creator.id, ou.id)
    add_membership(qv_db, teammate.id, ou.id)
    add_membership(qv_db, other_team_member.id, other_ou.id)
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou.id,
    )
    qv_db.commit()

    assert (
        q
        in filter_questions_for_user(qv_db.query(QuestionReview), teammate, qv_db).all()
    )
    assert (
        q
        not in filter_questions_for_user(
            qv_db.query(QuestionReview), other_team_member, qv_db
        ).all()
    )


def test_filter_team_visible_to_ancestor_org_unit_member(qv_db):
    """get_user_accessible_org_unit_ids is the union of DESCENDANT sets for
    every OrgUnit the user directly belongs to — a member of the parent
    Abteilung must see a question scoped to a child team."""
    inst = make_institution(qv_db, "anc1")
    parent = make_org_unit(qv_db, inst.id, "anc1parent")
    child = make_org_unit(qv_db, inst.id, "anc1child", parent_org_unit_id=parent.id)
    creator = make_user(qv_db, inst.id, "anc1creator")
    ancestor_member = make_user(qv_db, inst.id, "anc1ancestor")
    add_membership(qv_db, ancestor_member.id, parent.id)
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=child.id,
    )
    qv_db.commit()

    assert (
        q
        in filter_questions_for_user(
            qv_db.query(QuestionReview), ancestor_member, qv_db
        ).all()
    )
    assert is_question_visible_for(ancestor_member, q, qv_db) is True


def test_filter_team_not_visible_to_sibling_org_unit_member(qv_db):
    """The inverse of the ancestor case: membership in a SIBLING subtree
    (same parent, different child) must not grant access."""
    inst = make_institution(qv_db, "sib1")
    parent = make_org_unit(qv_db, inst.id, "sib1parent")
    child_a = make_org_unit(qv_db, inst.id, "sib1a", parent_org_unit_id=parent.id)
    child_b = make_org_unit(qv_db, inst.id, "sib1b", parent_org_unit_id=parent.id)
    creator = make_user(qv_db, inst.id, "sib1creator")
    sibling_member = make_user(qv_db, inst.id, "sib1sibling")
    add_membership(qv_db, sibling_member.id, child_b.id)
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=child_a.id,
    )
    qv_db.commit()

    assert (
        q
        not in filter_questions_for_user(
            qv_db.query(QuestionReview), sibling_member, qv_db
        ).all()
    )
    assert is_question_visible_for(sibling_member, q, qv_db) is False


def test_filter_team_requires_institution_match_even_with_org_unit_membership(qv_db):
    """Bugfix: a question whose org_unit_id and institution_id have drifted
    apart (e.g. an institution transfer that moves institution_id without
    clearing org_unit_id) must not leak to Org-Unit members of the OTHER
    institution — Org-Unit membership alone was previously sufficient for
    the TEAM branch, with no check that the question's institution_id still
    matches the viewer's."""
    inst_a = make_institution(qv_db, "ig1a")
    inst_b = make_institution(qv_db, "ig1b")
    ou = make_org_unit(qv_db, inst_a.id, "ig1")
    member = make_user(qv_db, inst_a.id, "ig1member")
    add_membership(qv_db, member.id, ou.id)
    # Simulated drift: org_unit_id still points at institution A's OrgUnit,
    # but institution_id now says institution B.
    drifted = make_question(
        qv_db,
        inst_b.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou.id,
    )
    qv_db.commit()

    assert (
        drifted
        not in filter_questions_for_user(
            qv_db.query(QuestionReview), member, qv_db
        ).all()
    )
    assert is_question_visible_for(member, drifted, qv_db) is False


def test_filter_read_all_bypass_sees_private_and_team_within_institution(qv_db):
    """The bypass name/docstring promises BOTH tiers — bug fix: the
    original version of this test only ever built a PRIVATE question, so it
    could not have caught a bypass regression that widened PRIVATE but left
    TEAM unaffected (or vice versa)."""
    inst = make_institution(qv_db, "r1")
    ou = make_org_unit(qv_db, inst.id, "r1")
    creator = make_user(qv_db, inst.id, "r1a")
    admin = make_user_with_role(qv_db, inst.id, "r1admin", ["questions:read_all"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
        suffix="r1priv",
    )
    team = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou.id,
        suffix="r1team",
    )
    qv_db.commit()

    visible = filter_questions_for_user(qv_db.query(QuestionReview), admin, qv_db).all()
    assert priv in visible
    # admin is not a member of `ou` — only the bypass grants this.
    assert team in visible


def test_filter_read_all_bypass_never_crosses_institutions(qv_db):
    inst1 = make_institution(qv_db, "x1")
    inst2 = make_institution(qv_db, "x2")
    admin = make_user_with_role(qv_db, inst1.id, "x1admin", ["questions:read_all"])
    foreign = make_question(qv_db, inst2.id)
    qv_db.commit()

    assert (
        foreign
        not in filter_questions_for_user(
            qv_db.query(QuestionReview), admin, qv_db
        ).all()
    )


def test_filter_superuser_bypasses_entirely(qv_db):
    inst = make_institution(qv_db, "s1")
    su = make_user(qv_db, inst.id, "s1su", is_superuser=True)
    q = make_question(qv_db, inst.id, visibility=QuestionReviewVisibility.PRIVATE)
    qv_db.commit()

    assert q in filter_questions_for_user(qv_db.query(QuestionReview), su, qv_db).all()


def test_is_question_visible_for_matches_filter(qv_db):
    inst = make_institution(qv_db, "m1")
    creator = make_user(qv_db, inst.id, "m1a")
    colleague = make_user(qv_db, inst.id, "m1b")
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()

    assert is_question_visible_for(creator, q, qv_db) is True
    assert is_question_visible_for(colleague, q, qv_db) is False


# ---------------------------------------------------------------------------
# Wired: Fragenpool-Liste (HTTP) — list_approved_questions
# ---------------------------------------------------------------------------


def test_approved_questions_list_hides_colleague_private_question(qv_db, qv_client):
    inst = make_institution(qv_db, "l1")
    creator = make_user(qv_db, inst.id, "l1a")
    viewer = make_user_with_role(qv_db, inst.id, "l1b", ["create_exams"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    visible = make_question(qv_db, inst.id, created_by=creator.id, suffix="pub")
    qv_db.commit()
    login(qv_client, viewer)

    resp = qv_client.get("/api/v1/exams/approved-questions")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert priv.id not in ids
    assert visible.id in ids


def test_approved_questions_list_read_all_admin_sees_private(qv_db, qv_client):
    inst = make_institution(qv_db, "l2")
    creator = make_user(qv_db, inst.id, "l2a")
    admin = make_user_with_role(
        qv_db, inst.id, "l2admin", ["create_exams", "questions:read_all"]
    )
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()
    login(qv_client, admin)

    resp = qv_client.get("/api/v1/exams/approved-questions")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert priv.id in ids


# ---------------------------------------------------------------------------
# Deliberately NOT filtered — regression guards for the /grilling decisions
# ---------------------------------------------------------------------------


def test_review_queue_ignores_visibility(qv_db, qv_client):
    """Reviewer sieht die private Frage einer Kollegin in der Review-Queue —
    Mutation/Review bleibt bewusst permission+institution-skopiert, nicht
    visibility-skopiert (/grilling TF-642)."""
    inst = make_institution(qv_db, "q1")
    creator = make_user(qv_db, inst.id, "q1a")
    reviewer = make_user_with_role(qv_db, inst.id, "q1rev", ["review_questions"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
        status=ReviewStatus.PENDING.value,
    )
    qv_db.commit()
    login(qv_client, reviewer)

    resp = qv_client.get("/api/v1/questions/review")
    assert resp.status_code == 200
    ids = {q["id"] for q in resp.json()["questions"]}
    assert priv.id in ids


def test_approved_question_detail_ignores_visibility(qv_db, qv_client):
    """Eine Kollegin kann eine private Frage weiterhin per Detail-Endpunkt
    einsehen — bewusster Carve-out, damit eine bereits einer Prüfung
    hinzugefügte Frage vorschaubar bleibt (siehe
    api.exams.get_approved_question-Docstring). Frage↔Prüfung-Verknüpfung
    selbst ist auf TF-643 verschoben, hier nicht vorentschieden."""
    inst = make_institution(qv_db, "d1")
    creator = make_user(qv_db, inst.id, "d1a")
    viewer = make_user_with_role(qv_db, inst.id, "d1b", ["create_exams"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()
    login(qv_client, viewer)

    resp = qv_client.get(f"/api/v1/exams/approved-questions/{priv.id}")
    assert resp.status_code == 200


def test_edit_question_mutation_ignores_visibility(qv_db, qv_client):
    """Eine Kollegin ohne read_all kann eine private Frage weiterhin
    bearbeiten, solange sie edit_questions hat — Mutation bleibt
    permission+institution-skopiert (/grilling TF-642)."""
    inst = make_institution(qv_db, "e1")
    creator = make_user(qv_db, inst.id, "e1a")
    editor = make_user_with_role(qv_db, inst.id, "e1b", ["edit_questions"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(
        f"/api/v1/questions/{priv.id}/edit", json={"difficulty": "hard"}
    )
    assert resp.status_code == 200
    assert resp.json()["difficulty"] == "hard"


# ---------------------------------------------------------------------------
# Visibility set-path: PUT /{id}/edit
# ---------------------------------------------------------------------------


def test_edit_question_sets_team_visibility_when_editor_is_member(qv_db, qv_client):
    inst = make_institution(qv_db, "v1")
    ou = make_org_unit(qv_db, inst.id, "v1")
    editor = make_user_with_role(qv_db, inst.id, "v1a", ["edit_questions"])
    add_membership(qv_db, editor.id, ou.id)
    q = make_question(qv_db, inst.id, created_by=editor.id)
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_edit_question_rejects_team_visibility_without_membership(qv_db, qv_client):
    inst = make_institution(qv_db, "v2")
    ou = make_org_unit(qv_db, inst.id, "v2")
    editor = make_user_with_role(qv_db, inst.id, "v2a", ["edit_questions"])
    q = make_question(qv_db, inst.id, created_by=editor.id)
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 400


def test_edit_question_clears_org_unit_id_when_leaving_team(qv_db, qv_client):
    inst = make_institution(qv_db, "v3")
    ou = make_org_unit(qv_db, inst.id, "v3")
    editor = make_user_with_role(qv_db, inst.id, "v3a", ["edit_questions"])
    add_membership(qv_db, editor.id, ou.id)
    q = make_question(
        qv_db,
        inst.id,
        created_by=editor.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou.id,
    )
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit",
        json={"visibility": "institution"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "institution"
    assert body["org_unit_id"] is None


# ---------------------------------------------------------------------------
# Defaults + DB constraints
# ---------------------------------------------------------------------------


def test_new_question_defaults_to_institution_visibility(qv_db):
    inst = make_institution(qv_db, "def1")
    creator = make_user(qv_db, inst.id, "def1a")
    q = QuestionReview(
        question_text="Default?",
        question_type="open_ended",
        difficulty="easy",
        topic="default",
        review_status=ReviewStatus.PENDING.value,
        institution_id=inst.id,
        created_by=creator.id,
    )
    qv_db.add(q)
    qv_db.commit()
    qv_db.refresh(q)

    assert q.visibility == QuestionReviewVisibility.INSTITUTION
    assert q.org_unit_id is None


def test_team_visibility_without_org_unit_violates_check_constraint(qv_db):
    inst = make_institution(qv_db, "cc1")
    q = QuestionReview(
        question_text="Invalid?",
        question_type="open_ended",
        difficulty="easy",
        topic="cc",
        review_status=ReviewStatus.PENDING.value,
        institution_id=inst.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=None,
    )
    qv_db.add(q)
    with pytest.raises(IntegrityError):
        qv_db.commit()
    qv_db.rollback()


def test_org_unit_id_set_without_team_visibility_violates_check_constraint(qv_db):
    """Reverse direction of the biconditional — the constraint is
    ``(visibility = 'team') = (org_unit_id IS NOT NULL)``, not just a
    one-way ``team requires org_unit_id``."""
    inst = make_institution(qv_db, "cc2")
    ou = make_org_unit(qv_db, inst.id, "cc2")
    q = QuestionReview(
        question_text="Invalid2?",
        question_type="open_ended",
        difficulty="easy",
        topic="cc2",
        review_status=ReviewStatus.PENDING.value,
        institution_id=inst.id,
        visibility=QuestionReviewVisibility.INSTITUTION,
        org_unit_id=ou.id,
    )
    qv_db.add(q)
    with pytest.raises(IntegrityError):
        qv_db.commit()
    qv_db.rollback()


def test_delete_org_unit_referenced_by_question_names_fragen(qv_db):
    """Bugfix: the shared delete_org_unit error-message dispatch (TF-620/
    TF-641) didn't yet know about question_reviews.org_unit_id — a Team-
    visible question blocking the delete would have been mislabeled as
    'Dokumente' or the generic 'Dokumente, Prompts oder Fragen' fallback."""
    inst = make_institution(qv_db, "delq1")
    ou = make_org_unit(qv_db, inst.id, "delq1")
    make_question(
        qv_db,
        inst.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou.id,
    )
    qv_db.commit()

    with pytest.raises(ValueError, match="Fragen") as exc:
        delete_org_unit(qv_db, ou)
    assert "Dokumente" not in str(exc.value)
    assert "Prompts" not in str(exc.value)
    qv_db.rollback()
    assert qv_db.query(OrgUnit).filter_by(id=ou.id).one_or_none() is not None


# ---------------------------------------------------------------------------
# add_questions / auto-fill — must honor the same visibility model as the
# Fragenpool list, not just tenant scoping (TF-642 bugfix)
# ---------------------------------------------------------------------------


def test_add_questions_rejects_colleague_private_question(qv_db, qv_client):
    """Bugfix: POST /{exam_id}/questions previously checked only institution
    membership (TenantFilter.verify_tenant_access), letting any create_exams
    holder add a colleague's PRIVATE question just by guessing its id --
    completely bypassing the visibility model this ticket introduces."""
    inst = make_institution(qv_db, "aq1")
    creator = make_user(qv_db, inst.id, "aq1creator")
    caller = make_user_with_role(qv_db, inst.id, "aq1caller", ["create_exams"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    exam = make_exam(qv_db, inst.id, created_by=caller.id)
    qv_db.commit()
    login(qv_client, caller)

    resp = qv_client.post(
        f"/api/v1/exams/{exam.id}/questions", json={"question_ids": [priv.id]}
    )
    # 404 (not 403): a hidden question must stay indistinguishable from a
    # missing one, same convention as assert_document_visible_for (TF-640).
    assert resp.status_code == 404
    qv_db.refresh(exam)
    assert exam.questions == []


def test_add_questions_allows_visible_institution_question(qv_db, qv_client):
    """Control: the fix must not block a legitimately-visible question."""
    inst = make_institution(qv_db, "aq2")
    creator = make_user(qv_db, inst.id, "aq2creator")
    caller = make_user_with_role(qv_db, inst.id, "aq2caller", ["create_exams"])
    visible = make_question(qv_db, inst.id, created_by=creator.id)
    exam = make_exam(qv_db, inst.id, created_by=caller.id)
    qv_db.commit()
    login(qv_client, caller)

    resp = qv_client.post(
        f"/api/v1/exams/{exam.id}/questions", json={"question_ids": [visible.id]}
    )
    assert resp.status_code == 200
    qv_db.refresh(exam)
    assert {eq.question_id for eq in exam.questions} == {visible.id}


def test_auto_fill_excludes_colleague_private_question(qv_db, qv_client):
    """Locks in that _build_candidate_query (the second wiring site besides
    list_approved_questions) actually excludes an invisible question -- both
    call sites share filter_questions_for_user today, but nothing previously
    proved that in a test (the exact shape TF-641/PR#189's second critical
    bug took: a second call site drifting from the first)."""
    inst = make_institution(qv_db, "af1")
    creator = make_user(qv_db, inst.id, "af1creator")
    caller = make_user_with_role(qv_db, inst.id, "af1caller", ["create_exams"])
    priv = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
        suffix="afpriv",
    )
    visible = make_question(qv_db, inst.id, created_by=creator.id, suffix="afvis")
    exam = make_exam(qv_db, inst.id, created_by=caller.id)
    qv_db.commit()
    login(qv_client, caller)

    resp = qv_client.post(f"/api/v1/exams/{exam.id}/auto-fill", json={"count": 5})
    assert resp.status_code == 200
    qv_db.refresh(exam)
    qids = {eq.question_id for eq in exam.questions}
    assert visible.id in qids
    assert priv.id not in qids


# ---------------------------------------------------------------------------
# Visibility mutation ownership (TF-642 bugfix) — owner or SuperUser only,
# mirrors Document/TF-620's identical rule
# ---------------------------------------------------------------------------


def test_edit_question_visibility_rejects_non_owner(qv_db, qv_client):
    inst = make_institution(qv_db, "own1")
    creator = make_user(qv_db, inst.id, "own1creator")
    editor = make_user_with_role(qv_db, inst.id, "own1editor", ["edit_questions"])
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit", json={"visibility": "institution"}
    )
    assert resp.status_code == 403
    qv_db.refresh(q)
    assert q.visibility == QuestionReviewVisibility.PRIVATE


def test_edit_question_visibility_allows_superuser_for_others_question(
    qv_db, qv_client
):
    inst = make_institution(qv_db, "own2")
    creator = make_user(qv_db, inst.id, "own2creator")
    su = make_user(qv_db, inst.id, "own2su", is_superuser=True)
    q = make_question(
        qv_db,
        inst.id,
        created_by=creator.id,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.commit()
    login(qv_client, su)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit", json={"visibility": "institution"}
    )
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "institution"


def test_edit_question_superuser_can_set_team_visibility_without_own_membership(
    qv_db, qv_client
):
    """SuperUser bugfix: validating org_unit_id against the ACTING
    superuser's own membership would reject a legitimate re-tier of
    someone else's question, since a superuser typically isn't a member of
    the question's own Org-Unit at all."""
    inst = make_institution(qv_db, "sut1")
    ou = make_org_unit(qv_db, inst.id, "sut1")
    creator = make_user(qv_db, inst.id, "sut1creator")
    su = make_user(qv_db, inst.id, "sut1su", is_superuser=True)
    q = make_question(qv_db, inst.id, created_by=creator.id)
    qv_db.commit()
    login(qv_client, su)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 200
    assert resp.json()["org_unit_id"] == ou.id


def test_edit_question_institution_visibility_on_orphan_question_returns_400(
    qv_db, qv_client
):
    """Bugfix: an orphaned question (institution_id IS NULL, reachable by a
    SuperUser via _get_scoped_question's tenant-filter bypass) previously
    passed validation here and then tripped
    ck_question_reviews_institution_visibility_requires_institution on
    commit, surfacing as an opaque 500 through edit_question's broad
    except-Exception handler instead of a clear 400."""
    su_inst = make_institution(qv_db, "orph1")
    su = make_user(qv_db, su_inst.id, "orph1su", is_superuser=True)
    q = QuestionReview(
        question_text="Orphan?",
        question_type="open_ended",
        difficulty="easy",
        topic="orphan",
        review_status=ReviewStatus.PENDING.value,
        institution_id=None,
        created_by=None,
        visibility=QuestionReviewVisibility.PRIVATE,
    )
    qv_db.add(q)
    qv_db.commit()
    qv_db.refresh(q)
    login(qv_client, su)

    resp = qv_client.put(
        f"/api/v1/questions/{q.id}/edit", json={"visibility": "institution"}
    )
    assert resp.status_code == 400
    qv_db.refresh(q)
    assert q.visibility == QuestionReviewVisibility.PRIVATE


# ---------------------------------------------------------------------------
# Audit history — org_unit_id changes must be recorded independently of
# visibility (TF-642 bugfix)
# ---------------------------------------------------------------------------


def test_org_unit_id_only_change_gets_its_own_audit_entry(qv_db, qv_client):
    """Bugfix: moving a TEAM question between Org-Units with visibility
    unchanged previously still wrote
    {"visibility": {"old": "team", "new": "team"}} -- an entry that reads
    as 'nothing changed' while the accessible audience for the question
    actually did."""
    inst = make_institution(qv_db, "aud1")
    ou1 = make_org_unit(qv_db, inst.id, "aud1a")
    ou2 = make_org_unit(qv_db, inst.id, "aud1b")
    editor = make_user_with_role(qv_db, inst.id, "aud1editor", ["edit_questions"])
    add_membership(qv_db, editor.id, ou1.id)
    add_membership(qv_db, editor.id, ou2.id)
    q = make_question(
        qv_db,
        inst.id,
        created_by=editor.id,
        visibility=QuestionReviewVisibility.TEAM,
        org_unit_id=ou1.id,
    )
    qv_db.commit()
    login(qv_client, editor)

    resp = qv_client.put(f"/api/v1/questions/{q.id}/edit", json={"org_unit_id": ou2.id})
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "team"
    assert resp.json()["org_unit_id"] == ou2.id

    history = (
        qv_db.query(ReviewHistory)
        .filter_by(question_id=q.id, action="edited")
        .order_by(ReviewHistory.id.desc())
        .first()
    )
    assert history is not None
    assert "org_unit_id" in history.changed_fields
    assert history.changed_fields["org_unit_id"]["old"] == ou1.id
    assert history.changed_fields["org_unit_id"]["new"] == ou2.id
    # visibility itself didn't change -- must not claim it did.
    assert "visibility" not in history.changed_fields
