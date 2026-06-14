"""ResultsDeletionService: delete all imported results of an exam (TF-421).

Background
----------
The Moodle result import is idempotent over
``(institution_id, source, source_attempt_id)`` — the key is derived from
student + start time + attempt number, *not* from the answers
(``import_service.py``). A re-import of the same CSV therefore **skips**
existing attempts instead of updating them. When a parse bug imported corrupt
data (e.g. TF-419: shifted answers), there was no way to fix it via re-import,
and no delete endpoint existed at all — correction meant a manual ``DELETE``
against the production DB.

This service removes that need. It deletes **all** imported results of one exam
(across every source) so the operator can then re-import cleanly: the
idempotency skip no longer triggers because the keys are gone.

Scope & semantics
-----------------
* Whole exam, all sources — the natural unit, since ``Attempt`` has no FK to a
  specific ``ImportJob`` (only ``source`` + ``source_attempt_id``).
* Deletes ``Attempt`` rows of the exam's submissions; the database cascades
  ``AttemptAnswer`` → ``Grade`` → ``GradeHistory`` (all ``ON DELETE CASCADE``).
* Then removes the now-empty ``Submission`` rows (orphan cleanup).
* **Keeps** ``Student`` rows (roster entities, shared across exams/classes) and
  ``ImportJob`` rows (historical record of the import; the audit log captures
  the deletion separately).

The service is read-only on counts (:meth:`summary`) and mutating on
:meth:`delete_exam_results`; it never commits — the caller owns the
transaction so the deletion and its audit-log entry commit atomically.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from enums import AttemptSource
from models.exam import Exam
from models.submission import Attempt, Submission

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SourceCount:
    """Attempt count for one import source within an exam."""

    source: AttemptSource
    attempt_count: int


@dataclass(frozen=True)
class DeletionSummary:
    """How much a delete would remove — drives the confirmation dialog."""

    exam_id: int
    submission_count: int
    attempt_count: int
    student_count: int
    by_source: list[SourceCount] = field(default_factory=list)


class ResultsDeletionService:
    """Deletes all imported results (attempts + answers + grades) of an exam."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def summary(self, *, exam: Exam) -> DeletionSummary:
        """Count what a delete would remove, without mutating anything.

        ``student_count`` counts distinct students that have a submission for
        the exam (i.e. would lose data), not the institution roster.
        """
        submission_ids = self._submission_ids(exam.id)
        if not submission_ids:
            return DeletionSummary(
                exam_id=exam.id,
                submission_count=0,
                attempt_count=0,
                student_count=0,
                by_source=[],
            )

        attempt_count = (
            self.db.query(func.count(Attempt.id))
            .filter(Attempt.submission_id.in_(submission_ids))
            .scalar()
            or 0
        )

        student_count = (
            self.db.query(func.count(func.distinct(Submission.student_id)))
            .filter(Submission.id.in_(submission_ids))
            .scalar()
            or 0
        )

        source_rows = (
            self.db.query(Attempt.source, func.count(Attempt.id))
            .filter(Attempt.submission_id.in_(submission_ids))
            .group_by(Attempt.source)
            .order_by(Attempt.source)
            .all()
        )
        # ``attempts.source`` is CHECK-constrained to the AttemptSource values,
        # so the coercion never raises in practice.
        by_source = [
            SourceCount(source=AttemptSource(source), attempt_count=count)
            for source, count in source_rows
        ]

        return DeletionSummary(
            exam_id=exam.id,
            submission_count=len(submission_ids),
            attempt_count=int(attempt_count),
            student_count=int(student_count),
            by_source=by_source,
        )

    def delete_exam_results(self, *, exam: Exam) -> DeletionSummary:
        """Delete all imported results of ``exam``; return what was removed.

        Captures the counts first (so the return value and audit log reflect
        the pre-deletion state), then bulk-deletes attempts — the DB cascades
        answers/grades/grade-history — and finally the orphaned submissions.
        Does **not** commit; the caller commits together with the audit entry.
        """
        result = self.summary(exam=exam)
        if result.submission_count == 0:
            return result

        submission_ids = self._submission_ids(exam.id)

        # Delete attempts first: ON DELETE CASCADE removes attempt_answers →
        # grades → grade_history; submissions.graded_attempt_id is SET NULL
        # (use_alter), so the circular FK never blocks the delete.
        self.db.query(Attempt).filter(Attempt.submission_id.in_(submission_ids)).delete(
            synchronize_session=False
        )

        # Orphan cleanup: every submission of the exam is now empty.
        self.db.query(Submission).filter(Submission.id.in_(submission_ids)).delete(
            synchronize_session=False
        )

        # Bulk deletes bypass the identity map; drop stale ORM state so later
        # queries in this session (and tests) observe the deletions.
        self.db.expire_all()

        logger.info(
            "ResultsDeletionService: exam_id=%s removed %s submission(s), "
            "%s attempt(s), %s student(s) affected",
            exam.id,
            result.submission_count,
            result.attempt_count,
            result.student_count,
        )
        return result

    def _submission_ids(self, exam_id: int) -> list[int]:
        return list(
            self.db.scalars(
                select(Submission.id).where(Submission.exam_id == exam_id)
            ).all()
        )
