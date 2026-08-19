"""Tests für die Kompetenz-Auflösung im Generierungs-Request (TF-400).

TF-644: ``resolve_competencies_text`` nimmt seither ``user`` statt
``institution_id`` entgegen und prüft zusätzlich ``is_framework_visible_for``
— schliesst die vorbestehende Lücke, dass jedes institutionsweite Framework
(auch private/team-gescopte anderer User) per direkt gesetztem
``framework_id`` wählbar war. Siehe ``test_private_framework_of_other_user_
not_resolvable``/``test_team_framework_resolvable_for_member_not_for_
outsider`` unten sowie ``utils/competency_visibility.py``'s Modul-Docstring.

PR #194 review follow-up: ``resolve_framework_for_user`` — the shared
resolver ``resolve_competencies_text`` now delegates to — is tested
separately below (``Test*ResolveFrameworkForUser`` section), mirroring the
same allow/deny matrix. This closes the gap where ``generate_rag_exam``
passed the raw, unchecked ``request.framework_id`` into
``tasks.question_tasks._persist_questions`` (whose ``Competency`` lookup has
no institution/visibility filter of its own) even though the *text* was
already correctly withheld — an invisible/cross-tenant framework's id could
still reach competency-code tagging on the persisted question.
"""

import json

from models.auth import Institution, Role, User, UserStatus
from api.rag_exams import resolve_competencies_text, resolve_framework_for_user


def _inst(test_db, suffix="wire"):
    inst = Institution(
        name=f"Wire Inst {suffix}",
        slug=f"wire-inst-{suffix}",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()
    return inst


def _user(test_db, institution_id, suffix="wire"):
    user = User(
        email=f"wireuser{suffix}@test.com",
        first_name="Wire",
        last_name=f"User{suffix}",
        password_hash="dummy_hash",  # pragma: allowlist secret
        institution_id=institution_id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()
    return user


def _admin_with_read_all(test_db, institution_id, suffix="wireadmin"):
    """User holding ``competencies:read_all`` (Institutions-Admin-Bypass,
    TF-639) but no other relation to the framework under test."""
    user = _user(test_db, institution_id, suffix=suffix)
    role = Role(
        name=f"tf644-wire-role-{suffix}",
        display_name=f"TF-644 Wire Role {suffix}",
        permissions=json.dumps(["competencies:read_all"]),
    )
    test_db.add(role)
    test_db.flush()
    user.roles.append(role)
    test_db.flush()
    return user


def _fw(test_db, rendered="# HKB B\n### B1 ...", inst=None, **kwargs):
    from models.competency import CompetencyFramework

    if inst is None:
        inst = _inst(test_db)
    fw = CompetencyFramework(
        name="Modul B",
        module_code="B",
        rendered_text=rendered,
        institution_id=inst.id,
        visibility=kwargs.pop("visibility", "institution"),
        **kwargs,
    )
    test_db.add(fw)
    test_db.commit()
    test_db.refresh(fw)
    return fw, inst


def test_override_wins_over_framework(test_db):
    fw, inst = _fw(test_db)
    user = _user(test_db, inst.id)
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override="NUR DIES",
        user=user,
    )
    assert out == "NUR DIES"


def test_framework_rendered_text_used(test_db):
    fw, inst = _fw(test_db, rendered="VOLLTEXT HKB")
    user = _user(test_db, inst.id)
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override=None,
        user=user,
    )
    assert out == "VOLLTEXT HKB"


def test_none_when_no_framework_and_no_override(test_db):
    inst = _inst(test_db)
    user = _user(test_db, inst.id)
    out = resolve_competencies_text(
        test_db,
        framework_id=None,
        override=None,
        user=user,
    )
    assert out is None


def test_framework_other_institution_not_leaked(test_db):
    fw, inst = _fw(test_db)
    other_inst = _inst(test_db, suffix="other")
    user = _user(test_db, other_inst.id, suffix="other")
    out = resolve_competencies_text(
        test_db,
        framework_id=fw.id,
        override=None,
        user=user,
    )
    assert out is None  # cross-institution → not found → None


def test_archived_framework_not_resolved(test_db):
    """Ein archiviertes Framework wird nicht mehr in den Prompt injiziert."""
    fw, inst = _fw(test_db, rendered="ARCHIVIERT")
    fw.is_archived = True
    test_db.commit()
    user = _user(test_db, inst.id)
    out = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=user
    )
    assert out is None


def test_requested_but_missing_framework_logs_warning(test_db):
    """Ein explizit gewähltes, aber nicht auflösbares framework_id (fremde
    Institution / archiviert / gelöscht / nicht sichtbar) wird geloggt —
    sonst bliebe das stille Ausbleiben der Kompetenz-Injektion unauffindbar.
    Modul-Logger gepatcht statt caplog (das in der Gesamt-Suite je nach
    Logging-Konfig nichts fängt)."""
    from unittest.mock import patch

    import api.rag_exams as rag_exams_mod

    fw, inst = _fw(test_db)
    other_inst = _inst(test_db, suffix="missing")
    user = _user(test_db, other_inst.id, suffix="missing")  # fremde Institution
    with patch.object(rag_exams_mod.logger, "warning") as warn:
        out = resolve_competencies_text(
            test_db,
            framework_id=fw.id,
            override=None,
            user=user,
        )
    assert out is None
    logged = " ".join(str(a) for call in warn.call_args_list for a in call.args)
    assert "resolve_competencies_text" in logged
    assert str(fw.id) in logged


def test_private_framework_of_other_user_not_resolvable(test_db):
    """TF-644: schliesst die vorbestehende Lücke — vor TF-644 war jedes
    institutionsweite Framework per framework_id wählbar, auch ein privates
    eines anderen Users; das Frontend-Dropdown ist ``list_frameworks``-
    gefiltert, aber die API selbst prüfte bislang nichts."""
    inst = _inst(test_db)
    owner = _user(test_db, inst.id, suffix="owner")
    colleague = _user(test_db, inst.id, suffix="colleague")
    fw, _ = _fw(
        test_db,
        rendered="PRIVAT",
        inst=inst,
        visibility="private",
        created_by=owner.id,
    )

    out_for_owner = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=owner
    )
    out_for_colleague = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=colleague
    )

    assert out_for_owner == "PRIVAT"
    assert out_for_colleague is None


def test_read_all_admin_can_resolve_colleagues_private_framework(test_db):
    """PR #194 review follow-up: unlike ``_get_for_write`` (mutation, always
    ``allow_read_all_bypass=False``), ``resolve_competencies_text`` calls
    ``is_framework_visible_for`` with the default ``allow_read_all_bypass=
    True`` — deliberate, not an oversight (see ``utils.competency_
    visibility``'s module docstring): generation is a read action, so a
    same-institution ``competencies:read_all`` admin may select a
    colleague's PRIVATE framework for exam generation, same as they may
    browse it via ``list_frameworks``/``get_framework``. This was previously
    untested."""
    inst = _inst(test_db)
    owner = _user(test_db, inst.id, suffix="rabowner")
    admin = _admin_with_read_all(test_db, inst.id, suffix="rabadmin")
    fw, _ = _fw(
        test_db,
        rendered="PRIVAT",
        inst=inst,
        visibility="private",
        created_by=owner.id,
    )

    out_for_admin = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=admin
    )

    assert out_for_admin == "PRIVAT"


def test_team_framework_resolvable_for_member_not_for_outsider(test_db):
    """TF-644: ein team-sichtbares Framework ist für Org-Unit-Mitglieder
    generierungs-auflösbar, für Institutionsmitglieder ausserhalb des Teams
    nicht."""
    from models.org_unit import OrgUnit, UserOrgUnit

    inst = _inst(test_db)
    ou = OrgUnit(institution_id=inst.id, unit_type="team", name="Team A")
    test_db.add(ou)
    test_db.flush()
    member = _user(test_db, inst.id, suffix="member")
    outsider = _user(test_db, inst.id, suffix="outsider")
    test_db.add(UserOrgUnit(user_id=member.id, org_unit_id=ou.id))
    test_db.flush()
    fw, _ = _fw(
        test_db,
        rendered="TEAM TEXT",
        inst=inst,
        visibility="team",
        org_unit_id=ou.id,
    )

    out_for_member = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=member
    )
    out_for_outsider = resolve_competencies_text(
        test_db, framework_id=fw.id, override=None, user=outsider
    )

    assert out_for_member == "TEAM TEXT"
    assert out_for_outsider is None


# ---------------------------------------------------------------------------
# resolve_framework_for_user — PR #194 review follow-up
#
# Mirrors the resolve_competencies_text matrix above one-to-one: the same
# framework_id that resolve_competencies_text withholds the *text* for must
# also resolve to None here, since generate_rag_exam now persists THIS
# function's result (not the raw request.framework_id) as the framework_id
# tagged onto generated questions in tasks.question_tasks._persist_questions.
# ---------------------------------------------------------------------------


def test_resolve_framework_for_user_none_when_no_framework_id(test_db):
    inst = _inst(test_db)
    user = _user(test_db, inst.id)
    assert resolve_framework_for_user(test_db, None, user) is None


def test_resolve_framework_for_user_returns_institution_visible_framework(test_db):
    """Baseline allow case: any institution member, not just the creator,
    can resolve the default (INSTITUTION-visibility) framework."""
    fw, inst = _fw(test_db)
    user = _user(test_db, inst.id)
    resolved = resolve_framework_for_user(test_db, fw.id, user)
    assert resolved is not None
    assert resolved.id == fw.id


def test_resolve_framework_for_user_none_for_other_institution(test_db):
    """The bug this closes: without this check, an attacker-chosen
    cross-institution framework_id reached _persist_questions'
    institution-unfiltered Competency lookup unchanged."""
    fw, inst = _fw(test_db)
    other_inst = _inst(test_db, suffix="fwother")
    user = _user(test_db, other_inst.id, suffix="fwother")
    assert resolve_framework_for_user(test_db, fw.id, user) is None


def test_resolve_framework_for_user_none_for_archived_framework(test_db):
    fw, inst = _fw(test_db)
    fw.is_archived = True
    test_db.commit()
    user = _user(test_db, inst.id)
    assert resolve_framework_for_user(test_db, fw.id, user) is None


def test_resolve_framework_for_user_none_for_colleagues_private_framework(test_db):
    inst = _inst(test_db)
    owner = _user(test_db, inst.id, suffix="fwowner")
    colleague = _user(test_db, inst.id, suffix="fwcolleague")
    fw, _ = _fw(test_db, inst=inst, visibility="private", created_by=owner.id)

    assert resolve_framework_for_user(test_db, fw.id, owner).id == fw.id
    assert resolve_framework_for_user(test_db, fw.id, colleague) is None


def test_resolve_framework_for_user_team_member_vs_outsider(test_db):
    from models.org_unit import OrgUnit, UserOrgUnit

    inst = _inst(test_db)
    ou = OrgUnit(institution_id=inst.id, unit_type="team", name="Team FW")
    test_db.add(ou)
    test_db.flush()
    member = _user(test_db, inst.id, suffix="fwmember")
    outsider = _user(test_db, inst.id, suffix="fwoutsider")
    test_db.add(UserOrgUnit(user_id=member.id, org_unit_id=ou.id))
    test_db.flush()
    fw, _ = _fw(test_db, inst=inst, visibility="team", org_unit_id=ou.id)

    assert resolve_framework_for_user(test_db, fw.id, member).id == fw.id
    assert resolve_framework_for_user(test_db, fw.id, outsider) is None
