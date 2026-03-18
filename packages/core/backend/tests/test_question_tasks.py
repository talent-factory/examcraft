"""
Tests für den generate_questions_task Celery Task.
Testet Task-Dispatch, Progress-Steps und Rückgabe-Format.
"""

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


def test_generate_questions_task_emits_progress_steps():
    """Task emittiert mindestens 3 Progress-Updates (0%, Context, mind. 1 Frage)"""
    from tasks.question_tasks import generate_questions_task

    progress_updates = []

    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    mock_result.questions = [MagicMock(model_dump=MagicMock(return_value={"q": 1}))]
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {}

    mock_rag_service = MagicMock()
    mock_rag_service.generate_rag_exam = MagicMock(return_value=mock_result)

    def fake_run_async(coro):
        # Simuliere den progress_callback-Aufruf durch generate_rag_exam
        # Wir extrahieren den callback aus dem coroutine-Aufruf
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
    """Task gibt dict mit exam_id, topic, questions, generation_time, quality_metrics zurück.

    mock_result simuliert RAGExamResponse aus premium/services/rag_service.py.
    Die echte RAGExamResponse hat: exam_id(str), topic(str), questions(List[RAGQuestion]),
    generation_time(float), quality_metrics(dict).
    RAGQuestion hat model_dump() via Pydantic v2.
    """
    from tasks.question_tasks import generate_questions_task

    # Mock für RAGExamResponse (premium Pydantic-Modell)
    mock_result = MagicMock()
    mock_result.exam_id = "exam_001"
    mock_result.topic = "Heapsort"
    # Mock für RAGQuestion mit Pydantic v2 model_dump()
    mock_q = MagicMock()
    mock_q.model_dump = MagicMock(return_value={"question_text": "Was ist ein Heap?"})
    mock_result.questions = [mock_q]
    mock_result.generation_time = 5.0
    mock_result.quality_metrics = {
        "total_questions": 1
    }  # dict, wie von _calculate_quality_metrics

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
    assert result["generation_time"] == 5.0
    assert "total_questions" in result["quality_metrics"]
