"""
Pydantic Schemas für Celery Task Status
Verwendet im WebSocket Task Progress Endpoint
"""

from enum import Enum
from typing import Any, Optional

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


class TaskStatusMessage(BaseModel):
    """WebSocket-Message Format für Task-Fortschritt"""

    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
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
