"""Reconcile the migration-built schema with the models (TF-961).

``alembic upgrade head`` from an empty database (TF-434) and ``create_all``
diverged in 21 places. Production follows the migration path, so this revision
fixes the real bugs there and makes any database — migrated or ``create_all``-
built — converge on the model schema:

1. ``ix_prompts_name`` is a global UNIQUE index in production. The original
   ``unique=True`` created a unique *index*, and tf346 only dropped the
   (never existing) ``prompts_name_key`` constraint. Prompt names must be
   unique per institution only (``ux_prompts_institution_name``, tf346), so
   the index is rebuilt non-unique. No partial index for system prompts is
   needed: ``prompts.institution_id`` is NOT NULL, system prompts belong to
   the ``is_system`` institution (tf410) and are covered by the
   per-institution index.
2. ``resource_usage.institution_id`` was added nullable by ``b2c3d4e5f6a7``;
   the model requires NOT NULL. Existing NULL rows abort the migration with
   an explicit error instead of being backfilled silently.
3. The legacy tag indexes ``uix_tag_name_lower_institution`` (tf320b) and
   ``uix_global_tag_name_lower`` (tf320e) were superseded by the scope- and
   kind-aware ``ux_tags_*`` indexes (tf372, tf397) but never dropped. The
   institution one has no scope filter, so it also blocks personal tags of
   two users in the same institution; both block a ``prompt``-kind tag next
   to a ``content``-kind tag of the same name. Dropped.
4. Indexes that only ``create_all`` produces (``index=True`` on four primary
   keys, ``ix_resource_usage_institution_id``) are redundant and no longer in
   the models; dropped where present (dev databases).
5. Indexes that only migrations created are now declared in the models. They
   are (re)created with ``IF NOT EXISTS`` so ``create_all``-built dev
   databases converge as well; a no-op in production. ``compare_metadata``
   does not compare partial-index predicates, so the one index whose
   ``create_all`` variant lacked its ``WHERE`` clause
   (``ix_question_reviews_archived_at``) is rebuilt explicitly.

Idempotent (IF [NOT] EXISTS, table guards), plain statements inside the
migration transaction — safe for ``AUTO_MIGRATE=true`` deploys.

Revision ID: tf961_schema_reconcile
Revises: tf736_job_dismissed_at
"""

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "tf961_schema_reconcile"
down_revision: Union[str, None] = "tf736_job_dismissed_at"
branch_labels = None
depends_on = None

# Declared in the models since TF-961; production already has all of them.
_MODEL_INDEXES = (
    "CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id_created_at_desc "
    "ON audit_logs (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_document_tags_tag_id ON document_tags (tag_id)",
    "CREATE INDEX IF NOT EXISTS ix_documents_inst_vis_created "
    "ON documents (institution_id, visibility, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS ix_documents_pending_reindex "
    "ON documents (pending_reindex) WHERE pending_reindex = true",
    "CREATE INDEX IF NOT EXISTS ix_exams_archived_at "
    "ON exams (archived_at) WHERE archived_at IS NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_exams_inst_vis_updated "
    "ON exams (institution_id, visibility, updated_at DESC)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_grading_schemes_system_name "
    "ON grading_schemes (name) WHERE institution_id IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_institutions_single_system "
    "ON institutions (is_system) WHERE is_system",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_org_units_unique_sibling_name "
    "ON org_units (institution_id, parent_org_unit_id, name)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_org_units_unique_root_name "
    "ON org_units (institution_id, name) WHERE parent_org_unit_id IS NULL",
    "CREATE INDEX IF NOT EXISTS ix_question_reviews_inst_vis_created "
    "ON question_reviews (institution_id, visibility, created_at DESC)",
)

# Produced only by create_all from index=True on a primary key or on a column
# that already leads a composite index. Redundant, no longer in the models.
_REDUNDANT_INDEXES = (
    "ix_competencies_id",
    "ix_competency_frameworks_id",
    "ix_feedback_clusters_id",
    "ix_moodle_feedback_push_jobs_id",
    "ix_resource_usage_institution_id",
)


def upgrade() -> None:
    # 1. prompts: global unique name index -> plain lookup index. The table
    #    is premium, guard for core-only databases.
    if "prompts" in sa.inspect(op.get_bind()).get_table_names():
        op.execute("DROP INDEX IF EXISTS ix_prompts_name")
        op.execute("CREATE INDEX ix_prompts_name ON prompts (name)")

    # 2. resource_usage.institution_id NOT NULL — fail loudly on orphans.
    op.execute(
        """
        DO $$
        DECLARE
            null_rows integer;
        BEGIN
            SELECT count(*) INTO null_rows
            FROM resource_usage WHERE institution_id IS NULL;
            IF null_rows > 0 THEN
                RAISE EXCEPTION
                    'TF-961: % resource_usage row(s) with institution_id IS NULL; '
                    'assign or delete them before SET NOT NULL', null_rows;
            END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE resource_usage ALTER COLUMN institution_id SET NOT NULL")

    # 3. Superseded legacy tag indexes.
    op.execute("DROP INDEX IF EXISTS uix_tag_name_lower_institution")
    op.execute("DROP INDEX IF EXISTS uix_global_tag_name_lower")

    # 4. Redundant create_all-only indexes.
    for name in _REDUNDANT_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")

    # 5. Migration-only indexes, now declared in the models.
    for statement in _MODEL_INDEXES:
        op.execute(statement)

    # 6. create_all built ix_question_reviews_archived_at without tf396's
    #    WHERE clause; rebuild it partial (already partial in production).
    op.execute("DROP INDEX IF EXISTS ix_question_reviews_archived_at")
    op.execute(
        "CREATE INDEX ix_question_reviews_archived_at "
        "ON question_reviews (archived_at) WHERE archived_at IS NOT NULL"
    )


def downgrade() -> None:
    # Only the column constraint is reverted. The index changes are not: the
    # old state was the bug (global prompt names, blocked personal/prompt
    # tags), and restoring those unique indexes would fail on data created
    # since. The model-declared indexes predate this revision in production.
    op.execute("ALTER TABLE resource_usage ALTER COLUMN institution_id DROP NOT NULL")
