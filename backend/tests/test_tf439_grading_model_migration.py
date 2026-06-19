"""
Unit-Tests für die TF-439 Alembic-Datenmigration.

Prüft:
1. Migrationsdatei existiert und exponiert upgrade/downgrade.
2. Revision-ID ist ≤32 Zeichen.
3. upgrade() setzt jeden NOT-NULL-Wert in llm_model_for_grading → 'examcraft/grading'.
4. downgrade() setzt 'examcraft/grading'-Zeilen auf NULL zurück.

SQLite-In-Memory-Tabelle als leichtgewichtige Testumgebung –
kein Docker-Postgres erforderlich.
"""

import importlib.util
from pathlib import Path

import sqlalchemy as sa

# ---------------------------------------------------------------------------
# Migrationsdatei laden
# ---------------------------------------------------------------------------
MIGRATION_PATH = Path(__file__).parent.parent / (
    "alembic/versions/2026_06_19_tf439_grading_model_logical.py"
)


def _load_migration():
    """Lädt das Migrationsmodul dynamisch, ohne alembic env.py zu starten."""
    spec = importlib.util.spec_from_file_location("tf439_migration", MIGRATION_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# SQLite-Hilfsfunktionen
# ---------------------------------------------------------------------------


def _make_engine():
    return sa.create_engine("sqlite:///:memory:", future=True)


def _create_table(eng):
    """Erstellt eine minimale institutions-Tabelle in SQLite."""
    with eng.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE institutions ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  name TEXT NOT NULL,"
                "  llm_model_for_grading TEXT"
                ")"
            )
        )


def _seed(conn, value):
    """Fügt eine Institution mit dem angegebenen Modellwert ein."""
    conn.execute(
        sa.text(
            "INSERT INTO institutions (name, llm_model_for_grading) VALUES ('T', :v)"
        ),
        {"v": value},
    )


def _fetch_model(conn):
    return conn.execute(
        sa.text("SELECT llm_model_for_grading FROM institutions LIMIT 1")
    ).scalar()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestMigrationMetadata:
    def test_migration_file_exists(self):
        assert MIGRATION_PATH.exists(), (
            f"Migrationsdatei nicht gefunden: {MIGRATION_PATH}"
        )

    def test_exposes_upgrade(self):
        mod = _load_migration()
        assert callable(getattr(mod, "upgrade", None)), (
            "upgrade() fehlt oder nicht callable"
        )

    def test_exposes_downgrade(self):
        mod = _load_migration()
        assert callable(getattr(mod, "downgrade", None)), (
            "downgrade() fehlt oder nicht callable"
        )

    def test_revision_id_max_32_chars(self):
        mod = _load_migration()
        revision = mod.revision
        assert len(revision) <= 32, (
            f"Revision-ID zu lang ({len(revision)} Zeichen): {revision!r}"
        )

    def test_revision_id_value(self):
        mod = _load_migration()
        assert mod.revision == "tf439_grade_logical"

    def test_down_revision(self):
        mod = _load_migration()
        assert mod.down_revision == "moodle_feedback_push_job"


def _run_migration_fn(eng, fn_name):
    """Führt die ECHTE upgrade()/downgrade()-Funktion gegen die SQLite-Engine aus.

    Bindet den alembic-``op``-Proxy an eine MigrationContext auf der Test-
    Connection und ruft die im Modul versandte Funktion auf — so wird die
    tatsächlich ausgelieferte SQL geprüft, nicht eine handkopierte Variante
    (die bei einer WHERE-Änderung in der Migration weiter grün bliebe).
    """
    import unittest.mock as mock

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mod = _load_migration()
    with eng.begin() as conn:
        ctx = MigrationContext.configure(connection=conn)
        ops = Operations(ctx)
        with mock.patch.object(mod, "op", ops):
            getattr(mod, fn_name)()


class TestUpgradeSql:
    """Treibt das versandte upgrade() (nicht kopierte SQL)."""

    def test_non_null_row_mapped(self):
        eng = _make_engine()
        _create_table(eng)
        with eng.begin() as conn:
            _seed(conn, "claude-opus-4-8")

        _run_migration_fn(eng, "upgrade")

        with eng.connect() as conn:
            assert _fetch_model(conn) == "examcraft/grading"

    def test_null_row_untouched(self):
        eng = _make_engine()
        _create_table(eng)
        with eng.begin() as conn:
            _seed(conn, None)

        _run_migration_fn(eng, "upgrade")

        with eng.connect() as conn:
            assert _fetch_model(conn) is None


class TestDowngradeSql:
    """Treibt das versandte downgrade() (nicht kopierte SQL)."""

    def test_examcraft_grading_set_to_null(self):
        eng = _make_engine()
        _create_table(eng)
        with eng.begin() as conn:
            _seed(conn, "examcraft/grading")

        _run_migration_fn(eng, "downgrade")

        with eng.connect() as conn:
            assert _fetch_model(conn) is None

    def test_other_values_untouched_on_downgrade(self):
        eng = _make_engine()
        _create_table(eng)
        with eng.begin() as conn:
            _seed(conn, "some-other-model")

        _run_migration_fn(eng, "downgrade")

        with eng.connect() as conn:
            assert _fetch_model(conn) == "some-other-model"
