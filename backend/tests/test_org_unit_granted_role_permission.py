"""Tests for Granted Role permission inheritance (TF-637).

Design: docs/superpowers/specs/2026-08-13-org-unit-rbac-vererbung-design.md
ADR: docs/adr/0003-granted-role-not-cascading.md

An OrgUnit can optionally grant a Role to its *direct* members via
``OrgUnit.role_id``. ``User.has_permission()`` must fold that Role's
permissions into the effective permission set, additively to the user's own
direct role assignments -- and, per ADR-0003, WITHOUT cascading through the
composite hierarchy the way Access Scope
(``get_user_accessible_org_unit_ids``) does.
"""

from models.auth import Institution, Role, User, UserStatus
from models.org_unit import OrgUnit, UserOrgUnit


def _make_institution(db, slug: str = "granted-role-test") -> Institution:
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


def _make_user(db, inst: Institution, email: str) -> User:
    user = User(
        email=email,
        institution_id=inst.id,
        first_name="Test",
        last_name="User",
        status=UserStatus.ACTIVE.value,
    )
    db.add(user)
    db.flush()
    return user


def _make_role(db, name: str, permissions: list[str], is_active: bool = True) -> Role:
    role = Role(
        name=name,
        display_name=name,
        permissions=permissions,
        is_active=is_active,
    )
    db.add(role)
    db.flush()
    return role


def test_direct_member_inherits_granted_role_permission(test_db):
    inst = _make_institution(test_db, "granted-direct")
    user = _make_user(test_db, inst, "direct@granted-role-test.example")
    granted_role = _make_role(test_db, "backend-grader", ["submissions:grade"])
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is True


def test_non_member_does_not_inherit_granted_role_permission(test_db):
    inst = _make_institution(test_db, "granted-nonmember")
    user = _make_user(test_db, inst, "nonmember@granted-role-test.example")
    granted_role = _make_role(test_db, "backend-grader-2", ["submissions:grade"])
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.commit()
    test_db.refresh(user)

    # user is not a member of `team` at all
    assert user.has_permission("submissions:grade") is False


def test_parent_membership_does_not_cascade_granted_role(test_db):
    """ADR-0003 regression: Access Scope cascades Parent->Child, Granted Role does not."""
    inst = _make_institution(test_db, "granted-cascade")
    user = _make_user(test_db, inst, "parentmember@granted-role-test.example")
    granted_role = _make_role(test_db, "backend-grader-3", ["submissions:grade"])
    abteilung = OrgUnit(
        institution_id=inst.id, unit_type="abteilung", name="Informatik"
    )
    test_db.add(abteilung)
    test_db.flush()
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        parent_org_unit_id=abteilung.id,
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.flush()
    # user is a direct member of the PARENT abteilung, not of `team` itself
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=abteilung.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is False


def test_inactive_granted_role_does_not_grant_permission(test_db):
    inst = _make_institution(test_db, "granted-inactive")
    user = _make_user(test_db, inst, "inactive@granted-role-test.example")
    granted_role = _make_role(
        test_db, "backend-grader-4", ["submissions:grade"], is_active=False
    )
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is False


def test_granted_role_is_additive_union_with_direct_role(test_db):
    inst = _make_institution(test_db, "granted-union")
    user = _make_user(test_db, inst, "union@granted-role-test.example")
    direct_role = _make_role(test_db, "dozent-union", ["create_questions"])
    granted_role = _make_role(test_db, "backend-grader-5", ["submissions:grade"])
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.flush()
    user.roles.append(direct_role)
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    # both the direct role's permission AND the granted role's permission apply
    assert user.has_permission("create_questions") is True
    assert user.has_permission("submissions:grade") is True
    # a permission neither role has is still denied
    assert user.has_permission("delete_exams") is False


def test_child_membership_does_not_inherit_ancestor_granted_role(test_db):
    """ADR-0003 regression, mirror direction of
    test_parent_membership_does_not_cascade_granted_role above.

    That test puts the Granted Role on the *child* and membership on the
    *parent*. This test covers the opposite -- and more plausible
    accidental-cascade -- direction: Granted Role on the *ancestor*,
    membership on the *descendant*. This is exactly how Access Scope
    (get_user_accessible_org_unit_ids) propagates (parent membership ->
    access to all descendants), so it's the direction a future refactor
    would most likely accidentally reintroduce if it conflated the two
    concepts.
    """
    inst = _make_institution(test_db, "granted-cascade-mirror")
    user = _make_user(test_db, inst, "childmember@granted-role-test.example")
    granted_role = _make_role(test_db, "backend-grader-6", ["submissions:grade"])
    abteilung = OrgUnit(
        institution_id=inst.id,
        unit_type="abteilung",
        name="Informatik",
        role_id=granted_role.id,
    )
    test_db.add(abteilung)
    test_db.flush()
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        parent_org_unit_id=abteilung.id,
    )
    test_db.add(team)
    test_db.flush()
    # user is a direct member of the CHILD team, not of `abteilung` itself
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is False


def test_member_of_both_levels_gets_both_granted_roles_additively(test_db):
    """A user can be a *direct* member of more than one level of the same
    tree at once (nothing prevents that); each level's own Granted Role
    should apply via direct membership, additively -- not merged, doubled,
    or lost due to the tree structure connecting the two OrgUnits."""
    inst = _make_institution(test_db, "granted-both-levels")
    user = _make_user(test_db, inst, "bothlevels@granted-role-test.example")
    parent_role = _make_role(test_db, "abteilungsleiter-7", ["manage_settings"])
    child_role = _make_role(test_db, "backend-grader-7", ["submissions:grade"])
    abteilung = OrgUnit(
        institution_id=inst.id,
        unit_type="abteilung",
        name="Informatik",
        role_id=parent_role.id,
    )
    test_db.add(abteilung)
    test_db.flush()
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        parent_org_unit_id=abteilung.id,
        role_id=child_role.id,
    )
    test_db.add(team)
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=abteilung.id))
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("manage_settings") is True
    assert user.has_permission("submissions:grade") is True
    assert user.has_permission("delete_exams") is False


def test_additive_union_across_two_distinct_org_unit_memberships(test_db):
    """Extends test_granted_role_is_additive_union_with_direct_role: here
    BOTH permissions come from Granted Roles (no direct role assignment
    involved), via two separate, unrelated OrgUnit memberships."""
    inst = _make_institution(test_db, "granted-two-units")
    user = _make_user(test_db, inst, "twounits@granted-role-test.example")
    role_a = _make_role(test_db, "backend-grader-8", ["submissions:grade"])
    role_b = _make_role(test_db, "document-manager-8", ["documents:read"])
    team_a = OrgUnit(
        institution_id=inst.id, unit_type="team", name="Team A", role_id=role_a.id
    )
    team_b = OrgUnit(
        institution_id=inst.id, unit_type="team", name="Team B", role_id=role_b.id
    )
    test_db.add_all([team_a, team_b])
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team_a.id))
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team_b.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is True
    assert user.has_permission("documents:read") is True
    assert user.has_permission("delete_exams") is False


def test_role_deactivated_after_being_granted_stops_granting_permission(test_db):
    """Distinct from test_inactive_granted_role_does_not_grant_permission,
    which creates the Role inactive from the start. Here the Role is
    active when granted and the membership is created, then deactivated
    afterwards -- exercising the "mutate, then re-check on a freshly
    refreshed user" path, which a naive is_active check evaluated once at
    membership-creation time (rather than at each has_permission() call)
    would get wrong."""
    inst = _make_institution(test_db, "granted-deactivated-later")
    user = _make_user(test_db, inst, "deactivatedlater@granted-role-test.example")
    granted_role = _make_role(test_db, "backend-grader-9", ["submissions:grade"])
    team = OrgUnit(
        institution_id=inst.id,
        unit_type="team",
        name="Team Backend",
        role_id=granted_role.id,
    )
    test_db.add(team)
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is True

    granted_role.is_active = False
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is False


def test_membership_with_org_unit_that_has_no_granted_role(test_db):
    """The one branch of the new has_permission() loop with no dedicated
    coverage elsewhere: a membership exists, but its OrgUnit has no
    Granted Role at all (role_id is None) -- must short-circuit cleanly,
    not raise, and not grant anything."""
    inst = _make_institution(test_db, "granted-no-role")
    user = _make_user(test_db, inst, "norole@granted-role-test.example")
    team = OrgUnit(institution_id=inst.id, unit_type="team", name="Team Backend")
    test_db.add(team)
    test_db.flush()
    test_db.add(UserOrgUnit(user_id=user.id, org_unit_id=team.id))
    test_db.commit()
    test_db.refresh(user)

    assert user.has_permission("submissions:grade") is False
