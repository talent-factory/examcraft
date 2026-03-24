"""
Tests für WebSocket Ownership-Check mit QuestionGenerationJob.
Deckt die 3 neuen Pfade ab: Job+richtiger User, Job+falscher User, unbekannte task_id.
Die bestehenden tests/test_websocket.py decken Document-Ownership (Pfade 1+2) ab.
"""

import importlib
import importlib.util
import os
import sys
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from starlette.testclient import TestClient
from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect


@pytest.fixture
def ws_module():
    """Lädt das websocket Modul frisch für jeden Test"""
    ws_path = os.path.join(os.path.dirname(__file__), "..", "api", "v1", "websocket.py")
    spec = importlib.util.spec_from_file_location("api.v1.websocket_test", ws_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["api.v1.websocket_test"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def ws_app(ws_module):
    app = FastAPI()
    app.include_router(ws_module.router)
    return app


class TestQuestionJobOwnership:
    def test_question_task_owner_can_connect(self, ws_app):
        """Owner eines QuestionGenerationJob kann WebSocket öffnen"""
        mock_user = MagicMock()
        mock_user.id = 42

        mock_job = MagicMock()
        mock_job.user_id = 42  # Same as current_user.id

        mock_task_data = {"state": "PENDING", "info": None, "result": None}

        with (
            patch(
                "api.v1.websocket_test._authenticate_websocket",
                new=AsyncMock(return_value=mock_user),
            ),
            patch("api.v1.websocket_test.SessionLocal") as mock_session_cls,
            patch(
                "api.v1.websocket_test._get_task_result", return_value=mock_task_data
            ),
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                None,  # Document lookup: not found
                mock_job,  # QuestionGenerationJob lookup: found
            ]
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with client.websocket_connect("/ws/tasks/test-task-999") as ws:
                ws.send_json({"token": "valid-token"})
                # Connection should stay open (PENDING, no timeout yet)

    def test_wrong_user_denied_for_question_task(self, ws_app):
        """Anderer User wird abgelehnt (Close 1008) für QuestionGenerationJob"""
        mock_user = MagicMock()
        mock_user.id = 99  # Different from job owner

        mock_job = MagicMock()
        mock_job.user_id = 42  # Job belongs to user 42

        with (
            patch(
                "api.v1.websocket_test._authenticate_websocket",
                new=AsyncMock(return_value=mock_user),
            ),
            patch("api.v1.websocket_test.SessionLocal") as mock_session_cls,
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.side_effect = [
                None,  # Document lookup: not found
                mock_job,  # QuestionGenerationJob lookup: found, wrong user
            ]
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/test-task-999") as ws:
                    ws.send_json({"token": "valid-token"})
                    ws.receive_json()

    def test_unknown_task_id_denied(self, ws_app):
        """Unbekannte task_id wird abgelehnt (Close 1008)"""
        mock_user = MagicMock()
        mock_user.id = 42

        with (
            patch(
                "api.v1.websocket_test._authenticate_websocket",
                new=AsyncMock(return_value=mock_user),
            ),
            patch("api.v1.websocket_test.SessionLocal") as mock_session_cls,
        ):
            mock_db = MagicMock()
            mock_db.query.return_value.filter.return_value.first.return_value = (
                None  # Nothing found
            )
            mock_session_cls.return_value = mock_db

            client = TestClient(ws_app, raise_server_exceptions=False)
            with pytest.raises(WebSocketDisconnect):
                with client.websocket_connect("/ws/tasks/unknown-task-xyz") as ws:
                    ws.send_json({"token": "valid-token"})
                    ws.receive_json()
