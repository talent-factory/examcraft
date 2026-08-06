"""BWZ-Lyss-Workshop (07.08.2026, Inputreferat "ExamCraft AI"): idempotentes
Provisioning fiktiven Institution + 20 wiederverwendbaren Demo-Accounts
in Produktion.

Sessions laufen daher sequentiell auf gemeinsamen Accounts — wir bauen
ein einziger Account-Pool statt 60 Einzel-Accounts (siehe docs/superpowers/specs/2026-08-06-bwz-lyss-workshop-inputreferat-design.md).

Idempotent: mehrfacher Aufruf legt weder Institution noch Accounts doppelt an,
sondern aktualisiert Passwort/Status/Rolle bestehender Zeilen.
"""

import logging
import os
import sys

from sqlalchemy import func
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.auth import Institution, Role, User, UserRole, UserStatus
from services.auth_service import AuthService
from utils.seed_roles import seed_default_roles

logger = logging.getLogger(__name__)

INSTITUTION_NAME = "BWZ Lyss Workshop"
INSTITUTION_SLUG = "bwz-lyss-workshop-2026"
EMAIL_DOMAIN = "examcraft-demo.local"
ACCOUNT_COUNT = 20
DEFAULT_PASSWORD = "BwzLyss2026"


def _get_or_create_institution(db: Session) -> Institution:
    """Findet oder erstellt die Workshop-Institution."""
    institution = (
        db.query(Institution).filter(Institution.slug == INSTITUTION_SLUG).first()
    )

    if institution is None:
        institution = Institution(
            name=INSTITUTION_NAME,
            slug=INSTITUTION_SLUG,
            is_active=True,
            subscription_tier="enterprise",
            max_users=-1,
            max_documents=-1,
            max_questions_per_month=-1,
            created_at=func.now(),
        )
        db.add(institution)
        db.flush()
    else:
        institution.is_active = True

    return institution


def _get_or_create_user(
    db: Session,
    institution: Institution,
    index: int,
    password_hash: str,
    dozent_role: Role,
) -> User:
    """Findet oder erstellt einen Demo-User mit idempotenten Passwort/Status-Updates."""
    email = f"workshop-lyss-{index:02d}@{EMAIL_DOMAIN}"

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        user = User(
            email=email,
            first_name="Workshop",
            last_name=f"Teilnehmer {index:02d}",
            password_hash=password_hash,
            institution_id=institution.id,
            status=UserStatus.ACTIVE.value,
            is_email_verified=True,
            is_superuser=False,
            password_changed_at=func.now(),
        )
        db.add(user)
        db.flush()
    else:
        user.password_hash = password_hash
        user.institution_id = institution.id
        user.status = UserStatus.ACTIVE.value
        user.is_email_verified = True
        user.is_superuser = False
        user.password_changed_at = func.now()

    if dozent_role not in user.roles:
        user.roles.append(dozent_role)

    return user


def provision_workshop_accounts(
    db: Session, password: str = DEFAULT_PASSWORD, count: int = ACCOUNT_COUNT
) -> dict:
    """Provisioning idempotent: Institution + Account-Pool."""
    seed_default_roles(db)

    dozent_role = db.query(Role).filter(Role.name == UserRole.DOZENT.value).first()
    if dozent_role is None:
        raise RuntimeError(
            "dozent-Rolle nicht gefunden trotz seed_default_roles()-Aufruf. "
            "Prüfe die Rollenseeding-Logik."
        )

    institution = _get_or_create_institution(db)
    password_hash = AuthService.get_password_hash(password)

    accounts = []
    for i in range(1, count + 1):
        user = _get_or_create_user(db, institution, i, password_hash, dozent_role)
        accounts.append({"email": user.email, "password": password})

    db.commit()
    logger.info(
        f"{len(accounts)} Accounts für Institution '{institution.name}' "
        f"({INSTITUTION_SLUG}) provisioned/updated."
    )

    return {
        "institution_id": institution.id,
        "institution_slug": institution.slug,
        "accounts": accounts,
    }


if __name__ == "__main__":
    from database import SessionLocal

    session = SessionLocal()
    try:
        result = provision_workshop_accounts(session)
        print(f"\n✓ Institution: {result['institution_slug']}")
        print(f"✓ Accounts provisioned: {len(result['accounts'])}\n")
        print("=" * 70)
        print(f"{'Email':<40} | {'Password':<28}")
        print("-" * 70)
        for account in result["accounts"]:
            print(f"{account['email']:<40} | {account['password']:<28}")
        print("=" * 70)
    finally:
        session.close()
