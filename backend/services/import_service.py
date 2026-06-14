"""ImportService: 8-step pipeline for results import.

Source-agnostic via the driver registry. Pipeline:

1. Driver loads source → ``ImportPayload``
2. Validate against exam (every ``exam_question_id`` belongs to the exam)
3. Idempotency check via ``(institution_id, source, source_attempt_id)``
4. Upsert students via ``(institution_id, external_id)``
5. Persist attempts + answers in a transaction
6. Submission aggregation → ``graded_attempt_id`` per ``scoring_strategy``
7. ``GradingService.grade_submission`` runs deterministic grading
8. Update ``import_jobs`` (rows_processed, rows_failed, error_log,
   status)

Failure semantics: any exception inside the pipeline triggers a session
rollback before the job row is updated and committed, so partial inserts
never leak into ``submissions``/``attempts``/``grades`` while the job
itself reports ``failed``.
"""

from __future__ import annotations

import logging
import re
import traceback
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from enums import (
    ImportJobStatus,
    ScoringStrategy,
    SubmissionGradeStatus,
)
from models.exam import Exam, ExamQuestion
from models.student import Student, StudentClass, StudentClassMembership
from models.submission import (
    Attempt,
    AttemptAnswer,
    ImportJob,
    Submission,
)
from services.grading_service import GradingService
from services.import_drivers import (
    BaseImportDriver,
    ImportDriverError,
    ImportPayload,
    ImportRowError,
    MoodleApiDriver,
    MoodleJsonDriver,
)


logger = logging.getLogger(__name__)


# Constraint names whose violation indicates a benign idempotency race
# (concurrent imports racing on the same attempt). Anything else from
# IntegrityError is a real bug and must be surfaced as a row error.
_BENIGN_RACE_CONSTRAINTS = frozenset(
    {
        "uq_attempts_submission_number",
        "uq_attempts_inst_source_attempt_id",
    }
)


class ImportValidationError(Exception):
    """Hard failure validating payload against the exam.

    May carry a list of structured per-row issues so the operator sees
    every offending question_id at once instead of having to re-upload
    the CSV after each fix.
    """

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []


class UnknownDriverError(ImportValidationError):
    """Driver name does not match any registered driver."""


class ImportService:
    """Orchestrates preview + commit + grading."""

    # MappingProxyType makes the registry read-only — callers cannot
    # mutate it at runtime (tests included).
    DRIVERS: Mapping[str, BaseImportDriver] = MappingProxyType(
        {
            MoodleJsonDriver.name: MoodleJsonDriver(),
            MoodleApiDriver.name: MoodleApiDriver(),
        }
    )

    def __init__(self, db: Session) -> None:
        self.db = db
        self.grading_service = GradingService(db)

    def preview(
        self,
        *,
        exam: Exam,
        driver_name: str,
        source: bytes | str,
    ) -> ImportPayload:
        """Steps 1+2: parse + validate, no persistence."""
        driver = self._get_driver(driver_name)
        payload = driver.parse(source, exam=exam, db=self.db)
        self._validate_payload(payload, exam)
        return payload

    def create_queued_job(
        self,
        *,
        exam: Exam,
        driver_name: str,
        triggered_by: int | None,
        source_metadata: dict[str, Any] | None = None,
    ) -> ImportJob:
        """Pre-create a committed ``ImportJob`` in ``queued`` state.

        Async callers (the Celery import task) reuse this exact row by passing
        its id to :meth:`commit` as ``import_job_id`` — ``commit`` flips it to
        ``running`` in place, so no duplicate job is produced and the polling
        client has a stable job id the instant the request returns. No parsing
        or grading happens here.
        """
        job = ImportJob(
            institution_id=exam.institution_id,
            exam_id=exam.id,
            driver_name=driver_name,
            status=ImportJobStatus.QUEUED.value,
            rows_processed=0,
            rows_failed=0,
            error_log=[],
            source_metadata=source_metadata or {},
            triggered_by=triggered_by,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def commit(
        self,
        *,
        exam: Exam,
        driver_name: str,
        source: bytes | str,
        triggered_by: int | None,
        source_metadata: dict[str, Any] | None = None,
        import_job_id: int | None = None,
    ) -> ImportJob:
        """Full pipeline: parse → validate → persist → grade → aggregate.

        Transaction model: the job row is committed first so it survives
        any failure with diagnostic state. The pipeline runs inside a
        nested-savepoint tree (one outer SAVEPOINT plus per-row inner
        ones in ``_upsert_students`` / ``_persist_attempts``). On any
        exception the outer savepoint rolls back, then ``_fail_job``
        mutates the already-committed job row in-place and the next
        commit flushes that mutation.

        ``import_job_id``: if given, reuse the existing row instead of
        creating one. Used by Celery callers so a transient-error retry
        does not produce duplicate ``ImportJob`` rows. Caller is
        responsible for creating the row in ``QUEUED``/``RUNNING`` state
        and matching ``institution_id``/``exam_id`` — mismatches raise.
        """
        driver = self._get_driver(driver_name)

        if import_job_id is not None:
            job = (
                self.db.query(ImportJob)
                .filter(ImportJob.id == import_job_id)
                .one_or_none()
            )
            if job is None:
                raise ImportValidationError(f"ImportJob {import_job_id} nicht gefunden")
            if job.exam_id != exam.id or job.institution_id != exam.institution_id:
                raise ImportValidationError(
                    f"ImportJob {import_job_id} gehört nicht zu Exam {exam.id}"
                )
            # Reset for the retry: a previous attempt may have left
            # status/aggregates from a failed run.
            job.status = ImportJobStatus.RUNNING.value
            job.started_at = datetime.now(timezone.utc)
            job.finished_at = None
            job.rows_processed = 0
            job.rows_failed = 0
            job.error_log = []
        else:
            job = ImportJob(
                institution_id=exam.institution_id,
                exam_id=exam.id,
                driver_name=driver_name,
                status=ImportJobStatus.RUNNING.value,
                rows_processed=0,
                rows_failed=0,
                error_log=[],
                source_metadata=source_metadata or {},
                triggered_by=triggered_by,
                started_at=datetime.now(timezone.utc),
            )
            self.db.add(job)
        self.db.commit()  # Job survives failures so the operator sees it.
        self.db.refresh(job)

        try:
            with self.db.begin_nested():  # SAVEPOINT: rolls back on failure
                payload = driver.parse(source, exam=exam, db=self.db)
                self._validate_payload(payload, exam)

                students_by_external_id = self._upsert_students(
                    payload, institution_id=exam.institution_id
                )
                # TF-336: auto-attach students to classes based on the
                # driver-supplied ``class_hint``. Missing classes are
                # created on the fly; existing memberships are kept.
                self._attach_class_memberships(
                    payload=payload,
                    institution_id=exam.institution_id,
                    students_by_external_id=students_by_external_id,
                )
                touched_submissions = self._persist_attempts(
                    payload=payload,
                    exam=exam,
                    students_by_external_id=students_by_external_id,
                    job=job,
                )

                grading_failures = self._grade_touched_submissions(
                    touched_submissions, job=job
                )

                self._finalise_job(job, payload, grading_failures=grading_failures)
        except (ImportDriverError, ImportValidationError) as exc:
            self._fail_job(job, exc, step="validate")
            self.db.commit()
            raise
        except Exception as exc:
            logger.exception("ImportService.commit unexpectedly failed")
            self._fail_job(job, exc, step="pipeline")
            self.db.commit()
            raise

        self.db.commit()
        self.db.refresh(job)
        return job

    @classmethod
    def _get_driver(cls, name: str) -> BaseImportDriver:
        try:
            return cls.DRIVERS[name]
        except KeyError as exc:
            raise UnknownDriverError(
                f"Unbekannter Driver '{name}'. Verfügbar: {sorted(cls.DRIVERS)}"
            ) from exc

    @staticmethod
    def _validate_payload(payload: ImportPayload, exam: Exam) -> None:
        """Collect every invalid-reference at once — operators want to
        fix the CSV in one round, not chase failures one-by-one."""
        if payload.exam_id != exam.id:
            raise ImportValidationError(
                f"Payload-exam_id {payload.exam_id} != exam.id {exam.id}"
            )

        valid_question_ids = {q.id for q in exam.questions}
        issues: list[str] = []
        for attempt_idx, attempt in enumerate(payload.attempts):
            for answer in attempt.answers:
                if answer.exam_question_id not in valid_question_ids:
                    issues.append(
                        f"Attempt #{attempt_idx} ({attempt.student_external_id}): "
                        f"AttemptAnswer referenziert exam_question_id "
                        f"{answer.exam_question_id} — nicht in Prüfung {exam.id}"
                    )
        if issues:
            raise ImportValidationError(
                f"{len(issues)} Validierungs-Fehler in Payload",
                issues=issues,
            )

    def _upsert_students(
        self, payload: ImportPayload, *, institution_id: int
    ) -> dict[str, Student]:
        external_ids = [s.external_id for s in payload.students]
        if not external_ids:
            return {}

        existing = (
            self.db.query(Student)
            .filter(
                Student.institution_id == institution_id,
                Student.external_id.in_(external_ids),
            )
            .all()
        )
        result: dict[str, Student] = {s.external_id: s for s in existing}

        for ref in payload.students:
            if ref.external_id in result:
                # Existing student: only fill display_name when blank
                # (preserve teacher edits — Lehrperson hat Vorrang).
                student = result[ref.external_id]
                if not student.display_name and ref.display_name:
                    student.display_name = ref.display_name
                continue

            # SAVEPOINT-protected insert: another concurrent import for
            # the same (institution_id, external_id) can race past our
            # SELECT above. On IntegrityError we roll back the savepoint
            # and refetch the row the other transaction inserted.
            try:
                with self.db.begin_nested():
                    student = Student(
                        institution_id=institution_id,
                        external_id=ref.external_id,
                        display_name=ref.display_name,
                    )
                    self.db.add(student)
                    self.db.flush()
            except IntegrityError:
                student = (
                    self.db.query(Student)
                    .filter(
                        Student.institution_id == institution_id,
                        Student.external_id == ref.external_id,
                    )
                    .one()
                )
            result[ref.external_id] = student

        self.db.flush()
        return result

    def _attach_class_memberships(
        self,
        *,
        payload: ImportPayload,
        institution_id: int,
        students_by_external_id: dict[str, Student],
    ) -> None:
        """Auto-attach students to a ``StudentClass`` per ``class_hint``.

        Idempotent: existing memberships (or pre-existing classes with
        the same name in the institution) are reused. A missing class is
        created. Per-student errors degrade to ``payload.warnings`` so
        one bad row never aborts the whole import.

        We trim and treat empty strings as None to defend against the
        Moodle locale exports that fill the column with whitespace.
        """
        hint_map: dict[str, list[Student]] = {}
        for ref in payload.students:
            hint = (ref.class_hint or "").strip()
            if not hint:
                continue
            student = students_by_external_id.get(ref.external_id)
            if student is None:
                continue
            hint_map.setdefault(hint, []).append(student)

        if not hint_map:
            return

        existing_classes = {
            cls.name: cls
            for cls in (
                self.db.query(StudentClass)
                .filter(
                    StudentClass.institution_id == institution_id,
                    StudentClass.name.in_(list(hint_map)),
                )
                .all()
            )
        }

        # Pre-load existing memberships to avoid one SELECT per student.
        student_ids = {s.id for students in hint_map.values() for s in students}
        existing_memberships: set[tuple[int, int]] = set()
        if student_ids and existing_classes:
            class_ids = [c.id for c in existing_classes.values()]
            rows = (
                self.db.query(
                    StudentClassMembership.student_id,
                    StudentClassMembership.class_id,
                )
                .filter(
                    StudentClassMembership.student_id.in_(student_ids),
                    StudentClassMembership.class_id.in_(class_ids),
                )
                .all()
            )
            existing_memberships = {(row.student_id, row.class_id) for row in rows}

        classes_created = 0
        members_added = 0
        for class_name, students in hint_map.items():
            student_class = existing_classes.get(class_name)
            if student_class is None:
                # Race-safe class insert: another concurrent import may
                # have created the same class name in the same
                # institution between our SELECT above and this INSERT.
                try:
                    with self.db.begin_nested():
                        student_class = StudentClass(
                            institution_id=institution_id,
                            name=class_name,
                        )
                        self.db.add(student_class)
                        self.db.flush()
                except IntegrityError:
                    student_class = (
                        self.db.query(StudentClass)
                        .filter(
                            StudentClass.institution_id == institution_id,
                            StudentClass.name == class_name,
                        )
                        .one()
                    )
                else:
                    classes_created += 1
                existing_classes[class_name] = student_class

            for student in students:
                key = (student.id, student_class.id)
                if key in existing_memberships:
                    continue
                try:
                    with self.db.begin_nested():
                        self.db.add(
                            StudentClassMembership(
                                student_id=student.id,
                                class_id=student_class.id,
                            )
                        )
                        self.db.flush()
                except IntegrityError:
                    # Same race window as above — another import added
                    # the membership; nothing to do.
                    continue
                existing_memberships.add(key)
                members_added += 1

        self.db.flush()
        if classes_created or members_added:
            payload.warnings.append(
                f"Klassen-Zuordnung: {classes_created} Klasse(n) angelegt, "
                f"{members_added} Mitgliedschaft(en) ergänzt"
            )

    def _persist_attempts(
        self,
        *,
        payload: ImportPayload,
        exam: Exam,
        students_by_external_id: dict[str, Student],
        job: ImportJob,
    ) -> list[Submission]:
        """Persist new attempts + answers; return touched submissions.

        Idempotent on ``(institution_id, source, source_attempt_id)``:
        a known attempt is skipped (no update). Skips and unexpected
        IntegrityErrors are surfaced as ``payload.errors`` so they show
        up on the import job rather than vanishing silently.

        Side effect: increments ``payload.attempts_persisted`` for every
        attempt that actually reached the DB (excluding idempotency
        skips and per-row failures). The job summary reports this
        count instead of ``len(payload.attempts)`` so operators see
        what was written, not what was parsed.
        """
        if not payload.attempts:
            return []

        existing_source_ids = self._load_existing_source_ids(
            payload, institution_id=exam.institution_id
        )
        submissions_by_student: dict[int, Submission] = {}
        touched_submissions: dict[int, Submission] = {}
        attempts_persisted = 0
        attempts_skipped_idempotent = 0

        for record_idx, attempt_record in enumerate(payload.attempts, start=1):
            student = students_by_external_id.get(attempt_record.student_external_id)
            if student is None:
                # Indicates a bug in _upsert_students — surface loudly so
                # the operator notices rather than letting the row vanish.
                logger.error(
                    "ImportService: student %r not found after upsert "
                    "(attempt #%s) — recording error and continuing",
                    attempt_record.student_external_id,
                    record_idx,
                )
                payload.errors.append(
                    ImportRowError(
                        row_index=record_idx,
                        reason=(
                            f"Student '{attempt_record.student_external_id}' "
                            "konnte nicht angelegt/gefunden werden"
                        ),
                    )
                )
                continue

            source_attempt_id = attempt_record.source_attempt_id
            if (
                source_attempt_id
                and (payload.driver_name, source_attempt_id) in existing_source_ids
            ):
                attempts_skipped_idempotent += 1
                continue  # Idempotency: attempt already imported

            submission = self._get_or_create_submission(
                exam=exam,
                student=student,
                cache=submissions_by_student,
            )

            try:
                with self.db.begin_nested():
                    attempt = Attempt(
                        submission_id=submission.id,
                        institution_id=exam.institution_id,
                        attempt_number=attempt_record.attempt_number,
                        started_at=attempt_record.started_at,
                        submitted_at=attempt_record.submitted_at,
                        source=payload.driver_name,
                        source_attempt_id=source_attempt_id,
                        raw_payload=attempt_record.raw_payload,
                    )
                    self.db.add(attempt)
                    self.db.flush()  # attempt.id for AttemptAnswer FK
            except IntegrityError as exc:
                constraint = self._extract_constraint_name(exc)
                # Idempotency races on the two unique constraints are
                # benign — a concurrent commit already inserted the row.
                # Anything else (NOT NULL, FK, future CHECK, length
                # overflow on source_attempt_id, …) is a real bug: log
                # the constraint name AND surface the row error.
                if constraint in _BENIGN_RACE_CONSTRAINTS:
                    logger.info(
                        "Idempotency race on %s for attempt #%s — skipped",
                        constraint,
                        record_idx,
                    )
                    attempts_skipped_idempotent += 1
                    continue
                logger.exception(
                    "Unexpected IntegrityError persisting attempt #%s (constraint=%s)",
                    record_idx,
                    constraint or "?",
                )
                payload.errors.append(
                    ImportRowError(
                        row_index=record_idx,
                        reason=(
                            f"DB-Fehler beim Persistieren des Attempts: "
                            f"{constraint or type(exc).__name__}"
                        ),
                    )
                )
                continue

            for answer_record in attempt_record.answers:
                answer = AttemptAnswer(
                    attempt_id=attempt.id,
                    exam_question_id=answer_record.exam_question_id,
                    given_answer=answer_record.given_answer,
                    moodle_points_awarded=answer_record.moodle_points_awarded,
                )
                self.db.add(answer)

            touched_submissions[submission.id] = submission
            attempts_persisted += 1

        if touched_submissions:
            from sqlalchemy import func as sa_func

            max_total = (
                self.db.query(sa_func.coalesce(sa_func.sum(ExamQuestion.points), 0.0))
                .filter(ExamQuestion.exam_id == exam.id)
                .scalar()
                or 0.0
            )
            for sub in touched_submissions.values():
                sub.total_points_max = max_total

        self.db.flush()

        # Stash counts on the payload so _finalise_job can report
        # actually-persisted rows rather than parsed-rows.
        payload.attempts_persisted = attempts_persisted
        payload.attempts_skipped_idempotent = attempts_skipped_idempotent

        return list(touched_submissions.values())

    def _grade_touched_submissions(
        self, submissions: list[Submission], *, job: ImportJob
    ) -> list[tuple[int, str, str]]:
        """Grade each submission, isolating per-submission failures.

        One bad submission must not roll back the whole import — record
        the failure on the job and continue with the next.

        Marks failed submissions with ``IMPORT_GRADING_FAILED`` so the
        UI can render a red banner instead of "0 / N points,
        pending_review" — which reads as "awaiting LLM" and would
        silently mask the real failure.

        Returns ``(submission_id, reason, traceback)`` per failure so
        the import-job error_log carries the full stack — the worker
        log alone is not visible to the operator triaging via the UI.
        """
        failures: list[tuple[int, str, str]] = []
        for submission in submissions:
            try:
                with self.db.begin_nested():
                    self.grading_service.grade_submission(submission.id)
            except Exception as exc:
                if not isinstance(exc, SQLAlchemyError):
                    # Unexpected exception type — likely a bug in the grading
                    # service (AttributeError, TypeError, etc.) rather than a
                    # DB or LLM API failure. Log at ERROR so operators can
                    # distinguish real bugs from expected API degradation.
                    logger.error(
                        "Grading failed for submission_id=%s during import — "
                        "unexpected exception type %s (may indicate a grading "
                        "service bug): %s",
                        submission.id,
                        type(exc).__name__,
                        exc,
                        exc_info=True,
                    )
                else:
                    logger.exception(
                        "Grading failed for submission_id=%s during import",
                        submission.id,
                    )
                tb = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
                failures.append((submission.id, f"{type(exc).__name__}: {exc}", tb))
                # Outside the rolled-back savepoint: mutate the
                # submission row in the outer transaction so the failed
                # state is visible to the UI even after the savepoint
                # for this submission's grade rows was rolled back.
                submission.grade_status = (
                    SubmissionGradeStatus.IMPORT_GRADING_FAILED.value
                )
        return failures

    _CONSTRAINT_NAME_REGEX = re.compile(
        r'violates (?:unique|foreign key|check) constraint "([^"]+)"'
    )

    @classmethod
    def _extract_constraint_name(cls, exc: IntegrityError) -> str | None:
        """Extract constraint name from a psycopg/asyncpg IntegrityError.

        Prefers ``diag.constraint_name`` (the only authoritative source).
        Falls back to a strictly-anchored regex against the canonical
        Postgres message format. Cascading FK messages can mention more
        than one constraint name; the anchor "violates X constraint" is
        always the one that actually failed, so we match only the
        first one and verify by anchor — not by free-text scanning.
        """
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        name = getattr(diag, "constraint_name", None)
        if name:
            return str(name)
        match = cls._CONSTRAINT_NAME_REGEX.search(str(exc))
        if match:
            return match.group(1)
        return None

    def _load_existing_source_ids(
        self, payload: ImportPayload, *, institution_id: int
    ) -> set[tuple[str, str]]:
        candidate_ids = [
            a.source_attempt_id for a in payload.attempts if a.source_attempt_id
        ]
        if not candidate_ids:
            return set()

        rows = (
            self.db.query(Attempt.source, Attempt.source_attempt_id)
            .filter(
                Attempt.institution_id == institution_id,
                Attempt.source == payload.driver_name,
                Attempt.source_attempt_id.in_(candidate_ids),
            )
            .all()
        )
        return {(row.source, row.source_attempt_id) for row in rows}

    def _get_or_create_submission(
        self,
        *,
        exam: Exam,
        student: Student,
        cache: dict[int, Submission],
    ) -> Submission:
        if student.id in cache:
            return cache[student.id]

        submission = (
            self.db.query(Submission)
            .options(joinedload(Submission.attempts))
            .filter(
                Submission.exam_id == exam.id,
                Submission.student_id == student.id,
            )
            .one_or_none()
        )
        if submission is None:
            submission = Submission(
                exam_id=exam.id,
                student_id=student.id,
                scoring_strategy=ScoringStrategy.LATEST.value,
                grade_status=SubmissionGradeStatus.PENDING_REVIEW.value,
            )
            self.db.add(submission)
            self.db.flush()

        cache[student.id] = submission
        return submission

    @staticmethod
    def _finalise_job(
        job: ImportJob,
        payload: ImportPayload,
        *,
        grading_failures: list[tuple[int, str, str]] | None = None,
    ) -> None:
        """Set job aggregates + status.

        ``PARTIAL`` vs ``FAILED`` is an operator-visibility choice:
        partial means *some* rows persisted (re-import with the failed
        rows fixed will round-trip clean). FAILED means nothing useful
        was imported.

        ``grading_failures``: ``(submission_id, reason, traceback)``
        tuples; the traceback ends up in ``error_log[*].details`` so
        the UI surfaces the real cause without server-log access.
        """
        grading_failures = grading_failures or []
        rows_failed = len(payload.errors) + len(grading_failures)
        # Report rows actually persisted, not parsed: idempotency skips
        # and per-row failures both reduce the persisted count and
        # operators reading "10 verarbeitet" expect to find 10 rows in
        # the DB. ``attempts_persisted`` defaults to None for legacy
        # callers — in that case fall back to the parsed length.
        rows_processed = (
            payload.attempts_persisted
            if payload.attempts_persisted is not None
            else len(payload.attempts)
        )

        job.rows_processed = rows_processed
        job.rows_failed = rows_failed
        existing = list(job.error_log or [])
        new_errors = [e.model_dump() for e in payload.errors]
        new_errors.extend(
            {
                "row_index": 0,
                "reason": reason,
                "step": "grading",
                "details": {
                    "submission_id": sub_id,
                    "traceback": tb,
                },
            }
            for sub_id, reason, tb in grading_failures
        )
        # Always store an explicit list — empty is still meaningful
        # ("never populated" vs "no errors" stays distinguishable).
        job.error_log = existing + new_errors
        job.source_metadata = {
            **(job.source_metadata or {}),
            **payload.source_metadata,
            "warnings": payload.warnings,
            "attempts_parsed": len(payload.attempts),
            "attempts_skipped_idempotent": payload.attempts_skipped_idempotent or 0,
        }
        job.finished_at = datetime.now(timezone.utc)

        if rows_processed == 0 and rows_failed > 0:
            job.status = ImportJobStatus.FAILED.value
        elif rows_failed > 0:
            job.status = ImportJobStatus.PARTIAL.value
        else:
            job.status = ImportJobStatus.SUCCEEDED.value

    @staticmethod
    def _fail_job(job: ImportJob, exc: Exception, *, step: str) -> None:
        """Record a job-level failure with structured diagnostic context.

        Captures exception class, step name, and full traceback so the
        UI can show a meaningful message and the operator can triage
        without server-log access.
        """
        job.status = ImportJobStatus.FAILED.value
        job.finished_at = datetime.now(timezone.utc)

        reason = f"{type(exc).__name__}: {exc}"
        details: dict[str, Any] = {
            "row_index": 0,  # 0 = job-level failure (not a row)
            "reason": reason,
            "step": step,
            "exception_type": type(exc).__name__,
            "traceback": "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ),
        }
        # If the exception carried structured per-row issues (validation
        # collected all problems), surface each one so the UI can show
        # the full list rather than only the first.
        if isinstance(exc, ImportValidationError) and exc.issues:
            details["issues"] = exc.issues

        existing = list(job.error_log or [])
        existing.append(
            ImportRowError(
                row_index=0,
                reason=reason,
            ).model_dump()
            | {"step": step, "details": details}
        )
        job.error_log = existing
