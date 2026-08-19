"""TF-644: Tests für CompetencyFramework-Sichtbarkeit (private/team/
institution) + Institutions-Admin-Bypass (``competencies:read_all``).

Scope-Grenze (siehe utils/competency_visibility.py Modul-Docstring +
/grilling-Entscheidungen TF-644): Sichtbarkeit gilt für Framework-Browsing
(``list_frameworks``/``get_framework``) UND — ohne den
``competencies:read_all``-Bypass — für jede Framework-Mutation (update/
archive/unarchive), da diese alle über ``_get_for_write`` laufen. Anders als
Exam/QuestionReview braucht ``update_framework`` KEINE separate
Owner-oder-SuperUser-Sonderrestriktion für Sichtbarkeits-Änderungen: der
Eintritt in ``update_framework``/``archive_framework``/``unarchive_framework``
ist bereits über ``_get_for_write`` (Owner ODER ``manage_settings``-Admin)
gegated — ein bereits vertrauenswürdiger Admin darf ein bereits sichtbares
Framework auch re-tieren (mit Org-Unit-Mitgliedschaftsprüfung wie jeder
andere, ausser SuperUser). Siehe test_manage_settings_admin_can_edit_*
unten für die (pre-existierende, unveränderte) Kehrseite: ein
``manage_settings``-Admin, der NICHT Ersteller ist, erreicht ein privates
Framework eines Kollegen weiterhin nicht — das war schon vor TF-644 so
(``_visible_query`` liess private, fremde Frameworks nie durch) und bleibt
unverändert (404 vor dem Owner-oder-Admin-Check).

Zusätzlich: DB-CHECK-Constraint-Regressionstests, ``delete_org_unit``-Block
bei team-sichtbarem Framework, und die generation-time
``resolve_competencies_text``-Lückenschliessung (/grilling-Entscheidung
TF-644 — vorher rein institutionsflach, ignorierte visibility komplett) lebt
in ``test_rag_competency_wiring.py`` (dort ist der Kontext/die bestehenden
Fixtures bereits vorhanden).
"""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from main import app
from models.auth import Institution, User, UserStatus, Role
from models.competency import CompetencyFramework, CompetencyFrameworkVisibility
from models.org_unit import OrgUnit, UserOrgUnit
from services.org_unit_service import delete_org_unit
from utils.auth_utils import get_current_user, get_current_active_user
from utils.competency_visibility import (
    filter_frameworks_for_user,
    is_framework_visible_for,
)
from database import get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def cv_db(test_engine):
    Session_ = sessionmaker(bind=test_engine)
    session = Session_()
    yield session
    session.close()


@pytest.fixture()
def cv_client(cv_db: Session):
    import api.competency_frameworks as cf_module

    app.include_router(cf_module.router)

    def override_get_db():
        yield cv_db

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_institution(db, suffix="cv"):
    inst = Institution(
        name=f"CV Uni {suffix}",
        slug=f"cv-uni-{suffix}",
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
        email=f"cvuser{suffix}@test.com",
        first_name="CV",
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

    Rollenname mit ``tf644-`` genamespaced — ``Role.name`` ist global unique
    (CI-Gotcha, siehe TF-640-Nachlese), Kollision mit anderen Testdateien
    vermeiden.
    """
    user = make_user(db, institution_id, suffix)
    role = Role(
        name=f"tf644-role-{suffix}",
        display_name=f"TF-644 Role {suffix}",
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


def make_framework(
    db,
    institution_id,
    created_by=None,
    visibility=CompetencyFrameworkVisibility.INSTITUTION,
    org_unit_id=None,
    is_archived=False,
    suffix="f",
):
    fw = CompetencyFramework(
        name=f"CV Framework {suffix}",
        module_code="B",
        rendered_text="# HKB Text",
        language="de",
        institution_id=institution_id,
        created_by=created_by,
        visibility=visibility,
        org_unit_id=org_unit_id,
        is_archived=is_archived,
    )
    db.add(fw)
    db.flush()
    return fw


def login(client, user):
    """Override beide Auth-Dependencies auf denselben User."""
    client.app.dependency_overrides[get_current_user] = lambda: user
    client.app.dependency_overrides[get_current_active_user] = lambda: user


# ---------------------------------------------------------------------------
# filter_frameworks_for_user / is_framework_visible_for — unit level
# ---------------------------------------------------------------------------


def test_filter_private_visible_only_to_creator(cv_db):
    inst = make_institution(cv_db, "p1")
    creator = make_user(cv_db, inst.id, "p1a")
    colleague = make_user(cv_db, inst.id, "p1b")
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()

    visible_to_creator = filter_frameworks_for_user(
        cv_db.query(CompetencyFramework), creator, cv_db
    ).all()
    visible_to_colleague = filter_frameworks_for_user(
        cv_db.query(CompetencyFramework), colleague, cv_db
    ).all()

    assert fw in visible_to_creator
    assert fw not in visible_to_colleague


def test_filter_institution_visible_to_institution_members_only(cv_db):
    inst = make_institution(cv_db, "i1")
    creator = make_user(cv_db, inst.id, "i1a")
    colleague = make_user(cv_db, inst.id, "i1b")
    outsider_inst = make_institution(cv_db, "i2")
    outsider = make_user(cv_db, outsider_inst.id, "i2a")
    fw = make_framework(cv_db, inst.id, created_by=creator.id)
    cv_db.commit()

    assert (
        fw
        in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), colleague, cv_db
        ).all()
    )
    assert (
        fw
        not in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), outsider, cv_db
        ).all()
    )


def test_filter_team_visible_to_org_unit_members_only(cv_db):
    inst = make_institution(cv_db, "t1")
    ou = make_org_unit(cv_db, inst.id, "t1")
    other_ou = make_org_unit(cv_db, inst.id, "t1-other")
    creator = make_user(cv_db, inst.id, "t1a")
    teammate = make_user(cv_db, inst.id, "t1b")
    other_team_member = make_user(cv_db, inst.id, "t1c")
    add_membership(cv_db, creator.id, ou.id)
    add_membership(cv_db, teammate.id, ou.id)
    add_membership(cv_db, other_team_member.id, other_ou.id)
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=ou.id,
    )
    cv_db.commit()

    assert (
        fw
        in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), teammate, cv_db
        ).all()
    )
    assert (
        fw
        not in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), other_team_member, cv_db
        ).all()
    )


def test_filter_team_visible_to_ancestor_org_unit_member(cv_db):
    """get_user_accessible_org_unit_ids is the union of DESCENDANT sets for
    every OrgUnit the user directly belongs to — a member of the parent
    Abteilung must see a framework scoped to a child team."""
    inst = make_institution(cv_db, "anc1")
    parent = make_org_unit(cv_db, inst.id, "anc1parent")
    child = make_org_unit(cv_db, inst.id, "anc1child", parent_org_unit_id=parent.id)
    creator = make_user(cv_db, inst.id, "anc1creator")
    ancestor_member = make_user(cv_db, inst.id, "anc1ancestor")
    add_membership(cv_db, ancestor_member.id, parent.id)
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=child.id,
    )
    cv_db.commit()

    assert (
        fw
        in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), ancestor_member, cv_db
        ).all()
    )
    assert is_framework_visible_for(ancestor_member, fw, cv_db) is True


def test_filter_team_not_visible_to_sibling_org_unit_member(cv_db):
    inst = make_institution(cv_db, "sib1")
    parent = make_org_unit(cv_db, inst.id, "sib1parent")
    child_a = make_org_unit(cv_db, inst.id, "sib1a", parent_org_unit_id=parent.id)
    child_b = make_org_unit(cv_db, inst.id, "sib1b", parent_org_unit_id=parent.id)
    creator = make_user(cv_db, inst.id, "sib1creator")
    sibling_member = make_user(cv_db, inst.id, "sib1sibling")
    add_membership(cv_db, sibling_member.id, child_b.id)
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=child_a.id,
    )
    cv_db.commit()

    assert (
        fw
        not in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), sibling_member, cv_db
        ).all()
    )
    assert is_framework_visible_for(sibling_member, fw, cv_db) is False


def test_filter_team_requires_institution_match_even_with_org_unit_membership(cv_db):
    """Bugfix-mirror (see exam_visibility's identical test): a framework
    whose org_unit_id and institution_id have drifted apart must not leak to
    Org-Unit members of the OTHER institution — Org-Unit membership alone is
    not sufficient without an institution_id match."""
    inst_a = make_institution(cv_db, "ig1a")
    inst_b = make_institution(cv_db, "ig1b")
    ou = make_org_unit(cv_db, inst_a.id, "ig1")
    member = make_user(cv_db, inst_a.id, "ig1member")
    add_membership(cv_db, member.id, ou.id)
    drifted = make_framework(
        cv_db,
        inst_b.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=ou.id,
    )
    cv_db.commit()

    assert (
        drifted
        not in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), member, cv_db
        ).all()
    )
    assert is_framework_visible_for(member, drifted, cv_db) is False


def test_filter_read_all_bypass_sees_private_and_team_within_institution(cv_db):
    inst = make_institution(cv_db, "r1")
    ou = make_org_unit(cv_db, inst.id, "r1")
    creator = make_user(cv_db, inst.id, "r1a")
    admin = make_user_with_role(cv_db, inst.id, "r1admin", ["competencies:read_all"])
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
        suffix="r1priv",
    )
    team = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=ou.id,
        suffix="r1team",
    )
    cv_db.commit()

    visible = filter_frameworks_for_user(
        cv_db.query(CompetencyFramework), admin, cv_db
    ).all()
    assert priv in visible
    # admin is not a member of `ou` — only the bypass grants this.
    assert team in visible


def test_filter_read_all_bypass_never_crosses_institutions(cv_db):
    inst1 = make_institution(cv_db, "x1")
    inst2 = make_institution(cv_db, "x2")
    admin = make_user_with_role(cv_db, inst1.id, "x1admin", ["competencies:read_all"])
    foreign = make_framework(cv_db, inst2.id)
    cv_db.commit()

    assert (
        foreign
        not in filter_frameworks_for_user(
            cv_db.query(CompetencyFramework), admin, cv_db
        ).all()
    )


def test_filter_superuser_bypasses_entirely(cv_db):
    inst = make_institution(cv_db, "s1")
    su = make_user(cv_db, inst.id, "s1su", is_superuser=True)
    fw = make_framework(
        cv_db, inst.id, visibility=CompetencyFrameworkVisibility.PRIVATE
    )
    cv_db.commit()

    assert (
        fw
        in filter_frameworks_for_user(cv_db.query(CompetencyFramework), su, cv_db).all()
    )


def test_is_framework_visible_for_matches_filter(cv_db):
    inst = make_institution(cv_db, "m1")
    creator = make_user(cv_db, inst.id, "m1a")
    colleague = make_user(cv_db, inst.id, "m1b")
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()

    assert is_framework_visible_for(creator, fw, cv_db) is True
    assert is_framework_visible_for(colleague, fw, cv_db) is False


# ---------------------------------------------------------------------------
# Wired: Framework-Liste + Detail (HTTP) — list_frameworks / get_framework
# ---------------------------------------------------------------------------


def test_list_frameworks_hides_colleague_private_framework(cv_db, cv_client):
    inst = make_institution(cv_db, "l1")
    creator = make_user(cv_db, inst.id, "l1a")
    viewer = make_user_with_role(cv_db, inst.id, "l1b", ["create_questions"])
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    visible_fw = make_framework(cv_db, inst.id, created_by=creator.id, suffix="pub")
    cv_db.commit()
    login(cv_client, viewer)

    resp = cv_client.get("/api/v1/competency-frameworks")
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()]
    assert priv.id not in ids
    assert visible_fw.id in ids


def test_list_frameworks_read_all_admin_sees_private(cv_db, cv_client):
    inst = make_institution(cv_db, "l2")
    creator = make_user(cv_db, inst.id, "l2a")
    admin = make_user_with_role(cv_db, inst.id, "l2admin", ["competencies:read_all"])
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, admin)

    resp = cv_client.get("/api/v1/competency-frameworks")
    assert resp.status_code == 200
    ids = [f["id"] for f in resp.json()]
    assert priv.id in ids


def test_get_framework_hides_colleague_private_framework_with_404(cv_db, cv_client):
    inst = make_institution(cv_db, "g1")
    creator = make_user(cv_db, inst.id, "g1a")
    viewer = make_user_with_role(cv_db, inst.id, "g1b", ["create_questions"])
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, viewer)

    resp = cv_client.get(f"/api/v1/competency-frameworks/{priv.id}")
    assert resp.status_code == 404


def test_get_framework_read_all_admin_sees_private(cv_db, cv_client):
    inst = make_institution(cv_db, "g2")
    creator = make_user(cv_db, inst.id, "g2a")
    admin = make_user_with_role(cv_db, inst.id, "g2admin", ["competencies:read_all"])
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, admin)

    resp = cv_client.get(f"/api/v1/competency-frameworks/{priv.id}")
    assert resp.status_code == 200
    assert resp.json()["visibility"] == "private"


# ---------------------------------------------------------------------------
# Mutation gate: allow_read_all_bypass=False + pre-existing owner-or-admin
# ---------------------------------------------------------------------------


def test_read_all_admin_alone_cannot_reach_others_private_framework_for_write(
    cv_db, cv_client
):
    """ADR-0004: ``competencies:read_all`` stays strictly read-only — an
    admin holding ONLY that permission (no ``manage_settings``, not the
    owner) gets 404 on PUT, mirroring GET (never 403 — a 403 would leak the
    row's existence to someone who must not see it)."""
    inst = make_institution(cv_db, "w1")
    creator = make_user(cv_db, inst.id, "w1a")
    admin = make_user_with_role(
        cv_db, inst.id, "w1admin", ["competencies:read_all", "create_questions"]
    )
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, admin)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{priv.id}", json={"name": "Hijacked"}
    )
    assert resp.status_code == 404


def test_manage_settings_admin_can_edit_others_institution_visible_framework(
    cv_db, cv_client
):
    """Pre-existing behaviour (unchanged by TF-644): a ``manage_settings``
    admin may edit ANY institution-visible framework, not just their own —
    ``_get_for_write``'s is_admin bypass applies once the framework is
    already visible."""
    inst = make_institution(cv_db, "w2")
    creator = make_user(cv_db, inst.id, "w2a")
    # create_questions is the endpoint's own require_permission gate;
    # manage_settings is what actually grants the cross-owner bypass inside
    # _get_for_write.
    admin = make_user_with_role(
        cv_db, inst.id, "w2admin", ["manage_settings", "create_questions"]
    )
    fw = make_framework(cv_db, inst.id, created_by=creator.id)
    cv_db.commit()
    login(cv_client, admin)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}", json={"name": "Renamed by Admin"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed by Admin"


def test_manage_settings_admin_still_cannot_reach_others_private_framework(
    cv_db, cv_client
):
    """Pre-existing behaviour (unchanged by TF-644, see module docstring):
    _get_for_write's owner-or-manage_settings-admin gate only decides what
    an ALREADY VISIBLE framework may do — a colleague's PRIVATE framework
    was never visible to a non-owner, admin or not, before or after
    TF-644."""
    inst = make_institution(cv_db, "w3")
    creator = make_user(cv_db, inst.id, "w3a")
    admin = make_user_with_role(
        cv_db, inst.id, "w3admin", ["manage_settings", "create_questions"]
    )
    priv = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, admin)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{priv.id}", json={"name": "Hijacked"}
    )
    assert resp.status_code == 404


def test_colleague_without_admin_cannot_edit_institution_visible_framework(
    cv_db, cv_client
):
    inst = make_institution(cv_db, "w4")
    creator = make_user(cv_db, inst.id, "w4a")
    colleague = make_user_with_role(cv_db, inst.id, "w4b", ["create_questions"])
    fw = make_framework(cv_db, inst.id, created_by=creator.id)
    cv_db.commit()
    login(cv_client, colleague)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}", json={"name": "Hijacked"}
    )
    assert resp.status_code == 403


# --- Bypass-exclusion across every _get_for_write-gated mutation endpoint
# (PR #194 review: only PUT had a dedicated test before, mirrors
# TF-643's test_read_all_bypass_excluded_from_every_mutation_endpoint) ------

_MUTATION_ENDPOINTS = [
    ("PUT", "/api/v1/competency-frameworks/{id}", {"name": "Hijacked"}),
    ("POST", "/api/v1/competency-frameworks/{id}/archive", None),
    ("POST", "/api/v1/competency-frameworks/{id}/unarchive", None),
]


@pytest.mark.parametrize(
    "idx,method,path_template,body",
    [(i, m, p, b) for i, (m, p, b) in enumerate(_MUTATION_ENDPOINTS)],
    ids=[f"{m} {p}" for m, p, _ in _MUTATION_ENDPOINTS],
)
def test_read_all_bypass_excluded_from_every_mutation_endpoint(
    cv_db, cv_client, idx, method, path_template, body
):
    """Every one of update/archive/unarchive runs through ``_get_for_write``
    with ``allow_read_all_bypass=False`` — each must actually deny a
    same-institution ``competencies:read_all`` admin on another user's
    PRIVATE framework (404, not the permission-layer 403 and not success).
    Only PUT was covered before this PR
    (``test_read_all_admin_alone_cannot_reach_others_private_framework_for_
    write``); archive/unarchive shared the exact same gate but had zero
    coverage — a refactor swapping ``_get_for_write`` for an unguarded
    lookup on either route would have passed the suite unnoticed.

    ``idx`` namespaces every fixture per parametrize case — institution/role
    names must stay unique across the 3 cases within this single test run.
    """
    suffix = f"byp{idx}"
    inst = make_institution(cv_db, suffix)
    creator = make_user(cv_db, inst.id, f"{suffix}creator")
    admin = make_user_with_role(
        cv_db,
        inst.id,
        f"{suffix}admin",
        ["competencies:read_all", "create_questions"],
    )
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
        suffix=suffix,
    )
    cv_db.commit()
    login(cv_client, admin)

    path = path_template.format(id=fw.id)
    kwargs = {"json": body} if body is not None else {}
    resp = cv_client.request(method, path, **kwargs)

    assert resp.status_code == 404, (
        f"{method} {path} leaked the read-all bypass into a mutation: "
        f"expected 404, got {resp.status_code} ({resp.text[:200]})"
    )


# --- Institution-drift boundary: require_same_institution=True -------------
#
# is_framework_visible_for's creator branch alone doesn't imply institution
# match — unlike the read-all-bypass/TEAM/INSTITUTION branches. Without
# require_same_institution, a framework creator whose user.institution_id
# has drifted from framework.institution_id (e.g. an institution transfer
# that intentionally left frameworks behind) would keep full mutation rights
# on a framework that now belongs to a different institution. Reads must
# stay permissive across the drift (mirrors Document/Question/Exam);
# mutations must not. Mirrors TF-643's
# test_creator_institution_drift_can_still_read_but_not_mutate.


def test_creator_institution_drift_can_still_read_but_not_mutate(cv_db, cv_client):
    inst_a = make_institution(cv_db, "drift1a")
    inst_b = make_institution(cv_db, "drift1b")
    creator = make_user_with_role(cv_db, inst_a.id, "drift1", ["create_questions"])
    fw = make_framework(
        cv_db,
        inst_b.id,
        created_by=creator.id,
        visibility=CompetencyFrameworkVisibility.PRIVATE,
    )
    cv_db.commit()
    login(cv_client, creator)

    # Read stays permissive across the drift.
    resp = cv_client.get(f"/api/v1/competency-frameworks/{fw.id}")
    assert resp.status_code == 200

    # Mutation must not — this is the fix require_same_institution=True buys.
    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}", json={"name": "Hijacked"}
    )
    assert resp.status_code == 404
    cv_db.refresh(fw)
    assert fw.name != "Hijacked"

    # Archive/unarchive go through the identical gate.
    resp = cv_client.post(f"/api/v1/competency-frameworks/{fw.id}/archive")
    assert resp.status_code == 404
    cv_db.refresh(fw)
    assert fw.is_archived is False


# ---------------------------------------------------------------------------
# create_framework — visibility/org_unit_id validation
# ---------------------------------------------------------------------------


def test_create_framework_defaults_to_institution_visibility(cv_db, cv_client):
    inst = make_institution(cv_db, "c1")
    creator = make_user_with_role(cv_db, inst.id, "c1a", ["create_questions"])
    login(cv_client, creator)

    resp = cv_client.post(
        "/api/v1/competency-frameworks",
        json={"name": "New Framework", "rendered_text": "# HKB"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "institution"
    assert body["org_unit_id"] is None


def test_create_framework_with_team_visibility(cv_db, cv_client):
    inst = make_institution(cv_db, "c2")
    ou = make_org_unit(cv_db, inst.id, "c2")
    creator = make_user_with_role(cv_db, inst.id, "c2a", ["create_questions"])
    add_membership(cv_db, creator.id, ou.id)
    cv_db.commit()
    login(cv_client, creator)

    resp = cv_client.post(
        "/api/v1/competency-frameworks",
        json={
            "name": "Team Framework",
            "rendered_text": "# HKB",
            "visibility": "team",
            "org_unit_id": ou.id,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_create_framework_team_visibility_requires_org_unit(cv_db, cv_client):
    inst = make_institution(cv_db, "c3")
    creator = make_user_with_role(cv_db, inst.id, "c3a", ["create_questions"])
    login(cv_client, creator)

    resp = cv_client.post(
        "/api/v1/competency-frameworks",
        json={"name": "Bad Team", "rendered_text": "# HKB", "visibility": "team"},
    )
    assert resp.status_code == 400


# NOTE: no HTTP-level test for _resolve_framework_visibility_for_create's
# "visibility=INSTITUTION and user.institution_id is None → 400" branch — CI
# caught that it's actually unreachable via the API: models/auth.py's
# ``User.institution_id`` column is ``nullable=False``, so no committable
# User can ever have ``institution_id is None`` in the first place (unlike
# CompetencyFramework.institution_id, which IS nullable — see the update-
# path test below, which exercises the framework-side branch of this same
# guard via a SuperUser actor instead). The branch is defensive-only dead
# code with respect to this specific check; left in place (mirrors
# question_review's analogous orphan guard) rather than removed, since a
# future relaxation of the NOT NULL constraint would silently reopen it.


def test_create_framework_team_visibility_requires_own_org_unit_membership(
    cv_db, cv_client
):
    inst = make_institution(cv_db, "c4")
    ou = make_org_unit(cv_db, inst.id, "c4")
    creator = make_user_with_role(cv_db, inst.id, "c4a", ["create_questions"])
    cv_db.commit()  # creator is NOT a member of ou
    login(cv_client, creator)

    resp = cv_client.post(
        "/api/v1/competency-frameworks",
        json={
            "name": "Foreign Team",
            "rendered_text": "# HKB",
            "visibility": "team",
            "org_unit_id": ou.id,
        },
    )
    assert resp.status_code == 400


def test_create_framework_team_visibility_allows_superuser_without_membership(
    cv_db, cv_client
):
    inst = make_institution(cv_db, "su1")
    ou = make_org_unit(cv_db, inst.id, "su1")
    su = make_user(cv_db, inst.id, "su1su", is_superuser=True)
    cv_db.commit()  # su is NOT a member of ou
    login(cv_client, su)

    resp = cv_client.post(
        "/api/v1/competency-frameworks",
        json={
            "name": "SU Team Framework",
            "rendered_text": "# HKB",
            "visibility": "team",
            "org_unit_id": ou.id,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


# ---------------------------------------------------------------------------
# update_framework — visibility/org_unit_id validation
# ---------------------------------------------------------------------------


def test_update_framework_changes_to_team_visibility(cv_db, cv_client):
    inst = make_institution(cv_db, "u1")
    ou = make_org_unit(cv_db, inst.id, "u1")
    owner = make_user_with_role(cv_db, inst.id, "u1a", ["create_questions"])
    add_membership(cv_db, owner.id, ou.id)
    fw = make_framework(cv_db, inst.id, created_by=owner.id)
    cv_db.commit()
    login(cv_client, owner)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_update_framework_rejects_team_visibility_without_membership(cv_db, cv_client):
    inst = make_institution(cv_db, "u2")
    ou = make_org_unit(cv_db, inst.id, "u2")
    owner = make_user_with_role(cv_db, inst.id, "u2a", ["create_questions"])
    fw = make_framework(cv_db, inst.id, created_by=owner.id)
    cv_db.commit()  # owner is NOT a member of ou
    login(cv_client, owner)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 400


def test_update_framework_allows_superuser_without_membership(cv_db, cv_client):
    """Mirrors ``test_create_framework_team_visibility_allows_superuser_
    without_membership`` — the identical ``if not user.is_superuser`` guard
    exists in ``_resolve_framework_visibility_update``, but was untested on
    the update path before this. A SuperUser typically has no Org-Unit
    memberships of their own and may re-tier a framework on behalf of its
    actual owners regardless. ``_get_for_write``'s ownership gate also
    passes for a SuperUser independently (``has_permission`` short-circuits
    True), so this exercises the update-specific bypass in isolation from
    that."""
    inst = make_institution(cv_db, "su2")
    ou = make_org_unit(cv_db, inst.id, "su2")
    owner = make_user(cv_db, inst.id, "su2owner")
    fw = make_framework(cv_db, inst.id, created_by=owner.id)
    su = make_user(cv_db, inst.id, "su2su", is_superuser=True)
    cv_db.commit()  # su is NOT a member of ou
    login(cv_client, su)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "team", "org_unit_id": ou.id},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id


def test_update_framework_clears_org_unit_id_when_leaving_team(cv_db, cv_client):
    inst = make_institution(cv_db, "u3")
    ou = make_org_unit(cv_db, inst.id, "u3")
    owner = make_user_with_role(cv_db, inst.id, "u3a", ["create_questions"])
    add_membership(cv_db, owner.id, ou.id)
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=owner.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=ou.id,
    )
    cv_db.commit()
    login(cv_client, owner)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "institution"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "institution"
    assert body["org_unit_id"] is None


def test_update_framework_institution_visibility_requires_institution(cv_db, cv_client):
    """HTTP-level counterpart to ``test_db_check_constraint_blocks_
    institution_visibility_without_institution`` (which only exercises the
    DB CHECK by bypassing the API): ``_resolve_framework_visibility_update``
    must reject re-tiering an orphaned (``institution_id IS NULL``)
    framework to ``institution`` with a clear 400, not let it reach
    ``_commit_or_conflict``'s opaque 500 on the CHECK constraint.

    Actor MUST be a SuperUser: an orphaned framework's own creator can never
    reach it via ``_get_for_write`` in the first place — ``require_same_
    institution=True`` demands ``framework.institution_id == user.
    institution_id``, and since ``User.institution_id`` is ``NOT NULL``
    (unlike ``CompetencyFramework.institution_id``), ``None`` can never equal
    a real user's institution. Only ``is_framework_visible_for``'s SuperUser
    short-circuit (checked before that comparison) can reach an orphaned
    framework's mutation gate at all — so this test doubles as the one place
    confirming a SuperUser still can't bypass *this particular* business
    rule, unlike the org-unit-membership check they otherwise skip."""
    inst = make_institution(cv_db, "noinst2")
    su = make_user(cv_db, inst.id, "noinst2su", is_superuser=True)
    fw = make_framework(cv_db, None, visibility=CompetencyFrameworkVisibility.PRIVATE)
    cv_db.commit()
    login(cv_client, su)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "institution"},
    )
    assert resp.status_code == 400


def test_update_framework_sending_unchanged_visibility_is_not_reevaluated(
    cv_db, cv_client
):
    """No-op detection: re-sending the current visibility (without
    org_unit_id, and without being a member of the framework's team) must
    not spuriously 400 — mirrors exams' identical no-op guard."""
    inst = make_institution(cv_db, "u4")
    ou = make_org_unit(cv_db, inst.id, "u4")
    owner = make_user_with_role(cv_db, inst.id, "u4a", ["create_questions"])
    fw = make_framework(
        cv_db,
        inst.id,
        created_by=owner.id,
        visibility=CompetencyFrameworkVisibility.TEAM,
        org_unit_id=ou.id,
    )
    cv_db.commit()  # owner not (any longer) a member of ou
    login(cv_client, owner)

    resp = cv_client.put(
        f"/api/v1/competency-frameworks/{fw.id}",
        json={"visibility": "team", "name": "Renamed Only"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["visibility"] == "team"
    assert body["org_unit_id"] == ou.id
    assert body["name"] == "Renamed Only"


# ---------------------------------------------------------------------------
# delete_org_unit — blocked by team-visible framework
# ---------------------------------------------------------------------------


def test_delete_org_unit_blocked_by_team_visible_framework(cv_db):
    """``match=`` alone can't distinguish the dedicated ``competency``-branch
    message from the generic 5-resource fallback (both contain
    "Kompetenz-Frameworks" as a substring) — assert the *other* named
    resources are absent too, so a broken ``constraint_name`` sniff in
    ``org_unit_service.delete_org_unit`` (falling through to the generic
    branch instead of the specific one) can't pass silently. Mirrors
    TF-643's PR #193 review-hardened version of this test."""
    inst = make_institution(cv_db, "d1")
    ou = make_org_unit(cv_db, inst.id, "d1")
    make_framework(
        cv_db, inst.id, visibility=CompetencyFrameworkVisibility.TEAM, org_unit_id=ou.id
    )
    cv_db.commit()

    with pytest.raises(ValueError, match="Kompetenz-Frameworks") as exc_info:
        delete_org_unit(cv_db, ou)
    assert "Dokumente" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# DB CHECK constraints — regression tests
# ---------------------------------------------------------------------------


def test_db_check_constraint_blocks_team_visibility_without_org_unit(cv_db):
    inst = make_institution(cv_db, "chk1")
    cv_db.commit()
    cv_db.add(
        CompetencyFramework(
            name="Bad",
            rendered_text="x",
            institution_id=inst.id,
            visibility=CompetencyFrameworkVisibility.TEAM,
            org_unit_id=None,
        )
    )
    with pytest.raises(IntegrityError):
        cv_db.commit()
    cv_db.rollback()


def test_db_check_constraint_blocks_org_unit_without_team_visibility(cv_db):
    inst = make_institution(cv_db, "chk2")
    ou = make_org_unit(cv_db, inst.id, "chk2")
    cv_db.commit()
    cv_db.add(
        CompetencyFramework(
            name="Bad",
            rendered_text="x",
            institution_id=inst.id,
            visibility=CompetencyFrameworkVisibility.INSTITUTION,
            org_unit_id=ou.id,
        )
    )
    with pytest.raises(IntegrityError):
        cv_db.commit()
    cv_db.rollback()


def test_db_check_constraint_blocks_institution_visibility_without_institution(cv_db):
    cv_db.add(
        CompetencyFramework(
            name="Orphan",
            rendered_text="x",
            institution_id=None,
            visibility=CompetencyFrameworkVisibility.INSTITUTION,
        )
    )
    with pytest.raises(IntegrityError):
        cv_db.commit()
    cv_db.rollback()
