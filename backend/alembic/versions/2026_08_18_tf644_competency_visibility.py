"""Add ``team`` visibility tier + ``org_unit_id`` to competency_frameworks (TF-644).

Introduces the private/team/institution visibility model for
CompetencyFramework, mirroring ``documents.visibility``/``documentvisibility``
(TF-354), ``prompts.visibility``/``promptvisibility`` (TF-410/TF-641),
``question_reviews.visibility``/``questionreviewvisibility`` (TF-642) and
``exams.visibility``/``examvisibility`` (TF-643) — see
``models.competency.CompetencyFrameworkVisibility`` for full semantics
(governs framework browsing — ``list_frameworks``/``get_framework`` — and,
per /grilling decision, TF-644 also wires it into
``api.rag_exams.resolve_competencies_text``, the generation-time framework
lookup, which previously ignored visibility entirely).

Unlike TF-642/TF-643 (brand-new visibility column), ``competency_frameworks``
already has a ``visibility VARCHAR(20)`` column with a plain
``ck_competency_frameworks_visibility_valid`` CHECK constraint
(private/institution) since TF-400 — this is the first ticket in the TF-638
epic to *promote* an existing plain-string+CHECK column to the native
Postgres enum type the other four resources use, rather than add a fresh
column. Every existing value is guaranteed to be ``'private'`` or
``'institution'`` (enforced by the CHECK being replaced), both valid labels
of the new enum, so the type conversion cannot fail on data.

Steps:
1. Backfill any ``institution_id IS NULL`` row (orphaned framework — should
   not exist in practice, ``seed_competency_frameworks``/``create_framework``
   always set ``institution_id``, but defensive, mirrors TF-642's identical
   ``question_reviews`` backfill) to ``visibility = 'private'`` while the
   column is still text, so the institution-requires-institution invariant
   added in step 6 holds for every row from the start.
2. Create the ``competencyframeworkvisibility`` enum
   (``private``/``team``/``institution``).
3. Drop the old ``ck_competency_frameworks_visibility_valid`` CHECK —
   validity is now enforced by the enum type itself, matching Document/
   Prompt/Question/Exam (none of which carry a redundant CHECK alongside
   their enum column).
4. Convert ``visibility`` from ``VARCHAR(20)`` to
   ``competencyframeworkvisibility`` (``USING visibility::
   competencyframeworkvisibility``) and set the new server default
   ``'institution'`` — preserves every existing value; DROP DEFAULT first so
   the old text default doesn't block the type change.
5. Add ``org_unit_id`` (FK ``org_units.id``, no ondelete — deleting a
   referenced Org-Unit is rejected at the DB level, see
   ``services.org_unit_service.delete_org_unit``).
6. CHECK constraints (both added after steps 1-5, so no existing row can
   violate either):
   - ``ck_competency_frameworks_inst_vis_requires_institution``
     mirrors Document/TF-354, Question/TF-642. Unlike Exam (``institution_id``
     NOT NULL), ``competency_frameworks.institution_id`` IS nullable, so this
     is real protection here, not pure defense-in-depth.
   - ``ck_competency_frameworks_team_visibility_requires_org_unit`` mirrors
     Document/TF-620, Prompt/TF-641, Question/TF-642, Exam/TF-643
     (biconditional, both directions).
7. Indexes: ``ix_competency_frameworks_visibility``,
   ``ix_competency_frameworks_org_unit_id``.

Additive and idempotent: enum + constraints guarded by DO blocks, column/
indexes/constraint-drop guarded by IF [NOT] EXISTS, and the ALTER COLUMN
TYPE cast is a no-op if ``visibility`` is already
``competencyframeworkvisibility`` (casting an enum value to its own type
always succeeds). Safe for AUTO_MIGRATE=true deploys — no manual step.

Revision ID: tf644_competency_visibility
Revises: tf643_exam_visibility
"""

from typing import Union

from alembic import op


revision: str = "tf644_competency_visibility"
down_revision: Union[str, None] = "tf643_exam_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Defensive backfill — while the column is still text — before the
    #    institution-requires-institution invariant (step 6) is added.
    op.execute(
        "UPDATE competency_frameworks SET visibility = 'private' "
        "WHERE institution_id IS NULL"
    )

    # 2. Enum type. CREATE TYPE has no IF NOT EXISTS — guard with a DO block.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_type WHERE typname = 'competencyframeworkvisibility'
            ) THEN
                CREATE TYPE competencyframeworkvisibility AS ENUM
                    ('private', 'team', 'institution');
            END IF;
        END$$;
        """
    )

    # 3. Drop the old TF-400 CHECK — superseded by the enum type itself.
    op.execute(
        "ALTER TABLE competency_frameworks DROP CONSTRAINT IF EXISTS "
        "ck_competency_frameworks_visibility_valid"
    )

    # 4. Type conversion. DROP DEFAULT first so the old text default
    #    ('institution') doesn't block the ALTER COLUMN TYPE.
    op.execute("ALTER TABLE competency_frameworks ALTER COLUMN visibility DROP DEFAULT")
    op.execute(
        "ALTER TABLE competency_frameworks "
        "ALTER COLUMN visibility TYPE competencyframeworkvisibility "
        "USING visibility::competencyframeworkvisibility"
    )
    op.execute(
        "ALTER TABLE competency_frameworks "
        "ALTER COLUMN visibility SET DEFAULT 'institution'"
    )

    # 5. Org-Unit scoping column.
    op.execute(
        "ALTER TABLE competency_frameworks "
        "ADD COLUMN IF NOT EXISTS org_unit_id INTEGER "
        "REFERENCES org_units(id)"
    )

    # 6. Invariants. Postgres has no ADD CONSTRAINT IF NOT EXISTS, so guard
    #    with DO blocks. No existing row can violate either after steps 1-5.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname =
                    'ck_competency_frameworks_inst_vis_requires_institution'
            ) THEN
                ALTER TABLE competency_frameworks
                    ADD CONSTRAINT
                        ck_competency_frameworks_inst_vis_requires_institution
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
                WHERE conname =
                    'ck_competency_frameworks_team_visibility_requires_org_unit'
            ) THEN
                ALTER TABLE competency_frameworks
                    ADD CONSTRAINT
                        ck_competency_frameworks_team_visibility_requires_org_unit
                    CHECK ((visibility = 'team') = (org_unit_id IS NOT NULL));
            END IF;
        END$$;
        """
    )

    # 7. Indexes. Plain CREATE INDEX (runs inside the migration transaction),
    #    matching tf620/tf641/tf642/tf643: competency_frameworks is small in
    #    prod, the brief write lock is acceptable.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_competency_frameworks_visibility "
        "ON competency_frameworks (visibility)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_competency_frameworks_org_unit_id "
        "ON competency_frameworks (org_unit_id)"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE competency_frameworks DROP CONSTRAINT IF EXISTS "
        "ck_competency_frameworks_team_visibility_requires_org_unit"
    )
    op.execute(
        "ALTER TABLE competency_frameworks DROP CONSTRAINT IF EXISTS "
        "ck_competency_frameworks_inst_vis_requires_institution"
    )
    op.execute("DROP INDEX IF EXISTS ix_competency_frameworks_org_unit_id")
    op.execute("DROP INDEX IF EXISTS ix_competency_frameworks_visibility")
    op.execute("ALTER TABLE competency_frameworks DROP COLUMN IF EXISTS org_unit_id")

    # 'team' has no representation in the pre-TF-644 model — collapse to
    # 'private' before converting back so the restored CHECK below (and the
    # narrower VARCHAR CHECK it re-adds) can't fail on live 'team' rows.
    op.execute(
        "UPDATE competency_frameworks SET visibility = 'private' "
        "WHERE visibility = 'team'"
    )
    op.execute("ALTER TABLE competency_frameworks ALTER COLUMN visibility DROP DEFAULT")
    op.execute(
        "ALTER TABLE competency_frameworks "
        "ALTER COLUMN visibility TYPE VARCHAR(20) USING visibility::text"
    )
    op.execute(
        "ALTER TABLE competency_frameworks "
        "ALTER COLUMN visibility SET DEFAULT 'institution'"
    )
    op.execute("DROP TYPE IF EXISTS competencyframeworkvisibility")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_competency_frameworks_visibility_valid'
            ) THEN
                ALTER TABLE competency_frameworks
                    ADD CONSTRAINT ck_competency_frameworks_visibility_valid
                    CHECK (visibility IN ('private', 'institution'));
            END IF;
        END$$;
        """
    )
