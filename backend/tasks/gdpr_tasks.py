"""GDPR Scheduled Deletion (TF-745).

Führt die im DSGVO-Löschantrag (`api/gdpr.py::request_account_deletion`)
zugesagte automatische Löschung nach Ablauf der 30-Tage-Widerrufsfrist aus.
Siehe docs/superpowers/specs/2026-08-27-tf745-gdpr-scheduled-deletion-design.md.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as SATimeoutError

from celery_app import celery_app
from database import SessionLocal
from models.auth import User
from services.audit_service import AuditService
from services.gdpr_deletion_service import delete_user_and_gdpr_data

logger = logging.getLogger(__name__)

# Retry nur bei transienten Fehlern (DB-Verbindungsabbruch, Deadlock,
# Netzwerk-Blip, Connection-Pool-Erschöpfung) — analog
# tasks/import_submissions_task.py:_TRANSIENT_ERRORS, ABER bewusst OHNE das
# dortige bare ``sqlalchemy.exc.DatabaseError``: das ist in SQLAlchemy die
# Oberklasse von ``IntegrityError``/``ProgrammingError``/``DataError``/
# ``InternalError`` — mit ihm in der Liste hätte dieser Fix genau den
# Fehlerfall NICHT gelöst, den er laut Kommentar unten lösen soll (eine
# noch nicht abgedeckte FK-Policy wirft ``IntegrityError``, eine
# ``DatabaseError``-Unterklasse, und würde trotzdem 3x sinnlos retried).
# ``OperationalError`` deckt DBAPI-/Statement-Verbindungsabbrüche/Deadlocks/
# Timeouts ab und ist KEINE Oberklasse von ``IntegrityError``.
# ``sqlalchemy.exc.TimeoutError`` (Connection-Pool-Checkout-Timeout bei
# Pool-Erschöpfung, z. B. viele parallel dispatchte execute_gdpr_deletion-
# Tasks) ist ein eigener, direkter ``SQLAlchemyError``-Ableger — KEIN
# DBAPI-Fehler, wird von ``OperationalError`` also NICHT mitabgedeckt,
# ist aber ebenso klar transient und retry-würdig.
#
# Ein echter Programmfehler (z. B. eine noch nicht abgedeckte FK-Policy, die
# IntegrityError wirft) darf NICHT 3x sinnlos mit 300s-Countdown retried
# werden, bevor er sichtbar wird — bei einem täglichen Sweep sonst bis zu
# 15 Minuten Verzögerung pro betroffenem User, für jeden Sweep erneut.
_TRANSIENT_ERRORS = (OperationalError, SATimeoutError, ConnectionError)


@celery_app.task(name="tasks.gdpr_tasks.process_scheduled_deletions")
def process_scheduled_deletions() -> dict:
    """Täglicher Beat-Sweep: findet fällige Löschungen und dispatcht pro
    User einen ``execute_gdpr_deletion``-Task.

    Fällig = ``deletion_requested_at`` gesetzt UND ``scheduled_deletion_date``
    in der Vergangenheit oder jetzt. Die eigentliche Löschung (inkl.
    Race-Schutz gegen zwischenzeitliche Stornierung) passiert im
    Einzel-Task, damit ein einzelner fehlschlagender User nicht den
    ganzen Sweep blockiert.
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due_users = (
            db.query(User)
            .filter(
                User.deletion_requested_at.isnot(None),
                User.scheduled_deletion_date.isnot(None),
                User.scheduled_deletion_date <= now,
            )
            .all()
        )

        dispatched = 0
        for user in due_users:
            execute_gdpr_deletion.delay(user.id)
            dispatched += 1

        if dispatched:
            logger.info("GDPR-Sweep: %s fällige Löschungen dispatcht", dispatched)

        return {"dispatched": dispatched}
    except Exception:
        # Ausdrücklich mit critical loggen statt den Fehler nur via
        # Celery-FAILURE-State/Sentry propagieren zu lassen: in
        # Self-Hosted-Deployments ohne SENTRY_DSN ist das sonst die
        # einzige Sichtbarkeit für den Ausfall des gesamten täglichen
        # DSGVO-Sweeps — eine fristgebundene Compliance-Pflicht (Art. 17).
        logger.critical(
            "GDPR-Sweep fehlgeschlagen — heutiger Lauf hat KEINE fälligen "
            "Löschungen dispatcht",
            exc_info=True,
        )
        raise
    finally:
        db.close()


@celery_app.task(
    name="tasks.gdpr_tasks.execute_gdpr_deletion",
    bind=True,
    autoretry_for=_TRANSIENT_ERRORS,
    # max_retries sowohl top-level als auch in retry_kwargs, damit
    # Celerys internes Retry und die manuelle
    # ``self.request.retries >= self.max_retries``-Prüfung unten
    # nicht auseinanderlaufen (siehe tasks/import_submissions_task.py:60-64).
    max_retries=3,
    retry_kwargs={"max_retries": 3, "countdown": 300},
)
def execute_gdpr_deletion(self, user_id: int) -> dict:
    """Löscht einen einzelnen fälligen User (DSGVO Art. 17).

    Re-prüft Grace-Period und Storno-Status zum Ausführungszeitpunkt
    (Race-Schutz: der User könnte zwischen Sweep-Dispatch und
    Task-Ausführung storniert haben). Der User wird dabei per
    ``SELECT ... FOR UPDATE`` gelockt, damit ein zeitgleicher
    ``POST /cancel-deletion``-Commit gegen diese Transaktion serialisiert
    wird, statt dass hier mit einem veralteten Snapshot weitergearbeitet
    wird. Bei endgültigem Fehlschlag (letzter Retry-Versuch) wird ein
    Audit-Log-Eintrag mit Status ERROR geschrieben, bevor die Exception
    erneut geworfen wird (Celery markiert den Task dann FAILURE).
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).with_for_update().first()
        if user is None:
            logger.info(
                "GDPR-Löschung übersprungen: User %s existiert nicht mehr", user_id
            )
            return {"status": "skipped", "reason": "user_not_found"}

        if not user.deletion_requested_at:
            logger.info("GDPR-Löschung übersprungen: User %s hat storniert", user_id)
            return {"status": "skipped", "reason": "cancelled"}

        if (
            user.scheduled_deletion_date is None
            or user.scheduled_deletion_date > datetime.now(timezone.utc)
        ):
            logger.info(
                "GDPR-Löschung übersprungen: User %s noch nicht fällig", user_id
            )
            return {"status": "skipped", "reason": "not_due"}

        result = delete_user_and_gdpr_data(db, user, action="account_deleted_scheduled")
        return {"status": "deleted", **result}

    except Exception as exc:
        # Erst loggen, DANN rollback — analog api/gdpr.py: schlägt
        # db.rollback() selbst fehl (am ehesten bei genau den
        # OperationalError/ConnectionError-Fällen, für die _TRANSIENT_ERRORS
        # existiert), soll die Diagnose trotzdem im Log stehen, statt von
        # einer Sekundär-Exception verdeckt zu werden.
        logger.error(
            "GDPR-Löschung fehlgeschlagen für User %s: %s",
            user_id,
            exc,
            exc_info=True,
        )
        db.rollback()
        # "Letzter Versuch" bedeutet zweierlei: entweder Celery hat die
        # konfigurierten Retries ausgeschöpft (transiente Fehler, siehe
        # _TRANSIENT_ERRORS), oder der Fehler ist gar nicht retry-fähig
        # (autoretry_for greift nicht) — dann gibt es nie einen weiteren
        # Versuch und dieser hier IST bereits der letzte. Ohne den zweiten
        # Fall würde ein permanenter Programmfehler (z. B. IntegrityError
        # durch eine fehlende FK-Policy) NIE einen Audit-Log-Eintrag
        # bekommen, weil `self.request.retries` bei einem nicht-retry-fähigen
        # Fehler für immer 0 bleibt.
        is_final_attempt = self.request.retries >= self.max_retries or not isinstance(
            exc, _TRANSIENT_ERRORS
        )
        if is_final_attempt:
            # Bewusst NICHT fail-closed (kein `raise` bei None): die
            # ursprüngliche Exception wird unten ohnehin re-raised und
            # propagiert zu Celery (FAILURE-State) bzw. Sentry — das
            # Fehlschlags-Audit-Log ist damit best effort, nicht die einzige
            # Sichtbarkeit. Ein fail-closed `raise` wie in
            # `gdpr_deletion_service.delete_user_and_gdpr_data` würde hier
            # nur eine zweite Exception innerhalb des except-Blocks riskieren
            # (und die erste, eigentliche Fehlerursache verdecken); der
            # `is None`-Check unten sorgt trotzdem für ein sichtbares Signal.
            failure_audit_entry = AuditService.log_action(
                db=db,
                action="gdpr_scheduled_deletion_failed",
                user_id=user_id,
                resource_type=AuditService.RESOURCE_USER,
                resource_id=str(user_id),
                status=AuditService.STATUS_ERROR,
                error_message=str(exc),
            )
            if failure_audit_entry is None:
                logger.critical(
                    "GDPR-Löschung endgültig fehlgeschlagen für User %s UND "
                    "das Fehlschlags-Audit-Log konnte ebenfalls nicht "
                    "geschrieben werden",
                    user_id,
                )
        raise
    finally:
        db.close()
