"""Unit tests for the audit category taxonomy and scope resolver (TF-415)."""

import pytest
from fastapi import HTTPException

from models.auth import Role, User
from services.audit_query_service import resolve_scope
from services.audit_service import (
    ACTIONS_BY_CATEGORY,
    AUDIT_CATEGORIES,
    AuditService,
    category_for_action,
)


class TestCategoryTaxonomy:
    def test_categories_are_the_four_known_ones(self):
        assert set(AUDIT_CATEGORIES) == {"business", "admin", "auth", "security"}

    def test_known_actions_map_to_expected_category(self):
        assert category_for_action(AuditService.ACTION_CREATE_DOCUMENT) == "business"
        assert category_for_action(AuditService.ACTION_DELETE_QUESTION) == "business"
        assert category_for_action("create_exam") == "business"
        assert category_for_action("data_export") == "business"
        assert category_for_action(AuditService.ACTION_CREATE_USER) == "admin"
        assert category_for_action(AuditService.ACTION_ASSIGN_ROLE) == "admin"
        assert category_for_action(AuditService.ACTION_LOGIN) == "auth"
        assert category_for_action(AuditService.ACTION_OAUTH_LOGIN) == "auth"
        assert category_for_action(AuditService.ACTION_PERMISSION_DENIED) == "security"
        assert category_for_action(AuditService.ACTION_SUPERUSER_BYPASS) == "security"
        assert category_for_action(AuditService.ACTION_VIEW_AUDIT_LOG) == "security"

    def test_unknown_action_fails_closed_to_security(self):
        assert category_for_action("ws_subscribe") == "security"
        assert category_for_action("totally_new_event") == "security"

    def test_no_action_belongs_to_two_categories(self):
        seen: set[str] = set()
        for actions in ACTIONS_BY_CATEGORY.values():
            overlap = seen & set(actions)
            assert not overlap, f"action(s) in multiple categories: {overlap}"
            seen |= set(actions)


def _user(*, is_superuser=False, institution_id=1, admin=False) -> User:
    """Transient User (no DB). roles defaults to [] on a transient instance."""
    u = User(
        email="x@test.ch",
        first_name="T",
        last_name="U",
        institution_id=institution_id,
        is_superuser=is_superuser,
    )
    u.roles = (
        [Role(name="admin", display_name="Admin", permissions="[]")] if admin else []
    )
    return u


class TestResolveScope:
    def test_superuser_sees_all_institutions_and_categories(self):
        scope = resolve_scope(_user(is_superuser=True, institution_id=None))
        assert scope.institution_id is None
        assert scope.allowed_categories == frozenset(
            {"business", "admin", "auth", "security"}
        )
        assert scope.can_see_pii is True
        assert scope.is_superuser is True

    def test_institution_admin_is_scoped_and_restricted(self):
        scope = resolve_scope(_user(admin=True, institution_id=7))
        assert scope.institution_id == 7
        assert scope.allowed_categories == frozenset({"business", "admin"})
        assert scope.can_see_pii is False
        assert scope.is_superuser is False

    def test_admin_without_institution_is_forbidden(self):
        with pytest.raises(HTTPException) as exc:
            resolve_scope(_user(admin=True, institution_id=None))
        assert exc.value.status_code == 403

    def test_plain_user_is_forbidden(self):
        with pytest.raises(HTTPException) as exc:
            resolve_scope(_user(admin=False, institution_id=3))
        assert exc.value.status_code == 403

    def test_superuser_with_admin_role_takes_superuser_branch(self):
        scope = resolve_scope(_user(is_superuser=True, admin=True, institution_id=5))
        assert scope.institution_id is None  # not pinned to 5
        assert scope.allowed_categories == frozenset(
            {"business", "admin", "auth", "security"}
        )
        assert scope.can_see_pii is True
        assert scope.is_superuser is True
