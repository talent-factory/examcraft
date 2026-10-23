"""Tests für den Gateway-Generierungspfad (TF-439).

Verifiziert den typisierten PydanticAI-Output, die 4xx→ModelUnavailableError-
Klassifizierung und die Transient-Weitergabe bei 5xx.
"""

import pytest
from services import gateway_generator as gg
from services.claude_service import ModelUnavailableError


@pytest.fixture(autouse=True)
def _gateway_env(monkeypatch):
    """Der Gateway-Pfad braucht URL + Virtual Key (Client-Konstruktion fail-fast)."""
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-x")


class _FakeResult:
    def __init__(self, output):
        self.output = output


@pytest.mark.asyncio
async def test_typed_generation_returns_dicts(monkeypatch):
    qs = gg.GeneratedQuestions(
        questions=[
            gg.GeneratedQuestion(
                id="q1",
                type="single_choice",
                question="Was ist `x`?",
                options=["a", "b", "c", "d"],
                correct_answer="a",
                explanation="weil `a`",
                difficulty="medium",
                topic="T",
            )
        ]
    )

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult(qs)

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_questions_via_gateway("prompt")
    assert isinstance(out, list) and out[0]["id"] == "q1"
    assert out[0]["type"] == "single_choice"


@pytest.mark.asyncio
async def test_typed_generation_preserves_open_ended_grading_fields(monkeypatch):
    """TF-594 regression: sample_answer/evaluation_criteria/bloom_level/
    competency_code/ln_level must survive the typed gateway round-trip.
    Before the fix, GeneratedQuestion had no fields for these — pydantic's
    default extra="ignore" silently dropped them on model_dump(), even
    though rag_service._convert_to_rag_question already reads exactly these
    keys for question_type="open_ended"."""
    qs = gg.GeneratedQuestions(
        questions=[
            gg.GeneratedQuestion(
                id="q1",
                type="open_ended",
                question="Analysieren Sie die Situation...",
                sample_answer="Die Musterlösung...",
                evaluation_criteria="Bewertungskriterien...",
                bloom_level=4,
                competency_code="B3",
                ln_level=3,
                difficulty="medium",
                topic="T",
            )
        ]
    )

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult(qs)

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_questions_via_gateway("prompt")

    assert out[0]["sample_answer"] == "Die Musterlösung..."
    assert out[0]["evaluation_criteria"] == "Bewertungskriterien..."
    assert out[0]["bloom_level"] == 4
    assert out[0]["competency_code"] == "B3"
    assert out[0]["ln_level"] == 3


@pytest.mark.asyncio
async def test_typed_generation_preserves_multiple_choice_correct_answers(monkeypatch):
    """TF-594 regression: correct_answers (plural, multiple_choice) must
    survive the typed gateway round-trip — rag_service reads this exact key
    for question_type="multiple_choice", distinct from the singular
    correct_answer used by single_choice/true_false."""
    qs = gg.GeneratedQuestions(
        questions=[
            gg.GeneratedQuestion(
                id="q1",
                type="multiple_choice",
                question="Welche Aussagen treffen zu?",
                options=["a", "b", "c", "d"],
                correct_answers=["a", "c"],
                difficulty="medium",
                topic="T",
            )
        ]
    )

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult(qs)

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_questions_via_gateway("prompt")

    assert out[0]["correct_answers"] == ["a", "c"]


@pytest.mark.asyncio
async def test_4xx_maps_to_model_unavailable(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=404, model_name="examcraft/generation", body="no"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelUnavailableError):
        await gg.generate_questions_via_gateway("prompt")


@pytest.mark.asyncio
async def test_5xx_propagates_as_transient(monkeypatch):
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=503, model_name="examcraft/generation", body="busy"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelHTTPError):
        await gg.generate_questions_via_gateway("prompt")


@pytest.mark.asyncio
async def test_raw_generation_returns_string(monkeypatch):
    """generate_raw_via_gateway gibt den rohen Output-String zurück."""

    async def fake_run(self, prompt):  # noqa: ANN001
        return _FakeResult("# Rohe Markdown-Ausgabe")

    monkeypatch.setattr(gg.Agent, "run", fake_run, raising=True)
    out = await gg.generate_raw_via_gateway("prompt")
    assert out == "# Rohe Markdown-Ausgabe"


@pytest.mark.asyncio
async def test_raw_4xx_maps_to_model_unavailable(monkeypatch):
    """4xx im Roh-Pfad wird wie im getypten Pfad als ModelUnavailableError klassifiziert."""
    from pydantic_ai.exceptions import ModelHTTPError

    async def boom(self, prompt):  # noqa: ANN001
        raise ModelHTTPError(
            status_code=404, model_name="examcraft/generation", body="no"
        )

    monkeypatch.setattr(gg.Agent, "run", boom, raising=True)
    with pytest.raises(ModelUnavailableError):
        await gg.generate_raw_via_gateway("prompt")


def test_open_ended_json_string_fields_become_markdown():
    """For structured model answers the model sometimes writes a JSON object
    as a string into sample_answer/evaluation_criteria. The validator renders
    it as Markdown instead of passing the raw JSON through."""
    q = gg.GeneratedQuestion(
        id="q1",
        type="open_ended",
        question="Fallstudie Projektplanung",
        sample_answer='{"structure":"Drei Teile","key_points":["Bauleitung"],'
        '"model_answer":"1. Planung\\n2. SWOT"}',
        evaluation_criteria='{"total_points":20,"criteria":[{"aspect":"SWOT",'
        '"points":5,"description":"Mit Massnahmen"}]}',
    )
    assert q.sample_answer == (
        "**Empfohlene Struktur:**\n\nDrei Teile\n\n**Kernpunkte:**\n\n"
        "- Bauleitung\n\n**Musterantwort:**\n\n1. Planung\n2. SWOT"
    )
    assert q.evaluation_criteria == (
        "**Gesamtpunkte: 20**\n\n**Bewertungskriterien:**\n\n"
        "- **SWOT** (5 Punkte): Mit Massnahmen"
    )


def test_open_ended_object_fields_are_accepted_as_markdown():
    """If the model returns a real object instead of a string, str validation
    must not fail (otherwise the run falls back to the raw-Markdown path)."""
    q = gg.GeneratedQuestion(
        id="q1",
        type="open_ended",
        question="Q",
        sample_answer={"model_answer": "Text"},
        evaluation_criteria=["Kriterium A", "Kriterium B"],
    )
    assert q.sample_answer == "**Musterantwort:**\n\nText"
    assert q.evaluation_criteria == "- Kriterium A\n- Kriterium B"


def test_plain_text_fields_pass_through_unchanged():
    q = gg.GeneratedQuestion(
        id="q1",
        type="open_ended",
        question="Q",
        sample_answer="Fliesstext",
        evaluation_criteria="Kriterien als Text",
        explanation="Erklärung",
    )
    assert q.sample_answer == "Fliesstext"
    assert q.evaluation_criteria == "Kriterien als Text"
    assert q.explanation == "Erklärung"


def test_explanation_json_rubric_string_becomes_markdown():
    q = gg.GeneratedQuestion(
        id="q1",
        type="open_ended",
        question="Q",
        explanation='{"total_points":20,"criteria":[{"aspect":"SWOT",'
        '"points":5,"description":"Mit Massnahmen"}]}',
    )
    assert q.explanation == (
        "**Gesamtpunkte: 20**\n\n**Bewertungskriterien:**\n\n"
        "- **SWOT** (5 Punkte): Mit Massnahmen"
    )


def test_json_sample_answer_that_is_not_a_rubric_is_unchanged():
    """A legitimate JSON answer (e.g. to "write a JSON object") must survive."""
    answer = '{"name": "Max", "age": 30}'
    q = gg.GeneratedQuestion(
        id="q1", type="open_ended", question="Q", sample_answer=answer
    )
    assert q.sample_answer == answer


def test_multiple_choice_answers_are_untouched():
    """multiple_choice answers are JSON arrays by design (DeterministicGrader
    parses them); the validator must not cover correct_answer(s)."""
    q = gg.GeneratedQuestion(
        id="q1",
        type="multiple_choice",
        question="Q",
        options=["A", "B", "C"],
        correct_answers=["A", "B"],
        correct_answer='["A", "B"]',
        explanation="A und B sind richtig",
    )
    assert q.correct_answers == ["A", "B"]
    assert q.correct_answer == '["A", "B"]'
    assert q.explanation == "A und B sind richtig"
