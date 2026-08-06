"""Räumt die BWZ-Lyss-Workshop-Institution (07.08.2026) wieder auf.

MANUELL auszuführen von Daniel nach Abschluss des dritten Durchgangs —
kein automatischer Trigger. Nutzung identisch zu provision_workshop_accounts.py:
    python scripts/deprovision_workshop_accounts.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

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
    db.delete(institution)
    db.commit()
    logger.info(f"Institution '{INSTITUTION_SLUG}' inkl. {user_count} Accounts gelöscht.")
    return user_count


if __name__ == "__main__":
    session = SessionLocal()
    try:
        deleted = deprovision_workshop_accounts(session)
    finally:
        session.close()
    print(f"{deleted} Workshop-Accounts entfernt.")
