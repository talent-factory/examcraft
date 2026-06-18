"""TF-435: MoodleFeedbackPushJob model defaults."""

import pytest

from models.exam import Exam
from models.submission import MoodleFeedbackPushJob


def test_push_job_defaults(test_db, test_institution):
    exam = Exam(institution_id=test_institution.id, title="Testprüfung")
    test_db.add(exam)
    test_db.flush()

    job = MoodleFeedbackPushJob(
        institution_id=test_institution.id,
        exam_id=exam.id,
        transport="plugin",
        triggered_by=None,
    )
    test_db.add(job)
    test_db.flush()

    assert job.status == "queued"
    assert job.students_total == 0
    assert job.students_pushed == 0
    assert job.students_skipped == 0
    assert job.students_failed == 0
    assert job.error_log is None
    assert job.transport == "plugin"


def test_status_validator_rejects_unknown_value():
    """@validates guards against a typo'd status before it hits the DB CHECK."""
    job = MoodleFeedbackPushJob()
    with pytest.raises(ValueError):
        job.status = "bogus"


def test_transport_validator_rejects_unknown_value():
    job = MoodleFeedbackPushJob()
    with pytest.raises(ValueError):
        job.transport = "ftp"


def test_transport_validator_allows_none():
    """transport is nullable until a transport is chosen — None must pass."""
    job = MoodleFeedbackPushJob()
    job.transport = None  # no raise
    assert job.transport is None
