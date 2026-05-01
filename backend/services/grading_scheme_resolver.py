"""Single source of truth for resolving the active grading scheme.

Both ``api.grade_export`` and ``services.statistics_service`` need to
answer "what scheme applies to this exam?" with the same fall-through
order (exam → institution-default → None). Keeping two copies in sync
silently rotted in TF-335 (the statistics version had a different
return-type annotation), so this module is the canonical
implementation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.auth import Institution
from models.exam import Exam
from models.grading_scheme import GradingScheme


def resolve_scheme_config(db: Session, exam: Exam) -> dict[str, Any] | None:
    """Resolve the scheme-config dict for an exam.

    Lookup order:
      1. ``exam.grading_scheme_id`` — explicit per-exam scheme
      2. ``institution.default_grading_scheme_id`` — institution default
      3. ``None`` — caller renders a "—" placeholder; never crashes.
    """
    scheme_id = exam.grading_scheme_id
    if scheme_id is None:
        institution = (
            db.query(Institution)
            .filter(Institution.id == exam.institution_id)
            .one_or_none()
        )
        scheme_id = institution.default_grading_scheme_id if institution else None
    if scheme_id is None:
        return None
    scheme = db.query(GradingScheme).filter(GradingScheme.id == scheme_id).one_or_none()
    return scheme.config if scheme is not None else None
