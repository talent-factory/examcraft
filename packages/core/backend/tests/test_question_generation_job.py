"""Tests für QuestionGenerationJob DB-Modell"""


def test_question_generation_job_model_importable():
    """Modell kann importiert werden"""
    from models.question_generation_job import QuestionGenerationJob

    assert QuestionGenerationJob.__tablename__ == "question_generation_jobs"


def test_question_generation_job_columns():
    """Modell hat die erwarteten Spalten"""
    from models.question_generation_job import QuestionGenerationJob

    columns = {c.name for c in QuestionGenerationJob.__table__.columns}
    assert "id" in columns
    assert "task_id" in columns
    assert "user_id" in columns
    assert "created_at" in columns


def test_task_id_is_unique():
    """task_id Spalte hat unique constraint"""
    from models.question_generation_job import QuestionGenerationJob

    task_id_col = QuestionGenerationJob.__table__.columns["task_id"]
    assert task_id_col.unique is True


def test_task_id_is_indexed():
    """task_id Spalte ist indexiert"""
    from models.question_generation_job import QuestionGenerationJob

    task_id_col = QuestionGenerationJob.__table__.columns["task_id"]
    assert task_id_col.index is True


def test_question_generation_job_has_metadata_columns():
    """New columns for parallel generation display and recovery."""
    from models.question_generation_job import QuestionGenerationJob

    columns = {c.name for c in QuestionGenerationJob.__table__.columns}
    assert "topic" in columns
    assert "question_count" in columns
    assert "status" in columns


def test_question_generation_job_status_default():
    """Status defaults to PENDING."""
    from models.question_generation_job import QuestionGenerationJob

    job = QuestionGenerationJob(task_id="test-123", user_id=1)
    assert job.status == "PENDING"
