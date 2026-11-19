"""Just-in-time user provisioning for the Zitadel login (EXAMCRAFT-125).

One function replaces the two former code paths (self-registration and
OAuth sign-up). Users are resolved by ``users.zitadel_sub`` only; an
unknown ``sub`` creates a user:

* institution by e-mail domain (only for an IdP-verified address),
  otherwise a personal institution of their own,
* the first user of a non-personal institution becomes its ``admin``,
  everybody else ``dozent`` (fallback ``viewer``).

There is deliberately no linking by e-mail address: a ``sub`` that is
unknown while the e-mail already belongs to another user is a conflict
(wrongly imported data), not something to resolve silently.
"""

import hashlib
import logging
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.auth import Institution, Role, User, UserRole, UserStatus

logger = logging.getLogger(__name__)


class EmailConflictError(Exception):
    """The e-mail belongs to a user with another Zitadel ``sub``."""


class AccountNotMigratedError(Exception):
    """The e-mail belongs to a local user without a Zitadel ``sub`` yet.

    The account exists but has not been imported into Zitadel (EXAMCRAFT-130).
    Never linked by e-mail, the user has to wait for the import or ask support.
    """


class MissingClaimError(Exception):
    """The claims lack ``sub`` or ``email``."""


class UserLimitReachedError(Exception):
    """The institution's user limit is reached."""


class ProvisioningError(Exception):
    """A new user cannot be set up (e.g. the roles are not seeded)."""


def _names(claims: Dict[str, Any], email: str) -> tuple[str, str]:
    first = (claims.get("given_name") or "").strip()
    last = (claims.get("family_name") or "").strip()
    if not first and not last:
        full = (claims.get("name") or "").strip()
        if full:
            first, _, last = full.partition(" ")
    if not first:
        first = email.split("@")[0]
    return first, last.strip()


def _resolve_institution(
    db: Session,
    sub: str,
    email: str,
    first: str,
    last: str,
    email_verified: bool,
) -> Institution:
    """Institution of a new user.

    The e-mail domain only counts if the IdP vouches for the address
    (``email_verified``): otherwise anybody could register an unconfirmed
    address on a school's domain, join that tenant and even become its
    first admin. Everybody else gets a personal institution of their own.
    An existing personal institution is never reused: a slug collision
    (same local part, other domain) must not put a stranger into someone
    else's tenant, so a colliding slug gets a suffix derived from the ``sub``.
    """
    local, _, domain = email.partition("@")
    if email_verified:
        institution = db.query(Institution).filter(Institution.domain == domain).first()
        if institution:
            return institution

    slug = f"{local}-personal"
    if db.query(Institution).filter(Institution.slug == slug).first() is not None:
        suffix = hashlib.sha256(sub.encode()).hexdigest()[:8]
        slug = f"{local}-{suffix}-personal"
    name = f"{first} {last}".strip() or local
    if db.query(Institution).filter(Institution.name == name).first() is not None:
        name = f"{name} ({hashlib.sha256(sub.encode()).hexdigest()[:8]})"
    institution = Institution(
        name=name,
        slug=slug,
        domain=None,
        subscription_tier="free",
        max_users=1,
        max_documents=10,
        max_questions_per_month=50,
    )
    db.add(institution)
    db.flush()
    return institution


def _primary_role(db: Session, institution: Institution, email: str) -> Role:
    is_personal = (institution.slug or "").endswith("-personal")
    is_first_user = (
        db.query(User).filter(User.institution_id == institution.id).count() == 1
    )
    wanted = (
        UserRole.ADMIN.value
        if (not is_personal and is_first_user)
        else UserRole.DOZENT.value
    )
    role = db.query(Role).filter(Role.name == wanted).first()
    if role is None and wanted == UserRole.ADMIN.value:
        # Silently downgrading would leave the institution without an admin.
        raise ProvisioningError("admin role is not seeded, run role seeding")
    if role is None:
        role = db.query(Role).filter(Role.name == UserRole.VIEWER.value).first()
    if role is None:
        raise ProvisioningError("no assignable role found, run role seeding")
    return role


def get_or_provision_user(db: Session, claims: Dict[str, Any]) -> tuple[User, bool]:
    """Resolve the user for verified OIDC claims, creating it if the ``sub`` is new.

    Returns ``(user, created)``. Commits when it creates a user.

    Raises:
        MissingClaimError: ``sub`` or ``email`` missing.
        EmailConflictError: unknown ``sub`` but the e-mail belongs to a user
            with another ``sub``.
        AccountNotMigratedError: unknown ``sub`` but the e-mail belongs to a
            user that has no ``sub`` yet (not migrated).
        UserLimitReachedError: the institution's user limit is reached.
        ProvisioningError: roles are not seeded.
    """
    sub = claims.get("sub")
    email = (claims.get("email") or "").strip().lower()
    if not sub:
        raise MissingClaimError("sub")

    user = db.query(User).filter(User.zitadel_sub == sub).first()
    if user is not None:
        return user, False

    if not email:
        raise MissingClaimError("email")
    existing = db.query(User).filter(func.lower(User.email) == email).first()
    if existing is not None:
        if not existing.zitadel_sub:
            raise AccountNotMigratedError(sub)
        raise EmailConflictError(sub)

    first, last = _names(claims, email)
    verified = claims.get("email_verified") is True
    institution = _resolve_institution(db, sub, email, first, last, verified)

    from utils.tenant_utils import SubscriptionLimits

    try:
        SubscriptionLimits.check_user_limit(institution, db)
    except HTTPException as exc:
        raise UserLimitReachedError(institution.slug) from exc

    user = User(
        email=email,
        zitadel_sub=sub,
        password_hash=None,
        first_name=first,
        last_name=last,
        institution_id=institution.id,
        status=UserStatus.ACTIVE.value,
        is_email_verified=verified,
        is_superuser=False,
        registration_method="zitadel",
        avatar_url=claims.get("picture"),
    )
    db.add(user)
    try:
        db.flush()
        user.roles.append(_primary_role(db, institution, email))
        db.commit()
    except ProvisioningError:
        db.rollback()
        raise
    except IntegrityError:
        # Two callbacks for the same new user at once (double click, second
        # tab): the loser hits the unique index on zitadel_sub or email.
        db.rollback()
        existing = db.query(User).filter(User.zitadel_sub == sub).first()
        if existing is not None:
            logger.info("JIT: paralleler Login, User existiert bereits (sub=%s).", sub)
            return existing, False
        raise EmailConflictError(sub)

    db.refresh(user)
    logger.info("JIT-provisioned user_id=%s sub=%s", user.id, sub)
    return user, True
