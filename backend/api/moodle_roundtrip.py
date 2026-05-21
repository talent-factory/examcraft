"""Moodle Question-ID Round-Trip API (TF-336 Subarea D).

Endpoint: ``POST /api/v1/exams/{id}/sync-moodle-question-ids``

Schliesst die Lücke zwischen ExamCraft-Export → Moodle-Upload →
ExamCraft-API-Re-Import:

1. Lehrperson exportiert die Prüfung als Moodle-XML und lädt sie in
   Moodle hoch (Moodle vergibt eigene Question-Bank-IDs).
2. Lehrperson notiert die Moodle-Quiz-ID (z. B. aus der URL der
   Quiz-Settings-Seite) und ruft diesen Endpoint auf.
3. Wir verifizieren via ``mod_quiz_get_quizzes_by_courses``, dass das
   Quiz für den gespeicherten Token sichtbar ist, und schreiben pro
   ExamCraft-Frage ``external_refs.moodle_slot = position`` plus
   ``external_refs.moodle_quiz_id`` zurück.
4. Damit kann der ``MoodleApiDriver`` beim Re-Import die Antworten
   slot-genau zuordnen — und nicht mehr nur per Position.

Annahme: Moodle vergibt Slots in der gleichen Reihenfolge, in der die
XML die Fragen auflistet (1:1 zur ExamCraft-Position). Das ist nach
einem frischen XML-Import der Default; falls die Lehrperson Fragen in
Moodle umgeordnet hat, muss sie den Endpoint nach der Umordnung erneut
aufrufen — wir überschreiben die alten Refs.

Multi-Tenancy: ``Exam.institution_id`` muss zum aufrufenden User
passen (404 bei Fremd-Institution).

RBAC: ``submissions:import`` reicht — die Lehrperson, die importiert,
ist auch die, die die Slot-Mappings pflegt. Das vermeidet einen Hop
zum Admin nur fürs Round-Trip-Setup.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models.auth import User
from models.exam import Exam
from models.submission import MoodleConnection
from utils.auth_utils import require_permission
from utils.secret_encryption import SecretEncryptionError, decrypt_secret


logger = logging.getLogger(__name__)


_STRICT_OUT = ConfigDict(extra="forbid")


router = APIRouter(prefix="/api/v1/exams", tags=["MoodleRoundtrip"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SyncMoodleQuestionIdsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    moodle_quiz_id: int = Field(gt=0)
    # Optional explicit override of the slot ↔ Moodle-question-id
    # mapping. When omitted we still write ``moodle_slot`` (= position)
    # so the API-Driver has at least the slot-anchored match.
    moodle_question_ids: list[int] | None = Field(
        default=None,
        description=(
            "Optional list of Moodle-Question-IDs in slot order "
            "(slot 1 first). Writes external_refs.moodle_question_id."
        ),
    )

    @field_validator("moodle_question_ids")
    @classmethod
    def _ids_must_be_positive_and_unique(
        cls, value: list[int] | None
    ) -> list[int] | None:
        """Catch duplicates and non-positive IDs at the schema level.

        Duplicates would corrupt ``external_refs`` (two slots mapping to
        the same Moodle-question-id breaks the API driver's reverse
        lookup); non-positive IDs are not valid Moodle question ids.
        Pydantic already rejects ``null`` entries via the inner ``int``
        type — we lock that in here too so the error message is
        consistent.
        """
        if value is None:
            return value
        if any(qid is None for qid in value):
            raise ValueError("moodle_question_ids darf keine null-Einträge enthalten.")
        if any(qid <= 0 for qid in value):
            raise ValueError("moodle_question_ids: alle IDs müssen > 0 sein.")
        if len(value) != len(set(value)):
            duplicates = sorted({qid for qid in value if value.count(qid) > 1})
            raise ValueError(
                f"moodle_question_ids enthält Duplikate: {duplicates}. "
                "Zwei Slots dürfen nicht auf dieselbe Moodle-Question-ID "
                "zeigen."
            )
        return value


class SyncedQuestionOut(BaseModel):
    model_config = _STRICT_OUT

    exam_question_id: int
    position: int
    moodle_slot: int
    moodle_question_id: int | None
    moodle_quiz_id: int


class SyncMoodleQuestionIdsOut(BaseModel):
    model_config = _STRICT_OUT

    exam_id: int
    moodle_quiz_id: int
    moodle_quiz_name: str | None
    questions: list[SyncedQuestionOut]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_exam(db: Session, user: User, exam_id: int) -> Exam:
    exam = (
        db.query(Exam)
        .options(joinedload(Exam.questions))
        .filter(
            Exam.id == exam_id,
            Exam.institution_id == user.institution_id,
        )
        .one_or_none()
    )
    if exam is None:
        raise HTTPException(status_code=404, detail="Prüfung nicht gefunden")
    return exam


async def _verify_moodle_quiz(
    *,
    base_url: str,
    token: str,
    quiz_id: int,
) -> dict[str, Any] | None:
    """Verify the quiz exists in Moodle. Returns the metadata dict or
    raises an ``HTTPException``.

    We want a *fail-fast* check before we update DB rows so the
    operator hears about a wrong quiz id immediately rather than after
    the next failed import.
    """
    endpoint = base_url.rstrip("/") + "/webservice/rest/server.php"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                endpoint,
                data={
                    "wstoken": token,
                    "moodlewsrestformat": "json",
                    "wsfunction": "mod_quiz_get_quizzes_by_courses",
                },
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Moodle-API nicht erreichbar: {exc}",
        ) from exc

    if response.status_code >= 500:
        raise HTTPException(
            status_code=502, detail=f"Moodle-API HTTP {response.status_code}"
        )
    if 400 <= response.status_code < 500:
        # Surface the real upstream status so the operator can act on
        # the response (401/403 → token, 404 → endpoint, 429 → retry).
        # Without this branch the JSON parse below tries to read an
        # HTML error body and 502s with a misleading message.
        raise HTTPException(
            status_code=502,
            detail=(
                f"Moodle-API HTTP {response.status_code} — "
                "Token-Berechtigung oder Endpoint prüfen."
            ),
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(
            status_code=502, detail="Moodle-API antwortete nicht mit JSON"
        ) from exc

    if isinstance(data, dict) and "exception" in data:
        # Surface the Moodle error verbatim — operators recognise the
        # canonical errorcodes (invalidtoken, accessexception, …).
        message = data.get("message") or "unbekannter Moodle-Fehler"
        raise HTTPException(status_code=400, detail=f"Moodle: {message}")

    if not isinstance(data, dict):
        raise HTTPException(
            status_code=502,
            detail="Moodle: 'mod_quiz_get_quizzes_by_courses' lieferte kein Objekt",
        )

    for quiz in data.get("quizzes", []) or []:
        try:
            if int(quiz.get("id")) == quiz_id:
                return quiz
        except (TypeError, ValueError):
            continue
    raise HTTPException(
        status_code=404,
        detail=(
            f"Moodle-Quiz {quiz_id} ist für den gespeicherten Token "
            "nicht sichtbar — Token-Berechtigung oder Course-Zugriff prüfen."
        ),
    )


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/{exam_id}/sync-moodle-question-ids",
    response_model=SyncMoodleQuestionIdsOut,
)
async def sync_moodle_question_ids(
    exam_id: int,
    body: SyncMoodleQuestionIdsIn,
    current_user: User = Depends(require_permission("submissions:import")),
    db: Session = Depends(get_db),
) -> SyncMoodleQuestionIdsOut:
    """Round-Trip-Phase: Moodle-Quiz-ID einsammeln und ``external_refs``
    pro ``ExamQuestion`` zurückschreiben.

    Wenn der Caller eine ``moodle_question_ids``-Liste übergibt (Slot-
    Reihenfolge), füllen wir auch ``moodle_question_id``. Sonst nur
    ``moodle_slot`` (= position) und die Quiz-ID. Die
    Slot-Voraussetzung passt zum Default-Verhalten von Moodle nach
    XML-Import; Umordnungen erfordern erneutes Sync.
    """
    exam = _load_exam(db, current_user, exam_id)
    questions = sorted(exam.questions, key=lambda q: q.position)
    if not questions:
        raise HTTPException(
            status_code=400,
            detail="Diese Prüfung hat keine Fragen — Sync nicht möglich.",
        )

    if body.moodle_question_ids is not None and len(body.moodle_question_ids) != len(
        questions
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"moodle_question_ids hat {len(body.moodle_question_ids)} "
                f"Einträge, Prüfung hat aber {len(questions)} Fragen."
            ),
        )

    # Verify the Moodle quiz exists (best-effort; allows the operator
    # to skip the check by not having a connection — useful in tests
    # and on-prem deploys without Web Services).
    connection = (
        db.query(MoodleConnection)
        .filter(MoodleConnection.institution_id == current_user.institution_id)
        .one_or_none()
    )
    quiz_meta: dict[str, Any] | None = None
    if connection is not None:
        try:
            token = decrypt_secret(connection.token_encrypted)
        except SecretEncryptionError as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Token-Verschlüsselung defekt: {exc}",
            ) from exc
        quiz_meta = await _verify_moodle_quiz(
            base_url=connection.base_url,
            token=token,
            quiz_id=body.moodle_quiz_id,
        )

    out_questions: list[SyncedQuestionOut] = []
    for slot_idx, eq in enumerate(questions, start=1):
        moodle_qid = (
            body.moodle_question_ids[slot_idx - 1]
            if body.moodle_question_ids is not None
            else None
        )
        existing = dict(eq.external_refs or {})
        existing["moodle_slot"] = slot_idx
        existing["moodle_quiz_id"] = body.moodle_quiz_id
        if moodle_qid is not None:
            existing["moodle_question_id"] = int(moodle_qid)
        eq.external_refs = existing
        out_questions.append(
            SyncedQuestionOut(
                exam_question_id=eq.id,
                position=eq.position,
                moodle_slot=slot_idx,
                moodle_question_id=existing.get("moodle_question_id"),
                moodle_quiz_id=body.moodle_quiz_id,
            )
        )

    db.commit()

    return SyncMoodleQuestionIdsOut(
        exam_id=exam.id,
        moodle_quiz_id=body.moodle_quiz_id,
        moodle_quiz_name=(
            str(quiz_meta.get("name")) if quiz_meta and quiz_meta.get("name") else None
        ),
        questions=out_questions,
    )
