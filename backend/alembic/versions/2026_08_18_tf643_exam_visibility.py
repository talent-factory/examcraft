"""Add ``visibility`` + ``org_unit_id`` to exams (TF-643).

Introduces the private/team/institution visibility model for Exam,
mirroring ``documents.visibility``/``documentvisibility`` (TF-354),
``prompts.visibility``/``promptvisibility`` (TF-410/TF-641) and
``question_reviews.visibility``/``questionreviewvisibility`` (TF-642) — see
``models.exam.ExamVisibility`` for full semantics (governs exam browsing —
``list_exams``/``get_exam`` — plus, without the ``exams:read_all`` bypass,
every exam-mutation endpoint; deliberately NOT ``submissions:grade``/
``submissions:read``, and independent of ``ExamStatus`` — /grilling
decisions, TF-643).

Brand-new field on ``exams`` (like TF-642, unlike TF-620/TF-641): the
``examvisibility`` enum is created with all three values from the start, so
this ships as a single migration, not a two-part split.

Steps:
1. Create the ``examvisibility`` enum (``private``/``team``/``institution``).
2. Add ``exams.visibility`` NOT NULL DEFAULT ``institution`` — preserves the
   pre-TF-643 status quo (every exam was reachable institution-wide via
   ``TenantFilter`` alone) for all existing + newly created rows; no
   behavior break (TF-638 decision). Unlike TF-642 (``QuestionReview
   .institution_id`` is nullable), ``Exam.institution_id`` has been
   ``NOT NULL`` since the table's first migration, so there is no orphaned
   ``institution_id IS NULL`` row to except from this default — every exam
   simply gets ``institution``.
3. Add ``exams.org_unit_id`` (FK ``org_units.id``, no ondelete — deleting a
   referenced Org-Unit is rejected at the DB level, see
   ``services.org_unit_service.delete_org_unit``).
4. CHECK constraints:
   - ``ck_exams_institution_visibility_requires_institution`` mirrors
     Document/TF-354. Given point 2, ``institution_id IS NOT NULL`` always
     holds for every row regardless of ``visibility`` — this constraint is
     currently unreachable/tautological for ``exams``, kept only as
     defense-in-depth should the column ever become nullable.
   - ``ck_exams_team_visibility_requires_org_unit`` mirrors Document/TF-620,
     Prompt/TF-641 and Question/TF-642 (biconditional, both directions) —
     this one IS reachable and enforced.
   Both added after steps 2-3, so no existing row can violate them.
5. Indexes: ``ix_exams_visibility``, ``ix_exams_inst_vis_updated`` (backs the
   exam list query — filter institution+visibility, ORDER BY updated_at
   DESC, matching ``list_exams``'s actual sort column), and
   ``ix_exams_org_unit_id``.

Additive and idempotent (enum + constraints guarded by DO blocks,
column/indexes guarded by IF NOT EXISTS). Safe for AUTO_MIGRATE=true deploys
— no manual step.

Revision ID: tf643_exam_visibility
Revises: tf642_question_visibility
"""

from typing import Union

from alembic import op


revision: str = "tf643_exam_visibility"
down_revision: Union[str, None] = "tf642_question_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enum type. CREATE TYPE has no IF NOT EXISTS — guard with a DO block.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'examvisibility'
            ) THEN
                CREATE TYPE examvisibility AS ENUM
                    ('private', 'team', 'institution');
            END IF;
        END$$;
        """
    )

    # 2. Column — NOT NULL with a server default backfills every existing row
    #    to 'institution' (metadata-only on PG 11+, no table rewrite).
    op.execute(
        "ALTER TABLE exams "
        "ADD COLUMN IF NOT EXISTS visibility examvisibility "
        "NOT NULL DEFAULT 'institution'"
    )

    # 3. Org-Unit scoping column.
    op.execute(
        "ALTER TABLE exams "
        "ADD COLUMN IF NOT EXISTS org_unit_id INTEGER "
        "REFERENCES org_units(id)"
    )

    # 4. Invariants. Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard
    #    with DO blocks. No existing row can violate either after steps 2-3.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_exams_institution_visibility_requires_institution'
            ) THEN
                ALTER TABLE exams
                    ADD CONSTRAINT
                        ck_exams_institution_visibility_requires_institution
                    CHECK (visibility <> 'institution' OR institution_id IS NOT NULL);
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_exams_team_visibility_requires_org_unit'
            ) THEN
                ALTER TABLE exams
                    ADD CONSTRAINT
                        ck_exams_team_visibility_requires_org_unit
                    CHECK ((visibility = 'team') = (org_unit_id IS NOT NULL));
            END IF;
        END$$;
        """
    )

    # 5. Indexes. Plain CREATE INDEX (runs inside the migration transaction),
    #    matching tf354_documents_visibility / tf642_question_visibility:
    #    exams is small in prod, so the brief write lock is acceptable.
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_visibility ON exams (visibility)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_inst_vis_updated "
        "ON exams (institution_id, visibility, updated_at DESC)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_exams_org_unit_id ON exams (org_unit_id)")


def downgrade() -> None:
    op.execute(
        "ALTER TABLE exams DROP CONSTRAINT IF EXISTS "
        "ck_exams_team_visibility_requires_org_unit"
    )
    op.execute(
        "ALTER TABLE exams DROP CONSTRAINT IF EXISTS "
        "ck_exams_institution_visibility_requires_institution"
    )
    op.execute("DROP INDEX IF EXISTS ix_exams_org_unit_id")
    op.execute("DROP INDEX IF EXISTS ix_exams_inst_vis_updated")
    op.execute("DROP INDEX IF EXISTS ix_exams_visibility")
    op.execute("ALTER TABLE exams DROP COLUMN IF EXISTS org_unit_id")
    op.execute("ALTER TABLE exams DROP COLUMN IF EXISTS visibility")
    op.execute("DROP TYPE IF EXISTS examvisibility")
