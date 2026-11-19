"""Request-scoped impersonation context (TF-741, part of the TF-739 epic).

``get_current_user`` (``utils/auth_utils.py``) populates this from the
``impersonator_id``/``impersonation_session_id`` columns of the
impersonation ``AuthSession``. Downstream code — the
account-security guard in this ticket, and the audit-log wiring in
TF-742 — reads it instead of needing the claims threaded through every
function signature.

``ImpersonationContextMiddleware`` (``middleware/impersonation_context.py``)
resets the value to ``None`` around every request so nothing can leak
across requests regardless of how the ASGI server schedules tasks.
"""

from contextvars import ContextVar
from typing import NamedTuple, Optional


class ImpersonationContext(NamedTuple):
    """Who is really behind the wheel of the current request."""

    impersonator_id: int
    impersonation_session_id: int
    auth_session_id: int


_impersonation_context: ContextVar[Optional[ImpersonationContext]] = ContextVar(
    "impersonation_context", default=None
)


def get_impersonation_context() -> Optional[ImpersonationContext]:
    """Return the impersonation context for the current request, if any."""
    return _impersonation_context.get()


def set_impersonation_context(value: Optional[ImpersonationContext]) -> None:
    """Set (or clear, with ``None``) the impersonation context."""
    _impersonation_context.set(value)
