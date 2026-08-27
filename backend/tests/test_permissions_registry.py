"""Tests for the permission registry (TF-603)."""

from utils.permissions import KNOWN_PERMISSIONS, OPT_IN_ONLY_PERMISSIONS

from tests.test_permission_consistency import _get_all_seed_permission_names


def test_known_permissions_has_manage_org_units():
    assert "manage_org_units" in KNOWN_PERMISSIONS
    assert KNOWN_PERMISSIONS["manage_org_units"]["category"] == "Organisation"


def test_known_permissions_covers_all_seeded_strings():
    # Reads the permission union directly from utils/seed_roles.py instead of
    # hard-coding it here a third time (test_permission_consistency.py and
    # seed_roles.py itself are the other two places) — this prevents exactly
    # the drift pattern that test_permission_consistency.py's own docstring
    # says it should prevent. If this test goes red because seed_roles.py
    # introduces a new string: extend KNOWN_PERMISSIONS accordingly, don't
    # loosen the test.
    #
    # TF-740: KNOWN_PERMISSIONS may additionally contain permissions that are
    # deliberately never seeded to any default role (opt-in only, assignable
    # solely via the custom role editor). Those are tracked explicitly in
    # OPT_IN_ONLY_PERMISSIONS so this equality check still catches any
    # *unintended* drift between the two sources of truth.
    seeded_permissions = _get_all_seed_permission_names()
    assert seeded_permissions == set(KNOWN_PERMISSIONS.keys()) - OPT_IN_ONLY_PERMISSIONS


def test_known_permissions_entries_have_label_and_category():
    for key, meta in KNOWN_PERMISSIONS.items():
        assert meta.get("label"), f"{key} fehlt ein label"
        assert meta.get("category"), f"{key} fehlt eine category"


def test_known_permissions_has_institution_admin_read_all_bypass_permissions():
    # TF-639: institution-admin always-read-access bypass per resource type.
    # "prompt:read_all" is deliberately singular (matches prompt:read/update/
    # delete/create), the other four are plural (match documents:read /
    # their respective resource category).
    expected_category_by_permission = {
        "documents:read_all": "Dokumente",
        "prompt:read_all": "Prompts",
        "questions:read_all": "Fragen",
        "exams:read_all": "Prüfungen",
        "competencies:read_all": "Kompetenzen",
    }
    for permission, category in expected_category_by_permission.items():
        assert permission in KNOWN_PERMISSIONS, (
            f"{permission} fehlt in KNOWN_PERMISSIONS"
        )
        assert KNOWN_PERMISSIONS[permission]["category"] == category


def test_known_permissions_has_impersonation_permission_deliberately_unseeded():
    # TF-740: "users:impersonate" must be assignable via the custom role
    # editor (i.e. registered in KNOWN_PERMISSIONS) but is deliberately NOT
    # part of any default role's seed permissions — opt-in only, see the
    # TF-739 epic description.
    assert "users:impersonate" in KNOWN_PERMISSIONS
    assert KNOWN_PERMISSIONS["users:impersonate"]["category"] == "System"
    assert "users:impersonate" in OPT_IN_ONLY_PERMISSIONS
    assert "users:impersonate" not in _get_all_seed_permission_names()


def test_opt_in_only_permissions_is_subset_of_known_permissions():
    # TF-740: set subtraction against a missing key is a silent no-op, so
    # test_known_permissions_covers_all_seeded_strings's equality check
    # alone would NOT catch an OPT_IN_ONLY_PERMISSIONS entry that has no
    # (or no longer has a) matching KNOWN_PERMISSIONS registration — that
    # permission would then be invisible in the custom role editor, quietly
    # defeating the "opt-in but assignable" contract. This test — and the
    # mirrored module-level assertion in utils/permissions.py, which fails
    # fast at import time even if this test file isn't collected — close
    # that gap explicitly, for every current and future opt-in permission.
    assert OPT_IN_ONLY_PERMISSIONS <= set(KNOWN_PERMISSIONS.keys())
