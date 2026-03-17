"""Tests für Task Status Schemas"""

import pytest
from pydantic import ValidationError


def test_task_status_message_valid():
    """TaskStatusMessage akzeptiert gültige Progress-Daten"""
    from schemas.task import TaskStatusMessage, TaskStatus

    msg = TaskStatusMessage(
        task_id="abc-123",
        status=TaskStatus.PROGRESS,
        progress=40,
        message="Docling-Verarbeitung läuft...",
    )
    assert msg.task_id == "abc-123"
    assert msg.progress == 40
    assert msg.message == "Docling-Verarbeitung läuft..."


def test_task_status_message_progress_bounds():
    """TaskStatusMessage lehnt progress > 100 ab"""
    from schemas.task import TaskStatusMessage, TaskStatus

    with pytest.raises(ValidationError):
        TaskStatusMessage(task_id="x", status=TaskStatus.PROGRESS, progress=101)


def test_task_status_message_success():
    """TaskStatusMessage enthält result bei SUCCESS"""
    from schemas.task import TaskStatusMessage, TaskStatus

    msg = TaskStatusMessage(
        task_id="abc-123",
        status=TaskStatus.SUCCESS,
        progress=100,
        result={"document_id": 42, "title": "Test"},
    )
    assert msg.result == {"document_id": 42, "title": "Test"}
    assert msg.error is None


def test_task_status_message_failure():
    """TaskStatusMessage enthält error bei FAILURE"""
    from schemas.task import TaskStatusMessage, TaskStatus

    msg = TaskStatusMessage(
        task_id="abc-123",
        status=TaskStatus.FAILURE,
        progress=0,
        error="Unbekannter Fehler",
    )
    assert msg.error == "Unbekannter Fehler"
    assert msg.result is None


def test_task_status_enum_contains_retry():
    """TaskStatus Enum enthält RETRY und REVOKED States"""
    from schemas.task import TaskStatus

    assert TaskStatus.RETRY == "RETRY"
    assert TaskStatus.REVOKED == "REVOKED"
