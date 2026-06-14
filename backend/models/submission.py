"""Submissions / Attempts / Grades + ImportJob models.

A Submission bundles the (potentially multiple) attempts of one student
on one exam. Each attempt persists every answer as an AttemptAnswer; the
GradingService produces exactly one Grade per AttemptAnswer.
GradeHistory is the audit trail for status or point changes.

ImportJob records the lifecycle of one results import including
per-row tolerance (``error_log``). The error_log entries match
``services.import_drivers.payloads.ImportRowError`` plus optional
``step``/``details`` fields populated by ImportService.

MoodleConnection stores per-institution Web Service credentials
(Fernet-encrypted token). The model is wired up here as forward-looking
infrastructure for the moodle_api driver — Phase 1 (CSV-only) does not
read from it.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

from database import Base
from enums import (
    GradeStatus,
    ImportJobStatus,
    ScoringStrategy,
    SubmissionGradeStatus,
)


_SUBMISSION_GRADE_STATUSES = frozenset(s.value for s in SubmissionGradeStatus)
_SCORING_STRATEGIES = frozenset(s.value for s in ScoringStrategy)
_GRADE_STATUSES = frozenset(s.value for s in GradeStatus)
_IMPORT_JOB_STATUSES = frozenset(s.value for s in ImportJobStatus)


class Submission(Base):
    """All attempts a student made on a given exam."""

    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    student_id = Column(
        Integer,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # use_alter: circular FK Submission ↔ Attempt — both tables are
    # created independently; the FK is added afterwards via ALTER.
    graded_attempt_id = Column(
        Integer,
        ForeignKey("attempts.id", ondelete="SET NULL", use_alter=True),
        nullable=True,
    )

    scoring_strategy = Column(String(20), default="latest", nullable=False)
    total_points_awarded = Column(Float, default=0.0, nullable=False)
    total_points_max = Column(Float, default=0.0, nullable=False)
    percentage = Column(Float, default=0.0, nullable=False)
    grade_status = Column(String(30), default="pending_review", nullable=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    exam = relationship("Exam", back_populates="submissions", foreign_keys=[exam_id])
    student = relationship("Student", back_populates="submissions")
    attempts = relationship(
        "Attempt",
        back_populates="submission",
        cascade="all, delete-orphan",
        foreign_keys="Attempt.submission_id",
    )
    # post_update because the FK to Attempt is set after both rows
    # exist (circular dependency, see use_alter above).
    graded_attempt = relationship(
        "Attempt",
        foreign_keys=[graded_attempt_id],
        post_update=True,
    )

    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_submissions_exam_student"),
        CheckConstraint(
            "scoring_strategy IN ('latest', 'best', 'first')",
            name="check_submission_scoring_strategy",
        ),
        CheckConstraint(
            "grade_status IN ('pending_review', 'partially_reviewed', "
            "'fully_reviewed', 'import_grading_failed')",
            name="check_submission_grade_status",
        ),
        CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="check_submission_percentage_range",
        ),
        CheckConstraint(
            "total_points_awarded >= 0 AND total_points_max >= 0 "
            "AND total_points_awarded <= total_points_max",
            name="check_submission_points_bounds",
        ),
        Index("ix_submissions_exam_grade_status", "exam_id", "grade_status"),
    )

    @validates("grade_status")
    def _validate_grade_status(self, _key: str, value: str) -> str:
        if value not in _SUBMISSION_GRADE_STATUSES:
            raise ValueError(
                f"Submission.grade_status {value!r} ungültig — erlaubt: "
                f"{sorted(_SUBMISSION_GRADE_STATUSES)}"
            )
        return value

    @validates("scoring_strategy")
    def _validate_scoring_strategy(self, _key: str, value: str) -> str:
        if value not in _SCORING_STRATEGIES:
            raise ValueError(
                f"Submission.scoring_strategy {value!r} ungültig — erlaubt: "
                f"{sorted(_SCORING_STRATEGIES)}"
            )
        return value

    @validates("graded_attempt")
    def _validate_graded_attempt(self, _key: str, attempt):
        """Reject pointing graded_attempt at another submission's attempt.

        Without this guard a grading bug could make Submission #5's
        graded_attempt_id point at Submission #99's attempt, and the
        denormalised ``total_points_awarded`` aggregate would silently
        report wrong numbers. Only checks the relationship form because
        we usually don't have the Attempt loaded when only the FK id is
        set; for the id-only path the (submission_id, attempt_number)
        unique-constraint plus ImportService's flow already guarantees
        correctness.
        """
        if attempt is not None and attempt.submission_id is not None:
            if self.id is not None and attempt.submission_id != self.id:
                raise ValueError(
                    f"Submission.graded_attempt verweist auf Attempt "
                    f"{attempt.id} (submission_id={attempt.submission_id}) "
                    f"— gehört nicht zu Submission {self.id}"
                )
        return attempt

    def __repr__(self):
        return (
            f"<Submission(id={self.id}, exam_id={self.exam_id}, "
            f"student_id={self.student_id}, status={self.grade_status})>"
        )


class Attempt(Base):
    """A single attempt (n per Submission, Moodle attempt number)."""

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(
        Integer,
        ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # institution_id is denormalised onto attempts so the (source,
    # source_attempt_id) idempotency key can be scoped per tenant —
    # otherwise two institutions with overlapping Moodle exports
    # collide on a globally-unique constraint and one tenant's import
    # is silently skipped.
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attempt_number = Column(Integer, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    submitted_at = Column(DateTime(timezone=True), nullable=True)

    source = Column(String(30), nullable=False)
    # 512 covers the worst-case composed key: RFC 5321 max email (254) +
    # ISO timestamp + separators + attempt_number. ``MoodleJsonDriver._compose_source_attempt_id``
    # documents the format; changing it is a data-migration boundary.
    source_attempt_id = Column(String(512), nullable=True)
    raw_payload = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    submission = relationship(
        "Submission", back_populates="attempts", foreign_keys=[submission_id]
    )
    answers = relationship(
        "AttemptAnswer", back_populates="attempt", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "submission_id", "attempt_number", name="uq_attempts_submission_number"
        ),
        UniqueConstraint(
            "institution_id",
            "source",
            "source_attempt_id",
            name="uq_attempts_inst_source_attempt_id",
        ),
        Index(
            "ix_attempts_inst_source_lookup",
            "institution_id",
            "source",
            "source_attempt_id",
        ),
        CheckConstraint(
            # 'moodle_csv' kept for historical rows (TF-423 removed the CSV
            # driver; the JSON driver writes 'moodle_json').
            "source IN ('moodle_csv', 'moodle_api', 'moodle_json')",
            name="check_attempt_source",
        ),
        CheckConstraint(
            "attempt_number >= 1",
            name="check_attempt_number_positive",
        ),
    )

    def __repr__(self):
        return (
            f"<Attempt(id={self.id}, submission_id={self.submission_id}, "
            f"attempt_number={self.attempt_number}, source={self.source})>"
        )


class AttemptAnswer(Base):
    """Answer to one question within one attempt."""

    __tablename__ = "attempt_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(
        Integer,
        ForeignKey("attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_question_id = Column(
        Integer,
        ForeignKey("exam_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    given_answer = Column(Text, nullable=True)
    moodle_points_awarded = Column(Float, nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    attempt = relationship("Attempt", back_populates="answers")
    grade = relationship(
        "Grade",
        back_populates="attempt_answer",
        cascade="all, delete-orphan",
        uselist=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "attempt_id",
            "exam_question_id",
            name="uq_attempt_answers_attempt_question",
        ),
    )

    def __repr__(self):
        return (
            f"<AttemptAnswer(id={self.id}, attempt_id={self.attempt_id}, "
            f"exam_question_id={self.exam_question_id})>"
        )


class Grade(Base):
    """ExamCraft grade for one AttemptAnswer."""

    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    attempt_answer_id = Column(
        Integer,
        ForeignKey("attempt_answers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    points_awarded = Column(Float, default=0.0, nullable=False)
    points_max = Column(Float, default=0.0, nullable=False)
    status = Column(String(30), default="proposed", nullable=False, index=True)
    is_correct = Column(Boolean, nullable=True)
    llm_confidence = Column(Float, nullable=True)
    llm_rationale = Column(Text, nullable=True)
    llm_matched_aspects = Column(JSON, nullable=True)
    llm_missing_aspects = Column(JSON, nullable=True)

    reviewer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_note = Column(Text, nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    attempt_answer = relationship("AttemptAnswer", back_populates="grade")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    history = relationship(
        "GradeHistory",
        back_populates="grade",
        cascade="all, delete-orphan",
        order_by="GradeHistory.changed_at",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed', 'approved', 'manual_override')",
            name="check_grade_status",
        ),
        CheckConstraint(
            "points_awarded >= 0 AND points_max >= 0 AND points_awarded <= points_max",
            name="check_grade_points_bounds",
        ),
        CheckConstraint(
            "llm_confidence IS NULL OR (llm_confidence >= 0 AND llm_confidence <= 1)",
            name="check_grade_llm_confidence_range",
        ),
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        if value not in _GRADE_STATUSES:
            raise ValueError(
                f"Grade.status {value!r} ungültig — erlaubt: {sorted(_GRADE_STATUSES)}"
            )
        return value

    def __repr__(self):
        return (
            f"<Grade(id={self.id}, attempt_answer_id={self.attempt_answer_id}, "
            f"points={self.points_awarded}/{self.points_max}, "
            f"status={self.status})>"
        )


class GradeHistory(Base):
    """Audit trail for status and point changes on a Grade."""

    __tablename__ = "grade_history"

    id = Column(Integer, primary_key=True, index=True)
    grade_id = Column(
        Integer,
        ForeignKey("grades.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    old_points = Column(Float, nullable=True)
    new_points = Column(Float, nullable=True)
    changed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    change_reason = Column(Text, nullable=True)
    changed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    grade = relationship("Grade", back_populates="history")
    changed_by_user = relationship("User", foreign_keys=[changed_by])

    def __repr__(self):
        return (
            f"<GradeHistory(id={self.id}, grade_id={self.grade_id}, "
            f"{self.old_status}->{self.new_status})>"
        )


class ImportJob(Base):
    """Lifecycle record of one results import (CSV or API)."""

    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    driver_name = Column(String(50), nullable=False)
    status = Column(String(20), default="queued", nullable=False)

    rows_processed = Column(Integer, default=0, nullable=False)
    rows_failed = Column(Integer, default=0, nullable=False)
    # error_log shape: list of {row_index: int, reason: str, step?: str,
    # details?: object}. Format intentionally documented by keys, not by
    # producer name — ImportService and the import drivers populate it.
    error_log = Column(JSON, nullable=True)
    source_metadata = Column(JSON, nullable=True)

    triggered_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="import_jobs")
    exam = relationship("Exam", back_populates="import_jobs", foreign_keys=[exam_id])
    triggered_by_user = relationship("User", foreign_keys=[triggered_by])

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'partial', 'failed')",
            name="check_import_job_status",
        ),
        CheckConstraint(
            # 'moodle_csv' kept for historical import_jobs rows (TF-423).
            "driver_name IN ('moodle_csv', 'moodle_api', 'moodle_json')",
            name="check_import_job_driver",
        ),
        Index("ix_import_jobs_exam_status", "exam_id", "status"),
    )

    @validates("status")
    def _validate_status(self, _key: str, value: str) -> str:
        if value not in _IMPORT_JOB_STATUSES:
            raise ValueError(
                f"ImportJob.status {value!r} ungültig — erlaubt: "
                f"{sorted(_IMPORT_JOB_STATUSES)}"
            )
        return value

    def __repr__(self):
        return (
            f"<ImportJob(id={self.id}, exam_id={self.exam_id}, "
            f"driver={self.driver_name}, status={self.status})>"
        )


class MoodleConnection(Base):
    """Moodle Web Service credentials per institution.

    ``token_encrypted`` is Fernet-encrypted (same pattern as OAuth
    secrets).
    """

    __tablename__ = "moodle_connections"

    id = Column(Integer, primary_key=True, index=True)
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    base_url = Column(String(500), nullable=False)
    token_encrypted = Column(Text, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    institution = relationship("Institution", back_populates="moodle_connection")

    def __repr__(self):
        return f"<MoodleConnection(id={self.id}, institution_id={self.institution_id})>"
