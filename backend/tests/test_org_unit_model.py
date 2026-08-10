"""Unit tests for OrgUnit/UserOrgUnit self-referencing model (Stufe 0 Fundament).

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

from models.auth import Institution, User, UserStatus
from models.org_unit import OrgUnit, UserOrgUnit


def _make_institution(db, slug: str = "orgunit-model-test") -> Institution:
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


def test_org_unit_parent_child_relationship(test_db):
    inst = _make_institution(test_db)
    abteilung = OrgUnit(
        institution_id=inst.id, unit_type="abteilung", name="Informatik"
    )
    test_db.add(abteilung)
    test_db.flush()

    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Backend-Team",
        parent_org_unit_id=abteilung.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(abteilung)
    test_db.refresh(team)

    assert team.parent_org_unit_id == abteilung.id
    assert team.parent.id == abteilung.id
    assert abteilung.children[0].id == team.id


def test_org_unit_cascade_delete_removes_children(test_db):
    inst = _make_institution(test_db, slug="orgunit-model-cascade")
    abteilung = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="HR")
    test_db.add(abteilung)
    test_db.flush()
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Recruiting",
        parent_org_unit_id=abteilung.id,
    )
    test_db.add(team)
    test_db.commit()
    team_id = team.id

    test_db.delete(abteilung)
    test_db.commit()

    assert test_db.query(OrgUnit).filter(OrgUnit.id == team_id).one_or_none() is None


def test_user_can_belong_to_multiple_org_units(test_db):
    inst = _make_institution(test_db, slug="orgunit-model-membership")
    abteilung_a = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="A")
    abteilung_b = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="B")
    test_db.add_all([abteilung_a, abteilung_b])
    test_db.flush()

    user = User(
        email="member@orgunit-test.ch",
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Multi",
        last_name="Member",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()

    test_db.add_all(
        [
            UserOrgUnit(user_id=user.id, org_unit_id=abteilung_a.id),
            UserOrgUnit(user_id=user.id, org_unit_id=abteilung_b.id),
        ]
    )
    test_db.commit()

    memberships = (
        test_db.query(UserOrgUnit).filter(UserOrgUnit.user_id == user.id).all()
    )
    assert {m.org_unit_id for m in memberships} == {abteilung_a.id, abteilung_b.id}
