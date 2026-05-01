"""TF-335: switch grading_scheme FKs from SET NULL to RESTRICT.

Why
---

The original phase-1 migration set ``ON DELETE SET NULL`` on both
``exams.grading_scheme_id`` and ``institutions.default_grading_scheme_id``.
That made delete look safe at the DB level but silently corrupted exams
and institution defaults — the API tried to compensate with a pre-flight
in-use guard, but it was racy (TOCTOU between the SELECT and the DELETE
COMMIT).

RESTRICT pushes the invariant down to Postgres. The API still does a
friendly pre-check so the user sees a 409 with a useful message; if
that pre-check loses the race, the constraint surfaces an
``IntegrityError`` and the API translates it into the same 409.
"""

from typing import Union

from alembic import op


revision: str = "tf335_fk_restrict"
down_revision: Union[str, None] = "tf333_phase1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("fk_exams_grading_scheme", "exams", type_="foreignkey")
    op.create_foreign_key(
        "fk_exams_grading_scheme",
        "exams",
        "grading_schemes",
        ["grading_scheme_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_institutions_default_grading_scheme",
        "institutions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutions_default_grading_scheme",
        "institutions",
        "grading_schemes",
        ["default_grading_scheme_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_exams_grading_scheme", "exams", type_="foreignkey")
    op.create_foreign_key(
        "fk_exams_grading_scheme",
        "exams",
        "grading_schemes",
        ["grading_scheme_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_institutions_default_grading_scheme",
        "institutions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_institutions_default_grading_scheme",
        "institutions",
        "grading_schemes",
        ["default_grading_scheme_id"],
        ["id"],
        ondelete="SET NULL",
    )
