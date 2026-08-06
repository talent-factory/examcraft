"""Räumt die BWZ-Lyss-Workshop-Institution (07.08.2026) wieder auf.

MANUELL auszuführen von Daniel nach Abschluss des dritten Durchgangs —
kein automatischer Trigger.

Muss vor der Ausführung separat in den laufenden Prod-Container hochgeladen
werden (kein Redeploy, siehe Task 3 im Implementierungsplan):
    fly ssh sftp put core/backend/scripts/deprovision_workshop_accounts.py \\
        scripts/deprovision_workshop_accounts.py -a examcraft-api

Danach im Container ausführen:
    python scripts/deprovision_workshop_accounts.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import SessionLocal
from models.auth import Institution
from scripts.provision_workshop_accounts import INSTITUTION_SLUG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def deprovision_workshop_accounts(db: Session) -> int:
    """Löscht die Workshop-Institution samt aller zugehörigen Accounts
    (Institution.users trägt cascade="all, delete-orphan" — ein ORM-Delete
    der Institution räumt alle 20 User-Zeilen mit auf). Gibt die Anzahl
    gelöschter User zurück; 0 wenn nichts (mehr) vorhanden ist.
    """
    institution = (
        db.query(Institution).filter(Institution.slug == INSTITUTION_SLUG).first()
    )
    if institution is None:
        logger.info("Keine Workshop-Institution gefunden — nichts zu tun.")
        return 0

    user_count = len(institution.users)
    try:
        db.delete(institution)
        db.commit()
    except IntegrityError:
        db.rollback()
        logger.error(
            "Löschen fehlgeschlagen (IntegrityError) — vermutlich blockiert eine "
            "abhängige Zeile ohne Cascade-Delete den Löschvorgang (z.B. eine "
            "Prompt-Wizard-Session eines Workshop-Users, siehe "
            "premium/backend/models/wizard.py:WizardSession.user_id). "
            "Transaktion wurde zurückgerollt, keine Daten wurden geändert."
        )
        raise

    logger.info(
        f"Institution '{INSTITUTION_SLUG}' inkl. {user_count} Accounts gelöscht."
    )
    return user_count


if __name__ == "__main__":
    session = SessionLocal()
    try:
        deleted = deprovision_workshop_accounts(session)
    finally:
        session.close()
    print(f"{deleted} Workshop-Accounts entfernt.")
