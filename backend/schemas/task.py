"""
Pydantic Schemas für Celery Task Status
Verwendet im WebSocket Task Progress Endpoint
"""

from enum import Enum
from typing import Any, Dict, Optional, Tuple

from pydantic import BaseModel, Field, model_validator


class TaskStatus(str, Enum):
    """
    Task-Status basierend auf Celery States.
    PROGRESS ist ein Custom-State via ProgressTask.update_progress().
    """

    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"

    @property
    def is_terminal(self) -> bool:
        return self in (TaskStatus.SUCCESS, TaskStatus.FAILURE, TaskStatus.REVOKED)


class ProgressCode(str, Enum):
    """Progress codes the frontend translates (TF-736).

    Keep in sync with ``KnownProgressCode`` in
    ``core/frontend/src/utils/generationTaskDisplay.ts``. The schema fields
    stay ``Optional[str]`` so a newer worker's unknown code can't turn
    ``/active-tasks`` into a 500 — the frontend falls back to ``message``.
    """

    GENERATION_STARTED = "generation_started"
    CONTEXT_LOADED = "context_loaded"  # params: total
    QUESTION_GENERATED = "question_generated"  # params: current, total
    TASK_STARTED = "task_started"
    TASK_RETRYING = "task_retrying"


def progress_code_fields(
    info: Any,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Read ``(code, params)`` from a Celery PROGRESS meta dict.

    Tolerates anything a worker may have written: a non-string code yields
    ``(None, None)``, non-dict params yield ``None``. Parameters never travel
    without their code.
    """
    if not isinstance(info, dict):
        return None, None
    code = info.get("code")
    if not isinstance(code, str) or not code:
        return None, None
    params = info.get("params")
    return code, params if isinstance(params, dict) else None


class TaskStatusMessage(BaseModel):
    """WebSocket-Message Format für Task-Fortschritt"""

    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    # TF-736: progress code plus interpolation values; the frontend renders
    # the text in the user's language and prefers it over `message`.
    message_code: Optional[str] = None
    message_params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> "TaskStatusMessage":
        if self.status == TaskStatus.SUCCESS:
            if self.progress != 100:
                raise ValueError("SUCCESS status must have progress=100")
            if self.error is not None:
                raise ValueError("SUCCESS status must not have error")
        if self.status in (TaskStatus.FAILURE, TaskStatus.REVOKED):
            if self.result is not None:
                raise ValueError("FAILURE/REVOKED must not have result")
        return self


class GenerateExamTaskResponse(BaseModel):
    """Response für den asynchronen Fragengenerierungs-Endpoint"""

    task_id: str
    message: str
