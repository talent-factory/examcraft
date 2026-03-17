"""
Pydantic Schemas für Celery Task Status
Verwendet im WebSocket Task Progress Endpoint
"""

from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    REVOKED = "REVOKED"
    RETRY = "RETRY"


class TaskStatusMessage(BaseModel):
    """WebSocket-Message Format für Task-Fortschritt"""

    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100)
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
