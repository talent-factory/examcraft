"""
Exam Export Service for ExamCraft AI
Exports exams to Markdown, JSON, and Moodle XML formats.
"""

import json
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

import markdown as _markdown

from services.grading.deterministic_grader import DeterministicGrader

logger = logging.getLogger(__name__)


def _normalized_option_token(text: str) -> str:
    """Normalize an option string exactly like the grader's
    ``_parse_answer_set`` (trim + lowercase + Moodle letter-prefix
    stripping), so the Moodle export marks the same options correct that
    ``DeterministicGrader`` scores as correct (TF-403). Without this the
    export compares raw option text while the grader compares normalized
    tokens, and letter-keyed ``correct_answer`` data grades and exports
    inconsistently."""
    norm = DeterministicGrader._normalise(text)
    stripped = DeterministicGrader._strip_letter_prefix(norm)
    return stripped if stripped else norm


def _md_to_html(text: str | None) -> str:
    """Convert Markdown source to HTML for Moodle's ``format="html"`` fields.

    Question and feedback text is authored in Markdown, but Moodle renders
    these fields as HTML (the elements carry ``format="html"``). Without
    conversion, Markdown markers such as ``**`` or ``- `` show up literally
    after import and paragraph/line structure is lost (TF-404). Converting
    here lets bold text, lists and paragraphs render correctly in Moodle.
    """
    if not text:
        return ""
    return _markdown.markdown(text, extensions=["sane_lists", "nl2br"])


class MarkdownExporter:
    @staticmethod
    def export(exam_data: dict, include_solutions: bool = False) -> str:
        try:
            return MarkdownExporter._export(exam_data, include_solutions)
        except Exception:
            logger.exception(
                "Export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export(exam_data: dict, include_solutions: bool = False) -> str:
        lines = []
        lines.append(f"# {exam_data['title']}\n")

        if exam_data.get("course"):
            lines.append(f"**Kurs:** {exam_data['course']}  ")
        if exam_data.get("exam_date"):
            lines.append(f"**Datum:** {exam_data['exam_date']}  ")
        if exam_data.get("time_limit_minutes"):
            lines.append(f"**Zeitlimit:** {exam_data['time_limit_minutes']} Minuten  ")
        if exam_data.get("allowed_aids"):
            lines.append(f"**Erlaubte Hilfsmittel:** {exam_data['allowed_aids']}  ")

        lines.append(f"**Gesamtpunktzahl:** {exam_data['total_points']} Punkte  ")
        lines.append(
            f"**Bestehensgrenze:** {exam_data['passing_percentage']}% "
            f"({exam_data['total_points'] * exam_data['passing_percentage'] / 100:.0f} Punkte)  "
        )

        if exam_data.get("instructions"):
            lines.append(f"\n## Hinweise\n\n{exam_data['instructions']}\n")

        lines.append("\n---\n")

        for q in exam_data["questions"]:
            pts = q["points"]
            pts_label = f"{int(pts) if pts == int(pts) else pts} Punkte"
            lines.append(
                f"## Frage {q['position']} ({pts_label}) — {_type_label(q['question_type'])}\n"
            )
            lines.append(f"{q['question_text']}\n")

            if q["question_type"] in ("single_choice", "multiple_choice") and q.get(
                "options"
            ):
                lines.append("")
                for opt in q["options"]:
                    lines.append(f"- [ ] {opt}")
                lines.append("")
            elif q["question_type"] == "true_false":
                lines.append("\n- [ ] Wahr\n- [ ] Falsch\n")
            else:
                lines.append("\n*Antwort:*\n\n\\  \n\\  \n\\  \n")

            if include_solutions and q.get("correct_answer"):
                lines.append(f"\n> **Musterlösung:** {q['correct_answer']}")
                if q.get("explanation"):
                    lines.append(f">\n> **Erklärung:** {q['explanation']}")
                lines.append("")

            lines.append("\n---\n")

        return "\n".join(lines)


class JsonExporter:
    @staticmethod
    def export(exam_data: dict) -> str:
        try:
            return JsonExporter._export(exam_data)
        except Exception:
            logger.exception(
                "Export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export(exam_data: dict) -> str:
        output = {
            "exam": {
                "title": exam_data["title"],
                "course": exam_data.get("course"),
                "exam_date": exam_data.get("exam_date"),
                "time_limit_minutes": exam_data.get("time_limit_minutes"),
                "allowed_aids": exam_data.get("allowed_aids"),
                "instructions": exam_data.get("instructions"),
                "total_points": exam_data["total_points"],
                "passing_percentage": exam_data["passing_percentage"],
                "language": exam_data.get("language", "de"),
            },
            "questions": [
                {
                    "position": q["position"],
                    "points": q["points"],
                    "question_text": q["question_text"],
                    "question_type": q["question_type"],
                    "difficulty": q.get("difficulty"),
                    "options": q.get("options"),
                    "correct_answer": q.get("correct_answer"),
                    "explanation": q.get("explanation"),
                }
                for q in exam_data["questions"]
            ],
        }
        return json.dumps(output, ensure_ascii=False, indent=2)


class MoodleXmlExporter:
    @staticmethod
    def export(exam_data: dict) -> str:
        """Backwards-compatible: returns just the XML.

        Callers that need the slot mapping for the round-trip (TF-336)
        use ``export_with_slot_mapping`` instead.
        """
        xml, _ = MoodleXmlExporter.export_with_slot_mapping(exam_data)
        return xml

    @staticmethod
    def export_with_slot_mapping(
        exam_data: dict,
    ) -> tuple[str, list[dict]]:
        """Return ``(xml, slot_mapping)`` for the round-trip.

        ``slot_mapping`` lists, in export order, dicts with the keys
        ``exam_question_id``, ``position`` and ``slot`` (which equals
        ``position`` because Moodle assigns slots 1..N in the order the
        XML lists them, and we don't reorder). The mapping is the
        anchor for the later
        ``POST /api/v1/exams/{id}/sync-moodle-question-ids`` round-trip.
        """
        try:
            return MoodleXmlExporter._export_with_mapping(exam_data)
        except Exception:
            logger.exception(
                "Export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export_with_mapping(exam_data: dict) -> tuple[str, list[dict]]:
        quiz = Element("quiz")
        slot_mapping: list[dict] = []

        for slot, q in enumerate(exam_data["questions"], start=1):
            qtype = q["question_type"]
            if qtype == "single_choice":
                _add_mc_question(quiz, q)
            elif qtype == "multiple_choice":
                _add_multichoice_multi_question(quiz, q)
            elif qtype == "true_false":
                _add_tf_question(quiz, q)
            else:
                _add_essay_question(quiz, q)
            # Record the slot the question lands on. Defaults are
            # forgiving so the exporter still works on payload shapes
            # that don't include the FK (legacy callers/tests).
            slot_mapping.append(
                {
                    "exam_question_id": q.get("exam_question_id"),
                    "position": q.get("position", slot),
                    "slot": slot,
                }
            )

        raw_xml = tostring(quiz, encoding="unicode")
        dom = parseString(raw_xml)
        pretty = dom.toprettyxml(indent="  ")
        # Remove the default XML declaration added by toprettyxml and add our own
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lines)
        return xml, slot_mapping


def _type_label(question_type: str) -> str:
    return {
        "single_choice": "Einfachauswahl",
        "multiple_choice": "Mehrfachauswahl",
        "true_false": "Wahr/Falsch",
        "open_ended": "Offene Frage",
    }.get(question_type, question_type)


def _add_mc_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="multichoice")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])
    SubElement(question, "single").text = "true"
    SubElement(question, "shuffleanswers").text = "0"

    correct = q.get("correct_answer", "")
    if correct and correct not in (q.get("options") or []):
        logger.warning(
            "MC question at position %s: correct_answer '%s' does not match any option",
            q.get("position"),
            correct,
        )
    for opt in q.get("options", []):
        answer = SubElement(
            question, "answer", fraction="100" if opt == correct else "0"
        )
        SubElement(answer, "text").text = opt
        feedback = SubElement(answer, "feedback")
        SubElement(feedback, "text").text = ""

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = _md_to_html(q["explanation"])


def _format_fraction(value: float) -> str:
    """Format a Moodle fraction: whole numbers without trailing ``.0``
    (``"50"``, ``"-50"``, ``"-100"``), thirds with 5 decimal places
    (``"33.33333"``) as required by Moodle's fixed fraction set."""
    rounded = round(value, 5)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.5f}"


def _add_multichoice_multi_question(quiz: Element, q: dict):
    """Export a multi-answer ``multiple_choice`` question as a Moodle
    multichoice with ``<single>false</single>`` and partial fractions.

    For k correct of N options, each correct option gets ``100/k`` and
    each wrong option ``-100/(N-k)`` so a fully-correct selection scores
    100 and over-selecting is penalised. Fractions are formatted to
    Moodle's fixed set (whole numbers plain, thirds to 5 dp).

    Membership is decided on grader-normalized tokens (see
    ``_normalized_option_token``) so the export marks exactly the options
    ``DeterministicGrader`` scores as correct. If no option matches the
    correct set (``k == 0`` — malformed/letter-mismatched data) the
    question would export with every option negative and be unscoreable,
    so it is skipped with a loud warning rather than shipped broken."""
    options = q.get("options") or []
    raw_correct = q.get("correct_answer", "") or ""
    # Same parser the grader uses: JSON-array canonical form, comma/
    # semicolon legacy fallback, trim + lowercase + letter-prefix strip.
    # Logs on its own when a JSON-looking value fails to parse.
    correct_set = DeterministicGrader._parse_answer_set(raw_correct)
    option_tokens = [(_normalized_option_token(opt), opt) for opt in options]
    k = sum(1 for tok, _ in option_tokens if tok in correct_set)

    if k == 0:
        logger.warning(
            "Multi-choice question at position %s: keine Option passt zur "
            "correct_answer %r — Frage wird NICHT exportiert (unbewertbar).",
            q.get("position"),
            raw_correct,
        )
        return

    question = SubElement(quiz, "question", type="multichoice")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])
    SubElement(question, "single").text = "false"
    SubElement(question, "shuffleanswers").text = "0"

    n_wrong = len(options) - k
    pos_fraction = _format_fraction(100 / k)
    neg_fraction = _format_fraction(-100 / n_wrong) if n_wrong else "0"

    for tok, opt in option_tokens:
        fraction = pos_fraction if tok in correct_set else neg_fraction
        answer = SubElement(question, "answer", fraction=fraction)
        SubElement(answer, "text").text = opt
        feedback = SubElement(answer, "feedback")
        SubElement(feedback, "text").text = ""

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = _md_to_html(q["explanation"])


def _add_tf_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="truefalse")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])

    correct_answer = (q.get("correct_answer") or "").lower()
    is_true = correct_answer in ("wahr", "true", "richtig")
    answer_true = SubElement(question, "answer", fraction="100" if is_true else "0")
    SubElement(answer_true, "text").text = "true"
    answer_false = SubElement(question, "answer", fraction="0" if is_true else "100")
    SubElement(answer_false, "text").text = "false"


def _add_essay_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="essay")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = _md_to_html(q["explanation"])
