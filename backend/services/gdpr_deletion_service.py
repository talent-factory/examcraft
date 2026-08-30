"""GDPR-Löschservice (TF-745).

Löscht einen User endgültig (DSGVO Art. 17) und alle mit ihm verknüpften
Daten. Der Daten-Fanout läuft dabei über die bereits im Schema kodierte
Retention-Policy:

  - Hart gelöscht (FK ondelete=CASCADE): Documents, UserSessions,
    OAuthAccounts, EmailVerificationTokens, OrgUnit-Mitgliedschaften,
    QuestionGenerationJobs, Rollen-Zuordnungen, Prompt-Wizard-Sitzungen
    (WizardSessions, Premium), Chat-Sitzungen (ChatSessions, Premium),
    persönliche Dokument-Tags (DocumentPersonalTags), Help-Center-Daten
    (HelpOnboardingProgress, HelpConversations, HelpDismissedHints).
  - Anonymisiert, Zeile bleibt (FK ondelete=SET NULL): Exams,
    QuestionReviews, AuditLogs (user_id + impersonator_user_id),
    ImpersonationSessions, Grades/GradeHistory/ImportJobs/
    MoodleFeedbackPushJobs (Noten-/Import-Audit-Trail), Tags,
    TagMergeLogs, CompetencyFrameworks, Subscriptions, Prompts (Premium),
    HelpFaqCache (approved_by).

  Diese Liste ist der Stand zum Zeitpunkt dieses Reviews, von Hand gegen
  jede ``ForeignKey("users.id", ...)``-Deklaration in core/backend/models
  und premium/backend/models abgeglichen — sie kann bei neuen Tabellen
  wieder driften. ``test_users_fk_ondelete_policy.py`` sichert NUR ab, dass
  jede tatsächliche FK eine gültige Policy (CASCADE/SET NULL) hat — es
  prüft NICHT, ob diese Aufzählung hier vollständig ist, und deckt nur
  Core-Modelle ab (Premium-Modelle sind in der Standard-Core-Testsuite
  nicht registriert). Diese Aufzählung bleibt also Handarbeit.

Hochgeladene Dateien (S3 oder lokale Disk) werden explizit entfernt
(``_delete_document_files``) — die FK-Cascade löscht nur die
``documents``-Zeilen, nicht die zugehörigen Objekte im Storage. Die Pfade
werden VOR dem Löschen eingesammelt (danach ist die Document->User-
Zuordnung weg), die Dateien selbst aber bewusst erst NACH dem
erfolgreichen ``db.commit()`` entfernt — sonst wären sie bei einem
Commit-Fehlschlag unwiederbringlich weg, obwohl der User dank Rollback
weiterhin existiert. Details siehe ``_delete_document_files``-Docstring.

Siehe docs/superpowers/specs/2026-08-27-tf745-gdpr-scheduled-deletion-design.md
für die vollständige Analyse der FK-Policy und die Design-Entscheidungen.
"""

import logging
import os

from sqlalchemy.orm import Session

from models.auth import User
from models.document import Document
from services.audit_service import AuditService
from services.storage_service import storage_service

logger = logging.getLogger(__name__)


def _document_file_paths(db: Session, user_id: int) -> list[str]:
    """Sammelt die ``file_path``-Werte aller Documents des Users — VOR dem
    DB-Löschen, danach ist die Zuordnung Document->User futsch."""
    return [
        file_path
        for (file_path,) in db.query(Document.file_path)
        .filter(Document.user_id == user_id)
        .all()
    ]


def _delete_document_files(file_paths: list[str], user_id: int) -> None:
    """Entfernt die Storage-Objekte (S3 oder lokale Disk) zu den gegebenen
    Document-``file_path``-Werten.

    Wird bewusst ERST NACH dem erfolgreichen ``db.commit()`` aufgerufen
    (siehe ``delete_user_and_gdpr_data``): würde der Storage-Cleanup VOR dem
    Commit laufen und der Commit dann fehlschlagen (z. B. IntegrityError
    durch eine noch nicht abgedeckte FK-Policy), wären die Dateien
    unwiederbringlich weg, obwohl der User (und seine Documents-Zeilen)
    wegen des Rollbacks weiterhin existieren — ein Konto mit toten
    Datei-Links. Nach erfolgreichem Commit ist der umgekehrte Fehlerfall
    (Crash zwischen Commit und Cleanup, verwaistes Objekt bleibt liegen)
    das kleinere, hier akzeptierte Risiko.

    Best-effort, analog zu ``DocumentService.delete_document``: ein
    einzelner fehlschlagender Storage-Delete (z. B. Objekt bereits weg,
    S3 vorübergehend nicht erreichbar) wird geloggt, aber nicht erneut
    geworfen — der User ist zu diesem Zeitpunkt bereits gelöscht.
    """
    for file_path in file_paths:
        try:
            if storage_service.is_configured and file_path.startswith("uploads/"):
                storage_service.delete_file(file_path)
            elif os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            logger.warning(
                "GDPR-Löschung: Storage-Datei %s (User %s) konnte nicht "
                "entfernt werden — User war bereits erfolgreich gelöscht",
                file_path,
                user_id,
                exc_info=True,
            )


def delete_user_and_gdpr_data(db: Session, user: User, *, action: str) -> dict:
    """Löscht `user` und alle verknüpften Daten atomar.

    Der Audit-Eintrag wird VOR dem Löschen in derselben Transaktion
    geschrieben (``commit=False`` — nur geflusht) und dadurch vom selben
    ``db.commit()`` gleich mit-anonymisiert (``user_id`` -> NULL) — konsistent
    mit allen anderen historischen Logs des Accounts.

    Args:
        db: DB-Session. Der Aufrufer übergibt eine offene Session; diese
            Funktion committet die gesamte Operation atomar, schliesst die
            Session aber NICHT (Lifecycle bleibt beim Aufrufer).
        user: Der zu löschende User (muss an ``db`` gebunden sein).
        action: Audit-Action-String für die Löschung — erlaubt Aufrufern,
            zwischen Sofortlöschung (``account_deleted_immediately``) und
            automatischer Fristlöschung (``account_deleted_scheduled``) zu
            unterscheiden.

    Returns:
        dict mit ``user_id`` und ``email`` des gelöschten Users (für Logging
        und Tests — nach dem Löschen sind diese Werte am ORM-Objekt nicht
        mehr zuverlässig abrufbar).

    Raises:
        RuntimeError: wenn der Audit-Log-Eintrag nicht geschrieben werden
            konnte (fail-closed, siehe unten) — die Session ist dann bereits
            zurückgerollt, der User bleibt unverändert bestehen.
        Exception: der ORIGINALE Fehlertyp (z. B. ``IntegrityError`` durch
            eine noch nicht abgedeckte FK-Policy), falls ``db.delete(user)``/
            ``db.commit()`` selbst fehlschlägt — wird unverändert erneut
            geworfen (bare ``raise``), nicht in ``RuntimeError`` umgewandelt.
            Auch hier ist die Session bereits zurückgerollt.
    """
    user_id = user.id
    email = user.email

    audit_entry = AuditService.log_action(
        db=db,
        action=action,
        user_id=user_id,
        resource_type=AuditService.RESOURCE_USER,
        resource_id=str(user_id),
        additional_data={"email": email},
        commit=False,
    )
    if audit_entry is None:
        # Fail-closed, konsistent mit AuditService.log_superuser_bypass /
        # log_admin_cross_owner: Audit-IST-der-Compliance-Nachweis — ein
        # fehlgeschlagener Audit-Log-Schreibversuch darf die Löschung nicht
        # unbeaufsichtigt durchlaufen lassen (und log_action hat bei Fehler
        # bereits intern db.rollback() aufgerufen).
        raise RuntimeError(
            f"GDPR-Löschung abgebrochen: Audit-Log-Eintrag konnte nicht "
            f"geschrieben werden für User {user_id}"
        )

    try:
        # Storage-Pfade VOR dem Löschen einsammeln (danach ist die
        # Zuordnung weg) — die eigentlichen Dateien werden aber erst NACH
        # dem Commit entfernt, siehe _delete_document_files-Docstring. Im
        # selben try-Block wie delete/commit, damit ein Fehler HIER (z. B.
        # ein DB-Verbindungsabbruch während dieser Query) dieselbe
        # Rollback-Garantie bekommt wie ein Fehler beim eigentlichen Löschen
        # — sonst bliebe der zuvor geflushte (aber uncommittete) Audit-Log-
        # Eintrag ungerollbackt in der Session zurück.
        document_file_paths = _document_file_paths(db, user_id)
        db.delete(user)
        db.commit()
    except Exception:
        # Eigenes Rollback statt Aufrufer-Vertrag: beide aktuellen Call-Sites
        # (api/gdpr.py, tasks/gdpr_tasks.py) rollen zwar selbst zurück, aber
        # diese Funktion soll auch für künftige Aufrufer (z. B. ein
        # Admin-Bulk-Delete) garantiert eine konsistente Session hinterlassen,
        # statt sich stillschweigend auf fremde Disziplin zu verlassen.
        db.rollback()
        raise

    _delete_document_files(document_file_paths, user_id)

    logger.info("GDPR-Löschung abgeschlossen für User %s (%s)", user_id, email)
    return {"user_id": user_id, "email": email}
