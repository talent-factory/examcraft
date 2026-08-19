"""Schemas for active generation task recovery."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator

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


class TaskResultResponse(BaseModel):
    """Ergebnis eines bereits abgeschlossenen Generierungs-Tasks (TF-608).

    Wird beim Recovery nach einem Reload gelesen: der WebSocket liefert das
    Ergebnis nur, solange er verbunden ist — ein während des Reloads fertig
    gewordener Task braucht diesen Pull-Weg zurück in die UI.

    ``result`` bleibt ``None``, solange kein SUCCESS-Ergebnis vorliegt — etwa
    weil das Celery-Result-Backend den Eintrag bereits verworfen hat
    (``result_expires``), der Broker beim Abruf nicht erreichbar war, oder der
    Task fehlgeschlagen ist (dann steht die Ursache stattdessen in ``error``).
    Der Task bleibt in jedem dieser Fälle sichtbar, nur ohne Detailansicht —
    die Fragen selbst liegen bei einem erfolgreichen Task ohnehin bereits in
    der Prüf-Queue.
    """

    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def validate_status_fields(self) -> "TaskResultResponse":
        """Hält dieselbe Status/Result/Error-Korrelation ein wie die
        WebSocket-Schwester-Type ``schemas.task.TaskStatusMessage`` — SUCCESS
        darf keinen ``error`` tragen, FAILURE/REVOKED kein ``result``. Ohne
        diese Invariante wäre z. B. ein `TaskResultResponse(status=SUCCESS,
        result=None, error="boom")` konstruierbar, was die Recovery-UI
        (`GenerationTasksContext.tsx`) in einen widersprüchlichen Zustand
        bringen könnte."""
        if self.status == TaskStatus.SUCCESS and self.error is not None:
            raise ValueError("SUCCESS status must not have error")
        if (
            self.status in (TaskStatus.FAILURE, TaskStatus.REVOKED)
            and self.result is not None
        ):
            raise ValueError("FAILURE/REVOKED must not have result")
        return self
