"""
Exam Export Service for ExamCraft AI
Exports exams to Markdown, PDF, JSON, Moodle XML, and ILIAS QTI formats.
"""

import json
import logging
import math
from html.parser import HTMLParser
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape as _xml_escape

import markdown as _markdown

from services.grading.deterministic_grader import DeterministicGrader
from services.translation_service import DEFAULT_LOCALE, t
from utils.question_options import normalize_options

logger = logging.getLogger(__name__)

_QUESTION_TYPES = frozenset(
    {"single_choice", "multiple_choice", "true_false", "open_ended"}
)


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
        locale = _exam_locale(exam_data)
        total_points = exam_data["total_points"]
        passing_pct = exam_data["passing_percentage"]

        lines = []
        lines.append(f"# {exam_data['title']}\n")

        if exam_data.get("course"):
            lines.append(
                f"**{t('export_course', locale=locale)}:** {exam_data['course']}  "
            )
        if exam_data.get("exam_date"):
            lines.append(
                f"**{t('export_date', locale=locale)}:** {exam_data['exam_date']}  "
            )
        if exam_data.get("time_limit_minutes"):
            lines.append(
                f"**{t('export_time_limit', locale=locale)}:** "
                f"{exam_data['time_limit_minutes']} "
                f"{t('export_minutes', locale=locale)}  "
            )
        if exam_data.get("allowed_aids"):
            lines.append(
                f"**{t('export_allowed_aids', locale=locale)}:** "
                f"{exam_data['allowed_aids']}  "
            )

        lines.append(
            f"**{t('export_total_points', locale=locale)}:** "
            f"{_points_label(total_points, locale)}  "
        )
        lines.append(
            f"**{t('export_pass_mark', locale=locale)}:** {passing_pct}% "
            f"({_points_label(round(total_points * passing_pct / 100), locale)})  "
        )

        if exam_data.get("instructions"):
            lines.append(
                f"\n## {t('export_instructions', locale=locale)}\n\n"
                f"{exam_data['instructions']}\n"
            )

        lines.append("\n---\n")

        question_word = t("export_question", locale=locale)
        for q in exam_data["questions"]:
            pts_label = _points_label(q["points"], locale)
            lines.append(
                f"## {question_word} {q['position']} ({pts_label}) "
                f"— {_type_label(q['question_type'], locale)}\n"
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
                lines.append(
                    f"\n- [ ] {t('export_true', locale=locale)}\n"
                    f"- [ ] {t('export_false', locale=locale)}\n"
                )
            else:
                lines.append(
                    f"\n*{t('export_answer', locale=locale)}:*\n\n\\  \n\\  \n\\  \n"
                )

            if include_solutions and q.get("correct_answer"):
                lines.append(
                    f"\n> **{t('export_sample_solution', locale=locale)}:** "
                    f"{q['correct_answer']}"
                )
                if q.get("explanation"):
                    lines.append(
                        f">\n> **{t('export_explanation', locale=locale)}:** "
                        f"{q['explanation']}"
                    )
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
        use ``export_with_slot_mapping``; callers that need to warn about
        skipped/unscoreable questions use ``export_with_skipped`` (review
        follow-up, mirrors ``IliasQtiExporter.export_with_skipped``).
        """
        xml, _ = MoodleXmlExporter.export_with_slot_mapping(exam_data)
        return xml

    @staticmethod
    def export_with_slot_mapping(
        exam_data: dict,
    ) -> tuple[str, list[dict]]:
        """Return ``(xml, slot_mapping)`` for the round-trip.

        ``slot_mapping`` lists, in export order, dicts with the keys
        ``exam_question_id``, ``position`` and ``slot`` — one entry per
        *exported* question only. A skipped/unscoreable question (see
        ``export_with_skipped``) gets no slot, matching the slot numbers
        Moodle itself assigns on import (1..N over the questions actually
        present in the XML) rather than a phantom slot for a question that
        was never written (review follow-up — the old unconditional
        ``enumerate`` would have desynced the mapping from Moodle's real
        slots as soon as any question was skipped). The mapping is the
        anchor for the later
        ``POST /api/v1/exams/{id}/sync-moodle-question-ids`` round-trip.
        """
        xml, slot_mapping, _ = MoodleXmlExporter._export(exam_data)
        return xml, slot_mapping

    @staticmethod
    def export_with_skipped(exam_data: dict) -> tuple[str, list[int]]:
        """Return ``(xml, skipped_positions)``.

        A question is skipped — omitted from the XML, its ``position``
        recorded here — when its ``correct_answer`` matches none of its
        options/tokens: it would otherwise export as an item nobody can
        score. Mirrors ``IliasQtiExporter.export_with_skipped`` (review
        follow-up: the Moodle exporter has quietly skipped unscoreable
        ``multiple_choice`` questions since TF-403, and now
        ``single_choice``/``true_false`` too, but never surfaced that to
        the caller before — the export endpoint now warns the Dozent for
        Moodle exports exactly like it already does for ILIAS)."""
        xml, _, skipped_positions = MoodleXmlExporter._export(exam_data)
        return xml, skipped_positions

    @staticmethod
    def _export(exam_data: dict) -> tuple[str, list[dict], list[int]]:
        try:
            return MoodleXmlExporter._export_impl(exam_data)
        except Exception:
            logger.exception(
                "Export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export_impl(exam_data: dict) -> tuple[str, list[dict], list[int]]:
        quiz = Element("quiz")
        slot_mapping: list[dict] = []
        skipped_positions: list[int] = []
        slot = 0

        for order, q in enumerate(exam_data["questions"], start=1):
            qtype = q["question_type"]
            if qtype == "single_choice":
                skipped = _add_mc_question(quiz, q)
            elif qtype == "multiple_choice":
                skipped = _add_multichoice_multi_question(quiz, q)
            elif qtype == "true_false":
                skipped = _add_tf_question(quiz, q)
            else:
                _add_essay_question(quiz, q)
                skipped = False

            if skipped:
                skipped_positions.append(q.get("position", order))
                continue

            # Record the slot the question lands on. Defaults are
            # forgiving so the exporter still works on payload shapes
            # that don't include the FK (legacy callers/tests).
            slot += 1
            slot_mapping.append(
                {
                    "exam_question_id": q.get("exam_question_id"),
                    "position": q.get("position", order),
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
        return xml, slot_mapping, skipped_positions


class IliasQtiExporter:
    """QTI 1.2.1 export for ILIAS (TF-782).

    Structure verified against a real ILIAS-10.11 sample export from the
    pilot customer (Linear TF-781/TF-782): root element
    ``<questestinterop>``, ILIAS's ``QUESTIONTYPE`` metadata field
    (``assSingleChoice``/``assMultipleChoice``/``assTextQuestion``), and
    ``<response_lid rcardinality="Single|Multiple">`` for choice
    questions. Produces a standalone document (not ILIAS's full
    Container-Export ZIP with manifest.xml + components/) — per the
    documented workflow, a plain QTI file is reimportable via a
    Fragenpool's "Fragen" tab, which is the smaller-scope target.

    ``true_false`` has no confirmed dedicated ILIAS type in the sample —
    mapped as a best-effort ``assSingleChoice`` with two options
    (using the exam's own true/false wording), pending the customer's
    test-import round-trip.
    """

    @staticmethod
    def export(exam_data: dict) -> str:
        """Backwards-compatible: returns just the XML.

        Callers that need to warn the user about unscoreable/skipped
        questions use ``export_with_skipped`` instead (TF-782 review)."""
        xml, _ = IliasQtiExporter.export_with_skipped(exam_data)
        return xml

    @staticmethod
    def export_with_skipped(exam_data: dict) -> tuple[str, list[int]]:
        """Return ``(xml, skipped_positions)``.

        A question is skipped — omitted from the XML, its ``position``
        recorded here — when its ``correct_answer`` matches none of its
        ``options``: it would otherwise export as an item nobody can
        score. Exporting that silently made the data loss invisible to
        the user (TF-782 review); the caller (the export endpoint)
        surfaces ``skipped_positions`` back to the frontend so the
        Dozent finds out before submitting the file to ILIAS."""
        try:
            return IliasQtiExporter._export(exam_data)
        except Exception:
            logger.exception(
                "ILIAS QTI export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export(exam_data: dict) -> tuple[str, list[int]]:
        questestinterop = Element("questestinterop")
        assessment = SubElement(
            questestinterop, "assessment", title=exam_data.get("title") or ""
        )
        section = SubElement(assessment, "section", ident="root_section")
        locale = _exam_locale(exam_data)
        skipped_positions: list[int] = []

        for order, q in enumerate(exam_data["questions"], start=1):
            qtype = q["question_type"]
            if qtype == "single_choice":
                skipped = _add_ilias_choice_item(section, q, order, multiple=False)
            elif qtype == "multiple_choice":
                skipped = _add_ilias_multiple_choice_item(section, q, order)
            elif qtype == "true_false":
                skipped = _add_ilias_true_false_item(section, q, order, locale)
            else:
                _add_ilias_text_item(section, q, order)
                skipped = False
            if skipped:
                skipped_positions.append(q.get("position", order))

        raw_xml = tostring(questestinterop, encoding="unicode")
        dom = parseString(raw_xml)
        pretty = dom.toprettyxml(indent="  ")
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(lines)
        return xml, skipped_positions


def _format_ilias_points(value: float) -> str:
    """Format a point value for ILIAS QTI numeric fields: whole numbers
    without a trailing ``.0`` (``"4"``, not ``"4.0"``) — the verified
    sample shows plain integers even where the field is declared
    ``vartype="Integer"``, which a stray ``.0`` might not parse against.
    Rounded to 4 decimal places first (mirrors
    ``DeterministicGrader._grade_multiple_response``'s own rounding) so an
    uneven point split (e.g. 1 point over 3 correct options) doesn't leak
    a 16-digit float into the XML (TF-782 review)."""
    rounded = round(value, 4)
    return str(int(rounded)) if rounded == int(rounded) else str(rounded)


def _ilias_item(section: Element, q: dict, question_type: str, order: int) -> Element:
    """New ``<item>`` with ILIAS's ``QUESTIONTYPE`` metadata field set and
    the question text as ``<presentation>`` material. ``ident`` uses the
    question's export order rather than its own ``position`` field —
    positions aren't guaranteed unique across an exam's questions, and a
    duplicate/missing position would otherwise produce two ``<item>``
    elements sharing an ``ident``, which is invalid/ambiguous QTI
    (TF-782 review). Returns the item so callers can append
    ``<response_*>``/``<resprocessing>``."""
    item = SubElement(
        section,
        "item",
        ident=f"exam_q_{order}",
        title=f"Frage {q.get('position', order)}",
    )
    itemmetadata = SubElement(item, "itemmetadata")
    qtimetadata = SubElement(itemmetadata, "qtimetadata")
    field = SubElement(qtimetadata, "qtimetadatafield")
    SubElement(field, "fieldlabel").text = "QUESTIONTYPE"
    SubElement(field, "fieldentry").text = question_type

    presentation = SubElement(item, "presentation")
    flow = SubElement(presentation, "flow")
    material = SubElement(flow, "material")
    SubElement(material, "mattext", texttype="text/xhtml").text = _md_to_html(
        q["question_text"]
    )
    return item


def _ilias_flow(item: Element) -> Element | None:
    return item.find("presentation/flow")


def _add_ilias_choice_item(
    section: Element, q: dict, order: int, *, multiple: bool
) -> bool:
    """Single- or multi-answer choice item (``assSingleChoice`` /
    ``assMultipleChoice``).

    Correct-option membership is decided on grader-normalized tokens (see
    ``_normalized_option_token``) for *both* single and multiple choice —
    so the export marks exactly the options ``DeterministicGrader`` scores
    as correct (TF-782 review: the single-choice branch used to compare
    raw option strings, so a letter-prefixed option like ``"A) Bern"``
    never matched a plain ``correct_answer`` of ``"Bern"`` and every
    option silently scored 0, with no warning).

    Wrong options score 0 for single choice (only one option can be
    selected, so no penalty is needed) and a symmetric negative fraction
    for multiple choice — mirroring ``DeterministicGrader.
    _grade_multiple_response`` and the Moodle multi-select exporter
    (``_add_multichoice_multi_question``) — so selecting every option can
    never net full marks (TF-782 review: wrong options previously scored
    a flat 0 here too, so ticking every box scored full marks in ILIAS
    unlike in ExamCraft/Moodle).

    Returns ``True`` if the question had no scoreable option and was
    skipped (nothing is appended to ``section`` in that case) — the
    caller collects skipped positions to warn the user instead of
    silently shipping an unscoreable question."""
    # options has historically also been persisted as a legacy
    # Dict[str, str] (see utils/question_options.py) — normalizing here
    # avoids silently iterating the dict's keys ('A'/'B'/'C') instead of
    # its values and therefore matching nothing (review follow-up: the PDF
    # exporter already guards against this the same way).
    options = normalize_options(q.get("options")) or []
    raw_correct = q.get("correct_answer", "") or ""
    option_tokens = [(_normalized_option_token(opt), opt) for opt in options]

    if multiple:
        correct_set = DeterministicGrader._parse_answer_set(raw_correct)
    else:
        token = _normalized_option_token(raw_correct)
        correct_set = {token} if token else set()

    k = sum(1 for tok, _ in option_tokens if tok in correct_set)
    if k == 0:
        logger.warning(
            "ILIAS %s question at position %s: keine Option passt zur "
            "correct_answer %r — Frage wird NICHT exportiert (unbewertbar).",
            "multi-choice" if multiple else "single-choice",
            q.get("position"),
            raw_correct,
        )
        return True

    is_correct = [tok in correct_set for tok, _ in option_tokens]
    n_wrong = len(options) - k
    points_per_correct = q["points"] / k
    points_per_wrong = -(q["points"] / n_wrong) if multiple and n_wrong else 0.0

    item = _ilias_item(
        section, q, "assMultipleChoice" if multiple else "assSingleChoice", order
    )
    flow = _ilias_flow(item)
    response_lid = SubElement(
        flow,
        "response_lid",
        ident="MCSR",
        rcardinality="Multiple" if multiple else "Single",
    )
    # No shuffle: options are frequently letter-prefixed ("A) …", "B) …"),
    # matching the Moodle exporter's shuffleanswers="0" so ILIAS doesn't
    # scramble an already-lettered list (TF-782 review).
    render_choice = SubElement(response_lid, "render_choice", shuffle="No")

    resprocessing = SubElement(item, "resprocessing")
    SubElement(SubElement(resprocessing, "outcomes"), "decvar")

    for idx, (_tok, opt) in enumerate(option_tokens):
        label = SubElement(render_choice, "response_label", ident=str(idx))
        material = SubElement(label, "material")
        SubElement(material, "mattext", texttype="text/xhtml").text = _md_to_html(opt)

        respcondition = SubElement(resprocessing, "respcondition", {"continue": "Yes"})
        conditionvar = SubElement(respcondition, "conditionvar")
        SubElement(conditionvar, "varequal", respident="MCSR").text = str(idx)
        points = points_per_correct if is_correct[idx] else points_per_wrong
        SubElement(respcondition, "setvar", action="Add").text = _format_ilias_points(
            points
        )
    return False


def _add_ilias_multiple_choice_item(section: Element, q: dict, order: int) -> bool:
    return _add_ilias_choice_item(section, q, order, multiple=True)


def _add_ilias_true_false_item(
    section: Element, q: dict, order: int, locale: str
) -> bool:
    """Best-effort mapping (no confirmed dedicated ILIAS type, see class
    docstring): a two-option ``assSingleChoice``.

    Token recognition reuses ``DeterministicGrader._to_bool`` — the same
    DE/EN synonym set the grading engine itself uses (``wahr``/``true``/
    ``richtig``/``ja``/``yes``/``1``/``stimmt``/``korrekt``/``t`` vs.
    ``falsch``/``false``/``nein``/``no``/``0``/...) — so the exported
    answer key always matches what ExamCraft itself grades (TF-782
    review: a hardcoded ``wahr``/``true``/``richtig``-only check silently
    inverted the key for tokens like ``"ja"``). Option labels follow the
    exam's own language via ``t("export_true"/"export_false")`` since
    they are candidate-facing text, not Moodle's internal true/false
    values (TF-782 review: previously hardcoded to German
    "Wahr"/"Falsch" regardless of exam language).

    Returns ``True`` (skipped) if ``correct_answer`` matches neither the
    true nor the false token set — the same "skip and report" contract as
    ``_add_ilias_choice_item`` (review follow-up: a first version of this
    fix guessed "falsch" and exported it anyway, which is worse than the
    original silent-skip bug it replaced — a guessed answer key used for
    real grading is more dangerous than a visibly missing question)."""
    is_true = DeterministicGrader._to_bool(q.get("correct_answer"))
    if is_true is None:
        logger.warning(
            "ILIAS true_false question at position %s: correct_answer %r "
            "not recognized as wahr/falsch — Frage wird NICHT exportiert "
            "(unbewertbar).",
            q.get("position"),
            q.get("correct_answer"),
        )
        return True
    label_true = t("export_true", locale=locale)
    label_false = t("export_false", locale=locale)
    synthetic_q = dict(q)
    synthetic_q["options"] = [label_true, label_false]
    synthetic_q["correct_answer"] = label_true if is_true else label_false
    return _add_ilias_choice_item(section, synthetic_q, order, multiple=False)


def _add_ilias_text_item(section: Element, q: dict, order: int) -> None:
    """``assTextQuestion`` (open_ended) — free-text response, human-graded
    in ILIAS (``scoremodel="HumanRater"``), same as ExamCraft's own model."""
    item = _ilias_item(section, q, "assTextQuestion", order)
    flow = _ilias_flow(item)
    response_str = SubElement(
        flow, "response_str", ident="TEXT", rcardinality="Ordered"
    )
    render_fib = SubElement(response_str, "render_fib", fibtype="String", prompt="Box")
    SubElement(render_fib, "response_label", ident="A")

    resprocessing = SubElement(item, "resprocessing", scoremodel="HumanRater")
    SubElement(
        SubElement(resprocessing, "outcomes"),
        "decvar",
        varname="WritingScore",
        vartype="Integer",
        minvalue="0",
        maxvalue=_format_ilias_points(q["points"]),
    )


def _exam_locale(exam_data: dict) -> str:
    """The language an export is rendered in.

    Deliberately the *exam's* language, not the exporting user's UI locale:
    the sheet goes to the candidates, so a German exam stays German even
    when a French-speaking teacher downloads it. ``t()`` falls back to the
    default locale for anything unsupported or missing.
    """
    return exam_data.get("language") or DEFAULT_LOCALE


def _points_label(points: float, locale: str = DEFAULT_LOCALE) -> str:
    """Render a point count with the right number word for ``locale``.

    Exactly one point is singular ("1 Punkt", "1 point", "1 punto");
    everything else, fractions included ("0.5 Punkte"), is plural. Whole
    numbers drop the ".0" so a printed sheet reads "3 Punkte", not
    "3.0 Punkte". Shared by the Markdown and PDF exporters so the two
    cannot drift apart.
    """
    amount = int(points) if points == int(points) else points
    key = "export_points_one" if amount == 1 else "export_points_other"
    return t(key, locale=locale, count=amount)


def _type_label(question_type: str, locale: str = DEFAULT_LOCALE) -> str:
    if question_type not in _QUESTION_TYPES:
        return question_type
    return t(f"export_type_{question_type}", locale=locale)


def _add_mc_question(quiz: Element, q: dict) -> bool:
    """single_choice -> Moodle ``multichoice``/``<single>true</single>``.

    Matches on the same grader-normalized token as ``_normalized_option_token``
    uses for ``multiple_choice``/the ILIAS exporter (review follow-up): a
    letter-prefixed option like ``"A) Bern"`` now matches a plain
    ``correct_answer`` of ``"Bern"``, where a raw string comparison
    previously left every option scoring 0 with no warning. options is
    normalized the same way the PDF exporter already does — the column has
    historically also held a legacy ``Dict[str, str]`` shape.

    Returns ``True`` (skipped) if no option matches — same "skip and
    report" contract as the sibling ``_add_multichoice_multi_question``,
    rather than shipping an unscoreable question."""
    options = normalize_options(q.get("options")) or []
    correct_token = _normalized_option_token(q.get("correct_answer") or "")
    option_tokens = [(_normalized_option_token(opt), opt) for opt in options]

    if not correct_token or not any(tok == correct_token for tok, _ in option_tokens):
        logger.warning(
            "MC question at position %s: correct_answer %r matches no "
            "option — Frage wird NICHT exportiert (unbewertbar).",
            q.get("position"),
            q.get("correct_answer"),
        )
        return True

    question = SubElement(quiz, "question", type="multichoice")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])
    SubElement(question, "single").text = "true"
    SubElement(question, "shuffleanswers").text = "0"

    for tok, opt in option_tokens:
        answer = SubElement(
            question, "answer", fraction="100" if tok == correct_token else "0"
        )
        SubElement(answer, "text").text = opt
        feedback = SubElement(answer, "feedback")
        SubElement(feedback, "text").text = ""

    if q.get("explanation"):
        gf = SubElement(question, "generalfeedback", format="html")
        SubElement(gf, "text").text = _md_to_html(q["explanation"])
    return False


def _format_fraction(value: float) -> str:
    """Format a Moodle fraction: whole numbers without trailing ``.0``
    (``"50"``, ``"-50"``, ``"-100"``), thirds with 5 decimal places
    (``"33.33333"``) as required by Moodle's fixed fraction set."""
    rounded = round(value, 5)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.5f}"


def _add_multichoice_multi_question(quiz: Element, q: dict) -> bool:
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
    so it is skipped with a loud warning rather than shipped broken.
    Returns ``True`` if skipped."""
    # options has historically also been persisted as a legacy
    # Dict[str, str] (see utils/question_options.py) — normalizing here
    # avoids silently iterating the dict's keys instead of its values
    # (review follow-up, mirrors the same fix in the ILIAS exporter).
    options = normalize_options(q.get("options")) or []
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
        return True

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
    return False


def _add_tf_question(quiz: Element, q: dict) -> bool:
    """Token recognition reuses ``DeterministicGrader._to_bool`` — the same
    DE/EN synonym set the grading engine itself uses — so the exported
    answer key always matches what ExamCraft itself grades (TF-822: a
    hardcoded wahr/true/richtig-only check silently inverted the key for
    tokens like "ja", mirroring the bug fixed in the ILIAS exporter by
    TF-782).

    Returns ``True`` (skipped) if ``correct_answer`` matches neither the
    true nor the false token set — never export a guessed answer key for
    real grading (review follow-up: an earlier version guessed "falsch"
    and exported it anyway, which is worse than a visibly missing
    question)."""
    is_true = DeterministicGrader._to_bool(q.get("correct_answer"))
    if is_true is None:
        logger.warning(
            "Moodle true_false question at position %s: correct_answer %r "
            "not recognized as wahr/falsch — Frage wird NICHT exportiert "
            "(unbewertbar).",
            q.get("position"),
            q.get("correct_answer"),
        )
        return True

    question = SubElement(quiz, "question", type="truefalse")
    name = SubElement(question, "name")
    SubElement(name, "text").text = f"Frage {q['position']}"
    qtext = SubElement(question, "questiontext", format="html")
    SubElement(qtext, "text").text = _md_to_html(q["question_text"])
    SubElement(question, "defaultgrade").text = str(q["points"])

    answer_true = SubElement(question, "answer", fraction="100" if is_true else "0")
    SubElement(answer_true, "text").text = "true"
    answer_false = SubElement(question, "answer", fraction="0" if is_true else "100")
    SubElement(answer_false, "text").text = "false"
    return False


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


# ---------------------------------------------------------------------------
# PDF (TF-656) — print-ready exam sheet
# ---------------------------------------------------------------------------


# ReportLab's ``Paragraph`` understands only a small inline subset of HTML.
# Everything a Markdown author can write has to be mapped onto it, dropped,
# or promoted to its own flowable.
_PDF_MD_EXTENSIONS = ["sane_lists", "nl2br", "fenced_code"]
_PDF_INLINE_TAGS = {
    "strong": "b",
    "b": "b",
    "em": "i",
    "i": "i",
    "u": "u",
    "sup": "super",
    "sub": "sub",
}
_PDF_BLOCK_TAGS = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "div", "ul", "ol"}
)


class _PdfMarkdownParser(HTMLParser):
    """Reduce Markdown-generated HTML to blocks ReportLab can render.

    Yields ``(kind, content)`` pairs where *kind* is ``"para"``,
    ``"bullet"`` or ``"code"``. Inline tags are mapped onto the subset
    ``Paragraph`` supports; list items and code blocks become their own
    flowables because ``Paragraph`` cannot express them; every other tag
    is dropped while its text content is kept.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._buffer: list[str] = []
        self._kind = "para"
        self._in_pre = False
        # Inline tags still open. ReportLab parses Paragraph content as
        # strict XML, so an author's stray "<b>" would abort the entire
        # export unless we balance the markup ourselves.
        self._open_inline: list[str] = []

    def _flush(self):
        # Close anything left open so the block is valid XML on its own.
        self._buffer.extend(f"</{tag}>" for tag in reversed(self._open_inline))
        self._open_inline.clear()
        raw = "".join(self._buffer)
        # Code keeps its indentation; prose does not keep its stray newlines.
        content = raw.strip("\n") if self._kind == "code" else raw.strip()
        if content:
            self.blocks.append((self._kind, content))
        self._buffer = []
        self._kind = "para"

    def close(self):
        super().close()
        self._flush()

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self._flush()
            self._in_pre = True
            self._kind = "code"
            return
        if self._in_pre:
            return
        if tag == "li":
            self._flush()
            self._kind = "bullet"
            return
        if tag in _PDF_BLOCK_TAGS:
            self._flush()
            return
        if tag == "br":
            self._buffer.append("<br/>")
            return
        mapped = _PDF_INLINE_TAGS.get(tag)
        if mapped:
            self._open_inline.append(mapped)
            self._buffer.append(f"<{mapped}>")

    def handle_endtag(self, tag):
        if tag == "pre":
            self._flush()
            self._in_pre = False
            return
        if self._in_pre:
            return
        if tag == "li" or tag in _PDF_BLOCK_TAGS:
            self._flush()
            return
        mapped = _PDF_INLINE_TAGS.get(tag)
        # Only close what is actually open, and only in order — a stray
        # "</i>" inside a <b> run is dropped rather than emitted.
        if mapped and self._open_inline and self._open_inline[-1] == mapped:
            self._open_inline.pop()
            self._buffer.append(f"</{mapped}>")

    def handle_data(self, data):
        self._buffer.append(data if self._in_pre else _pdf_escape(data))


def _md_to_flowables(
    text: str | None, styles: dict, style_key: str = "body", prefix: str = ""
) -> list:
    """Render Markdown source as print-ready flowables.

    ``prefix`` is raw Paragraph markup (e.g. a bold label) merged into the
    first paragraph so a label and its text share a line.
    """
    from reportlab.platypus import Paragraph, Preformatted

    parser = _PdfMarkdownParser()
    parser.feed(_markdown.markdown(text or "", extensions=_PDF_MD_EXTENSIONS))
    parser.close()

    blocks = parser.blocks
    if prefix:
        if blocks and blocks[0][0] == "para":
            blocks[0] = ("para", prefix + blocks[0][1])
        else:
            blocks.insert(0, ("para", prefix))

    flowables = []
    for kind, content in blocks:
        if kind == "code":
            flowables.append(Preformatted(content, styles["code"]))
        elif kind == "bullet":
            flowables.append(Paragraph(content, styles["indent"], bulletText="•"))
        else:
            flowables.append(Paragraph(content, styles[style_key]))
    return flowables


def _pdf_escape(value) -> str:
    """Escape a value for ReportLab's ``Paragraph`` mini-XML dialect.

    ``Paragraph`` parses its content as XML, so a raw ``&`` or ``<`` from
    user-authored text aborts the whole export. Everything that reaches a
    Paragraph passes through here first.
    """
    if value is None:
        return ""
    return _xml_escape(str(value), {'"': "&quot;", "'": "&apos;"})


class PdfExporter:
    """Print-ready exam sheet as PDF (ReportLab)."""

    @staticmethod
    def export(exam_data: dict, include_solutions: bool = False) -> bytes:
        try:
            return PdfExporter._export(exam_data, include_solutions)
        except Exception:
            logger.exception(
                "Export failed for exam '%s'",
                exam_data.get("title", "unknown"),
            )
            raise

    @staticmethod
    def _export(exam_data: dict, include_solutions: bool = False) -> bytes:
        # reportlab is heavy — import lazily so smoke imports of this module
        # don't pull the lib unless PDF export is actually used.
        import io

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            KeepTogether,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
        )

        styles = _pdf_styles()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            title=exam_data["title"],
        )

        locale = _exam_locale(exam_data)
        story: list = []
        story.extend(_pdf_header(exam_data, styles))
        story.append(Spacer(1, 0.3 * cm))
        story.extend(_pdf_fill_in_block(styles, doc.width, locale))

        if exam_data.get("instructions"):
            story.append(Spacer(1, 0.3 * cm))
            story.append(
                Paragraph(t("export_instructions", locale=locale), styles["heading"])
            )
            story.extend(_md_to_flowables(exam_data["instructions"], styles))

        for q in exam_data["questions"]:
            # A question and its answer area belong together: KeepTogether
            # pushes the whole group to the next page rather than tearing the
            # answer lines off the question. Groups taller than a page are
            # split by reportlab anyway, which is what we want — an oversized
            # question must still print.
            story.append(
                KeepTogether(
                    [
                        Spacer(1, 0.35 * cm),
                        *_pdf_question(q, styles, doc.width, include_solutions, locale),
                    ]
                )
            )

        doc.build(story, canvasmaker=_numbered_canvas(exam_data["title"], locale))
        return buffer.getvalue()


def _numbered_canvas(exam_title: str, locale: str = DEFAULT_LOCALE):
    """Canvas that stamps "page X of Y" and the exam title on every page.

    The total page count is unknown while a page is being laid out, so the
    pages are buffered and the footer drawn on the way out — the usual
    reportlab two-pass trick.
    """
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas as pdf_canvas

    font, _bold = _register_pdf_fonts()
    # Keep a long title from colliding with the page counter.
    title = exam_title if len(exam_title) <= 70 else exam_title[:69] + "…"

    class _NumberedCanvas(pdf_canvas.Canvas):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._buffered_pages = []

        def showPage(self):
            self._buffered_pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            total = len(self._buffered_pages)
            for state in self._buffered_pages:
                self.__dict__.update(state)
                self._draw_footer(total)
                super().showPage()
            super().save()

        def _draw_footer(self, total: int):
            page_width = self._pagesize[0]
            self.setFont(font, 8)
            self.setFillColor(colors.grey)
            self.drawString(2 * cm, 1.2 * cm, title)
            self.drawRightString(
                page_width - 2 * cm,
                1.2 * cm,
                t(
                    "export_page_x_of_y",
                    locale=locale,
                    current=self._pageNumber,
                    total=total,
                ),
            )

    return _NumberedCanvas


_CHECKBOX_CLASS = None


def _checkbox_class():
    """Build (once) the tick-box flowable.

    Defined lazily rather than at module scope so that merely importing
    this module does not pull reportlab in — the same reason every other
    reportlab import here sits inside a function.

    The box is *drawn*, not typed: the obvious ``☐`` (U+2610) is absent
    from the embedded font, so a text checkbox would print as a
    replacement glyph on the exam sheet.
    """
    global _CHECKBOX_CLASS
    if _CHECKBOX_CLASS is not None:
        return _CHECKBOX_CLASS

    from reportlab.lib.units import cm
    from reportlab.platypus import Flowable

    class _CheckBox(Flowable):
        def __init__(self, size=0.32 * cm):
            super().__init__()
            self.size = size
            self.width = self.height = size

        def draw(self):
            self.canv.setLineWidth(0.7)
            self.canv.rect(0, 0, self.size, self.size)

    _CHECKBOX_CLASS = _CheckBox
    return _CHECKBOX_CLASS


def _pdf_question(
    q: dict,
    styles: dict,
    content_width: float,
    include_solutions: bool,
    locale: str = DEFAULT_LOCALE,
) -> list:
    """One question: heading, question text and the type-specific answer area."""
    from reportlab.platypus import Paragraph

    flowables = [
        Paragraph(
            f"{t('export_question', locale=locale)} {_pdf_escape(q['position'])} "
            f"({_points_label(q['points'], locale)}) "
            f"— {_pdf_escape(_type_label(q['question_type'], locale))}",
            styles["heading"],
        ),
        *_md_to_flowables(q["question_text"], styles),
    ]
    flowables.extend(_pdf_answer_area(q, styles, content_width, locale))
    if include_solutions and q.get("correct_answer"):
        flowables.append(_pdf_solution_box(q, styles, content_width, locale))
    return flowables


def _readable_answer(correct_answer: str) -> str:
    """Turn a stored answer into something readable on paper.

    ``multiple_choice`` answers are persisted as a JSON array (the
    canonical form ``DeterministicGrader`` parses). Printing that verbatim
    would put ``["A", "B"]`` on a marking guide, so a JSON array becomes a
    comma-separated list. Anything that is not a JSON array of strings —
    the legacy and single-answer forms — is left untouched.
    """
    text = (correct_answer or "").strip()
    if not text.startswith("["):
        return text
    try:
        parsed = json.loads(text)
    except (ValueError, TypeError):
        return text
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return ", ".join(parsed)
    return text


def _pdf_solution_box(
    q: dict, styles: dict, content_width: float, locale: str = DEFAULT_LOCALE
):
    """Sample solution in a visually set-off box.

    Only ever reached when ``include_solutions`` is true — the caller
    decides, so that a candidate's sheet carries no solution text at all,
    not even hidden.
    """
    from reportlab.lib import colors
    from reportlab.platypus import Table, TableStyle

    lines = _md_to_flowables(
        _readable_answer(q["correct_answer"]),
        styles,
        prefix=f"<b>{t('export_sample_solution', locale=locale)}:</b> ",
    )
    if q.get("explanation"):
        lines.extend(
            _md_to_flowables(
                q["explanation"],
                styles,
                prefix=f"<b>{t('export_explanation', locale=locale)}:</b> ",
            )
        )

    table = Table([[lines]], colWidths=[content_width])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.whitesmoke),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def _pdf_answer_area(
    q: dict, styles: dict, content_width: float, locale: str = DEFAULT_LOCALE
) -> list:
    """The blank area a candidate fills in, per question type."""
    from reportlab.platypus import Spacer

    question_type = q["question_type"]
    if question_type in ("single_choice", "multiple_choice"):
        # options has historically also been persisted as a legacy
        # Dict[str, str] (see utils/question_options.py) — normalizing
        # here avoids silently printing the dict's keys ('A'/'B'/'C')
        # instead of the real answer text.
        options = normalize_options(q.get("options")) or []
    elif question_type == "true_false":
        options = [
            t("export_true", locale=locale),
            t("export_false", locale=locale),
        ]
    else:
        return [Spacer(1, 4), *_pdf_answer_lines(q["points"])]
    return [Spacer(1, 4), _pdf_option_boxes(options, styles, content_width)]


def _pdf_option_boxes(options: list, styles: dict, content_width: float):
    """Options as a two-column table: tick box left, option text right."""
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    check_box = _checkbox_class()
    box_column = 0.9 * cm
    rows = [
        [check_box(), Paragraph(_pdf_escape(option), styles["body"])]
        for option in options
    ]
    table = Table(rows, colWidths=[box_column, content_width - box_column])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (0, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _pdf_answer_lines(points: float) -> list:
    """Ruled writing lines for open questions: 3 per point, never fewer than 3.

    The gap matches ordinary ruled paper (~8.5 mm). Platypus collapses the
    space between two flowables to the larger of the two, so the leading is
    carried by ``spaceBefore`` alone — setting both would not double it.
    """
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.platypus.flowables import HRFlowable

    line_count = max(3, math.ceil(points * 3))
    return [
        HRFlowable(
            width="100%",
            thickness=0.5,
            color=colors.grey,
            spaceBefore=0.85 * cm,
            spaceAfter=0,
        )
        for _ in range(line_count)
    ]


_PDF_FONT = "ExamSans"
_PDF_FONTS_REGISTERED = False


def _register_pdf_fonts() -> tuple[str, str]:
    """Register the exam sheet's font family; return ``(regular, bold)``.

    ReportLab's default Helvetica is a standard-14 font and therefore is
    *not* embedded — the reader substitutes a local font, which is how
    umlauts, accents and cedillas end up as replacement glyphs on a
    printed exam. Bitstream Vera Sans ships inside reportlab itself (no
    new dependency, no system font lookup) and covers German, French and
    Italian, so it is registered and embedded instead.
    """
    global _PDF_FONTS_REGISTERED

    if _PDF_FONTS_REGISTERED:
        return _PDF_FONT, f"{_PDF_FONT}-Bold"

    import os

    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_dir = os.path.join(os.path.dirname(reportlab.__file__), "fonts")
    faces = {
        _PDF_FONT: "Vera.ttf",
        f"{_PDF_FONT}-Bold": "VeraBd.ttf",
        f"{_PDF_FONT}-Italic": "VeraIt.ttf",
        f"{_PDF_FONT}-BoldItalic": "VeraBI.ttf",
    }
    for name, filename in faces.items():
        pdfmetrics.registerFont(TTFont(name, os.path.join(font_dir, filename)))
    # Without the family mapping, <b>/<i> inside a Paragraph would silently
    # keep the regular face.
    pdfmetrics.registerFontFamily(
        _PDF_FONT,
        normal=_PDF_FONT,
        bold=f"{_PDF_FONT}-Bold",
        italic=f"{_PDF_FONT}-Italic",
        boldItalic=f"{_PDF_FONT}-BoldItalic",
    )
    _PDF_FONTS_REGISTERED = True
    return _PDF_FONT, f"{_PDF_FONT}-Bold"


def _pdf_styles() -> dict:
    """Paragraph styles for the exam sheet."""
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm

    font, font_bold = _register_pdf_fonts()
    base = ParagraphStyle(
        "ExamBody", fontName=font, fontSize=10, leading=14, spaceAfter=2
    )
    return {
        "title": ParagraphStyle(
            "ExamTitle",
            parent=base,
            fontName=font_bold,
            fontSize=17,
            leading=21,
            spaceAfter=8,
        ),
        "meta": base,
        "heading": ParagraphStyle(
            "ExamHeading",
            parent=base,
            fontName=font_bold,
            fontSize=12,
            leading=16,
            spaceBefore=6,
            spaceAfter=4,
        ),
        "body": base,
        "fill_in": ParagraphStyle(
            "ExamFillIn", parent=base, fontSize=11, leading=22, spaceAfter=4
        ),
        "indent": ParagraphStyle(
            "ExamIndent", parent=base, leftIndent=0.7 * cm, spaceAfter=1
        ),
        # Courier is a standard-14 font and thus not embedded, but reportlab
        # ships no monospaced TTF and its WinAnsi encoding still covers every
        # de/fr/it character — acceptable for the rare fenced code block.
        "code": ParagraphStyle(
            "ExamCode",
            parent=base,
            fontName="Courier",
            fontSize=9,
            leading=12,
            leftIndent=0.5 * cm,
        ),
    }


def _pdf_header(exam_data: dict, styles: dict) -> list:
    """Title + metadata block.

    The field set mirrors ``MarkdownExporter`` exactly so the MD and PDF
    exports cannot drift apart (TF-656).
    """
    from reportlab.platypus import Paragraph

    flowables = [Paragraph(_pdf_escape(exam_data["title"]), styles["title"])]

    locale = _exam_locale(exam_data)
    meta: list[str] = []
    if exam_data.get("course"):
        meta.append(
            f"<b>{t('export_course', locale=locale)}:</b> "
            f"{_pdf_escape(exam_data['course'])}"
        )
    if exam_data.get("exam_date"):
        meta.append(
            f"<b>{t('export_date', locale=locale)}:</b> "
            f"{_pdf_escape(exam_data['exam_date'])}"
        )
    if exam_data.get("time_limit_minutes"):
        meta.append(
            f"<b>{t('export_time_limit', locale=locale)}:</b> "
            f"{_pdf_escape(exam_data['time_limit_minutes'])} "
            f"{t('export_minutes', locale=locale)}"
        )
    if exam_data.get("allowed_aids"):
        meta.append(
            f"<b>{t('export_allowed_aids', locale=locale)}:</b> "
            f"{_pdf_escape(exam_data['allowed_aids'])}"
        )

    total_points = exam_data["total_points"]
    passing_pct = exam_data["passing_percentage"]
    meta.append(
        f"<b>{t('export_total_points', locale=locale)}:</b> "
        f"{_points_label(total_points, locale)}"
    )
    meta.append(
        f"<b>{t('export_pass_mark', locale=locale)}:</b> {passing_pct}% "
        f"({_points_label(round(total_points * passing_pct / 100), locale)})"
    )

    flowables.extend(Paragraph(line, styles["meta"]) for line in meta)
    return flowables


def _pdf_fill_in_block(styles: dict, content_width: float, locale: str) -> list:
    """Name / class fill-in lines directly below the header.

    Laid out as a table so both rules start at the same x despite the
    labels differing in width. The rules are underscores rather than drawn
    lines so they cannot be confused with an answer line.
    """
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, Table, TableStyle

    label_column = 2 * cm
    rule = "_" * 44
    rows = [
        [
            Paragraph(f"{t(key, locale=locale)}:", styles["fill_in"]),
            Paragraph(rule, styles["fill_in"]),
        ]
        for key in ("export_name", "export_class")
    ]
    table = Table(rows, colWidths=[label_column, content_width - label_column])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return [table]
