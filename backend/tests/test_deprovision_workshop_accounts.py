from models.auth import Institution, User
from scripts.provision_workshop_accounts import provision_workshop_accounts
from scripts.deprovision_workshop_accounts import deprovision_workshop_accounts


def test_deletes_institution_and_all_accounts(test_db):
    provision_workshop_accounts(test_db, password="TestPass123")

    deleted_count = deprovision_workshop_accounts(test_db)

    assert deleted_count == 20
    assert test_db.query(Institution).filter(
        Institution.slug == "bwz-lyss-workshop-2026"
    ).first() is None
    assert test_db.query(User).filter(
        User.email.like("workshop-lyss-%@demo.examcraft-api.fly.dev")
    ).count() == 0


def test_is_safe_to_run_when_nothing_provisioned(test_db):
    deleted_count = deprovision_workshop_accounts(test_db)
    assert deleted_count == 0
