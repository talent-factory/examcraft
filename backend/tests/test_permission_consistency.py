"""
Permission Consistency Tests

Ensures permission names are consistent across the entire codebase:
- Backend seed roles (source of truth)
- Backend API endpoint guards (require_permission)
- Frontend route guards (requiredPermissions)
- Frontend navigation config (requiredPermissions)

This test suite prevents the recurring bug where permission names
drift between frontend and backend (e.g. 'questions:create' vs 'create_questions').
"""

import os
import re


# ============================================================================
# Constants: Source of truth
# ============================================================================

# Root paths
BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
)


def _get_seed_permissions() -> dict[str, list[str]]:
    """
    Parse seed_roles.py and extract all permission strings per role.
    This is the single source of truth for valid permission names.

    Uses regex to reliably extract role blocks from the seed file,
    since AST parsing struggles with enum attribute access patterns
    like UserRole.ADMIN.value.
    """
    seed_path = os.path.join(BACKEND_DIR, "utils", "seed_roles.py")
    with open(seed_path) as f:
        source = f.read()

    roles = {}
    # Split by role blocks (each { ... } dict in roles_data list)
    blocks = re.split(r'\{\s*\n\s*"name":', source)

    for block in blocks[1:]:  # Skip the part before first role
        name_match = re.search(r"UserRole\.(\w+)\.value", block)
        if not name_match:
            name_match = re.search(r'"(\w+)"', block)
        if not name_match:
            continue

        role_name = name_match.group(1).lower()

        # Find the permissions list
        perms_match = re.search(r'"permissions":\s*\[(.*?)\]', block, re.DOTALL)
        if perms_match:
            perms_str = perms_match.group(1)
            perms = re.findall(r'"([^"]+)"', perms_str)
            roles[role_name] = perms

    return roles


def _get_all_seed_permission_names() -> set[str]:
    """Get the union of all permission names from all seed roles."""
    roles = _get_seed_permissions()
    all_perms = set()
    for perms in roles.values():
        all_perms.update(perms)
    return all_perms


def _get_backend_require_permission_calls() -> list[tuple[str, str, int]]:
    """
    Find all require_permission("...") calls in backend API files.
    Returns list of (file, permission_name, line_number).
    """
    api_dir = os.path.join(BACKEND_DIR, "api")
    results = []
    pattern = re.compile(r'require_permission\(["\']([^"\']+)["\']\)')

    for root, _, files in os.walk(api_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                for lineno, line in enumerate(f, 1):
                    for match in pattern.finditer(line):
                        results.append((fpath, match.group(1), lineno))

    return results


def _get_frontend_required_permissions() -> list[tuple[str, str, int]]:
    """
    Find all requiredPermissions={['...']} and requiredPermissions: ['...']
    in frontend source files.
    Returns list of (file, permission_name, line_number).
    """
    results = []
    # Matches: requiredPermissions={['perm']} or requiredPermissions: ['perm']
    pattern = re.compile(r"requiredPermissions[=:{}\s\[]+['\"]([^'\"]+)['\"]")

    for root, _, files in os.walk(FRONTEND_SRC_DIR):
        for fname in files:
            if not fname.endswith((".ts", ".tsx")):
                continue
            fpath = os.path.join(root, fname)
            with open(fpath) as f:
                for lineno, line in enumerate(f, 1):
                    for match in pattern.finditer(line):
                        results.append((fpath, match.group(1), lineno))

    return results


def _get_frontend_feature_names() -> set[str]:
    """
    Extract feature names from config/features.ts Feature enum.
    These are valid as permission names in the tier-based check.
    """
    features_path = os.path.join(FRONTEND_SRC_DIR, "config", "features.ts")
    if not os.path.exists(features_path):
        return set()

    with open(features_path) as f:
        content = f.read()

    # Match: FEATURE_NAME = 'feature_value'
    return set(re.findall(r"=\s*['\"]([^'\"]+)['\"]", content))


# ============================================================================
# Tests
# ============================================================================


class TestPermissionConsistency:
    """Verify permission names are consistent across the entire stack."""

    def test_seed_roles_exist(self):
        """Seed roles file must exist and contain roles."""
        roles = _get_seed_permissions()
        assert len(roles) >= 4, f"Expected at least 4 roles, got {len(roles)}"
        assert "admin" in [r.lower() for r in roles] or any("ADMIN" in r for r in roles)

    def test_all_backend_permissions_exist_in_seed_roles(self):
        """
        Every permission used in require_permission() must exist
        in at least one seed role.
        """
        valid_perms = _get_all_seed_permission_names()
        api_perms = _get_backend_require_permission_calls()

        mismatches = []
        for fpath, perm, lineno in api_perms:
            if perm not in valid_perms:
                rel_path = os.path.relpath(fpath, BACKEND_DIR)
                mismatches.append(f"  {rel_path}:{lineno} — '{perm}'")

        assert not mismatches, (
            "Backend API uses permissions not found in seed roles:\n"
            + "\n".join(mismatches)
            + "\n\nValid permissions: "
            + ", ".join(sorted(valid_perms))
        )

    def test_all_frontend_permissions_exist_in_backend(self):
        """
        Every permission used in frontend PermissionGuard must exist either:
        - In the seed role permissions (role-based check), OR
        - In the Feature enum (tier-based check)
        """
        valid_role_perms = _get_all_seed_permission_names()
        valid_feature_names = _get_frontend_feature_names()
        valid_all = valid_role_perms | valid_feature_names

        frontend_perms = _get_frontend_required_permissions()

        mismatches = []
        for fpath, perm, lineno in frontend_perms:
            if perm not in valid_all:
                rel_path = os.path.relpath(fpath, FRONTEND_SRC_DIR)
                mismatches.append(f"  {rel_path}:{lineno} — '{perm}'")

        assert not mismatches, (
            "Frontend uses permissions not found in backend roles or features:\n"
            + "\n".join(mismatches)
            + "\n\nValid role permissions: "
            + ", ".join(sorted(valid_role_perms))
            + "\nValid feature names: "
            + ", ".join(sorted(valid_feature_names))
        )

    def test_no_colon_format_in_route_guards(self):
        """
        Route guards must NOT use the old colon-separated format
        (e.g. 'questions:create') for action permissions.

        The colon format is only valid for the documents/prompt namespace
        where both backend and frontend consistently use it
        (e.g. 'documents:read', 'prompt:create').
        """
        # These colon-format permissions are consistent and valid
        allowed_colon_perms = {
            "documents:read",
            "prompt:create",
            "prompt:read",
            "prompt:update",
            "prompt:delete",
        }

        frontend_perms = _get_frontend_required_permissions()
        backend_perms = _get_backend_require_permission_calls()

        violations = []
        for fpath, perm, lineno in frontend_perms + backend_perms:
            if ":" in perm and perm not in allowed_colon_perms:
                rel_path = os.path.relpath(
                    fpath,
                    FRONTEND_SRC_DIR if "frontend" in fpath else BACKEND_DIR,
                )
                violations.append(f"  {rel_path}:{lineno} — '{perm}'")

        assert not violations, (
            "Found colon-format permissions outside the allowed set.\n"
            "Use underscore format instead (e.g. 'create_questions' not 'questions:create'):\n"
            + "\n".join(violations)
        )

    def test_no_duplicate_permission_formats(self):
        """
        There must not be both 'action_resource' and 'resource:action'
        for the same concept (e.g. 'create_questions' and 'questions:create').
        """
        valid_perms = _get_all_seed_permission_names()

        # Build a normalized map: for each perm, check if its "flipped" version exists
        conflicts = []
        for perm in valid_perms:
            if ":" in perm:
                # Convert resource:action to action_resource
                parts = perm.split(":", 1)
                flipped = f"{parts[1]}_{parts[0]}"
                if flipped in valid_perms:
                    conflicts.append(f"  '{perm}' AND '{flipped}' both exist")
            elif "_" in perm:
                # Convert action_resource to resource:action
                parts = perm.split("_", 1)
                flipped = f"{parts[1]}:{parts[0]}"
                if flipped in valid_perms:
                    conflicts.append(f"  '{perm}' AND '{flipped}' both exist")

        assert not conflicts, (
            "Found duplicate permission formats (same concept, different naming):\n"
            + "\n".join(conflicts)
        )

    def test_frontend_navigation_matches_routes(self):
        """
        Frontend navigation items (useRoleBasedNavigation) must use the same
        permission names as the route guards (AppWithAuth).
        """
        frontend_perms = _get_frontend_required_permissions()

        # Group by source file
        by_file = {}
        for fpath, perm, lineno in frontend_perms:
            fname = os.path.basename(fpath)
            by_file.setdefault(fname, set()).add(perm)

        routes_perms = by_file.get("AppWithAuth.tsx", set())
        nav_perms = by_file.get("useRoleBasedNavigation.ts", set())

        if routes_perms and nav_perms:
            routes_only = routes_perms - nav_perms
            nav_only = nav_perms - routes_perms

            mismatches = []
            if routes_only:
                mismatches.append(f"  In routes but not navigation: {routes_only}")
            if nav_only:
                mismatches.append(f"  In navigation but not routes: {nav_only}")

            assert not mismatches, (
                "Permission mismatch between routes and navigation:\n"
                + "\n".join(mismatches)
            )

    def test_dozent_has_core_feature_permissions(self):
        """
        The Dozent role (default for self-registered users) must have
        all permissions needed for core Free-tier features.
        """
        roles = _get_seed_permissions()
        dozent_perms = set()
        for role_name, perms in roles.items():
            if "dozent" in role_name.lower():
                dozent_perms = set(perms)
                break

        # Core feature permissions that must be in Dozent role
        required_for_free_tier = {
            "create_questions",  # Question generation
            "documents:read",  # Document library
            "create_documents",  # Document upload
            "create_exams",  # Exam composer
            "view_questions",  # View generated questions
        }

        missing = required_for_free_tier - dozent_perms
        assert not missing, (
            f"Dozent role is missing permissions required for Free-tier features: {missing}"
        )

    def test_permission_parsing_formats(self):
        """
        The User.has_permission() method must correctly parse permissions
        stored in all known formats.
        """
        from unittest.mock import MagicMock
        from models.auth import User

        def _make_user(permissions_str, is_superuser=False):
            role = MagicMock()
            role.permissions = permissions_str
            user = MagicMock(spec=User)
            user.is_superuser = is_superuser
            user.roles = [role]
            # Use actual method
            user.has_permission = User.has_permission.__get__(user)
            return user

        # Test PG array format
        user = _make_user("{create_questions,edit_questions,view_questions}")
        assert user.has_permission("create_questions") is True
        assert user.has_permission("edit_questions") is True
        assert user.has_permission("nonexistent") is False

        # Test JSON format
        user2 = _make_user('["create_questions", "edit_questions"]')
        assert user2.has_permission("create_questions") is True
        assert user2.has_permission("nonexistent") is False

        # Test empty PG array
        user3 = _make_user("{}")
        assert user3.has_permission("anything") is False

        # Test colon-format permissions
        user4 = _make_user("{documents:read,prompt:create}")
        assert user4.has_permission("documents:read") is True
        assert user4.has_permission("prompt:create") is True

    def test_superuser_bypasses_permissions(self):
        """Superuser must have access to all permissions."""
        from unittest.mock import MagicMock
        from models.auth import User

        user = MagicMock(spec=User)
        user.is_superuser = True
        user.roles = []
        user.has_permission = User.has_permission.__get__(user)

        assert user.has_permission("create_questions") is True
        assert user.has_permission("manage_users") is True
        assert user.has_permission("any_permission") is True
