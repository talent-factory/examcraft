"""Guards the invariant `services.gdpr_deletion_service.delete_user_and_gdpr_data`
depends on entirely (TF-745 PR review fix): every column that references
`users.id` must declare `ondelete="CASCADE"` or `ondelete="SET NULL"` on
the SQLAlchemy model.

Scope, precisely: this only inspects `Base.metadata` (the Python model
declarations), never the real database. It catches a NEW `users.id` FK
added to a model WITHOUT any `ondelete` at all — a straightforward
model-review-time guard. It CANNOT catch model/migration drift, where the
model declares `ondelete="CASCADE"` but the migration that created the
table never applied it to the real database (`Base.metadata.create_all()`,
which this test and the regular test suite both use, always reproduces
the model's DDL, never a hand-drifted migration). This PR's own migration
(`2026_08_30_tf745_fk_ondelete_cascade.py`) had to fix exactly that for
`question_generation_jobs`: the model already declared `ondelete="CASCADE"`
correctly, but the migration that created the table never applied it — a
case this test cannot see. `wizard_sessions` was a *different* failure
mode in the same migration: neither the model nor any migration declared
`ondelete` at all (fixed by correcting the model itself, in this same PR —
see commit `14883253`), so a version of this test run *after* that model
fix would in fact have passed for `wizard_sessions` all along; it's the
`question_generation_jobs`-style drift (model right, DB wrong) that stays
permanently outside this test's reach. Real migration-drift protection is
`test_tf745_fk_ondelete_migration_safety.py` plus, for a new production
database, manually verifying the applied migration against a throwaway DB
(see the project's "Einzel-Migration verifizieren" convention) — there is
no fully automated guard against that class of drift.

Only covers models registered on `Base.metadata` at collection time — in
the standard core/backend test run that's every core model (imported
transitively via `from main import app` in conftest.py) plus whatever
conftest.py imports explicitly. Premium-only models (`wizard_sessions`,
`chat_sessions`, `prompts`) are NOT registered here and therefore not
checked by this test at all; they get their own dedicated FK/cascade tests
in `premium/backend/tests/`.
"""

from database import Base


def test_every_users_id_foreign_key_has_ondelete_policy() -> None:
    violations = []

    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            referenced_table = fk.column.table.name
            referenced_column = fk.column.name
            if referenced_table != "users" or referenced_column != "id":
                continue

            ondelete = (fk.ondelete or "").upper()
            if ondelete not in ("CASCADE", "SET NULL"):
                violations.append(
                    f"{table.name}.{fk.parent.name} -> users.id "
                    f"(ondelete={fk.ondelete!r})"
                )

    assert not violations, (
        "Diese Spalten referenzieren users.id ohne gültige ondelete-Policy "
        "(muss CASCADE oder SET NULL sein) — ein `db.delete(user)` in "
        "gdpr_deletion_service.py würde hier mit IntegrityError gegen "
        "NO ACTION laufen:\n" + "\n".join(sorted(violations))
    )
