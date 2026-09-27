"""Ein Test je Fehlercode der elf Router aus TF-773 PR 2d, dazu ``submissions.py``
und ``tags.py`` (Review-Nachtrag zu Teil D, PR #319).

Der Contract-Test (``test_error_codes_contract.py``) prüft statisch, dass jeder
Code einen Locale-Schlüssel hat. Das sagt nichts darüber, ob der Code je
*geworfen* wird — ein Tippfehler im Code-Namen einer Wurfstelle, die kein Test
anfasst, wäre dort grün und im Betrieb ein generischer Satz.

Diese Datei schliesst die Lücke von der anderen Seite: sie ruft jede Wurfstelle
und liest den Code aus der Antwort. ``test_jede_wurfstelle_ist_hier_abgedeckt``
unten hält die beiden Seiten zusammen — ein neuer Code in einem dieser Router
macht diese Datei rot, bis jemand ihn hier belegt.

Abgrenzung: wo ein Code auch die *Meldung* trägt, wird zusätzlich geprüft, dass
``detail`` ein String ist und nicht mehr die rohe Exception zitiert. Wo der Code
ein Passthrough ist (englischer Text, kein Locale-Schlüssel — TF-295), wird der
Text wörtlich geprüft, weil er genau dort der Vertrag ist.

Bekannte Lücke: ``moodle_feedback_push.py``/``moodle_roundtrip.py`` prüfen ein
"Exam existiert" (jetzt mit Code, siehe ``exams_not_found`` unten) UND separat
ein "Exam existiert, ist aber für diesen Nutzer nicht sichtbar" via
``utils.exam_visibility.assert_exam_visible_for`` — letzteres wirft weiterhin
ein rohes ``HTTPException`` ohne ``error_code``. Dieser gemeinsame Util-Helfer
ist keiner der elf PR-2d-Router und bleibt deshalb bewusst ausserhalb dieses
PRs; ein 404 aus diesen beiden Endpunkten trägt also je nach Zweig
unterschiedlich viel Struktur. ``grade_export.py`` ruft
``assert_exam_visible_for`` nicht — dort deckt der eine, jetzt codierte
``exams_not_found``-Check die gesamte Multi-Tenancy-Prüfung ab.
"""

from __future__ import annotations

import ast
import json
import pathlib
from datetime import date
from types import SimpleNamespace

import httpx
import pytest
import respx
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import get_db
from main import app
from models.auth import Institution, User, UserStatus
from models.exam import Exam, ExamQuestion, ExamVisibility
from models.question_review import QuestionReview
from models.student import Student
from models.submission import MoodleConnection, Submission
from utils.auth_utils import get_current_active_user, get_current_user
from utils.secret_encryption import encrypt_secret, reset_cache_for_tests

pytestmark = pytest.mark.usefixtures("test_engine")


# ---------------------------------------------------------------------------
# Die Router und was sie werfen dürfen
#
# Die elf aus PR 2d plus ``submissions.py`` (Teil D von TF-773, letzter Router
# mit nackten ``HTTPException``) und ``tags.py`` (Review-Nachtrag PR #319: war
# schon vor Teil D auf Codes umgestellt, stand aber nie in dieser Liste).
# ---------------------------------------------------------------------------

#: ``ROUTERS`` selbst bleibt relativ (kürzer, matcht main.py-Importpfade) —
#: aber jede Datei-Öffnung geht über diese Konstante, nicht über das CWD.
#: Ohne sie ist der Scan nur grün, wenn pytest aus core/backend/ gestartet
#: wird; `just test-file`/`just test-one` (CLAUDE.md) laufen aus dem
#: Repo-Root und würden sonst mit FileNotFoundError rot.
BACKEND_ROOT = pathlib.Path(__file__).resolve().parents[1]

ROUTERS = (
    "api/activity.py",
    "api/audit.py",
    "api/grade_export.py",
    "api/moodle_connections.py",
    "api/moodle_feedback_push.py",
    "api/moodle_roundtrip.py",
    "api/rag_exams.py",
    "api/specula_test.py",
    "api/stats.py",
    "api/students.py",
    "api/submissions.py",
    "api/tags.py",
    "api/v1/webhooks.py",
)

#: Codes, die schon vor PR 2d in einem dieser Router standen und anderswo
#: geprüft werden. Sie stehen hier, damit der Wächter unten ein *exakter*
#: Mengenvergleich bleibt: ohne sie müsste er "mindestens" prüfen und würde
#: einen neuen, ungetesteten Code genau dann übersehen, wenn es darauf ankommt.
PRE_EXISTING: dict[str, str] = {
    "rag_context_retrieval_failed": "tests/test_rag_api.py",
    "rag_document_not_found": "tests/test_rag_api.py",
    "rag_document_not_processed": "tests/test_rag_api.py",
    "rag_generation_failed": "tests/test_rag_api.py",
    "rag_get_documents_failed": "tests/test_rag_api.py",
    "rag_invalid_question_type": "tests/test_rag_api.py",
    "rag_no_institution": "tests/test_rag_api.py",
    "rag_retry_no_request_data": "tests/test_rag_retry.py",
    "rag_retry_only_failed": "tests/test_rag_retry.py",
    "rag_retry_owner_unavailable": "tests/test_rag_retry.py",
    "rag_task_not_found": "tests/test_rag_api.py",
    "rag_task_queue_unavailable": "tests/test_rag_api.py",
    "submissions_grade_export_blocked_draft": "tests/test_grade_export_api.py",
    "submissions_grade_export_blocked_pending_review": "tests/test_grade_export_api.py",
    "submissions_grade_export_internal_error": "tests/test_grade_export_api.py",
    # -- submissions.py, TF-773 PR 2c (Import-Endpunkte)
    "submissions_import_driver_unknown": "tests/test_submissions_import_error_codes.py",
    "submissions_import_enqueue_failed": "tests/test_submissions_import_error_codes.py",
    "submissions_import_file_too_large": "tests/test_submissions_import_error_codes.py",
    "submissions_import_internal_error": "tests/test_submissions_import_error_codes.py",
    # -- tags.py (Review-Nachtrag zu TF-773 Teil D, PR #319: der Router fehlte
    # in ROUTERS, wodurch test_backend_codes_sind_im_frontend_registriert ihn
    # nie mit dem Frontend abglich — ein neuer tags_*-Code wäre still auf den
    # UI-Sammelsatz gefallen)
    "tags_access_denied": "tests/test_tags_api_iter2.py::test_unarchive_others_tag_as_non_admin_returns_403",
    "tags_create_questions_permission_required": (
        "tests/test_tags_api.py::test_create_tag_without_permission_returns_403"
    ),
    "tags_delete_archived_only": "tests/test_tags_api_iter2.py::test_cannot_delete_active_tag",
    "tags_global_create_superuser_only": (
        "tests/test_tags_kind_tf397.py::test_content_global_tag_still_requires_superuser"
    ),
    "tags_global_edit_superuser_only": (
        "tests/test_tags_kind_tf397.py::test_non_creator_cannot_archive_global_prompt_tag"
    ),
    "tags_merge_target_in_sources": (
        "tests/test_tags_api_iter2.py::test_merge_with_target_as_source_returns_422"
    ),
    "tags_name_exists": "tests/test_tags_api.py::test_create_tag_race_condition_returns_409",
    "tags_name_exists_on_rename": (
        "tests/test_tags_api_iter2.py::test_rename_to_existing_name_returns_409"
    ),
    "tags_not_found": (
        "tests/test_error_envelope.py::"
        "test_umgestellter_endpunkt_liefert_detail_und_error_code"
    ),
    "tags_prompt_create_permission_required": (
        "tests/test_tags_kind_tf397.py::"
        "test_prompt_tag_create_denied_without_prompt_create_permission"
    ),
    "tags_prompt_delete_not_allowed": "tests/test_tags_kind_tf397.py::test_delete_prompt_tag_blocked",
    "tags_prompt_merge_not_allowed": "tests/test_tags_kind_tf397.py::test_merge_blocks_prompt_kind",
    "tags_still_in_use": "tests/test_tags_api_iter2.py::test_cannot_delete_tag_with_usage",
}

#: Codes, die ein Test unten tatsächlich aus einer Antwort liest, plus die
#: Begründung für die wenigen, die sich nicht über HTTP auslösen lassen.
COVERED: dict[str, str] = {
    # -- moodle_roundtrip.py
    "exams_not_found": "test_roundtrip_exam_not_found",
    "moodle_roundtrip_exam_has_no_questions": "test_roundtrip_exam_without_questions",
    "moodle_roundtrip_question_ids_count_mismatch": "test_roundtrip_count_mismatch",
    "moodle_roundtrip_api_unreachable": "test_roundtrip_api_unreachable",
    "moodle_roundtrip_api_error": "test_roundtrip_api_5xx",
    "moodle_roundtrip_api_rejected": "test_roundtrip_api_4xx",
    "moodle_roundtrip_api_invalid_response": "test_roundtrip_api_not_json",
    "moodle_roundtrip_api_exception": "test_roundtrip_api_exception_is_not_echoed",
    "moodle_roundtrip_quiz_not_visible": "test_roundtrip_quiz_not_visible",
    "moodle_roundtrip_token_decryption_failed": "test_roundtrip_token_undecryptable",
    # -- moodle_connections.py
    "moodle_connections_not_found": "test_connections_not_found",
    "moodle_connections_already_exists": "test_connections_duplicate",
    "moodle_connections_no_fields": "test_connections_empty_update",
    "moodle_connections_token_decryption_failed": "test_connections_token_undecryptable",
    # -- moodle_feedback_push.py
    "moodle_feedback_push_no_connection": "test_push_without_connection",
    "moodle_feedback_push_no_quiz_id": "test_push_without_quiz_id",
    "moodle_feedback_push_queue_unavailable": "test_push_broker_down",
    "moodle_feedback_push_job_not_found": "test_push_job_not_found",
    # -- students.py
    "students_not_found": "test_students_not_found",
    # -- stats.py
    "stats_submission_not_found": "test_stats_submission_not_found",
    # -- activity.py
    "activity_unknown_type": "test_activity_unknown_type",
    "activity_scope_institution_forbidden": (
        "tests/test_activity_api.py::test_scope_institution_rejects_user_without_"
        "institution — braucht eine abgehängte User-Instanz, die dort schon steht"
    ),
    # -- audit.py
    "audit_invalid_date_range": "test_audit_invalid_date_range",
    "audit_unknown_category": "test_audit_unknown_category",
    # -- grade_export.py
    "grade_export_unsupported_format": "test_grade_export_unsupported_format",
    # -- rag_exams.py
    "rag_tag_ids_invalid": "tests/test_rag_api.py::test_generate_rag_exam_with_missing_tag_id_returns_422",
    "rag_tag_archived": "tests/test_rag_api.py::test_generate_rag_exam_with_archived_tag_returns_422",
    "rag_service_unhealthy": "test_rag_service_unhealthy",
    # -- specula_test.py
    "specula_test_dev_only": "test_specula_dev_only",
    "specula_test_queue_unavailable": (
        "tests/test_observability_celery_integration.py::"
        "test_worker_error_endpoint_returns_503_when_broker_unreachable — echter "
        "HTTP-Test über den bereits vorhandenen Broker-down-Mock für diesen "
        "SuperAdmin-gated Endpunkt."
    ),
    # -- submissions.py (TF-773 Teil D; exams_not_found und
    #    stats_submission_not_found stehen oben, derselbe Code aus zwei Routern)
    "submissions_import_job_not_found": "test_submissions_import_job_not_found",
    "submissions_delete_audit_unavailable": "test_submissions_delete_audit_unavailable",
    # -- v1/webhooks.py
    "webhooks_stripe_not_configured": "test_webhook_without_secret",
    "webhooks_stripe_invalid_payload": "test_webhook_invalid_payload",
    "webhooks_stripe_invalid_signature": "test_webhook_invalid_signature",
    "webhooks_stripe_upstream_error": "test_webhook_stripe_error_returns_502",
    "webhooks_stripe_processing_failed": "test_webhook_unexpected_error_returns_500",
}


def _codes_raised_by(rel_path: str) -> set[str]:
    """Konstante Codes, die ``rel_path`` wirft — per AST, nicht per Regex."""
    tree = ast.parse((BACKEND_ROOT / rel_path).read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", getattr(node.func, "attr", ""))
        if name == "api_error" and len(node.args) >= 2:
            arg = node.args[1]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.add(arg.value)
        elif name == "AppHTTPException":
            kw = next((k for k in node.keywords if k.arg == "error_code"), None)
            if kw is not None and isinstance(kw.value, ast.Constant):
                found.add(kw.value.value)
    return found


def test_jede_wurfstelle_ist_hier_abgedeckt() -> None:
    """Der Wächter, der diese Datei am Code festnagelt.

    Ohne ihn wäre ein neuer Code in einem dieser Router hier unsichtbar — und
    genau das war die Lücke, die PR 2d überhaupt erst gefunden hat.
    """
    raised: set[str] = set()
    for rel in ROUTERS:
        raised |= _codes_raised_by(rel)

    fehlend = sorted(raised - set(COVERED) - set(PRE_EXISTING))
    assert not fehlend, (
        f"Diese Codes werfen die Router aus ROUTERS, ohne dass ein Test sie liest: "
        f"{fehlend}. Einen Test ergänzen oder — wenn er sich nicht über HTTP "
        f"auslösen lässt — mit Begründung in COVERED eintragen."
    )

    ueberfluessig = sorted((set(COVERED) | set(PRE_EXISTING)) - raised)
    assert not ueberfluessig, (
        f"COVERED nennt Codes, die keiner der Router mehr wirft: "
        f"{ueberfluessig}. Der Eintrag ist tot — löschen, sonst behauptet diese "
        f"Datei eine Abdeckung, die es nicht gibt."
    )


def test_keine_rohe_exception_mehr_in_den_routern() -> None:
    """``detail=str(exc)`` und f-String-Details sind in diesen Routern weg.

    Statisch geprüft, weil ein einzelner Test pro Wurfstelle nur die Pfade
    sieht, die er selbst auslöst — ein durchgereichter Exception-Text in einem
    Zweig, den kein Test erreicht, bliebe sonst stehen.
    """
    treffer: list[str] = []
    for rel in ROUTERS:
        tree = ast.parse((BACKEND_ROOT / rel).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name not in ("HTTPException", "AppHTTPException"):
                continue
            werte = list(node.args) + [
                k.value for k in node.keywords if k.arg == "detail"
            ]
            for wert in werte:
                if isinstance(wert, ast.JoinedStr):
                    treffer.append(f"{rel}:{node.lineno} (f-String im detail)")
                elif (
                    isinstance(wert, ast.Call) and getattr(wert.func, "id", "") == "str"
                ):
                    treffer.append(f"{rel}:{node.lineno} (str(...) im detail)")
    assert not treffer, "Rohe Exception-Texte in der Antwort: " + ", ".join(treffer)


def test_kein_core_router_wirft_nackte_http_exception() -> None:
    """Kein Router unter ``api/`` erzeugt mehr ein ``HTTPException`` ohne Code.

    Seit TF-773 Teil D gilt das ausnahmslos: ``submissions.py`` war der letzte
    Core-Router mit nackten ``HTTPException`` (vier Stellen, handgeschriebenes
    Deutsch ohne ``error_code``). Geprüft wird bewusst *jede* Datei unter
    ``api/`` und nicht nur ``ROUTERS`` — ein neuer Router soll nicht erst in
    eine Liste eingetragen werden müssen, bevor der Wächter ihn sieht.

    Nur der Aufruf zählt. ``except HTTPException:`` und ein ``raise`` einer
    gefangenen Instanz bleiben erlaubt; ``AppHTTPException`` ist der
    dokumentierte Weg für einen Text, der bewusst nicht aus den Locales kommt.
    """
    api_dir = BACKEND_ROOT / "api"
    dateien = sorted(api_dir.rglob("*.py"))
    assert len(dateien) > 20, (
        f"Nur {len(dateien)} Dateien unter {api_dir} — der Scan greift "
        f"vermutlich nicht mehr."
    )
    treffer: list[str] = []
    for path in dateien:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name == "HTTPException":
                treffer.append(f"{path.relative_to(BACKEND_ROOT)}:{node.lineno}")
    assert not treffer, (
        "Nackte HTTPException ohne error_code: "
        + ", ".join(treffer)
        + ". api_error(status, code, locale) verwenden; der Code braucht einen "
        "Schlüssel in allen vier core/backend/locales/t.*.json."
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _crypto_env(monkeypatch):
    monkeypatch.delenv("MOODLE_TOKEN_ENCRYPTION_KEY", raising=False)
    monkeypatch.setenv("SECRET_KEY", "dev-secret-key-for-tests")
    reset_cache_for_tests()
    yield
    reset_cache_for_tests()


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def _institution(db: Session, slug: str = "pr2d") -> Institution:
    inst = Institution(
        name=f"Inst-{slug}",
        slug=slug,
        subscription_tier="enterprise",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    db.add(inst)
    db.flush()
    return inst


def _user(db: Session, inst_id: int, email: str = "pr2d@test.ch") -> User:
    user = User(
        email=email,
        first_name="P",
        last_name="R",
        password_hash="dummy",  # pragma: allowlist secret
        institution_id=inst_id,
        status=UserStatus.ACTIVE.value,
        is_superuser=True,
        preferred_language="de",
    )
    db.add(user)
    db.flush()
    return user


def _exam(
    db: Session, inst_id: int, *, questions: int = 1, quiz_id: int | None = None
) -> Exam:
    exam = Exam(
        title="PR2D",
        course="TF-773",
        exam_date=date(2026, 5, 15),
        passing_percentage=50.0,
        total_points=float(max(questions, 1)),
        status="finalized",
        language="de",
        institution_id=inst_id,
        visibility=ExamVisibility.INSTITUTION.value,
    )
    db.add(exam)
    db.flush()
    for i in range(questions):
        q = QuestionReview(
            question_text=f"Frage {i}?",
            question_type="true_false",
            correct_answer="wahr",
            difficulty="easy",
            topic="T",
            institution_id=inst_id,
        )
        db.add(q)
        db.flush()
        db.add(
            ExamQuestion(
                exam_id=exam.id,
                question_id=q.id,
                position=i + 1,
                points=1.0,
                external_refs={"moodle_quiz_id": quiz_id} if quiz_id else None,
            )
        )
    db.flush()
    return exam


def _connection(db: Session, inst_id: int, token: str = "tok") -> MoodleConnection:
    conn = MoodleConnection(
        institution_id=inst_id,
        base_url="https://moodle.example",
        token_encrypted=encrypt_secret(token),
    )
    db.add(conn)
    db.flush()
    return conn


def _client(db: Session, user: User, *modules: str) -> TestClient:
    import importlib

    for mod_name in modules:
        mod = importlib.import_module(mod_name)
        for attr in ("router", "router_exam_stats", "router_submission_stats"):
            router = getattr(mod, attr, None)
            if router is not None and router not in app.router.routes:
                app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_active_user] = lambda: user
    return TestClient(app, raise_server_exceptions=True)


def _sync(client: TestClient, exam_id: int, **body) -> httpx.Response:
    payload = {"moodle_quiz_id": 7}
    payload.update(body)
    return client.post(
        f"/api/v1/exams/{exam_id}/sync-moodle-question-ids", json=payload
    )


_MOODLE_URL = "https://moodle.example/webservice/rest/server.php"


# ---------------------------------------------------------------------------
# moodle_roundtrip.py
# ---------------------------------------------------------------------------


def test_roundtrip_exam_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "rt-404")
    user = _user(test_db, inst.id, "rt404@test.ch")
    test_db.commit()
    body = _sync(_client(test_db, user, "api.moodle_roundtrip"), 999999).json()
    assert body["error_code"] == "exams_not_found"
    assert body["detail"] == "Prüfung nicht gefunden"


def test_roundtrip_exam_without_questions(test_db: Session) -> None:
    inst = _institution(test_db, "rt-empty")
    user = _user(test_db, inst.id, "rtempty@test.ch")
    exam = _exam(test_db, inst.id, questions=0)
    test_db.commit()
    resp = _sync(_client(test_db, user, "api.moodle_roundtrip"), exam.id)
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "moodle_roundtrip_exam_has_no_questions"
    assert (
        resp.json()["detail"] == "Diese Prüfung hat keine Fragen — Sync nicht möglich."
    )


def test_roundtrip_count_mismatch(test_db: Session) -> None:
    inst = _institution(test_db, "rt-count")
    user = _user(test_db, inst.id, "rtcount@test.ch")
    exam = _exam(test_db, inst.id, questions=2)
    test_db.commit()
    resp = _sync(
        _client(test_db, user, "api.moodle_roundtrip"), exam.id, moodle_question_ids=[1]
    )
    body = resp.json()
    assert resp.status_code == 400
    assert body["error_code"] == "moodle_roundtrip_question_ids_count_mismatch"
    # Die Zahlen kommen als error_params mit, damit ein Client den Satz selbst
    # bauen kann — genau der Zweck des Feldes (ADR 0005).
    assert body["error_params"] == {"given": 1, "expected": 2}
    assert "1" in body["detail"] and "2" in body["detail"]


def _roundtrip_with_connection(test_db: Session, slug: str):
    inst = _institution(test_db, slug)
    user = _user(test_db, inst.id, f"{slug}@test.ch")
    exam = _exam(test_db, inst.id, questions=1)
    _connection(test_db, inst.id)
    test_db.commit()
    return _client(test_db, user, "api.moodle_roundtrip"), exam


@respx.mock
def test_roundtrip_api_unreachable(test_db: Session) -> None:
    client, exam = _roundtrip_with_connection(test_db, "rt-down")
    respx.post(_MOODLE_URL).mock(side_effect=httpx.ConnectError("no route"))
    resp = _sync(client, exam.id)
    assert resp.status_code == 502
    body = resp.json()
    assert body["error_code"] == "moodle_roundtrip_api_unreachable"
    # Der Kern der Umstellung: der Transportfehler steht nicht mehr drin.
    assert "no route" not in body["detail"]


@respx.mock
def test_roundtrip_api_5xx(test_db: Session) -> None:
    client, exam = _roundtrip_with_connection(test_db, "rt-5xx")
    respx.post(_MOODLE_URL).mock(return_value=httpx.Response(500, text="boom"))
    resp = _sync(client, exam.id)
    assert resp.status_code == 502
    assert resp.json()["error_code"] == "moodle_roundtrip_api_error"
    assert "500" not in resp.json()["detail"]


@respx.mock
def test_roundtrip_api_4xx(test_db: Session) -> None:
    client, exam = _roundtrip_with_connection(test_db, "rt-4xx")
    respx.post(_MOODLE_URL).mock(return_value=httpx.Response(403, text="<html>"))
    resp = _sync(client, exam.id)
    assert resp.status_code == 502
    assert resp.json()["error_code"] == "moodle_roundtrip_api_rejected"


@respx.mock
def test_roundtrip_api_not_json(test_db: Session) -> None:
    client, exam = _roundtrip_with_connection(test_db, "rt-html")
    respx.post(_MOODLE_URL).mock(return_value=httpx.Response(200, text="<html>nope"))
    resp = _sync(client, exam.id)
    assert resp.status_code == 502
    assert resp.json()["error_code"] == "moodle_roundtrip_api_invalid_response"


@respx.mock
def test_roundtrip_api_json_not_a_dict(test_db: Session) -> None:
    """``moodle_roundtrip_api_invalid_response`` has a second, independent
    raise site: valid JSON that parses but isn't an object (e.g. Moodle
    returning a bare array), distinct from the "not JSON at all" case above."""
    client, exam = _roundtrip_with_connection(test_db, "rt-array")
    respx.post(_MOODLE_URL).mock(return_value=httpx.Response(200, json=[]))
    resp = _sync(client, exam.id)
    assert resp.status_code == 502
    assert resp.json()["error_code"] == "moodle_roundtrip_api_invalid_response"


@respx.mock
def test_roundtrip_api_exception_is_not_echoed(test_db: Session) -> None:
    """Moodles eigener Fehlertext ist Upstream-Inhalt und bleibt im Log."""
    client, exam = _roundtrip_with_connection(test_db, "rt-exc")
    respx.post(_MOODLE_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "exception": "moodle_exception",
                "errorcode": "invalidtoken",
                "message": "Ungültiges Token für Kurs 4711",
            },
        )
    )
    resp = _sync(client, exam.id)
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "moodle_roundtrip_api_exception"
    assert "4711" not in body["detail"]
    assert "invalidtoken" not in body["detail"]


@respx.mock
def test_roundtrip_quiz_not_visible(test_db: Session) -> None:
    client, exam = _roundtrip_with_connection(test_db, "rt-vis")
    respx.post(_MOODLE_URL).mock(
        return_value=httpx.Response(200, json={"quizzes": [{"id": 999}]})
    )
    resp = _sync(client, exam.id)
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "moodle_roundtrip_quiz_not_visible"
    assert body["error_params"] == {"quiz_id": 7}
    assert "7" in body["detail"]


def test_roundtrip_token_undecryptable(test_db: Session) -> None:
    inst = _institution(test_db, "rt-key")
    user = _user(test_db, inst.id, "rtkey@test.ch")
    exam = _exam(test_db, inst.id, questions=1)
    conn = _connection(test_db, inst.id)
    conn.token_encrypted = "nicht-entschluesselbar"
    test_db.commit()
    resp = _sync(_client(test_db, user, "api.moodle_roundtrip"), exam.id)
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "moodle_roundtrip_token_decryption_failed"
    assert "nicht-entschluesselbar" not in body["detail"]


# ---------------------------------------------------------------------------
# moodle_connections.py
# ---------------------------------------------------------------------------


def test_connections_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "mc-404")
    user = _user(test_db, inst.id, "mc404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").get(
        "/api/v1/admin/moodle-connections/999999"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "moodle_connections_not_found"


def test_connections_duplicate(test_db: Session) -> None:
    inst = _institution(test_db, "mc-dup")
    user = _user(test_db, inst.id, "mcdup@test.ch")
    _connection(test_db, inst.id)
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").post(
        "/api/v1/admin/moodle-connections",
        json={"base_url": "https://m2.example", "token": "zweites-token"},
    )
    assert resp.status_code == 409
    body = resp.json()
    assert body["error_code"] == "moodle_connections_already_exists"
    assert body["detail"] == (
        "Es existiert bereits eine Moodle-Verbindung für diese Institution."
    )


def test_connections_empty_update(test_db: Session) -> None:
    inst = _institution(test_db, "mc-empty")
    user = _user(test_db, inst.id, "mcempty@test.ch")
    conn = _connection(test_db, inst.id)
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").patch(
        f"/api/v1/admin/moodle-connections/{conn.id}", json={}
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "moodle_connections_no_fields"


def test_connections_token_undecryptable(test_db: Session) -> None:
    inst = _institution(test_db, "mc-key")
    user = _user(test_db, inst.id, "mckey@test.ch")
    conn = _connection(test_db, inst.id)
    conn.token_encrypted = "kaputt"
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").get(
        f"/api/v1/admin/moodle-connections/{conn.id}"
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "moodle_connections_token_decryption_failed"
    assert "kaputt" not in body["detail"]


def test_connections_update_not_found(test_db: Session) -> None:
    """``_load_for_user`` is called independently from four endpoints; this
    covers its second call site (update), distinct from ``get_connection``
    above."""
    inst = _institution(test_db, "mc-upd-404")
    user = _user(test_db, inst.id, "mcupd404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").patch(
        "/api/v1/admin/moodle-connections/999999", json={"base_url": "https://x.test"}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "moodle_connections_not_found"


def test_connections_delete_not_found(test_db: Session) -> None:
    """``_load_for_user``'s third call site (delete)."""
    inst = _institution(test_db, "mc-del-404")
    user = _user(test_db, inst.id, "mcdel404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_connections").delete(
        "/api/v1/admin/moodle-connections/999999"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "moodle_connections_not_found"


# ---------------------------------------------------------------------------
# moodle_feedback_push.py
# ---------------------------------------------------------------------------


def test_push_exam_not_found(test_db: Session) -> None:
    """``exams_not_found`` is shared across four routers; this is
    ``moodle_feedback_push.py``'s own, independent call site
    (``_ensure_exam_for_user``) — a nonexistent id, not the separate
    cross-tenant-visibility 404 that ``assert_exam_visible_for`` raises."""
    inst = _institution(test_db, "fp-exam-404")
    user = _user(test_db, inst.id, "fpexam404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_feedback_push").post(
        "/api/v1/exams/999999/moodle/push-feedback"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "exams_not_found"


def test_push_without_connection(test_db: Session) -> None:
    inst = _institution(test_db, "fp-noconn")
    user = _user(test_db, inst.id, "fpnoconn@test.ch")
    exam = _exam(test_db, inst.id, questions=1, quiz_id=7)
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_feedback_push").post(
        f"/api/v1/exams/{exam.id}/moodle/push-feedback"
    )
    assert resp.status_code == 412
    body = resp.json()
    assert body["error_code"] == "moodle_feedback_push_no_connection"
    assert body["detail"] == (
        "Keine Moodle-Verbindung für diese Institution konfiguriert."
    )


def test_push_without_quiz_id(test_db: Session) -> None:
    inst = _institution(test_db, "fp-noquiz")
    user = _user(test_db, inst.id, "fpnoquiz@test.ch")
    exam = _exam(test_db, inst.id, questions=1)
    _connection(test_db, inst.id)
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_feedback_push").post(
        f"/api/v1/exams/{exam.id}/moodle/push-feedback"
    )
    assert resp.status_code == 412
    assert resp.json()["error_code"] == "moodle_feedback_push_no_quiz_id"


def test_push_broker_down(test_db: Session, monkeypatch) -> None:
    inst = _institution(test_db, "fp-broker")
    user = _user(test_db, inst.id, "fpbroker@test.ch")
    exam = _exam(test_db, inst.id, questions=1, quiz_id=7)
    _connection(test_db, inst.id)
    test_db.commit()

    import api.moodle_feedback_push as mod

    def _boom(**_kwargs):
        raise RuntimeError("broker unreachable at amqp://secret@rabbit")

    monkeypatch.setattr(mod.push_moodle_feedback, "apply_async", _boom)
    resp = _client(test_db, user, "api.moodle_feedback_push").post(
        f"/api/v1/exams/{exam.id}/moodle/push-feedback"
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error_code"] == "moodle_feedback_push_queue_unavailable"
    assert "amqp" not in body["detail"]


def test_push_job_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "fp-job")
    user = _user(test_db, inst.id, "fpjob@test.ch")
    exam = _exam(test_db, inst.id, questions=1, quiz_id=7)
    test_db.commit()
    resp = _client(test_db, user, "api.moodle_feedback_push").get(
        f"/api/v1/exams/{exam.id}/moodle/push-feedback/999999"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "moodle_feedback_push_job_not_found"


# ---------------------------------------------------------------------------
# students.py / stats.py
# ---------------------------------------------------------------------------


def test_students_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "st-404")
    user = _user(test_db, inst.id, "st404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.students").get("/api/v1/students/999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "students_not_found"
    assert body["detail"] == "Studi nicht gefunden"


def test_students_history_not_found(test_db: Session) -> None:
    """``_load_student_for_user`` (shared helper, raises ``students_not_found``)
    hat einen zweiten Call-Site: ``get_student_history`` ruft ihn als Gate,
    bevor der eigentliche Verlauf geladen wird — derselbe Code wie bei
    ``test_students_not_found``, aber über einen anderen Endpunkt ausgelöst.
    Der zweite, unabhängige ``students_not_found``-``raise`` in
    ``get_student_history`` selbst (Fallback, falls ``student_history()``
    ``None`` liefert) ist nach dem Gate praktisch unerreichbar, solange
    ``_load_student_for_user`` dieselbe Institution-Filterung verwendet —
    dieser Test deckt ihn nicht ab."""
    inst = _institution(test_db, "st-hist-404")
    user = _user(test_db, inst.id, "sthist404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.students").get("/api/v1/students/999999/stats")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "students_not_found"


def test_stats_submission_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "stats-404")
    user = _user(test_db, inst.id, "stats404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.stats").get("/api/v1/submissions/999999/stats")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "stats_submission_not_found"


def test_stats_submission_cross_tenant_not_found(test_db: Session) -> None:
    """A submission that exists, but whose exam belongs to another
    institution, must 404 — the same code as a nonexistent id (no
    cross-tenant existence leak). This is the multi-tenancy boundary check
    in ``_ensure_submission_for_user``, distinct from the "no row at all"
    branch above."""
    own_inst = _institution(test_db, "stats-own")
    user = _user(test_db, own_inst.id, "statsown@test.ch")
    other_inst = _institution(test_db, "stats-other")
    exam = _exam(test_db, other_inst.id, questions=1)
    student = Student(institution_id=other_inst.id, external_id="ext-1")
    test_db.add(student)
    test_db.flush()
    submission = Submission(exam_id=exam.id, student_id=student.id)
    test_db.add(submission)
    test_db.commit()

    resp = _client(test_db, user, "api.stats").get(
        f"/api/v1/submissions/{submission.id}/stats"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "stats_submission_not_found"


def test_stats_exam_overview_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "stats-ov-404")
    user = _user(test_db, inst.id, "statsov404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.stats").get(
        "/api/v1/exams/999999/stats/overview"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "exams_not_found"


def test_stats_exam_per_question_not_found(test_db: Session) -> None:
    inst = _institution(test_db, "stats-pq-404")
    user = _user(test_db, inst.id, "statspq404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.stats").get(
        "/api/v1/exams/999999/stats/per-question"
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "exams_not_found"


# ---------------------------------------------------------------------------
# activity.py / audit.py — Passthrough bleibt englisch (TF-295)
# ---------------------------------------------------------------------------


def test_activity_unknown_type(test_db: Session) -> None:
    inst = _institution(test_db, "act-422")
    user = _user(test_db, inst.id, "act422@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.activity").get(
        "/api/v1/activity?types=gibts_nicht"
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["error_code"] == "activity_unknown_type"
    assert isinstance(body["detail"], str), "ADR 0005: detail bleibt ein String"
    assert body["error_params"]["unknown_types"] == "gibts_nicht"


def test_audit_invalid_date_range(test_db: Session) -> None:
    inst = _institution(test_db, "aud-date")
    user = _user(test_db, inst.id, "auddate@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.audit").get(
        "/api/v1/audit?date_from=2026-02-01T00:00:00Z&date_to=2026-01-01T00:00:00Z"
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "audit_invalid_date_range"
    # Passthrough: der englische Text IST hier der Vertrag, nicht ein Locale.
    assert body["detail"] == "date_from must be <= date_to"


def test_audit_unknown_category(test_db: Session) -> None:
    inst = _institution(test_db, "aud-cat")
    user = _user(test_db, inst.id, "audcat@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.audit").get("/api/v1/audit?category=quatsch")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "audit_unknown_category"
    # Der Text ist statisch, der variable Teil steckt in error_params — das
    # dict-``detail`` von früher hätte ADR 0005 verletzt.
    assert body["detail"] == "Unknown category"
    assert body["error_params"]["unknown"] == "quatsch"


# ---------------------------------------------------------------------------
# grade_export.py / rag_exams.py / specula_test.py / v1/webhooks.py
# ---------------------------------------------------------------------------


def test_grade_export_unsupported_format(test_db: Session, monkeypatch) -> None:
    """Der Zweig sitzt hinter einem ``Literal`` und ist über HTTP nicht
    erreichbar — FastAPI weist ein unbekanntes Format schon als 422 ab. Der
    Test leert deshalb die Exporter-Tabelle, damit ein *gültiges* Format die
    ``is None``-Bedingung trifft."""
    import api.grade_export as mod

    inst = _institution(test_db, "ge-fmt")
    user = _user(test_db, inst.id, "gefmt@test.ch")
    exam = _exam(test_db, inst.id, questions=1)
    exam.status = "finalized"
    test_db.commit()

    monkeypatch.setattr(mod, "_EXPORTERS", {})
    resp = _client(test_db, user, "api.grade_export").get(
        f"/api/v1/exams/{exam.id}/grades/export/csv"
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "grade_export_unsupported_format"
    # Passthrough: englisch und ohne Locale-Schlüssel (TF-295).
    assert body["detail"] == "Unsupported export format"


def test_rag_service_unhealthy() -> None:
    """Der Health-Endpunkt hängt an Qdrant; hier zählt die Feldform.

    Vor PR 2d war ``detail`` ein dict — genau die Form, die ADR 0005
    ausschliesst und die ``AppHTTPException`` deshalb ablehnt.
    """
    from errors import api_error

    err = api_error(
        503, "rag_service_unhealthy", "de", service="RAG Service", status="unhealthy"
    )
    assert isinstance(err.detail, str)
    assert err.error_params == {"service": "RAG Service", "status": "unhealthy"}


def test_specula_dev_only(monkeypatch) -> None:
    import api.specula_test as mod

    monkeypatch.setenv("ENVIRONMENT", "production")
    if mod.router not in app.router.routes:
        app.include_router(mod.router)
    resp = TestClient(app, raise_server_exceptions=True).post("/api/specula-test/error")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error_code"] == "specula_test_dev_only"
    assert body["detail"] == "Specula test endpoints are only available in development"


def _webhook_client(test_db: Session) -> TestClient:
    import api.v1.webhooks as mod

    if not any(
        getattr(r, "path", None) == "/api/v1/webhooks/stripe" for r in app.routes
    ):
        app.include_router(mod.router, prefix="/api/v1/webhooks")
    app.dependency_overrides[get_db] = lambda: test_db
    return TestClient(app, raise_server_exceptions=True)


def test_webhook_without_secret(test_db: Session, monkeypatch) -> None:
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    resp = _webhook_client(test_db).post("/api/v1/webhooks/stripe", content=b"{}")
    assert resp.status_code == 500
    assert resp.json()["error_code"] == "webhooks_stripe_not_configured"


def test_webhook_invalid_payload(test_db: Session, monkeypatch) -> None:
    """``construct_event`` wird gestellt statt echt gerufen.

    Stripe prüft die Signatur vor dem JSON-Parsen, ein kaputter Body allein
    landet also im Signatur-Zweig (genau das zeigte der erste Lauf). Der
    ValueError-Zweig des Routers ist trotzdem erreichbar — nur eben nicht über
    einen Body, den dieser Test formen kann.
    """
    import stripe

    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        staticmethod(lambda *a, **k: (_ for _ in ()).throw(ValueError("bad json"))),
    )
    resp = _webhook_client(test_db).post(
        "/api/v1/webhooks/stripe",
        content=b"kein json",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "webhooks_stripe_invalid_payload"
    assert "bad json" not in body["detail"]


def test_webhook_invalid_signature(test_db: Session, monkeypatch) -> None:
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    resp = _webhook_client(test_db).post(
        "/api/v1/webhooks/stripe",
        content=json.dumps({"id": "evt_1", "object": "event"}).encode(),
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "webhooks_stripe_invalid_signature"


def test_webhook_stripe_error_returns_502(test_db: Session, monkeypatch) -> None:
    """A ``stripe.error.StripeError`` out of a handler (e.g. Stripe API outage
    while retrieving the subscription) is a 502 with its own code — unlike a
    ``ValueError`` it should make Stripe retry, so it can't reuse the 200
    ``webhooks_stripe_data_error`` acknowledgement. The raw Stripe message stays out
    of the response body."""
    import stripe

    import api.v1.webhooks as mod

    message = "Stripe API is temporarily unavailable (internal diagnostic detail)"
    event = SimpleNamespace(
        type="checkout.session.completed", data=SimpleNamespace(object=object())
    )
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(
        mod.stripe.Webhook, "construct_event", staticmethod(lambda *a, **k: event)
    )

    async def _raise(*_args, **_kwargs):
        raise stripe.error.StripeError(message)

    monkeypatch.setattr(mod, "handle_checkout_session_completed", _raise)

    resp = _webhook_client(test_db).post(
        "/api/v1/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 502
    body = resp.json()
    assert body["error_code"] == "webhooks_stripe_upstream_error"
    assert message not in body["detail"]


def test_webhook_unexpected_error_returns_500(test_db: Session, monkeypatch) -> None:
    """Any other exception out of a handler (a genuine bug, not a Stripe or
    data problem) is a generic 500 with its own code; the real exception text
    and type stay in the log, not the response."""
    import api.v1.webhooks as mod

    message = "boom: unexpected KeyError('institution_id')"
    event = SimpleNamespace(
        type="checkout.session.completed", data=SimpleNamespace(object=object())
    )
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    monkeypatch.setattr(
        mod.stripe.Webhook, "construct_event", staticmethod(lambda *a, **k: event)
    )

    async def _raise(*_args, **_kwargs):
        raise RuntimeError(message)

    monkeypatch.setattr(mod, "handle_checkout_session_completed", _raise)

    resp = _webhook_client(test_db).post(
        "/api/v1/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=deadbeef"},
    )
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "webhooks_stripe_processing_failed"
    assert message not in body["detail"]


# ---------------------------------------------------------------------------
# submissions.py (TF-773 Teil D)
# ---------------------------------------------------------------------------


def test_submissions_exam_not_found(test_db: Session) -> None:
    """``_load_exam_for_user`` sendet den gemeinsamen Code, kein Synonym."""
    inst = _institution(test_db, "sub-exam-404")
    user = _user(test_db, inst.id, "subexam404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.submissions").get(
        "/api/v1/submissions/import/summary", params={"exam_id": 999999}
    )
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "exams_not_found"


def test_submissions_import_job_not_found(test_db: Session) -> None:
    """Bewusst dieselbe Wurfstelle wie
    ``test_submissions_import_error_codes.py::test_unbekannter_import_job_hat_eigenen_code``
    (beide von ``test_jede_wurfstelle_ist_hier_abgedeckt`` bzw. dessen
    Import-Pendant ``test_jeder_import_code_hat_einen_nachweis`` verlangt,
    unabhängig voneinander): jener Test prüft nur die Abwesenheit von Interna
    (``_assert_clean``), dieser hier zusätzlich den exakten, lokalisierten
    ``detail``-Text — kein Kopierfehler, sondern zwei verschiedene Zusagen."""
    inst = _institution(test_db, "sub-job-404")
    user = _user(test_db, inst.id, "subjob404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.submissions").get(
        "/api/v1/submissions/import-jobs/999999"
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "submissions_import_job_not_found"
    assert body["detail"] == "Import-Job nicht gefunden"


def test_submissions_detail_not_found(test_db: Session) -> None:
    """Dieselbe Tatsache wie in ``stats.py``, derselbe Code (ADR 0006)."""
    inst = _institution(test_db, "sub-detail-404")
    user = _user(test_db, inst.id, "subdetail404@test.ch")
    test_db.commit()
    resp = _client(test_db, user, "api.submissions").get("/api/v1/submissions/999999")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "stats_submission_not_found"


def test_submissions_delete_audit_unavailable(test_db: Session, monkeypatch) -> None:
    """Scheitert der Audit-Eintrag, wird die Löschung zurückgerollt — und die
    Antwort muss das sagen, nicht bloss «Löschen fehlgeschlagen»."""
    import api.submissions as mod

    inst = _institution(test_db, "sub-audit")
    user = _user(test_db, inst.id, "subaudit@test.ch")
    exam = _exam(test_db, inst.id, questions=1)
    test_db.commit()
    monkeypatch.setattr(mod.AuditService, "log_action", lambda **_kwargs: None)

    resp = _client(test_db, user, "api.submissions").delete(
        "/api/v1/submissions/import", params={"exam_id": exam.id}
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error_code"] == "submissions_delete_audit_unavailable"
    assert "Audit-Log" in body["detail"]


@pytest.mark.parametrize(
    ("preferred", "accept_language", "erwarteter_text"),
    [
        # 1. preferred_language gesetzt — gewinnt auch gegen Accept-Language
        ("fr", "it-CH,it;q=0.9", "Tâche d'import introuvable"),
        # 2. nur Accept-Language
        (None, "en-US,en;q=0.9", "Import job not found"),
        # 3. keines von beiden — Default de
        (None, None, "Import-Job nicht gefunden"),
    ],
    ids=["preferred_language", "accept_language", "default"],
)
def test_submissions_locale_aufloesungspfade(
    test_db: Session, preferred, accept_language, erwarteter_text
) -> None:
    """Die drei Auflösungspfade über HTTP, an einem Endpunkt, dem Teil D die
    Locale erst verdrahtet hat.

    ``test_error_envelope.py::test_aufloesungspfade`` prüft dieselben drei
    Pfade seit #249 an ``tags.py``. Das beweist aber nichts für einen anderen
    Router: dort war die Lehre, dass die Unit-Tests grün waren, während
    ``tags.py`` die Locale gar nicht auflöste. Hier also dieselbe Probe für
    ``submissions.py``.
    """
    inst = _institution(test_db, f"sub-loc-{preferred}-{bool(accept_language)}")
    user = _user(
        test_db, inst.id, f"subloc-{preferred}-{bool(accept_language)}@test.ch"
    )
    user.preferred_language = preferred
    test_db.commit()
    headers = {"Accept-Language": accept_language} if accept_language else {}
    resp = _client(test_db, user, "api.submissions").get(
        "/api/v1/submissions/import-jobs/999999", headers=headers
    )
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "submissions_import_job_not_found"
    assert body["detail"] == erwarteter_text


# ---------------------------------------------------------------------------
# Der Wächter, an dem der Zweck dieses PRs hängt
# ---------------------------------------------------------------------------

#: Codes, die das Frontend bewusst NICHT annimmt, mit dem Grund. Ohne diese
#: Liste müsste der Test unten "mindestens" prüfen statt exakt — und würde
#: genau dann nichts sagen, wenn jemand einen Code vergisst.
NICHT_IM_FRONTEND: dict[str, str] = {
    "moodle_roundtrip_quiz_not_visible": (
        "SyncMoodleIdsDialog fängt status === 404 vorher ab und rendert seine "
        "eigene notVisible-Meldung mit der Quiz-ID darin"
    ),
    "activity_unknown_type": (
        "Frontend-Bug, kein Nutzerfehler — Aktivitaeten.tsx baut die types-CSV "
        "selbst; der Satz gehört in die Konsole, nicht auf den Schirm"
    ),
    "activity_scope_institution_forbidden": "Passthrough (TF-295), kein Locale-Schlüssel",
    "audit_invalid_date_range": "Passthrough (TF-295), AuditLogView sendet keine Datumsfilter",
    "audit_unknown_category": "Passthrough (TF-295), Kategorie kommt aus einem Select",
    "grade_export_unsupported_format": "Passthrough (TF-295), hinter einem Literal unerreichbar",
    "specula_test_dev_only": "Diagnose-Endpunkt, kein Frontend-Pfad",
    "specula_test_queue_unavailable": "Diagnose-Endpunkt, kein Frontend-Pfad",
    # rag_*: seit TF-773 Teil D sind die erreichbaren zehn registriert (und
    # RAGService liest den Code überhaupt erst). Diese vier erreicht keine
    # Aufrufstelle — dieselbe Liste steht im Kopf von codes/rag.ts.
    "rag_invalid_question_type": (
        "RAGService.validateRAGRequest lässt vor dem Senden nur eine echte "
        "Teilmenge der Backend-Fragetypen durch"
    ),
    "rag_retry_only_failed": (
        "Retry-Knopf nur bei FAILURE/REVOKED und während des Laufs gesperrt"
    ),
    "rag_retry_no_request_data": "generate-exam speichert request_data immer",
    "rag_service_unhealthy": "RAGService.checkHealth hat keinen Aufrufer",
    # tags_prompt_*: TagCreateForm/TagSettingsPage senden nie kind='prompt'
    # (listTags()/createTag() ohne kind, Backend-Default 'content') — dieselbe
    # Begründung steht im Kopf von codes/tags.ts.
    "tags_prompt_create_permission_required": (
        "Nur für kind='prompt'; TagCreateForm/TagSettingsPage senden nie kind='prompt'"
    ),
    "tags_prompt_delete_not_allowed": (
        "Nur für kind='prompt'; TagCreateForm/TagSettingsPage senden nie kind='prompt'"
    ),
    "tags_prompt_merge_not_allowed": (
        "Nur für kind='prompt'; TagCreateForm/TagSettingsPage senden nie kind='prompt'"
    ),
    "submissions_grade_export_internal_error": (
        "NotenexportPanel rendert nur die conflict-Art aus der Antwort; ein 500 "
        "bekommt den eigenen auswertungen.export.*-Satz, siehe codes/submissions.ts"
    ),
    "webhooks_stripe_not_configured": "Stripe ruft das, kein Browser",
    "webhooks_stripe_invalid_payload": "Stripe ruft das, kein Browser",
    "webhooks_stripe_invalid_signature": "Stripe ruft das, kein Browser",
    "webhooks_stripe_upstream_error": "Stripe ruft das, kein Browser",
    "webhooks_stripe_processing_failed": "Stripe ruft das, kein Browser",
}


def _frontend_root() -> pathlib.Path | None:
    """``core/frontend/src`` — oder ``None`` im ``core/``-Mirror.

    Der Mirror entsteht per ``git subtree split --prefix=core``, dort liegt das
    Frontend unter ``frontend/`` statt ``core/frontend/``; ein fester
    ``parents[3]``-Pfad greift daneben und der Wächter wäre dort rot, ohne dass
    irgendetwas kaputt ist. Deshalb aufwärts suchen statt zählen — dieselbe
    Vorsichtsmassnahme, die ``test_error_codes_contract.py`` für die fehlenden
    premium-/enterprise-Verzeichnisse trifft.
    """
    here = pathlib.Path(__file__).resolve()
    for base in here.parents:
        for rel in ("core/frontend/src", "frontend/src"):
            cand = base / rel
            if (cand / "errors" / "codes").is_dir():
                return cand
    return None


def _frontend_accept_list(root: pathlib.Path) -> set[str]:
    """Alle Codes aus ``errors/codes/*.ts``.

    Bewusst textuell und nicht über einen TS-Parser: die Dateien sind
    ausnahmslos ``export const X = ['a', 'b'] as const;``, und ein Testlauf,
    der dafür eine Node-Toolchain braucht, liefe in der Backend-CI nicht.
    """
    import re

    codes_dir = root / "errors" / "codes"
    found: set[str] = set()
    for path in sorted(codes_dir.glob("*.ts")):
        text = path.read_text(encoding="utf-8")
        # Nur die Array-Literale, nicht die Prosa in den Kopfkommentaren.
        for block in re.findall(r"=\s*\[(.*?)\]\s*as const", text, re.S):
            found |= set(re.findall(r"'([a-z0-9_.]+)'", block))
    return found


def test_backend_codes_sind_im_frontend_registriert() -> None:
    """Ein Code, der nicht in der Accept-List steht, ist im UI unsichtbar.

    ``selectCode()`` (``core/frontend/src/errors/errorBody.ts``) verwirft einen
    unbekannten ``error_code`` und setzt den Fallback der aufrufenden Stelle;
    ``translateError()`` rendert ``detail`` grundsätzlich nie. Ein Backend-Code
    ohne Registrierung erreicht den Bildschirm also nicht — und *kein*
    bestehender Test wird davon rot, weil die Antwort formal korrekt ist. Die
    einzige Spur ist ein ``console.warn``.

    Genau das war der Ausgangsbefund von PR 2d: alle zehn Codes, die PR #273
    für diese Router registriert hatte, waren Operations-Fallbacks — das
    Senden desselben Namens hätte auf dem Schirm nichts geändert.

    Der Test ist ein exakter Mengenvergleich in beide Richtungen: ein neuer
    Code muss entweder registriert werden oder mit Grund in
    ``NICHT_IM_FRONTEND`` stehen.
    """
    # PRE_EXISTING zählt hier mit: dass ein anderer Test den Code *wirft*,
    # sagt nichts darüber, ob das UI ihn *zeigt*. Bis Teil D fehlten genau
    # dort die zwölf rag_*-Codes aus #249.
    raised: set[str] = set()
    for rel in ROUTERS:
        raised |= _codes_raised_by(rel)

    root = _frontend_root()
    if root is None:
        pytest.skip("Kein Frontend im Baum (core/-Mirror) — nichts zu prüfen.")
    registriert = _frontend_accept_list(root)
    assert len(registriert) > 200, (
        f"Nur {len(registriert)} Frontend-Codes gefunden — der Scan greift "
        f"vermutlich nicht mehr (Dateiform in errors/codes/ geändert?)."
    )

    unsichtbar = sorted(raised - registriert - set(NICHT_IM_FRONTEND))
    assert not unsichtbar, (
        f"Diese Backend-Codes erreichen das UI nicht: {unsichtbar}. Entweder in "
        f"core/frontend/src/errors/codes/*.ts eintragen (plus errors.<code> in "
        f"allen vier Frontend-Locales) oder mit Begründung in NICHT_IM_FRONTEND "
        f"aufnehmen. Stillschweigend liegen lassen heisst: die Lehrperson sieht "
        f"den generischen Sammelsatz und nichts wird rot."
    )

    unnoetig = sorted(set(NICHT_IM_FRONTEND) & registriert)
    assert not unnoetig, (
        f"NICHT_IM_FRONTEND nennt Codes, die sehr wohl registriert sind: "
        f"{unnoetig}. Der Eintrag ist falsch — löschen."
    )

    tot = sorted(set(NICHT_IM_FRONTEND) - raised)
    assert not tot, (
        f"NICHT_IM_FRONTEND nennt Codes, die keiner der Router wirft: {tot}."
    )


def test_registrierte_codes_haben_einen_frontend_text() -> None:
    """Die zweite Hälfte: registriert, aber ohne ``errors.<code>`` im Locale,
    rendert ``translateError`` wieder den Fallback — dieselbe stille Lücke, nur
    eine Ebene weiter. ``AppErrorCode.i18n.test.ts`` prüft das für die ganze
    Registry, läuft aber in der Frontend-Suite; für die Codes aus diesem Paket
    hängt die Zusage sonst an einer Suite, die der Backend-Teil nicht sieht.
    """
    raised: set[str] = set()
    for rel in ROUTERS:
        raised |= _codes_raised_by(rel)
    zu_pruefen = raised - set(NICHT_IM_FRONTEND)

    root = _frontend_root()
    if root is None:
        pytest.skip("Kein Frontend im Baum (core/-Mirror) — nichts zu prüfen.")
    for lang in ("de", "en", "fr", "it"):
        doc = json.loads(
            (root / "locales" / lang / "translation.json").read_text(encoding="utf-8")
        )
        fehlend = sorted(c for c in zu_pruefen if c not in doc.get("errors", {}))
        assert not fehlend, f"errors.<code> fehlt in {lang}/translation.json: {fehlend}"
