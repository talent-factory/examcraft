"""Import endpoints answer with distinguishable error codes (TF-773 PR 2c).

Two claims are held here, and they are different claims:

1. **Every hard failure of the import pipeline carries its own code.** The
   import path is the one place where the service text *was* the message —
   «Die Datei ist leer.» is what the teacher needed to read, and a single
   ``submissions_import_failed`` would have replaced it with «Import
   fehlgeschlagen». So this file asserts one code per failure kind, not one
   code per endpoint.
2. **Nothing internal reaches the response.** Raw exception text, developer
   sentences («MoodleApiDriver braucht eine DB-Session …») and internal ids
   (``exam_question_id 42``) belong in the log. ``_assert_clean`` checks the
   whole serialised body, not just ``detail`` — an id smuggled into
   ``error_params`` would be just as visible to a client.

The pairing matters: a test that only checks the code would stay green if the
raw text were still echoed next to it, and a test that only checks the absence
of raw text would stay green if every failure collapsed onto one code.
"""

from __future__ import annotations

import json
import logging
import pathlib
from datetime import date
from io import BytesIO
from unittest.mock import patch

import httpx
import pytest
import respx
from sqlalchemy.orm import Session

from models.exam import Exam
from services.import_drivers import ImportDriverError, MoodleApiDriver
from tests.test_moodle_api_driver import (  # noqa: F401 -- _crypto_env is autouse
    _crypto_env,
    _make_institution as _api_institution,
    _setup_connection,
    _setup_exam_with_two_questions,
)
from tests.test_submissions_api import (
    _JSON_FIXTURE,
    _client,
    _make_exam,
    _make_institution,
    _make_user,
)


# Fragments that must never appear in a response body: developer wording,
# exception class names, and the internal identifiers of the old messages.
_INTERNAL_FRAGMENTS = (
    "Traceback",
    "ImportDriverError",
    "ImportValidationError",
    "MoodleApiDriver",
    "exam_question_id",
    "institution_id",
    "moodle_connections",
    "Payload-exam_id",
    "wsfunction",
)


def _assert_clean(body: dict) -> None:
    """No internal wording anywhere in the serialised response."""
    serialised = json.dumps(body, ensure_ascii=False)
    leaked = [f for f in _INTERNAL_FRAGMENTS if f in serialised]
    assert not leaked, f"Interna in der Antwort: {leaked} — {serialised}"


def _preview(client, exam_id: int, payload: bytes, *, filename: str = "quelle.json"):
    return client.post(
        "/api/v1/submissions/import/preview",
        files={"file": (filename, BytesIO(payload), "application/json")},
        data={"exam_id": str(exam_id), "driver_name": "moodle_json"},
    )


@pytest.fixture
def import_client(test_db: Session):
    """Client + exam id for a user allowed to import."""
    inst = _make_institution(test_db, slug="import-codes")
    user = _make_user(test_db, inst.id, email="import-codes@test.ch")
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    return _client(test_db, user), exam.id


# ---------------------------------------------------------------------------
# Moodle web-service driver
#
# These run against the driver instead of an endpoint: the web-service call
# sequence needs respx, and the endpoint's own mapping (code -> response) is
# already covered above. What matters here is that each transport failure
# keeps its own code and that the raw httpx/Moodle wording never leaves the
# exception.
# ---------------------------------------------------------------------------

_MOODLE_ENDPOINT = "https://moodle.example.org/webservice/rest/server.php"


def _api_exam(test_db: Session):
    inst = _api_institution(test_db, slug=f"codes-{_next_slug()}")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()
    return exam


_slug_counter = iter(range(1000))


def _next_slug() -> int:
    return next(_slug_counter)


def _parse_quiz(exam, db, quiz_id: int = 42):
    return MoodleApiDriver().parse(
        json.dumps({"quiz_id": quiz_id}).encode("utf-8"), exam=exam, db=db
    )


@pytest.mark.parametrize(
    "response_or_error, expected_code",
    [
        (httpx.ConnectError("no route"), "submissions_import_moodle_unreachable"),
        (httpx.ReadTimeout("read timeout"), "submissions_import_moodle_unreachable"),
        (httpx.Response(503), "submissions_import_moodle_server_error"),
        (httpx.Response(429), "submissions_import_moodle_rate_limited"),
        (
            httpx.Response(401, text="<html>nope</html>"),
            "submissions_import_moodle_auth_failed",
        ),
        (
            httpx.Response(200, text="<html>not json</html>"),
            "submissions_import_moodle_unexpected_response",
        ),
    ],
)
def test_moodle_transportfehler_behalten_je_eigenen_code(
    test_db: Session, response_or_error, expected_code
) -> None:
    exam = _api_exam(test_db)

    with respx.mock() as mock:
        route = mock.post(_MOODLE_ENDPOINT)
        if isinstance(response_or_error, httpx.Response):
            route.mock(return_value=response_or_error)
        else:
            route.mock(side_effect=response_or_error)
        with pytest.raises(ImportDriverError) as excinfo:
            _parse_quiz(exam, test_db)

    assert excinfo.value.code == expected_code


def test_moodle_serverfehler_traegt_den_status_als_parameter(test_db: Session) -> None:
    """The status is the one number a teacher can repeat to support, so it is
    a parameter of the sentence rather than a detail of the log line."""
    exam = _api_exam(test_db)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(return_value=httpx.Response(502))
        with pytest.raises(ImportDriverError) as excinfo:
            _parse_quiz(exam, test_db)

    assert excinfo.value.params == {"status": 502}


def test_unbekanntes_quiz_nennt_die_quiz_id(test_db: Session) -> None:
    exam = _api_exam(test_db)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(
            return_value=httpx.Response(200, json={"quizzes": [{"id": 7, "name": "x"}]})
        )
        with pytest.raises(ImportDriverError) as excinfo:
            _parse_quiz(exam, test_db, quiz_id=4242)

    assert excinfo.value.code == "submissions_import_quiz_not_found"
    assert excinfo.value.params == {"quiz_id": 4242}


def test_fehlende_moodle_verbindung_hat_eigenen_code(test_db: Session) -> None:
    inst = _api_institution(test_db, slug=f"codes-noconn-{_next_slug()}")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    test_db.commit()

    with pytest.raises(ImportDriverError) as excinfo:
        _parse_quiz(exam, test_db)

    assert excinfo.value.code == "submissions_import_moodle_connection_missing"


def test_entwicklerfehler_bekommen_den_internen_code() -> None:
    """«MoodleApiDriver braucht eine DB-Session …» named a class and an
    internal table. It is a programming error, so the teacher gets the
    internal-error sentence and the original text goes to the log."""

    class FakeExam:
        id = 1
        institution_id = 1
        questions: list = []

    with pytest.raises(ImportDriverError) as excinfo:
        MoodleApiDriver().parse(b'{"quiz_id": 1}', exam=FakeExam(), db=None)

    assert excinfo.value.code == "submissions_import_internal_error"
    assert "DB-Session" in excinfo.value.log_message


@pytest.mark.parametrize("source", [b"", b"{}", b"nicht-json"])
def test_kaputte_source_ist_ein_interner_fehler(source) -> None:
    """The endpoint builds this source itself from a validated ``quiz_id``;
    anything wrong with it is our bug, not the teacher's."""

    class FakeExam:
        id = 1
        institution_id = 1
        questions: list = []

    with pytest.raises(ImportDriverError) as excinfo:
        MoodleApiDriver().parse(source, exam=FakeExam(), db=object())

    assert excinfo.value.code == "submissions_import_internal_error"


@pytest.mark.parametrize("quiz_id", ["abc", 0, -3])
def test_unbrauchbare_quiz_id_hat_eigenen_code(quiz_id) -> None:
    class FakeExam:
        id = 1
        institution_id = 1
        questions: list = []

    with pytest.raises(ImportDriverError) as excinfo:
        MoodleApiDriver().parse(
            json.dumps({"quiz_id": quiz_id}).encode("utf-8"),
            exam=FakeExam(),
            db=object(),
        )

    assert excinfo.value.code == "submissions_import_quiz_id_invalid"


def test_moodle_ausnahme_echot_die_fremde_meldung_nicht(test_db: Session) -> None:
    """Moodle answers 200 with an ``exception`` envelope whose ``message`` is
    written by Moodle, in Moodle's language. Echoing it put a foreign, often
    English sentence into a German UI."""
    exam = _api_exam(test_db)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "exception": "moodle_exception",
                    "errorcode": "nopermissions",
                    "message": "Sorry, but you do not currently have permissions",
                },
            )
        )
        with pytest.raises(ImportDriverError) as excinfo:
            _parse_quiz(exam, test_db)

    assert excinfo.value.code == "submissions_import_moodle_unexpected_response"
    assert excinfo.value.params == {}
    assert "nopermissions" in excinfo.value.log_message


@pytest.mark.parametrize(
    "errorcode", ["invalidtoken", "accessexception", "webservice_access_exception"]
)
def test_moodle_200_envelope_auth_fehlercodes_sind_eigener_code(
    test_db: Session, errorcode
) -> None:
    """Moodle answers HTTP 200 for an auth rejection too, encoding it as an
    ``exception``/``errorcode`` envelope instead of a 401/403 status (unlike
    ``test_moodle_transportfehler_behalten_je_eigenen_code``, which only
    drives the HTTP-status path). All three ``errorcode`` values in
    ``_call``'s allowlist must keep mapping to the actionable
    ``submissions_import_moodle_auth_failed`` — removing one from that
    allowlist would silently misfile it as the generic
    ``submissions_import_moodle_unexpected_response`` instead (TF-773 PR 2c
    review)."""
    exam = _api_exam(test_db)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(
            return_value=httpx.Response(
                200,
                json={
                    "exception": "webservice_access_exception",
                    "errorcode": errorcode,
                    "message": "Access control exception",
                },
            )
        )
        with pytest.raises(ImportDriverError) as excinfo:
            _parse_quiz(exam, test_db)

    assert excinfo.value.code == "submissions_import_moodle_auth_failed"


def test_defekte_token_verschluesselung_hat_eigenen_code(test_db: Session) -> None:
    inst = _api_institution(test_db, slug=f"codes-token-{_next_slug()}")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    connection = _setup_connection(test_db, inst.id)
    connection.token_encrypted = "nicht-entschluesselbar"
    test_db.commit()

    with pytest.raises(ImportDriverError) as excinfo:
        _parse_quiz(exam, test_db)

    assert excinfo.value.code == "submissions_import_moodle_connection_invalid"
    assert excinfo.value.params == {}


# ---------------------------------------------------------------------------
# The API endpoints, not just the driver
#
# The driver tests above prove the codes; these prove the wiring — that all
# four endpoints hand a coded exception to `_import_error` and that the
# response really carries the envelope. `api-commit` and `commit` matter
# separately from their preview twins: they run the same parse a second time
# and used to have their own copy of the `detail=str(exc)` handler.
# ---------------------------------------------------------------------------


def test_api_preview_uebersetzt_unbekanntes_quiz(test_db: Session) -> None:
    inst = _api_institution(test_db, slug=f"codes-ep-{_next_slug()}")
    user = _make_user(test_db, inst.id, email="api-preview@test.ch")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(
            return_value=httpx.Response(200, json={"quizzes": [{"id": 7, "name": "x"}]})
        )
        response = client.post(
            "/api/v1/submissions/import/api-preview",
            json={"exam_id": exam.id, "quiz_id": 4242},
        )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_quiz_not_found"
    assert body["error_params"] == {"quiz_id": 4242}
    assert "4242" in body["detail"]
    _assert_clean(body)


def test_api_commit_uebersetzt_fehlende_verbindung(test_db: Session) -> None:
    inst = _api_institution(test_db, slug=f"codes-ac-{_next_slug()}")
    user = _make_user(test_db, inst.id, email="api-commit@test.ch")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    response = client.post(
        "/api/v1/submissions/import/api-commit",
        json={"exam_id": exam.id, "quiz_id": 42},
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_moodle_connection_missing"
    _assert_clean(body)


def test_commit_uebersetzt_die_leere_datei(import_client) -> None:
    client, exam_id = import_client

    response = client.post(
        "/api/v1/submissions/import/commit",
        files={"file": ("leer.json", BytesIO(b""), "application/json")},
        data={"exam_id": str(exam_id), "driver_name": "moodle_json"},
    )

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_file_empty"
    _assert_clean(body)


def test_antwort_folgt_der_nutzersprache(test_db: Session) -> None:
    """``detail`` is the sentence for the code in the caller's language.

    Without this the code would be the only thing that travelled and
    ``detail`` would silently stay German for every client — the failure mode
    ADR 0005 exists to prevent.
    """
    inst = _make_institution(test_db, slug="import-locale")
    user = _make_user(test_db, inst.id, email="import-locale@test.ch")
    user.preferred_language = "fr"
    exam = _make_exam(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    response = _preview(client, exam.id, b"")

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_file_empty"
    assert body["detail"] == "Le fichier est vide."


def test_broker_ausfall_liefert_einen_code_statt_eines_dict_details(
    import_client, caplog
) -> None:
    """The 503 from a broker outage was the last hand-written German sentence
    on this router, and it arrived as a ``detail`` dict — which ADR 0005 says
    ``detail`` never is. The dialog therefore showed its generic «Import
    fehlgeschlagen.» fallback for an outage it could have named.

    The job id it used to carry is a support detail, not something a teacher
    can act on, so it moves to the log.
    """
    from unittest.mock import patch

    client, exam_id = import_client

    with patch(
        "api.submissions.import_submissions.delay",
        side_effect=RuntimeError("broker unreachable"),
    ):
        with caplog.at_level(logging.WARNING):
            response = client.post(
                "/api/v1/submissions/import/commit",
                files={
                    "file": (
                        "klasse.json",
                        BytesIO(_JSON_FIXTURE.encode("utf-8")),
                        "application/json",
                    )
                },
                data={"exam_id": str(exam_id), "driver_name": "moodle_json"},
            )

    assert response.status_code == 503, response.text
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["error_code"] == "submissions_import_enqueue_failed"
    assert "import_job_id" not in json.dumps(body)
    _assert_clean(body)
    assert any("job_id" in r.getMessage() for r in caplog.records), (
        "Die Job-ID gehört ins Log, damit der Support sie noch findet"
    )


# ---------------------------------------------------------------------------
# The two shapes that were not `str(exc)` and therefore not in the ticket's
# list, but sit on the same four endpoints and answered the same way: hand-
# written German, no code, so the dialog fell back to «Vorschau
# fehlgeschlagen.» for a cause it could have named.
# ---------------------------------------------------------------------------


def test_api_vorschau_absturz_nennt_keine_server_logs(test_db: Session) -> None:
    from unittest.mock import patch

    from services.import_service import ImportService

    inst = _api_institution(test_db, slug=f"codes-500-{_next_slug()}")
    user = _make_user(test_db, inst.id, email="api-500@test.ch")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    _setup_connection(test_db, inst.id)
    test_db.commit()
    client = _client(test_db, user)

    def boom(*args, **kwargs):
        raise RuntimeError("synthetischer Absturz")

    with patch.object(ImportService, "preview", boom):
        response = client.post(
            "/api/v1/submissions/import/api-preview",
            json={"exam_id": exam.id, "quiz_id": 42},
        )

    assert response.status_code == 500, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_internal_error"
    assert "Server-Logs" not in body["detail"]
    _assert_clean(body)


# ---------------------------------------------------------------------------
# Abnahme TF-773 PR 2c: je Code ein Nachweis
#
# «Je Code ein Test, der belegt: rohe Exception-Texte und interne IDs im Log,
# nicht in der Antwort.» Every code goes through a real endpoint with a real
# input — no patched exception — so the matrix also proves each throw site is
# reachable. Each case names a fragment of the old service sentence (``raw``):
# it must show up in the log and must not show up in the body. Codes that no
# endpoint can produce are pinned separately below, and
# ``test_jeder_import_code_hat_einen_nachweis`` fails the moment a new code
# appears without an entry here.
# ---------------------------------------------------------------------------

_NO_QUESTION_MATCH = json.dumps(
    [
        {
            "e-mail-adresse": "anna@example.org",
            "frage1": "Welches Element hat die Ordnungszahl 79?",
            "antwort1": "Gold",
        }
    ]
).encode("utf-8")

_NO_FRAGE_KEYS = json.dumps(
    [{"e-mail-adresse": "anna@example.org", "antwort1": "Bern"}]
).encode("utf-8")

# code -> (payload, status, raw fragment of the log message, expected params)
_DATEI_FAELLE = {
    # Nothing internal in this one — its service sentence *is* the teacher's
    # sentence. The log line itself is the proof that the path logs.
    "submissions_import_file_empty": (
        b"",
        400,
        "Import abgebrochen (submissions_import_file_empty",
        None,
    ),
    "submissions_import_file_not_json": (
        b'[{"e-mail-adresse": ',
        400,
        "Quelle ist kein gültiges JSON",
        None,
    ),
    "submissions_import_file_not_utf8": (
        '[{"e-mail-adresse": "j\u00fcrg@example.org"}]'.encode("latin-1"),
        400,
        "JSON-Datei ist nicht UTF-8-kodiert",
        None,
    ),
    "submissions_import_json_structure_invalid": (
        b'{"studierende": []}',
        400,
        "war dict",
        None,
    ),
    "submissions_import_no_attempts": (
        b"[]",
        400,
        "JSON enthält keine Datenzeilen",
        None,
    ),
    "submissions_import_question_texts_missing": (
        _NO_FRAGE_KEYS,
        400,
        "Schlüssel 'frageN'",
        None,
    ),
    "submissions_import_question_mapping_failed": (
        _NO_QUESTION_MATCH,
        400,
        "Zuordnung der JSON-Fragen",
        None,
    ),
}


def _assert_log_not_body(caplog, body: dict, code: str, raw: str) -> None:
    """The raw service text is in the log, and nowhere in the response."""
    assert raw in caplog.text, f"{code}: «{raw}» fehlt im Log"
    assert raw not in json.dumps(body, ensure_ascii=False), (
        f"{code}: «{raw}» steht in der Antwort"
    )
    _assert_clean(body)


@pytest.mark.parametrize("code", sorted(_DATEI_FAELLE))
def test_datei_codes_loggen_interna_statt_sie_zu_antworten(
    import_client, caplog, code
) -> None:
    payload, status, raw, params = _DATEI_FAELLE[code]
    client, exam_id = import_client

    with caplog.at_level(logging.WARNING):
        response = _preview(client, exam_id, payload)

    assert response.status_code == status, response.text
    body = response.json()
    assert body["error_code"] == code
    assert body.get("error_params") == params
    _assert_log_not_body(caplog, body, code, raw)


def test_pruefung_ohne_fragen_loggt_interna(test_db: Session, caplog) -> None:
    inst = _make_institution(test_db, slug="import-codes-leer")
    user = _make_user(test_db, inst.id, email="import-leer@test.ch")
    exam = Exam(
        title="Ohne Fragen",
        course="Test",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=0.0,
        status="finalized",
        language="de",
        institution_id=inst.id,
    )
    test_db.add(exam)
    test_db.commit()
    client = _client(test_db, user)

    with caplog.at_level(logging.WARNING):
        response = _preview(client, exam.id, _JSON_FIXTURE.encode("utf-8"))

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_exam_without_questions"
    _assert_log_not_body(
        caplog, body, body["error_code"], "denen Antworten zugeordnet werden könnten"
    )


def test_fremde_fragen_loggen_die_ids_und_antworten_mit_der_anzahl(
    import_client, caplog
) -> None:
    """The old 422 listed «AttemptAnswer referenziert exam_question_id 42 —
    nicht in Prüfung 7» once per offending row. The JSON driver only emits ids
    it matched, so the foreign ids are injected at the driver boundary; the
    throw site under test is ``_validate_payload``, unpatched."""
    from services.import_drivers.payloads import (
        AnswerRecord,
        AttemptRecord,
        ImportPayload,
        StudentRef,
    )
    from services.import_service import ImportService

    client, exam_id = import_client

    def _foreign(self, source, *, exam, db=None):
        payload = ImportPayload(exam_id=exam.id, driver_name="moodle_json")
        payload.students.append(StudentRef(external_id="anna@example.org"))
        payload.attempts.append(
            AttemptRecord(
                student_external_id="anna@example.org",
                attempt_number=1,
                source_attempt_id="a-1",
                answers=[
                    AnswerRecord(exam_question_id=9042, given_answer="Bern"),
                    AnswerRecord(exam_question_id=9043, given_answer="Chur"),
                ],
            )
        )
        return payload

    with patch.object(type(ImportService.DRIVERS["moodle_json"]), "parse", _foreign):
        with caplog.at_level(logging.WARNING):
            response = _preview(client, exam_id, b"[]")

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_exam_mismatch"
    assert body["error_params"] == {"count": 2}
    assert "issues" not in json.dumps(body)
    _assert_log_not_body(caplog, body, body["error_code"], "9042")


def test_zu_grosse_datei_loggt_die_bytezahl(import_client, caplog) -> None:
    from api.submissions import MAX_UPLOAD_BYTES

    client, exam_id = import_client

    with caplog.at_level(logging.WARNING):
        response = _preview(client, exam_id, b"x" * (MAX_UPLOAD_BYTES + 1))

    assert response.status_code == 413, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_file_too_large"
    # The limit is what the teacher acts on; the byte count is a log detail.
    assert body["error_params"] == {"max_mb": MAX_UPLOAD_BYTES // (1024 * 1024)}
    _assert_log_not_body(caplog, body, body["error_code"], str(MAX_UPLOAD_BYTES + 1))


def test_absturz_loggt_die_ursache_statt_server_logs_zu_nennen(
    import_client, caplog
) -> None:
    """«— siehe Server-Logs» was an instruction to an operator, printed on a
    teacher's screen. The cause goes to the log with its traceback."""
    from services.import_service import ImportService

    client, exam_id = import_client

    def boom(*args, **kwargs):
        raise RuntimeError("synthetischer Absturz")

    with patch.object(ImportService, "preview", boom):
        with caplog.at_level(logging.ERROR):
            response = _preview(client, exam_id, b"[]")

    assert response.status_code == 500, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_internal_error"
    assert "Server-Logs" not in body["detail"]
    _assert_log_not_body(caplog, body, body["error_code"], "synthetischer Absturz")


# ---- Moodle web service, through /import/api-preview ----------------------


def _by_function(**answers):
    """respx side effect answering per Moodle ``wsfunction``."""

    def _answer(request):
        body = request.read().decode("utf-8")
        for function, response in answers.items():
            if function in body:
                return response
        raise AssertionError(f"unerwarteter Moodle-Aufruf: {body[:120]}")

    return _answer


_QUIZ_42 = httpx.Response(200, json={"quizzes": [{"id": 42, "name": "Geo"}]})

# code -> (respx side effect or response, raw fragment, expected params)
_MOODLE_FAELLE = {
    "submissions_import_moodle_unreachable": (
        httpx.ConnectError("no route to moodle-host"),
        "no route to moodle-host",
        None,
    ),
    "submissions_import_moodle_server_error": (
        httpx.Response(502),
        "mod_quiz_get_quizzes_by_courses",
        {"status": 502},
    ),
    "submissions_import_moodle_rate_limited": (
        httpx.Response(429),
        "mod_quiz_get_quizzes_by_courses",
        None,
    ),
    "submissions_import_moodle_auth_failed": (
        httpx.Response(401, text="<html>nope</html>"),
        "mod_quiz_get_quizzes_by_courses",
        None,
    ),
    "submissions_import_moodle_unexpected_response": (
        httpx.Response(200, text="<html>kein json</html>"),
        "antwortete nicht mit JSON",
        None,
    ),
    "submissions_import_quiz_not_found": (
        httpx.Response(200, json={"quizzes": [{"id": 7, "name": "x"}]}),
        "Token-Sicht",
        {"quiz_id": 42},
    ),
    "submissions_import_attempt_without_user": (
        _by_function(
            mod_quiz_get_quizzes_by_courses=_QUIZ_42,
            mod_quiz_get_user_attempts=httpx.Response(
                200, json={"attempts": [{"id": 501, "state": "finished"}]}
            ),
        ),
        "ohne identifizierbaren",
        None,
    ),
}


def _moodle_client(test_db: Session, *, connection: bool = True):
    inst = _api_institution(test_db, slug=f"codes-matrix-{_next_slug()}")
    user = _make_user(test_db, inst.id, email=f"matrix-{inst.id}@test.ch")
    exam, _eq1, _eq2 = _setup_exam_with_two_questions(test_db, inst.id)
    connection_row = _setup_connection(test_db, inst.id) if connection else None
    test_db.commit()
    return _client(test_db, user), exam.id, connection_row


def _api_preview(client, exam_id: int, quiz_id: int = 42):
    return client.post(
        "/api/v1/submissions/import/api-preview",
        json={"exam_id": exam_id, "quiz_id": quiz_id},
    )


@pytest.mark.parametrize("code", sorted(_MOODLE_FAELLE))
def test_moodle_codes_loggen_interna_statt_sie_zu_antworten(
    test_db: Session, caplog, code
) -> None:
    answer, raw, params = _MOODLE_FAELLE[code]
    client, exam_id, _ = _moodle_client(test_db)

    with respx.mock() as mock:
        route = mock.post(_MOODLE_ENDPOINT)
        if isinstance(answer, httpx.Response):
            route.mock(return_value=answer)
        else:
            route.mock(side_effect=answer)
        with caplog.at_level(logging.WARNING):
            response = _api_preview(client, exam_id)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == code
    assert body.get("error_params") == params
    _assert_log_not_body(caplog, body, code, raw)


def test_fehlende_verbindung_loggt_interna(test_db: Session, caplog) -> None:
    client, exam_id, _ = _moodle_client(test_db, connection=False)

    with caplog.at_level(logging.WARNING):
        response = _api_preview(client, exam_id)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_moodle_connection_missing"
    _assert_log_not_body(caplog, body, body["error_code"], "Admin muss zuerst")


def test_unlesbarer_token_loggt_interna(test_db: Session, caplog) -> None:
    client, exam_id, connection = _moodle_client(test_db)
    connection.token_encrypted = "nicht-entschluesselbar"
    test_db.commit()

    with caplog.at_level(logging.WARNING):
        response = _api_preview(client, exam_id)

    assert response.status_code == 400, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_moodle_connection_invalid"
    _assert_log_not_body(
        caplog, body, body["error_code"], "konnte nicht entschlüsselt werden"
    )


def test_quiz_ohne_versuche_ist_derselbe_satz_als_422(test_db: Session, caplog) -> None:
    """``no_attempts`` is the one code raised under two statuses: 400 from the
    JSON driver for an empty export, 422 from the payload validation for a
    Moodle quiz nobody finished. Same fact for the teacher, same sentence."""
    client, exam_id, _ = _moodle_client(test_db)

    with respx.mock() as mock:
        mock.post(_MOODLE_ENDPOINT).mock(
            side_effect=_by_function(
                mod_quiz_get_quizzes_by_courses=_QUIZ_42,
                mod_quiz_get_user_attempts=httpx.Response(200, json={"attempts": []}),
            )
        )
        with caplog.at_level(logging.WARNING):
            response = _api_preview(client, exam_id)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error_code"] == "submissions_import_no_attempts"
    _assert_log_not_body(
        caplog, body, body["error_code"], "Quelldatei enthält keine Versuche"
    )


# ---- A code no endpoint can produce ----------------------------------------
#
# Raised by the service for a caller that bypasses the HTTP layer, but a
# guard in front of the service answers first. That is why it is *not* in
# ``core/frontend/src/errors/codes/submissions.ts``: the registry accepts
# only codes some endpoint can produce. This test pins the guard — if it
# goes away, the code becomes reachable and must be registered.

HTTP_UNERREICHBAR = {
    "submissions_import_quiz_id_invalid": "Pydantic antwortet vorher mit 422",
}


def test_unbekannter_driver_scheitert_an_der_tier_sperre(import_client) -> None:
    """An arbitrary, unregistered driver name never reaches
    ``ImportService._get_driver`` — the tier gate answers first with 402,
    so ``submissions_import_driver_unknown`` stays unreachable *for this
    input*. ``moodle_api`` specifically has its own, endpoint-level guard
    with its own reachability proof — see
    ``test_moodle_api_ueber_upload_endpunkt_hat_eigenen_code`` below."""
    from services.import_service import ImportService, UnknownDriverError

    client, exam_id = import_client
    response = client.post(
        "/api/v1/submissions/import/preview",
        files={"file": ("q.json", BytesIO(b"[]"), "application/json")},
        data={"exam_id": str(exam_id), "driver_name": "gibt_es_nicht"},
    )
    assert response.status_code == 402, response.text
    assert "submissions_import_driver_unknown" not in response.text

    # Below the guard, the service still answers with its own code.
    with pytest.raises(UnknownDriverError) as excinfo:
        ImportService._get_driver("gibt_es_nicht")
    assert excinfo.value.code == "submissions_import_driver_unknown"


@pytest.mark.parametrize(
    "endpoint",
    ["/api/v1/submissions/import/preview", "/api/v1/submissions/import/commit"],
)
def test_moodle_api_ueber_upload_endpunkt_hat_eigenen_code(
    import_client, endpoint
) -> None:
    """``moodle_api`` has no file to parse — it belongs on
    ``/import/api-preview``/``/import/api-commit`` (JSON body, Pydantic-
    validated ``quiz_id``). Without ``_reject_driver_without_upload_body``,
    posting ``driver_name=moodle_api`` to the multipart endpoints here could
    reach ``MoodleApiDriver.parse()`` with a hand-crafted, unvalidated
    ``quiz_id`` (``submissions_import_quiz_id_invalid`` — a code the
    frontend registry deliberately does not carry because it is documented
    as unreachable via HTTP). The guard answers first, with its own,
    registered code (TF-773 PR 2c review)."""
    client, exam_id = import_client
    response = client.post(
        endpoint,
        files={
            "file": (
                "q.json",
                BytesIO(b'{"quiz_id": "not-an-int"}'),
                "application/json",
            )
        },
        data={"exam_id": str(exam_id), "driver_name": "moodle_api"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "submissions_import_driver_unknown"


@pytest.mark.parametrize("quiz_id", [0, -3])
def test_ungueltige_quiz_id_scheitert_an_pydantic(test_db: Session, quiz_id) -> None:
    client, exam_id, _ = _moodle_client(test_db)
    response = _api_preview(client, exam_id, quiz_id=quiz_id)
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"
    # The driver-level code for the same input is pinned in
    # test_unbrauchbare_quiz_id_hat_eigenen_code above.


# Codes whose proof lives in a dedicated test rather than in the matrix.
_EIGENE_TESTS = {
    "submissions_import_driver_unknown": (
        "test_moodle_api_ueber_upload_endpunkt_hat_eigenen_code"
    ),
    "submissions_import_enqueue_failed": (
        "test_broker_ausfall_liefert_einen_code_statt_eines_dict_details"
    ),
    "submissions_import_exam_mismatch": (
        "test_fremde_fragen_loggen_die_ids_und_antworten_mit_der_anzahl"
    ),
    "submissions_import_exam_without_questions": (
        "test_pruefung_ohne_fragen_loggt_interna"
    ),
    "submissions_import_file_too_large": "test_zu_grosse_datei_loggt_die_bytezahl",
    "submissions_import_internal_error": (
        "test_absturz_loggt_die_ursache_statt_server_logs_zu_nennen"
    ),
    "submissions_import_moodle_connection_invalid": (
        "test_unlesbarer_token_loggt_interna"
    ),
    "submissions_import_moodle_connection_missing": (
        "test_fehlende_verbindung_loggt_interna"
    ),
}


def test_jeder_import_code_hat_einen_nachweis() -> None:
    """Turns the acceptance criterion into an invariant: a new
    ``submissions_import_*`` key without a case here fails the build."""
    doc = json.loads(
        (
            pathlib.Path(__file__).resolve().parents[1] / "locales" / "t.de.json"
        ).read_text(encoding="utf-8")
    )["de"]
    alle = {k for k in doc if k.startswith("submissions_import_")}

    belegt = (
        set(_DATEI_FAELLE)
        | set(_MOODLE_FAELLE)
        | set(_EIGENE_TESTS)
        | set(HTTP_UNERREICHBAR)
    )
    assert alle - belegt == set(), f"Code(s) ohne Nachweis: {sorted(alle - belegt)}"
    assert belegt - alle == set(), f"Nachweis ohne Code: {sorted(belegt - alle)}"
    fehlende_tests = [t for t in _EIGENE_TESTS.values() if t not in globals()]
    assert not fehlende_tests, f"verwiesene Tests existieren nicht: {fehlende_tests}"
