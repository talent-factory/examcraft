"""
Tests for Exam Export Service.
Covers MarkdownExporter, JsonExporter, and MoodleXmlExporter.
"""

import json
import pytest

from services.exam_export_service import (
    MarkdownExporter,
    JsonExporter,
    MoodleXmlExporter,
)


@pytest.fixture
def sample_exam_data():
    return {
        "title": "Algorithmen Midterm",
        "course": "Algo & DS",
        "exam_date": "2026-04-15",
        "time_limit_minutes": 90,
        "allowed_aids": "Alle schriftlichen Unterlagen",
        "instructions": "Beantworten Sie alle Fragen.",
        "passing_percentage": 50.0,
        "total_points": 10.0,
        "language": "de",
        "questions": [
            {
                "position": 1,
                "points": 4.0,
                "question_text": "Wie funktioniert Heapify?",
                "question_type": "multiple_choice",
                "difficulty": "medium",
                "options": ["A) Top-down", "B) Bottom-up", "C) Beide", "D) Keines"],
                "correct_answer": "C) Beide",
                "explanation": "Heapify kann top-down und bottom-up arbeiten.",
            },
            {
                "position": 2,
                "points": 6.0,
                "question_text": "Erklären Sie die Zeitkomplexität von BuildHeap.",
                "question_type": "open_ended",
                "difficulty": "hard",
                "options": None,
                "correct_answer": "O(n) amortisiert.",
                "explanation": "Durch die Summe der Höhen ergibt sich O(n).",
            },
        ],
    }


class TestMarkdownExporter:
    def test_export_questions_only(self, sample_exam_data):
        """Export without solutions does not include answers."""
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "# Algorithmen Midterm" in md
        assert "Wie funktioniert Heapify?" in md
        # Points label can be "4 Punkte" or "4.0 Punkte"
        assert "4" in md and "Punkte" in md
        assert "Musterlösung" not in md
        # The solution marker and open-ended answer should not appear
        assert "O(n) amortisiert" not in md  # open-ended correct_answer not shown

    def test_export_with_solutions(self, sample_exam_data):
        """Export with solutions includes correct_answer and explanation."""
        md = MarkdownExporter.export(sample_exam_data, include_solutions=True)
        assert "Musterlösung" in md
        assert "C) Beide" in md
        assert "Heapify kann top-down" in md

    def test_export_contains_exam_metadata(self, sample_exam_data):
        """Export includes course, date, time limit, and aids."""
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "Algo & DS" in md
        assert "2026-04-15" in md
        assert "90 Minuten" in md
        assert "Alle schriftlichen Unterlagen" in md

    def test_export_mc_options_as_checkboxes(self, sample_exam_data):
        """Multiple choice options are rendered as checkboxes."""
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "- [ ] A) Top-down" in md
        assert "- [ ] B) Bottom-up" in md

    def test_export_open_ended_has_answer_space(self, sample_exam_data):
        """Open-ended questions include placeholder answer space."""
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "*Antwort:*" in md


class TestJsonExporter:
    def test_export_structure(self, sample_exam_data):
        """JSON output has exam metadata and questions array."""
        result = JsonExporter.export(sample_exam_data)
        data = json.loads(result)
        assert data["exam"]["title"] == "Algorithmen Midterm"
        assert data["exam"]["course"] == "Algo & DS"
        assert data["exam"]["total_points"] == 10.0
        assert len(data["questions"]) == 2

    def test_export_question_fields(self, sample_exam_data):
        """Each question in JSON has required fields."""
        result = JsonExporter.export(sample_exam_data)
        data = json.loads(result)
        q = data["questions"][0]
        assert q["position"] == 1
        assert q["points"] == 4.0
        assert q["question_text"] == "Wie funktioniert Heapify?"
        assert q["question_type"] == "multiple_choice"
        assert q["correct_answer"] == "C) Beide"

    def test_export_is_valid_json(self, sample_exam_data):
        """Output is valid, pretty-printed JSON."""
        result = JsonExporter.export(sample_exam_data)
        # Must not raise
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


class TestMoodleXmlExporter:
    def test_export_valid_xml(self, sample_exam_data):
        """Output is valid XML with quiz root and question elements."""
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert "<?xml" in xml
        assert "<quiz>" in xml
        assert "<question type=" in xml
        assert "Heapify" in xml

    def test_mc_question_format(self, sample_exam_data):
        """Multiple choice questions use 'multichoice' type."""
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert 'type="multichoice"' in xml

    def test_open_ended_question_format(self, sample_exam_data):
        """Open-ended questions use 'essay' type."""
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert 'type="essay"' in xml

    def test_true_false_question_format(self):
        """True/false questions use 'truefalse' type."""
        exam_data = {
            "title": "TF Test",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 2.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 2.0,
                    "question_text": "Python ist eine kompilierte Sprache.",
                    "question_type": "true_false",
                    "difficulty": "easy",
                    "options": None,
                    "correct_answer": "Falsch",
                    "explanation": "Python ist interpretiert.",
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert 'type="truefalse"' in xml

    def test_mc_correct_answer_fraction(self, sample_exam_data):
        """Correct MC answer has fraction=100, others have fraction=0."""
        xml = MoodleXmlExporter.export(sample_exam_data)
        # C) Beide is the correct answer — should appear with fraction="100"
        assert 'fraction="100"' in xml
        assert 'fraction="0"' in xml
