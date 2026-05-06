"""Moodle Web Service driver (TF-336 / Spec 5.3).

Pulls quiz attempts directly from a Moodle instance via the REST
Web Services API. Calls (in order):

1. ``mod_quiz_get_quizzes_by_courses`` — quiz metadata; we use it to
   discover the ``cmid`` (course-module-id) belonging to the quiz, and
   to surface the resolved title in ``payload.source_metadata``.
2. ``mod_quiz_get_user_attempts`` — every user's attempt list. We pass
   ``status=finished`` because in-progress attempts have no
   ``timefinish`` and would otherwise be silently scored.
3. ``mod_quiz_get_attempt_review`` — full per-attempt response data
   (questions + given answers).

Question matching prefers ``exam_questions.external_refs.moodle_slot``,
then ``moodle_question_id``, falling back to ``position``. The slot
mapping is populated by the export round-trip (Subarea D); when
``external_refs`` is empty we degrade to position-based matching with
a warning so the operator knows to run the round-trip first.

Per-row tolerance: a single failed attempt becomes a row error; the
import continues. Hard failures (auth, network, schema mismatch) raise
``ImportDriverError`` subclasses so the job lands in ``failed``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

import httpx

from models.submission import MoodleConnection
from services.import_drivers.base import (
    BaseImportDriver,
    ImportDriverError,
    ExamLike,
)
from services.import_drivers.payloads import (
    AnswerRecord,
    AttemptRecord,
    ImportPayload,
    ImportRowError,
    StudentRef,
)
from utils.secret_encryption import SecretEncryptionError, decrypt_secret


logger = logging.getLogger(__name__)


class MoodleApiAuthError(ImportDriverError):
    """The Moodle Web Service returned an auth-rejection."""


class MoodleApiSchemaError(ImportDriverError):
    """The response did not match the expected shape."""


class MoodleConnectionMissingError(ImportDriverError):
    """No ``moodle_connections`` row exists for the institution."""


class MoodleApiDriver(BaseImportDriver):
    """REST API driver for Moodle Web Services."""

    name: ClassVar[str] = "moodle_api"

    # Single httpx client per driver instance — Moodle responds with
    # large attempt payloads and we want connection reuse across the
    # 1 + N + N×attempts call sequence.
    DEFAULT_TIMEOUT_SECONDS: ClassVar[float] = 30.0

    def parse(
        self,
        source: bytes | str,
        *,
        exam: ExamLike,
        db=None,
    ) -> ImportPayload:
        if db is None:
            raise ImportDriverError(
                "MoodleApiDriver braucht eine DB-Session, um die "
                "moodle_connections-Konfiguration zu laden."
            )
        params = self._parse_source(source)
        quiz_id = params["quiz_id"]
        institution_id = getattr(exam, "institution_id", None)
        if institution_id is None:
            # exam.institution_id missing on the stub means the caller
            # passed an exam-shaped object that's not actually attached
            # to a tenant; fail loudly.
            raise ImportDriverError(
                "Exam ohne institution_id übergeben — API-Driver "
                "benötigt Multi-Tenancy-Kontext."
            )

        connection = (
            db.query(MoodleConnection)
            .filter(MoodleConnection.institution_id == institution_id)
            .one_or_none()
        )
        if connection is None:
            raise MoodleConnectionMissingError(
                "Keine Moodle-Connection für diese Institution. "
                "Admin muss zuerst eine Verbindung anlegen."
            )

        try:
            token = decrypt_secret(connection.token_encrypted)
        except SecretEncryptionError as exc:
            raise MoodleApiAuthError(
                f"Moodle-Connection-Token konnte nicht entschlüsselt werden: {exc}"
            ) from exc

        client = self._build_client(connection.base_url, token)
        try:
            quiz_meta = self._fetch_quiz_meta(client, quiz_id)
            attempts = self._fetch_attempts(client, quiz_id)
            payload = ImportPayload(
                exam_id=exam.id,
                driver_name=self.name,
                source_metadata={
                    "moodle_base_url": connection.base_url,
                    "moodle_quiz_id": quiz_id,
                    "moodle_quiz_name": quiz_meta.get("name"),
                    "moodle_attempts_total": len(attempts),
                },
            )

            question_lookup = self._build_question_lookup(exam)
            if question_lookup["unmatched_total"] > 0:
                payload.warnings.append(
                    "Fragenmapping nutzt nur die Position — kein "
                    "external_refs gesetzt. Erst 'Moodle-IDs erfassen' "
                    "ausführen, damit Slot/Question-ID einfliessen."
                )

            students_by_id: dict[str, StudentRef] = {}
            for attempt_idx, attempt in enumerate(attempts, start=1):
                try:
                    self._process_attempt(
                        client=client,
                        attempt=attempt,
                        payload=payload,
                        students_by_id=students_by_id,
                        question_lookup=question_lookup,
                    )
                except ImportDriverError:
                    raise
                except Exception as exc:
                    logger.exception(
                        "MoodleApiDriver: Attempt %s konnte nicht verarbeitet werden",
                        attempt.get("id"),
                    )
                    payload.errors.append(
                        ImportRowError(
                            row_index=attempt_idx,
                            reason=(
                                f"Moodle-Attempt {attempt.get('id')} "
                                f"fehlgeschlagen: "
                                f"{type(exc).__name__}: {exc}"
                            ),
                        )
                    )

            # Mark connection.last_used_at — this mutation lives inside the
            # outer ImportService savepoint. If that savepoint rolls back
            # (e.g. on a pipeline failure), this update is also rolled back;
            # persistence is not guaranteed on every call.
            connection.last_used_at = datetime.now(timezone.utc)
            db.flush()
            return payload
        finally:
            client.close()

    # ------------------------------------------------------------------
    # Source parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_source(source: bytes | str) -> dict[str, int]:
        """Source is a small JSON object: ``{"quiz_id": 42}``.

        We accept ``int`` quiz_ids only — Moodle quiz ids are positive
        integers, never strings, never UUIDs. Catching the wrong type
        early makes the failure visible rather than letting the API
        return a silent empty list.
        """
        if isinstance(source, bytes):
            source = source.decode("utf-8")
        if not isinstance(source, str):
            raise ImportDriverError(
                f"MoodleApiDriver: source-Type {type(source).__name__} "
                "nicht unterstützt — JSON-String oder Bytes erwartet."
            )
        text = source.strip()
        if not text:
            raise ImportDriverError(
                "MoodleApiDriver: leerer Source-Wert — {'quiz_id': int} erwartet."
            )
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ImportDriverError(
                f"MoodleApiDriver: source ist kein gültiges JSON — {exc}"
            ) from exc
        if not isinstance(data, dict) or "quiz_id" not in data:
            raise ImportDriverError(
                "MoodleApiDriver: source-JSON braucht den Key 'quiz_id'."
            )
        try:
            quiz_id = int(data["quiz_id"])
        except (TypeError, ValueError) as exc:
            raise ImportDriverError(
                f"MoodleApiDriver: quiz_id muss eine Ganzzahl sein, "
                f"erhalten: {data['quiz_id']!r}"
            ) from exc
        if quiz_id <= 0:
            raise ImportDriverError(
                f"MoodleApiDriver: quiz_id muss > 0 sein, erhalten: {quiz_id}"
            )
        return {"quiz_id": quiz_id}

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _build_client(self, base_url: str, token: str) -> httpx.Client:
        """Configure an httpx client carrying the auth token.

        Moodle exposes every Web Service through ``/webservice/rest/server.php``
        with the function name as a POST field. We resolve the full
        endpoint per call (rather than using ``base_url=`` and POSTing
        to ``""`` — that combination triggers httpx's path
        normalisation and appends a trailing slash, which Moodle treats
        as a different route).

        ``wstoken`` and ``moodlewsrestformat`` are stashed on the client
        and added to the POST body in ``_call`` instead of the URL query
        string. Moodle accepts both, but the body keeps the token out of
        any reverse-proxy / Moodle access logs.
        """
        client = httpx.Client(timeout=self.DEFAULT_TIMEOUT_SECONDS)
        client.examcraft_endpoint = (  # type: ignore[attr-defined]
            base_url.rstrip("/") + "/webservice/rest/server.php"
        )
        client.examcraft_token = token  # type: ignore[attr-defined]
        return client

    def _call(self, client: httpx.Client, function: str, **payload: Any) -> Any:
        """POST one Web Service call and unwrap the canonical errors.

        Moodle returns a 200 body even on auth failure, encoding the
        problem as ``{"exception": ..., "errorcode": ..., "message": ...}``.
        We translate those to ``MoodleApiAuthError`` so the import job
        records the right reason.
        """
        endpoint = client.examcraft_endpoint  # type: ignore[attr-defined]
        token = client.examcraft_token  # type: ignore[attr-defined]
        try:
            response = client.post(
                endpoint,
                data={
                    "wstoken": token,
                    "moodlewsrestformat": "json",
                    "wsfunction": function,
                    **payload,
                },
            )
        except httpx.HTTPError as exc:
            raise ImportDriverError(
                f"Moodle-API erreichbarkeitsfehler ({function}): {exc}"
            ) from exc
        if response.status_code >= 500:
            raise ImportDriverError(
                f"Moodle-API HTTP {response.status_code} bei {function}"
            )
        if 400 <= response.status_code < 500:
            # 401/403/404/429 hit before we get JSON. Surface the real
            # status — without this branch the next ``response.json()``
            # tries to parse Moodle's HTML error page and the operator
            # sees a misleading "antwortete nicht mit JSON" message.
            if response.status_code == 429:
                raise ImportDriverError(
                    f"Moodle-API rate-limited ({function}): HTTP 429 "
                    "(Retry-After ignoriert — bitte später erneut versuchen)."
                )
            raise MoodleApiAuthError(
                f"Moodle-API HTTP {response.status_code} bei {function} "
                "(Token-Berechtigung oder Endpoint prüfen)."
            )
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise MoodleApiSchemaError(
                f"Moodle-API antwortete nicht mit JSON ({function})"
            ) from exc

        if isinstance(data, dict) and "exception" in data:
            errorcode = data.get("errorcode") or ""
            message = data.get("message") or "unbekannter Fehler"
            if errorcode in (
                "invalidtoken",
                "accessexception",
                "webservice_access_exception",
            ):
                raise MoodleApiAuthError(
                    f"Moodle-Auth fehlgeschlagen ({errorcode}): {message}"
                )
            raise ImportDriverError(f"Moodle-API meldet {errorcode}: {message}")
        return data

    def _fetch_quiz_meta(self, client: httpx.Client, quiz_id: int) -> dict[str, Any]:
        """Find the quiz row in any of the courses that returned by ``mod_quiz_get_quizzes_by_courses``.

        We omit the ``courseids`` argument so Moodle returns every quiz
        the token's user can see — a single account often spans multiple
        courses and pre-filtering would force the operator to also
        specify the course.
        """
        data = self._call(client, "mod_quiz_get_quizzes_by_courses")
        if not isinstance(data, dict):
            raise MoodleApiSchemaError(
                "mod_quiz_get_quizzes_by_courses hat kein Objekt geliefert"
            )
        for quiz in data.get("quizzes", []):
            try:
                if int(quiz.get("id")) == quiz_id:
                    return quiz
            except (TypeError, ValueError):
                continue
        raise ImportDriverError(
            f"Quiz {quiz_id} nicht in der Token-Sicht gefunden — "
            "Token-Berechtigung oder Course-Membership prüfen."
        )

    def _fetch_attempts(
        self, client: httpx.Client, quiz_id: int
    ) -> list[dict[str, Any]]:
        """Return *all* finished attempts; in-progress get filtered.

        Moodle requires a ``userid`` in the regular function. Setting
        ``userid=0`` switches it to the "all users" mode (only allowed
        for accounts with the ``mod/quiz:viewreports`` capability —
        which is exactly what the operator's API token must have). If
        Moodle rejects the call we surface the auth error.
        """
        data = self._call(
            client,
            "mod_quiz_get_user_attempts",
            quizid=quiz_id,
            userid=0,
            status="finished",
            includepreviews=0,
        )
        if not isinstance(data, dict) or "attempts" not in data:
            raise MoodleApiSchemaError(
                "mod_quiz_get_user_attempts antwortete ohne 'attempts'-Liste"
            )
        attempts = data["attempts"]
        if not isinstance(attempts, list):
            raise MoodleApiSchemaError("'attempts' ist keine Liste")
        return attempts

    def _fetch_attempt_review(
        self, client: httpx.Client, attempt_id: int
    ) -> dict[str, Any]:
        """Full review payload incl. per-question text and given answers."""
        data = self._call(client, "mod_quiz_get_attempt_review", attemptid=attempt_id)
        if not isinstance(data, dict):
            raise MoodleApiSchemaError(
                "mod_quiz_get_attempt_review hat kein Objekt geliefert"
            )
        return data

    # ------------------------------------------------------------------
    # Domain mapping
    # ------------------------------------------------------------------

    @staticmethod
    def _build_question_lookup(exam: ExamLike) -> dict[str, Any]:
        """Build the slot/question-id → exam_question_id maps.

        Returns a dict with three keys:

        * ``by_slot``: ``{moodle_slot: exam_question_id}``
        * ``by_question_id``: ``{moodle_question_id: exam_question_id}``
        * ``by_position``: ``{position: exam_question_id}`` (always set)
        * ``unmatched_total``: how many questions lack ``external_refs``
          (≥ 0). When > 0 the driver emits a warning.
        """
        by_slot: dict[int, int] = {}
        by_question_id: dict[int, int] = {}
        by_position: dict[int, int] = {}
        unmatched = 0
        for q in exam.questions:
            position = getattr(q, "position", None)
            if position is not None:
                by_position[int(position)] = q.id
            refs = getattr(q, "external_refs", None) or {}
            slot = refs.get("moodle_slot")
            question_id = refs.get("moodle_question_id")
            if slot is not None:
                try:
                    by_slot[int(slot)] = q.id
                except (TypeError, ValueError):
                    pass
            if question_id is not None:
                try:
                    by_question_id[int(question_id)] = q.id
                except (TypeError, ValueError):
                    pass
            if slot is None and question_id is None:
                unmatched += 1
        return {
            "by_slot": by_slot,
            "by_question_id": by_question_id,
            "by_position": by_position,
            "unmatched_total": unmatched,
        }

    @staticmethod
    def _resolve_question_id(
        question_lookup: dict[str, Any], *, slot: int | None, question_id: int | None
    ) -> int | None:
        """Match a Moodle answer to an ``exam_question_id``.

        Priority: ``moodle_slot`` → ``moodle_question_id`` → position.
        ``slot`` and ``position`` happen to coincide in unmodified
        Moodle quizzes, but Moodle's question-bank may shuffle slots
        between attempts, so we honour the explicit slot mapping when
        present and fall back to position only when no external_refs
        have been recorded yet.
        """
        if slot is not None:
            mapped = question_lookup["by_slot"].get(slot)
            if mapped is not None:
                return mapped
        if question_id is not None:
            mapped = question_lookup["by_question_id"].get(question_id)
            if mapped is not None:
                return mapped
        if slot is not None:
            return question_lookup["by_position"].get(slot)
        return None

    def _process_attempt(
        self,
        *,
        client: httpx.Client,
        attempt: dict[str, Any],
        payload: ImportPayload,
        students_by_id: dict[str, StudentRef],
        question_lookup: dict[str, Any],
    ) -> None:
        """Translate one Moodle attempt into ``StudentRef`` + ``AttemptRecord``."""
        attempt_id = int(attempt["id"])
        external_id = self._extract_user_external_id(attempt)
        if not external_id:
            raise ImportDriverError(
                f"Moodle-Attempt {attempt_id} ohne identifizierbaren "
                "User (weder userid noch email gesetzt)."
            )

        if external_id not in students_by_id:
            student = StudentRef(
                external_id=external_id,
                display_name=self._extract_user_display_name(attempt),
                class_hint=None,
            )
            students_by_id[external_id] = student
            payload.students.append(student)

        review = self._fetch_attempt_review(client, attempt_id)
        attempt_number = int(attempt.get("attempt", 1) or 1)
        started_at = self._unix_to_dt(attempt.get("timestart"))
        submitted_at = self._unix_to_dt(attempt.get("timefinish"))

        answers: list[AnswerRecord] = []
        for question in review.get("questions", []) or []:
            slot_value = question.get("slot")
            slot = (
                int(slot_value)
                if slot_value is not None and str(slot_value).isdigit()
                else None
            )
            qid = question.get("questionid")
            given = self._extract_given_answer(question)
            mark = question.get("mark")
            try:
                moodle_points = float(mark) if mark is not None else None
            except (TypeError, ValueError):
                moodle_points = None
            mapped = self._resolve_question_id(
                question_lookup,
                slot=slot,
                question_id=int(qid) if isinstance(qid, int) else None,
            )
            if mapped is None:
                payload.warnings.append(
                    f"Attempt {attempt_id}: Frage Slot={slot} "
                    f"questionid={qid} hat keine ExamCraft-Zuordnung — "
                    "Antwort wird verworfen."
                )
                continue
            answers.append(
                AnswerRecord(
                    exam_question_id=mapped,
                    given_answer=given,
                    moodle_points_awarded=moodle_points,
                )
            )

        payload.attempts.append(
            AttemptRecord(
                student_external_id=external_id,
                attempt_number=attempt_number,
                started_at=started_at,
                submitted_at=submitted_at,
                source_attempt_id=str(attempt_id),
                answers=answers,
                raw_payload={"attempt": attempt, "review": review},
            )
        )

    # ------------------------------------------------------------------
    # Mini extractors — kept static for unit-test ergonomics.
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_user_external_id(attempt: dict[str, Any]) -> str | None:
        """Pseudonym-first: prefer Moodle-User-ID over email."""
        user_id = attempt.get("userid")
        if user_id is not None:
            return str(user_id)
        email = attempt.get("useremail") or attempt.get("email")
        if email:
            return str(email).strip()
        return None

    @staticmethod
    def _extract_user_display_name(attempt: dict[str, Any]) -> str | None:
        full = attempt.get("fullname") or attempt.get("user_fullname")
        if full:
            return str(full).strip() or None
        first = attempt.get("firstname")
        last = attempt.get("lastname")
        parts = [p for p in (first, last) if p]
        return " ".join(str(p).strip() for p in parts) or None

    @staticmethod
    def _extract_given_answer(question: dict[str, Any]) -> str | None:
        # Moodle exposes the rendered answer as ``responsesummary``;
        # ``answer`` is sometimes present in custom plugins. Falling
        # through the candidates keeps us tolerant of plugin variation.
        for key in ("responsesummary", "answer", "response"):
            value = question.get(key)
            if value not in (None, ""):
                return str(value)
        return None

    @staticmethod
    def _unix_to_dt(value: Any) -> datetime | None:
        try:
            ts = int(value)
        except (TypeError, ValueError):
            return None
        if ts <= 0:
            return None
        return datetime.fromtimestamp(ts, tz=timezone.utc)
