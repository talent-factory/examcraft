"""Schemas for active generation task recovery."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from schemas.task import TaskStatus


class ActiveTaskInfo(BaseModel):
    task_id: str
    status: TaskStatus
    progress: int = Field(ge=0, le=100, default=0)
    message: Optional[str] = None
    created_at: datetime
    topic: Optional[str] = None
    question_count: Optional[int] = None


class ActiveTasksResponse(BaseModel):
    tasks: List[ActiveTaskInfo]
