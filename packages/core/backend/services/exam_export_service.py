"""
Exam Export Service for ExamCraft AI
Exports exams to Markdown, JSON, and Moodle XML formats.
"""

import json
import logging
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

logger = logging.getLogger(__name__)


class MarkdownExporter:
    @staticmethod
    def export(exam_data: dict, include_solutions: bool = False) -> str:
        try:
            return MarkdownExporter._export(exam_data, include_solutions)
        except Exception as exc:
            logger.error(
                "Export failed for exam '%s': %s",
                exam_data.get("title", "unknown"),
                exc,
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

            if q["question_type"] == "multiple_choice" and q.get("options"):
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
        except Exception as exc:
            logger.error(
                "Export failed for exam '%s': %s",
                exam_data.get("title", "unknown"),
                exc,
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
        try:
            return MoodleXmlExporter._export(exam_data)
        except Exception as exc:
            logger.error(
                "Export failed for exam '%s': %s",
                exam_data.get("title", "unknown"),
                exc,
            )
            raise

    @staticmethod
    def _export(exam_data: dict) -> str:
        quiz = Element("quiz")

        for q in exam_data["questions"]:
            qtype = q["question_type"]
            if qtype == "multiple_choice":
                _add_mc_question(quiz, q)
            elif qtype == "true_false":
                _add_tf_question(quiz, q)
            else:
                _add_essay_question(quiz, q)

        raw_xml = tostring(quiz, encoding="unicode")
        dom = parseString(raw_xml)
        pretty = dom.toprettyxml(indent="  ")
        # Remove the default XML declaration added by toprettyxml and add our own
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lines)


def _type_label(question_type: str) -> str:
    return {
        "multiple_choice": "Multiple Choice",
        "true_false": "Wahr/Falsch",
        "open_ended": "Offene Frage",
    }.get(question_type, question_type)


def _add_mc_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="multichoice")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = q["question_text"]
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
        SubElement(gf, "text").text = q["explanation"]


def _add_tf_question(quiz: Element, q: dict):
    question = SubElement(quiz, "question", type="truefalse")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = q["question_text"]
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
    SubElement(qtext, "text").text = q["question_text"]
    SubElement(question, "defaultgrade").text = str(q["points"])

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = q["explanation"]
