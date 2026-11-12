"""In-memory adapter for the Celery-state seam of ``services.generation_job_state``.

Lets tests put a task into any Celery state (including the ones Celery reports
for a job that is already SUCCESS in the DB) without a Redis result backend.
"""

from typing import Any, Callable, Optional

from services.generation_job_state import (
    CeleryKnown,
    CeleryReading,
    CeleryUnknown,
    JobState,
)


class InMemoryCelery:
    """Fake ``CeleryStatePort``.

    - ``set`` puts a task into a state (with its ``info``: progress dict, result
      or exception); unknown tasks read as ``PENDING`` (what
      Celery reports for a task it has never seen or whose entry expired).
    - ``break_backend`` makes every read return ``CeleryUnknown``.
    - ``before_read`` runs at the start of every read: a test uses it to
      simulate that the task committed SUCCESS between the caller loading the
      job row and reading Celery's state.
    - ``failed`` records ``mark_failed`` calls.
    """

    def __init__(self) -> None:
        self._states: dict[str, tuple[str, Any]] = {}
        self._broken: Optional[Exception] = None
        self.before_read: Optional[Callable[[str], None]] = None
        self.failed: list[tuple[str, BaseException]] = []

    def set(self, task_id: str, state: str, info: Any = None) -> None:
        self._states[task_id] = (state, info)

    def break_backend(self, cause: Optional[Exception] = None) -> None:
        self._broken = cause or ConnectionError("redis down")

    def read(self, task_id: str) -> CeleryReading:
        if self.before_read is not None:
            self.before_read(task_id)
        if self._broken is not None:
            return CeleryUnknown(cause=self._broken)
        state, info = self._states.get(task_id, ("PENDING", None))
        return CeleryKnown(state=state, info=info)

    def mark_failed(self, task_id: str, exc: BaseException) -> None:
        self.failed.append((task_id, exc))
        self._states[task_id] = ("FAILURE", exc)


def job_state(celery_status: str = "PENDING", **overrides) -> JobState:
    """A ``JobState`` for tests of callers that patch ``read_state``."""
    fields = dict(
        task_id="task",
        status=celery_status,
        db_status=None,
        celery=CeleryKnown(state=celery_status),
        celery_status=celery_status,
        progress=None,
        result=None,
        error=None,
        db_overrode_celery=False,
        phantom=False,
    )
    return JobState(**{**fields, **overrides})
