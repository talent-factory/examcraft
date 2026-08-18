"""Exam visibility filtering (TF-643 — Exam visibility model).

Governs exam browsing (``api.exams.list_exams``, ``api.exams.get_exam``) and,
via ``allow_read_all_bypass=False``, every exam-mutation endpoint reachable
through ``api.exams._get_exam_or_404`` (update/update-grading-scheme/delete/
archive/restore/add-questions/update-question/remove-question/reorder/
auto-fill/finalize/unfinalize/export) — see that function's docstring for
exactly which. Also wired into ``api.moodle_roundtrip.sync_moodle_question_ids``
and ``api.moodle_feedback_push.push_feedback`` (both mutations, gated the
same way). Deliberately NOT wired into the grading/reporting pipeline —
``api.submissions._load_exam_for_user``, ``api.stats``, ``api.grades`` and
``api.grade_export`` all stay institution-flat, unaffected by this module —
and NOT coupled to ``ExamStatus`` — visibility applies uniformly across
DRAFT/FINALIZED/EXPORTED (/grilling decisions, TF-643).

Every mutation call site additionally passes ``require_same_institution=True``
(see :func:`is_exam_visible_for`): the owner/creator branch alone doesn't
imply institution match (an owner's ``institution_id`` can drift away from
their exams', e.g. via an institution transfer that leaves exams behind), so
mutations need a stricter check than reads. Mirrors
``utils.auth_utils.enforce_resource_access``'s ``require_same_institution``
parameter, which Documents use for the same purpose via a separate
mutation-only gate.

Otherwise mirrors ``utils.question_visibility`` (TF-642), which itself
mirrors ``utils.document_visibility`` (TF-354/TF-620/TF-639/TF-640) — see
that module's docstring for the general shape (owner + visibility +
Institution-Admin read-all bypass). The owner column here is
``Exam.created_by`` (not ``user_id``).
"""

import logging
from typing import Optional, Set

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.exam import Exam, ExamVisibility
from services.org_unit_service import get_user_accessible_org_unit_ids
from utils.resource_visibility import has_read_all_bypass

logger = logging.getLogger(__name__)


def filter_exams_for_user(query: Query, user: User, db: Session) -> Query:
    """Restrict an ``Exam`` query to rows ``user`` may browse.

    SuperUser bypasses the filter. An ``exams:read_all`` holder
    (Institution-Admin bypass, TF-643) sees every exam within their own
    institution, regardless of visibility. Otherwise: creator rows OR
    institution-shared rows within the user's institution OR team-shared rows
    scoped to an Org-Unit the user has (hierarchical) access to.
    """
    if user.is_superuser:
        return query

    if user.institution_id is not None and has_read_all_bypass(user, "exams"):
        # OR'd with creatorship, not a bare institution_id filter: an exam
        # the user created but whose institution_id predates their current
        # institution (e.g. after an institution transfer that left exams
        # behind) must stay visible to its creator for READS — granting a
        # read permission must never remove visibility. Mutations get a
        # stricter check; see require_same_institution on
        # is_exam_visible_for/assert_exam_visible_for below.
        return query.filter(
            or_(
                Exam.institution_id == user.institution_id,
                Exam.created_by == user.id,
            )
        )

    conditions = [
        Exam.created_by == user.id,
        and_(
            Exam.visibility == ExamVisibility.INSTITUTION,
            Exam.institution_id == user.institution_id,
        ),
    ]

    if user.institution_id is not None:
        accessible_org_unit_ids = get_user_accessible_org_unit_ids(
            db, user.id, user.institution_id
        )
        if accessible_org_unit_ids:
            conditions.append(
                and_(
                    Exam.visibility == ExamVisibility.TEAM,
                    Exam.org_unit_id.in_(accessible_org_unit_ids),
                    # Org-Unit membership alone isn't sufficient — it only
                    # proves the user can see INTO that Org-Unit, not which
                    # institution the exam's institution_id currently claims
                    # (they can drift apart, e.g. after an owner transfer).
                    # Mirrors question_visibility.filter_questions_for_user's
                    # identical TEAM condition.
                    Exam.institution_id == user.institution_id,
                )
            )

    return query.filter(or_(*conditions))


def is_exam_visible_for(
    user: User,
    exam: Exam,
    db: Session,
    *,
    accessible_org_unit_ids: Optional[Set[int]] = None,
    allow_read_all_bypass: bool = True,
    require_same_institution: bool = False,
) -> bool:
    """True if ``user`` may see ``exam`` under the visibility rules.

    Low-level predicate kept for symmetry with
    ``document_visibility.is_document_visible_for`` /
    ``question_visibility.is_question_visible_for`` (single source of truth
    for the visibility rules) — wired into ``api.exams._get_exam_or_404`` via
    :func:`assert_exam_visible_for`.

    ``accessible_org_unit_ids``: optional pre-computed result of
    ``get_user_accessible_org_unit_ids``, see
    ``document_visibility.is_document_visible_for`` for why that matters when
    checking many exams in a loop.

    ``allow_read_all_bypass``: set False to evaluate visibility *without* the
    ``exams:read_all`` bypass — mirrors
    ``document_visibility.is_document_visible_for``'s / ``question_visibility
    .is_question_visible_for``'s same parameter (TF-640/TF-642): every
    exam-mutation call site passes ``False`` so the bypass stays strictly
    read-only (ADR-0004). SuperUser still bypasses regardless.

    ``require_same_institution``: set True to additionally require
    ``exam.institution_id == user.institution_id`` in the *creator* branch
    (the only branch that doesn't already imply institution match — the
    read-all-bypass, TEAM and INSTITUTION branches all check it inherently).
    Without this, a creator whose ``institution_id`` has drifted away from
    their exam's (e.g. an institution transfer that intentionally left exams
    behind) would keep full mutation rights on an exam that now belongs to a
    different institution. Reads leave this ``False`` by design — a creator
    must stay able to *see* their own exam across institution drift, mirrors
    ``document_visibility``'s identical read-side leniency; mutations pass
    ``True`` (wired automatically in ``api.exams._get_exam_or_404``, mirrors
    ``utils.auth_utils.enforce_resource_access``'s parameter of the same name,
    which Documents use for the equivalent mutation-only gate).
    """
    if user.is_superuser:
        return True
    if (
        allow_read_all_bypass
        and user.institution_id is not None
        and exam.institution_id == user.institution_id
        and has_read_all_bypass(user, "exams")
    ):
        return True
    if exam.created_by is not None and exam.created_by == user.id:
        if require_same_institution and exam.institution_id != user.institution_id:
            return False
        return True
    if (
        exam.visibility == ExamVisibility.INSTITUTION
        and exam.institution_id is not None
        and exam.institution_id == user.institution_id
    ):
        return True
    if (
        exam.visibility == ExamVisibility.TEAM
        and exam.org_unit_id is not None
        and user.institution_id is not None
        # Mirrors the filter_exams_for_user TEAM condition above — see its
        # comment for the concrete institution-transfer scenario this closes.
        and exam.institution_id == user.institution_id
    ):
        if accessible_org_unit_ids is None:
            accessible_org_unit_ids = get_user_accessible_org_unit_ids(
                db, user.id, user.institution_id
            )
        return exam.org_unit_id in accessible_org_unit_ids
    return False


def assert_exam_visible_for(
    user: User,
    exam: Exam,
    db: Session,
    *,
    detail: str = "Exam nicht gefunden",
    allow_read_all_bypass: bool = True,
    require_same_institution: bool = False,
) -> None:
    """Raise 404 if ``exam`` is not visible to ``user`` under the visibility
    rules.

    Deliberately 404 (not 403): a 403 would confirm that a private/off-team
    exam with this id exists, leaking its existence to a colleague who must
    not see it — mirrors ``document_visibility.assert_document_visible_for``
    / ``question_visibility.assert_question_visible_for``.

    ``require_same_institution``: forwarded to :func:`is_exam_visible_for` —
    see its docstring. Pass True for mutations.
    """
    if is_exam_visible_for(
        user,
        exam,
        db,
        allow_read_all_bypass=allow_read_all_bypass,
        require_same_institution=require_same_institution,
    ):
        return
    # Kept at info (not warning): a denial here is expected traffic — a
    # colleague browsing to an exam id they can't see, or (post-TF-643) a
    # mutation blocked by require_same_institution — not necessarily
    # malicious. Still worth a trace: the previous TenantFilter-based check
    # logged every denial, and losing that made cross-tenant probing and
    # "why can't I see this" support tickets equally invisible in the logs.
    logger.info(
        "Exam %s not visible to user %s (institution %s, "
        "require_same_institution=%s): denied by visibility rules",
        exam.id,
        user.id,
        user.institution_id,
        require_same_institution,
    )
    raise HTTPException(status_code=404, detail=detail)
