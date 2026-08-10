"""Unit tests for org_unit_service recursive traversal helpers.

Design: docs/superpowers/specs/2026-08-07-org-unit-hierarchie-design.md
"""

import pytest

from models.auth import Institution, User, UserStatus
from models.org_unit import OrgUnit, UserOrgUnit
from services.org_unit_service import (
    assign_user_to_org_unit,
    create_org_unit,
    delete_org_unit,
    get_ancestor_ids,
    get_descendant_ids,
    get_user_accessible_org_unit_ids,
    move_org_unit,
    remove_user_from_org_unit,
    would_create_cycle,
)


def _make_institution(db, slug: str = "orgunit-service-test") -> Institution:
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


def _make_three_level_tree(db, inst):
    """institution -> abteilung -> team -> subteam"""
    abteilung = OrgUnit(
        institution_id=inst.id, unit_type="abteilung", name="Informatik"
    )
    db.add(abteilung)
    db.flush()
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Backend",
        parent_org_unit_id=abteilung.id,
    )
    db.add(team)
    db.flush()
    subteam = OrgUnit(
        institution_id=inst.id,
        unit_type="subteam",
        name="Payments",
        parent_org_unit_id=team.id,
    )
    db.add(subteam)
    db.commit()
    return abteilung, team, subteam


def test_get_descendant_ids_includes_all_levels_below(test_db):
    inst = _make_institution(test_db)
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)

    descendants = get_descendant_ids(test_db, abteilung.id)

    assert descendants == {abteilung.id, team.id, subteam.id}


def test_get_descendant_ids_leaf_returns_only_itself(test_db):
    inst = _make_institution(test_db, slug="orgunit-service-leaf")
    _, _, subteam = _make_three_level_tree(test_db, inst)

    assert get_descendant_ids(test_db, subteam.id) == {subteam.id}


def test_get_ancestor_ids_includes_all_levels_above(test_db):
    inst = _make_institution(test_db, slug="orgunit-service-ancestors")
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)

    ancestors = get_ancestor_ids(test_db, subteam.id)

    assert ancestors == {abteilung.id, team.id, subteam.id}


def test_would_create_cycle_detects_move_under_own_descendant(test_db):
    inst = _make_institution(test_db, slug="orgunit-service-cycle")
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)

    assert would_create_cycle(test_db, abteilung.id, team.id) is True
    assert would_create_cycle(test_db, abteilung.id, abteilung.id) is True


def test_would_create_cycle_allows_valid_move(test_db):
    inst = _make_institution(test_db, slug="orgunit-service-validmove")
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)
    other_abteilung = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="HR")
    test_db.add(other_abteilung)
    test_db.commit()

    assert would_create_cycle(test_db, team.id, other_abteilung.id) is False
    assert would_create_cycle(test_db, subteam.id, None) is False


def test_get_user_accessible_org_unit_ids_unions_multiple_memberships(test_db):
    inst = _make_institution(test_db, slug="orgunit-service-access")
    abteilung_a, team_a, subteam_a = _make_three_level_tree(test_db, inst)
    abteilung_b = OrgUnit(institution_id=inst.id, unit_type="abteilung", name="HR")
    test_db.add(abteilung_b)
    test_db.commit()

    user = User(
        email="access@orgunit-service-test.ch",
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Access",
        last_name="Test",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.flush()

    test_db.add_all(
        [
            UserOrgUnit(user_id=user.id, org_unit_id=team_a.id),
            UserOrgUnit(user_id=user.id, org_unit_id=abteilung_b.id),
        ]
    )
    test_db.commit()

    accessible = get_user_accessible_org_unit_ids(test_db, user.id, inst.id)

    assert accessible == {team_a.id, subteam_a.id, abteilung_b.id}
    assert abteilung_a.id not in accessible


def test_create_org_unit_persists_with_parent(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-create")
    abteilung = create_org_unit(
        test_db,
        institution_id=inst.id,
        unit_type="abteilung",
        name="IT",
        parent_org_unit_id=None,
    )
    team = create_org_unit(
        test_db,
        institution_id=inst.id,
        unit_type="team",
        name="Backend",
        parent_org_unit_id=abteilung.id,
    )

    assert team.parent_org_unit_id == abteilung.id
    assert team.id is not None


def test_create_org_unit_rejects_duplicate_sibling_name(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-dup")
    create_org_unit(
        test_db,
        institution_id=inst.id,
        unit_type="abteilung",
        name="IT",
        parent_org_unit_id=None,
    )

    with pytest.raises(ValueError, match="existiert bereits"):
        create_org_unit(
            test_db,
            institution_id=inst.id,
            unit_type="abteilung",
            name="IT",
            parent_org_unit_id=None,
        )


def test_create_org_unit_rejects_parent_from_other_institution(test_db):
    inst_a = _make_institution(test_db, slug="orgunit-crud-cross-a")
    inst_b = _make_institution(test_db, slug="orgunit-crud-cross-b")
    foreign_parent = create_org_unit(
        test_db,
        institution_id=inst_b.id,
        unit_type="abteilung",
        name="Fremd",
        parent_org_unit_id=None,
    )

    with pytest.raises(ValueError, match="Parent-OrgUnit"):
        create_org_unit(
            test_db,
            institution_id=inst_a.id,
            unit_type="team",
            name="X",
            parent_org_unit_id=foreign_parent.id,
        )


def test_move_org_unit_rejects_cycle(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-move-cycle")
    abteilung, team, _subteam = _make_three_level_tree(test_db, inst)

    with pytest.raises(ValueError, match="Ring"):
        move_org_unit(test_db, abteilung, team.id)


def test_move_org_unit_to_valid_new_parent_succeeds(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-move-ok")
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)
    other = create_org_unit(
        test_db,
        institution_id=inst.id,
        unit_type="abteilung",
        name="HR",
        parent_org_unit_id=None,
    )

    moved = move_org_unit(test_db, team, other.id)

    assert moved.parent_org_unit_id == other.id


def test_delete_org_unit_returns_descendant_count(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-delete")
    abteilung, team, subteam = _make_three_level_tree(test_db, inst)

    deleted_count = delete_org_unit(test_db, abteilung)

    assert deleted_count == 2  # team + subteam
    assert test_db.query(OrgUnit).filter(OrgUnit.id == team.id).one_or_none() is None


def test_assign_and_remove_user_membership(test_db):
    inst = _make_institution(test_db, slug="orgunit-crud-membership")
    abteilung = create_org_unit(
        test_db,
        institution_id=inst.id,
        unit_type="abteilung",
        name="IT",
        parent_org_unit_id=None,
    )
    user = User(
        email="member2@orgunit-crud-test.ch",
        password_hash="dummy",  # pragma: allowlist secret
        first_name="Member",
        last_name="Two",
        institution_id=inst.id,
        status=UserStatus.ACTIVE.value,
    )
    test_db.add(user)
    test_db.commit()

    membership = assign_user_to_org_unit(
        test_db, user_id=user.id, org_unit_id=abteilung.id
    )
    assert membership.user_id == user.id

    with pytest.raises(ValueError, match="bereits zugeordnet"):
        assign_user_to_org_unit(test_db, user_id=user.id, org_unit_id=abteilung.id)

    remove_user_from_org_unit(test_db, user_id=user.id, org_unit_id=abteilung.id)
    assert (
        test_db.query(UserOrgUnit)
        .filter(UserOrgUnit.user_id == user.id, UserOrgUnit.org_unit_id == abteilung.id)
        .one_or_none()
        is None
    )
