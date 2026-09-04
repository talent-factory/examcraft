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
    unknowns get a generic one (no info leak)."""

    def test_no_context_maps_to_actionable_message(self, ws_module):
        # The exact production error from TF-358.
        msg = ws_module.user_facing_task_error(
            ValueError("No context available for question generation")
        )
        assert "durchsuchbaren Inhalt" in msg
        assert msg != ws_module.GENERIC_TASK_ERROR

    def test_no_relevant_context_maps_to_actionable_message(self, ws_module):
        msg = ws_module.user_facing_task_error(
            ValueError("No relevant context found for topic: Foo")
        )
        assert "durchsuchbaren Inhalt" in msg

    def test_unknown_question_type_maps_to_actionable_message(self, ws_module):
        msg = ws_module.user_facing_task_error(ValueError("Unknown question type: xyz"))
        assert "Fragetyp" in msg
        assert msg != ws_module.GENERIC_TASK_ERROR

    def test_unknown_error_falls_back_to_generic_no_leak(self, ws_module):
        # Internals (table names, stack trace fragments) must NOT leak through.
        leaky = ValueError(
            "IntegrityError: duplicate key value violates unique constraint "
            '"question_source_doc_pkey" DETAIL: Key (id)=(42) at /app/secret.py'
        )
        msg = ws_module.user_facing_task_error(leaky)
        assert msg == ws_module.GENERIC_TASK_ERROR
        assert "question_source_doc" not in msg
        assert "secret" not in msg

    def test_none_info_falls_back_to_generic(self, ws_module):
        assert ws_module.user_facing_task_error(None) == ws_module.GENERIC_TASK_ERROR

    def test_maps_via_stable_code_independent_of_message(self, ws_module):
        # TF-358: Mapping must work via the stable .code, even if the raw
        # message does NOT contain the English substring (robustness against
        # rewording/localization). The typed errors live in core.
        from services.rag_errors import NoContextError, UnknownQuestionTypeError

        no_ctx = ws_module.user_facing_task_error(
            NoContextError("völlig andere Formulierung ohne Schlüsselwörter")
        )
        assert "durchsuchbaren Inhalt" in no_ctx

        unknown_type = ws_module.user_facing_task_error(
            UnknownQuestionTypeError("anderer Text")
        )
        assert "Fragetyp" in unknown_type


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
