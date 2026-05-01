"""Tests for ``LlmGrader`` + ``GradingService`` open_ended-Routing
(TF-334).

Pure-functional Stubs für den Anthropic-Client — der echte SDK-Call
ist nie Teil eines Tests. Wir mocken auf Client-Ebene, weil das
genau die Naht ist, an der ``LlmGrader`` injizierbar gebaut wurde.
"""

from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from models.auth import Institution
from models.exam import Exam, ExamQuestion
from models.question_review import QuestionReview
from models.student import Student
from models.submission import (
    Attempt,
    AttemptAnswer,
    Submission,
)
from services.grading.llm_grader import (
    LlmGradeOutcome,
    LlmGrader,
    OpenEndedGrade,
)
from services.grading_service import GradingService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_anthropic(json_payload: dict | str | Exception):
    """Build a fake anthropic-client whose ``messages.create`` returns a
    response shaped like the real SDK does (object with ``.content``
    list of blocks with ``.type``/``.text``).

    Pass an ``Exception`` instance to make the call raise — covers the
    fail-soft path back to the 0-Punkte-Stub.
    """
    client = MagicMock()
    if isinstance(json_payload, Exception):
        client.messages.create.side_effect = json_payload
        return client

    text = json_payload if isinstance(json_payload, str) else json.dumps(json_payload)
    block = SimpleNamespace(type="text", text=text)
    client.messages.create.return_value = SimpleNamespace(content=[block])
    return client


# ---------------------------------------------------------------------------
# OpenEndedGrade schema
# ---------------------------------------------------------------------------


def test_open_ended_grade_schema_accepts_minimal_payload() -> None:
    grade = OpenEndedGrade(
        points_awarded=2.5,
        confidence=0.7,
        rationale="Antwort deckt 2 von 3 Aspekten ab.",
        matched_aspects=["Aspekt A"],
        missing_aspects=["Aspekt C"],
    )
    assert grade.points_awarded == 2.5
    assert grade.matched_aspects == ["Aspekt A"]


# ---------------------------------------------------------------------------
# LlmGrader.grade — happy path
# ---------------------------------------------------------------------------


def test_llm_grader_returns_outcome_from_model_response() -> None:
    client = _stub_anthropic(
        {
            "points_awarded": 4.0,
            "confidence": 0.85,
            "rationale": "Vollständig korrekt.",
            "matched_aspects": ["Definition", "Beispiel"],
            "missing_aspects": [],
        }
    )
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="Was ist OOP?",
        correct_answer="Programmier-Paradigma rund um Objekte.",
        given_answer="Ein Paradigma, das Daten und Verhalten in Objekten kapselt.",
        points_max=4.0,
    )
    assert isinstance(outcome, LlmGradeOutcome)
    assert outcome.points_awarded == 4.0
    assert outcome.confidence == 0.85
    assert outcome.matched_aspects == ["Definition", "Beispiel"]
    assert outcome.is_correct is None
    assert outcome.status == "proposed"


def test_llm_grader_clamps_overshooting_points() -> None:
    """Modell-Halluzination: 12/10 Punkte → clamp auf points_max."""
    client = _stub_anthropic(
        {
            "points_awarded": 12.0,
            "confidence": 0.95,
            "rationale": "...",
            "matched_aspects": [],
            "missing_aspects": [],
        }
    )
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=10.0,
    )
    assert outcome.points_awarded == 10.0


# ---------------------------------------------------------------------------
# LlmGrader.grade — error paths fall back to 0-Punkte-Stub
# ---------------------------------------------------------------------------


def test_llm_grader_falls_back_when_model_raises() -> None:
    client = _stub_anthropic(RuntimeError("API down"))
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=4.0,
    )
    assert outcome.points_awarded == 0.0
    assert outcome.confidence == 0.0
    assert "fehlgeschlagen" in outcome.rationale.lower()


def test_llm_grader_falls_back_on_invalid_json() -> None:
    client = _stub_anthropic("not json at all")
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=4.0,
    )
    assert outcome.points_awarded == 0.0
    assert outcome.confidence == 0.0


def test_llm_grader_falls_back_on_empty_content_blocks() -> None:
    """Anthropic kann content=[] zurückgeben (z. B. wenn nur thinking-
    Blöcke ohne Text geliefert werden). _extract_text wirft → fail-soft."""
    client = MagicMock()
    client.messages.create.return_value = SimpleNamespace(content=[])
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=4.0,
    )
    assert outcome.points_awarded == 0.0
    assert outcome.confidence == 0.0


def test_llm_grader_demo_mode_without_api_key(monkeypatch) -> None:
    """Ohne ANTHROPIC_API_KEY und ohne injizierten Client läuft der
    Grader im Stub-Modus. Wichtig für Free-Tier-Setups und CI ohne
    Secret-Provisionierung."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    grader = LlmGrader()
    assert grader.demo_mode is True
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=4.0,
    )
    assert outcome.points_awarded == 0.0
    assert outcome.confidence == 0.0
    assert "ANTHROPIC_API_KEY" in outcome.rationale


def test_llm_grader_strips_markdown_code_block() -> None:
    """Manche Modell-Antworten kommen in ``` json ``` Wrappern — die müssen
    weg, sonst wird jede Bewertung zur Stub-Antwort."""
    fenced = (
        "```json\n"
        '{"points_awarded": 1.0, "confidence": 0.5, '
        '"rationale": "ok", "matched_aspects": [], '
        '"missing_aspects": []}\n'
        "```"
    )
    client = _stub_anthropic(fenced)
    grader = LlmGrader(client=client)
    outcome = grader.grade(
        question_text="X",
        correct_answer="Y",
        given_answer="Z",
        points_max=4.0,
    )
    assert outcome.points_awarded == 1.0
    assert outcome.confidence == 0.5


def test_llm_grader_returns_stub_when_correct_answer_missing() -> None:
    """Ohne Musterlösung lohnt sich ein API-Call gar nicht; stattdessen
    klar markieren, dass die Lehrperson manuell ranmuss."""
    grader = LlmGrader(client=_stub_anthropic({}))
    outcome = grader.grade(
        question_text="X",
        correct_answer="",
        given_answer="something",
        points_max=4.0,
    )
    assert outcome.points_awarded == 0.0
    assert "Musterlösung" in outcome.rationale


def test_llm_grader_uses_prompt_caching_on_static_blocks() -> None:
    """Spec 6.3: Frage + Musterlösung als statischer Cache-Anteil pro
    Prüfung. System-Prompt ebenfalls gecached. Studi-Antwort variabel.
    """
    client = _stub_anthropic(
        {
            "points_awarded": 2.0,
            "confidence": 0.6,
            "rationale": "...",
            "matched_aspects": [],
            "missing_aspects": [],
        }
    )
    grader = LlmGrader(client=client)
    grader.grade(
        question_text="Q",
        correct_answer="A",
        given_answer="B",
        points_max=4.0,
    )

    call_kwargs = client.messages.create.call_args.kwargs
    # System-Prompt cached
    system = call_kwargs["system"]
    assert isinstance(system, list)
    assert system[0]["cache_control"] == {"type": "ephemeral"}

    # User-Block: erster (statischer) cached, zweiter (variabel) nicht
    contents = call_kwargs["messages"][0]["content"]
    assert contents[0]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in contents[1]


# ---------------------------------------------------------------------------
# GradingService open_ended-Routing — End-to-End mit DB
# ---------------------------------------------------------------------------


def _seed_open_ended_submission(
    test_db: Session, *, given_answer: str = "Studi-Antwort"
) -> tuple[Submission, AttemptAnswer]:
    inst = Institution(
        name="LLM-Routing",
        slug="llm-routing",
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(inst)
    test_db.flush()

    open_q = QuestionReview(
        question_text="Erkläre OOP in zwei Sätzen.",
        question_type="open_ended",
        correct_answer="Programmier-Paradigma, das Daten + Verhalten in Objekten kapselt.",
        explanation="Belohne Kapselung + Vererbung; ignoriere Stilfragen.",
        difficulty="medium",
        topic="Informatik",
        institution_id=inst.id,
    )
    test_db.add(open_q)
    test_db.flush()

    exam = Exam(
        title="LLM Routing",
        course="Informatik",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=4.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    student = Student(
        institution_id=inst.id, external_id="s@example.org", display_name="Test S."
    )
    test_db.add_all([exam, student])
    test_db.flush()

    eq = ExamQuestion(exam_id=exam.id, question_id=open_q.id, position=1, points=4.0)
    test_db.add(eq)
    test_db.flush()

    submission = Submission(
        exam_id=exam.id, student_id=student.id, scoring_strategy="latest"
    )
    test_db.add(submission)
    test_db.flush()

    attempt = Attempt(
        submission_id=submission.id,
        institution_id=inst.id,
        attempt_number=1,
        source="moodle_csv",
        source_attempt_id="s|1",
    )
    test_db.add(attempt)
    test_db.flush()

    answer = AttemptAnswer(
        attempt_id=attempt.id,
        exam_question_id=eq.id,
        given_answer=given_answer,
    )
    test_db.add(answer)
    test_db.commit()
    return submission, answer


def test_grading_service_routes_open_ended_to_llm(test_db: Session) -> None:
    submission, answer = _seed_open_ended_submission(test_db)

    fake_llm = MagicMock(spec=LlmGrader)
    fake_llm.grade.return_value = LlmGradeOutcome(
        points_awarded=3.0,
        points_max=4.0,
        confidence=0.7,
        rationale="Gut, aber Vererbung fehlt.",
        matched_aspects=["Kapselung"],
        missing_aspects=["Vererbung"],
    )

    GradingService(test_db, llm_grader=fake_llm).grade_submission(submission.id)
    test_db.refresh(answer)

    assert answer.grade is not None
    assert answer.grade.points_awarded == 3.0
    assert answer.grade.points_max == 4.0
    assert answer.grade.llm_confidence == 0.7
    assert answer.grade.llm_rationale.startswith("Gut")
    assert answer.grade.llm_matched_aspects == ["Kapselung"]
    assert answer.grade.llm_missing_aspects == ["Vererbung"]
    assert answer.grade.is_correct is None
    # is_correct=None gates pending_review (kein approved/manual_override).
    test_db.refresh(submission)
    assert submission.grade_status == "pending_review"


def test_grading_service_passes_question_context_to_llm(test_db: Session) -> None:
    """Spec 6.3 verlangt Fragetext + Musterlösung + Erklärung +
    Schwierigkeit + Bloom an den LLM. Ohne diesen Test würde ein
    Refactor still die Cache-Effizienz killen, weil ein leerer Text-
    Block auch ein gültiger Anthropic-Call ist.
    """
    submission, _ = _seed_open_ended_submission(test_db)

    fake_llm = MagicMock(spec=LlmGrader)
    fake_llm.grade.return_value = LlmGradeOutcome(
        points_awarded=0.0,
        points_max=4.0,
        confidence=0.5,
        rationale="...",
        matched_aspects=[],
        missing_aspects=[],
    )

    GradingService(test_db, llm_grader=fake_llm).grade_submission(submission.id)

    call_kwargs = fake_llm.grade.call_args.kwargs
    assert call_kwargs["question_text"] == "Erkläre OOP in zwei Sätzen."
    assert call_kwargs["correct_answer"].startswith("Programmier-Paradigma")
    assert "Kapselung" in call_kwargs["explanation"]
    assert call_kwargs["points_max"] == 4.0
    assert call_kwargs["difficulty"] == "medium"
