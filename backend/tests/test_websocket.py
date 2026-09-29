"""Tests for the WebSocket task progress endpoint"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def ws_app():
    """Minimal FastAPI app carrying the real WebSocket router.

    Uses the canonically imported module rather than loading a private copy
    over ``sys.modules["api.v1.websocket"]``. The old form left that entry
    pointing at a throwaway module for the rest of the session, so a later
    app lifespan would register the throwaway router on the real app and
    ``patch("api.v1.websocket....")`` would reach an object no route used
    (TF-660).
    """
    from api.v1 import websocket as ws_module

    app = FastAPI()
    app.include_router(ws_module.router)
    return app


@pytest.fixture
def valid_token_payload():
    return {"sub": "1", "jti": "test-jti-123", "email": "test@example.com"}


@pytest.fixture
def mock_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.is_active = True
    user.is_superuser = False
    return user


@pytest.fixture
def mock_document():
    doc = MagicMock()
    doc.user_id = 1
    doc.task_id = "test-task-id"
    return doc


class TestWebSocketConnection:
    def test_websocket_connection_valid_token(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """Connection with a valid token handshake is accepted"""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "SUCCESS"
            mock_task_result.info = {}
            mock_task_result.result = {"document_id": 1}
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})
                data = ws.receive_json()
                assert data["status"] == "SUCCESS"

    def test_websocket_invalid_token(self, ws_app):
        """Invalid token → WebSocket is closed"""
        with patch("api.v1.websocket.AuthService") as mock_auth:
            mock_auth.decode_token.return_value = None

            client = TestClient(ws_app)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "invalid-token"})
                    ws.receive_json()

    def test_websocket_revoked_token(self, ws_app, valid_token_payload, mock_user):
        """Revoked token → WebSocket is closed"""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = True

            mock_db = MagicMock()
            mock_session.return_value = mock_db

            client = TestClient(ws_app)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "revoked-token"})
                    ws.receive_json()

    def test_websocket_wrong_ownership(self, ws_app, valid_token_payload, mock_user):
        """Task belongs to a different user → WebSocket is closed"""
        wrong_doc = MagicMock()
        wrong_doc.user_id = 999

        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                wrong_doc
            )

            client = TestClient(ws_app)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "valid-token"})
                    ws.receive_json()


class TestWebSocketProgressUpdates:
    def test_task_progress_updates(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """PROGRESS messages are transmitted correctly"""
        call_count = 0

        def make_result(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if call_count == 1:
                r.state = "PROGRESS"
                r.info = {"progress": 40, "message": "Docling-Verarbeitung läuft..."}
                r.result = None
            else:
                r.state = "SUCCESS"
                r.info = {}
                r.result = {"document_id": 1}
            return r

        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult", side_effect=make_result),
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})

                first = ws.receive_json()
                assert first["status"] == "PROGRESS"
                assert first["progress"] == 40
                assert "Docling" in first["message"]

                second = ws.receive_json()
                assert second["status"] == "SUCCESS"

    @pytest.mark.parametrize(
        "state, info, expected_code, expected_params",
        [
            (
                "PROGRESS",
                {
                    "progress": 50,
                    "message": "",
                    "code": "question_generated",
                    "params": {"current": 2, "total": 6},
                },
                "question_generated",
                {"current": 2, "total": 6},
            ),
            ("STARTED", {}, "task_started", {}),
            ("RETRY", {}, "task_retrying", {}),
        ],
    )
    def test_progress_code_and_params_are_relayed(
        self,
        ws_app,
        valid_token_payload,
        mock_user,
        mock_document,
        state,
        info,
        expected_code,
        expected_params,
    ):
        """TF-736: code + params reach the client; no German display text."""
        call_count = 0

        def make_result(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            r = MagicMock()
            if call_count == 1:
                r.state = state
                r.info = info
                r.result = None
            else:
                r.state = "SUCCESS"
                r.info = {}
                r.result = {"document_id": 1}
            return r

        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult", side_effect=make_result),
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})

                first = ws.receive_json()
                assert first["status"] == "PROGRESS"
                assert first["message"] is None
                assert first["message_code"] == expected_code
                assert first["message_params"] == expected_params

    def test_connection_closed_on_success(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """Connection is closed after SUCCESS"""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "SUCCESS"
            mock_task_result.info = {}
            mock_task_result.result = {"document_id": 1}
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})
                data = ws.receive_json()
                assert data["status"] == "SUCCESS"
                with pytest.raises(Exception):
                    ws.receive_json()

    def test_connection_closed_on_failure(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """Connection is closed after FAILURE"""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "FAILURE"
            mock_task_result.info = Exception("Verarbeitung fehlgeschlagen")
            mock_task_result.result = None
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})
                data = ws.receive_json()
                assert data["status"] == "FAILURE"
                assert data["error"] is not None

    def test_connection_closed_on_revoked(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """REVOKED is just as terminal as FAILURE — the client must not
        receive any further updates after a REVOKED message. Without this
        test, a regression that removes REVOKED from the terminal tuple
        (e.g. a "unification" with FAILURE) would go unnoticed — the
        frontend's sticky-terminal protection (TF-328) would then be
        ineffective, because the backend would no longer send a REVOKED
        frame at all.
        """
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "REVOKED"
            mock_task_result.info = Exception("Task wurde abgebrochen")
            mock_task_result.result = None
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})
                data = ws.receive_json()
                assert data["status"] == "REVOKED"
                assert data["error"] is not None
                with pytest.raises(Exception):
                    # Server must close after REVOKED — no further
                    # frame (analogous to SUCCESS/FAILURE behavior).
                    ws.receive_json()


class TestWebSocketDisconnect:
    def test_websocket_disconnect_handling(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        """Sauberes Cleanup bei Client-Disconnect"""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "PENDING"
            mock_task_result.info = {}
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            try:
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "valid-token"})
            except Exception:
                pass  # Disconnect is OK


@pytest.fixture
def ws_module():
    """The websocket module, so pure helper functions like
    user_facing_task_error can be tested directly. Canonical import — see
    ws_app above for why this must not load a private copy."""
    from api.v1 import websocket

    return websocket


class TestUserFacingError:
    """TF-358: The real task error is logged, but the user is shown a safe,
    actionable message — known error classes get a specific message,
    unknowns get a generic one (no info leak). TF-967: each message comes
    with its API error code, and the German text is the de locale entry."""

    def test_no_context_maps_to_actionable_message(self, ws_module):
        # The exact production error from TF-358.
        code, msg = ws_module.user_facing_task_error(
            ValueError("No context available for question generation")
        )
        assert code == "rag_task_no_context"
        assert "durchsuchbaren Inhalt" in msg

    def test_no_relevant_context_maps_to_actionable_message(self, ws_module):
        code, msg = ws_module.user_facing_task_error(
            ValueError("No relevant context found for topic: Foo")
        )
        assert code == "rag_task_no_context"
        assert "durchsuchbaren Inhalt" in msg

    def test_unknown_question_type_maps_to_actionable_message(self, ws_module):
        code, msg = ws_module.user_facing_task_error(
            ValueError("Unknown question type: xyz")
        )
        assert code == "rag_task_unknown_question_type"
        assert "Fragetyp" in msg

    def test_unknown_error_falls_back_to_generic_no_leak(self, ws_module):
        # Internals (table names, stack trace fragments) must NOT leak through.
        leaky = ValueError(
            "IntegrityError: duplicate key value violates unique constraint "
            '"question_source_doc_pkey" DETAIL: Key (id)=(42) at /app/secret.py'
        )
        code, msg = ws_module.user_facing_task_error(leaky)
        assert code == ws_module.TASK_FAILED
        assert "question_source_doc" not in msg
        assert "secret" not in msg

    def test_none_info_falls_back_to_generic(self, ws_module):
        assert ws_module.user_facing_task_error(None).code == ws_module.TASK_FAILED

    def test_maps_via_stable_code_independent_of_message(self, ws_module):
        # TF-358: Mapping must work via the stable .code, even if the raw
        # message does NOT contain the English substring (robustness against
        # rewording/localization). The typed errors live in core.
        from services.rag_errors import NoContextError, UnknownQuestionTypeError

        no_ctx = ws_module.user_facing_task_error(
            NoContextError("völlig andere Formulierung ohne Schlüsselwörter")
        )
        assert no_ctx.code == "rag_task_no_context"

        unknown_type = ws_module.user_facing_task_error(
            UnknownQuestionTypeError("anderer Text")
        )
        assert unknown_type.code == "rag_task_unknown_question_type"

    def test_message_is_the_german_locale_text_of_the_code(self, ws_module):
        # TF-967: one source for the text. `error` is the de locale entry of
        # the code the frontend renders, not a second, drifting literal.
        from services.translation_service import t

        for raw in (None, ValueError("no context available"), ValueError("x")):
            code, msg = ws_module.user_facing_task_error(raw)
            assert msg == t(code, "de")


def _task_error_codes() -> set[str]:
    """Every ``rag_task_*`` constant in ``services.rag_errors``. Derived, not
    listed, so a code added there is checked below without touching this
    test."""
    from services import rag_errors

    return {
        value
        for name, value in vars(rag_errors).items()
        if name.isupper() and isinstance(value, str) and value.startswith("rag_task_")
    }


TASK_ERROR_CODES = _task_error_codes()


class TestTaskErrorCodeContract:
    """TF-967: the task error codes are sent from a WebSocket frame or the
    task result response, not raised via ``api_error()``, so
    ``test_error_codes_contract.py`` does not see them. Tie every code in
    ``services.rag_errors`` to the locales and to the frontend accept-list
    here — a code missing from ``codes/rag.ts`` would be dropped silently and
    the panel would show the German ``error`` text again."""

    def test_derivation_finds_the_known_codes(self):
        # Guards the introspection itself: if it found nothing, the two
        # tests below would pass vacuously.
        from services import rag_errors

        assert {
            rag_errors.TASK_FAILED,
            rag_errors.TASK_NO_CONTEXT,
            rag_errors.TASK_UNKNOWN_QUESTION_TYPE,
            rag_errors.TASK_STATUS_UNAVAILABLE,
            rag_errors.TASK_PENDING_TIMEOUT,
            rag_errors.TASK_STREAM_ERROR,
        } <= TASK_ERROR_CODES

    def test_every_code_has_a_backend_locale_key(self):
        import json
        import pathlib

        locales = pathlib.Path(__file__).resolve().parents[1] / "locales"
        de = json.loads((locales / "t.de.json").read_text(encoding="utf-8"))["de"]
        assert [c for c in sorted(TASK_ERROR_CODES) if c not in de] == []

    def test_every_code_is_registered_in_the_frontend(self):
        import pathlib
        import re

        rag_ts = (
            pathlib.Path(__file__).resolve().parents[2]
            / "frontend/src/errors/codes/rag.ts"
        ).read_text(encoding="utf-8")
        registered = set(re.findall(r"^\s*'(rag_[a-z_]+)',$", rag_ts, re.M))
        assert len(registered) > 5, "rag.ts scan finds nothing — file rebuilt?"
        assert [c for c in sorted(TASK_ERROR_CODES) if c not in registered] == []


class TestFailureMessageMapping:
    """Integration test: the FAILURE frame carries the actionable message
    instead of the generic one — this test fails without the TF-358 fix."""

    def test_no_context_failure_sends_actionable_error(
        self, ws_app, valid_token_payload, mock_user, mock_document
    ):
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
            patch("api.v1.websocket.AsyncResult") as mock_result,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False

            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            mock_task_result = MagicMock()
            mock_task_result.state = "FAILURE"
            mock_task_result.info = ValueError(
                "No context available for question generation"
            )
            mock_task_result.result = None
            mock_result.return_value = mock_task_result

            client = TestClient(ws_app)
            with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                ws.send_json({"token": "valid-token"})
                data = ws.receive_json()
                assert data["status"] == "FAILURE"
                assert "durchsuchbaren Inhalt" in data["error"]
                assert (
                    data["error"]
                    != "Verarbeitung fehlgeschlagen. Bitte erneut versuchen."
                )


class TestFailureFramesCarryErrorCode:
    """TF-967: every FAILURE frame the stream can send carries ``error_code``,
    so the frontend renders it in the user's language. ``error`` stays as the
    German fallback and must equal the de locale text of that code."""

    @pytest.fixture
    def connect(self, ws_app, valid_token_payload, mock_user, mock_document):
        """Open an authenticated socket on an owned task; yields a function
        that sends the handshake and returns the first frame."""
        with (
            patch("api.v1.websocket.AuthService") as mock_auth,
            patch("api.v1.websocket.SessionLocal") as mock_session,
        ):
            mock_auth.decode_token.return_value = valid_token_payload
            mock_auth.is_token_revoked.return_value = False
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_document
            )

            def _first_frame():
                client = TestClient(ws_app)
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "valid-token"})
                    return ws.receive_json()

            yield _first_frame

    @staticmethod
    def _assert_frame(data, code, params=None):
        from services.translation_service import t

        assert data["status"] == "FAILURE"
        assert data["error_code"] == code
        assert data["error_params"] == params
        assert data["error"] == t(code, "de", **(params or {}))

    @staticmethod
    def _failed_task(info):
        task = MagicMock()
        task.state = "FAILURE"
        task.info = info
        task.result = None
        return task

    def test_case_1_unmapped_error(self, connect):
        with patch("api.v1.websocket.AsyncResult") as mock_result:
            mock_result.return_value = self._failed_task(RuntimeError("boom"))
            data = connect()
        self._assert_frame(data, "rag_task_failed")

    def test_case_2_no_context(self, connect):
        from services.rag_errors import NoContextError

        with patch("api.v1.websocket.AsyncResult") as mock_result:
            mock_result.return_value = self._failed_task(NoContextError("x"))
            data = connect()
        self._assert_frame(data, "rag_task_no_context")

    def test_case_3_unknown_question_type(self, connect):
        from services.rag_errors import UnknownQuestionTypeError

        with patch("api.v1.websocket.AsyncResult") as mock_result:
            mock_result.return_value = self._failed_task(UnknownQuestionTypeError("x"))
            data = connect()
        self._assert_frame(data, "rag_task_unknown_question_type")

    def test_case_4_redis_unreachable(self, connect):
        with (
            patch("api.v1.websocket.AsyncResult", side_effect=ConnectionError("down")),
            patch("api.v1.websocket.POLL_INTERVAL_SECONDS", 0),
        ):
            data = connect()
        self._assert_frame(data, "rag_task_status_unavailable")

    def test_case_5_pending_timeout_without_task_id(self, connect):
        import logging

        pending = MagicMock()
        pending.state = "PENDING"
        pending.info = None
        ws_logger = logging.getLogger("api.v1.websocket")
        with (
            patch("api.v1.websocket.AsyncResult", return_value=pending),
            patch("api.v1.websocket.POLL_INTERVAL_SECONDS", 0),
            patch("api.v1.websocket.PENDING_TIMEOUT_SECONDS", 0),
            patch.object(ws_logger, "error") as mock_error,
        ):
            data = connect()
        self._assert_frame(data, "rag_task_pending_timeout", {"seconds": 0})
        # The internal id is of no use to the user — neither in the fallback
        # text nor anywhere else in the payload besides `task_id` itself.
        assert "test-task-id" not in data["error"]
        assert "test-task-id" not in str(data["error_params"])
        # ...but operations need it: a task that never starts is logged.
        mock_error.assert_called_once()
        assert mock_error.call_args[0][1] == "test-task-id"

    def test_case_6_unexpected_stream_error(self, connect):
        with patch(
            "api.v1.websocket._get_task_result", side_effect=RuntimeError("bug")
        ):
            data = connect()
        self._assert_frame(data, "rag_task_stream_error")

    def test_revoked_frame_carries_the_code_too(self, connect):
        task = self._failed_task(RuntimeError("revoked"))
        task.state = "REVOKED"
        with patch("api.v1.websocket.AsyncResult", return_value=task):
            data = connect()
        assert data["status"] == "REVOKED"
        assert data["error_code"] == "rag_task_failed"

    def test_unmapped_alert_log_is_keyed_on_the_code(self, connect):
        # The alerting hangs on "unmapped error class". It must keep firing
        # for the generic fallback and stay quiet for a mapped error, now that
        # the check compares the code instead of the German text.
        import logging

        from services.rag_errors import NoContextError

        ws_logger = logging.getLogger("api.v1.websocket")
        for info, expected in (
            (RuntimeError("boom"), "unmapped error class"),
            (NoContextError("x"), "mapped error"),
        ):
            with (
                patch("api.v1.websocket.AsyncResult") as mock_result,
                patch.object(ws_logger, "error") as mock_error,
            ):
                mock_result.return_value = self._failed_task(info)
                connect()
            assert mock_error.call_args[0][2] == expected


class TestSchemaRejectsErrorCodeOnSuccess:
    """TF-967: `error_code` follows the same invariant as `error`."""

    def test_task_status_message(self):
        from pydantic import ValidationError

        from schemas.task import TaskStatus, TaskStatusMessage

        with pytest.raises(ValidationError, match="must not have error"):
            TaskStatusMessage(
                task_id="t",
                status=TaskStatus.SUCCESS,
                progress=100,
                error_code="rag_task_failed",
            )

    def test_task_result_response(self):
        from pydantic import ValidationError

        from schemas.active_tasks import TaskResultResponse
        from schemas.task import TaskStatus

        with pytest.raises(ValidationError, match="must not have error"):
            TaskResultResponse(
                task_id="t", status=TaskStatus.SUCCESS, error_code="rag_task_failed"
            )
