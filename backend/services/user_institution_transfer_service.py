"""SuperAdmin user-institution transfer service (TF-352).

Moves a user to a different institution and, optionally, also transfers
the user's artifacts (documents, exams, question-reviews, tags) so they
remain visible under the new institution scope.

Out of scope: Students, StudentClasses, Submissions — these belong to
the institution organizationally, not to the individual user/lecturer.
Global tags (institution_id IS NULL) stay unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import func

from models.auth import Institution, User
from models.document import Document
from models.exam import Exam
from models.question_review import QuestionReview
from models.student import Student, StudentClass
from models.submission import Attempt
from models.tag import Tag
from services.audit_service import AuditService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TransferFlags:
    """Per-artifact-type opt-in flags for institution transfer."""

    documents: bool
    exams: bool
    questions: bool
    tags: bool


@dataclass(frozen=True)
class PreviewCounts:
    """Counts returned by preview_transfer() for UI display."""

    documents: int
    exams: int
    questions: int
    tags: int


@dataclass(frozen=True)
class ExcludedCounts:
    """Informational counts of artifacts that stay with the source institution."""

    students: int
    classes: int
    submissions: int


@dataclass(frozen=True)
class TransferPreview:
    transferable: PreviewCounts
    excluded: ExcludedCounts
    source_institution_id: int
    source_institution_name: str
    target_institution_id: int
    target_institution_name: str


@dataclass(frozen=True)
class TransferStats:
    """Actual counts after a transfer, plus document_ids for Celery dispatch."""

    documents: int
    exams: int
    questions: int
    tags: int
    document_ids: list[int]


class TransferError(Exception):
    """Raised when transfer pre-conditions fail. Endpoint translates to HTTP."""

    def __init__(self, code: str, http_status: int = 400):
        super().__init__(code)
        self.code = code
        self.http_status = http_status


def preview_transfer(
    db: "Session",
    user_id: int,
    target_institution_id: int,
) -> TransferPreview:
    """Compute counts that *would* be transferred if the user moved to target.

    Returns counts of:
      - Transferable artifacts (filtered by user ownership AND source institution)
      - Excluded artifacts (informational: students/classes/submissions stay)

    Raises TransferError if the user doesn't exist, the target institution
    doesn't exist, or source == target.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise TransferError("admin_user_not_found", http_status=404)

    target = (
        db.query(Institution).filter(Institution.id == target_institution_id).first()
    )
    if target is None:
        raise TransferError("admin_institution_not_found", http_status=404)

    if user.institution_id == target_institution_id:
        raise TransferError("admin_transfer_same_institution", http_status=400)

    source = db.query(Institution).filter(Institution.id == user.institution_id).first()
    source_name = source.name if source else ""

    source_iid = user.institution_id

    docs = (
        db.query(func.count(Document.id))
        .filter(Document.user_id == user_id, Document.institution_id == source_iid)
        .scalar()
    )
    exams = (
        db.query(func.count(Exam.id))
        .filter(Exam.created_by == user_id, Exam.institution_id == source_iid)
        .scalar()
    )
    questions = (
        db.query(func.count(QuestionReview.id))
        .filter(
            QuestionReview.created_by == user_id,
            QuestionReview.institution_id == source_iid,
        )
        .scalar()
    )
    tags = (
        db.query(func.count(Tag.id))
        .filter(
            Tag.created_by == user_id,
            Tag.institution_id == source_iid,
            Tag.institution_id.isnot(None),
        )
        .scalar()
    )

    students = (
        db.query(func.count(Student.id))
        .filter(Student.institution_id == source_iid)
        .scalar()
    )
    classes = (
        db.query(func.count(StudentClass.id))
        .filter(StudentClass.institution_id == source_iid)
        .scalar()
    )
    submissions = (
        db.query(func.count(Attempt.id))
        .filter(Attempt.institution_id == source_iid)
        .scalar()
    )

    return TransferPreview(
        transferable=PreviewCounts(
            documents=int(docs or 0),
            exams=int(exams or 0),
            questions=int(questions or 0),
            tags=int(tags or 0),
        ),
        excluded=ExcludedCounts(
            students=int(students or 0),
            classes=int(classes or 0),
            submissions=int(submissions or 0),
        ),
        source_institution_id=source_iid,
        source_institution_name=source_name,
        target_institution_id=target_institution_id,
        target_institution_name=target.name,
    )


def transfer_user(
    db: "Session",
    user_id: int,
    target_institution_id: int,
    flags: TransferFlags,
    actor: User,
) -> TransferStats:
    """Move user (and optionally their artifacts) to target institution.

    Runs all updates inside a single transaction. The AuditService.log_action
    call commits the transaction (it calls db.commit() internally), so all
    staged ORM changes — user, documents, exams, questions, tags — are
    committed atomically with the audit log row.

    Pre-conditions are validated here so the service stays callable from
    non-HTTP contexts (CLI, future admin scripts). Endpoints translate
    TransferError → HTTPException.

    On exception inside the transaction, db.rollback() is called before
    re-raising so the session is left in a clean state.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise TransferError("admin_user_not_found", http_status=404)

    if user.id == actor.id:
        raise TransferError("admin_transfer_self_forbidden", http_status=400)

    target = (
        db.query(Institution).filter(Institution.id == target_institution_id).first()
    )
    if target is None:
        raise TransferError("admin_institution_not_found", http_status=404)

    if user.institution_id == target_institution_id:
        raise TransferError("admin_transfer_same_institution", http_status=400)

    old_iid = user.institution_id
    document_ids: list[int] = []

    try:
        user.institution_id = target_institution_id

        # 2. Documents — collect as objects to set pending_reindex and capture ids
        docs_moved = 0
        if flags.documents:
            rows = (
                db.query(Document)
                .filter(
                    Document.user_id == user_id,
                    Document.institution_id == old_iid,
                )
                .all()
            )
            document_ids = [d.id for d in rows]
            for d in rows:
                d.institution_id = target_institution_id
                d.pending_reindex = True
            docs_moved = len(rows)

        exams_moved = 0
        if flags.exams:
            exams_moved = (
                db.query(Exam)
                .filter(
                    Exam.created_by == user_id,
                    Exam.institution_id == old_iid,
                )
                .update(
                    {"institution_id": target_institution_id},
                    synchronize_session=False,
                )
            )

        questions_moved = 0
        if flags.questions:
            questions_moved = (
                db.query(QuestionReview)
                .filter(
                    QuestionReview.created_by == user_id,
                    QuestionReview.institution_id == old_iid,
                )
                .update(
                    {"institution_id": target_institution_id},
                    synchronize_session=False,
                )
            )

        # 5. Tags — skip global (institution_id IS NULL)
        tags_moved = 0
        if flags.tags:
            tags_moved = (
                db.query(Tag)
                .filter(
                    Tag.created_by == user_id,
                    Tag.institution_id == old_iid,
                    Tag.institution_id.isnot(None),
                )
                .update(
                    {"institution_id": target_institution_id},
                    synchronize_session=False,
                )
            )

        # 6. Audit log — AuditService.log_action runs db.commit() internally as
        # its final step. It catches its own internal exceptions, rolls back,
        # and returns None on failure. We MUST detect that None and surface
        # it as a 500 — otherwise the caller sees a "success" response while
        # the database is rolled back to pre-transfer state. The
        # additional_data schema below is consumed by the audit-log UI /
        # exports (operation=institution_transfer is the discriminator).
        audit_log = AuditService.log_action(
            db=db,
            action=AuditService.ACTION_UPDATE_USER,
            status=AuditService.STATUS_SUCCESS,
            user_id=actor.id,
            resource_type=AuditService.RESOURCE_USER,
            resource_id=str(user_id),
            additional_data={
                "operation": "institution_transfer",
                "old_institution_id": old_iid,
                "new_institution_id": target_institution_id,
                "counts": {
                    "documents": docs_moved,
                    "exams": exams_moved,
                    "questions": questions_moved,
                    "tags": tags_moved,
                },
            },
        )
        if audit_log is None:
            # AuditService already rolled back. Don't pretend success.
            raise TransferError("admin_transfer_audit_failed", http_status=500)

    except TransferError:
        # Pre-condition errors: nothing was staged, just re-raise cleanly.
        raise
    except Exception:
        db.rollback()
        raise

    logger.info(
        "Institution transfer: user_id=%d %d -> %d by actor=%d "
        "(docs=%d exams=%d questions=%d tags=%d)",
        user_id,
        old_iid,
        target_institution_id,
        actor.id,
        docs_moved,
        exams_moved,
        questions_moved,
        tags_moved,
    )

    return TransferStats(
        documents=docs_moved,
        exams=exams_moved,
        questions=questions_moved,
        tags=tags_moved,
        document_ids=document_ids,
    )
