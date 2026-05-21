"""TF-333: Auswertungen — Datenmodell für Resultate-Import + Bewertung

Spec: docs/superpowers/specs/2026-04-30-exam-results-import-grading-design.md

Additive Migration (kein Datenverlust): legt 11 neue Tabellen + drei
Spalten-Erweiterungen an, alle Indexes aus Spec Abschnitt 4.3, den Partial
Unique Index auf grading_schemes(institution_id) für Default-Schemes pro
Institution, sowie den Seed der 8 System-Grading-Schemes (Spec 4.6).

`AUTO_MIGRATE=true` ist in Prod aktiv → die Migration läuft beim
Deployment automatisch. Da rein additiv, kein Downtime-Risiko.

Revision ID: tf333_phase1
Revises: tf331_display_name
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "tf333_phase1"
down_revision: Union[str, None] = "tf331_display_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# System-Grading-Schemes (Spec 4.6)
# ---------------------------------------------------------------------------

SYSTEM_GRADING_SCHEMES: list[dict] = [
    {
        "name": "Swiss 1.0–6.0",
        "display_format": "numeric",
        "config": {
            "type": "linear_segments",
            "round_to": 0.1,
            "pass_grade_label": "4.0",
            "segments": [
                {
                    "from_pct": 0,
                    "to_pct": 50,
                    "from_grade": 1.0,
                    "to_grade": 4.0,
                },
                {
                    "from_pct": 50,
                    "to_pct": 100,
                    "from_grade": 4.0,
                    "to_grade": 6.0,
                },
            ],
        },
    },
    {
        "name": "German 1.0–5.0",
        "display_format": "numeric",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 92, "grade_label": "1.0", "is_passing": True},
                {"min_pct": 81, "grade_label": "2.0", "is_passing": True},
                {"min_pct": 67, "grade_label": "3.0", "is_passing": True},
                {"min_pct": 50, "grade_label": "4.0", "is_passing": True},
                {"min_pct": 0, "grade_label": "5.0", "is_passing": False},
            ],
        },
    },
    {
        "name": "Austrian 1–5",
        "display_format": "numeric",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 90, "grade_label": "1", "is_passing": True},
                {"min_pct": 80, "grade_label": "2", "is_passing": True},
                {"min_pct": 65, "grade_label": "3", "is_passing": True},
                {"min_pct": 51, "grade_label": "4", "is_passing": True},
                {"min_pct": 0, "grade_label": "5", "is_passing": False},
            ],
        },
    },
    {
        "name": "French 0–20",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 0,
            "max_grade": 20,
            "round_to": 0.5,
            "pass_grade_label": "10",
        },
    },
    {
        "name": "Dutch 1–10",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 1,
            "max_grade": 10,
            "round_to": 0.1,
            "pass_grade_label": "5.5",
        },
    },
    {
        "name": "ECTS A–F",
        "display_format": "letter",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 90, "grade_label": "A", "is_passing": True},
                {"min_pct": 80, "grade_label": "B", "is_passing": True},
                {"min_pct": 65, "grade_label": "C", "is_passing": True},
                {"min_pct": 55, "grade_label": "D", "is_passing": True},
                {"min_pct": 50, "grade_label": "E", "is_passing": True},
                {"min_pct": 0, "grade_label": "F", "is_passing": False},
            ],
        },
    },
    {
        "name": "Prozent",
        "display_format": "numeric",
        "config": {
            "type": "linear",
            "min_pct": 0,
            "max_pct": 100,
            "min_grade": 0,
            "max_grade": 100,
            "round_to": 0.1,
            "pass_grade_label": "50",
        },
    },
    {
        "name": "Pass/Fail",
        "display_format": "pass_fail",
        "config": {
            "type": "stepped",
            "steps": [
                {"min_pct": 50, "grade_label": "Pass", "is_passing": True},
                {"min_pct": 0, "grade_label": "Fail", "is_passing": False},
            ],
        },
    },
]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1) grading_schemes (institution_id NULL = System-Scheme)
    # ------------------------------------------------------------------
    op.create_table(
        "grading_schemes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("display_format", sa.String(length=20), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column(
            "is_default_for_institution",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "institution_id", "name", name="uq_grading_schemes_institution_name"
        ),
        sa.CheckConstraint(
            "display_format IN ('numeric', 'letter', 'pass_fail')",
            name="check_grading_scheme_display_format",
        ),
    )
    op.create_index(
        op.f("ix_grading_schemes_id"), "grading_schemes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_grading_schemes_institution_id"),
        "grading_schemes",
        ["institution_id"],
        unique=False,
    )
    # Partial Unique Index: höchstens ein Default pro Institution
    op.create_index(
        "uq_grading_schemes_default_per_institution",
        "grading_schemes",
        ["institution_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_default_for_institution = true AND institution_id IS NOT NULL"
        ),
    )
    # System-Schemes (institution_id IS NULL) müssen eindeutig sein.
    # Postgres behandelt NULL in Unique-Constraints standardmässig als
    # "distinct", was beim Re-Run einer fehlgeschlagenen Migration zu
    # stillem Duplizieren der 8 Default-Schemes führen würde. Dieser
    # partielle Unique-Index lässt Duplikat-Inserts laut crashen statt
    # Operator-unsichtbar einen zweiten "Swiss 1.0–6.0" anzulegen.
    op.create_index(
        "uq_grading_schemes_system_name",
        "grading_schemes",
        ["name"],
        unique=True,
        postgresql_where=sa.text("institution_id IS NULL"),
    )

    # ------------------------------------------------------------------
    # 2) Seed System-Grading-Schemes
    # ------------------------------------------------------------------
    grading_schemes_seed = sa.table(
        "grading_schemes",
        sa.column("institution_id", sa.Integer),
        sa.column("name", sa.String),
        sa.column("display_format", sa.String),
        sa.column("config", sa.JSON),
        sa.column("is_default_for_institution", sa.Boolean),
    )
    op.bulk_insert(
        grading_schemes_seed,
        [
            {
                "institution_id": None,
                "name": s["name"],
                "display_format": s["display_format"],
                "config": s["config"],
                "is_default_for_institution": False,
            }
            for s in SYSTEM_GRADING_SCHEMES
        ],
    )

    # ------------------------------------------------------------------
    # 3) Studierenden-Stammdaten
    # ------------------------------------------------------------------
    op.create_table(
        "students",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "institution_id", "external_id", name="uq_students_institution_external"
        ),
    )
    op.create_index(op.f("ix_students_id"), "students", ["id"], unique=False)
    op.create_index(
        op.f("ix_students_institution_id"),
        "students",
        ["institution_id"],
        unique=False,
    )

    op.create_table(
        "student_classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "institution_id",
            "name",
            name="uq_student_classes_institution_name",
        ),
    )
    op.create_index(
        op.f("ix_student_classes_id"), "student_classes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_student_classes_institution_id"),
        "student_classes",
        ["institution_id"],
        unique=False,
    )

    op.create_table(
        "student_class_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["class_id"], ["student_classes.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "student_id", "class_id", name="uq_student_class_memberships"
        ),
    )
    op.create_index(
        op.f("ix_student_class_memberships_id"),
        "student_class_memberships",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_class_memberships_student_id"),
        "student_class_memberships",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_student_class_memberships_class_id"),
        "student_class_memberships",
        ["class_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 4) Submissions / Attempts / Answers / Grades
    # ------------------------------------------------------------------
    # submissions referenziert attempts (graded_attempt_id) — zirkulärer
    # FK; deshalb erst submissions ohne diesen FK, dann attempts, dann FK
    # nachträglich per ALTER hinzufügen.
    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column("graded_attempt_id", sa.Integer(), nullable=True),
        sa.Column(
            "scoring_strategy",
            sa.String(length=20),
            server_default=sa.text("'latest'"),
            nullable=False,
        ),
        sa.Column(
            "total_points_awarded",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "total_points_max",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "percentage", sa.Float(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "grade_status",
            sa.String(length=30),
            server_default=sa.text("'pending_review'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_id"], ["students.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "exam_id", "student_id", name="uq_submissions_exam_student"
        ),
        sa.CheckConstraint(
            "scoring_strategy IN ('latest', 'best', 'first')",
            name="check_submission_scoring_strategy",
        ),
        sa.CheckConstraint(
            "grade_status IN ('pending_review', 'partially_reviewed', "
            "'fully_reviewed', 'import_grading_failed')",
            name="check_submission_grade_status",
        ),
        sa.CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="check_submission_percentage_range",
        ),
        sa.CheckConstraint(
            "total_points_awarded >= 0 AND total_points_max >= 0 "
            "AND total_points_awarded <= total_points_max",
            name="check_submission_points_bounds",
        ),
    )
    op.create_index(op.f("ix_submissions_id"), "submissions", ["id"], unique=False)
    op.create_index(
        op.f("ix_submissions_exam_id"), "submissions", ["exam_id"], unique=False
    )
    op.create_index(
        op.f("ix_submissions_student_id"),
        "submissions",
        ["student_id"],
        unique=False,
    )
    op.create_index(
        "ix_submissions_exam_grade_status",
        "submissions",
        ["exam_id", "grade_status"],
        unique=False,
    )

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        # institution_id is denormalised so the (source, source_attempt_id)
        # idempotency key can be scoped per tenant.
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        # 512 covers worst-case composed key (RFC 5321 max email + ISO ts + separators + n).
        sa.Column("source_attempt_id", sa.String(length=512), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["submission_id"], ["submissions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "submission_id",
            "attempt_number",
            name="uq_attempts_submission_number",
        ),
        sa.UniqueConstraint(
            "institution_id",
            "source",
            "source_attempt_id",
            name="uq_attempts_inst_source_attempt_id",
        ),
        sa.CheckConstraint(
            "source IN ('moodle_csv', 'moodle_api')",
            name="check_attempt_source",
        ),
        sa.CheckConstraint(
            "attempt_number >= 1",
            name="check_attempt_number_positive",
        ),
    )
    op.create_index(op.f("ix_attempts_id"), "attempts", ["id"], unique=False)
    op.create_index(
        op.f("ix_attempts_submission_id"),
        "attempts",
        ["submission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attempts_institution_id"),
        "attempts",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        "ix_attempts_inst_source_lookup",
        "attempts",
        ["institution_id", "source", "source_attempt_id"],
        unique=False,
    )

    # Zirkulärer FK: submissions.graded_attempt_id → attempts.id
    op.create_foreign_key(
        "fk_submissions_graded_attempt",
        "submissions",
        "attempts",
        ["graded_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "attempt_answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("exam_question_id", sa.Integer(), nullable=False),
        sa.Column("given_answer", sa.Text(), nullable=True),
        sa.Column("moodle_points_awarded", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["attempt_id"], ["attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["exam_question_id"], ["exam_questions.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "attempt_id",
            "exam_question_id",
            name="uq_attempt_answers_attempt_question",
        ),
    )
    op.create_index(
        op.f("ix_attempt_answers_id"), "attempt_answers", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_attempt_answers_attempt_id"),
        "attempt_answers",
        ["attempt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_attempt_answers_exam_question_id"),
        "attempt_answers",
        ["exam_question_id"],
        unique=False,
    )

    op.create_table(
        "grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_answer_id", sa.Integer(), nullable=False, unique=True),
        sa.Column(
            "points_awarded",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "points_max", sa.Float(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("llm_confidence", sa.Float(), nullable=True),
        sa.Column("llm_rationale", sa.Text(), nullable=True),
        sa.Column("llm_matched_aspects", sa.JSON(), nullable=True),
        sa.Column("llm_missing_aspects", sa.JSON(), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["attempt_answer_id"], ["attempt_answers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('proposed', 'approved', 'manual_override')",
            name="check_grade_status",
        ),
        sa.CheckConstraint(
            "points_awarded >= 0 AND points_max >= 0 AND points_awarded <= points_max",
            name="check_grade_points_bounds",
        ),
        sa.CheckConstraint(
            "llm_confidence IS NULL OR (llm_confidence >= 0 AND llm_confidence <= 1)",
            name="check_grade_llm_confidence_range",
        ),
    )
    op.create_index(op.f("ix_grades_id"), "grades", ["id"], unique=False)
    op.create_index(op.f("ix_grades_status"), "grades", ["status"], unique=False)

    op.create_table(
        "grade_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("grade_id", sa.Integer(), nullable=False),
        sa.Column("old_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("old_points", sa.Float(), nullable=True),
        sa.Column("new_points", sa.Float(), nullable=True),
        sa.Column("changed_by", sa.Integer(), nullable=True),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["grade_id"], ["grades.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["changed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("ix_grade_history_id"), "grade_history", ["id"], unique=False)
    op.create_index(
        op.f("ix_grade_history_grade_id"),
        "grade_history",
        ["grade_id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 5) Import-Jobs + Moodle-Connection
    # ------------------------------------------------------------------
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("exam_id", sa.Integer(), nullable=False),
        sa.Column("driver_name", sa.String(length=50), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'queued'"),
            nullable=False,
        ),
        sa.Column(
            "rows_processed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "rows_failed",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("error_log", sa.JSON(), nullable=True),
        sa.Column("source_metadata", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["exam_id"], ["exams.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by"], ["users.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed')",
            name="check_import_job_status",
        ),
        sa.CheckConstraint(
            "driver_name IN ('moodle_csv', 'moodle_api')",
            name="check_import_job_driver",
        ),
    )
    op.create_index(op.f("ix_import_jobs_id"), "import_jobs", ["id"], unique=False)
    op.create_index(
        op.f("ix_import_jobs_institution_id"),
        "import_jobs",
        ["institution_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_jobs_exam_id"),
        "import_jobs",
        ["exam_id"],
        unique=False,
    )
    op.create_index(
        "ix_import_jobs_exam_status",
        "import_jobs",
        ["exam_id", "status"],
        unique=False,
    )

    op.create_table(
        "moodle_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("base_url", sa.String(length=500), nullable=False),
        sa.Column("token_encrypted", sa.Text(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["institution_id"], ["institutions.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        op.f("ix_moodle_connections_id"),
        "moodle_connections",
        ["id"],
        unique=False,
    )

    # ------------------------------------------------------------------
    # 6) Erweiterungen bestehender Tabellen
    # ------------------------------------------------------------------
    op.add_column(
        "exams",
        sa.Column("grading_scheme_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exams_grading_scheme",
        "exams",
        "grading_schemes",
        ["grading_scheme_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "exam_questions",
        sa.Column("external_refs", sa.JSON(), nullable=True),
    )

    op.add_column(
        "institutions",
        sa.Column("default_grading_scheme_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_institutions_default_grading_scheme",
        "institutions",
        "grading_schemes",
        ["default_grading_scheme_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Rollback Phase-1-Datenmodell.

    Reversibel, aber DESTRUKTIV: alle Submissions, Attempts, Grades und
    History-Einträge gehen verloren. System-Grading-Schemes ebenfalls.

    Mit ``AUTO_MIGRATE=true`` in Prod hat der Operator beim Container-
    Start keine Möglichkeit, vorher ein Backup zu ziehen. Deshalb sind
    zwei Env-Variablen Pflicht für genau diesen Downgrade:

    * ``ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE=1`` — explizite Bestätigung
      durch den Operator.
    * ``ALEMBIC_BACKUP_TIMESTAMP`` — der Operator klebt den Dateinamen
      des ``pg_dump``-Backups hier rein. Wird unverändert in den
      Server-Log geschrieben, damit man später nachvollziehen kann,
      welches Backup zu welchem Downgrade gehört.

    Der Standard-Auto-Migrate-Pfad führt nur Upgrades aus, nicht
    Downgrades — beide Variablen sind also nur in einer manuellen
    Rollback-Session nötig.
    """
    import logging
    import os

    if os.environ.get("ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE") != "1":
        raise RuntimeError(
            "Downgrade von tf333_phase1 löscht Submissions/Attempts/Grades. "
            "Vorgehen:\n"
            "  1. pg_dump des aktuellen Stands ziehen.\n"
            "  2. ALEMBIC_BACKUP_TIMESTAMP=<dump-dateiname> setzen.\n"
            "  3. ALEMBIC_ALLOW_DESTRUCTIVE_DOWNGRADE=1 setzen.\n"
            "  4. alembic downgrade -1 erneut ausführen."
        )

    backup_ref = os.environ.get("ALEMBIC_BACKUP_TIMESTAMP", "").strip()
    if not backup_ref:
        raise RuntimeError(
            "ALEMBIC_BACKUP_TIMESTAMP fehlt — bitte den pg_dump-"
            "Dateinamen oder einen ISO-Zeitstempel als Backup-Referenz "
            "setzen, damit der Audit-Log nachvollziehbar bleibt."
        )

    logging.getLogger("alembic.runtime.migration").warning(
        "tf333_phase1 DESTRUCTIVE downgrade: backup_ref=%r — Submissions/"
        "Attempts/Grades werden gelöscht.",
        backup_ref,
    )

    # Erst FK-Spalten in bestehenden Tabellen droppen, damit die Targets
    # frei werden.
    op.drop_constraint(
        "fk_institutions_default_grading_scheme",
        "institutions",
        type_="foreignkey",
    )
    op.drop_column("institutions", "default_grading_scheme_id")

    op.drop_column("exam_questions", "external_refs")

    op.drop_constraint("fk_exams_grading_scheme", "exams", type_="foreignkey")
    op.drop_column("exams", "grading_scheme_id")

    # Moodle-Connection / Import-Jobs
    op.drop_index(op.f("ix_moodle_connections_id"), table_name="moodle_connections")
    op.drop_table("moodle_connections")

    op.drop_index("ix_import_jobs_exam_status", table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_exam_id"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_institution_id"), table_name="import_jobs")
    op.drop_index(op.f("ix_import_jobs_id"), table_name="import_jobs")
    op.drop_table("import_jobs")

    # Grade-Historie + Grades + AttemptAnswers
    op.drop_index(op.f("ix_grade_history_grade_id"), table_name="grade_history")
    op.drop_index(op.f("ix_grade_history_id"), table_name="grade_history")
    op.drop_table("grade_history")

    op.drop_index(op.f("ix_grades_status"), table_name="grades")
    op.drop_index(op.f("ix_grades_id"), table_name="grades")
    op.drop_table("grades")

    op.drop_index(
        op.f("ix_attempt_answers_exam_question_id"), table_name="attempt_answers"
    )
    op.drop_index(op.f("ix_attempt_answers_attempt_id"), table_name="attempt_answers")
    op.drop_index(op.f("ix_attempt_answers_id"), table_name="attempt_answers")
    op.drop_table("attempt_answers")

    # Zirkulärer FK lösen, dann attempts, dann submissions
    op.drop_constraint(
        "fk_submissions_graded_attempt", "submissions", type_="foreignkey"
    )

    op.drop_index("ix_attempts_inst_source_lookup", table_name="attempts")
    op.drop_index(op.f("ix_attempts_institution_id"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_submission_id"), table_name="attempts")
    op.drop_index(op.f("ix_attempts_id"), table_name="attempts")
    op.drop_table("attempts")

    op.drop_index("ix_submissions_exam_grade_status", table_name="submissions")
    op.drop_index(op.f("ix_submissions_student_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_exam_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_id"), table_name="submissions")
    op.drop_table("submissions")

    # Studierenden-Stammdaten
    op.drop_index(
        op.f("ix_student_class_memberships_class_id"),
        table_name="student_class_memberships",
    )
    op.drop_index(
        op.f("ix_student_class_memberships_student_id"),
        table_name="student_class_memberships",
    )
    op.drop_index(
        op.f("ix_student_class_memberships_id"),
        table_name="student_class_memberships",
    )
    op.drop_table("student_class_memberships")

    op.drop_index(
        op.f("ix_student_classes_institution_id"), table_name="student_classes"
    )
    op.drop_index(op.f("ix_student_classes_id"), table_name="student_classes")
    op.drop_table("student_classes")

    op.drop_index(op.f("ix_students_institution_id"), table_name="students")
    op.drop_index(op.f("ix_students_id"), table_name="students")
    op.drop_table("students")

    # Zuletzt grading_schemes
    op.drop_index("uq_grading_schemes_system_name", table_name="grading_schemes")
    op.drop_index(
        "uq_grading_schemes_default_per_institution", table_name="grading_schemes"
    )
    op.drop_index(
        op.f("ix_grading_schemes_institution_id"), table_name="grading_schemes"
    )
    op.drop_index(op.f("ix_grading_schemes_id"), table_name="grading_schemes")
    op.drop_table("grading_schemes")
