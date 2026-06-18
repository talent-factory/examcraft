"""Orchestrate one feedback push job end to end (TF-435)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from enums import MoodleFeedbackPushStatus, StudentPushStatus
from models.exam import Exam
from models.submission import MoodleConnection, MoodleFeedbackPushJob
from services.moodle_feedback.payload import MissingQuizIdError, build_feedback_payload
from services.moodle_feedback.selection import select_transport
from services.moodle_feedback.ws_client import MoodleWsError
from utils.secret_encryption import SecretEncryptionError, decrypt_secret

logger = logging.getLogger(__name__)


class MoodleConnectionError(RuntimeError):
    """Connection/token/probe stage failed — distinct from a push failure.

    Lets the job's error_log carry ``scope="connection"`` so the UI can render
    an actionable "check your Moodle token/connection" message rather than an
    opaque internal error.
    """


class MoodleFeedbackPushService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, *, job_id: int, force_transport: str | None = None) -> None:
        # acks_late=True means a broker-visibility timeout can redeliver this
        # task while a slow push is still in flight (or already finished). Lock
        # the row and claim it only while still QUEUED, so a redelivered twin
        # bails idempotently instead of firing a second, interleaving push
        # against Moodle. (with_for_update is a no-op on SQLite; the QUEUED
        # check still guards there.)
        job = (
            self.db.query(MoodleFeedbackPushJob)
            .filter(MoodleFeedbackPushJob.id == job_id)
            .with_for_update()
            .one()
        )
        if job.status != MoodleFeedbackPushStatus.QUEUED.value:
            logger.info(
                "Feedback-Push job_id=%s bereits in Status %r — übersprungen.",
                job_id,
                job.status,
            )
            self.db.commit()  # release the row lock
            return
        job.status = MoodleFeedbackPushStatus.PROCESSING.value
        job.started_at = datetime.now(timezone.utc)
        self.db.commit()

        try:
            self._execute(job, force_transport)
        except MissingQuizIdError as exc:
            self._fail(job, scope="config", exc=exc)
        except MoodleConnectionError as exc:
            self._fail(job, scope="connection", exc=exc)
        except Exception as exc:  # noqa: BLE001 — record, never crash the worker
            self._fail(job, scope="job", exc=exc)

    def _fail(self, job: MoodleFeedbackPushJob, *, scope: str, exc: Exception) -> None:
        logger.exception("Feedback-Push fehlgeschlagen (job_id=%s)", job.id)
        job.status = MoodleFeedbackPushStatus.FAILED.value
        job.error_log = [
            {"scope": scope, "reason": str(exc), "error_type": type(exc).__name__}
        ]
        job.finished_at = datetime.now(timezone.utc)
        self.db.commit()

    def _execute(self, job: MoodleFeedbackPushJob, force_transport: str | None) -> None:
        connection = (
            self.db.query(MoodleConnection)
            .filter(MoodleConnection.institution_id == job.institution_id)
            .one_or_none()
        )
        if connection is None:
            raise MoodleConnectionError(
                "Keine Moodle-Connection für diese Institution."
            )
        try:
            token = decrypt_secret(connection.token_encrypted)
        except SecretEncryptionError as exc:
            raise MoodleConnectionError(
                f"Token-Entschlüsselung fehlgeschlagen: {exc}"
            ) from exc

        exam = self.db.query(Exam).filter(Exam.id == job.exam_id).one()
        payload = build_feedback_payload(self.db, exam)  # may raise MissingQuizIdError

        try:
            transport = select_transport(
                connection.base_url, token, force=force_transport
            )
        except MoodleWsError as exc:
            # Probe stage — a bad token or unreachable site fails here, before
            # any student push. Classify it so the user sees the right remedy.
            raise MoodleConnectionError(
                f"Moodle-Verbindung konnte nicht geprüft werden "
                f"(Token/Erreichbarkeit): {exc}"
            ) from exc

        results = transport.push(payload)

        # Exhaustive bucketing — every known status maps to exactly one counter.
        # `partial` is folded into `failed` (no transport emits it yet; Plan 2's
        # plugin may). Unknown statuses are impossible post-normalisation, but
        # the else branch logs+counts-failed rather than dropping silently.
        pushed = skipped = failed = 0
        for r in results.values():
            if r.status == StudentPushStatus.OK:
                pushed += 1
            elif r.status == StudentPushStatus.NOT_FOUND:
                skipped += 1
            elif r.status in (StudentPushStatus.ERROR, StudentPushStatus.PARTIAL):
                failed += 1
            else:  # pragma: no cover — normalisation guarantees this is unreachable
                logger.error(
                    "Unbekannter Push-Status %r — als failed gezählt", r.status
                )
                failed += 1

        error_log: list[dict] = [
            {
                "external_id": r.external_id,
                "status": str(r.status),
                "errors": r.errors or [],
            }
            for r in results.values()
            if r.status != StudentPushStatus.OK
        ]
        error_log += [{"scope": "warning", "reason": w} for w in payload.warnings]
        if not payload.students:
            # Ran fine, but nothing was eligible — make "pushed nothing" visible
            # rather than indistinguishable from "pushed everyone".
            error_log.append(
                {
                    "scope": "info",
                    "reason": "Keine vollständig geprüften Abgaben zum Zurückschreiben.",
                }
            )

        job.transport = transport.name.value
        # Count the rows we actually bucketed (results is keyed by external_id),
        # so pushed + skipped + failed == students_total always holds — even if
        # two submissions collapsed onto one identifier. The DB CHECK
        # `check_moodle_feedback_push_counter_sum` enforces this invariant.
        job.students_total = len(results)
        job.students_pushed = pushed
        job.students_failed = failed
        job.students_skipped = skipped
        job.error_log = error_log or None
        job.status = MoodleFeedbackPushStatus.COMPLETED.value
        job.finished_at = datetime.now(timezone.utc)
        connection.last_used_at = datetime.now(timezone.utc)
        self.db.commit()
