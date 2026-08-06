"""BWZ-Lyss-Workshop (07.08.2026): idempotentes Provisioning von Institution
+ 20 wiederverwendbaren Demo-Accounts. Muss idempotent sein, da das Skript
notfalls ein zweites Mal gegen Prod laufen könnte (z.B. nach einem Abbruch)."""

from models.auth import Institution, User, UserRole
from services.auth_service import AuthService
from scripts.provision_workshop_accounts import (
    provision_workshop_accounts,
    INSTITUTION_SLUG,
    ACCOUNT_COUNT,
)


def test_creates_institution_and_accounts(test_db):
    result = provision_workshop_accounts(test_db, password="TestPass123")

    institution = (
        test_db.query(Institution).filter(Institution.slug == INSTITUTION_SLUG).first()
    )
    assert institution is not None
    assert institution.is_active is True
    assert result["institution_id"] == institution.id

    users = test_db.query(User).filter(User.institution_id == institution.id).all()
    assert len(users) == ACCOUNT_COUNT
    assert len(result["accounts"]) == ACCOUNT_COUNT

    first = users[0]
    assert first.status == "active"
    assert first.is_email_verified is True
    assert first.is_superuser is False
    assert AuthService.verify_password("TestPass123", first.password_hash)
    assert any(role.name == UserRole.DOZENT.value for role in first.roles)


def test_is_idempotent(test_db):
    provision_workshop_accounts(test_db, password="TestPass123")
    provision_workshop_accounts(test_db, password="TestPass123")

    institutions = (
        test_db.query(Institution).filter(Institution.slug == INSTITUTION_SLUG).all()
    )
    assert len(institutions) == 1

    users = (
        test_db.query(User)
        .filter(User.institution_id == institutions[0].id)
        .all()
    )
    assert len(users) == ACCOUNT_COUNT


def test_account_emails_are_unique_and_patterned(test_db):
    result = provision_workshop_accounts(test_db, password="TestPass123")

    emails = [a["email"] for a in result["accounts"]]
    assert len(emails) == len(set(emails))
    assert all(e.startswith("workshop-lyss-") for e in emails)
    assert all(e.endswith("@examcraft-demo.local") for e in emails)
