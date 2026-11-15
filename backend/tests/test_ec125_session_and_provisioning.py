"""Sessions and JIT provisioning for the Zitadel login (EXAMCRAFT-125)."""

from datetime import datetime, timedelta, timezone

import pytest

from models.auth import AuthSession, Institution, Role, User, UserRole, UserStatus
from services import session_service
from services.user_provisioning import (
    EmailConflictError,
    MissingClaimError,
    UserLimitReachedError,
    get_or_provision_user,
)


@pytest.fixture
def seeded(test_db):
    inst = Institution(
        name="Schule",
        slug="schule-ec125",
        domain="schule-ec125.example",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=100,
    )
    test_db.add(inst)
    for name in (UserRole.ADMIN.value, UserRole.DOZENT.value, UserRole.VIEWER.value):
        if not test_db.query(Role).filter(Role.name == name).first():
            test_db.add(
                Role(
                    name=name,
                    display_name=name,
                    description=name,
                    permissions=[],
                    is_system_role=True,
                )
            )
    test_db.commit()
    return inst


def _claims(sub="sub-1", email="a@schule-ec125.example", **extra):
    return {"sub": sub, "email": email, "email_verified": True, **extra}


class TestSessions:
    def _user(self, db, inst, email="s@x.example", sub="s-1"):
        user = User(
            email=email,
            zitadel_sub=sub,
            first_name="S",
            last_name="U",
            institution_id=inst.id,
            status=UserStatus.ACTIVE.value,
        )
        db.add(user)
        db.commit()
        return user

    def test_token_is_stored_only_as_hash(self, test_db, seeded):
        user = self._user(test_db, seeded)
        token, row = session_service.create_session(test_db, user.id)
        assert row.token_hash != token
        assert len(row.token_hash) == 64
        assert session_service.get_active_session(test_db, token).id == row.id

    def test_unknown_or_missing_token(self, test_db, seeded):
        assert session_service.get_active_session(test_db, None) is None
        assert session_service.get_active_session(test_db, "nope") is None

    def test_expired_session_is_rejected_and_deleted(self, test_db, seeded):
        user = self._user(test_db, seeded)
        token, row = session_service.create_session(
            test_db, user.id, max_age=timedelta(seconds=-1)
        )
        assert session_service.get_active_session(test_db, token) is None
        assert test_db.query(AuthSession).count() == 0

    def test_default_lifetime_is_14_days_absolute(self, test_db, seeded):
        user = self._user(test_db, seeded)
        _token, row = session_service.create_session(test_db, user.id)
        delta = row.expires_at - datetime.now(timezone.utc)
        assert timedelta(days=13, hours=23) < delta <= timedelta(days=14)

    def test_delete_is_idempotent(self, test_db, seeded):
        user = self._user(test_db, seeded)
        token, _ = session_service.create_session(test_db, user.id)
        session_service.delete_session(test_db, token)
        session_service.delete_session(test_db, token)
        session_service.delete_session(test_db, None)
        assert session_service.get_active_session(test_db, token) is None

    def test_impersonation_cookie_needs_matching_admin_session(self, test_db, seeded):
        admin = self._user(test_db, seeded, "adm@x.example", "adm")
        admin.is_superuser = True  # may impersonate
        test_db.commit()
        target = self._user(test_db, seeded, "tgt@x.example", "tgt")
        other = self._user(test_db, seeded, "oth@x.example", "oth")
        from models.auth import ImpersonationSession

        imp = ImpersonationSession(
            admin_user_id=admin.id, target_user_id=target.id, reason="support"
        )
        test_db.add(imp)
        test_db.flush()
        admin_tok, _ = session_service.create_session(test_db, admin.id)
        other_tok, _ = session_service.create_session(test_db, other.id)
        imp_tok, _ = session_service.create_session(
            test_db,
            target.id,
            max_age=session_service.IMPERSONATION_SESSION_MAX_AGE,
            impersonator_id=admin.id,
            impersonation_session_id=imp.id,
        )
        eff = session_service.resolve_effective_session(test_db, admin_tok, imp_tok)
        assert eff.user_id == target.id and eff.impersonator_id == admin.id
        # the impersonation cookie of another admin's session is ignored
        eff = session_service.resolve_effective_session(test_db, other_tok, imp_tok)
        assert eff.user_id == other.id
        # the impersonation cookie alone is worthless
        assert session_service.resolve_effective_session(test_db, None, imp_tok) is None

    def test_recent_login_window(self, test_db, seeded):
        user = self._user(test_db, seeded)
        _tok, row = session_service.create_session(test_db, user.id)
        # a fresh session alone proves nothing (silent SSO login)
        assert not session_service.is_recent_login(row)
        row.authenticated_at = datetime.now(timezone.utc)
        assert session_service.is_recent_login(row)
        row.authenticated_at = datetime.now(timezone.utc) - timedelta(hours=1)
        assert not session_service.is_recent_login(row)


class TestProvisioning:
    def test_known_sub_resolves_without_creating(self, test_db, seeded):
        user, created = get_or_provision_user(test_db, _claims())
        assert created is True
        again, created = get_or_provision_user(test_db, _claims(email="changed@x.y"))
        assert created is False and again.id == user.id

    def test_domain_institution_first_user_becomes_admin(self, test_db, seeded):
        user, _ = get_or_provision_user(test_db, _claims())
        assert user.institution_id == seeded.id
        assert [r.name for r in user.roles] == [UserRole.ADMIN.value]
        assert user.status == UserStatus.ACTIVE.value
        assert user.password_hash is None
        assert user.zitadel_sub == "sub-1"

    def test_second_user_is_dozent(self, test_db, seeded):
        get_or_provision_user(test_db, _claims())
        second, _ = get_or_provision_user(
            test_db, _claims(sub="sub-2", email="b@schule-ec125.example")
        )
        assert [r.name for r in second.roles] == [UserRole.DOZENT.value]

    def test_unknown_domain_gets_personal_institution_without_admin(
        self, test_db, seeded
    ):
        user, _ = get_or_provision_user(
            test_db, _claims(sub="sub-p", email="solo@nowhere.example")
        )
        assert user.institution.slug == "solo-personal"
        assert [r.name for r in user.roles] == [UserRole.DOZENT.value]

    def test_unverified_email_does_not_join_the_domain_institution(
        self, test_db, seeded
    ):
        user, _ = get_or_provision_user(
            test_db, _claims(sub="sub-u", email_verified=False)
        )
        assert user.institution_id != seeded.id
        assert user.institution.slug.endswith("-personal")
        assert [r.name for r in user.roles] == [UserRole.DOZENT.value]
        assert user.is_email_verified is False

    def test_missing_email_verified_claim_counts_as_unverified(self, test_db, seeded):
        claims = _claims(sub="sub-m")
        del claims["email_verified"]
        user, _ = get_or_provision_user(test_db, claims)
        assert user.institution_id != seeded.id

    def test_personal_slug_collision_never_reuses_the_institution(
        self, test_db, seeded
    ):
        first, _ = get_or_provision_user(
            test_db, _claims(sub="sub-a", email="max@one.example")
        )
        second, _ = get_or_provision_user(
            test_db, _claims(sub="sub-b", email="max@two.example")
        )
        assert first.institution_id != second.institution_id
        assert first.institution.slug == "max-personal"
        assert second.institution.slug.startswith("max-")
        assert second.institution.slug != first.institution.slug

    def test_names_from_claims(self, test_db, seeded):
        user, _ = get_or_provision_user(
            test_db, _claims(given_name="Anna", family_name="Muster")
        )
        assert (user.first_name, user.last_name) == ("Anna", "Muster")

    def test_email_of_other_user_is_a_conflict_no_linking(self, test_db, seeded):
        get_or_provision_user(test_db, _claims())
        with pytest.raises(EmailConflictError):
            get_or_provision_user(test_db, _claims(sub="other-sub"))

    def test_missing_claims(self, test_db, seeded):
        with pytest.raises(MissingClaimError):
            get_or_provision_user(test_db, {"email": "x@y.z"})
        with pytest.raises(MissingClaimError):
            get_or_provision_user(test_db, {"sub": "new"})

    def test_user_limit_is_enforced(self, test_db, seeded):
        seeded.max_users = 1
        test_db.commit()
        get_or_provision_user(test_db, _claims())
        with pytest.raises(UserLimitReachedError):
            get_or_provision_user(
                test_db, _claims(sub="sub-2", email="b@schule-ec125.example")
            )


class TestImpersonatorStillAllowed:
    def _setup(self, db, inst):
        from models.auth import ImpersonationSession

        admin = User(
            email="adm2@x.example",
            zitadel_sub="adm2",
            first_name="A",
            last_name="D",
            institution_id=inst.id,
            status=UserStatus.ACTIVE.value,
            is_superuser=True,
        )
        target = User(
            email="tgt2@x.example",
            zitadel_sub="tgt2",
            first_name="T",
            last_name="G",
            institution_id=inst.id,
            status=UserStatus.ACTIVE.value,
        )
        db.add_all([admin, target])
        db.flush()
        imp = ImpersonationSession(
            admin_user_id=admin.id, target_user_id=target.id, reason="support"
        )
        db.add(imp)
        db.flush()
        admin_tok, _ = session_service.create_session(db, admin.id)
        imp_tok, _ = session_service.create_session(
            db,
            target.id,
            max_age=session_service.IMPERSONATION_SESSION_MAX_AGE,
            impersonator_id=admin.id,
            impersonation_session_id=imp.id,
        )
        return admin, target, admin_tok, imp_tok

    def test_active_admin_keeps_the_impersonation(self, test_db, seeded):
        admin, target, admin_tok, imp_tok = self._setup(test_db, seeded)
        eff = session_service.resolve_effective_session(test_db, admin_tok, imp_tok)
        assert eff.user_id == target.id

    def test_suspended_admin_loses_the_impersonation(self, test_db, seeded):
        admin, _target, admin_tok, imp_tok = self._setup(test_db, seeded)
        admin.status = UserStatus.SUSPENDED.value
        test_db.commit()
        eff = session_service.resolve_effective_session(test_db, admin_tok, imp_tok)
        assert eff.user_id == admin.id
        assert session_service.get_active_session(test_db, imp_tok) is None

    def test_admin_without_permission_loses_the_impersonation(self, test_db, seeded):
        admin, _target, admin_tok, imp_tok = self._setup(test_db, seeded)
        admin.is_superuser = False
        test_db.commit()
        eff = session_service.resolve_effective_session(test_db, admin_tok, imp_tok)
        assert eff.user_id == admin.id
