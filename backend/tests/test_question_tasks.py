"""
Tests for the generate_questions_task Celery task.
Tests task dispatch, progress steps, and the return format.
"""

import dataclasses
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# Mock system-level dependencies before any project imports
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()

from unittest.mock import ANY, patch

import pytest


@pytest.fixture(autouse=True)
def _no_job_row():
    """TF-964: the task opens SessionLocal at start (idempotency guard) and
    for the single SUCCESS commit. Tests that don't bring a DB get a stub
    session that finds no job row, so both run through as before. Tests
    that need a real or failing session patch ``database.SessionLocal``
    themselves; their patch is applied later and wins."""
    session = MagicMock()
    query = session.query.return_value.filter_by.return_value
    query.first.return_value = None
    query.with_for_update.return_value.first.return_value = None
    with patch("database.SessionLocal", return_value=session):
        yield session


def test_generate_questions_task_importable():
    """Task can be imported"""
    from tasks.question_tasks import generate_questions_task

    assert generate_questions_task is not None


def test_generate_questions_task_name():
    """Task has the correct Celery name"""
    from tasks.question_tasks import generate_questions_task

    assert generate_questions_task.name == "tasks.question_tasks.generate_questions"


def test_generate_questions_task_uses_progress_task_base():
    """Task uses ProgressTask as its base"""
    from tasks.question_tasks import generate_questions_task
    from tasks.document_tasks import ProgressTask

    assert isinstance(generate_questions_task, ProgressTask)


def test_generate_questions_task_registered_in_celery():
    """Task is registered in the Celery app"""
    from celery_app import celery_app

    assert "tasks.question_tasks.generate_questions" in celery_app.tasks


def test_generate_questions_task_has_correct_queue_route():
    """Task is routed to the question_generation queue"""
    from celery_app import celery_app

    routes = celery_app.conf.task_routes
    route = routes.get("tasks.question_tasks.generate_questions", {})
    assert route.get("queue") == "question_generation"
    assert route.get("routing_key") == "question.generate"


def test_generate_questions_task_emits_step_zero():
    """Task emits the step-0 progress update (0%) at start"""
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
        patch("tasks.question_tasks._persist_questions", return_value=[1]),
        patch("tasks.question_tasks._safe_update_job_status"),
    ):
        task = generate_questions_task
        task.update_state = MagicMock(
            side_effect=lambda state, meta: progress_updates.append(meta)
        )

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["single_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        generate_questions_task.run(request_data, "42")

    # Step 0 must be emitted
    assert len(progress_updates) >= 1
    first = progress_updates[0]
    assert first["current"] == 0
    assert first["progress"] == 0
    # TF-736: a code the frontend translates, no German text …
    assert first["code"] == "generation_started"
    assert first["message"] == ""
    # … and no step total derived from the requested count: the effective
    # count is unknown until the context is loaded (cause 3).
    assert first["total"] == 1
    assert first["params"] == {}


def test_generate_questions_task_relays_service_progress_codes():
    """TF-736: the callback handed to generate_rag_exam forwards the
    service's (current, total, code, params) to update_progress unchanged.
    The premium tests call the service with lambdas, so only this test
    catches a signature break between task and service."""
    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    progress_updates = []
    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    mock_result.questions = []
    mock_result.context_summary = FakeContextSummary(query="Heapsort")
    mock_result.generation_time = 1.0
    mock_result.quality_metrics = {}

    mock_rag_service = MagicMock()
    mock_rag_service.generate_rag_exam = MagicMock(return_value=mock_result)

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=mock_rag_service),
        patch("tasks.question_tasks._persist_questions", return_value=[]),
        patch("tasks.question_tasks._safe_update_job_status"),
        patch.object(
            generate_questions_task,
            "update_state",
            side_effect=lambda state, meta: progress_updates.append(meta),
        ),
    ):
        generate_questions_task.run(
            {
                "topic": "Heapsort",
                "question_count": 15,
                "question_types": ["single_choice"],
                "difficulty": "medium",
                "language": "de",
                "document_ids": None,
                "context_chunks_per_question": 3,
                "prompt_config": None,
            },
            "42",
        )
        callback = mock_rag_service.generate_rag_exam.call_args.kwargs[
            "progress_callback"
        ]
        callback(1, 8, "context_loaded", {"total": 6})
        callback(2, 8, "question_generated", {"current": 1, "total": 6})

    assert progress_updates[-2:] == [
        {
            "current": 1,
            "total": 8,
            "progress": 12,
            "message": "",
            "code": "context_loaded",
            "params": {"total": 6},
        },
        {
            "current": 2,
            "total": 8,
            "progress": 25,
            "message": "",
            "code": "question_generated",
            "params": {"current": 1, "total": 6},
        },
    ]


def test_generate_questions_task_returns_correct_format():
    """Task returns a dict with exam_id, topic, questions, context_summary,
    generation_time, quality_metrics. Uses real dataclasses to test
    dataclasses.asdict().
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
        FakeQuestion(question_text="Was ist ein Heap?", question_type="single_choice")
    ]
    mock_result.context_summary = FakeContextSummary(query="Heapsort", total_chunks=3)
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {"total_questions": 1}

    mock_rag_service = MagicMock()

    # TF-359/TF-865: capture the OTel span tags set by the task so a
    # regression that drops user_id/topic tagging fails here (the lines
    # execute either way).
    captured_tags: dict[str, str] = {}

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=mock_rag_service),
        patch("tasks.question_tasks._persist_questions", return_value=[1]),
        patch("tasks.question_tasks._safe_update_job_status"),
        patch(
            "tasks.question_tasks.set_span_tag",
            side_effect=lambda key, value: captured_tags.__setitem__(key, value),
        ),
    ):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["single_choice"],
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
    assert captured_tags["user_id"] == "42"
    assert captured_tags["topic"] == "Heapsort"


def test_generate_questions_task_rejects_when_rag_service_unavailable():
    """Task raises Reject when RAGService is unavailable (Core deployment)."""
    from tasks.question_tasks import generate_questions_task
    from celery.exceptions import Reject

    with patch("tasks.question_tasks.RAGService", None):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["single_choice"],
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
        mock_session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = mock_job

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
    healthy_session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = healthy_job

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
        mock_session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = None

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
        mock_session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = mock_job

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
        mock_session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = None

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


def test_safe_update_job_status_swallows_job_status_update_error_and_logs(mocker):
    """When _update_job_status raises JobStatusUpdateError, _safe_update_job_status
    logs at CRITICAL level with traceback (logger.critical + exc_info=True), and
    does NOT re-raise.

    mocker.patch directly on the module logger instead of caplog: pytest 7.4.3
    (the CI-pinned version) leaves caplog.records empty here; the direct mock
    is version-independent.
    """
    from tasks.question_tasks import (
        JobStatusUpdateError,
        JobStatusWrite,
        _safe_update_job_status,
    )

    mock_logger = mocker.patch("tasks.question_tasks.logger")
    err = JobStatusUpdateError("task-x", "FAILURE", 4, RuntimeError("simulated cause"))

    with patch("tasks.question_tasks._update_job_status", side_effect=err):
        outcome = _safe_update_job_status("task-x", "FAILURE")  # no exception

    assert outcome is JobStatusWrite.FAILED

    mock_logger.critical.assert_called_once()
    call = mock_logger.critical.call_args
    rendered = call.args[0] % call.args[1:] if len(call.args) > 1 else call.args[0]
    assert "task-x" in rendered
    assert call.kwargs.get("exc_info") is True


def test_safe_update_job_status_swallows_job_not_found_error_and_logs(mocker):
    """When _update_job_status raises JobNotFoundError, _safe_update_job_status
    logs at CRITICAL with exc_info and does NOT re-raise."""
    from tasks.question_tasks import JobNotFoundError, _safe_update_job_status

    mock_logger = mocker.patch("tasks.question_tasks.logger")

    with patch(
        "tasks.question_tasks._update_job_status",
        side_effect=JobNotFoundError("ghost", "SUCCESS"),
    ):
        _safe_update_job_status("ghost", "SUCCESS")  # no exception

    mock_logger.critical.assert_called_once()
    call = mock_logger.critical.call_args
    rendered = call.args[0] % call.args[1:] if len(call.args) > 1 else call.args[0]
    assert "ghost" in rendered
    assert call.kwargs.get("exc_info") is True


def test_safe_update_job_status_passes_through_on_success():
    """Happy path: _safe_update_job_status delegates to _update_job_status."""
    from tasks.question_tasks import _safe_update_job_status

    with patch("tasks.question_tasks._update_job_status") as mock_update:
        _safe_update_job_status("task-1", "SUCCESS")

    mock_update.assert_called_once_with("task-1", "SUCCESS")


def test_generate_questions_task_writes_success_in_the_save_commit():
    """TF-964: on success, SUCCESS is written inside ``_save_generation``'s
    single commit together with the questions — not afterwards through
    ``_safe_update_job_status``, whose separate commit was the window in
    which a crash left saved questions on a PENDING job."""
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
        question_type="single_choice",
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
        "question_types": ["single_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
        patch("tasks.question_tasks._save_generation", return_value=[1]) as mock_save,
        patch("tasks.question_tasks._safe_update_job_status") as mock_safe,
    ):
        generate_questions_task.update_state = MagicMock()
        result = generate_questions_task.run(request_data, "42")

    mock_save.assert_called_once()
    mock_safe.assert_not_called()
    assert result["review_question_ids"] == [1]


def test_generate_questions_task_uses_safe_update_on_reject():
    """Reject path goes through _safe_update_job_status with FAILURE status."""
    from celery.exceptions import Reject

    from tasks.question_tasks import generate_questions_task

    request_data = {
        "topic": "T",
        "question_count": 1,
        "question_types": ["single_choice"],
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


def test_generate_questions_task_uses_safe_update_on_model_unavailable():
    """TF-438: a ModelUnavailableError (whole fallback chain 404) is permanent —
    it must fail the job immediately via _safe_update_job_status FAILURE and
    re-raise, NOT fall through to the generic handler that only marks FAILURE on
    the final retry (which would re-introduce the TF-351 ghost-task symptom)."""
    from services.claude_service import ModelUnavailableError
    from tasks.question_tasks import generate_questions_task

    request_data = {
        "topic": "T",
        "question_count": 1,
        "question_types": ["single_choice"],
        "difficulty": "medium",
        "language": "de",
        "document_ids": None,
        "context_chunks_per_question": 3,
        "prompt_config": None,
    }

    with (
        patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
        patch(
            "tasks.question_tasks.run_async",
            side_effect=ModelUnavailableError("all models returned 404"),
        ),
        patch("tasks.question_tasks._safe_update_job_status") as mock_safe,
    ):
        generate_questions_task.update_state = MagicMock()
        try:
            generate_questions_task.run(request_data, "42")
            raise AssertionError("expected ModelUnavailableError")
        except ModelUnavailableError:
            pass

    # Fail fast: FAILURE recorded immediately, not deferred to the final retry.
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
        "question_types": ["single_choice"],
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
        finally:
            # Task.retry() stores max_retries=0 as `override_max_retries` on
            # the task; called directly it re-raises before Celery's autoretry
            # wrapper deletes it again. Left behind, the wrapper copies 0 into
            # retry_kwargs on the next autoretry in this process, and every
            # later test runs as if on its final retry.
            vars(generate_questions_task._get_current_object()).pop(
                "override_max_retries", None
            )

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
    healthy.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = healthy_job

    with (
        patch("database.SessionLocal", side_effect=[*failing, healthy]),
        patch("tasks.question_tasks.time.sleep") as mock_sleep,
    ):
        from tasks.question_tasks import _update_job_status

        _update_job_status("task-1", "SUCCESS")  # no exception

        assert healthy_job.status == "SUCCESS"
        assert mock_sleep.call_args_list == [((2,),), ((5,),), ((10,),)]


def test_job_status_update_error_carries_structured_fields():
    """JobStatusUpdateError exposes task_id, status, attempts, last_err for observability tagging."""
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


# === TF-330: write-path normalization in _persist_questions ===


def _make_fake_question(options):
    """Premium RAGQuestion is a dataclass; the persist path uses attribute
    access, so a SimpleNamespace is enough for unit-level tests."""
    from types import SimpleNamespace

    return SimpleNamespace(
        question_text="Welche Empfehlung gilt für E-Mails?",
        question_type="single_choice",
        options=options,
        correct_answer="A",
        explanation="Aktive Sprache ist klarer.",
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.9,
        bloom_level=3,
    )


def _capture_persisted_options(fake_question):
    """Run ``_persist_questions`` against a stubbed SessionLocal and return
    the ``options`` value that ended up on the QuestionReview row."""
    from tasks.question_tasks import _persist_questions

    captured: list = []

    class _EmptyQuery:
        """Tiny chainable stub for the Document filename→id lookup path
        introduced by TF-321. Returns no documents so the QuestionSourceDocument
        merge loop is a no-op — these tests focus on options normalization."""

        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    class _StubSession:
        def add(self, obj):
            # Capture the first QuestionReview only — ReviewHistory rows
            # come through later in the same loop and don't carry options.
            if obj.__class__.__name__ == "QuestionReview":
                captured.append(obj.options)

        def query(self, *_args, **_kwargs):
            return _EmptyQuery()

        def merge(self, obj):
            # TF-321 QuestionSourceDocument merge — no-op for these tests.
            return obj

        def flush(self):
            # Simulate the autoincrement IDs the real DB would assign so the
            # subsequent ReviewHistory rows have something to FK against.
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    # _persist_questions iterates ``reviews`` after flush() to read .id for
    # the history rows; pre-seed an id so that loop succeeds.
    def _flush():
        for obj in captured_objs:
            obj.id = 1

    captured_objs: list = []

    class _StubSessionWithIds(_StubSession):
        def add(self, obj):
            if obj.__class__.__name__ == "QuestionReview":
                captured.append(obj.options)
                captured_objs.append(obj)

        def flush(self):
            _flush()

    with patch("database.SessionLocal", return_value=_StubSessionWithIds()):
        _persist_questions(
            questions=[fake_question],
            exam_id="exam_demo",
            topic="Kommunikation",
            language="de",
            user_id=42,
            institution_id=1,
        )

    assert captured, "QuestionReview row was not added to the session"
    return captured[0]


def test_persist_questions_normalizes_dict_options_to_list():
    """TF-330 AC #2: write-path emits the canonical List[str] shape even when
    the upstream generator returns the legacy dict shape."""
    legacy_dict = {
        "A": "Verwenden Sie aktive Sprache",
        "B": "Schreiben Sie passiv",
        "C": "Antworten Sie spät",
        "D": "Melden Sie sich bis Freitag",
    }

    persisted = _capture_persisted_options(_make_fake_question(legacy_dict))

    assert persisted == [
        "Verwenden Sie aktive Sprache",
        "Schreiben Sie passiv",
        "Antworten Sie spät",
        "Melden Sie sich bis Freitag",
    ]


def test_persist_questions_passes_list_options_through():
    """List-shape generation paths must round-trip unchanged."""
    list_options = ["alpha", "beta", "gamma", "delta"]

    persisted = _capture_persisted_options(_make_fake_question(list_options))

    assert persisted == list_options


def test_persist_questions_preserves_none_options():
    """Open-ended / true-false rows have no options; ``None`` stays ``None``."""
    persisted = _capture_persisted_options(_make_fake_question(None))

    assert persisted is None


# ---------------------------------------------------------------------------
# TF-351 regression: correct_answer serialization
# ---------------------------------------------------------------------------


def _make_open_ended_question(correct_answer):
    """SimpleNamespace for open_ended questions with an arbitrary correct_answer type."""
    from types import SimpleNamespace

    return SimpleNamespace(
        question_text="Erläutern Sie den Begriff Kommunikation.",
        question_type="open_ended",
        options=None,
        correct_answer=correct_answer,
        explanation="Musterlösung.",
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.85,
        bloom_level=4,
    )


def _capture_persisted_correct_answer(fake_question):
    """Runs _persist_questions with a single open_ended question and returns
    the correct_answer value that ended up on the QuestionReview row."""
    from tasks.question_tasks import _persist_questions

    captured: list = []
    captured_objs: list = []

    class _EmptyQuery:
        def filter(self, *_a, **_kw):
            return self

        def all(self):
            return []

    class _StubSession:
        def add(self, obj):
            if obj.__class__.__name__ == "QuestionReview":
                captured.append(obj.correct_answer)
                captured_objs.append(obj)

        def query(self, *_a, **_kw):
            return _EmptyQuery()

        def merge(self, obj):  # noqa: ARG002
            return obj

        def flush(self):
            for obj in captured_objs:
                obj.id = 1

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    with patch("database.SessionLocal", return_value=_StubSession()):
        _persist_questions(
            questions=[fake_question],
            exam_id="exam_tf351",
            topic="Kommunikation",
            language="de",
            user_id=42,
            institution_id=1,
        )

    assert captured, "QuestionReview row was not added to the session"
    return captured[0]


def test_persist_questions_serializes_dict_correct_answer_to_json():
    """Premium open_ended rubric dicts must be JSON-serialized before INSERT —
    psycopg2 cannot adapt a bare dict to the TEXT column."""
    import json

    rubric = {
        "overview": "Vollständige Antwort beschreibt Sender-Empfänger-Modell.",
        "excellent": "Alle drei Komponenten korrekt benannt.",
        "good": "Zwei Komponenten korrekt.",
        "satisfactory": "Eine Komponente korrekt.",
        "insufficient": "Keine korrekte Komponente.",
    }

    persisted = _capture_persisted_correct_answer(_make_open_ended_question(rubric))

    assert isinstance(persisted, str), "dict must be serialized to str for TEXT column"
    parsed = json.loads(persisted)
    assert parsed == rubric


def test_persist_questions_serializes_list_correct_answer_to_string():
    """list correct_answer (grading criteria) becomes semicolon-joined string."""
    criteria = ["Sachliche Richtigkeit", "Vollständigkeit", "Sprachliche Qualität"]

    persisted = _capture_persisted_correct_answer(_make_open_ended_question(criteria))

    assert isinstance(persisted, str)
    assert "Sachliche Richtigkeit" in persisted
    assert "Vollständigkeit" in persisted


def test_persist_questions_passes_string_correct_answer_unchanged():
    """Plain string correct_answer (standard case) round-trips unchanged."""
    sample = "Das Sender-Empfänger-Modell beschreibt..."

    persisted = _capture_persisted_correct_answer(_make_open_ended_question(sample))

    assert persisted == sample


def test_persist_questions_passes_empty_string_correct_answer_unchanged():
    """Empty-string correct_answer (else-branch with falsy value) stays as empty
    string — not None — so downstream consumers can distinguish "no answer
    provided" from "answer was the empty string"."""
    persisted = _capture_persisted_correct_answer(_make_open_ended_question(""))

    assert persisted == ""


def test_persist_questions_serializes_nested_dict_correct_answer_to_json():
    """Nested rubric dicts (Premium open_ended) must round-trip via JSON, not
    end up as Python repr (``"{'key': {'nested': ...}}"``) in the TEXT column."""
    import json

    nested_rubric = {
        "criteria": {
            "content_accuracy": {
                "description": "Sachliche Richtigkeit",
                "max_points": 5,
            },
            "completeness": {"description": "Vollständigkeit", "max_points": 3},
        },
        "overview": "Vollständige Antwort beschreibt Sender-Empfänger-Modell.",
    }

    persisted = _capture_persisted_correct_answer(
        _make_open_ended_question(nested_rubric)
    )

    assert isinstance(persisted, str)
    assert not persisted.startswith("{'"), "Must not be Python repr"
    parsed = json.loads(persisted)
    assert parsed == nested_rubric


def test_persist_questions_preserves_none_correct_answer():
    """None correct_answer stays None (open_ended without sample answer)."""
    persisted = _capture_persisted_correct_answer(_make_open_ended_question(None))

    assert persisted is None


# ---------------------------------------------------------------------------
# TF-351 follow-up: explanation dict serialization
# ---------------------------------------------------------------------------


def _capture_persisted_explanation(fake_question):
    """Runs _persist_questions and returns the explanation value that ended
    up on the QuestionReview row."""
    from tasks.question_tasks import _persist_questions

    captured: list = []
    captured_objs: list = []

    class _EmptyQuery:
        def filter(self, *_a, **_kw):
            return self

        def all(self):
            return []

    class _StubSession:
        def add(self, obj):
            if obj.__class__.__name__ == "QuestionReview":
                captured.append(obj.explanation)
                captured_objs.append(obj)

        def query(self, *_a, **_kw):
            return _EmptyQuery()

        def merge(self, obj):  # noqa: ARG002
            return obj

        def flush(self):
            for obj in captured_objs:
                obj.id = 1

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    with patch("database.SessionLocal", return_value=_StubSession()):
        _persist_questions(
            questions=[fake_question],
            exam_id="exam_tf351",
            topic="Kommunikation",
            language="de",
            user_id=42,
            institution_id=1,
        )

    assert captured, "QuestionReview row was not added to the session"
    return captured[0]


def _make_question_with_explanation(explanation):
    from types import SimpleNamespace

    return SimpleNamespace(
        question_text="Erläutern Sie den Begriff Kommunikation.",
        question_type="open_ended",
        options=None,
        correct_answer="Musterlösung",
        explanation=explanation,
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.85,
        bloom_level=4,
    )


def test_persist_questions_serializes_dict_explanation_to_json():
    """explanation dict (Premium open_ended rubrics) must be JSON-serialized,
    not str()-repr — same contract as correct_answer above."""
    import json

    rubric = {
        "content_accuracy": {"description": "Sachliche Richtigkeit", "max_points": 5},
        "completeness": {"description": "Vollständigkeit", "max_points": 3},
    }

    persisted = _capture_persisted_explanation(_make_question_with_explanation(rubric))

    assert isinstance(persisted, str)
    # Must be valid JSON, not Python repr like "{'key': 'value'}"
    parsed = json.loads(persisted)
    assert parsed == rubric


def test_persist_questions_explanation_dict_is_not_python_repr():
    """Ensure we don't produce str(dict) Python-repr in DB — this is the
    failure mode that triggered TF-351 on the correct_answer column."""
    rubric = {"overview": "Vollständige Antwort"}

    persisted = _capture_persisted_explanation(_make_question_with_explanation(rubric))

    # Python repr starts with { and uses single quotes — not valid JSON
    assert not persisted.startswith("{'"), "Must not be Python repr"


def test_persist_questions_explanation_list_joined_with_semicolons():
    """list explanation (grading criteria) becomes semicolon-joined string."""
    criteria = [
        "Sender korrekt benannt",
        "Empfänger korrekt benannt",
        "Kanal beschrieben",
    ]

    persisted = _capture_persisted_explanation(
        _make_question_with_explanation(criteria)
    )

    assert (
        persisted
        == "Sender korrekt benannt; Empfänger korrekt benannt; Kanal beschrieben"
    )


def test_persist_questions_explanation_empty_list_becomes_empty_string():
    """Empty list explanation joins to empty string (not None) — documents the
    current contract so future refactors don't silently change it."""
    persisted = _capture_persisted_explanation(_make_question_with_explanation([]))

    assert persisted == ""


def test_persist_questions_preserves_none_explanation():
    """None explanation stays None — open_ended questions may omit it."""
    persisted = _capture_persisted_explanation(_make_question_with_explanation(None))

    assert persisted is None


# ---------------------------------------------------------------------------
# TF-351: ProgrammingError must mark the job FAILURE and not loop-retry
# ---------------------------------------------------------------------------


def test_programming_error_marks_job_failure_and_propagates():
    """End-to-end: when _persist_questions raises ProgrammingError (e.g. psycopg2
    ``can't adapt type 'dict'``), the task must call _safe_update_job_status
    with ``FAILURE`` *and* re-raise, so the frontend sees a terminal state
    instead of a PENDING ghost-task. This is the TF-351 anti-pattern."""
    import dataclasses

    from sqlalchemy.exc import ProgrammingError

    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str
        question_type: str

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    mock_result = MagicMock()
    mock_result.exam_id = "exam_e2e"
    mock_result.topic = "Heapsort"
    mock_result.questions = [
        FakeQuestion(question_text="Was ist ein Heap?", question_type="single_choice")
    ]
    mock_result.context_summary = FakeContextSummary(query="Heapsort")
    mock_result.generation_time = 1.0
    mock_result.quality_metrics = {}

    boom = ProgrammingError("INSERT ...", {}, Exception("can't adapt type 'dict'"))

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
        patch("tasks.question_tasks._persist_questions", side_effect=boom),
        patch("tasks.question_tasks._safe_update_job_status") as mock_status,
    ):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Heapsort",
            "question_count": 1,
            "question_types": ["single_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
        }

        try:
            generate_questions_task.run(request_data, "42")
        except ProgrammingError:
            raised = True
        else:
            raised = False

    assert raised, "ProgrammingError must propagate so Celery records the failure"
    # FAILURE must be set unconditionally — not only on the final retry — because
    # ProgrammingError is in dont_autoretry_for and never retries.
    failure_calls = [
        call for call in mock_status.call_args_list if call.args[1] == "FAILURE"
    ]
    assert failure_calls, (
        "Job status must be marked FAILURE so the frontend leaves PENDING — "
        "otherwise the ghost-task symptom of TF-351 returns."
    )


def test_programming_error_in_dont_autoretry_for():
    """Sanity guard: keep ProgrammingError in dont_autoretry_for so Celery does
    not blindly retry a non-recoverable DB error and burn Claude credits."""
    from sqlalchemy.exc import ProgrammingError
    from tasks.question_tasks import generate_questions_task

    dont_retry = getattr(generate_questions_task, "dont_autoretry_for", ())
    assert ProgrammingError in dont_retry


def test_model_unavailable_error_in_dont_autoretry_for():
    """TF-438: a fully-retired model chain (every model 404) is permanent. Keep
    ModelUnavailableError in dont_autoretry_for so Celery cannot resurrect the
    TF-437 endless-retry loop that burned Claude credits on a dead model."""
    from services.claude_service import ModelUnavailableError
    from tasks.question_tasks import generate_questions_task

    dont_retry = getattr(generate_questions_task, "dont_autoretry_for", ())
    assert ModelUnavailableError in dont_retry


# ---------------------------------------------------------------------------
# TF-351: run_async must use a fresh, isolated event loop
# ---------------------------------------------------------------------------


def test_run_async_creates_fresh_loop_per_call():
    """run_async must create a new event loop for every call so that stale
    async state from a prior task or retry cannot leak into the next one."""
    loops_created = []

    class _FakeLoop:
        def run_until_complete(self, coro):
            coro.close()
            return "result"

        def close(self):
            pass

    def _fake_new_loop():
        loop = _FakeLoop()
        loops_created.append(loop)
        return loop

    async def _dummy():
        return "result"

    with (
        patch(
            "tasks.document_tasks.asyncio.new_event_loop", side_effect=_fake_new_loop
        ),
        patch("tasks.document_tasks.asyncio.set_event_loop"),
    ):
        from tasks.document_tasks import run_async

        run_async(_dummy())
        run_async(_dummy())

    assert len(loops_created) == 2, (
        "A fresh loop must be created for every run_async call"
    )


def test_run_async_closes_loop_after_exception():
    """run_async must close the event loop in the finally block even when the
    coroutine raises, so resources are never leaked across retries."""
    closed: list = []

    class _TrackingLoop:
        def run_until_complete(self, coro):
            coro.close()
            raise RuntimeError("boom")

        def close(self):
            closed.append(True)

    with (
        patch(
            "tasks.document_tasks.asyncio.new_event_loop", return_value=_TrackingLoop()
        ),
        patch("tasks.document_tasks.asyncio.set_event_loop"),
    ):
        from tasks.document_tasks import run_async

        async def _failing():
            raise RuntimeError("boom")

        try:
            run_async(_failing())
        except RuntimeError:
            pass

    assert closed, "Event loop must be closed even when the coroutine raises"


# === TF-320: QuestionTag assignment in _persist_questions ===


def _run_persist_with_tags(tag_ids: list):
    """Run _persist_questions with the given tag_ids against a stub session.
    Returns (added_question_tags, execute_calls)."""
    from types import SimpleNamespace
    from unittest.mock import patch
    from tasks.question_tasks import _persist_questions

    fake_question = SimpleNamespace(
        question_text="Welche Tags werden zugewiesen?",
        question_type="single_choice",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="Erklärung.",
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.9,
        bloom_level=None,
    )

    added_question_tags = []
    execute_calls = []

    class _TagStubSession:
        def __init__(self):
            self._objs = []

        def add(self, obj):
            self._objs.append(obj)
            if obj.__class__.__name__ == "QuestionTag":
                added_question_tags.append(obj)

        def query(self, *args, **_kwargs):
            # Branch on the first column being queried so the Tag visibility
            # query returns visible IDs while the Document lookup query
            # returns no document rows (the persist path tolerates an empty
            # filename→document_id map).
            first = args[0] if args else None
            class_name = getattr(getattr(first, "class_", None), "__name__", "")
            if class_name == "Tag":
                rows = [(tid,) for tid in tag_ids]
            else:
                rows = []

            class _Q:
                def filter(self, *a, **kw):
                    return self

                def all(self):
                    return rows

            return _Q()

        def merge(self, obj):
            return obj

        def flush(self):
            counter = [0]
            for obj in self._objs:
                if obj.__class__.__name__ == "QuestionReview":
                    counter[0] += 1
                    obj.id = counter[0]

        def execute(self, *args, **kwargs):
            execute_calls.append((args, kwargs))

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    with patch("database.SessionLocal", return_value=_TagStubSession()):
        _persist_questions(
            questions=[fake_question],
            exam_id="exam_tf320",
            topic="Tags Test",
            language="de",
            user_id=1,
            institution_id=1,
            tag_ids=tag_ids,
        )

    return added_question_tags, execute_calls


def test_persist_questions_creates_question_tag_rows_for_each_review_and_tag():
    """For 1 question and 2 tags -> 2 QuestionTag rows with correct IDs."""
    added_tags, _ = _run_persist_with_tags([10, 20])

    assert len(added_tags) == 2
    tag_id_pairs = {(obj.question_id, obj.tag_id) for obj in added_tags}
    assert (1, 10) in tag_id_pairs
    assert (1, 20) in tag_id_pairs


def test_persist_questions_does_not_write_denormalised_usage_count():
    """Regression: usage_count is no longer written via UPDATE — it's live from QuestionTag."""
    _, execute_calls = _run_persist_with_tags([10, 20])
    update_calls = [c for c in execute_calls if "UPDATE tags" in str(c)]
    assert update_calls == []


def test_persist_questions_without_tag_ids_creates_no_question_tags():
    """Without tag_ids -> no QuestionTag rows, no UPDATE tags."""
    added_tags, execute_calls = _run_persist_with_tags([])
    update_calls = [c for c in execute_calls if "UPDATE tags" in str(c)]

    assert added_tags == []
    assert update_calls == []


def test_persist_questions_rejects_invisible_tag_ids():
    """Tag IDs that are NOT in the visible list -> ValueError (no FK violation)."""
    import pytest
    from types import SimpleNamespace
    from tasks.question_tasks import _persist_questions

    fake_question = SimpleNamespace(
        question_text="Q?",
        question_type="single_choice",
        options=["A", "B"],
        correct_answer="A",
        explanation="x",
        difficulty="easy",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.5,
        bloom_level=None,
    )

    class _EmptyVisibleSession:
        def __init__(self):
            self._objs = []

        def add(self, obj):
            self._objs.append(obj)

        def query(self, *_a, **_kw):
            class _Q:
                def filter(self, *a, **kw):
                    return self

                def all(self):
                    return []

            return _Q()

        def merge(self, obj):
            return obj

        def flush(self):
            counter = [0]
            for obj in self._objs:
                if obj.__class__.__name__ == "QuestionReview":
                    counter[0] += 1
                    obj.id = counter[0]

        def execute(self, *_a, **_kw):
            pass

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    from unittest.mock import patch

    with patch("database.SessionLocal", return_value=_EmptyVisibleSession()):
        with pytest.raises(ValueError, match="Ungültige oder unsichtbare Tag-IDs"):
            _persist_questions(
                questions=[fake_question],
                exam_id="ex",
                topic="t",
                language="de",
                user_id=1,
                institution_id=1,
                tag_ids=[999],
            )


def test_generate_questions_task_passes_tag_ids_from_request_data():
    """generate_questions_task extracts tag_ids from request_data and passes them along."""
    import dataclasses
    from unittest.mock import MagicMock, patch
    from tasks.question_tasks import generate_questions_task

    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str
        question_type: str

    @dataclasses.dataclass
    class FakeContext:
        query: str
        total_chunks: int

    mock_result = MagicMock()
    mock_result.exam_id = "exam_tf320_task"
    mock_result.topic = "Tags Task Test"
    mock_result.questions = [FakeQuestion("Q?", "single_choice")]
    mock_result.context_summary = FakeContext("Tags Task Test", 1)
    mock_result.generation_time = 1.0
    mock_result.quality_metrics = {}

    mock_persist = MagicMock(return_value=[1])

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService"),
        patch("tasks.question_tasks._persist_questions", mock_persist),
        patch("tasks.question_tasks._safe_update_job_status"),
    ):
        generate_questions_task.update_state = MagicMock()

        request_data = {
            "topic": "Tags Task Test",
            "question_count": 1,
            "question_types": ["single_choice"],
            "difficulty": "medium",
            "language": "de",
            "document_ids": None,
            "context_chunks_per_question": 3,
            "prompt_config": None,
            "tag_ids": [5, 7],
        }

        generate_questions_task.run(request_data, "1", institution_id=1)

    mock_persist.assert_called_once_with(
        questions=mock_result.questions,
        exam_id="exam_tf320_task",
        topic="Tags Task Test",
        language="de",
        user_id=1,
        institution_id=1,
        tag_ids=[5, 7],
        framework_id=None,
        db=ANY,
        generation_job_id=None,
    )


# === TF-383: generation_metadata (prompt/template provenance) in the write path ===


def _capture_persisted_question(fake_question):
    """Run ``_persist_questions`` against a stubbed SessionLocal and return the
    QuestionReview object that was added — used to assert provenance fields."""
    from tasks.question_tasks import _persist_questions

    captured_objs: list = []

    class _EmptyQuery:
        def filter(self, *_args, **_kwargs):
            return self

        def all(self):
            return []

    class _StubSession:
        def add(self, obj):
            if obj.__class__.__name__ == "QuestionReview":
                captured_objs.append(obj)

        def query(self, *_args, **_kwargs):
            return _EmptyQuery()

        def merge(self, obj):
            return obj

        def flush(self):
            for obj in captured_objs:
                obj.id = 1

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    with patch("database.SessionLocal", return_value=_StubSession()):
        _persist_questions(
            questions=[fake_question],
            exam_id="exam_demo",
            topic="Kommunikation",
            language="de",
            user_id=42,
            institution_id=1,
        )

    assert captured_objs, "QuestionReview row was not added to the session"
    return captured_objs[0]


def test_persist_questions_stores_generation_metadata():
    """TF-383: the provenance snapshot of the Premium question is persisted
    on the QuestionReview row."""
    from types import SimpleNamespace

    snapshot = {
        "prompt_id": "uuid-1",
        "prompt_name": "universal_single_choice_generator",
        "prompt_version": 3,
        "is_default_template": False,
        "variables": {"topic": "Heaps", "difficulty": "medium"},
    }
    fake_question = SimpleNamespace(
        question_text="Was ist ein Heap?",
        question_type="single_choice",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation="…",
        difficulty="medium",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.9,
        bloom_level=3,
        generation_metadata=snapshot,
    )

    persisted = _capture_persisted_question(fake_question)

    assert persisted.generation_metadata == snapshot


def test_persist_questions_generation_metadata_defaults_to_none():
    """Question sources without provenance (e.g. manual, no Premium snapshot)
    must not crash — getattr returns None."""
    from types import SimpleNamespace

    # Deliberately NO generation_metadata attribute -> tests the getattr(..., None).
    fake_question = SimpleNamespace(
        question_text="Frage ohne Herkunft",
        question_type="open_ended",
        options=None,
        correct_answer="Antwort",
        explanation="…",
        difficulty="easy",
        source_chunks=[],
        source_documents=[],
        confidence_score=0.5,
        bloom_level=2,
    )

    persisted = _capture_persisted_question(fake_question)

    assert persisted.generation_metadata is None


# ===========================================================================
# TF-605: source_document_ids join-key fix in _persist_questions
#
# TF-605 changed RAGQuestion.source_documents from filenames to display
# titles for the provenance UI. Titles are free text and can differ
# arbitrarily from Document.original_filename, so linking QuestionSourceDocument
# rows can no longer rely on matching source_documents against filenames.
# These tests pin the fix: _persist_questions must prefer the parallel
# source_document_ids field (document primary keys) when present, and only
# fall back to filename-matching for callers that don't supply it.
# ===========================================================================


class _DocumentQueryStubSession:
    """Stub SessionLocal whose `Document.id, Document.original_filename` query
    returns a fixed set of rows, and which records every QuestionSourceDocument
    merged so tests can assert on the resulting (question_id, document_id) links."""

    def __init__(self, doc_rows):
        # doc_rows: list of (id, original_filename) tuples
        self._doc_rows = doc_rows
        self._objs = []
        self.merged = []

    def add(self, obj):
        self._objs.append(obj)

    def query(self, *args, **_kwargs):
        first = args[0] if args else None
        class_name = getattr(getattr(first, "class_", None), "__name__", "")

        from types import SimpleNamespace

        rows = (
            [SimpleNamespace(id=i, original_filename=f) for i, f in self._doc_rows]
            if class_name == "Document"
            else []
        )

        class _Q:
            def filter(self, *_a, **_kw):
                return self

            def all(self):
                return rows

        return _Q()

    def merge(self, obj):
        if obj.__class__.__name__ == "QuestionSourceDocument":
            self.merged.append((obj.question_id, obj.document_id))
        return obj

    def flush(self):
        counter = [0]
        for obj in self._objs:
            if obj.__class__.__name__ == "QuestionReview":
                counter[0] += 1
                obj.id = counter[0]

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def test_persist_questions_links_via_source_document_ids_when_title_differs_from_filename():
    """TF-605: source_documents now carries the display title, which can
    legitimately differ from Document.original_filename. Linking must still
    succeed by going through source_document_ids instead."""
    from types import SimpleNamespace
    from tasks.question_tasks import _persist_questions

    fake_question = SimpleNamespace(
        question_text="Was ist die 3NF?",
        question_type="open_ended",
        options=None,
        correct_answer="Transitive Abhängigkeiten entfallen",
        explanation="…",
        difficulty="medium",
        source_chunks=[],
        # Title — deliberately does NOT match any original_filename below.
        source_documents=["Kapitel 3 — Normalisierung"],
        source_document_ids=[7],
        confidence_score=0.9,
        bloom_level=3,
    )

    session = _DocumentQueryStubSession(
        doc_rows=[(7, "2026-02-03_Skript_final_v2.pdf")]
    )

    _persist_questions(
        questions=[fake_question],
        exam_id="exam_tf605",
        topic="Normalisierung",
        language="de",
        user_id=42,
        institution_id=1,
        db=session,
    )

    assert session.merged == [(1, 7)], (
        "Expected QuestionSourceDocument(question_id=1, document_id=7) via "
        "source_document_ids — filename-based matching would have found "
        "nothing since the title doesn't match original_filename."
    )


def test_persist_questions_ignores_source_document_ids_outside_institution():
    """An id not present in this institution's Document table (e.g. the
    document was deleted between retrieval and persistence, or a
    cross-tenant id somehow slipped through) must not be linked."""
    from types import SimpleNamespace
    from tasks.question_tasks import _persist_questions

    fake_question = SimpleNamespace(
        question_text="Q?",
        question_type="open_ended",
        options=None,
        correct_answer="A",
        explanation="…",
        difficulty="medium",
        source_chunks=[],
        source_documents=["Ghost Document"],
        source_document_ids=[999],
        confidence_score=0.5,
        bloom_level=None,
    )

    session = _DocumentQueryStubSession(doc_rows=[(7, "Skript.pdf")])

    _persist_questions(
        questions=[fake_question],
        exam_id="exam_tf605_ghost",
        topic="t",
        language="de",
        user_id=1,
        institution_id=1,
        db=session,
    )

    assert session.merged == []


def test_persist_questions_falls_back_to_filename_matching_without_source_document_ids():
    """Callers that don't supply source_document_ids (older replayed jobs,
    non-Premium question sources) must still link via filename matching —
    the pre-TF-605 behavior, preserved as a fallback."""
    from types import SimpleNamespace
    from tasks.question_tasks import _persist_questions

    # Deliberately NO source_document_ids attribute -> tests getattr(..., None).
    fake_question = SimpleNamespace(
        question_text="Q?",
        question_type="open_ended",
        options=None,
        correct_answer="A",
        explanation="…",
        difficulty="medium",
        source_chunks=[],
        source_documents=["Skript.pdf"],
        confidence_score=0.5,
        bloom_level=None,
    )

    session = _DocumentQueryStubSession(doc_rows=[(7, "Skript.pdf")])

    _persist_questions(
        questions=[fake_question],
        exam_id="exam_tf605_fallback",
        topic="t",
        language="de",
        user_id=1,
        institution_id=1,
        db=session,
    )

    assert session.merged == [(1, 7)]


# ---------------------------------------------------------------------------
# TF-736: the outcome of a SUCCESS run is persisted on the job row, so an
# under-filled generation stays explainable after the Celery result expired.
# ---------------------------------------------------------------------------


_TF736_REQUEST = {
    "topic": "Knappes Material",
    "question_count": 15,
    "question_types": ["single_choice"],
    "difficulty": "medium",
    "language": "de",
    "document_ids": None,
    "context_chunks_per_question": 3,
    "prompt_config": None,
}


def _tf736_result(generated: int, quality_metrics: dict):
    @dataclasses.dataclass
    class FakeQuestion:
        question_text: str

    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    result = MagicMock()
    result.exam_id = "rag_exam_tf736"
    result.topic = "Knappes Material"
    result.questions = [FakeQuestion(question_text=f"q{i}") for i in range(generated)]
    result.context_summary = FakeContextSummary(query="Knappes Material")
    result.generation_time = 1.0
    result.quality_metrics = quality_metrics
    return result


def _run_task_with(result, task_id: str):
    from tasks.question_tasks import generate_questions_task

    generate_questions_task.update_state = MagicMock()
    generate_questions_task.push_request(id=task_id)
    try:
        with (
            patch("tasks.question_tasks.run_async", return_value=result),
            patch("tasks.question_tasks.RAGService", return_value=MagicMock()),
            patch("tasks.question_tasks._persist_questions", return_value=[1]),
        ):
            return generate_questions_task.run(_TF736_REQUEST, "42")
    finally:
        generate_questions_task.pop_request()


@pytest.fixture
def tf736_job_session(test_db):
    """A real job row plus a SessionLocal bound to the test transaction, so
    the task's own sessions read and write the same row the test inspects."""
    from sqlalchemy.orm import sessionmaker

    from models.auth import Institution, User
    from models.question_generation_job import QuestionGenerationJob

    institution = Institution(
        name="TF-736 University",
        slug="tf736-uni",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    test_db.add(institution)
    test_db.flush()
    user = User(
        email="tf736@example.com",
        first_name="TF",
        last_name="736",
        institution_id=institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.flush()
    test_db.add(
        QuestionGenerationJob(
            task_id="tf736-task",
            user_id=user.id,
            topic="Knappes Material",
            question_count=15,
        )
    )
    test_db.commit()

    bound = sessionmaker(
        bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
    )
    with patch("database.SessionLocal", bound):
        yield test_db


def _tf736_job(session):
    from models.question_generation_job import QuestionGenerationJob

    session.expire_all()
    return session.query(QuestionGenerationJob).filter_by(task_id="tf736-task").one()


def test_underfilled_generation_persists_outcome_on_job(tf736_job_session):
    """TF-736 test case 7: 6 of 15 → generated_question_count=6,
    context_limited=True on question_generation_jobs, status SUCCESS."""
    metrics = {
        "requested_question_count": 15,
        "generated_question_count": 6,
        "context_limited": True,
    }

    _run_task_with(_tf736_result(6, metrics), "tf736-task")

    job = _tf736_job(tf736_job_session)
    assert job.status == "SUCCESS"
    assert job.generated_question_count == 6
    assert job.context_limited is True


def test_complete_generation_persists_unlimited_outcome(tf736_job_session):
    """TF-736 test case 8: 15 of 15 → context_limited=False,
    generated_question_count == question_count."""
    metrics = {"requested_question_count": 15, "generated_question_count": 15}

    _run_task_with(_tf736_result(15, metrics), "tf736-task")

    job = _tf736_job(tf736_job_session)
    assert job.status == "SUCCESS"
    assert job.context_limited is False
    assert job.generated_question_count == job.question_count == 15


def test_underfilled_generation_with_zero_generated_questions(tf736_job_session):
    """Boundary: 0 of 15 generated must persist generated_question_count=0,
    not be treated as falsy/None (contextLimitOf on the frontend relies on
    the same `??`-not-`||` distinction)."""
    metrics = {
        "requested_question_count": 15,
        "generated_question_count": 0,
        "context_limited": True,
    }

    _run_task_with(_tf736_result(0, metrics), "tf736-task")

    job = _tf736_job(tf736_job_session)
    assert job.status == "SUCCESS"
    assert job.generated_question_count == 0
    assert job.context_limited is True


# === TF-964: no second set of questions after a crash between save and SUCCESS ===


@dataclasses.dataclass
class _TF964Question:
    question_text: str
    question_type: str = "single_choice"
    options: list = dataclasses.field(default_factory=lambda: ["a", "b", "c", "d"])
    correct_answer: str = "a"
    explanation: str = "weil"
    difficulty: str = "medium"
    source_chunks: list = dataclasses.field(default_factory=lambda: ["chunk-1"])
    source_documents: list = dataclasses.field(default_factory=list)
    confidence_score: float = 0.8


def _tf964_result(count: int = 3):
    @dataclasses.dataclass
    class FakeContextSummary:
        query: str

    result = MagicMock()
    result.exam_id = "rag_exam_tf964"
    result.topic = "Idempotenz"
    result.questions = [
        _TF964Question(question_text=f"Frage {i}?") for i in range(count)
    ]
    result.context_summary = FakeContextSummary(query="Idempotenz")
    result.generation_time = 1.0
    result.quality_metrics = {"requested_question_count": 3}
    return result


_TF964_TASK_ID = "tf964-task"


@pytest.fixture
def tf964_job_session(test_db):
    """A real job row plus a SessionLocal bound to the test transaction —
    same construction as ``tf736_job_session`` — so the guard, the real
    ``_persist_questions`` and the single commit all hit rows the test can
    count."""
    from sqlalchemy.orm import sessionmaker

    from models.auth import Institution, User
    from models.question_generation_job import QuestionGenerationJob

    institution = Institution(
        name="TF-964 University",
        slug="tf964-uni",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    test_db.add(institution)
    test_db.flush()
    user = User(
        email="tf964@example.com",
        first_name="TF",
        last_name="964",
        institution_id=institution.id,
        status="active",
    )
    test_db.add(user)
    test_db.flush()
    test_db.add(
        QuestionGenerationJob(
            task_id=_TF964_TASK_ID,
            user_id=user.id,
            topic="Idempotenz",
            question_count=3,
        )
    )
    test_db.commit()

    bound = sessionmaker(
        bind=test_db.get_bind(), join_transaction_mode="create_savepoint"
    )
    with patch("database.SessionLocal", bound):
        yield test_db, bound, user, institution


def _run_tf964(user, institution, *, redelivered=False, retries=0, rag=None):
    """Runs the task body as the worker would for ``_TF964_TASK_ID``.
    Returns (task result, RAGService mock)."""
    from tasks.question_tasks import generate_questions_task

    rag = rag if rag is not None else MagicMock()
    generate_questions_task.update_state = MagicMock()
    generate_questions_task.push_request(
        id=_TF964_TASK_ID,
        retries=retries,
        delivery_info={"redelivered": redelivered},
    )
    try:
        with (
            patch("tasks.question_tasks.run_async", return_value=_tf964_result()),
            patch("tasks.question_tasks.RAGService", rag),
        ):
            result = generate_questions_task.run(
                _TF736_REQUEST, str(user.id), institution_id=institution.id
            )
    finally:
        generate_questions_task.pop_request()
    return result, rag


def _tf964_job(session):
    from models.question_generation_job import QuestionGenerationJob

    session.expire_all()
    return session.query(QuestionGenerationJob).filter_by(task_id=_TF964_TASK_ID).one()


def _tf964_review_count(session):
    from models.question_review import QuestionReview

    return (
        session.query(QuestionReview)
        .filter(QuestionReview.exam_id == "rag_exam_tf964")
        .count()
    )


def test_single_commit_links_questions_and_finishes_job(tf964_job_session):
    """The first run stores the questions linked to the job, together with
    SUCCESS and the TF-736 outcome."""
    from models.question_review import QuestionReview

    session, _, user, institution = tf964_job_session

    result, _ = _run_tf964(user, institution)

    job = _tf964_job(session)
    assert job.status == "SUCCESS"
    assert job.generated_question_count == 3
    assert job.redelivery_count == 0
    linked = (
        session.query(QuestionReview.id)
        .filter(QuestionReview.generation_job_id == job.id)
        .order_by(QuestionReview.id)
        .all()
    )
    assert [row[0] for row in linked] == result["review_question_ids"]
    assert len(linked) == 3


@pytest.mark.parametrize(
    "second_run",
    [
        pytest.param({"redelivered": True}, id="redelivery"),
        pytest.param({"retries": 1}, id="autoretry"),
    ],
)
def test_second_run_after_commit_does_not_generate_again(tf964_job_session, second_run):
    """Acceptance «Weg B»: the worker dies after the commit (here: the task
    raises after ``_save_generation``, which is what an autoretry after the
    commit looks like), then the same task_id runs again — as a RabbitMQ
    redelivery or as Celery's autoretry. The second run must not call
    ``generate_rag_exam`` and must not add rows; it returns the stored
    result instead."""
    session, _, user, institution = tf964_job_session

    with patch(
        "tasks.question_tasks.dataclasses.asdict",
        side_effect=RuntimeError("worker lost after commit"),
    ):
        with pytest.raises(RuntimeError):
            _run_tf964(user, institution)
    assert _tf964_job(session).status == "SUCCESS"
    assert _tf964_review_count(session) == 3

    result, rag = _run_tf964(user, institution, **second_run)

    assert rag.return_value.generate_rag_exam.call_count == 0
    assert _tf964_review_count(session) == 3
    job = _tf964_job(session)
    assert job.status == "SUCCESS"
    assert len(result["review_question_ids"]) == 3
    assert [q["question_text"] for q in result["questions"]] == [
        "Frage 0?",
        "Frage 1?",
        "Frage 2?",
    ]


def test_redelivery_without_saved_questions_generates_and_counts(tf964_job_session):
    """A redelivery before anything was saved is a legitimate first attempt:
    it generates, and the redelivery is counted on the row."""
    session, _, user, institution = tf964_job_session

    _, rag = _run_tf964(user, institution, redelivered=True)

    assert rag.return_value.generate_rag_exam.call_count == 1
    job = _tf964_job(session)
    assert job.redelivery_count == 1
    assert job.status == "SUCCESS"
    assert _tf964_review_count(session) == 3


def test_autoretry_is_not_counted_as_redelivery(tf964_job_session):
    """Autoretries have their own budget (max_retries=4) and must not use up
    the redelivery limit."""
    session, _, user, institution = tf964_job_session

    _run_tf964(user, institution, retries=2)

    assert _tf964_job(session).redelivery_count == 0


def test_third_redelivery_without_questions_fails_job_and_rejects(tf964_job_session):
    """Acceptance «Obergrenze»: on the 3rd redelivery without saved
    questions the job goes to FAILURE and the message is rejected without
    requeue — no generation, no endless loop."""
    from celery.exceptions import Reject

    from tasks.question_tasks import _MAX_REDELIVERIES

    session, bound, user, institution = tf964_job_session
    assert _MAX_REDELIVERIES == 3
    db = bound()
    job = db.query(type(_tf964_job(session))).filter_by(task_id=_TF964_TASK_ID).one()
    job.redelivery_count = 2
    db.commit()
    db.close()

    with (
        patch("tasks.question_tasks.celery_app.backend.mark_as_failure") as mark,
        pytest.raises(Reject) as excinfo,
    ):
        _run_tf964(user, institution, redelivered=True)

    assert excinfo.value.requeue is False
    job = _tf964_job(session)
    assert job.status == "FAILURE"
    assert job.redelivery_count == 3
    assert _tf964_review_count(session) == 0
    _assert_marked_failure(mark)


def _assert_marked_failure(mark):
    """Celery's Reject writes nothing to the result backend; without this
    mirror the result stays STARTED and the progress WebSocket shows a
    running task forever."""
    from tasks.question_tasks import GenerationRejected

    mark.assert_called_once()
    assert mark.call_args.args[0] == _TF964_TASK_ID
    assert isinstance(mark.call_args.args[1], GenerationRejected)


def _set_tf964_status(session, bound, status):
    db = bound()
    job = db.query(type(_tf964_job(session))).filter_by(task_id=_TF964_TASK_ID).one()
    job.status = status
    db.commit()
    db.close()


@pytest.mark.parametrize("status", ["FAILURE", "REVOKED"])
@pytest.mark.parametrize("redelivered", [False, True])
def test_stale_message_for_given_up_job_is_rejected(
    tf964_job_session, status, redelivered
):
    """A job that is already FAILURE/REVOKED is never re-run — a retry gets
    a new job and task_id. A message that still arrives for it (e.g. one the
    watchdog gave up on while it waited in the queue) must not generate a
    second set next to the user's retry."""
    from celery.exceptions import Reject

    session, bound, user, institution = tf964_job_session
    _set_tf964_status(session, bound, status)
    rag = MagicMock()

    with (
        patch("tasks.question_tasks.celery_app.backend.mark_as_failure") as mark,
        pytest.raises(Reject) as excinfo,
    ):
        _run_tf964(user, institution, redelivered=redelivered, rag=rag)

    assert excinfo.value.requeue is False
    assert rag.return_value.generate_rag_exam.call_count == 0
    assert _tf964_review_count(session) == 0
    assert _tf964_job(session).status == status
    _assert_marked_failure(mark)


def test_reject_still_raised_when_celery_backend_is_down(tf964_job_session):
    """Mirroring into Celery's backend is best-effort; the message is still
    dropped."""
    from celery.exceptions import Reject

    session, bound, user, institution = tf964_job_session
    _set_tf964_status(session, bound, "FAILURE")

    with (
        patch(
            "tasks.question_tasks.celery_app.backend.mark_as_failure",
            side_effect=ConnectionError("redis down"),
        ),
        pytest.raises(Reject),
    ):
        _run_tf964(user, institution)


def _run_tf964_with_parallel_save(user, institution, parallel):
    """Runs the task while ``parallel`` acts on the job in the middle of the
    generation — like a second delivery of the same message on another
    worker (RabbitMQ consumer_timeout, broker reconnect)."""
    from tasks.question_tasks import generate_questions_task

    def generate(_coro):
        parallel()
        return _tf964_result()

    generate_questions_task.update_state = MagicMock()
    generate_questions_task.push_request(
        id=_TF964_TASK_ID, retries=0, delivery_info={"redelivered": False}
    )
    try:
        with (
            patch("tasks.question_tasks.run_async", side_effect=generate),
            patch("tasks.question_tasks.RAGService", MagicMock()),
        ):
            return generate_questions_task.run(
                _TF736_REQUEST, str(user.id), institution_id=institution.id
            )
    finally:
        generate_questions_task.pop_request()


def test_parallel_run_that_saved_first_wins(tf964_job_session):
    """Two deliveries of the same message both pass the start check. The
    one that saves second finds the job SUCCESS under its row lock, stores
    nothing and returns the first run's result."""
    from tasks.question_tasks import _save_generation

    session, _, user, institution = tf964_job_session
    first_ids = []

    def other_worker_saves():
        request = MagicMock(topic="T", language="de", tag_ids=[], framework_id=None)
        first_ids.extend(
            _save_generation(
                _TF964_TASK_ID, _tf964_result(), request, user.id, institution.id
            )
        )

    result = _run_tf964_with_parallel_save(user, institution, other_worker_saves)

    assert _tf964_review_count(session) == 3
    assert _tf964_job(session).status == "SUCCESS"
    assert result["review_question_ids"] == first_ids


def test_parallel_give_up_discards_the_run(tf964_job_session):
    """The job is given up while the run generates (e.g. the redelivery
    limit hit on another delivery): the run stores nothing and the message
    is rejected."""
    from celery.exceptions import Reject

    session, bound, user, institution = tf964_job_session

    with (
        patch("tasks.question_tasks.celery_app.backend.mark_as_failure") as mark,
        pytest.raises(Reject),
    ):
        _run_tf964_with_parallel_save(
            user, institution, lambda: _set_tf964_status(session, bound, "FAILURE")
        )

    assert _tf964_review_count(session) == 0
    assert _tf964_job(session).status == "FAILURE"
    _assert_marked_failure(mark)


@pytest.mark.parametrize(
    ("update", "expected"),
    [
        pytest.param({"return_value": True}, "WRITTEN", id="written"),
        pytest.param({"return_value": False}, "KEPT_SUCCESS", id="kept-success"),
        pytest.param(
            {"side_effect": RuntimeError("never raised as such")},
            None,
            id="unexpected-error-propagates",
        ),
    ],
)
def test_safe_update_job_status_reports_outcome(update, expected):
    """The watchdog tells a kept SUCCESS row from a written one (TF-964):
    only a real write counts as reconciled and is mirrored into Celery."""
    from tasks.question_tasks import JobStatusWrite, _safe_update_job_status

    with patch("tasks.question_tasks._update_job_status", **update):
        if expected is None:
            with pytest.raises(RuntimeError):
                _safe_update_job_status("task-1", "FAILURE")
        else:
            outcome = _safe_update_job_status("task-1", "FAILURE")
            assert outcome is JobStatusWrite[expected]


def test_second_redelivery_still_generates(tf964_job_session):
    """Boundary below the limit: the 2nd redelivery still runs."""
    session, bound, user, institution = tf964_job_session
    db = bound()
    job = db.query(type(_tf964_job(session))).filter_by(task_id=_TF964_TASK_ID).one()
    job.redelivery_count = 1
    db.commit()
    db.close()

    _, rag = _run_tf964(user, institution, redelivered=True)

    assert rag.return_value.generate_rag_exam.call_count == 1
    assert _tf964_job(session).redelivery_count == 2


@pytest.fixture
def tf964_committed(test_engine):
    """Job, user and institution committed for real, on their own
    connection — not inside ``test_db``'s outer transaction.

    The atomicity test needs this: with every session sharing one connection
    through savepoints, a rolled-back session also discards savepoints that
    other sessions opened and released after it began. A separate commit for
    the questions would then vanish in the test although it survives in
    production, and the test could not tell one commit from three. Rows are
    deleted afterwards."""
    from sqlalchemy.orm import sessionmaker

    from models.auth import Institution, User
    from models.question_generation_job import QuestionGenerationJob
    from models.question_review import QuestionReview, ReviewHistory

    factory = sessionmaker(bind=test_engine)
    db = factory()
    institution = Institution(
        name="TF-964 Atomic",
        slug="tf964-atomic",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    db.add(institution)
    db.flush()
    user = User(
        email="tf964-atomic@example.com",
        first_name="TF",
        last_name="964",
        institution_id=institution.id,
        status="active",
    )
    db.add(user)
    db.flush()
    db.add(
        QuestionGenerationJob(
            task_id=_TF964_TASK_ID,
            user_id=user.id,
            topic="Idempotenz",
            question_count=3,
        )
    )
    db.commit()
    ids = SimpleNamespace(id=user.id), SimpleNamespace(id=institution.id)
    try:
        with patch("database.SessionLocal", factory):
            yield factory, *ids
    finally:
        db.rollback()
        review_ids = [
            row[0]
            for row in db.query(QuestionReview.id).filter(
                QuestionReview.institution_id == institution.id
            )
        ]
        if review_ids:
            db.query(ReviewHistory).filter(
                ReviewHistory.question_id.in_(review_ids)
            ).delete(synchronize_session=False)
            db.query(QuestionReview).filter(QuestionReview.id.in_(review_ids)).delete(
                synchronize_session=False
            )
        db.query(QuestionGenerationJob).filter_by(task_id=_TF964_TASK_ID).delete()
        db.query(User).filter_by(id=user.id).delete()
        db.query(Institution).filter_by(id=institution.id).delete()
        db.commit()
        db.close()


def test_failed_save_commit_leaves_neither_questions_nor_success(tf964_committed):
    """Acceptance «Atomarität»: if the commit that writes SUCCESS fails, the
    questions are rolled back with it. The task raises so the autoretry can
    run it again — as a legitimate first attempt, since nothing was saved.

    Only the commit carrying the job's SUCCESS fails, not every commit: with
    separate commits for questions and status (the pre-TF-964 design), the
    questions' own commit goes through and this test turns red."""
    from sqlalchemy.exc import OperationalError

    from models.question_generation_job import QuestionGenerationJob

    factory, user, institution = tf964_committed

    def session_failing_the_success_commit():
        db = factory()
        real_commit = db.commit

        def commit():
            writes_success = any(
                isinstance(obj, QuestionGenerationJob) and obj.status == "SUCCESS"
                for obj in db.dirty
            )
            if writes_success:
                raise OperationalError("COMMIT", {}, Exception("connection lost"))
            real_commit()

        db.commit = commit
        return db

    with (
        patch("database.SessionLocal", session_failing_the_success_commit),
        # Old-design status writes retry with backoffs; don't wait for them.
        patch("tasks.question_tasks.time.sleep"),
    ):
        with pytest.raises(OperationalError):
            _run_tf964(user, institution)

    check = factory()
    try:
        job = _tf964_job(check)
        assert job.status != "SUCCESS"
        assert job.generated_question_count is None
        assert _tf964_review_count(check) == 0
    finally:
        check.close()


def test_missing_job_row_saves_questions_unlinked_and_logs_critical(mocker):
    """No job row (data-integrity issue): the questions are still saved —
    losing a finished generation would be worse — and it is logged CRITICAL,
    like the status writes do."""
    from tasks.question_tasks import _save_generation

    mock_logger = mocker.patch("tasks.question_tasks.logger")
    session = MagicMock()
    session.query.return_value.filter_by.return_value.with_for_update.return_value.first.return_value = None
    request = MagicMock(topic="T", language="de", tag_ids=[], framework_id=None)

    with (
        patch("database.SessionLocal", return_value=session),
        patch(
            "tasks.question_tasks._persist_questions", return_value=[7]
        ) as mock_persist,
    ):
        ids = _save_generation("ghost", _tf964_result(1), request, 1, None)

    assert ids == [7]
    assert mock_persist.call_args.kwargs["generation_job_id"] is None
    session.commit.assert_called_once()
    mock_logger.critical.assert_called_once()


def test_failure_after_commit_on_last_retry_keeps_success(tf964_job_session):
    """The task raises after its commit on the last retry: the generic
    except writes FAILURE — which must not replace the committed SUCCESS,
    or the panel offers a retry that generates the set a second time."""
    from tasks.question_tasks import generate_questions_task

    session, _, user, institution = tf964_job_session

    with (
        patch.dict(generate_questions_task.retry_kwargs, {"max_retries": 0}),
        patch(
            "tasks.question_tasks.dataclasses.asdict",
            side_effect=RuntimeError("worker lost after commit"),
        ),
    ):
        with pytest.raises(RuntimeError):
            _run_tf964(user, institution)

    assert _tf964_job(session).status == "SUCCESS"
    assert _tf964_review_count(session) == 3


@pytest.mark.parametrize("status", ["FAILURE", "REVOKED", "PENDING"])
def test_try_update_job_status_never_downgrades_success(tf964_job_session, status):
    """Every status writer (task, watchdog, /active-tasks phantom sync) goes
    through _try_update_job_status; a SUCCESS row stays SUCCESS."""
    from tasks.question_tasks import _try_update_job_status

    session, bound, _, _ = tf964_job_session
    db = bound()
    job = db.query(type(_tf964_job(session))).filter_by(task_id=_TF964_TASK_ID).one()
    job.status = "SUCCESS"
    db.commit()
    db.close()

    assert _try_update_job_status(_TF964_TASK_ID, status) is False

    assert _tf964_job(session).status == "SUCCESS"
