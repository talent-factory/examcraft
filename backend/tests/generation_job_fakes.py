"""In-memory adapter for the Celery-state seam of ``services.generation_job_state``.

Lets tests put a task into any Celery state (including the ones Celery reports
for a job that is already SUCCESS in the DB) without a Redis result backend.
"""

from typing import Callable, Optional

from services.generation_job_state import CeleryKnown, CeleryReading, CeleryUnknown


class InMemoryCelery:
    """Fake ``CeleryStatePort``.

    - ``set`` puts a task into a state; unknown tasks read as ``PENDING`` (what
      Celery reports for a task it has never seen or whose entry expired).
    - ``break_backend`` makes every read return ``CeleryUnknown``.
    - ``before_read`` runs at the start of every read: a test uses it to
      simulate that the task committed SUCCESS between the caller loading the
      job row and reading Celery's state.
    - ``failed`` records ``mark_failed`` calls.
    """

    def __init__(self) -> None:
        self._states: dict[str, str] = {}
        self._broken: Optional[Exception] = None
        self.before_read: Optional[Callable[[str], None]] = None
        self.failed: list[tuple[str, BaseException]] = []

    def set(self, task_id: str, state: str) -> None:
        self._states[task_id] = state

    def break_backend(self, cause: Optional[Exception] = None) -> None:
        self._broken = cause or ConnectionError("redis down")

    def read(self, task_id: str) -> CeleryReading:
        if self.before_read is not None:
            self.before_read(task_id)
        if self._broken is not None:
            return CeleryUnknown(cause=self._broken)
        return CeleryKnown(state=self._states.get(task_id, "PENDING"))

    def mark_failed(self, task_id: str, exc: BaseException) -> None:
        self.failed.append((task_id, exc))
        self._states[task_id] = "FAILURE"
