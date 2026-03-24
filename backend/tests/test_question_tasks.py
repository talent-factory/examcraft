"""
Tests für den generate_questions_task Celery Task.
Testet Task-Dispatch, Progress-Steps und Rückgabe-Format.
"""

import dataclasses
import sys
from unittest.mock import MagicMock

# Mock system-level dependencies before any project imports
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()

from unittest.mock import patch


def test_generate_questions_task_importable():
    """Task kann importiert werden"""
    from tasks.question_tasks import generate_questions_task

    assert generate_questions_task is not None


def test_generate_questions_task_name():
    """Task hat den korrekten Celery-Namen"""
    from tasks.question_tasks import generate_questions_task

    assert generate_questions_task.name == "tasks.question_tasks.generate_questions"


def test_generate_questions_task_uses_progress_task_base():
    """Task verwendet ProgressTask als Basis"""
    from tasks.question_tasks import generate_questions_task
    from tasks.document_tasks import ProgressTask

    assert isinstance(generate_questions_task, ProgressTask)


def test_generate_questions_task_registered_in_celery():
    """Task ist in der Celery-App registriert"""
    from celery_app import celery_app

    assert "tasks.question_tasks.generate_questions" in celery_app.tasks


def test_generate_questions_task_has_correct_queue_route():
    """Task ist der question_generation Queue zugeordnet"""
    from celery_app import celery_app

    routes = celery_app.conf.task_routes
    route = routes.get("tasks.question_tasks.generate_questions", {})
    assert route.get("queue") == "question_generation"
    assert route.get("routing_key") == "question.generate"


def test_generate_questions_task_emits_step_zero():
    """Task emittiert Step-0-Progress-Update (0%) beim Start"""
    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    progress_updates = []

    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    mock_result.questions = [FakeQuestion(question_text="Was ist ein Heap?")]
    mock_result.context_summary = FakeContextSummary(query="Heapsort")
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {}

    mock_rag_service = MagicMock()
    mock_rag_service.generate_rag_exam = MagicMock(return_value=mock_result)

    def fake_run_async(coro):
        return mock_result

    with (
        patch("tasks.question_tasks.run_async", side_effect=fake_run_async),
        patch("tasks.question_tasks.RAGService", return_value=mock_rag_service),
    ):
        task = generate_questions_task
        task.update_state = MagicMock(
            side_effect=lambda state, meta: progress_updates.append(meta)
        )

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        generate_questions_task.run(request_data, "42")

    # Step 0 muss emittiert werden
    assert len(progress_updates) >= 1
    first = progress_updates[0]
    assert first["current"] == 0
    assert first["progress"] == 0
    assert "Fragengenerierung" in first["message"] or "Starte" in first["message"]


def test_generate_questions_task_returns_correct_format():
    """Task gibt dict mit exam_id, topic, questions, context_summary, generation_time,
    quality_metrics zurück. Verwendet echte Dataclasses um dataclasses.asdict() zu testen.
    """
    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str
        question_type: str

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str
        total_chunks: int

    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    mock_result.questions = [
        FakeQuestion(question_text="Was ist ein Heap?", question_type="multiple_choice")
    ]
    mock_result.context_summary = FakeContextSummary(query="Heapsort", total_chunks=3)
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {"total_questions": 1}

    mock_rag_service = MagicMock()

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=mock_rag_service),
    ):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        result = generate_questions_task.run(request_data, "42")

    assert result["exam_id"] == "exam_001"
    assert result["topic"] == "Heapsort"
    assert isinstance(result["questions"], list)
    assert result["questions"][0]["question_text"] == "Was ist ein Heap?"
    assert result["context_summary"]["query"] == "Heapsort"
    assert result["context_summary"]["total_chunks"] == 3
    assert result["generation_time"] == 5.0
    assert "total_questions" in result["quality_metrics"]


def test_generate_questions_task_rejects_when_rag_service_unavailable():
    """Task wirft Reject wenn RAGService nicht verfügbar (Core-Deployment)."""
    from tasks.question_tasks import generate_questions_task
    from celery.exceptions import Reject

    with patch("tasks.question_tasks.RAGService", None):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["multiple_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        try:
            generate_questions_task.run(request_data, "42")
            assert False, "Reject hätte geworfen werden sollen"
        except Reject as e:
            assert e.requeue is False


def test_update_job_status_sets_success():
    """_update_job_status should set job.status to SUCCESS and commit."""
    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_job
        )

        from tasks.question_tasks import _update_job_status

        _update_job_status("test-task-id", "SUCCESS")

        assert mock_job.status == "SUCCESS"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_update_job_status_sets_failure():
    """_update_job_status should set job.status to FAILURE and commit."""
    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_job
        )

        from tasks.question_tasks import _update_job_status

        _update_job_status("test-task-id", "FAILURE")

        assert mock_job.status == "FAILURE"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_update_job_status_handles_missing_job():
    """_update_job_status should not crash if job not found."""
    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        from tasks.question_tasks import _update_job_status

        _update_job_status("nonexistent-task", "SUCCESS")

        mock_session.commit.assert_not_called()
        mock_session.close.assert_called_once()
