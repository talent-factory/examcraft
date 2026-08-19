"""CompetencyFramework visibility filtering (TF-644 — Competency-Framework
visibility model).

Governs framework browsing (``api.competency_frameworks.list_frameworks``,
``get_framework``) and, via ``allow_read_all_bypass=False``, every framework
mutation reachable through ``api.competency_frameworks._get_for_write``
(update/archive/unarchive). Per /grilling decision (TF-644) also wired into
``api.rag_exams.resolve_competencies_text`` — the generation-time framework
lookup, which previously ignored visibility entirely (any framework in the
institution, private or not, was selectable via a client-supplied
``framework_id``); this closes that pre-existing gap as part of the same
ticket, mirroring how TF-643 closed the analogous Moodle-endpoint gap.
``resolve_competencies_text`` calls ``is_framework_visible_for`` with the
default ``allow_read_all_bypass=True`` (unlike ``_get_for_write``'s explicit
``False``) — deliberate, not an oversight: generation is a read action, so a
``competencies:read_all`` admin may select a colleague's private/team
framework for exam generation, same as they may browse it via
``list_frameworks``/``get_framework``.

Two distinct "not gated" decisions, not to be conflated: (1) at WRITE time,
``api.rag_exams.resolve_framework_for_user`` (built on
``is_framework_visible_for`` from this module) DOES gate which
``framework_id`` may reach ``tasks.question_tasks._persist_questions``'
competency-code tagging — PR #194 review follow-up, previously the raw,
unchecked client-supplied id reached that unfiltered ``Competency`` lookup
even though ``resolve_competencies_text`` already withheld the *text*. (2) at
READ time, once a ``QuestionReview.competency_id`` is legitimately set, its
``competency``/``code``/``title``/``module_code`` metadata (see
``api.question_review._serialize_competency``) is deliberately NOT re-gated
against the framework's visibility on display: that FK is read-only metadata
on a resource the viewer already has legitimate access to, not a "browse the
framework" action — mirrors how TF-643 treats a question already embedded in
a wider-visibility exam (/grilling decision, TF-644).

Otherwise mirrors ``utils.exam_visibility`` (TF-643), which itself mirrors
``utils.question_visibility`` (TF-642) and ``utils.document_visibility``
(TF-354/TF-620/TF-639/TF-640) — see that module's docstring for the general
shape (owner + visibility + Institution-Admin read-all bypass). The owner
column here is ``CompetencyFramework.created_by`` (like ``Exam``, not
``user_id``).
"""

import logging
from typing import Optional, Set

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.competency import CompetencyFramework, CompetencyFrameworkVisibility
from services.org_unit_service import get_user_accessible_org_unit_ids
from utils.resource_visibility import has_read_all_bypass

logger = logging.getLogger(__name__)


def filter_frameworks_for_user(query: Query, user: User, db: Session) -> Query:
    """Restrict a ``CompetencyFramework`` query to rows ``user`` may browse.

    SuperUser bypasses the filter. A ``competencies:read_all`` holder
    (Institution-Admin bypass, TF-639) sees every framework within their own
    institution, regardless of visibility. Otherwise: creator rows OR
    institution-shared rows within the user's institution OR team-shared rows
    scoped to an Org-Unit the user has (hierarchical) access to.
    """
    if user.is_superuser:
        return query

    if user.institution_id is not None and has_read_all_bypass(user, "competencies"):
        # OR'd with creatorship, not a bare institution_id filter: a
        # framework the user created but whose institution_id predates their
        # current institution (e.g. after an institution transfer that left
        # frameworks behind) must stay visible to its creator for READS —
        # granting a read permission must never remove visibility. Mutations
        # get a stricter check; see require_same_institution on
        # is_framework_visible_for/assert_framework_visible_for below.
        return query.filter(
            or_(
                CompetencyFramework.institution_id == user.institution_id,
                CompetencyFramework.created_by == user.id,
            )
        )

    conditions = [
        CompetencyFramework.created_by == user.id,
        and_(
            CompetencyFramework.visibility == CompetencyFrameworkVisibility.INSTITUTION,
            CompetencyFramework.institution_id == user.institution_id,
        ),
    ]

    if user.institution_id is not None:
        accessible_org_unit_ids = get_user_accessible_org_unit_ids(
            db, user.id, user.institution_id
        )
        if accessible_org_unit_ids:
            conditions.append(
                and_(
                    CompetencyFramework.visibility
                    == CompetencyFrameworkVisibility.TEAM,
                    CompetencyFramework.org_unit_id.in_(accessible_org_unit_ids),
                    # Org-Unit membership alone isn't sufficient — it only
                    # proves the user can see INTO that Org-Unit, not which
                    # institution the framework's institution_id currently
                    # claims (they can drift apart, e.g. after an owner
                    # transfer). Mirrors exam_visibility's identical TEAM
                    # condition.
                    CompetencyFramework.institution_id == user.institution_id,
                )
            )

    return query.filter(or_(*conditions))


def is_framework_visible_for(
    user: User,
    framework: CompetencyFramework,
    db: Session,
    *,
    accessible_org_unit_ids: Optional[Set[int]] = None,
    allow_read_all_bypass: bool = True,
    require_same_institution: bool = False,
) -> bool:
    """True if ``user`` may see ``framework`` under the visibility rules.

    Low-level predicate kept for symmetry with
    ``exam_visibility.is_exam_visible_for`` / ``document_visibility
    .is_document_visible_for`` (single source of truth for the visibility
    rules) — wired into ``api.competency_frameworks._get_for_write`` via
    :func:`assert_framework_visible_for`, and into
    ``api.rag_exams.resolve_competencies_text`` directly.

    ``accessible_org_unit_ids``: optional pre-computed result of
    ``get_user_accessible_org_unit_ids``, see
    ``document_visibility.is_document_visible_for`` for why that matters when
    checking many frameworks in a loop.

    ``allow_read_all_bypass``: set False to evaluate visibility *without* the
    ``competencies:read_all`` bypass — mirrors ``exam_visibility
    .is_exam_visible_for``'s same parameter (TF-640/TF-642/TF-643): every
    framework-mutation call site passes ``False`` so the bypass stays
    strictly read-only (ADR-0004). SuperUser still bypasses regardless.

    ``require_same_institution``: set True to additionally require
    ``framework.institution_id == user.institution_id`` in the *creator*
    branch (the only branch that doesn't already imply institution match —
    the read-all-bypass, TEAM and INSTITUTION branches all check it
    inherently). Without this, a creator whose ``institution_id`` has
    drifted away from their framework's (e.g. an institution transfer that
    intentionally left frameworks behind) would keep full mutation rights on
    a framework that now belongs to a different institution. Reads leave
    this ``False`` by design — a creator must stay able to *see* their own
    framework across institution drift, mirrors ``exam_visibility``'s
    identical read-side leniency; mutations pass ``True`` (wired in
    ``api.competency_frameworks._get_for_write``).
    """
    if user.is_superuser:
        return True
    if (
        allow_read_all_bypass
        and user.institution_id is not None
        and framework.institution_id == user.institution_id
        and has_read_all_bypass(user, "competencies")
    ):
        return True
    if framework.created_by is not None and framework.created_by == user.id:
        if require_same_institution and framework.institution_id != user.institution_id:
            return False
        return True
    if (
        framework.visibility == CompetencyFrameworkVisibility.INSTITUTION
        and framework.institution_id is not None
        and framework.institution_id == user.institution_id
    ):
        return True
    if (
        framework.visibility == CompetencyFrameworkVisibility.TEAM
        and framework.org_unit_id is not None
        and user.institution_id is not None
        # Mirrors the filter_frameworks_for_user TEAM condition above — see
        # its comment for the concrete institution-transfer scenario this
        # closes.
        and framework.institution_id == user.institution_id
    ):
        if accessible_org_unit_ids is None:
            accessible_org_unit_ids = get_user_accessible_org_unit_ids(
                db, user.id, user.institution_id
            )
        return framework.org_unit_id in accessible_org_unit_ids
    return False


def assert_framework_visible_for(
    user: User,
    framework: CompetencyFramework,
    db: Session,
    *,
    detail: str = "Kompetenzrahmen nicht gefunden.",
    allow_read_all_bypass: bool = True,
    require_same_institution: bool = False,
) -> None:
    """Raise 404 if ``framework`` is not visible to ``user`` under the
    visibility rules.

    Deliberately 404 (not 403): a 403 would confirm that a private/off-team
    framework with this id exists, leaking its existence to a colleague who
    must not see it — mirrors ``exam_visibility.assert_exam_visible_for`` /
    ``document_visibility.assert_document_visible_for``.

    ``require_same_institution``: forwarded to :func:`is_framework_visible_for`
    — see its docstring. Pass True for mutations.
    """
    if is_framework_visible_for(
        user,
        framework,
        db,
        allow_read_all_bypass=allow_read_all_bypass,
        require_same_institution=require_same_institution,
    ):
        return
    # Kept at info (not warning): a denial here is expected traffic — a
    # colleague browsing to a framework id they can't see, or a mutation
    # blocked by require_same_institution — not necessarily malicious. Still
    # worth a trace, mirrors exam_visibility.assert_exam_visible_for.
    logger.info(
        "CompetencyFramework %s not visible to user %s (institution %s, "
        "require_same_institution=%s): denied by visibility rules",
        framework.id,
        user.id,
        user.institution_id,
        require_same_institution,
    )
    raise HTTPException(status_code=404, detail=detail)
