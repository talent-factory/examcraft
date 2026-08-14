"""Question visibility filtering (TF-642 — QuestionReview visibility model).

Governs *only* the exam-composition reuse pool ("Fragenpool",
``api.exams.list_approved_questions``) — deliberately NOT the Review-Queue
(``api.question_review.get_review_queue``) nor any review-workflow mutation
(edit/approve/reject/archive/delete, all reachable via
``api.question_review._get_scoped_question``). Those stay exactly as before
this field existed: permission + institution scoped only, via
``utils.tenant_utils.TenantFilter``. A reviewer holding
``review_questions``/``edit_questions``/etc. still sees and acts on every
institution question regardless of its visibility — reviewing isn't
"browsing" a colleague's private draft, it's processing a shared work queue
(/grilling decision, TF-642).

``api.exams.get_approved_question`` (the single-question detail view behind
the reuse pool) is likewise deliberately left tenant-scoped only, NOT routed
through this module — its own docstring already establishes that principle
for a different axis (``review_status``/``archived_at``): a question already
added to an exam must stay previewable to any institution colleague viewing
that exam, even after it's since been edited or archived. Extending that same
"once referenced elsewhere, stay visible" reasoning to the new visibility
axis avoids breaking exam-preview for a private/team question a colleague
already added to a shared exam — the question→exam visibility interaction is
explicitly deferred to TF-643 (Exam visibility ticket), not decided here.

Otherwise mirrors ``utils.document_visibility`` (TF-354/TF-620/TF-639/TF-640)
— see that module's docstring for the general shape (owner + visibility +
Institution-Admin read-all bypass). The owner column here is
``QuestionReview.created_by`` (not ``user_id``).
"""

from typing import Optional, Set

from fastapi import HTTPException
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from models.auth import User
from models.question_review import QuestionReview, QuestionReviewVisibility
from services.org_unit_service import get_user_accessible_org_unit_ids
from utils.resource_visibility import has_read_all_bypass


def filter_questions_for_user(query: Query, user: User, db: Session) -> Query:
    """Restrict a ``QuestionReview`` query (the Fragenpool reuse list) to
    rows ``user`` may reuse.

    SuperUser bypasses the filter. A ``questions:read_all`` holder
    (Institution-Admin bypass, TF-642) sees every question within their own
    institution, regardless of visibility. Otherwise: creator rows OR
    institution-shared rows within the user's institution OR team-shared rows
    scoped to an Org-Unit the user has (hierarchical) access to.
    """
    if user.is_superuser:
        return query

    if user.institution_id is not None and has_read_all_bypass(user, "questions"):
        # OR'd with creatorship, not a bare institution_id filter: a question
        # the user created but whose institution_id is NULL or predates their
        # current institution must stay visible to its creator — granting a
        # read permission must never remove visibility.
        return query.filter(
            or_(
                QuestionReview.institution_id == user.institution_id,
                QuestionReview.created_by == user.id,
            )
        )

    conditions = [
        QuestionReview.created_by == user.id,
        and_(
            QuestionReview.visibility == QuestionReviewVisibility.INSTITUTION,
            QuestionReview.institution_id == user.institution_id,
        ),
    ]

    if user.institution_id is not None:
        accessible_org_unit_ids = get_user_accessible_org_unit_ids(
            db, user.id, user.institution_id
        )
        if accessible_org_unit_ids:
            conditions.append(
                and_(
                    QuestionReview.visibility == QuestionReviewVisibility.TEAM,
                    QuestionReview.org_unit_id.in_(accessible_org_unit_ids),
                    # Bugfix: an Org-Unit membership only proves the user can
                    # see INTO that Org-Unit — it says nothing about which
                    # institution a given question's institution_id field
                    # currently claims. Without this, a question whose
                    # org_unit_id and institution_id have drifted apart (e.g.
                    # its owner was later transferred to a different
                    # institution without org_unit_id being cleared) would
                    # leak to institution-A colleagues even though the row
                    # now belongs to institution B. org_unit_id membership is
                    # necessary but not sufficient; institution match is too.
                    QuestionReview.institution_id == user.institution_id,
                )
            )

    return query.filter(or_(*conditions))


def is_question_visible_for(
    user: User,
    question: QuestionReview,
    db: Session,
    *,
    accessible_org_unit_ids: Optional[Set[int]] = None,
    allow_read_all_bypass: bool = True,
) -> bool:
    """True if ``user`` may reuse ``question`` under the visibility rules.

    Low-level predicate kept for symmetry with
    ``document_visibility.is_document_visible_for`` (single source of truth
    for the visibility rules) — wired into ``api.exams.add_questions`` (via
    :func:`assert_question_visible_for`) so a caller cannot add a question
    they cannot otherwise see to an exam by guessing its numeric id.
    ``get_approved_question`` (single-question preview) deliberately stays
    unwired/tenant-only (see module docstring).
    ``accessible_org_unit_ids``: optional pre-computed result of
    ``get_user_accessible_org_unit_ids``, see
    ``document_visibility.is_document_visible_for`` for why that matters when
    checking many questions in a loop.
    ``allow_read_all_bypass``: set False to evaluate visibility *without* the
    ``questions:read_all`` bypass — mirrors
    ``document_visibility.is_document_visible_for``'s same parameter (TF-640):
    for a future caller that gates a state-changing action on this, the
    bypass is meant to stay strictly read-only (ADR-0004). SuperUser still
    bypasses regardless.
    """
    if user.is_superuser:
        return True
    if (
        allow_read_all_bypass
        and user.institution_id is not None
        and question.institution_id == user.institution_id
        and has_read_all_bypass(user, "questions")
    ):
        return True
    if question.created_by is not None and question.created_by == user.id:
        return True
    if (
        question.visibility == QuestionReviewVisibility.INSTITUTION
        and question.institution_id is not None
        and question.institution_id == user.institution_id
    ):
        return True
    if (
        question.visibility == QuestionReviewVisibility.TEAM
        and question.org_unit_id is not None
        and user.institution_id is not None
        # Bugfix: mirrors the filter_questions_for_user TEAM condition above
        # — Org-Unit membership alone isn't sufficient, the question's
        # institution_id must also still match the viewer's (see comment
        # there for the concrete institution-transfer scenario this closes).
        and question.institution_id == user.institution_id
    ):
        if accessible_org_unit_ids is None:
            accessible_org_unit_ids = get_user_accessible_org_unit_ids(
                db, user.id, user.institution_id
            )
        return question.org_unit_id in accessible_org_unit_ids
    return False


def assert_question_visible_for(
    user: User,
    question: QuestionReview,
    db: Session,
    *,
    detail: str = "Question nicht gefunden",
    allow_read_all_bypass: bool = True,
) -> None:
    """Raise 404 if ``question`` is not visible to ``user`` under the
    Fragenpool visibility rules.

    Deliberately 404 (not 403): a 403 would confirm that a private/off-team
    question with this id exists, leaking its existence to a colleague who
    must not see it — mirrors
    ``document_visibility.assert_document_visible_for`` (TF-640).
    """
    if is_question_visible_for(
        user, question, db, allow_read_all_bypass=allow_read_all_bypass
    ):
        return
    raise HTTPException(status_code=404, detail=detail)
