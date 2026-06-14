"""Subscription-Tier-Quotas für die Auswertungs-Pipeline (TF-336).

Spec 7.7. Vier Tiers, vier Dimensionen (Anzahl auswertbarer Prüfungen
pro Monat, Submissions pro Prüfung, erlaubte Driver, erlaubte Premium-
Features wie Klassen-Verlaufsstatistik).

Zentrale Funktionen sind defensiv:

* Bei unbekanntem Tier behandeln wir die Institution wie ``free`` —
  das ist das sichere Failure-Mode für eine fehlkonfigurierte DB-Row.
* HTTP 402 (Payment Required) wird konsistent verwendet, damit das
  Frontend den Tier-Banner korrekt anzeigen kann.
* Die Fehlermeldungen tragen einen ``error_code``-Feld in ``detail``,
  das das Frontend für das i18n-Lookup nutzt — der Plain-Text ist
  Fallback.

Counting-Semantik für ``exams_per_month``:

Wir zählen ``COUNT(DISTINCT import_jobs.exam_id)`` für die Institution
im laufenden Kalendermonat über alle nicht-fehlgeschlagenen Status. Das
ist die einzige Metrik, die der Pilot wirklich beobachten kann; wir
haben keine eigene Buchung für "Auswertung gestartet".
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from config.features import SubscriptionTier
from models.auth import Institution, User
from models.submission import ImportJob, Submission


logger = logging.getLogger(__name__)


def _is_production() -> bool:
    """Production means we must NOT silently downgrade misconfigured rows.

    Tests and local dev (where ``ENV`` is unset or ``test``/``development``)
    keep the soft-fallback so a single typo doesn't break the whole suite.
    """
    return (os.getenv("ENV") or "").strip().lower() == "production"


@dataclass(frozen=True)
class TierLimits:
    """Effektive Limits für einen Tier.

    ``-1`` = unbegrenzt (gleicher Code wie der bestehende RBAC).
    """

    tier: str
    label: str
    exams_per_month: int
    submissions_per_exam: int
    drivers: tuple[str, ...]
    llm_grading: bool
    class_history_stats: bool
    review_bulk: bool
    custom_grading_schemes: bool
    custom_llm_model: bool


# Keys are the canonical ``SubscriptionTier.value`` strings; the dict
# is built from the enum so a new tier added in ``config/features.py``
# fails the consistency check below until it gets quotas defined.
_TIER_LIMITS: dict[str, TierLimits] = {
    SubscriptionTier.FREE.value: TierLimits(
        tier=SubscriptionTier.FREE.value,
        label="Free",
        exams_per_month=3,
        submissions_per_exam=30,
        drivers=("moodle_json",),
        llm_grading=False,
        class_history_stats=False,
        review_bulk=False,
        custom_grading_schemes=False,
        custom_llm_model=False,
    ),
    SubscriptionTier.STARTER.value: TierLimits(
        tier=SubscriptionTier.STARTER.value,
        label="Starter",
        exams_per_month=-1,
        submissions_per_exam=50,
        drivers=("moodle_json",),
        llm_grading=True,
        class_history_stats=False,
        review_bulk=False,
        custom_grading_schemes=False,
        custom_llm_model=False,
    ),
    SubscriptionTier.PROFESSIONAL.value: TierLimits(
        tier=SubscriptionTier.PROFESSIONAL.value,
        label="Professional",
        exams_per_month=-1,
        submissions_per_exam=-1,
        drivers=("moodle_json", "moodle_api"),
        llm_grading=True,
        class_history_stats=False,
        review_bulk=True,
        custom_grading_schemes=False,
        custom_llm_model=False,
    ),
    SubscriptionTier.ENTERPRISE.value: TierLimits(
        tier=SubscriptionTier.ENTERPRISE.value,
        label="Enterprise",
        exams_per_month=-1,
        submissions_per_exam=-1,
        drivers=("moodle_json", "moodle_api"),
        llm_grading=True,
        class_history_stats=True,
        review_bulk=True,
        custom_grading_schemes=True,
        custom_llm_model=True,
    ),
}

# Module-load consistency check: every enum tier must have quotas
# defined. Catches the "added a tier in features.py, forgot to add
# quotas" drift at import time rather than the first 5xx in production.
_missing_quotas = {t.value for t in SubscriptionTier} - _TIER_LIMITS.keys()
if _missing_quotas:
    raise RuntimeError(
        f"SubscriptionTier(s) {sorted(_missing_quotas)} ohne quotas in "
        "_TIER_LIMITS — auswertung_quotas.py muss erweitert werden."
    )


# Status-Werte, bei denen ein ImportJob als "ausgeführt" zählt — d. h.
# auch ``partial`` zählt zur Auswertungs-Quote, weil der Lehrperson
# danach echte Daten zur Verfügung stehen. ``failed``/``running``
# zählen nicht.
_COUNTING_JOB_STATUSES: tuple[str, ...] = ("succeeded", "partial")


class UnknownTierError(RuntimeError):
    """Raised in production when an institution has an unknown tier value.

    Hiding the misconfiguration as a Free downgrade silently revokes
    contractually-paid features. Operators must see the failure.
    """


def get_tier_for_institution(institution: Institution | None) -> str:
    """Tier-String aus der Institution lesen.

    In **production** an unknown tier raises ``UnknownTierError`` so the
    misconfiguration becomes a visible 5xx instead of a silent feature
    downgrade. In dev/test we fall back to ``free`` and log a warning so
    ad-hoc fixtures with mistyped tiers don't break the whole suite.

    A ``None`` institution always falls back to ``free`` — that is the
    expected state for users without an institution (e.g. before
    onboarding).
    """
    if institution is None:
        return "free"
    raw = (institution.subscription_tier or "free").strip().lower()
    if raw not in _TIER_LIMITS:
        logger.warning(
            "Institution %s hat unbekannten Tier %r — Fallback auf 'free'",
            institution.id,
            raw,
        )
        if _is_production():
            raise UnknownTierError(
                f"Institution {institution.id} hat unbekannten Tier {raw!r}. "
                "Tier-Wert in der DB korrigieren oder neuen Tier in "
                "_TIER_LIMITS registrieren."
            )
        return "free"
    return raw


def get_limits(tier: str) -> TierLimits:
    """Limits für einen Tier-String. Unbekannt → ``free``."""
    return _TIER_LIMITS.get(tier.lower(), _TIER_LIMITS["free"])


def get_limits_for_user(user: User) -> TierLimits:
    return get_limits(get_tier_for_institution(user.institution))


# ---------------------------------------------------------------------------
# Quota-Checks (raise HTTPException 402)
# ---------------------------------------------------------------------------


def _http_402(error_code: str, message: str, **details) -> HTTPException:
    """402 Payment Required mit i18n-freundlichem ``error_code``."""
    return HTTPException(
        status_code=402,
        detail={
            "error_code": error_code,
            "message": message,
            **details,
        },
    )


def assert_driver_allowed(*, user: User, driver_name: str) -> None:
    """Free/Starter dürfen nur den CSV-Driver nutzen.

    Wir prüfen vor der teuren Pipeline, damit das Limit nicht durch
    bereits verbrannte Web-Service-Calls verraten wird.
    """
    limits = get_limits_for_user(user)
    if driver_name not in limits.drivers:
        raise _http_402(
            error_code="auswertung_driver_not_in_tier",
            message=(
                f"Der Driver '{driver_name}' ist im Tier "
                f"'{limits.label}' nicht freigeschaltet. "
                "Upgrade auf Professional oder höher."
            ),
            tier=limits.tier,
            driver=driver_name,
            allowed_drivers=list(limits.drivers),
            upgrade_to="professional",
        )


def assert_class_history_allowed(user: User) -> None:
    """Klassen- und Studi-Verlaufsstatistik ist Enterprise-only."""
    limits = get_limits_for_user(user)
    if not limits.class_history_stats:
        raise _http_402(
            error_code="auswertung_class_history_enterprise_only",
            message=(
                "Klassen- und Studi-Verlauf ist im Tier "
                f"'{limits.label}' nicht enthalten. "
                "Upgrade auf Enterprise."
            ),
            tier=limits.tier,
            upgrade_to="enterprise",
        )


def assert_review_bulk_allowed(user: User) -> None:
    """Bulk-Aktionen in der Review-Queue sind Pro+."""
    limits = get_limits_for_user(user)
    if not limits.review_bulk:
        raise _http_402(
            error_code="auswertung_review_bulk_pro_only",
            message=(
                "Bulk-Aktionen in der Review-Queue sind im Tier "
                f"'{limits.label}' nicht freigeschaltet. "
                "Upgrade auf Professional oder höher."
            ),
            tier=limits.tier,
            upgrade_to="professional",
        )


def assert_custom_grading_schemes_allowed(user: User) -> None:
    """Custom Grading-Schemes sind Enterprise-only."""
    limits = get_limits_for_user(user)
    if not limits.custom_grading_schemes:
        raise _http_402(
            error_code="auswertung_custom_grading_schemes_enterprise_only",
            message=(
                "Eigene Notenmodelle sind im Tier "
                f"'{limits.label}' nicht enthalten. "
                "Upgrade auf Enterprise."
            ),
            tier=limits.tier,
            upgrade_to="enterprise",
        )


# ---------------------------------------------------------------------------
# Counting helpers (DB)
# ---------------------------------------------------------------------------


def _start_of_month_utc() -> datetime:
    """Erster Tag des laufenden Kalendermonats (UTC, 00:00:00).

    Wir benutzen UTC bewusst — TZ-Drift zwischen Worker und API würde
    sonst dazu führen, dass ein Import an einem 1. Tag-Wechsel doppelt
    in zwei Monaten zählt.
    """
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def count_evaluated_exams_this_month(db: Session, *, institution_id: int) -> int:
    """Distinct exam_ids im laufenden Monat (succeeded/partial)."""
    return int(
        db.query(sa_func.count(sa_func.distinct(ImportJob.exam_id)))
        .filter(
            ImportJob.institution_id == institution_id,
            ImportJob.status.in_(_COUNTING_JOB_STATUSES),
            ImportJob.created_at >= _start_of_month_utc(),
        )
        .scalar()
        or 0
    )


def count_submissions_for_exam(db: Session, *, exam_id: int) -> int:
    return int(
        db.query(sa_func.count(Submission.id))
        .filter(Submission.exam_id == exam_id)
        .scalar()
        or 0
    )


def assert_exam_quota_for_import(*, db: Session, user: User, exam_id: int) -> None:
    """Prüft die ``exams_per_month``-Quota.

    Free hat 3 Prüfungen/Monat (distinct exam_ids mit erfolgreichem
    Import). Wenn das aktuelle Exam *bereits* in diesem Monat
    importiert wurde (z. B. erneuter Import zur Nachkorrektur), zählt
    es nicht zusätzlich. Sonst muss
    ``count + 1 <= exams_per_month``.
    """
    limits = get_limits_for_user(user)
    if limits.exams_per_month == -1:
        return
    institution_id = user.institution_id
    if institution_id is None:
        # No institution → no tenant boundary for the quota. Refusing the
        # request is the safe default; the previous fail-open lets a
        # misconfigured user bypass the cap entirely.
        raise HTTPException(
            status_code=403,
            detail="Benutzer ohne Institution darf keinen Import auslösen.",
        )

    current_count = count_evaluated_exams_this_month(db, institution_id=institution_id)
    # Wenn der aktuelle Exam-ID schon in diesem Monat einen Job hat,
    # liegt er bereits in current_count drin — Re-Imports sollen nicht
    # nochmal zählen.
    already_in_month = (
        db.query(ImportJob.id)
        .filter(
            ImportJob.institution_id == institution_id,
            ImportJob.exam_id == exam_id,
            ImportJob.status.in_(_COUNTING_JOB_STATUSES),
            ImportJob.created_at >= _start_of_month_utc(),
        )
        .first()
        is not None
    )
    if already_in_month:
        return  # Re-Import des gleichen Exams ist frei.
    if current_count >= limits.exams_per_month:
        raise _http_402(
            error_code="auswertung_exam_monthly_quota_exceeded",
            message=(
                f"Tier '{limits.label}' erlaubt {limits.exams_per_month} "
                "Auswertungen pro Monat. "
                "Upgrade auf Starter oder höher."
            ),
            tier=limits.tier,
            quota="exams_per_month",
            limit=limits.exams_per_month,
            used=current_count,
            upgrade_to="starter",
        )


def assert_submission_quota_for_exam(
    *, db: Session, user: User, exam_id: int, additional: int = 1
) -> None:
    """Prüft, dass die Anzahl Submissions für die Prüfung das Tier-
    Limit nicht überschreitet.

    ``additional`` ist ein optionaler Hint für Bulk-Imports, der die
    Vorab-Prüfung präziser macht (z. B. CSV mit 60 Zeilen vs.
    Limit 50). Für die einfachen Aufrufer ist 1 ein konservativer
    Default.
    """
    limits = get_limits_for_user(user)
    if limits.submissions_per_exam == -1:
        return
    current = count_submissions_for_exam(db, exam_id=exam_id)
    if current + additional > limits.submissions_per_exam:
        raise _http_402(
            error_code="auswertung_submission_quota_exceeded",
            message=(
                f"Tier '{limits.label}' erlaubt {limits.submissions_per_exam} "
                "Submissions pro Prüfung. "
                "Upgrade auf Professional oder höher."
            ),
            tier=limits.tier,
            quota="submissions_per_exam",
            limit=limits.submissions_per_exam,
            used=current,
            additional=additional,
            upgrade_to="professional",
        )


def list_known_tiers() -> Iterable[str]:
    """Public read-only view of the registered tiers (for admin UI/tests)."""
    return tuple(_TIER_LIMITS.keys())
