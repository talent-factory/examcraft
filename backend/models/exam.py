"""
Exam Composer Models for ExamCraft AI
Implements exam assembly from approved questions with M:N relationship.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ExamStatus(str, enum.Enum):
    DRAFT = "draft"
    FINALIZED = "finalized"
    EXPORTED = "exported"


class ExamVisibility(enum.Enum):
    """Who may browse/open an exam outside its owner (TF-643).

    Governs ``api.exams.list_exams`` and ``api.exams.get_exam`` (plus, per
    ``allow_read_all_bypass=False``, every exam-mutation endpoint reachable
    via ``_get_exam_or_404`` — see that function's docstring). Mirrors
    ``DocumentVisibility`` (TF-354/TF-620), ``PromptVisibility``
    (TF-410/TF-641) and ``QuestionReviewVisibility`` (TF-642).

    - ``PRIVATE``: only the creator (``created_by``) may see it.
    - ``TEAM``: members of the exam's Org-Unit (``org_unit_id``) may see it,
      hierarchically (``services.org_unit_service.get_user_accessible_org_unit_ids``).
    - ``INSTITUTION``: every member of the creator's institution may see it.
      Default — matches the pre-TF-643 status quo (every exam was reachable
      institution-wide via ``TenantFilter`` alone), so introducing this field
      is not a behavior break for existing or newly created rows (TF-638
      decision).

    A user holding ``exams:read_all`` (Institution-Admin bypass,
    TF-639/utils/resource_visibility.py) sees every exam within their own
    institution regardless of visibility, same as the Document/Prompt/
    Question bypass — read-only (never grants mutation), never crosses
    institutions.

    Deliberately independent of ``ExamStatus`` (DRAFT/FINALIZED/EXPORTED) —
    visibility applies uniformly across the exam lifecycle, no special-casing
    (/grilling decision, TF-643). Also deliberately independent of
    ``submissions:grade``/``submissions:read`` — the grading pipeline keeps
    bypassing browsing visibility exactly as before (institution-flat via
    ``submissions.py::_load_exam_for_user``), same /grilling decision. And a
    private/team question embedded into a wider-visibility exam via
    ``ExamQuestion`` follows the *exam's* visibility from that point on — see
    ``utils.question_visibility`` module docstring for the question-side half
    of that decision.
    """

    PRIVATE = "private"
    TEAM = "team"
    INSTITUTION = "institution"


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(300), nullable=False)
    course = Column(String(200), nullable=True)
    exam_date = Column(Date, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    allowed_aids = Column(Text, nullable=True)
    instructions = Column(Text, nullable=True)
    passing_percentage = Column(Float, default=50.0, nullable=False)
    total_points = Column(Float, default=0.0, nullable=False)
    status = Column(
        String(20), default=ExamStatus.DRAFT.value, nullable=False, index=True
    )
    language = Column(String(10), default="de", nullable=False)
    default_document_ids = Column(JSON, nullable=True)  # List[int] | null
    grading_scheme_id = Column(
        Integer,
        # ON DELETE RESTRICT: deleting a scheme that's still attached to
        # an exam would silently break the export contract (Note column
        # would render "—" for every row). Force the lehrperson to
        # detach first.
        ForeignKey("grading_schemes.id", ondelete="RESTRICT"),
        nullable=True,
    )

    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Org-Unit scoping (TF-643): set iff visibility='team' — enforced by
    # ck_exams_team_visibility_requires_org_unit (both directions). No
    # ondelete cascade — deleting a referenced Org-Unit is rejected at the
    # DB level (services.org_unit_service.delete_org_unit), mirrors
    # Document/TF-620, Prompt/TF-641 and Question/TF-642.
    org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id"),
        nullable=True,
        index=True,
    )

    # Visibility (TF-643): see ExamVisibility docstring for exact scope.
    # Default 'institution' preserves pre-TF-643 behavior.
    visibility = Column(
        Enum(
            ExamVisibility,
            name="examvisibility",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=ExamVisibility.INSTITUTION,
        server_default=ExamVisibility.INSTITUTION.value,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Archive axis (TF-398): orthogonal to ``status``. archived_at IS NULL =>
    # active; set => archived. Mirrors the TF-396 pattern
    # (question_reviews). Archiving is allowed in any status and leaves
    # ``status`` untouched.
    archived_at = Column(DateTime(), nullable=True)
    archived_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    archive_reason = Column(Text, nullable=True)

    institution = relationship(
        "Institution",
        foreign_keys=[institution_id],
    )
    questions = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.position",
    )
    submissions = relationship(
        "Submission",
        back_populates="exam",
        cascade="all, delete-orphan",
        foreign_keys="Submission.exam_id",
    )
    import_jobs = relationship(
        "ImportJob",
        back_populates="exam",
        cascade="all, delete-orphan",
        foreign_keys="ImportJob.exam_id",
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'finalized', 'exported')", name="check_exam_status"
        ),
        # TF-643: mirrors Document/TF-354. Unlike Document/QuestionReview,
        # Exam.institution_id is NOT NULL (see column above), so this
        # constraint can never actually fire today — kept as
        # defense-in-depth should the column ever become nullable.
        CheckConstraint(
            "visibility <> 'institution' OR institution_id IS NOT NULL",
            name="ck_exams_institution_visibility_requires_institution",
        ),
        # TF-643: mirrors Document/TF-620, Prompt/TF-641, Question/TF-642.
        CheckConstraint(
            "(visibility = 'team') = (org_unit_id IS NOT NULL)",
            name="ck_exams_team_visibility_requires_org_unit",
        ),
    )

    def recalculate_total_points(self):
        self.total_points = sum(eq.points for eq in self.questions)

    def __repr__(self):
        return f"<Exam(id={self.id}, title='{self.title}', status={self.status})>"


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(
        Integer,
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    position = Column(Integer, nullable=False)
    points = Column(Float, nullable=False)
    section = Column(String(100), nullable=True)
    external_refs = Column(JSON, nullable=True)

    exam = relationship("Exam", back_populates="questions")
    question = relationship("QuestionReview")

    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
        UniqueConstraint("exam_id", "position", name="uq_exam_position"),
    )

    def __repr__(self):
        return f"<ExamQuestion(exam_id={self.exam_id}, question_id={self.question_id}, pos={self.position})>"
