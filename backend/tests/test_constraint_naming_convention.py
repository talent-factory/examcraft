"""Constraint names are fixed by ``Base.metadata``'s naming convention (TF-339).

Before TF-339 ``create_all`` left unnamed PK/FK/UNIQUE constraints to
PostgreSQL, while some migrations created the same FK under an explicit name
(``fk_exams_grading_scheme`` vs. ``exams_grading_scheme_id_fkey``). A migration
dropping the constraint by name then failed on whichever bootstrap path it was
not written for (TF-335).

The suite's database is built by ``create_all`` (see ``conftest.test_engine``),
so this checks the ``create_all`` side; ``test_alembic_upgrade_from_empty``
checks the same names on the replayed migration chain.
"""

from sqlalchemy import (
    ForeignKeyConstraint,
    PrimaryKeyConstraint,
    UniqueConstraint,
    text,
)

from database import NAMING_CONVENTION, Base

_NAMED_KINDS = (PrimaryKeyConstraint, ForeignKeyConstraint, UniqueConstraint)


def model_constraint_names() -> set[tuple[str, str]]:
    """(table, constraint name) of every PK/FK/UNIQUE the models declare."""
    names = set()
    for table in Base.metadata.tables.values():
        for constraint in table.constraints:
            if isinstance(constraint, _NAMED_KINDS):
                assert constraint.name, f"{table.name}: unnamed {constraint!r}"
                names.add((table.name, str(constraint.name)))
    return names


def db_constraint_names(conn, tables: set[str]) -> set[tuple[str, str]]:
    """(table, constraint name) of every PK/FK/UNIQUE in the database's public schema."""
    rows = conn.execute(
        text(
            "SELECT t.relname, c.conname FROM pg_constraint c"
            " JOIN pg_class t ON t.oid = c.conrelid"
            " JOIN pg_namespace n ON n.oid = t.relnamespace"
            " WHERE n.nspname = 'public' AND c.contype IN ('p', 'f', 'u')"
        )
    )
    return {(table, name) for table, name in rows if table in tables}


def test_convention_reproduces_postgres_default_names():
    """The templates mirror PostgreSQL's own names, so production keeps its names."""
    assert NAMING_CONVENTION["pk"] == "%(table_name)s_pkey"
    assert NAMING_CONVENTION["fk"] == "%(table_name)s_%(column_0_N_name)s_fkey"
    assert NAMING_CONVENTION["uq"] == "%(table_name)s_%(column_0_N_name)s_key"
    # A "ck" template would be fed the explicit CHECK names and rename them all.
    assert "ck" not in NAMING_CONVENTION

    exams = Base.metadata.tables["exams"]
    assert exams.primary_key.name == "exams_pkey"
    fk_names = {fk.name for fk in exams.foreign_key_constraints}
    assert "exams_created_by_fkey" in fk_names
    # Created under an explicit name by a migration — the model carries it too.
    assert "fk_exams_grading_scheme" in fk_names


def test_create_all_names_match_models(test_engine):
    with test_engine.connect() as conn:
        actual = db_constraint_names(conn, set(Base.metadata.tables))
    # Only tables create_all built — a model imported later by another test
    # module is not in the session database.
    built = {table for table, _ in actual}
    expected = {key for key in model_constraint_names() if key[0] in built}

    assert sorted(actual - expected) == []
    assert sorted(expected - actual) == []
