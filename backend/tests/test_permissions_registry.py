"""Tests for the permission registry (TF-603)."""

from utils.permissions import KNOWN_PERMISSIONS

from tests.test_permission_consistency import _get_all_seed_permission_names


def test_known_permissions_has_manage_org_units():
    assert "manage_org_units" in KNOWN_PERMISSIONS
    assert KNOWN_PERMISSIONS["manage_org_units"]["category"] == "Organisation"


def test_known_permissions_covers_all_seeded_strings():
    # Liest die Permission-Union direkt aus utils/seed_roles.py, statt sie hier
    # ein drittes Mal hart zu kodieren (test_permission_consistency.py und
    # seed_roles.py selbst sind die anderen beiden Stellen) — verhindert genau
    # das Drift-Muster, das test_permission_consistency.py laut eigenem
    # Docstring verhindern soll. Wird dieser Test rot, weil seed_roles.py einen
    # neuen String einführt: KNOWN_PERMISSIONS entsprechend ergänzen, nicht den
    # Test lockern.
    seeded_permissions = _get_all_seed_permission_names()
    assert seeded_permissions == set(KNOWN_PERMISSIONS.keys())


def test_known_permissions_entries_have_label_and_category():
    for key, meta in KNOWN_PERMISSIONS.items():
        assert meta.get("label"), f"{key} fehlt ein label"
        assert meta.get("category"), f"{key} fehlt eine category"


def test_known_permissions_has_institution_admin_read_all_bypass_permissions():
    # TF-639: Institutions-Admin-Immer-Lesezugriff pro Ressourcentyp.
    # "prompt:read_all" ist bewusst Singular (matcht prompt:read/update/
    # delete/create), die anderen vier Plural (matchen documents:read /
    # ihre jeweilige Ressourcen-Kategorie).
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
