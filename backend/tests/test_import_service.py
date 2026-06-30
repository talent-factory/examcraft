"""Integration tests for ImportService.

Covers idempotency, per-row tolerance, submission aggregation and
deterministic grading of MC + true/false answers, plus the
``manual_override`` sacrosanct rule and mid-pipeline rollback semantics.
"""

from __future__ import annotations

import json
from datetime import date

import pytest
from sqlalchemy.orm import Session

from models.auth import Institution
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.submission import (
    Attempt,
    AttemptAnswer,
    Grade,
    ImportJob,
    Submission,
)
from models.student import Student
from enums import ImportJobStatus
from services.import_service import ImportService, ImportValidationError


# ---------------------------------------------------------------------------
# Test-Fixtures: Institution + Exam mit gemischten Frage-Typen
# ---------------------------------------------------------------------------


@pytest.fixture
def institution(test_db: Session) -> Institution:
    inst = Institution(
        name="TF-333 Test Inst",
        slug="tf333-test",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.commit()
    test_db.refresh(inst)
    return inst


@pytest.fixture
def exam_with_questions(test_db: Session, institution: Institution) -> Exam:
    """Prüfung mit 1 MC, 1 W/F, 1 offene Frage. Punkte: 4 + 1 + 5 = 10."""
    mc_q = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        options=["A) Zürich", "B) Bern", "C) Genf", "D) Basel"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    tf_q = QuestionReview(
        question_text="Bern ist die Hauptstadt der Schweiz.",
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    open_q = QuestionReview(
        question_text="Erkläre Föderalismus in der Schweiz in 3 Sätzen.",
        question_type="open_ended",
        correct_answer="Drei-Ebenen-System aus Bund, Kantonen, Gemeinden …",
        difficulty="medium",
        topic="Politik",
        institution_id=institution.id,
    )
    test_db.add_all([mc_q, tf_q, open_q])
    test_db.flush()

    exam = Exam(
        title="Allgemeinbildung",
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=10.0,
        status="finalized",
        language="de",
        institution_id=institution.id,
    )
    test_db.add(exam)
    test_db.flush()

    test_db.add_all(
        [
            ExamQuestion(
                exam_id=exam.id,
                question_id=mc_q.id,
                position=1,
                points=4.0,
            ),
            ExamQuestion(
                exam_id=exam.id,
                question_id=tf_q.id,
                position=2,
                points=1.0,
            ),
            ExamQuestion(
                exam_id=exam.id,
                question_id=open_q.id,
                position=3,
                points=5.0,
            ),
        ]
    )
    test_db.commit()
    test_db.refresh(exam)
    return exam


# Question texts mirror ``exam_with_questions`` verbatim so the JSON
# driver's exact-match stage resolves each ``frageN`` to a unique exam
# question (TF-423: mapping is by question text, not column position).
_Q1 = "Hauptstadt der Schweiz?"
_Q2 = "Bern ist die Hauptstadt der Schweiz."
_Q3 = "Erkläre Föderalismus in der Schweiz in 3 Sätzen."


def _attempt_row(
    *,
    email: str,
    vorname: str = "Anna",
    nachname: str = "Beispiel",
    begonnen: str | None = "2026-05-15 09:00:00",
    beendet: str | None = "2026-05-15 09:30:00",
    a1: str = "Bern",
    a2: str = "wahr",
    a3: str = "Antworttext",
) -> dict:
    """One student attempt as the Moodle JSON plugin export shapes it."""
    row: dict[str, object] = {
        "vorname": vorname,
        "nachname": nachname,
        "e-mail-adresse": email,
    }
    if begonnen is not None:
        row["begonnen"] = begonnen
    if beendet is not None:
        row["beendet"] = beendet
    row.update(
        {
            "frage1": _Q1,
            "antwort1": a1,
            "frage2": _Q2,
            "antwort2": a2,
            "frage3": _Q3,
            "antwort3": a3,
        }
    )
    return row


def _json_source(rows: list[dict]) -> bytes:
    """Serialise like the plugin export: outer ``[[ {row}, ... ]]`` envelope."""
    return json.dumps([rows]).encode("utf-8")


def _json_two_students(*, anna_q1: str = "Bern", anna_q2: str = "wahr") -> bytes:
    """Zwei Studierende mit je einem Versuch.

    Anna: anpassbare Antworten. Bruno: alles falsch.
    """
    return _json_source(
        [
            _attempt_row(email="anna@example.org", a1=anna_q1, a2=anna_q2),
            _attempt_row(
                vorname="Bruno",
                nachname="Muster",
                email="bruno@example.org",
                beendet="2026-05-15 09:25:00",
                a1="Zürich",
                a2="falsch",
                a3="",
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Preview (kein Persistenz)
# ---------------------------------------------------------------------------


def test_preview_does_not_persist(test_db: Session, exam_with_questions: Exam) -> None:
    service = ImportService(test_db)
    payload = service.preview(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
    )

    assert len(payload.students) == 2
    assert len(payload.attempts) == 2
    assert test_db.query(Student).count() == 0
    assert test_db.query(Attempt).count() == 0
    assert test_db.query(ImportJob).count() == 0


def test_validate_rejects_mismatched_exam_id(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Payload-exam_id != exam.id ⇒ Hard-Failure (Spec 5.1 Schritt 2)."""
    from services.import_drivers import ImportPayload

    payload = ImportPayload(
        exam_id=exam_with_questions.id + 99,  # absichtliche Diskrepanz
        driver_name="moodle_json",
    )
    with pytest.raises(ImportValidationError, match="exam_id"):
        ImportService._validate_payload(payload, exam_with_questions)


def test_validate_rejects_question_id_outside_exam(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """AttemptAnswer mit fremder exam_question_id ⇒ Hard-Failure."""
    from services.import_drivers import (
        AnswerRecord,
        AttemptRecord,
        ImportPayload,
    )

    payload = ImportPayload(
        exam_id=exam_with_questions.id,
        driver_name="moodle_json",
        attempts=[
            AttemptRecord(
                student_external_id="anna@example.org",
                attempt_number=1,
                answers=[AnswerRecord(exam_question_id=99999)],
            )
        ],
    )
    with pytest.raises(ImportValidationError) as excinfo:
        ImportService._validate_payload(payload, exam_with_questions)
    assert excinfo.value.issues
    assert any("exam_question_id" in iss for iss in excinfo.value.issues)


def test_validate_rejects_empty_attempts(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Zero-attempt payload ⇒ Hard-Failure, not a hollow 0-row success.

    A source that parses to no attempts must fail loud at the validation
    boundary so the job is recorded as failed — otherwise it reaches
    _finalise_job as status=succeeded / rows_processed=0, the same
    misleading-success class TF-500 set out to eliminate.
    """
    from services.import_drivers import ImportPayload

    payload = ImportPayload(
        exam_id=exam_with_questions.id,
        driver_name="moodle_json",
        attempts=[],
    )
    with pytest.raises(ImportValidationError, match="keine Versuche"):
        ImportService._validate_payload(payload, exam_with_questions)


# ---------------------------------------------------------------------------
# Commit + Grading
# ---------------------------------------------------------------------------


def test_commit_persists_students_attempts_grades(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
        source_metadata={"filename": "klasse-fs26.json"},
    )

    assert job.status == "succeeded"
    assert job.rows_processed == 2
    assert job.rows_failed == 0
    assert test_db.query(Student).count() == 2
    assert test_db.query(Submission).count() == 2
    assert test_db.query(Attempt).count() == 2
    # 2 Versuche × 3 Antworten = 6 AttemptAnswers + 6 Grades
    assert test_db.query(AttemptAnswer).count() == 6
    assert test_db.query(Grade).count() == 6


def test_import_sets_grading_progress_counters(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """TF-428: the job carries graded_total/graded_done so the UI can show
    "n/total bewertet" while grading runs. On a clean import both reach the
    number of graded submissions."""
    service = ImportService(test_db)
    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
        source_metadata={"filename": "klasse-fs26.json"},
    )

    assert job.graded_total == 2
    assert job.graded_done == 2


def test_import_emits_live_progress_updates(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """TF-428: progress is written live (own short transaction) while grading
    runs, not only as the committed terminal value. The kickoff call announces
    the total and resets graded_done to 0; a later call reports completion.
    Asserting the call sequence covers the live path the counter test cannot
    (it only sees the final committed row)."""
    service = ImportService(test_db)
    calls: list[dict] = []
    original = service._update_import_progress

    def _record(job_id: int, **kwargs: object) -> None:
        calls.append(kwargs)
        original(job_id, **kwargs)  # type: ignore[arg-type]

    service._update_import_progress = _record  # type: ignore[assignment, method-assign]

    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
        source_metadata={"filename": "klasse-fs26.json"},
    )

    # Kickoff: total announced, done reset to 0.
    assert {"graded_total": 2, "graded_done": 0} in calls
    # Live increment reaches completion (done == total).
    assert any(call.get("graded_done") == 2 for call in calls)


def test_anna_gets_full_mc_and_tf_points(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),  # Anna: Bern + wahr
        triggered_by=None,
    )

    anna = (
        test_db.query(Student).filter(Student.external_id == "anna@example.org").one()
    )
    submission = (
        test_db.query(Submission)
        .filter(
            Submission.exam_id == exam_with_questions.id,
            Submission.student_id == anna.id,
        )
        .one()
    )

    # MC (4 P.) + W/F (1 P.) korrekt; offene Frage stub = 0 P.
    assert submission.total_points_awarded == 5.0
    assert submission.total_points_max == 10.0
    assert submission.percentage == pytest.approx(50.0)
    # offene Frage vorhanden ⇒ pending_review (Phase-2-Routing)
    assert submission.grade_status == "pending_review"


def test_bruno_gets_zero_points_when_wrong(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )

    bruno = (
        test_db.query(Student).filter(Student.external_id == "bruno@example.org").one()
    )
    submission = (
        test_db.query(Submission).filter(Submission.student_id == bruno.id).one()
    )
    assert submission.total_points_awarded == 0.0
    assert submission.percentage == pytest.approx(0.0)


def test_grades_have_correct_status_and_correctness(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )
    grades = test_db.query(Grade).all()
    assert all(g.status == "proposed" for g in grades)
    # Genau eine richtige MC + eine richtige W/F (Annas Versuch):
    correct_count = sum(1 for g in grades if g.is_correct is True)
    open_ended_count = sum(1 for g in grades if g.is_correct is None)
    assert correct_count == 2
    assert open_ended_count == 2  # offene Frage × 2 Studis


# ---------------------------------------------------------------------------
# Idempotenz (Spec DoD)
# ---------------------------------------------------------------------------


def test_re_import_same_csv_creates_no_duplicates(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    csv_text = _json_two_students()

    job1 = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=csv_text,
        triggered_by=None,
    )
    assert job1.status == "succeeded"

    # Zweiter Import mit identischer CSV
    job2 = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=csv_text,
        triggered_by=None,
    )
    assert job2.status == "succeeded"
    # All-duplicates outcome must be durably distinguishable from a real
    # import at the job level (TF-500): nothing persisted, and the skip count
    # is surfaced into source_metadata so the API/UI can render the "info"
    # banner instead of a hollow green "0 verarbeitet" success. The frontend
    # test mocks this contract — assert the backend actually emits it.
    assert job2.rows_processed == 0
    assert (job2.source_metadata or {}).get("attempts_skipped_idempotent") == 2
    # Keine zusätzlichen Versuche / Antworten / Grades:
    assert test_db.query(Attempt).count() == 2
    assert test_db.query(AttemptAnswer).count() == 6
    assert test_db.query(Grade).count() == 6
    assert test_db.query(Student).count() == 2


def test_second_import_with_new_attempt_adds_only_delta(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Bestehende Versuche idempotent skipped; nur neue Versuche werden
    persistiert."""
    service = ImportService(test_db)

    json_v1 = _json_two_students()
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_v1,
        triggered_by=None,
    )

    # v2: Anna macht zusätzlich einen zweiten Versuch (anderer
    # Started-Zeitstempel) — Bruno bleibt gleich. Reihenfolge erhält die
    # Versuchs-Nummerierung (1 vor 2), sodass der erste Versuch idempotent
    # übersprungen und nur der zweite ergänzt wird.
    json_v2 = _json_source(
        [
            _attempt_row(email="anna@example.org"),
            _attempt_row(
                email="anna@example.org",
                begonnen="2026-05-16 10:00:00",
                beendet="2026-05-16 10:25:00",
                a3="Bessere Antwort",
            ),
            _attempt_row(
                vorname="Bruno",
                nachname="Muster",
                email="bruno@example.org",
                beendet="2026-05-15 09:25:00",
                a1="Zürich",
                a2="falsch",
                a3="",
            ),
        ]
    )
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_v2,
        triggered_by=None,
    )

    anna = (
        test_db.query(Student).filter(Student.external_id == "anna@example.org").one()
    )
    anna_attempts = (
        test_db.query(Attempt)
        .join(Submission, Submission.id == Attempt.submission_id)
        .filter(Submission.student_id == anna.id)
        .all()
    )
    assert len(anna_attempts) == 2  # erster Versuch + neuer Versuch
    bruno_attempts = (
        test_db.query(Attempt)
        .join(Submission, Submission.id == Attempt.submission_id)
        .join(Student, Submission.student_id == Student.id)
        .filter(Student.external_id == "bruno@example.org")
        .all()
    )
    assert len(bruno_attempts) == 1  # idempotent skipped


def _make_exam_with_same_questions(
    test_db: Session, institution: Institution, *, title: str
) -> Exam:
    """Zweite Prüfung mit denselben Fragetexten wie ``exam_with_questions``.

    Eigene ``QuestionReview``-Zeilen mit identischem Text — der JSON-Driver
    matcht über Text, nicht über IDs, also mappt dieselbe Quelle auf beide
    Prüfungen. Spiegelt die Prod-Realität (zwei separate Prüfungen mit
    identischen Fragen in derselben Institution).
    """
    mc_q = QuestionReview(
        question_text=_Q1,
        question_type="single_choice",
        options=["A) Zürich", "B) Bern", "C) Genf", "D) Basel"],
        correct_answer="Bern",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    tf_q = QuestionReview(
        question_text=_Q2,
        question_type="true_false",
        correct_answer="wahr",
        difficulty="easy",
        topic="Geografie",
        institution_id=institution.id,
    )
    open_q = QuestionReview(
        question_text=_Q3,
        question_type="open_ended",
        correct_answer="Drei-Ebenen-System aus Bund, Kantonen, Gemeinden …",
        difficulty="medium",
        topic="Politik",
        institution_id=institution.id,
    )
    test_db.add_all([mc_q, tf_q, open_q])
    test_db.flush()

    exam = Exam(
        title=title,
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=10.0,
        status="finalized",
        language="de",
        institution_id=institution.id,
    )
    test_db.add(exam)
    test_db.flush()
    test_db.add_all(
        [
            ExamQuestion(exam_id=exam.id, question_id=mc_q.id, position=1, points=4.0),
            ExamQuestion(exam_id=exam.id, question_id=tf_q.id, position=2, points=1.0),
            ExamQuestion(
                exam_id=exam.id, question_id=open_q.id, position=3, points=5.0
            ),
        ]
    )
    test_db.commit()
    test_db.refresh(exam)
    return exam


def test_same_source_attempt_imports_into_two_exams_same_institution(
    test_db: Session, exam_with_questions: Exam, institution: Institution
) -> None:
    """TF-500: Derselbe Moodle-Attempt muss in ZWEI verschiedene Prüfungen
    derselben Institution importiert werden können.

    Regression: Der Idempotenz-Check dedupte institutions-weit auf
    ``(institution_id, source, source_attempt_id)`` — ohne ``exam_id``, und die
    DB-Unique-Constraint war ebenso institutions-scoped. Ein zweiter Import
    derselben Moodle-Resultate in eine *andere* Prüfung lief dadurch still leer
    (``rows_processed=0, status=succeeded``), die Prüfung blieb leer. Der
    Idempotenz-Schutz darf nur denselben Attempt in dieselbe Prüfung
    deduplizieren, nicht prüfungsübergreifend.
    """
    service = ImportService(test_db)
    source = _json_two_students()

    job_a = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=source,
        triggered_by=None,
    )
    assert job_a.rows_processed == 2

    exam_b = _make_exam_with_same_questions(
        test_db, institution, title="Zweite Prüfung gleiche Fragen"
    )

    # Identische Quelle (gleiche source_attempt_ids) in die ZWEITE Prüfung.
    job_b = service.commit(
        exam=exam_b,
        driver_name="moodle_json",
        source=source,
        triggered_by=None,
    )
    assert job_b.status == "succeeded"
    # Vor dem Fix: 0 (alle als institutions-weites Duplikat übersprungen).
    assert job_b.rows_processed == 2

    subs_a = (
        test_db.query(Submission)
        .filter(Submission.exam_id == exam_with_questions.id)
        .count()
    )
    subs_b = test_db.query(Submission).filter(Submission.exam_id == exam_b.id).count()
    assert subs_a == 2
    assert subs_b == 2


# ---------------------------------------------------------------------------
# Partial Failures + error_log
# ---------------------------------------------------------------------------


def test_partial_failure_when_some_rows_invalid(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Eine Zeile ohne E-Mail → row error; Job-Status partial."""
    service = ImportService(test_db)
    json_with_bad_row = _json_source(
        [
            {"e-mail-adresse": ""},  # leere E-Mail → error (Index 0)
            _attempt_row(email="anna@example.org"),
        ]
    )
    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_with_bad_row,
        triggered_by=None,
    )
    assert job.status == "partial"
    assert job.rows_failed == 1
    assert job.rows_processed == 1
    assert job.error_log
    assert job.error_log[0]["row_index"] == 0


def test_failed_job_when_all_rows_invalid(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    # Rows carry frageN (so the column map resolves) but no e-mail → every
    # row is an identity error: 0 processed, 2 failed → job failed.
    bad_row = {"e-mail-adresse": "", "frage1": _Q1, "antwort1": "A"}
    json_all_bad = _json_source([dict(bad_row), dict(bad_row)])
    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_all_bad,
        triggered_by=None,
    )
    assert job.status == "failed"
    assert job.rows_processed == 0
    assert job.rows_failed == 2


# ---------------------------------------------------------------------------
# Driver-Errors → Job-Status failed
# ---------------------------------------------------------------------------


def test_empty_csv_marks_job_failed(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    with pytest.raises(Exception):
        service.commit(
            exam=exam_with_questions,
            driver_name="moodle_json",
            source="",
            triggered_by=None,
        )
    # ImportJob existiert + ist auf failed
    job = test_db.query(ImportJob).order_by(ImportJob.id.desc()).first()
    assert job is not None
    assert job.status == "failed"


def test_unknown_driver_raises(test_db: Session, exam_with_questions: Exam) -> None:
    service = ImportService(test_db)
    with pytest.raises(ImportValidationError, match="Unbekannter Driver"):
        service.commit(
            exam=exam_with_questions,
            driver_name="ilias_csv",
            source="dummy",
            triggered_by=None,
        )


# ---------------------------------------------------------------------------
# Scoring-Strategy für Mehrfachversuche
# ---------------------------------------------------------------------------


def test_latest_strategy_picks_most_recent_attempt(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    json_two_attempts = _json_source(
        [
            # Versuch 1: alles falsch
            _attempt_row(email="anna@example.org", a1="Zürich", a2="falsch", a3=""),
            # Versuch 2: korrekt
            _attempt_row(
                email="anna@example.org",
                begonnen="2026-05-16 10:00:00",
                beendet="2026-05-16 10:25:00",
                a1="Bern",
                a2="wahr",
                a3="Antwort",
            ),
        ]
    )
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_two_attempts,
        triggered_by=None,
    )
    submission = (
        test_db.query(Submission)
        .join(Student, Student.id == Submission.student_id)
        .filter(Student.external_id == "anna@example.org")
        .one()
    )
    # Default 'latest' → der zweite Versuch zählt:
    assert submission.total_points_awarded == 5.0  # MC 4 + W/F 1


def test_best_strategy_picks_highest_scoring_attempt(
    test_db: Session, exam_with_questions: Exam
) -> None:
    service = ImportService(test_db)
    json_two_attempts = _json_source(
        [
            _attempt_row(email="anna@example.org", a1="Bern", a2="wahr", a3="Antwort"),
            _attempt_row(
                email="anna@example.org",
                begonnen="2026-05-16 10:00:00",
                beendet="2026-05-16 10:25:00",
                a1="Zürich",
                a2="falsch",
                a3="",
            ),
        ]
    )
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_two_attempts,
        triggered_by=None,
    )
    submission = (
        test_db.query(Submission)
        .join(Student, Student.id == Submission.student_id)
        .filter(Student.external_id == "anna@example.org")
        .one()
    )
    # Strategy umstellen + erneut grading auslösen:
    submission.scoring_strategy = "best"
    test_db.flush()
    service.grading_service.grade_submission(submission.id)
    test_db.refresh(submission)
    assert submission.total_points_awarded == 5.0  # erster Versuch wins


# ---------------------------------------------------------------------------
# Multi-Tenancy: Studierende sind institution-scoped
# ---------------------------------------------------------------------------


def test_same_external_id_in_different_institutions_are_separate(
    test_db: Session,
) -> None:
    """Zwei Institutions ⇒ zwei voneinander unabhängige Student-Records
    auch bei identischer external_id."""
    inst_a = Institution(
        name="Inst A",
        slug="inst-a",
        subscription_tier="free",
        max_users=1,
        max_documents=5,
        max_questions_per_month=20,
    )
    inst_b = Institution(
        name="Inst B",
        slug="inst-b",
        subscription_tier="free",
        max_users=1,
        max_documents=5,
        max_questions_per_month=20,
    )
    test_db.add_all([inst_a, inst_b])
    test_db.flush()

    s_a = Student(institution_id=inst_a.id, external_id="overlap@example.org")
    s_b = Student(institution_id=inst_b.id, external_id="overlap@example.org")
    test_db.add_all([s_a, s_b])
    test_db.commit()

    students = (
        test_db.query(Student)
        .filter(Student.external_id == "overlap@example.org")
        .all()
    )
    assert len(students) == 2
    assert {s.institution_id for s in students} == {inst_a.id, inst_b.id}


# ---------------------------------------------------------------------------
# manual_override sacrosanct (Spec 6.6)
# ---------------------------------------------------------------------------


def test_manual_override_grades_are_preserved_on_reimport(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """A teacher's manual_override grade must survive a re-import and a
    re-grade cycle — Spec 6.6 says the human always wins."""
    service = ImportService(test_db)
    csv_text = _json_two_students()  # Anna correct, Bruno wrong
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=csv_text,
        triggered_by=None,
    )

    bruno = (
        test_db.query(Student).filter(Student.external_id == "bruno@example.org").one()
    )
    bruno_submission = (
        test_db.query(Submission).filter(Submission.student_id == bruno.id).one()
    )
    bruno_attempt = bruno_submission.attempts[0]
    mc_answer = next(a for a in bruno_attempt.answers if a.given_answer == "Zürich")
    grade = mc_answer.grade
    assert grade is not None and grade.points_awarded == 0.0

    # Teacher manually marks the answer as correct.
    grade.status = "manual_override"
    grade.points_awarded = 4.0
    grade.is_correct = True
    grade.reviewer_note = "anerkannt nach Rückfrage"
    test_db.commit()

    # Re-import the same CSV; grading runs again.
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=csv_text,
        triggered_by=None,
    )

    test_db.refresh(grade)
    assert grade.status == "manual_override"
    assert grade.points_awarded == 4.0
    assert grade.is_correct is True
    assert grade.reviewer_note == "anerkannt nach Rückfrage"

    # Also exercise the direct grade_submission path.
    service.grading_service.grade_submission(bruno_submission.id)
    test_db.refresh(grade)
    assert grade.status == "manual_override"
    assert grade.points_awarded == 4.0


# ---------------------------------------------------------------------------
# Mid-pipeline rollback: failure mid-grading must not leak partial data
# ---------------------------------------------------------------------------


def test_per_submission_grading_failure_isolates_to_error_log(
    test_db: Session, exam_with_questions: Exam, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When grade_submission raises for one student, the rest of the
    import must still go through. The failure lands in job.error_log
    with step=grading rather than rolling back the whole CSV."""
    service = ImportService(test_db)

    def _boom(_self, _submission_id, **_kwargs):
        raise RuntimeError("simulated grading crash")

    monkeypatch.setattr(
        "services.grading_service.GradingService.grade_submission", _boom
    )

    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )

    assert job.status in ("partial", "failed")
    assert job.error_log
    grading_entries = [e for e in job.error_log if (e.get("step") == "grading")]
    assert len(grading_entries) == 2
    assert all("RuntimeError" in e["reason"] for e in grading_entries)

    assert test_db.query(Student).count() == 2
    assert test_db.query(Attempt).count() == 2
    assert test_db.query(AttemptAnswer).count() > 0
    assert test_db.query(Grade).count() == 0

    # Submissions must be marked IMPORT_GRADING_FAILED so the UI shows the
    # failure rather than leaving submissions in an indeterminate state.
    from enums import SubmissionGradeStatus
    from models.submission import Submission as Sub

    failed = test_db.query(Sub).all()
    assert all(
        s.grade_status == SubmissionGradeStatus.IMPORT_GRADING_FAILED.value
        for s in failed
    )


def test_sqlalchemy_grading_failure_also_marks_submission_failed(
    test_db: Session, exam_with_questions: Exam, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SQLAlchemyError during grade_submission is handled identically to
    unexpected exceptions: the submission is marked IMPORT_GRADING_FAILED and
    the error is recorded in the job log."""
    from sqlalchemy.exc import OperationalError

    from enums import SubmissionGradeStatus
    from models.submission import Submission as Sub

    service = ImportService(test_db)

    def _boom(_self, _submission_id, **_kwargs):
        raise OperationalError("simulated DB error", params=None, orig=None)

    monkeypatch.setattr(
        "services.grading_service.GradingService.grade_submission", _boom
    )

    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )

    assert job.status in ("partial", "failed")
    grading_entries = [e for e in (job.error_log or []) if e.get("step") == "grading"]
    assert len(grading_entries) == 2
    assert all("OperationalError" in e["reason"] for e in grading_entries)

    failed = test_db.query(Sub).all()
    assert all(
        s.grade_status == SubmissionGradeStatus.IMPORT_GRADING_FAILED.value
        for s in failed
    )


def test_unexpected_pipeline_failure_rolls_back_partial_data(
    test_db: Session, exam_with_questions: Exam, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-grading exception (e.g. a bug in _persist_attempts itself)
    must roll the SAVEPOINT back so partial Students/Attempts don't leak,
    while the ImportJob survives marked failed."""
    service = ImportService(test_db)

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated pipeline crash")

    monkeypatch.setattr(ImportService, "_persist_attempts", _boom)

    with pytest.raises(RuntimeError, match="simulated pipeline crash"):
        service.commit(
            exam=exam_with_questions,
            driver_name="moodle_json",
            source=_json_two_students(),
            triggered_by=None,
        )

    job = test_db.query(ImportJob).order_by(ImportJob.id.desc()).first()
    assert job is not None
    assert job.status == "failed"
    assert job.error_log
    first_entry = job.error_log[0]
    assert "RuntimeError" in first_entry["reason"]
    assert first_entry.get("step") == "pipeline"
    assert "traceback" in (first_entry.get("details") or {})

    assert test_db.query(Submission).count() == 0
    assert test_db.query(Attempt).count() == 0
    assert test_db.query(AttemptAnswer).count() == 0
    assert test_db.query(Grade).count() == 0


def test_validation_failure_collects_all_invalid_question_ids(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Hard-fail validation should report every offending answer at
    once so the teacher fixes the CSV in one round."""
    from services.import_drivers import (
        AnswerRecord,
        AttemptRecord,
        ImportPayload,
    )

    payload = ImportPayload(
        exam_id=exam_with_questions.id,
        driver_name="moodle_json",
        attempts=[
            AttemptRecord(
                student_external_id="anna@example.org",
                attempt_number=1,
                answers=[
                    AnswerRecord(exam_question_id=99001),
                    AnswerRecord(exam_question_id=99002),
                ],
            ),
            AttemptRecord(
                student_external_id="bruno@example.org",
                attempt_number=1,
                answers=[AnswerRecord(exam_question_id=99003)],
            ),
        ],
    )
    with pytest.raises(ImportValidationError) as excinfo:
        ImportService._validate_payload(payload, exam_with_questions)
    assert len(excinfo.value.issues) == 3
    assert any("99001" in issue for issue in excinfo.value.issues)
    assert any("99003" in issue for issue in excinfo.value.issues)


def test_failed_job_for_unparseable_source_records_step(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """When the driver hard-fails (invalid JSON), the job error_log
    captures step + exception class so the operator can triage."""
    from services.import_drivers import ImportDriverError

    service = ImportService(test_db)
    with pytest.raises(ImportDriverError):
        service.commit(
            exam=exam_with_questions,
            driver_name="moodle_json",
            source="not valid json {",
            triggered_by=None,
        )
    job = test_db.query(ImportJob).order_by(ImportJob.id.desc()).first()
    assert job is not None
    assert job.status == "failed"
    assert job.error_log
    entry = job.error_log[0]
    assert entry.get("step") == "validate"
    assert "ImportDriverError" in entry["reason"]


def test_unknown_scoring_strategy_raises(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """A typo'd scoring_strategy must crash the grading step rather
    than silently defaulting to 'latest'.

    The ORM @validates hook rejects bad values at write time, so to
    test the *grading-service* guard we patch the attribute directly on
    the in-memory instance after loading (which bypasses the ORM
    setter and thus the validator)."""
    service = ImportService(test_db)
    service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )
    submission = test_db.query(Submission).first()
    assert submission is not None

    # __dict__ assignment bypasses SQLAlchemy's @validates so the
    # grading_service code-path actually sees the typo'd value.
    submission.__dict__["scoring_strategy"] = "frist"  # typo
    with pytest.raises(ValueError, match="Unbekannte scoring_strategy"):
        service.grading_service.grade_submission(submission.id)


def test_attempt_with_null_timestamps_does_not_crash_pick_attempt(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """Missing date columns are tolerated; pick_attempt must order
    safely instead of raising TypeError on None comparison."""
    service = ImportService(test_db)
    # JSON rows without 'begonnen' / 'beendet' keys at all. Two attempts
    # for one student → attempt_number disambiguates the source key even
    # without timestamps.
    json_no_dates = _json_source(
        [
            _attempt_row(
                email="anna@example.org",
                begonnen=None,
                beendet=None,
                a1="Bern",
                a2="wahr",
                a3="Antwort",
            ),
            _attempt_row(
                email="anna@example.org",
                begonnen=None,
                beendet=None,
                a1="Zürich",
                a2="falsch",
                a3="Antwort",
            ),
        ]
    )
    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=json_no_dates,
        triggered_by=None,
    )
    assert job.status == "succeeded"
    submission = test_db.query(Submission).one()
    assert submission.graded_attempt_id is not None


# ---------------------------------------------------------------------------
# Cross-Tenant-Isolation für Idempotenz-Schlüssel
# ---------------------------------------------------------------------------


def test_two_institutions_can_have_overlapping_source_attempt_ids(
    test_db: Session, institution: Institution
) -> None:
    """Regression for the Cross-Tenant-Idempotenz-Bug: two institutions
    with the *same* (driver_name, source_attempt_id) tuple must not
    collide. Before scoping the unique constraint by institution_id,
    tenant B's import would either raise IntegrityError or be silently
    skipped as "idempotent — already imported"."""
    # Build a second institution with its own exam mirroring the first.
    inst_b = Institution(
        name="Andere Inst",
        slug="andere",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst_b)
    test_db.flush()

    mc_q_b = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=inst_b.id,
    )
    test_db.add(mc_q_b)
    test_db.flush()

    exam_b = Exam(
        title="Inst-B Mini",
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst_b.id,
    )
    test_db.add(exam_b)
    test_db.flush()
    test_db.add(
        ExamQuestion(exam_id=exam_b.id, question_id=mc_q_b.id, position=1, points=4.0)
    )

    # Build matching exam in institution A so the source_attempt_id
    # collision case is reachable from CSV.
    mc_q_a = QuestionReview(
        question_text="Hauptstadt der Schweiz?",
        question_type="single_choice",
        correct_answer="Bern",
        difficulty="easy",
        topic="Geo",
        institution_id=institution.id,
    )
    test_db.add(mc_q_a)
    test_db.flush()
    exam_a = Exam(
        title="Inst-A Mini",
        course="ABU",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=institution.id,
    )
    test_db.add(exam_a)
    test_db.flush()
    test_db.add(
        ExamQuestion(exam_id=exam_a.id, question_id=mc_q_a.id, position=1, points=4.0)
    )
    test_db.commit()

    # Same email, same timestamp, same attempt_number → identical
    # source_attempt_id across both tenants. Single-question exam, so the
    # JSON carries only frage1/antwort1.
    source = _json_source(
        [
            {
                "vorname": "Anna",
                "nachname": "Beispiel",
                "e-mail-adresse": "anna@example.org",
                "begonnen": "2026-05-15 09:00:00",
                "beendet": "2026-05-15 09:30:00",
                "frage1": _Q1,
                "antwort1": "Bern",
            }
        ]
    )
    job_a = ImportService(test_db).commit(
        exam=exam_a, driver_name="moodle_json", source=source, triggered_by=None
    )
    job_b = ImportService(test_db).commit(
        exam=exam_b, driver_name="moodle_json", source=source, triggered_by=None
    )

    assert job_a.status == "succeeded"
    assert job_b.status == "succeeded"

    inst_a_attempts = (
        test_db.query(Attempt).filter(Attempt.institution_id == institution.id).all()
    )
    inst_b_attempts = (
        test_db.query(Attempt).filter(Attempt.institution_id == inst_b.id).all()
    )
    assert len(inst_a_attempts) == 1
    assert len(inst_b_attempts) == 1
    # Same source_attempt_id, different institution_id — proves the
    # idempotency key is tenant-scoped.
    assert inst_a_attempts[0].source_attempt_id == inst_b_attempts[0].source_attempt_id


def test_persist_attempts_records_unexpected_integrity_error(
    test_db: Session, exam_with_questions: Exam, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Forcing a CHECK violation on attempt_number must surface as a
    row error (not a silent ``continue``).
    """
    from services.import_drivers import (
        AnswerRecord,
        AttemptRecord,
        ImportPayload,
        StudentRef,
    )
    from services.import_drivers.moodle_json_driver import MoodleJsonDriver

    eq_id = exam_with_questions.questions[0].id

    def _bad_parse(self, source, *, exam, db=None):  # type: ignore[no-untyped-def]
        # ``model_construct`` bypasses the pydantic ``ge=1`` guard so
        # attempt_number=0 actually reaches the DB and trips
        # ``check_attempt_number_positive`` — the DB-level branch the
        # service must record rather than silently swallow.
        bad_attempt = AttemptRecord.model_construct(
            student_external_id="anna@example.org",
            attempt_number=0,
            started_at=None,
            submitted_at=None,
            source_attempt_id="anna@example.org||0",
            answers=[AnswerRecord(exam_question_id=eq_id)],
            raw_payload={},
        )
        return ImportPayload(
            exam_id=exam.id,
            driver_name="moodle_json",
            students=[
                StudentRef(external_id="anna@example.org", display_name="Anna Beispiel")
            ],
            attempts=[bad_attempt],
        )

    monkeypatch.setattr(MoodleJsonDriver, "parse", _bad_parse)

    job = ImportService(test_db).commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=b"[]",  # ignored by the patched parse
        triggered_by=None,
    )
    # The DB-level CHECK constraint trips and is recorded as a row error.
    assert job.status in ("failed", "partial")
    assert (job.rows_failed or 0) >= 0
    assert job.error_log  # not None / not empty
    # monkeypatch auto-restores ``MoodleJsonDriver.parse`` at teardown.


# ---------------------------------------------------------------------------
# _extract_constraint_name: parse PG constraint name from IntegrityError
# ---------------------------------------------------------------------------


def test_extract_constraint_name_from_message_fallback() -> None:
    """When the DBAPI doesn't expose .diag.constraint_name, fall back to
    parsing the PG error message."""
    from sqlalchemy.exc import IntegrityError

    fake = IntegrityError(
        statement="INSERT ...",
        params={},
        orig=Exception(
            "duplicate key value violates unique constraint "
            '"uq_attempts_submission_source_attempt_id"\nDETAIL: Key (...)=(...) already exists.'
        ),
    )
    name = ImportService._extract_constraint_name(fake)
    assert name == "uq_attempts_submission_source_attempt_id"


def test_extract_constraint_name_returns_none_when_unparseable() -> None:
    from sqlalchemy.exc import IntegrityError

    fake = IntegrityError(
        statement="INSERT ...", params={}, orig=Exception("Something else went wrong")
    )
    assert ImportService._extract_constraint_name(fake) is None


def test_extract_constraint_name_prefers_diag_attribute() -> None:
    """When psycopg's .diag.constraint_name is set, use it directly."""
    from types import SimpleNamespace

    from sqlalchemy.exc import IntegrityError

    diag = SimpleNamespace(constraint_name="uq_attempts_submission_number")
    orig = SimpleNamespace(diag=diag)
    fake = IntegrityError.__new__(IntegrityError)
    fake.statement = ""
    fake.params = ()
    fake.orig = orig  # type: ignore[assignment]
    name = ImportService._extract_constraint_name(fake)
    assert name == "uq_attempts_submission_number"


# ---------------------------------------------------------------------------
# Surface stiller Fehler im _persist_attempts: student is None branch
# ---------------------------------------------------------------------------


def test_silent_skip_on_missing_student_now_records_row_error(
    test_db: Session, exam_with_questions: Exam, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: previously, an attempt whose student was missing from
    the upsert dict was silently dropped. Now it must land in
    payload.errors so the operator sees rows_failed > 0.
    """
    service = ImportService(test_db)

    # Force _upsert_students to return an empty dict, so every attempt's
    # student lookup misses.
    monkeypatch.setattr(
        ImportService,
        "_upsert_students",
        lambda self, payload, *, institution_id: {},
    )

    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
    )
    # rows_processed reports actually-persisted attempts (0 here),
    # rows_failed counts the per-row failures (2). With nothing
    # persisted but errors recorded, the job is FAILED (not partial) —
    # "partial" requires at least one row to have made it through.
    assert job.status == "failed"
    assert job.rows_processed == 0
    assert job.rows_failed == 2
    assert job.error_log
    assert all(
        "konnte nicht angelegt/gefunden werden" in e["reason"] for e in job.error_log
    )


# ---------------------------------------------------------------------------
# create_queued_job: pre-creates the row a Celery worker reuses (TF-412)
# ---------------------------------------------------------------------------


def test_create_queued_job_persists_queued_row(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """``create_queued_job`` inserts a *committed* ImportJob in ``queued``
    state that an async worker later picks up via ``import_job_id``. No
    parsing or grading happens here — only the row is created."""
    service = ImportService(test_db)

    job = service.create_queued_job(
        exam=exam_with_questions,
        driver_name="moodle_json",
        triggered_by=None,
    )

    assert job.id is not None
    assert job.status == ImportJobStatus.QUEUED.value
    assert job.exam_id == exam_with_questions.id
    assert job.institution_id == exam_with_questions.institution_id
    assert job.driver_name == "moodle_json"
    assert job.rows_processed == 0
    assert job.rows_failed == 0
    assert job.started_at is None  # not started until the worker runs commit()

    # Committed, so a fresh query in the same session sees it.
    fetched = test_db.query(ImportJob).filter(ImportJob.id == job.id).one()
    assert fetched.status == ImportJobStatus.QUEUED.value


def test_queued_job_is_reused_by_commit_without_duplicate(
    test_db: Session, exam_with_questions: Exam
) -> None:
    """A queued job handed to ``commit`` via ``import_job_id`` is reused
    in place (transitioned to a terminal state) — no second ImportJob row."""
    service = ImportService(test_db)
    queued = service.create_queued_job(
        exam=exam_with_questions, driver_name="moodle_json", triggered_by=None
    )

    job = service.commit(
        exam=exam_with_questions,
        driver_name="moodle_json",
        source=_json_two_students(),
        triggered_by=None,
        import_job_id=queued.id,
    )

    assert job.id == queued.id
    assert job.status in {
        ImportJobStatus.SUCCEEDED.value,
        ImportJobStatus.PARTIAL.value,
    }
    assert test_db.query(ImportJob).count() == 1
