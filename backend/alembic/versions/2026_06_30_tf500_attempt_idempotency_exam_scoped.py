"""TF-500: scope attempt idempotency per submission, not per institution.

The unique key ``(institution_id, source, source_attempt_id)`` collided across
exams: the same Moodle attempt (same email + start time) could only ever be
imported into ONE exam per institution. A second import of the same Moodle
results into a *different* exam was silently skipped (0 rows persisted,
status=succeeded), leaving that exam empty with no error.

Re-scope to ``(submission_id, source, source_attempt_id)``. A ``submission``
already encodes ``(exam_id, student_id)``, so this keeps the re-import guard
(same attempt into the same exam still dedups) while allowing the same attempt
into a different exam.

Safety: the new key is strictly *narrower* than the old one — any pair unique
under ``(institution_id, source, source_attempt_id)`` is also unique under
``(submission_id, source, source_attempt_id)`` (one submission has exactly one
institution). So no existing row can violate the new constraint; no backfill or
de-duplication is required. The now-dead institution-scoped lookup index is
dropped: the dedup query now joins via ``submissions.exam_id`` (served by
``ix_submissions_exam_id`` + the ``attempts.submission_id`` FK index), and the
inner probe on ``(submission_id, source, source_attempt_id)`` is supported by
the new unique constraint's index.

Revision ID: tf500_attempt_idem_exam
Revises: tf439_grade_logical
Create Date: 2026-06-30
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "tf500_attempt_idem_exam"
down_revision = "tf439_grade_logical"
branch_labels = None
depends_on = None


_OLD_CONSTRAINT = "uq_attempts_inst_source_attempt_id"
_NEW_CONSTRAINT = "uq_attempts_submission_source_attempt_id"
_OLD_LOOKUP_INDEX = "ix_attempts_inst_source_lookup"


def upgrade() -> None:
    # Dead after the re-scope: the dedup lookup now joins through
    # ``submissions.exam_id``; the inner probe on the new key is supported by
    # the unique constraint's own index.
    op.drop_index(_OLD_LOOKUP_INDEX, table_name="attempts")
    op.drop_constraint(_OLD_CONSTRAINT, "attempts", type_="unique")
    op.create_unique_constraint(
        _NEW_CONSTRAINT,
        "attempts",
        ["submission_id", "source", "source_attempt_id"],
    )


def downgrade() -> None:
    # NB: widening back to the institution-scoped key can fail if, while the
    # new schema was live, the same Moodle attempt was imported into more than
    # one exam of the same institution (exactly what TF-500 enables). That data
    # is incompatible with the old, stricter constraint — resolve the duplicates
    # before downgrading.
    op.drop_constraint(_NEW_CONSTRAINT, "attempts", type_="unique")
    op.create_unique_constraint(
        _OLD_CONSTRAINT,
        "attempts",
        ["institution_id", "source", "source_attempt_id"],
    )
    op.create_index(
        _OLD_LOOKUP_INDEX,
        "attempts",
        ["institution_id", "source", "source_attempt_id"],
    )
