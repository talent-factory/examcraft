"""
Question Review Models für ExamCraft AI
Implementiert Review-Workflow für generierte Prüfungsfragen
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    DateTime,
    Enum,
    ForeignKey,
    JSON,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ReviewStatus(str, enum.Enum):
    """Status einer Question Review (Python Enum für Type-Safety)"""

    PENDING = "pending"  # Wartet auf Review
    APPROVED = "approved"  # Genehmigt
    REJECTED = "rejected"  # Abgelehnt
    EDITED = "edited"  # Bearbeitet (wartet auf erneute Genehmigung)
    IN_REVIEW = "in_review"  # Wird gerade überprüft


class QuestionReviewVisibility(enum.Enum):
    """Who may reuse a question outside the review workflow (TF-642).

    Governs the exam-composition reuse pool ("Fragenpool",
    ``api.exams.list_approved_questions``) and nothing else — deliberately
    NOT the Review-Queue (``api.question_review.get_review_queue``) or any
    review-workflow mutation (edit/approve/reject/archive/delete). Those stay
    permission + institution scoped exactly as before this field existed: a
    reviewer holding ``review_questions``/``edit_questions``/etc. still sees
    and acts on every institution question regardless of its visibility
    (/grilling decision, TF-642 — reviewing isn't "browsing", so it shouldn't
    lose access to a colleague's draft). Mirrors ``DocumentVisibility``
    (TF-354/TF-620) and ``PromptVisibility`` (TF-410/TF-641).

    - ``PRIVATE``: only the creator (``created_by``) may reuse it.
    - ``TEAM``: members of the question's Org-Unit (``org_unit_id``) may
      reuse it, hierarchically
      (``services.org_unit_service.get_user_accessible_org_unit_ids``).
    - ``INSTITUTION``: every member of the creator's institution may reuse
      it. Default — matches the pre-TF-642 status quo (every question was
      reachable institution-wide via ``TenantFilter`` alone), so introducing
      this field is not a behavior break for existing or newly generated
      rows (TF-638 decision).

    A user holding ``questions:read_all`` (Institution-Admin bypass,
    TF-639/utils/resource_visibility.py) sees every question within their own
    institution regardless of visibility, same as the Document/Prompt bypass
    — read-only, never crosses institutions.
    """

    PRIVATE = "private"
    TEAM = "team"
    INSTITUTION = "institution"


class QuestionReview(Base):
    """
    Haupttabelle für Question Reviews
    Speichert generierte Fragen mit Review-Status
    """

    __tablename__ = "question_reviews"

    id = Column(Integer, primary_key=True, index=True)

    # Question Content
    question_text = Column(Text, nullable=False)
    question_type = Column(
        String(50), nullable=False
    )  # single_choice, open_ended, true_false
    options = Column(
        JSON, nullable=True
    )  # Für Multiple Choice: ["A) ...", "B) ...", ...]
    correct_answer = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)

    # Metadata
    difficulty = Column(String(20), nullable=False)  # easy, medium, hard
    topic = Column(String(200), nullable=False)
    language = Column(String(10), default="de")

    # RAG-specific
    source_chunks = Column(JSON, nullable=True)  # List of chunk IDs
    source_documents = Column(JSON, nullable=True)  # List of document names
    confidence_score = Column(Float, default=0.0)

    # Quality Indicators
    bloom_level = Column(Integer, nullable=True)  # 1-6 (Bloom's Taxonomy)
    estimated_time_minutes = Column(Integer, nullable=True)
    quality_tier = Column(String(1), nullable=True)  # A, B, C

    # Kompetenz-Zuordnung (TF-400): geprüfte Handlungskompetenz + Ziel-LN-Stufe.
    # ln_level (1-4) ist distinkt von bloom_level (1-6). NULL für Altbestand und
    # für Fragen ohne Kompetenz-Bezug. Der Wert stammt aus Modell-Output; der
    # Bereich wird per CHECK (check_ln_level_range, s. __table_args__) erzwungen.
    competency_id = Column(
        Integer,
        ForeignKey("competencies.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    ln_level = Column(Integer, nullable=True)

    # Generation provenance (TF-383): Snapshot der Vorlage/des Prompts, mit dem
    # diese Frage erzeugt wurde. Eingefroren zum Generierungszeitpunkt, damit
    # spätere Template-Änderungen die Herkunft alter Fragen nicht verfälschen.
    # Form: {"prompt_id", "prompt_name", "prompt_version", "is_default_template",
    #        "fallback_to_default", "variables": {...}} — siehe das Envelope in
    #        schemas/generation_metadata.py. "fallback_to_default" ist IMMER
    #        präsent (Default false; true nur, wenn ein Custom-Prompt-Render
    #        fehlschlug und aufs Default-Template zurückfiel). NULL für Altbestand
    #        (Daten existierten nie).
    generation_metadata = Column(JSON, nullable=True)

    # Review Status (String mit CHECK Constraint statt Enum)
    review_status = Column(
        String(20), default=ReviewStatus.PENDING.value, nullable=False, index=True
    )
    reviewed_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # User ID
    reviewed_at = Column(DateTime, nullable=True)

    # Multi-Tenancy: Institution association
    institution_id = Column(
        Integer,
        ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )  # User who created the question

    # Org-Unit scoping (TF-642): set iff visibility='team' — enforced by
    # ck_question_reviews_team_visibility_requires_org_unit (both directions).
    # No ondelete cascade — deleting a referenced Org-Unit is rejected at the
    # DB level (services.org_unit_service.delete_org_unit), mirrors
    # Document/TF-620 and Prompt/TF-641.
    org_unit_id = Column(
        Integer,
        ForeignKey("org_units.id"),
        nullable=True,
        index=True,
    )

    # Visibility (TF-642): governs the Fragenpool reuse pool + its
    # single-question preview only — see QuestionReviewVisibility docstring
    # for what it deliberately does NOT govern (Review-Queue, mutation).
    # Default 'institution' preserves pre-TF-642 behavior.
    visibility = Column(
        Enum(
            QuestionReviewVisibility,
            name="questionreviewvisibility",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=QuestionReviewVisibility.INSTITUTION,
        server_default=QuestionReviewVisibility.INSTITUTION.value,
        index=True,
    )

    # Exam Association
    exam_id = Column(String(100), nullable=True, index=True)  # RAG Exam ID

    # TF-396: Archiv-Achse (orthogonal zu review_status).
    # archived_at IS NULL  => aktiv; gesetzt => archiviert (aus Bank/Listen
    # ausgeblendet, in Prüfungen aber erhalten). Wiederherstellen = archived_at
    # zurück auf NULL, review_status bleibt unverändert.
    archived_at = Column(DateTime, nullable=True, index=True)
    archived_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    archive_reason = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    comments = relationship(
        "ReviewComment", back_populates="question", cascade="all, delete-orphan"
    )
    history = relationship(
        "ReviewHistory", back_populates="question", cascade="all, delete-orphan"
    )
    tags = relationship(
        "Tag",
        secondary="question_tags",
        lazy="selectin",
    )
    source_document_links = relationship(
        "QuestionSourceDocument",
        cascade="all, delete-orphan",
        back_populates="question",
    )
    # TF-400: read-only Anzeige-Relationship auf die geprüfte Handlungskompetenz.
    # viewonly + kein cascade — die FK ist SET NULL, die Frage darf die Kompetenz
    # überleben. lazy="selectin" batcht den competency-Load über die Queue.
    # ACHTUNG: _serialize_competency liest zusätzlich competency.framework
    # (Competency.framework ist default-lazy) → ein Folge-Query pro HK-behafteter
    # Frage; bei wachsender Queue dort ebenfalls selectin setzen.
    competency = relationship("Competency", lazy="selectin", viewonly=True)

    # Table constraints
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('pending', 'approved', 'rejected', 'edited', 'in_review')",
            name="check_review_status",
        ),
        # TF-400: ln_level ist 1–4 oder NULL (distinkt von bloom_level 1–6).
        CheckConstraint(
            "ln_level IS NULL OR (ln_level >= 1 AND ln_level <= 4)",
            name="check_ln_level_range",
        ),
        # TF-642: mirrors Document/TF-354 — an institution-visible question
        # must belong to an institution.
        CheckConstraint(
            "visibility <> 'institution' OR institution_id IS NOT NULL",
            name="ck_question_reviews_institution_visibility_requires_institution",
        ),
        # TF-642: mirrors Document/TF-620 and Prompt/TF-641 — biconditional,
        # enforces both directions (team ⇒ has org_unit, and vice versa).
        CheckConstraint(
            "(visibility = 'team') = (org_unit_id IS NOT NULL)",
            name="ck_question_reviews_team_visibility_requires_org_unit",
        ),
    )

    def __repr__(self):
        return f"<QuestionReview(id={self.id}, type={self.question_type}, status={self.review_status})>"


class ReviewComment(Base):
    """
    Kommentare zu Question Reviews
    Ermöglicht Feedback und Diskussion
    """

    __tablename__ = "review_comments"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Comment Content
    comment_text = Column(Text, nullable=False)
    comment_type = Column(
        String(50), default="general"
    )  # general, suggestion, issue, approval_note

    # Author
    author = Column(String(100), nullable=False)  # User ID
    author_role = Column(String(50), nullable=True)  # reviewer, admin, system

    # Timestamps
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    question = relationship("QuestionReview", back_populates="comments")

    def __repr__(self):
        return f"<ReviewComment(id={self.id}, question_id={self.question_id}, author={self.author})>"


class ReviewHistory(Base):
    """
    Änderungshistorie für Question Reviews
    Audit Trail für alle Änderungen
    """

    __tablename__ = "review_history"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Change Information
    action = Column(
        String(50), nullable=False
    )  # created, edited, approved, rejected, status_changed
    old_status = Column(String(20), nullable=True)  # ReviewStatus values
    new_status = Column(String(20), nullable=True)  # ReviewStatus values

    # Changed Fields
    changed_fields = Column(
        JSON, nullable=True
    )  # {"question_text": {"old": "...", "new": "..."}}

    # Actor
    changed_by = Column(String(100), nullable=False)  # User ID
    change_reason = Column(Text, nullable=True)

    # Timestamp
    changed_at = Column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    question = relationship("QuestionReview", back_populates="history")

    def __repr__(self):
        return f"<ReviewHistory(id={self.id}, question_id={self.question_id}, action={self.action})>"


class QuestionSourceDocument(Base):
    """Join table linking QuestionReview to Document (normalised source_documents)."""

    __tablename__ = "question_source_documents"

    id = Column(Integer, primary_key=True)
    question_id = Column(
        Integer,
        ForeignKey("question_reviews.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Relationships
    question = relationship("QuestionReview", back_populates="source_document_links")

    __table_args__ = (UniqueConstraint("question_id", "document_id"),)
