"""Feedback transports: plugin (native per-question) and gradebook (fallback). TF-435."""

from __future__ import annotations

import html
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from enums import FeedbackTransportName, StudentPushStatus
from services.moodle_feedback.payload import FeedbackPayload, StudentFeedback
from services.moodle_feedback.ws_client import MoodleWsError, call_moodle

logger = logging.getLogger(__name__)

FORMAT_HTML = 1  # Moodle FORMAT_HTML

# Per-student lookups against Moodle can fail in two ways: the WS itself errors
# (MoodleWsError), or the reply is shaped unexpectedly (missing key, empty list,
# non-numeric id). Both must degrade to a single student-level error, never abort
# the whole push — so the per-student except catches the shape errors too.
_SHAPE_ERRORS = (KeyError, IndexError, TypeError, ValueError)


@dataclass
class StudentResult:
    external_id: str  # the value pushed to Moodle (email, username, or Moodle id)
    status: StudentPushStatus
    graded: int = 0
    errors: list[str] | None = None


class FeedbackTransport(ABC):
    name: FeedbackTransportName

    @abstractmethod
    def push(self, payload: FeedbackPayload) -> dict[str, StudentResult]:
        """Push the whole payload; return per-identifier results."""


def _comment_html(raw: str) -> str:
    """Escape comment text and convert newlines to ``<br>`` for Moodle.

    The newline→``<br>`` step is the load-bearing half: Moodle renders the
    comment as HTML (``commentformat=FORMAT_HTML``) and otherwise flattens
    multi-line reviewer notes onto one line (see TF-430).
    """
    return html.escape(raw).replace("\n", "<br>")


def _normalize_status(raw: object) -> StudentPushStatus:
    """Map a plugin's wire status onto the known set; unknown → error.

    The plugin reply is untrusted input — without this an unrecognised status
    string would slip past every counter bucket in the service and be silently
    dropped from the totals.
    """
    try:
        return StudentPushStatus(str(raw))
    except ValueError:
        return StudentPushStatus.ERROR


class PluginFeedbackTransport(FeedbackTransport):
    """Transport A — native per-question via local_examcraft WS."""

    name = FeedbackTransportName.PLUGIN

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url
        self._token = token

    def push(self, payload: FeedbackPayload) -> dict[str, StudentResult]:
        results: dict[str, StudentResult] = {}
        # A student whose questions all lacked a moodle_slot has nothing to
        # transmit. Counting that as OK would land a zero-mark push in the
        # "pushed" tally, so mark PARTIAL (folds into students_failed) and
        # don't send them to the plugin.
        to_send = [s for s in payload.students if s.questions]
        for s in payload.students:
            if not s.questions:
                results[s.external_id] = StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.PARTIAL,
                    errors=["Keine Frage mit moodle_slot — nichts übertragen."],
                )
        params = {
            "quizid": payload.quiz_id,
            "students": [
                {
                    "useridentifier": s.external_id,
                    "questions": [
                        {
                            "slot": q.slot,
                            "mark": q.mark,
                            "comment": _comment_html(q.comment),
                            "commentformat": FORMAT_HTML,
                        }
                        for q in s.questions
                    ],
                }
                for s in to_send
            ],
        }
        try:
            reply = call_moodle(
                self._base_url,
                self._token,
                "local_examcraft_set_quiz_feedback",
                params,
            )
        except MoodleWsError as exc:
            # Whole-call failure → mark every sent student as error.
            logger.warning("Plugin-Feedback-Push fehlgeschlagen (gesamt): %s", exc)
            for s in to_send:
                results[s.external_id] = StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.ERROR,
                    errors=[str(exc)],
                )
            return results

        for row in reply or []:
            external_id = row.get("useridentifier", "")
            results[external_id] = StudentResult(
                external_id=external_id,
                status=_normalize_status(row.get("status")),
                graded=int(row.get("graded", 0) or 0),
                errors=list(row.get("errors") or []),
            )
        # Any sent student the plugin didn't report on → error.
        for s in to_send:
            results.setdefault(
                s.external_id,
                StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.ERROR,
                    errors=["Keine Antwort vom Plugin für diese Person."],
                ),
            )
        return results


def _moodle_lookup_field(identifier: str) -> str:
    """Choose the ``core_user_get_users_by_field`` field by identifier shape.

    ``Student.external_id`` may be an email, a Moodle username, or a numeric
    Moodle user id (per the Student model docstring). Hardcoding ``email``
    silently returns not_found for every student at institutions keyed
    otherwise. Heuristic: ``@`` → email, all-digits → id, else → username.
    Institutions keyed by ``idnumber`` (matriculation number) are not covered
    here — that needs an explicit per-institution setting (follow-up).
    """
    if "@" in identifier:
        return "email"
    if identifier.isdigit():
        return "id"
    return "username"


class GradebookFeedbackTransport(FeedbackTransport):
    """Transport B — bundled feedback block in the gradebook (standard WS)."""

    name = FeedbackTransportName.GRADEBOOK

    def __init__(self, base_url: str, token: str) -> None:
        self._base_url = base_url
        self._token = token

    def _resolve_cm(self, quiz_id: int) -> tuple[int, int]:
        reply = call_moodle(
            self._base_url,
            self._token,
            "core_course_get_course_module_by_instance",
            {"module": "quiz", "instance": quiz_id},
        )
        cm = reply.get("cm") if isinstance(reply, dict) else None
        if not isinstance(cm, dict) or "id" not in cm or "course" not in cm:
            raise MoodleWsError(
                f"Unerwartete Antwort für quiz_id={quiz_id} (kein gültiges 'cm')."
            )
        return int(cm["id"]), int(cm["course"])

    def _resolve_user_id(self, external_id: str) -> int | None:
        reply = call_moodle(
            self._base_url,
            self._token,
            "core_user_get_users_by_field",
            {"field": _moodle_lookup_field(external_id), "values": [external_id]},
        )
        if isinstance(reply, list) and reply and isinstance(reply[0], dict):
            return int(reply[0]["id"])
        return None

    def _feedback_html(self, student: StudentFeedback) -> str:
        lines = [
            f"<p>Gesamt: {student.total_points_awarded:g}/"
            f"{student.total_points_max:g} Punkte</p>",
            "<ul>",
        ]
        for q in sorted(student.questions, key=lambda x: x.slot):
            lines.append(
                f"<li><strong>Frage {q.slot}: {q.mark:g} Punkte</strong>"
                + (f" — {_comment_html(q.comment)}" if q.comment else "")
                + "</li>"
            )
        lines.append("</ul>")
        return "".join(lines)

    def push(self, payload: FeedbackPayload) -> dict[str, StudentResult]:
        results: dict[str, StudentResult] = {}
        try:
            activity_id, course_id = self._resolve_cm(payload.quiz_id)
        except (MoodleWsError, *_SHAPE_ERRORS) as exc:
            logger.warning("Gradebook-Push: Kursmodul nicht auflösbar: %s", exc)
            return {
                s.external_id: StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.ERROR,
                    errors=[str(exc)],
                )
                for s in payload.students
            }

        for s in payload.students:
            if not s.questions:
                # No slot-mapped question → nothing to transmit; PARTIAL keeps
                # it out of the "pushed" success tally (see PluginFeedbackTransport).
                results[s.external_id] = StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.PARTIAL,
                    errors=["Keine Frage mit moodle_slot — nichts übertragen."],
                )
                continue
            try:
                user_id = self._resolve_user_id(s.external_id)
                if user_id is None:
                    results[s.external_id] = StudentResult(
                        external_id=s.external_id,
                        status=StudentPushStatus.NOT_FOUND,
                        errors=["Person in Moodle nicht gefunden."],
                    )
                    continue
                call_moodle(
                    self._base_url,
                    self._token,
                    "core_grades_update_grades",
                    {
                        "source": "examcraft",
                        "courseid": course_id,
                        "component": "mod_quiz",
                        "activityid": activity_id,
                        "itemnumber": 0,
                        "grades": [
                            {
                                "studentid": user_id,
                                "grade": s.total_points_awarded,
                                "str_feedback": self._feedback_html(s),
                                "str_feedbackformat": FORMAT_HTML,
                            }
                        ],
                    },
                )
                results[s.external_id] = StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.OK,
                    graded=len(s.questions),
                )
            except (MoodleWsError, *_SHAPE_ERRORS) as exc:
                # One bad lookup/push degrades to a single error row — it must
                # not abort feedback for the remaining students.
                logger.warning("Gradebook-Push für eine Person fehlgeschlagen: %s", exc)
                results[s.external_id] = StudentResult(
                    external_id=s.external_id,
                    status=StudentPushStatus.ERROR,
                    errors=[str(exc)],
                )
        return results
