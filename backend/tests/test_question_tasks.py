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


def test_update_job_status_succeeds_first_attempt():
    """Happy path: first attempt succeeds, no sleep, no extra retries."""
    with (
        patch("database.SessionLocal") as mock_session_cls,
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_job
        )

        from tasks.question_tasks import _update_job_status

        _update_job_status("task-1", "SUCCESS")

        assert mock_job.status == "SUCCESS"
        mock_sleep.assert_not_called()


def test_update_job_status_recovers_on_second_attempt():
    """Transient DB error on attempt 1, success on attempt 2 → no exception."""
    from sqlalchemy.exc import OperationalError

    failing_session = MagicMock()
    failing_session.query.side_effect = OperationalError(
        "stmt", {}, Exception("conn closed")
    )

    healthy_session = MagicMock()
    healthy_job = MagicMock()
    healthy_session.query.return_value.filter_by.return_value.first.return_value = (
        healthy_job
    )

    with (
        patch("database.SessionLocal", side_effect=[failing_session, healthy_session]),
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        from tasks.question_tasks import _update_job_status

        _update_job_status("task-1", "FAILURE")  # no exception

        assert healthy_job.status == "FAILURE"
        # Slept exactly once, with the first backoff (2 s).
        mock_sleep.assert_called_once_with(2)


def test_update_job_status_raises_after_four_failures():
    """All 4 attempts fail → JobStatusUpdateError, three sleeps with backoffs 2, 5, 10."""
    from sqlalchemy.exc import OperationalError
    from tasks.question_tasks import JobStatusUpdateError

    def make_failing_session():
        s = MagicMock()
        s.query.side_effect = OperationalError("stmt", {}, Exception("conn closed"))
        return s

    sessions = [make_failing_session() for _ in range(4)]

    with (
        patch("database.SessionLocal", side_effect=sessions),
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        from tasks.question_tasks import _update_job_status

        try:
            _update_job_status("task-1", "FAILURE")
            raise AssertionError("expected JobStatusUpdateError")
        except JobStatusUpdateError as e:
            assert "task-1" in str(e)
            assert isinstance(e.__cause__, OperationalError)

        assert mock_sleep.call_args_list == [((2,),), ((5,),), ((10,),)]


def test_update_job_status_propagates_job_not_found_immediately():
    """Missing job → JobNotFoundError propagates without retry, without sleep."""
    from tasks.question_tasks import JobNotFoundError, _update_job_status

    with (
        patch("database.SessionLocal") as mock_session_cls,
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        try:
            _update_job_status("ghost", "SUCCESS")
            raise AssertionError("expected JobNotFoundError")
        except JobNotFoundError:
            pass

        mock_sleep.assert_not_called()
        # SessionLocal called exactly once — no retry
        assert mock_session_cls.call_count == 1


def test_update_job_status_does_not_retry_programmer_errors():
    """AttributeError / TypeError must propagate immediately, not be retried."""
    from tasks.question_tasks import _update_job_status

    failing_session = MagicMock()
    failing_session.query.side_effect = AttributeError("simulated programmer error")

    with (
        patch("database.SessionLocal", return_value=failing_session),
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        try:
            _update_job_status("task-1", "SUCCESS")
            raise AssertionError("expected AttributeError")
        except AttributeError:
            pass

        mock_sleep.assert_not_called()


def test_job_status_update_error_is_exported():
    """JobStatusUpdateError is importable from tasks.question_tasks."""
    from tasks.question_tasks import JobStatusUpdateError

    assert issubclass(JobStatusUpdateError, Exception)


def test_try_update_job_status_sets_status_and_commits():
    """_try_update_job_status sets job.status, commits, closes session."""
    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_job = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            mock_job
        )

        from tasks.question_tasks import _try_update_job_status

        _try_update_job_status("task-1", "SUCCESS")

        assert mock_job.status == "SUCCESS"
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


def test_try_update_job_status_raises_when_job_missing():
    """Missing job → JobNotFoundError. NOT retriable; data-integrity issue."""
    from tasks.question_tasks import JobNotFoundError, _try_update_job_status

    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.return_value.filter_by.return_value.first.return_value = None

        try:
            _try_update_job_status("ghost", "SUCCESS")
            raise AssertionError("expected JobNotFoundError")
        except JobNotFoundError as e:
            assert e.task_id == "ghost"
            assert e.status == "SUCCESS"

        mock_session.commit.assert_not_called()
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


def test_try_update_job_status_propagates_db_errors():
    """DB errors must bubble — retry loop in _update_job_status decides what to do."""
    from sqlalchemy.exc import OperationalError

    with patch("database.SessionLocal") as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.query.side_effect = OperationalError(
            "stmt", {}, Exception("conn closed")
        )

        from tasks.question_tasks import _try_update_job_status

        try:
            _try_update_job_status("task-1", "FAILURE")
            raise AssertionError("expected OperationalError")
        except OperationalError:
            pass

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


def test_safe_update_job_status_swallows_job_status_update_error_and_logs(caplog):
    """When _update_job_status raises JobStatusUpdateError, _safe_update_job_status
    logs at CRITICAL level with traceback (logger.critical + exc_info=True), and
    does NOT re-raise.
    """
    import logging

    from tasks.question_tasks import JobStatusUpdateError, _safe_update_job_status

    err = JobStatusUpdateError("task-x", "FAILURE", 4, RuntimeError("simulated cause"))

    with (
        patch("tasks.question_tasks._update_job_status", side_effect=err),
        caplog.at_level(logging.CRITICAL, logger="tasks.question_tasks"),
    ):
        _safe_update_job_status("task-x", "FAILURE")  # no exception

    matching = [
        r
        for r in caplog.records
        if r.levelno == logging.CRITICAL
        and "task-x" in r.message
        and r.exc_info is not None
    ]
    assert matching, (
        "expected at least one CRITICAL log record with task-x in message and exc_info set"
    )


def test_safe_update_job_status_swallows_job_not_found_error_and_logs(caplog):
    """When _update_job_status raises JobNotFoundError, _safe_update_job_status
    logs at CRITICAL with exc_info and does NOT re-raise.
    """
    import logging

    from tasks.question_tasks import JobNotFoundError, _safe_update_job_status

    with (
        patch(
            "tasks.question_tasks._update_job_status",
            side_effect=JobNotFoundError("ghost", "SUCCESS"),
        ),
        caplog.at_level(logging.CRITICAL, logger="tasks.question_tasks"),
    ):
        _safe_update_job_status("ghost", "SUCCESS")  # no exception

    matching = [
        r
        for r in caplog.records
        if r.levelno == logging.CRITICAL
        and "ghost" in r.message
        and r.exc_info is not None
    ]
    assert matching, (
        "expected at least one CRITICAL log record with ghost in message and exc_info set"
    )


def test_safe_update_job_status_passes_through_on_success():
    """Happy path: _safe_update_job_status delegates to _update_job_status."""
    from tasks.question_tasks import _safe_update_job_status

    with patch("tasks.question_tasks._update_job_status") as mock_update:
        _safe_update_job_status("task-1", "SUCCESS")

    mock_update.assert_called_once_with("task-1", "SUCCESS")


def test_generate_questions_task_uses_safe_update_on_success():
    """Success path goes through _safe_update_job_status (not _update_job_status directly)."""
    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str
        question_type: str
        options: list
        correct_answer: str
        explanation: str
        difficulty: str
        source_chunks: list
        source_documents: list
        confidence_score: float

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    fake_q = FakeQuestion(
        question_text="q?",
        question_type="multiple_choice",
        options=["a", "b", "c", "d"],
        correct_answer="a",
        explanation="e",
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.9,
    )
    mock_result = MagicMock()
    mock_result.exam_id = "exam_1"
    mock_result.topic = "T"
    mock_result.questions = [fake_q]
    mock_result.context_summary = FakeContextSummary(query="T")
    mock_result.generation_time = 1.0
    mock_result.quality_metrics = {}

    request_data = {
        "topic": "T",
        "question_count": 1,
        "question_types": ["multiple_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
        patch("tasks.question_tasks._persist_questions", return_value=[1]),
        patch("tasks.question_tasks._safe_update_job_status") as mock_safe,
    ):
        generate_questions_task.update_state = MagicMock()
        generate_questions_task.run(request_data, "42")

    mock_safe.assert_called_once()
    args, _ = mock_safe.call_args
    assert args[1] == "SUCCESS"


def test_generate_questions_task_uses_safe_update_on_reject():
    """Reject path goes through _safe_update_job_status with FAILURE status."""
    from celery.exceptions import Reject

    from tasks.question_tasks import generate_questions_task

    request_data = {
        "topic": "T",
        "question_count": 1,
        "question_types": ["multiple_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }

    with (
        patch("tasks.question_tasks.RAGService", None),  # forces Reject
        patch("tasks.question_tasks._safe_update_job_status") as mock_safe,
    ):
        generate_questions_task.update_state = MagicMock()
        try:
            generate_questions_task.run(request_data, "42")
            raise AssertionError("expected Reject")
        except Reject:
            pass

    # _safe_update_job_status MUST be called with FAILURE on the Reject path
    mock_safe.assert_called_once()
    args, _ = mock_safe.call_args
    assert args[1] == "FAILURE"


def test_generate_questions_task_uses_safe_update_on_final_retry_failure():
    """Generic exception with retries >= max_retries goes through _safe_update_job_status FAILURE.

    Celery task.request is a property backed by a thread-local stack and cannot be
    patched with patch.object. Instead we patch retry_kwargs to {"max_retries": 0}
    so that self.request.retries (== 0 when called via .run()) >= 0 is True and the
    FAILURE branch is taken.
    """
    from tasks.question_tasks import generate_questions_task

    request_data = {
        "topic": "T",
        "question_count": 1,
        "question_types": ["multiple_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }

    boom = RuntimeError("simulated transient failure")

    with (
        patch("tasks.question_tasks.run_async", side_effect=boom),
        patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
        patch("tasks.question_tasks._safe_update_job_status") as mock_safe,
        patch.dict(generate_questions_task.retry_kwargs, {"max_retries": 0}),
    ):
        generate_questions_task.update_state = MagicMock()
        try:
            generate_questions_task.run(request_data, "42")
            raise AssertionError("expected RuntimeError")
        except RuntimeError:
            pass

    mock_safe.assert_called_once()
    args, _ = mock_safe.call_args
    assert args[1] == "FAILURE"


def test_update_job_status_recovers_on_fourth_attempt():
    """Three failures, success on attempt 4 → no exception, three sleeps consumed."""
    from sqlalchemy.exc import OperationalError

    failing = [MagicMock() for _ in range(3)]
    for s in failing:
        s.query.side_effect = OperationalError("stmt", {}, Exception("conn closed"))

    healthy = MagicMock()
    healthy_job = MagicMock()
    healthy.query.return_value.filter_by.return_value.first.return_value = healthy_job

    with (
        patch("database.SessionLocal", side_effect=[*failing, healthy]),
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        from tasks.question_tasks import _update_job_status

        _update_job_status("task-1", "SUCCESS")  # no exception

        assert healthy_job.status == "SUCCESS"
        assert mock_sleep.call_args_list == [((2,),), ((5,),), ((10,),)]


def test_job_status_update_error_carries_structured_fields():
    """JobStatusUpdateError exposes task_id, status, attempts, last_err for Sentry tagging."""
    from tasks.question_tasks import JobStatusUpdateError

    cause = RuntimeError("simulated")
    err = JobStatusUpdateError("task-1", "FAILURE", 4, cause)

    assert err.task_id == "task-1"
    assert err.status == "FAILURE"
    assert err.attempts == 4
    assert err.last_err is cause
    assert "task-1" in str(err)
    assert "FAILURE" in str(err)


def test_job_not_found_error_carries_structured_fields():
    """JobNotFoundError exposes task_id and status for diagnostics."""
    from tasks.question_tasks import JobNotFoundError

    err = JobNotFoundError("ghost", "SUCCESS")

    assert err.task_id == "ghost"
    assert err.status == "SUCCESS"
    assert "ghost" in str(err)
    assert "SUCCESS" in str(err)
