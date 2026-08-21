"""
Tests for Exam Export Service.
Covers MarkdownExporter, JsonExporter, MoodleXmlExporter and PdfExporter.

The PDF tests assert on the *rendered* document — text and vector paths
extracted with PyMuPDF — rather than on the exporter's internal flowables,
so that font embedding, tick boxes, ruled lines and page breaks are checked
as a reader would see them.
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
                "question_type": "single_choice",
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

    def test_single_point_question_uses_singular(self, sample_exam_data):
        """ "1 Punkte" is simply wrong German — and the PDF export shares this
        label with Markdown, so both must agree."""
        sample_exam_data["questions"][0]["points"] = 1.0
        md = MarkdownExporter.export(sample_exam_data, include_solutions=False)
        assert "(1 Punkt)" in md
        assert "1 Punkte" not in md

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
        assert q["question_type"] == "single_choice"
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

    def test_multichoice_multi_export_single_false_and_fractions(self):
        """multiple_choice exports as multichoice with <single>false</single>.

        Two-of-four correct → positive fraction 100/2 = 50 for each correct
        option, negative fraction -100/(4-2) = -50 for each wrong option.
        """
        exam_data = {
            "title": "Multi Test",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 4.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 4.0,
                    "question_type": "multiple_choice",
                    "question_text": "Welche zwei treffen zu?",
                    "difficulty": "medium",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": '["A", "C"]',
                    "explanation": None,
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert 'type="multichoice"' in xml
        assert "<single>false</single>" in xml
        assert 'fraction="50"' in xml  # two correct → 100/2
        assert 'fraction="-50"' in xml  # two wrong → -100/(4-2)

    def test_multichoice_multi_export_three_correct_fraction_5dp(self):
        """Three-of-four correct uses Moodle-conformant 5-dp thirds."""
        exam_data = {
            "title": "Multi Test 3",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 6.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 6.0,
                    "question_type": "multiple_choice",
                    "question_text": "Welche drei treffen zu?",
                    "difficulty": "medium",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": '["A", "B", "C"]',
                    "explanation": None,
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert "<single>false</single>" in xml
        assert 'fraction="33.33333"' in xml  # 100/3 to 5 dp
        assert 'fraction="-100"' in xml  # single wrong → -100/(4-3)

    def test_multichoice_multi_export_canonical_text_options(self):
        """Production shape (TF-403): options are plain text and
        correct_answer holds the exact option strings. The exporter marks
        them correct via the same grader normalization, emits the original
        option text, single=false, and 50/-50 fractions."""
        exam_data = {
            "title": "Multi Canonical",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 4.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 4.0,
                    "question_type": "multiple_choice",
                    "question_text": "Welche zwei sind Schweizer Städte?",
                    "difficulty": "medium",
                    "options": ["Bern", "Paris", "Zürich", "London"],
                    "correct_answer": '["Bern", "Zürich"]',
                    "explanation": None,
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert "<single>false</single>" in xml
        assert 'fraction="50"' in xml  # 100/2
        assert 'fraction="-50"' in xml  # -100/(4-2)
        assert "Bern" in xml and "Zürich" in xml  # original text emitted

    def test_multichoice_multi_export_negative_thirds(self):
        """2-of-5 produces -100/3 = -33.33333 for the three wrong options."""
        exam_data = {
            "title": "Multi 2of5",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 5.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 5.0,
                    "question_type": "multiple_choice",
                    "question_text": "Welche zwei von fünf?",
                    "difficulty": "medium",
                    "options": ["A", "B", "C", "D", "E"],
                    "correct_answer": '["A", "C"]',
                    "explanation": None,
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert 'fraction="50"' in xml  # 100/2
        assert 'fraction="-33.33333"' in xml  # -100/3 to 5 dp

    def test_multichoice_multi_export_skips_unscoreable_question(self, monkeypatch):
        """When no option matches correct_answer (malformed/letter-mismatch),
        the exporter skips the question with a warning rather than emitting an
        unscoreable all-negative Moodle question (TF-403)."""
        import services.exam_export_service as ees

        captured: list = []
        monkeypatch.setattr(
            ees.logger,
            "warning",
            lambda fmt, *args, **kwargs: captured.append((fmt, args)),
        )
        exam_data = {
            "title": "Multi Broken",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 4.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 4.0,
                    "question_type": "multiple_choice",
                    "question_text": "Unbewertbare Frage",
                    "difficulty": "medium",
                    "options": ["A) 2", "B) 4", "C) 3", "D) 6"],
                    "correct_answer": '["X", "Y"]',  # matches no option
                    "explanation": None,
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)
        assert 'type="multichoice"' not in xml  # question skipped
        assert "Unbewertbare Frage" not in xml
        assert captured  # warning emitted

    def test_single_choice_export_still_single_true(self, sample_exam_data):
        """single_choice still routes to single-answer multichoice."""
        xml = MoodleXmlExporter.export(sample_exam_data)
        assert "<single>true</single>" in xml
        assert "<single>false</single>" not in xml

    def test_markdown_question_text_rendered_as_html(self):
        """Markdown in question text is converted to HTML (TF-404).

        Question text is authored in Markdown but Moodle renders the
        ``questiontext`` field as HTML (format="html"). Without
        conversion, markers like ``**`` and ``- `` show up literally in
        Moodle. The exporter must convert Markdown to HTML so bold text,
        lists and paragraphs render after import.
        """
        exam_data = {
            "title": "MD Test",
            "course": None,
            "exam_date": None,
            "time_limit_minutes": None,
            "allowed_aids": None,
            "instructions": None,
            "passing_percentage": 50.0,
            "total_points": 6.0,
            "language": "de",
            "questions": [
                {
                    "position": 1,
                    "points": 6.0,
                    "question_text": (
                        "**Szenario:** Sie leiten ein Projekt.\n\n"
                        "- Erster Punkt\n"
                        "- Zweiter Punkt\n\n"
                        "Zeile A\nZeile B"
                    ),
                    "question_type": "open_ended",
                    "difficulty": "hard",
                    "options": None,
                    "correct_answer": "",
                    "explanation": "Ein **wichtiger** Hinweis.",
                }
            ],
        }
        xml = MoodleXmlExporter.export(exam_data)

        # Bold Markdown must become an HTML <strong> tag (escaped in XML),
        # never a literal ``**``.
        assert "&lt;strong&gt;Szenario:&lt;/strong&gt;" in xml
        assert "**Szenario:**" not in xml
        # A blank-line-separated list becomes a real HTML list.
        assert "&lt;li&gt;Erster Punkt&lt;/li&gt;" in xml
        assert "- Erster Punkt" not in xml
        # Tight single newlines are preserved as <br> (not collapsed into
        # one block like the unconverted output was).
        assert "&lt;br" in xml
        # generalfeedback (explanation) is converted too.
        assert "&lt;strong&gt;wichtiger&lt;/strong&gt;" in xml
        assert "**wichtiger**" not in xml


# ---------------------------------------------------------------------------
# PdfExporter (TF-656)
# ---------------------------------------------------------------------------


def _pdf_text(pdf_bytes: bytes) -> str:
    """Extract the rendered text of a PDF via PyMuPDF.

    Asserting on extracted text (rather than on the exporter's internal
    story objects) is what makes these tests meaningful: it proves the
    glyphs actually reach the page with the right encoding, which is the
    whole point of the font requirement.
    """
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return "\n".join(page.get_text() for page in doc)


class TestPdfExporter:
    def test_export_returns_pdf_bytes(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        result = PdfExporter.export(sample_exam_data)
        assert isinstance(result, bytes)
        assert result.startswith(b"%PDF-")

    def test_export_contains_title_and_all_question_texts(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Algorithmen Midterm" in text
        for q in sample_exam_data["questions"]:
            assert q["question_text"] in text

    def test_header_contains_all_metadata_fields(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Kurs: Algo & DS" in text
        assert "Datum: 2026-04-15" in text
        assert "Zeitlimit: 90 Minuten" in text
        assert "Erlaubte Hilfsmittel: Alle schriftlichen Unterlagen" in text
        # Goes through _points_label, so no stray ".0" reaches the sheet.
        assert "Gesamtpunktzahl: 10 Punkte" in text
        # Percentage AND absolute points, mirroring the MarkdownExporter
        assert "Bestehensgrenze: 50.0% (5 Punkte)" in text

    def test_header_omits_unset_optional_fields(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        sample_exam_data["course"] = None
        sample_exam_data["exam_date"] = None
        sample_exam_data["time_limit_minutes"] = None
        sample_exam_data["allowed_aids"] = None
        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Kurs" not in text
        assert "Zeitlimit" not in text
        assert "Erlaubte Hilfsmittel" not in text
        # Mandatory fields survive
        assert "Gesamtpunktzahl" in text

    def test_has_name_and_class_fill_in_lines(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Name:" in text
        assert "Klasse:" in text

    def test_instructions_rendered_when_set(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Hinweise" in text
        assert "Beantworten Sie alle Fragen." in text

    def test_instructions_block_omitted_when_unset(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        sample_exam_data["instructions"] = None
        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Hinweise" not in text


def _pdf_checkbox_count(pdf_bytes: bytes) -> int:
    """Count drawn empty checkboxes (small square ``re`` paths)."""
    import fitz

    count = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            for path in page.get_drawings():
                for item in path["items"]:
                    if item[0] != "re":
                        continue
                    rect = item[1]
                    if abs(rect.width - rect.height) < 0.5 and 5 < rect.width < 20:
                        count += 1
    return count


def _pdf_answer_line_count(pdf_bytes: bytes) -> int:
    """Count drawn horizontal answer lines (``l`` paths)."""
    import fitz

    count = 0
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            for path in page.get_drawings():
                for item in path["items"]:
                    if item[0] == "l" and abs(item[1].y - item[2].y) < 0.5:
                        count += 1
    return count


def _pdf_answer_line_gaps_mm(pdf_bytes: bytes) -> list[float]:
    """Vertical gaps, in millimetres, between consecutive answer lines."""
    import fitz

    gaps = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            ys = sorted(
                item[1].y
                for path in page.get_drawings()
                for item in path["items"]
                if item[0] == "l" and abs(item[1].y - item[2].y) < 0.5
            )
            # 1 pt = 1/72 inch = 25.4/72 mm
            gaps.extend(
                (later - earlier) * 25.4 / 72 for earlier, later in zip(ys, ys[1:])
            )
    return gaps


def _pdf_span_font(pdf_bytes: bytes, needle: str) -> str:
    """Return the font name of the first text span containing ``needle``.

    Lets a test assert on actual rendering (bold, monospace) rather than
    on the exporter's internal styling decisions.
    """
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if needle in span["text"]:
                            return span["font"]
    raise AssertionError(f"no span containing {needle!r} found in the PDF")


def _single_question_exam(question: dict) -> dict:
    return {
        "title": "Typtest",
        "total_points": question["points"],
        "passing_percentage": 50.0,
        "questions": [question],
    }


class TestPdfExporterQuestionTypes:
    @pytest.mark.parametrize(
        "question_type,options",
        [
            ("single_choice", ["A", "B"]),
            ("multiple_choice", ["A", "B"]),
            ("true_false", None),
            ("open_ended", None),
        ],
    )
    def test_every_question_type_produces_a_readable_pdf(self, question_type, options):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": f"Frage vom Typ {question_type}?",
                "question_type": question_type,
                "options": options,
                "correct_answer": "A",
            }
        )
        pdf = PdfExporter.export(exam)
        assert pdf.startswith(b"%PDF-")
        assert f"Frage vom Typ {question_type}?" in _pdf_text(pdf)

    @pytest.mark.parametrize(
        "points,expected",
        [
            (1.0, "Frage 1 (1 Punkt) —"),
            (2.0, "Frage 1 (2 Punkte) —"),
            (0.5, "Frage 1 (0.5 Punkte) —"),
        ],
    )
    def test_question_heading_uses_singular_for_exactly_one_point(
        self, points, expected
    ):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": points,
                "question_text": "Eine Frage.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
        )
        assert expected in _pdf_text(PdfExporter.export(exam))

    def test_question_heading_shows_position_points_and_type_label(
        self, sample_exam_data
    ):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data))
        assert "Frage 1 (4 Punkte) — Einfachauswahl" in text
        assert "Frage 2 (6 Punkte) — Offene Frage" in text

    def test_single_choice_renders_one_empty_checkbox_per_option(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Aussage stimmt?",
                "question_type": "single_choice",
                "options": ["Alpha", "Beta", "Gamma"],
                "correct_answer": "Beta",
            }
        )
        pdf = PdfExporter.export(exam)
        text = _pdf_text(pdf)
        for option in ("Alpha", "Beta", "Gamma"):
            assert option in text
        assert _pdf_checkbox_count(pdf) == 3

    def test_legacy_dict_shaped_options_render_the_option_text_not_the_keys(self):
        """``Question.options`` has historically also been persisted as a
        ``Dict[str, str]`` keyed 'A'/'B'/'C'/'D' (see
        utils/question_options.py). Iterating a dict yields its keys, so
        an un-normalized dict here would silently print 'A'/'B'/'C'
        instead of the real answer text."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Aussage stimmt?",
                "question_type": "single_choice",
                "options": {"A": "Alpha", "B": "Beta", "C": "Gamma"},
                "correct_answer": "Beta",
            }
        )
        pdf = PdfExporter.export(exam)
        text = _pdf_text(pdf)
        for option in ("Alpha", "Beta", "Gamma"):
            assert option in text
        assert _pdf_checkbox_count(pdf) == 3

    def test_multiple_choice_renders_one_empty_checkbox_per_option(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Aussagen stimmen?",
                "question_type": "multiple_choice",
                "options": ["Eins", "Zwei", "Drei", "Vier"],
                "correct_answer": '["Eins", "Drei"]',
            }
        )
        pdf = PdfExporter.export(exam)
        assert _pdf_checkbox_count(pdf) == 4

    def test_true_false_renders_two_checkboxes_labelled_wahr_and_falsch(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 1.0,
                "question_text": "Heapify ist linear.",
                "question_type": "true_false",
                "options": None,
                "correct_answer": "Wahr",
            }
        )
        pdf = PdfExporter.export(exam)
        text = _pdf_text(pdf)
        assert "Wahr" in text
        assert "Falsch" in text
        assert _pdf_checkbox_count(pdf) == 2

    def test_open_ended_renders_three_answer_lines_per_point(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 4.0,
                "question_text": "Erläutern Sie den Ablauf.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
        )
        pdf = PdfExporter.export(exam)
        assert _pdf_answer_line_count(pdf) == 12
        assert _pdf_checkbox_count(pdf) == 0

    def test_open_ended_renders_at_least_three_answer_lines(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 0.5,
                "question_text": "Kurz begründen.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
        )
        assert _pdf_answer_line_count(PdfExporter.export(exam)) == 3

    def test_answer_lines_are_far_enough_apart_to_write_on(self):
        """Ruled lines a candidate cannot write between are useless on paper.
        Ordinary ruled paper sits at roughly 8 mm; require at least 7 mm."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 3.0,
                "question_text": "Ausführlich begründen.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
        )
        gaps = _pdf_answer_line_gaps_mm(PdfExporter.export(exam))
        assert gaps, "no answer lines found"
        assert min(gaps) >= 7.0, f"answer lines only {min(gaps):.1f} mm apart"


class TestPdfExporterSolutions:
    def test_include_solutions_renders_answer_and_explanation(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data, include_solutions=True))
        assert "Musterlösung" in text
        assert "C) Beide" in text
        assert "O(n) amortisiert." in text
        assert "Heapify kann top-down und bottom-up arbeiten." in text

    def test_without_solutions_no_solution_information_reaches_the_pdf(
        self, sample_exam_data
    ):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data, include_solutions=False))
        assert "Musterlösung" not in text
        assert "O(n) amortisiert." not in text
        for q in sample_exam_data["questions"]:
            assert q["explanation"] not in text

    def test_without_solutions_options_still_render(self, sample_exam_data):
        """The MC options are the answer *area*, not the solution — they must
        survive the solution suppression."""
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(sample_exam_data, include_solutions=False))
        assert "A) Top-down" in text
        assert "C) Beide" in text

    def test_multi_answer_solution_is_printed_as_a_readable_list(self):
        """``correct_answer`` is stored as a JSON array for multiple_choice.
        Raw JSON on a printed marking guide is unreadable."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Verfahren sind stabil?",
                "question_type": "multiple_choice",
                "options": ["Mergesort", "Quicksort", "Insertion Sort"],
                "correct_answer": '["Mergesort", "Insertion Sort"]',
                "explanation": None,
            }
        )
        text = _pdf_text(PdfExporter.export(exam, include_solutions=True))
        assert "Musterlösung: Mergesort, Insertion Sort" in text
        assert "[" not in text
        assert '"' not in text

    def test_malformed_json_looking_solution_is_printed_unchanged(self):
        """A ``correct_answer`` that starts with '[' but isn't valid JSON
        (e.g. from a corrupted or hand-edited DB row) must not crash the
        export — ``json.loads`` raises, and the raw text is the fallback."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Verfahren sind stabil?",
                "question_type": "multiple_choice",
                "options": ["Mergesort", "Quicksort"],
                "correct_answer": "[Mergesort, Incomplete",
                "explanation": None,
            }
        )
        text = _pdf_text(PdfExporter.export(exam, include_solutions=True))
        assert "Musterlösung: [Mergesort, Incomplete" in text

    def test_json_solution_that_is_not_a_list_of_strings_is_printed_unchanged(self):
        """A ``correct_answer`` that parses as JSON but isn't a list of
        strings (e.g. a legacy list of option indices) must fall back to
        the raw text rather than being silently coerced or crashing."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Verfahren sind stabil?",
                "question_type": "multiple_choice",
                "options": ["Mergesort", "Quicksort", "Insertion Sort"],
                "correct_answer": "[0, 2]",
                "explanation": None,
            }
        )
        text = _pdf_text(PdfExporter.export(exam, include_solutions=True))
        assert "Musterlösung: [0, 2]" in text

    def test_non_json_solution_is_printed_unchanged(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Welche Aussage stimmt?",
                "question_type": "single_choice",
                "options": ["A) Eins", "B) Zwei"],
                "correct_answer": "B) Zwei",
                "explanation": None,
            }
        )
        text = _pdf_text(PdfExporter.export(exam, include_solutions=True))
        assert "Musterlösung: B) Zwei" in text

    def test_solutions_omitted_per_question_when_answer_missing(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 2.0,
                "question_text": "Ohne hinterlegte Lösung.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": None,
                "explanation": None,
            }
        )
        text = _pdf_text(PdfExporter.export(exam, include_solutions=True))
        assert "Musterlösung" not in text


class TestPdfExporterMarkdown:
    """Question text is authored in Markdown; raw markers must never reach
    the printed sheet (same failure class as TF-420 / TF-429)."""

    def _exam_with_question_text(self, question_text: str) -> dict:
        return _single_question_exam(
            {
                "position": 1,
                "points": 1.0,
                "question_text": question_text,
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "egal",
            }
        )

    def test_bold_and_italic_markers_are_not_printed(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Das ist **fett** und das *kursiv* gesetzt."
        )
        text = _pdf_text(PdfExporter.export(exam))
        assert "Das ist fett und das kursiv gesetzt." in text
        assert "**" not in text

    def test_heading_marker_is_stripped_but_text_survives(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text("# Kapitel Eins\n\nWas gilt hier?")
        text = _pdf_text(PdfExporter.export(exam))
        assert "Kapitel Eins" in text
        assert "Was gilt hier?" in text
        assert "#" not in text

    def test_list_items_become_bulleted_lines_without_dash_markers(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Ordnen Sie zu:\n\n- Erster Punkt\n- Zweiter Punkt\n- Dritter Punkt"
        )
        text = _pdf_text(PdfExporter.export(exam))
        for item in ("Erster Punkt", "Zweiter Punkt", "Dritter Punkt"):
            assert item in text
            assert f"- {item}" not in text
        assert text.count("•") == 3

    def test_code_block_content_is_kept_and_fences_are_dropped(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Was gibt der Code aus?\n\n```python\nprint(sum([1, 2]))\n```"
        )
        text = _pdf_text(PdfExporter.export(exam))
        assert "print(sum([1, 2]))" in text
        assert "```" not in text

    def test_code_block_uses_a_monospaced_font(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Was gibt der Code aus?\n\n```python\nprint(sum([1, 2]))\n```"
        )
        assert "Courier" in _pdf_span_font(
            PdfExporter.export(exam), "print(sum([1, 2]))"
        )

    def test_bold_run_is_actually_rendered_bold(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text("Ein **fettes** Wort.")
        assert "Bold" in _pdf_span_font(PdfExporter.export(exam), "fettes")

    def test_markdown_in_solution_and_explanation_is_converted(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        sample_exam_data["questions"][1]["correct_answer"] = "**O(n)** amortisiert"
        sample_exam_data["questions"][1]["explanation"] = "Siehe *Skript*, Kapitel 3"
        text = _pdf_text(PdfExporter.export(sample_exam_data, include_solutions=True))
        assert "O(n) amortisiert" in text
        assert "Siehe Skript, Kapitel 3" in text
        assert "**" not in text

    def test_html_in_question_text_is_escaped_not_interpreted(self):
        """Angle brackets from the author are content, not markup — they must
        neither crash the ReportLab parser nor smuggle styling."""
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Vergleichen Sie a < b & c > d in <script>alert(1)</script>"
        )
        text = _pdf_text(PdfExporter.export(exam))
        assert "a < b & c > d" in text
        assert "alert(1)" in text

    def test_unbalanced_inline_html_does_not_break_the_export(self):
        """An author who types a stray ``<b>`` must not make the whole export
        fail — ReportLab parses Paragraph content as XML and would reject
        unbalanced markup."""
        from services.exam_export_service import PdfExporter

        exam = self._exam_with_question_text(
            "Ein <b>offener Fettdruck und </i> zu viel"
        )
        text = _pdf_text(PdfExporter.export(exam))
        assert "offener Fettdruck" in text
        assert "zu viel" in text


def _pdf_font_is_embedded(pdf_bytes: bytes, font_name: str) -> bool:
    """Whether ``font_name`` is embedded in the file rather than referenced.

    ReportLab's standard-14 fonts (Helvetica & co) are *not* embedded —
    the reader substitutes whatever it has locally, which is exactly how
    accented characters turn into replacement glyphs on someone else's
    printer.
    """
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            for _xref, ext, _ftype, basefont, _name, _enc in page.get_fonts():
                if font_name in basefont and ext != "n/a":
                    return True
    return False


class TestExporterLanguage:
    """The export follows the *exam's* language, not the exporting user's UI
    locale: a German exam printed by a French-speaking teacher still goes to
    German-speaking candidates."""

    def _exam(self, language: str, **overrides) -> dict:
        exam = {
            "title": "Titel",
            "course": "Kurs X",
            "time_limit_minutes": 90,
            "instructions": "Lest alles.",
            "total_points": 3.0,
            "passing_percentage": 50.0,
            "language": language,
            "questions": [
                {
                    "position": 1,
                    "points": 1.0,
                    "question_text": "Stimmt das?",
                    "question_type": "true_false",
                    "options": None,
                    "correct_answer": "Wahr",
                    "explanation": "Weil.",
                },
                {
                    "position": 2,
                    "points": 2.0,
                    "question_text": "Begründe.",
                    "question_type": "open_ended",
                    "options": None,
                    "correct_answer": "Darum",
                    "explanation": None,
                },
            ],
        }
        exam.update(overrides)
        return exam

    @pytest.mark.parametrize(
        "language,course,question,total",
        [
            ("de", "Kurs", "Frage", "Gesamtpunktzahl"),
            ("en", "Course", "Question", "Total points"),
            ("fr", "Cours", "Question", "Total des points"),
            ("it", "Corso", "Domanda", "Punteggio totale"),
        ],
    )
    def test_pdf_labels_follow_the_exam_language(
        self, language, course, question, total
    ):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(self._exam(language)))
        assert f"{course}:" in text
        assert f"{question} 1" in text
        assert f"{total}:" in text

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("de", ("Wahr", "Falsch")),
            ("en", ("True", "False")),
            ("fr", ("Vrai", "Faux")),
            ("it", ("Vero", "Falso")),
        ],
    )
    def test_true_false_options_follow_the_exam_language(self, language, expected):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(self._exam(language)))
        for label in expected:
            assert label in text

    @pytest.mark.parametrize(
        "language,one,many",
        [
            ("de", "1 Punkt)", "2 Punkte)"),
            ("en", "1 point)", "2 points)"),
            ("fr", "1 point)", "2 points)"),
            ("it", "1 punto)", "2 punti)"),
        ],
    )
    def test_points_are_pluralised_per_language(self, language, one, many):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(PdfExporter.export(self._exam(language)))
        assert one in text
        assert many in text

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("de", "Seite 1 von 1"),
            ("en", "Page 1 of 1"),
            ("fr", "Page 1 sur 1"),
            ("it", "Pagina 1 di 1"),
        ],
    )
    def test_page_footer_follows_the_exam_language(self, language, expected):
        from services.exam_export_service import PdfExporter

        assert expected in _pdf_text(PdfExporter.export(self._exam(language)))

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("de", "Musterlösung"),
            ("en", "Sample solution"),
            ("fr", "Corrigé"),
            ("it", "Soluzione"),
        ],
    )
    def test_solution_box_follows_the_exam_language(self, language, expected):
        from services.exam_export_service import PdfExporter

        text = _pdf_text(
            PdfExporter.export(self._exam(language), include_solutions=True)
        )
        assert expected in text

    @pytest.mark.parametrize(
        "language,expected",
        [
            ("de", "Offene Frage"),
            ("en", "Open question"),
            ("fr", "Question ouverte"),
            ("it", "Domanda aperta"),
        ],
    )
    def test_question_type_label_follows_the_exam_language(self, language, expected):
        from services.exam_export_service import PdfExporter

        assert expected in _pdf_text(PdfExporter.export(self._exam(language)))

    def test_markdown_export_follows_the_exam_language_too(self):
        md = MarkdownExporter.export(self._exam("en"), include_solutions=True)
        assert "**Course:**" in md
        assert "## Question 1" in md
        assert "Sample solution" in md
        # The German label is gone — "Kurs X" as a *value* must survive.
        assert "**Kurs:**" not in md
        assert "Kurs X" in md

    def test_missing_language_falls_back_to_german(self):
        from services.exam_export_service import PdfExporter

        exam = self._exam("de")
        del exam["language"]
        assert "Frage 1" in _pdf_text(PdfExporter.export(exam))

    def test_unsupported_language_falls_back_to_german(self):
        from services.exam_export_service import PdfExporter

        assert "Frage 1" in _pdf_text(PdfExporter.export(self._exam("es")))


class TestPdfExporterTypography:
    def test_german_french_italian_characters_survive_round_trip(self):
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 1.0,
                "question_text": "Prüfung über Grösse — français: à, è, ç, œ; "
                "italiano: perché, è, così",
                "question_type": "single_choice",
                "options": ["Größenordnung", "Ça marche", "Perciò"],
                "correct_answer": "Ça marche",
            }
        )
        text = _pdf_text(PdfExporter.export(exam))
        assert (
            "Prüfung über Grösse — français: à, è, ç, œ; italiano: perché, è, così"
            in (text)
        )
        assert "Größenordnung" in text
        assert "Ça marche" in text
        assert "Perciò" in text

    def test_body_text_font_is_embedded_in_the_document(self, sample_exam_data):
        from services.exam_export_service import PdfExporter

        pdf = PdfExporter.export(sample_exam_data)
        font = _pdf_span_font(pdf, "Wie funktioniert Heapify?")
        assert _pdf_font_is_embedded(pdf, font), (
            f"body font {font!r} is not embedded — accented characters would "
            "depend on the reader's own fonts"
        )


def _pdf_page_texts(pdf_bytes: bytes) -> list[str]:
    import fitz

    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        return [page.get_text() for page in doc]


def _pdf_answer_lines_per_page(pdf_bytes: bytes) -> list[int]:
    import fitz

    counts = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
        for page in doc:
            counts.append(
                sum(
                    1
                    for path in page.get_drawings()
                    for item in path["items"]
                    if item[0] == "l" and abs(item[1].y - item[2].y) < 0.5
                )
            )
    return counts


def _multi_page_exam(question_count: int, points: float = 1.0) -> dict:
    """An exam long enough to span several pages, one open question each."""
    return {
        "title": "Mehrseitige Prüfung",
        "total_points": question_count * points,
        "passing_percentage": 60.0,
        "questions": [
            {
                "position": i,
                "points": points,
                "question_text": f"Beschreiben Sie Sachverhalt {i}.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
            for i in range(1, question_count + 1)
        ],
    }


class TestPdfExporterPagination:
    def test_every_page_carries_page_number_and_exam_title(self):
        from services.exam_export_service import PdfExporter

        pages = _pdf_page_texts(PdfExporter.export(_multi_page_exam(20)))
        assert len(pages) >= 2
        for index, page_text in enumerate(pages, start=1):
            assert f"Seite {index} von {len(pages)}" in page_text
            assert "Mehrseitige Prüfung" in page_text

    def test_footer_title_longer_than_seventy_characters_is_truncated(self):
        """_numbered_canvas truncates the footer title at 70 characters —
        a threshold and truncation point independent of filename_stem's
        80-char cap on the download filename, so it needs its own test."""
        from services.exam_export_service import PdfExporter

        exam = _multi_page_exam(20)
        long_title = "A" * 100
        exam["title"] = long_title
        pages = _pdf_page_texts(PdfExporter.export(exam))
        assert len(pages) >= 2

        truncated = long_title[:69] + "…"
        # The full title is only printed once, in the page-1 heading —
        # later pages carry only the truncated footer form.
        assert truncated in pages[-1]
        assert long_title not in pages[-1]

    def test_question_is_never_split_from_its_answer_area(self):
        """Each open question owns exactly three answer lines, so a page whose
        line count is not three times its question count has a split question.
        """
        from services.exam_export_service import PdfExporter

        pdf = PdfExporter.export(_multi_page_exam(20))
        pages = _pdf_page_texts(pdf)
        lines_per_page = _pdf_answer_lines_per_page(pdf)

        for page_text, line_count in zip(pages, lines_per_page):
            heading_count = page_text.count("Frage ")
            assert line_count == 3 * heading_count, (
                f"page has {heading_count} question(s) but {line_count} answer "
                "lines — a question was split from its answer area"
            )

    def test_question_taller_than_one_page_is_allowed_to_break(self):
        """A single oversized question must still render — falling back to a
        page break beats dropping it or looping forever."""
        from services.exam_export_service import PdfExporter

        exam = _single_question_exam(
            {
                "position": 1,
                "points": 40.0,
                "question_text": "Sehr ausführlich begründen.",
                "question_type": "open_ended",
                "options": None,
                "correct_answer": "Antwort",
            }
        )
        pdf = PdfExporter.export(exam)
        assert len(_pdf_page_texts(pdf)) > 1
        assert "Sehr ausführlich begründen." in _pdf_text(pdf)
        assert _pdf_answer_line_count(pdf) == 120
