"""Add ``visibility`` + ``org_unit_id`` to question_reviews (TF-642).

Introduces the private/team/institution visibility model for QuestionReview,
mirroring ``documents.visibility``/``documentvisibility`` (TF-354) and
``prompts.visibility``/``promptvisibility`` (TF-410/TF-641) — see
``models.question_review.QuestionReviewVisibility`` for full semantics
(governs only the exam-composition reuse pool / "Fragenpool", NOT the
Review-Queue or any review-workflow mutation — /grilling decision, TF-642).

Unlike TF-620/TF-641 (adding a ``team`` value to an *existing* enum type,
which Postgres forbids using in the same transaction it's added in — hence
those tickets' two-part migration split), this is a brand-new field on
``question_reviews``: the ``questionreviewvisibility`` enum is created with
all three values from the start, so this ships as a single migration.

Steps:
1. Create the ``questionreviewvisibility`` enum
   (``private``/``team``/``institution``).
2. Add ``question_reviews.visibility`` NOT NULL DEFAULT ``institution`` —
   preserves the pre-TF-642 status quo (every question was reachable
   institution-wide via ``TenantFilter`` alone) for all existing + newly
   generated rows; no behavior break (TF-638 decision).
3. Backfill exception: rows with ``institution_id IS NULL`` (orphaned —
   already invisible to everyone but superusers under the old
   ``TenantFilter`` equality filter, which never matches NULL) are set to
   ``private`` instead of the column default, so they (a) don't trip the
   institution-requires-institution_id invariant added in step 5, and (b)
   stay just as unreachable as before — private + no institution/org-unit
   match still excludes everyone but the creator/read_all-bypass admin, a
   strict subset of "invisible to all".
4. Add ``question_reviews.org_unit_id`` (FK ``org_units.id``, no ondelete —
   deleting a referenced Org-Unit is rejected at the DB level, see
   ``services.org_unit_service.delete_org_unit``).
5. CHECK constraints:
   - ``ck_question_reviews_institution_visibility_requires_institution``
     mirrors Document/TF-354.
   - ``ck_question_reviews_team_visibility_requires_org_unit`` mirrors
     Document/TF-620 and Prompt/TF-641 (biconditional, both directions).
   Both added after steps 2–4, so no existing row can violate them.
6. Indexes: ``ix_question_reviews_visibility``,
   ``ix_question_reviews_inst_vis_created`` (backs the Fragenpool list query
   — filter institution+visibility, ORDER BY created_at DESC), and
   ``ix_question_reviews_org_unit_id``.

Additive and idempotent (enum + constraints guarded by DO blocks,
column/indexes guarded by IF NOT EXISTS). Safe for AUTO_MIGRATE=true deploys
— no manual step.

Revision ID: tf642_question_visibility
Revises: tf641_prompt_org_unit_scope
"""

from typing import Union

from alembic import op


revision: str = "tf642_question_visibility"
down_revision: Union[str, None] = "tf641_prompt_org_unit_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enum type. CREATE TYPE has no IF NOT EXISTS — guard with a DO block.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'questionreviewvisibility'
            ) THEN
                CREATE TYPE questionreviewvisibility AS ENUM
                    ('private', 'team', 'institution');
            END IF;
        END$$;
        """
    )

    # 2. Column — NOT NULL with a server default backfills every existing row
    #    to 'institution' (metadata-only on PG 11+, no table rewrite).
    op.execute(
        "ALTER TABLE question_reviews "
        "ADD COLUMN IF NOT EXISTS visibility questionreviewvisibility "
        "NOT NULL DEFAULT 'institution'"
    )

    # 3. Orphan backfill exception (see module docstring point 3).
    op.execute(
        "UPDATE question_reviews SET visibility = 'private' "
        "WHERE institution_id IS NULL"
    )

    # 4. Org-Unit scoping column.
    op.execute(
        "ALTER TABLE question_reviews "
        "ADD COLUMN IF NOT EXISTS org_unit_id INTEGER "
        "REFERENCES org_units(id)"
    )

    # 5. Invariants. Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard
    #    with DO blocks. No existing row can violate either after steps 2-4.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_question_reviews_institution_visibility_requires_institution'
            ) THEN
                ALTER TABLE question_reviews
                    ADD CONSTRAINT
                        ck_question_reviews_institution_visibility_requires_institution
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
                WHERE conname = 'ck_question_reviews_team_visibility_requires_org_unit'
            ) THEN
                ALTER TABLE question_reviews
                    ADD CONSTRAINT
                        ck_question_reviews_team_visibility_requires_org_unit
                    CHECK ((visibility = 'team') = (org_unit_id IS NOT NULL));
            END IF;
        END$$;
        """
    )

    # 6. Indexes. Plain CREATE INDEX (runs inside the migration transaction),
    #    matching tf354_documents_visibility: question_reviews is small in
    #    prod, so the brief write lock is acceptable.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_reviews_visibility "
        "ON question_reviews (visibility)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_reviews_inst_vis_created "
        "ON question_reviews (institution_id, visibility, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_reviews_org_unit_id "
        "ON question_reviews (org_unit_id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE question_reviews DROP CONSTRAINT IF EXISTS "
        "ck_question_reviews_team_visibility_requires_org_unit"
    )
    op.execute(
        "ALTER TABLE question_reviews DROP CONSTRAINT IF EXISTS "
        "ck_question_reviews_institution_visibility_requires_institution"
    )
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_org_unit_id")
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_inst_vis_created")
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_visibility")
    op.execute("ALTER TABLE question_reviews DROP COLUMN IF EXISTS org_unit_id")
    op.execute("ALTER TABLE question_reviews DROP COLUMN IF EXISTS visibility")
    op.execute("DROP TYPE IF EXISTS questionreviewvisibility")
