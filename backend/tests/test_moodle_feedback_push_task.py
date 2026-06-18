"""TF-435: Celery task delegates to the service."""

from unittest.mock import patch

from models.exam import Exam
from models.submission import MoodleFeedbackPushJob
from tasks.moodle_feedback_push_task import push_moodle_feedback


def test_task_invokes_service(test_db, test_institution):
    exam = Exam(institution_id=test_institution.id, title="X")
    test_db.add(exam)
    test_db.flush()
    job = MoodleFeedbackPushJob(institution_id=test_institution.id, exam_id=exam.id)
    test_db.add(job)
    test_db.flush()
    with (
        patch("tasks.moodle_feedback_push_task.SessionLocal", return_value=test_db),
        patch.object(test_db, "close"),
        patch("tasks.moodle_feedback_push_task.MoodleFeedbackPushService") as svc,
    ):
        push_moodle_feedback.run(job_id=job.id, force_transport=None)
    svc.return_value.run.assert_called_once_with(job_id=job.id, force_transport=None)
