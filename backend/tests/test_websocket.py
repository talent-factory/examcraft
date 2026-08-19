"""Tests für WebSocket Task Progress Endpoint"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect
import importlib
import os


@pytest.fixture
def ws_app():
    """Minimale FastAPI-App mit WebSocket-Router für Tests"""
    import sys

    app = FastAPI()
    ws_path = os.path.join(os.path.dirname(__file__), "..", "api", "v1", "websocket.py")
    spec = importlib.util.spec_from_file_location("ws_module", ws_path)
    ws_module = importlib.util.module_from_spec(spec)
    # Registriere unter dem kanonischen Namen, damit patch("api.v1.websocket.*") greift
    sys.modules["api.v1.websocket"] = ws_module
    spec.loader.exec_module(ws_module)
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
        """Verbindung mit gültigem Token-Handshake wird akzeptiert"""
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
        """Ungültiger Token → WebSocket wird geschlossen"""
        with patch("api.v1.websocket.AuthService") as mock_auth:
            mock_auth.decode_token.return_value = None

            client = TestClient(ws_app)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                    ws.send_json({"token": "invalid-token"})
                    ws.receive_json()

    def test_websocket_revoked_token(self, ws_app, valid_token_payload, mock_user):
        """Revozierter Token → WebSocket wird geschlossen"""
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
        """Task gehört einem anderen User → WebSocket wird geschlossen"""
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
        """PROGRESS-Messages werden korrekt übertragen"""
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
        """Connection wird nach SUCCESS geschlossen"""
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
        """Connection wird nach FAILURE geschlossen"""
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
        """REVOKED ist genauso terminal wie FAILURE — der Client darf nach
        einer REVOKED-Nachricht keine weiteren Updates erhalten. Ohne diesen
        Test würde eine Regression, die REVOKED aus dem Terminal-Tuple
        entfernt (z. B. eine "Vereinheitlichung" mit FAILURE), unbemerkt
        bleiben — der Frontend-Sticky-Terminal-Schutz (TF-328) wäre dann
        wirkungslos, weil das Backend gar keinen REVOKED-Frame mehr sendet.
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
                    # Server muss nach REVOKED schliessen — kein weiterer
                    # Frame (analog zum SUCCESS- und FAILURE-Verhalten).
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
    """Lädt das websocket-Modul (wie ws_app) und gibt es zurück, damit reine
    Hilfsfunktionen wie user_facing_task_error direkt getestet werden können."""
    import sys

    ws_path = os.path.join(os.path.dirname(__file__), "..", "api", "v1", "websocket.py")
    spec = importlib.util.spec_from_file_location("ws_module", ws_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["api.v1.websocket"] = module
    spec.loader.exec_module(module)
    return module


class TestUserFacingError:
    """TF-358: Der echte Task-Fehler wird geloggt, dem User aber eine sichere,
    handlungsleitende Meldung gezeigt — bekannte Fehlerklassen konkret,
    Unbekanntes generisch (kein Info-Leak)."""

    def test_no_context_maps_to_actionable_message(self, ws_module):
        # Genau der Prod-Fehler aus TF-358.
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
        # Interna (Tabellennamen, Stacktrace-Fragmente) dürfen NICHT durchsickern.
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
        # TF-358: Mapping muss über den stabilen .code greifen, auch wenn die
        # Roh-Message den englischen Substring NICHT enthält (Robustheit gegen
        # Umformulierung/Lokalisierung). Die typisierten Fehler leben in core.
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
    """Integrationstest: der FAILURE-Frame trägt die handlungsleitende Meldung
    statt der pauschalen — der Test schlägt ohne den TF-358-Fix fehl."""

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
