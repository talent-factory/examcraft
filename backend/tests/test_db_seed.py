"""TF-433: idempotent system seed (grading_schemes).

The create_all bootstrap skips migration bodies; ``seed_system_grading_schemes``
retroactively inserts the system grading schemes embedded in tf333. Must be
idempotent so it can run safely on every bootstrap and heal existing DBs.
"""

from db_seed import SYSTEM_GRADING_SCHEMES, seed_system_grading_schemes
from models.grading_scheme import GradingScheme


_SYSTEM_NAMES = {s["name"] for s in SYSTEM_GRADING_SCHEMES}


def _system_count(db) -> int:
    """Count only the schemes this seed owns.

    Counting every institution-less scheme also picks up rows other test
    modules committed on the app's own connection — outside this test's
    transaction, so not rolled back. That made the counts order-dependent
    (TF-660).
    """
    return (
        db.query(GradingScheme)
        .filter(
            GradingScheme.institution_id.is_(None),
            GradingScheme.name.in_(_SYSTEM_NAMES),
        )
        .count()
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
    assert second == 0  # second call must not insert duplicates
    assert _system_count(test_db) == len(SYSTEM_GRADING_SCHEMES)


def test_seed_heals_partial_state(test_db):
    """Partial heal: when system schemes are only partially present, the seed
    inserts exactly the missing ones (the stated goal of idempotency — heals
    existing DBs)."""
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

    assert inserted == len(SYSTEM_GRADING_SCHEMES) - 2  # only the missing ones
    assert _system_count(test_db) == len(SYSTEM_GRADING_SCHEMES)
