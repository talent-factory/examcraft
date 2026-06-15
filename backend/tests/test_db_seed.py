"""TF-433: idempotenter System-Seed (grading_schemes).

Der create_all-Bootstrap überspringt Migrationskörper; ``seed_system_grading_schemes``
holt die in tf333 eingebetteten System-Notenschemata nach. Muss idempotent sein,
damit er bei jedem Bootstrap gefahrlos läuft und bestehende DBs heilt.
"""

from db_seed import SYSTEM_GRADING_SCHEMES, seed_system_grading_schemes
from models.grading_scheme import GradingScheme


def _system_count(db) -> int:
    return (
        db.query(GradingScheme).filter(GradingScheme.institution_id.is_(None)).count()
    )


def test_seed_inserts_all_system_schemes(test_db):
    inserted = seed_system_grading_schemes(test_db.connection())
    test_db.flush()

    assert inserted == len(SYSTEM_GRADING_SCHEMES)
    assert _system_count(test_db) == len(SYSTEM_GRADING_SCHEMES)
    names = {
        s.name
        for s in test_db.query(GradingScheme).filter(
            GradingScheme.institution_id.is_(None)
        )
    }
    assert {s["name"] for s in SYSTEM_GRADING_SCHEMES} <= names


def test_seed_is_idempotent(test_db):
    first = seed_system_grading_schemes(test_db.connection())
    test_db.flush()
    second = seed_system_grading_schemes(test_db.connection())
    test_db.flush()

    assert first == len(SYSTEM_GRADING_SCHEMES)
    assert second == 0  # zweiter Aufruf fügt nichts doppelt ein
    assert _system_count(test_db) == len(SYSTEM_GRADING_SCHEMES)


def test_seed_heals_partial_state(test_db):
    """Partial-Heal: bei teilweise vorhandenen System-Schemata fügt der Seed genau
    die fehlenden ein (das erklärte Ziel der Idempotenz — heilt bestehende DBs)."""
    for s in SYSTEM_GRADING_SCHEMES[:2]:
        test_db.add(
            GradingScheme(
                institution_id=None,
                name=s["name"],
                display_format=s["display_format"],
                config=s["config"],
                is_default_for_institution=False,
            )
        )
    test_db.flush()

    inserted = seed_system_grading_schemes(test_db.connection())
    test_db.flush()

    assert inserted == len(SYSTEM_GRADING_SCHEMES) - 2  # nur die fehlenden
    assert _system_count(test_db) == len(SYSTEM_GRADING_SCHEMES)
