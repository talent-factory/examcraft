"""
Tests for the generate_questions_task Celery task.
Tests task dispatch, progress steps, and the return format.
"""

import dataclasses
import sys
from unittest.mock import MagicMock

# Mock system-level dependencies before any project imports
if "magic" not in sys.modules:
    sys.modules["magic"] = MagicMock()

from unittest.mock import patch


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
    assert "Fragengenerierung" in first["message"] or "Starte" in first["message"]


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

    # TF-359: capture the Sentry scope tags set by the task so a regression that
    # drops user_id/topic tagging fails here (the lines execute either way).
    captured_tags: dict[str, str] = {}

    with (
        patch("tasks.question_tasks.run_async", return_value=mock_result),
        patch("tasks.question_tasks.RAGService", return_value=mock_rag_service),
        patch("tasks.question_tasks._persist_questions", return_value=[1]),
        patch("tasks.question_tasks._safe_update_job_status"),
        patch(
            "tasks.question_tasks.sentry_sdk.set_tag",
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


def test_safe_update_job_status_swallows_job_status_update_error_and_logs(mocker):
    """When _update_job_status raises JobStatusUpdateError, _safe_update_job_status
    logs at CRITICAL level with traceback (logger.critical + exc_info=True), and
    does NOT re-raise.

    mocker.patch directly on the module logger instead of caplog: pytest 7.4.3
    (the CI-pinned version) leaves caplog.records empty here; the direct mock
    is version-independent.
    """
    from tasks.question_tasks import JobStatusUpdateError, _safe_update_job_status

    mock_logger = mocker.patch("tasks.question_tasks.logger")
    err = JobStatusUpdateError("task-x", "FAILURE", 4, RuntimeError("simulated cause"))

    with patch("tasks.question_tasks._update_job_status", side_effect=err):
        _safe_update_job_status("task-x", "FAILURE")  # no exception

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
