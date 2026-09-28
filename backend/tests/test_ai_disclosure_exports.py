"""EU AI Act Art. 50 marking in exam and grade exports (TF-747)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from xml.etree.ElementTree import fromstring

import pytest

from services.ai_disclosure import (
    AI_DISCLOSURE_TAG,
    exam_ai_notice,
    grades_ai_notice,
)
from services.exam_export_service import (
    IliasQtiExporter,
    JsonExporter,
    MarkdownExporter,
    MoodleXmlExporter,
    PdfExporter,
)
from services.translation_service import SUPPORTED_LOCALES


def _exam(language: str = "de") -> dict:
    return {
        "title": "Algorithmen",
        "language": language,
        "total_points": 3,
        "passing_percentage": 50,
        "questions": [
            {
                "position": 1,
                "points": 1,
                "question_text": "Was ist O(n)?",
                "question_type": "single_choice",
                "options": ["Linear", "Konstant"],
                "correct_answer": "Linear",
            },
            {
                "position": 2,
                "points": 2,
                "question_text": "Erkläre Heapsort.",
                "question_type": "open_ended",
                "correct_answer": "Heap bauen, Maximum entnehmen.",
            },
        ],
    }


@pytest.mark.parametrize("locale", SUPPORTED_LOCALES)
def test_notices_match_locale_files(locale: str) -> None:
    """Each locale resolves to its own file's text, not a German fallback."""
    path = Path(__file__).parent.parent / "locales" / f"t.{locale}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))[locale]
    assert exam_ai_notice(locale) == raw["export_ai_notice"]
    assert grades_ai_notice(locale) == raw["export_ai_notice_grades"]
    if locale != "de":
        assert raw["export_ai_notice"] != exam_ai_notice("de")


def test_markdown_export_carries_visible_notice() -> None:
    assert f"> {exam_ai_notice('de')}" in MarkdownExporter.export(_exam())


def test_markdown_notice_follows_exam_language() -> None:
    assert exam_ai_notice("en") in MarkdownExporter.export(_exam("en"))


def test_json_export_carries_machine_readable_disclosure() -> None:
    data = json.loads(JsonExporter.export(_exam()))
    disclosure = data["ai_disclosure"]
    assert disclosure["ai_generated_content"] is True
    assert disclosure["generator"] == "ExamCraft AI"
    assert "Art. 50" in disclosure["regulation"]
    assert disclosure["notice"] == exam_ai_notice("de")


def test_moodle_export_has_comment_and_tag_per_exported_question() -> None:
    xml = MoodleXmlExporter.export(_exam())
    assert f"<!-- {exam_ai_notice('de')} -->" in xml
    root = fromstring(xml)
    questions = root.findall("question")
    assert len(questions) == 2
    for question in questions:
        assert question.findtext("tags/tag/text") == AI_DISCLOSURE_TAG


def test_moodle_export_skipped_question_gets_no_tag() -> None:
    exam = _exam()
    exam["questions"][0]["correct_answer"] = "Nicht vorhanden"
    xml, skipped = MoodleXmlExporter.export_with_skipped(exam)
    assert skipped == [1]
    questions = fromstring(xml).findall("question")
    assert len(questions) == 1
    assert questions[0].findtext("tags/tag/text") == AI_DISCLOSURE_TAG


def test_ilias_export_has_qti_comment() -> None:
    xml = IliasQtiExporter.export(_exam())
    assert fromstring(xml).findtext("assessment/qticomment") == exam_ai_notice("de")


def test_pdf_export_has_metadata_marker() -> None:
    pdf = PdfExporter.export(_exam())
    assert re.search(rb"/Keywords\s*\(" + AI_DISCLOSURE_TAG.encode(), pdf)
    assert re.search(rb"/Creator\s*\(ExamCraft AI\)", pdf)


def test_grade_pdf_has_metadata_marker() -> None:
    from services.grade_export_service import GradeExportData, GradePdfExporter

    data = GradeExportData(
        institution_name="Schule",
        exam_title="Algorithmen",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=[],
    )
    pdf = GradePdfExporter.export(data)
    assert re.search(rb"/Keywords\s*\(" + AI_DISCLOSURE_TAG.encode(), pdf)
    assert re.search(rb"/Creator\s*\(ExamCraft AI\)", pdf)


def test_grade_csv_stays_uniform_without_in_file_notice() -> None:
    from services.grade_export_service import GradeCsvExporter, GradeExportData

    data = GradeExportData(
        institution_name="Schule",
        exam_title="Algorithmen",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=[],
    )
    text = GradeCsvExporter.export(data).decode("utf-8-sig")
    assert len(text.splitlines()) == 1  # header only


def _pdf_text(pdf: bytes) -> str:
    import fitz

    with fitz.open(stream=pdf, filetype="pdf") as doc:
        # Normalise soft line breaks: the notice wraps across lines.
        return " ".join(" ".join(page.get_text().split()) for page in doc)


def test_exam_pdf_shows_visible_notice_in_exam_language() -> None:
    text = _pdf_text(PdfExporter.export(_exam("en")))
    assert exam_ai_notice("en") in text


def test_grade_pdf_shows_visible_notice() -> None:
    from services.grade_export_service import GradeExportData, GradePdfExporter

    data = GradeExportData(
        institution_name="Schule",
        exam_title="Algorithmen",
        exam_course=None,
        exam_date=None,
        passing_percentage=50.0,
        scheme_config=None,
        rows=[],
    )
    assert grades_ai_notice("de") in _pdf_text(GradePdfExporter.export(data))


def test_moodle_export_tags_every_question_type() -> None:
    exam = _exam()
    exam["questions"] += [
        {
            "position": 3,
            "points": 1,
            "question_text": "Stimmt das?",
            "question_type": "true_false",
            "correct_answer": "true",
        },
        {
            "position": 4,
            "points": 2,
            "question_text": "Wähle alle.",
            "question_type": "multiple_choice",
            "options": ["A", "B", "C"],
            "correct_answer": json.dumps(["A", "B"]),
        },
    ]
    questions = fromstring(MoodleXmlExporter.export(exam)).findall("question")
    assert len(questions) == 4
    assert {q.get("type") for q in questions} >= {"essay", "multichoice", "truefalse"}
    for question in questions:
        assert question.findtext("tags/tag/text") == AI_DISCLOSURE_TAG
