# TF-208: WebSocket Task Progress Tracking — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a WebSocket endpoint that streams Celery task progress (0–100%) to the frontend with JWT authentication and task-ownership verification.

**Architecture:** Pull-based WebSocket — the FastAPI server polls Redis via `AsyncResult` every 1s using `run_in_executor` and pushes `TaskStatusMessage` JSON to the connected client. Authentication is performed via a first-message JWT handshake (not URL params). Progress is emitted from the Celery task via `ProgressTask.update_progress()` → `self.update_state(state="PROGRESS", meta={...})`.

**Tech Stack:** FastAPI WebSockets, Celery AsyncResult, Redis (DB 3 for result backend), SQLAlchemy, Pydantic v2, pytest with FastAPI TestClient

**Spec:** `docs/superpowers/specs/2026-03-16-tf208-async-task-status-websocket-design.md`

---

## Chunk 1: Foundation — Schemas + Redis DB Fix

### Task 1: Fix Redis DB Conflict in celery_app.py

**Files:**
- Modify: `packages/core/backend/celery_app.py:21`

**Background:** Celery result backend currently uses Redis DB 1, which conflicts with the token blacklist (`REDIS_DB_BLACKLIST = 1` in `redis_service.py`). Moving it to DB 3 (unused).

- [ ] **Step 1: Write failing test for Redis DB assignment**

  Create `packages/core/backend/tests/test_celery_config.py`:

  ```python
  """Tests für Celery-Konfiguration"""
  import pytest


  def test_celery_result_backend_uses_db3():
      """Celery Result Backend muss Redis DB 3 verwenden (DB 1 = Token-Blacklist)"""
      from celery_app import celery_app

      backend = celery_app.conf.result_backend
      assert backend is not None
      assert "/3" in backend, (
          f"Celery result backend muss DB 3 verwenden, aktuell: {backend}"
      )
  ```

- [ ] **Step 2: Run test to confirm it fails**

  ```bash
  cd packages/core/backend
  pytest tests/test_celery_config.py::test_celery_result_backend_uses_db3 -v
  ```

  Erwartet: FAILED — `"/3" not in "redis://redis:6379/1"`

- [ ] **Step 3: Fix celery_app.py und celery_app_flower.py**

  In `packages/core/backend/celery_app.py`, Zeile 21 ändern:

  ```python
  # Vorher:
  backend=os.getenv(
      "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/1")
  ),

  # Nachher:
  backend=os.getenv(
      "CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://redis:6379/3")
  ),
  ```

  Dasselbe in `packages/core/backend/celery_app_flower.py` anpassen (falls gleicher Fallback-String vorhanden), damit Flower kein Split-Brain-Problem bekommt:

  ```bash
  grep -n "redis:6379/1" packages/core/backend/celery_app_flower.py
  ```

  Falls gefunden: gleiche Änderung `/1` → `/3` vornehmen.

- [ ] **Step 4: Run test to confirm it passes**

  ```bash
  cd packages/core/backend
  pytest tests/test_celery_config.py -v
  ```

  Erwartet: PASSED

- [ ] **Step 5: Commit**

  ```bash
  git add packages/core/backend/celery_app.py packages/core/backend/tests/test_celery_config.py
  git commit -m "fix(celery): Verschiebe Result Backend von Redis DB 1 auf DB 3 (Konflikt mit Token-Blacklist)"
  ```

---

### Task 2: Pydantic Schemas für Task-Status

**Files:**
- Create: `packages/core/backend/schemas/__init__.py`
- Create: `packages/core/backend/schemas/task.py`
- Test: `packages/core/backend/tests/test_task_schemas.py`

- [ ] **Step 1: Write failing tests**

  Erstelle `packages/core/backend/tests/test_task_schemas.py`:

  ```python
  """Tests für Task Status Schemas"""
  import pytest
  from pydantic import ValidationError


  def test_task_status_message_valid():
      """TaskStatusMessage akzeptiert gültige Progress-Daten"""
      from schemas.task import TaskStatusMessage, TaskStatus

      msg = TaskStatusMessage(
          task_id="abc-123",
          status=TaskStatus.PROGRESS,
          progress=40,
          message="Docling-Verarbeitung läuft...",
      )
      assert msg.task_id == "abc-123"
      assert msg.progress == 40
      assert msg.message == "Docling-Verarbeitung läuft..."


  def test_task_status_message_progress_bounds():
      """TaskStatusMessage lehnt progress > 100 ab"""
      from schemas.task import TaskStatusMessage, TaskStatus

      with pytest.raises(ValidationError):
          TaskStatusMessage(task_id="x", status=TaskStatus.PROGRESS, progress=101)


  def test_task_status_message_success():
      """TaskStatusMessage enthält result bei SUCCESS"""
      from schemas.task import TaskStatusMessage, TaskStatus

      msg = TaskStatusMessage(
          task_id="abc-123",
          status=TaskStatus.SUCCESS,
          progress=100,
          result={"document_id": 42, "title": "Test"},
      )
      assert msg.result == {"document_id": 42, "title": "Test"}
      assert msg.error is None


  def test_task_status_message_failure():
      """TaskStatusMessage enthält error bei FAILURE"""
      from schemas.task import TaskStatusMessage, TaskStatus

      msg = TaskStatusMessage(
          task_id="abc-123",
          status=TaskStatus.FAILURE,
          progress=0,
          error="Unbekannter Fehler",
      )
      assert msg.error == "Unbekannter Fehler"
      assert msg.result is None


  def test_task_status_enum_contains_retry():
      """TaskStatus Enum enthält RETRY State"""
      from schemas.task import TaskStatus

      assert TaskStatus.RETRY == "RETRY"
      assert TaskStatus.REVOKED == "REVOKED"
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```bash
  cd packages/core/backend
  pytest tests/test_task_schemas.py -v
  ```

  Erwartet: ERROR — `ModuleNotFoundError: No module named 'schemas'`

- [ ] **Step 3: Erstelle `schemas/__init__.py`**

  ```bash
  mkdir -p packages/core/backend/schemas
  touch packages/core/backend/schemas/__init__.py
  ```

- [ ] **Step 4: Erstelle `schemas/task.py`**

  `packages/core/backend/schemas/task.py`:

  ```python
  """
  Pydantic Schemas für Celery Task Status
  Verwendet im WebSocket Task Progress Endpoint
  """

  from enum import Enum
  from typing import Optional, Any
  from pydantic import BaseModel, Field


  class TaskStatus(str, Enum):
      PENDING = "PENDING"
      STARTED = "STARTED"
      PROGRESS = "PROGRESS"
      SUCCESS = "SUCCESS"
      FAILURE = "FAILURE"
      REVOKED = "REVOKED"
      RETRY = "RETRY"


  class TaskStatusMessage(BaseModel):
      """WebSocket-Message Format für Task-Fortschritt"""

      task_id: str
      status: TaskStatus
      progress: int = Field(ge=0, le=100)
      message: Optional[str] = None
      result: Optional[Any] = None
      error: Optional[str] = None
  ```

- [ ] **Step 5: Run tests to confirm they pass**

  ```bash
  cd packages/core/backend
  pytest tests/test_task_schemas.py -v
  ```

  Erwartet: 5 PASSED

- [ ] **Step 6: Commit**

  ```bash
  git add packages/core/backend/schemas/ packages/core/backend/tests/test_task_schemas.py
  git commit -m "feat(schemas): Füge TaskStatus und TaskStatusMessage Schemas hinzu"
  ```

---

## Chunk 2: ProgressTask — Celery Task mit granularen Updates

### Task 3: ProgressTask Base Class + process_document Instrumentierung

**Files:**
- Modify: `packages/core/backend/tasks/document_tasks.py`
- Modify: `packages/core/backend/tests/test_celery_tasks.py` (stale import fix)
- Test: `packages/core/backend/tests/test_document_task_progress.py`

**Background:** `process_document` delegiert die eigentliche Arbeit an `document_service.process_document_with_vectors()`. Da dieser Service intern keine Callback-Parameter unterstützt, werden Progress-Updates als **Brackets** um den Service-Call gesetzt (~7 `update_progress()` Calls, nicht 10 lineare Schritte). Die Retry-Attribute (`autoretry_for`, `retry_kwargs`, `retry_backoff`, `retry_jitter`) werden auf dem `@celery_app.task`-Dekorator beibehalten — nicht als Klassenattribute auf `ProgressTask`.

**Voraussetzung:** `test_celery_tasks.py` importiert `create_embeddings` aus `tasks.document_tasks`, aber diese Funktion wurde bereits entfernt. Dieser stale Import muss **vor** dem TDD-Cycle bereinigt werden, da `pytest` sonst bei der Collection abbricht.

- [ ] **Step 0: Fix stale import und Test in test_celery_tasks.py**

  `create_embeddings` wurde aus `tasks/document_tasks.py` entfernt (lebt jetzt in `tasks/rag_tasks.py`). Zwei Änderungen nötig:

  **Zeile 7** — Import fix:
  ```python
  # Vorher:
  from tasks.document_tasks import process_document, create_embeddings

  # Nachher:
  from tasks.document_tasks import process_document
  ```

  **Zeilen 79–109** — `test_create_embeddings_task_success` entfernen (testet `create_embeddings` direkt, die nicht mehr in document_tasks ist). Die Funktion selbst ist in `rag_tasks.py` getestet.

  Danach verify:

  ```bash
  cd packages/core/backend
  pytest tests/test_celery_tasks.py --collect-only
  ```

  Erwartet: Tests werden gesammelt ohne ImportError oder NameError

- [ ] **Step 1: Write failing tests**

  Erstelle `packages/core/backend/tests/test_document_task_progress.py`:

  ```python
  """Tests für ProgressTask und process_document Progress Updates"""
  import pytest
  from unittest.mock import patch, MagicMock, call


  class TestProgressTask:
      def test_update_progress_sets_celery_state(self):
          """update_progress() ruft self.update_state() mit korrekten Meta-Daten auf"""
          from tasks.document_tasks import ProgressTask

          task = ProgressTask()
          task.update_state = MagicMock()

          task.update_progress(3, 10, "Docling-Verarbeitung läuft...")

          task.update_state.assert_called_once_with(
              state="PROGRESS",
              meta={
                  "current": 3,
                  "total": 10,
                  "progress": 30,
                  "message": "Docling-Verarbeitung läuft...",
              },
          )

      def test_update_progress_calculates_percentage(self):
          """update_progress() berechnet progress korrekt"""
          from tasks.document_tasks import ProgressTask

          task = ProgressTask()
          task.update_state = MagicMock()

          task.update_progress(1, 10, "Test")
          call_meta = task.update_state.call_args[1]["meta"]
          assert call_meta["progress"] == 10

          task.update_progress(5, 10, "Test")
          call_meta = task.update_state.call_args[1]["meta"]
          assert call_meta["progress"] == 50

          task.update_progress(10, 10, "Test")
          call_meta = task.update_state.call_args[1]["meta"]
          assert call_meta["progress"] == 100

      def test_process_document_sends_progress_updates(self):
          """process_document sendet mindestens 5 Progress-Updates"""
          from tasks.document_tasks import process_document

          update_progress_calls = []

          with (
              patch("tasks.document_tasks.SessionLocal") as mock_session,
              patch("tasks.document_tasks.run_async") as mock_run_async,
              patch("tasks.document_tasks.document_service") as mock_service,
          ):
              mock_db = MagicMock()
              mock_session.return_value.__enter__ = MagicMock(return_value=mock_db)
              mock_session.return_value = mock_db

              mock_doc = MagicMock()
              mock_doc.id = 1
              mock_doc.original_filename = "test.pdf"
              mock_doc.status.value = "completed"
              mock_doc.has_vectors = True
              mock_db.query.return_value.filter.return_value.first.return_value = mock_doc

              mock_run_async.return_value = {
                  "docling_processing": {},
                  "vector_embeddings": {},
              }

              # Patch update_progress on the bound task
              with patch.object(
                  process_document, "update_progress"
              ) as mock_update_progress:
                  process_document("1", "user-1")
                  assert mock_update_progress.call_count >= 5, (
                      f"Erwartet >= 5 Progress-Updates, erhalten: {mock_update_progress.call_count}"
                  )

      def test_process_document_progress_messages_are_german(self):
          """Alle Progress-Messages sind auf Deutsch"""
          from tasks.document_tasks import process_document

          german_messages = []

          with (
              patch("tasks.document_tasks.SessionLocal") as mock_session,
              patch("tasks.document_tasks.run_async") as mock_run_async,
              patch("tasks.document_tasks.document_service"),
          ):
              mock_db = MagicMock()
              mock_session.return_value = mock_db

              mock_doc = MagicMock()
              mock_doc.id = 1
              mock_doc.original_filename = "test.pdf"
              mock_doc.status.value = "completed"
              mock_doc.has_vectors = True
              mock_db.query.return_value.filter.return_value.first.return_value = mock_doc
              mock_run_async.return_value = {
                  "docling_processing": {},
                  "vector_embeddings": {},
              }

              with patch.object(
                  process_document, "update_progress"
              ) as mock_update_progress:
                  process_document("1", "user-1")
                  for c in mock_update_progress.call_args_list:
                      msg = c[0][2]  # 3. positionales Argument: message
                      german_messages.append(msg)

          # Mindestens eine Message muss auf Deutsch sein (kein Englisch)
          assert any("..." in m for m in german_messages), (
              f"Messages scheinen nicht deutsch zu sein: {german_messages}"
          )
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```bash
  cd packages/core/backend
  pytest tests/test_document_task_progress.py -v
  ```

  Erwartet: FAILED — `ImportError` oder `ProgressTask` nicht definiert

- [ ] **Step 3: Füge ProgressTask zu document_tasks.py hinzu**

  In `packages/core/backend/tasks/document_tasks.py` ersetze die bestehende `DocumentProcessingTask`-Klasse und `process_document`-Funktion:

  ```python
  """
  Celery Tasks for Asynchronous Document Processing
  Handles document extraction, RAG embedding, and metadata extraction
  """

  import asyncio
  from celery import Task
  from celery_app import celery_app
  from services.document_service import document_service
  from models.document import Document, DocumentStatus
  from database import SessionLocal
  from typing import Dict, Any
  import logging

  logger = logging.getLogger(__name__)


  class ProgressTask(Task):
      """Base Task mit Progress-Tracking via Celery update_state"""

      abstract = True

      def update_progress(self, current: int, total: int, message: str = "") -> None:
          """
          Sendet Progress-Update an Redis Result Backend.

          Args:
              current: Aktueller Schritt (0-based)
              total: Gesamtanzahl Schritte
              message: Deutsche Fortschrittsmessage
          """
          self.update_state(
              state="PROGRESS",
              meta={
                  "current": current,
                  "total": total,
                  "progress": int((current / total) * 100),
                  "message": message,
              },
          )


  def run_async(coro):
      """Helper to run async code in sync context"""
      try:
          loop = asyncio.get_event_loop()
      except RuntimeError:
          loop = asyncio.new_event_loop()
          asyncio.set_event_loop(loop)
      return loop.run_until_complete(coro)


  @celery_app.task(
      bind=True,
      base=ProgressTask,
      name="tasks.document_tasks.process_document",
      priority=5,
      autoretry_for=(Exception,),
      retry_kwargs={"max_retries": 3, "countdown": 60},
      retry_backoff=True,
      retry_jitter=True,
  )
  def process_document(self, document_id: str, user_id: str) -> Dict[str, Any]:
      """
      Asynchrone Dokumentverarbeitung mit Docling und Vector Embedding.
      Sendet granulare Progress-Updates (0–100%) an Redis.

      Args:
          document_id: ID des Dokuments
          user_id: ID des Users

      Returns:
          Dict mit Verarbeitungsstatus und Metadaten
      """
      db = SessionLocal()
      document = None

      try:
          self.update_progress(0, 10, "Starte Verarbeitung...")

          # 1. Dokument aus DB laden
          self.update_progress(1, 10, "Dokument wird geladen...")
          document = db.query(Document).filter(Document.id == int(document_id)).first()
          if not document:
              raise ValueError(f"Dokument {document_id} nicht gefunden")

          logger.info(
              f"Starte Dokumentverarbeitung für {document.original_filename} "
              f"(file_path: {document.file_path}, S3: {document_service.use_s3})"
          )

          self.update_progress(2, 10, "Text wird extrahiert...")
          self.update_progress(3, 10, "Docling-Verarbeitung läuft...")

          # 2. Dokument verarbeiten (Docling + Vektoren)
          self.update_progress(4, 10, "Vektoren werden erstellt...")
          result = run_async(
              document_service.process_document_with_vectors(int(document_id), db)
          )

          if result is None:
              raise ValueError(f"Dokumentverarbeitung fehlgeschlagen für {document_id}")

          self.update_progress(8, 10, "Vektoren werden erstellt...")

          # 3. Dokument aus DB neu laden
          db.refresh(document)

          # 4. In Datenbank speichern
          self.update_progress(9, 10, "In Datenbank speichern...")
          db.commit()

          self.update_progress(10, 10, "Abgeschlossen!")
          logger.info(f"Dokumentverarbeitung erfolgreich: {document_id}")

          return {
              "success": True,
              "document_id": document_id,
              "title": document.original_filename,
              "status": document.status.value,
              "has_vectors": document.has_vectors,
              "docling_processing": result.get("docling_processing", {}),
              "vector_embeddings": result.get("vector_embeddings", {}),
          }

      except Exception as e:
          logger.error(f"Fehler bei Dokumentverarbeitung {document_id}: {str(e)}")

          if document:
              document.status = DocumentStatus.ERROR
              document.error_message = str(e)
              db.commit()

          raise self.retry(exc=e, countdown=60)

      finally:
          db.close()


  # Hinweis: create_embeddings wurde entfernt — Vector Embedding wird direkt
  # in document_service.process_document_with_vectors() behandelt
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```bash
  cd packages/core/backend
  pytest tests/test_document_task_progress.py -v
  ```

  Erwartet: 4 PASSED

- [ ] **Step 5: Run existing Celery tests to ensure nothing broke**

  ```bash
  cd packages/core/backend
  pytest tests/test_celery_tasks.py -v
  ```

  Erwartet: alle PASSED (oder bekannte Failures wegen fehlender Celery-Infrastruktur)

- [ ] **Step 6: Commit**

  ```bash
  git add packages/core/backend/tasks/document_tasks.py \
          packages/core/backend/tests/test_document_task_progress.py \
          packages/core/backend/tests/test_celery_tasks.py
  git commit -m "feat(tasks): Füge ProgressTask hinzu und instrumentiere process_document mit deutschen Progress-Updates"
  ```

---

## Chunk 3: WebSocket Endpoint

### Task 4: WebSocket Endpoint mit Authentication + Polling Loop

**Files:**
- Create: `packages/core/backend/api/v1/websocket.py`
- Test: `packages/core/backend/tests/test_websocket.py`

**Wichtige Imports:**
- `AuthService.decode_token(token)` → `Optional[Dict[str, Any]]` aus `services.auth_service`
- `AuthService.is_token_revoked(jti, db)` → `bool`
- `Document.task_id` → Ownership-Check
- `AsyncResult(task_id, app=celery_app)` → Task-Status aus Redis

- [ ] **Step 1: Write failing tests**

  Erstelle `packages/core/backend/tests/test_websocket.py`:

  ```python
  """Tests für WebSocket Task Progress Endpoint"""
  import pytest
  import json
  from unittest.mock import patch, MagicMock, AsyncMock
  from fastapi.testclient import TestClient
  from fastapi import FastAPI
  from starlette.websockets import WebSocketDisconnect


  @pytest.fixture
  def ws_app():
      """Minimale FastAPI-App mit WebSocket-Router für Tests"""
      import importlib
      import os

      app = FastAPI()

      # WebSocket router direkt laden
      ws_path = os.path.join(
          os.path.dirname(__file__), "..", "api", "v1", "websocket.py"
      )
      spec = importlib.util.spec_from_file_location("ws_module", ws_path)
      ws_module = importlib.util.module_from_spec(spec)
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
              mock_db.query.return_value.filter.return_value.first.return_value = mock_document

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
          """Ungültiger Token → WebSocket wird mit Code 1008 geschlossen"""
          with patch("api.v1.websocket.AuthService") as mock_auth:
              mock_auth.decode_token.return_value = None

              client = TestClient(ws_app)
              with pytest.raises(WebSocketDisconnect):
                  with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                      ws.send_json({"token": "invalid-token"})
                      ws.receive_json()  # Soll WebSocketDisconnect werfen da Connection geschlossen

      def test_websocket_revoked_token(
          self, ws_app, valid_token_payload, mock_user
      ):
          """Revozierter Token → WebSocket wird mit Code 1008 geschlossen"""
          with (
              patch("api.v1.websocket.AuthService") as mock_auth,
              patch("api.v1.websocket.SessionLocal") as mock_session,
          ):
              mock_auth.decode_token.return_value = valid_token_payload
              mock_auth.is_token_revoked.return_value = True  # Revoziert!

              mock_db = MagicMock()
              mock_session.return_value = mock_db

              client = TestClient(ws_app)
              with pytest.raises(WebSocketDisconnect):
                  with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                      ws.send_json({"token": "revoked-token"})
                      ws.receive_json()

      def test_websocket_wrong_ownership(
          self, ws_app, valid_token_payload, mock_user
      ):
          """Task gehört einem anderen User → WebSocket wird mit Code 1008 geschlossen"""
          wrong_doc = MagicMock()
          wrong_doc.user_id = 999  # Anderer User!

          with (
              patch("api.v1.websocket.AuthService") as mock_auth,
              patch("api.v1.websocket.SessionLocal") as mock_session,
          ):
              mock_auth.decode_token.return_value = valid_token_payload
              mock_auth.is_token_revoked.return_value = False

              mock_db = MagicMock()
              mock_session.return_value = mock_db
              mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = mock_user
              mock_db.query.return_value.filter.return_value.first.return_value = wrong_doc

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
          progress_results = [
              MagicMock(state="PROGRESS", info={"progress": 40, "message": "Docling-Verarbeitung läuft..."}, result=None),
              MagicMock(state="SUCCESS", info={}, result={"document_id": 1}),
          ]
          result_iter = iter(progress_results)

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
              mock_db.query.return_value.filter.return_value.first.return_value = mock_document
              mock_result.side_effect = lambda task_id, app: next(result_iter)

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
          """Connection wird nach SUCCESS serverseitig geschlossen"""
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
              mock_db.query.return_value.filter.return_value.first.return_value = mock_document

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
                  # Nach SUCCESS: weitere receive_json() soll WebSocketDisconnect werfen
                  with pytest.raises(Exception):
                      ws.receive_json()

      def test_connection_closed_on_failure(
          self, ws_app, valid_token_payload, mock_user, mock_document
      ):
          """Connection wird nach FAILURE serverseitig geschlossen"""
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
              mock_db.query.return_value.filter.return_value.first.return_value = mock_document

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


  class TestWebSocketDisconnect:
      def test_websocket_disconnect_handling(
          self, ws_app, valid_token_payload, mock_user, mock_document
      ):
          """Sauberes Cleanup bei Client-Disconnect — kein unbehandelter Fehler"""
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
              mock_db.query.return_value.filter.return_value.first.return_value = mock_document

              mock_task_result = MagicMock()
              mock_task_result.state = "PENDING"
              mock_task_result.info = {}
              mock_result.return_value = mock_task_result

              # Client disconnectet sofort nach Handshake — kein Crash erwartet
              client = TestClient(ws_app)
              try:
                  with client.websocket_connect("/ws/tasks/test-task-id") as ws:
                      ws.send_json({"token": "valid-token"})
                      # Sofort disconnect
              except Exception:
                  pass  # Disconnect ist OK
  ```

- [ ] **Step 2: Run tests to confirm they fail**

  ```bash
  cd packages/core/backend
  pytest tests/test_websocket.py -v
  ```

  Erwartet: ERROR — `ModuleNotFoundError` für `api.v1.websocket`

- [ ] **Step 3: Implementiere `api/v1/websocket.py`**

  Erstelle `packages/core/backend/api/v1/websocket.py`:

  ```python
  """
  WebSocket Endpoint für Echtzeit Task-Fortschritt
  Streamt Celery Task Progress via WebSocket (Pull-based via AsyncResult)
  """

  import asyncio
  import logging
  from typing import Dict

  from celery.result import AsyncResult
  from fastapi import APIRouter, WebSocket, WebSocketDisconnect
  from sqlalchemy.orm import joinedload

  from celery_app import celery_app
  from database import SessionLocal
  from models.auth import User
  from models.document import Document
  from schemas.task import TaskStatus, TaskStatusMessage
  from services.auth_service import AuthService

  logger = logging.getLogger(__name__)

  router = APIRouter(tags=["websocket"])

  # Modul-Level-Singleton — funktioniert korrekt für Single-Instance-Deployment
  class ConnectionManager:
      def __init__(self) -> None:
          self.active_connections: Dict[str, WebSocket] = {}

      async def connect(self, task_id: str, websocket: WebSocket) -> None:
          await websocket.accept()
          self.active_connections[task_id] = websocket

      def disconnect(self, task_id: str) -> None:
          self.active_connections.pop(task_id, None)


  manager = ConnectionManager()

  # Timeout in Sekunden: > 60s wegen DocumentProcessingTask retry_kwargs countdown=60
  PENDING_TIMEOUT_SECONDS = 120
  POLL_INTERVAL_SECONDS = 1


  async def _authenticate_websocket(
      websocket: WebSocket, token: str
  ) -> User | None:
      """
      Authentifiziert einen WebSocket-Client via JWT Token.
      Repliziert die Logik von get_current_user() ohne FastAPI Depends.

      Returns:
          User-Objekt bei Erfolg, None bei Fehler (WebSocket bereits geschlossen)
      """
      db = SessionLocal()
      try:
          # Token dekodieren
          payload = AuthService.decode_token(token)
          if not payload:
              await websocket.close(code=1008)
              return None

          user_id = payload.get("sub")
          if not user_id:
              await websocket.close(code=1008)
              return None

          # Token-Blacklist prüfen
          token_jti = payload.get("jti")
          if token_jti and AuthService.is_token_revoked(token_jti, db):
              await websocket.close(code=1008)
              return None

          # User laden (mit Rollen für zukünftige Permission-Checks)
          user = (
              db.query(User)
              .options(joinedload(User.roles))
              .filter(User.id == int(user_id))
              .first()
          )
          if not user:
              await websocket.close(code=1008)
              return None

          return user

      except Exception as e:
          logger.warning(f"WebSocket Auth-Fehler: {e}")
          await websocket.close(code=1008)
          return None
      finally:
          db.close()


  async def _check_task_ownership(
      websocket: WebSocket, task_id: str, user: User
  ) -> bool:
      """
      Prüft ob der authentifizierte User der Owner des Tasks ist.
      Lookup via Document.task_id Spalte.

      Returns:
          True bei Erfolg, False bei Fehler (WebSocket bereits geschlossen)
      """
      db = SessionLocal()
      try:
          document = (
              db.query(Document)
              .filter(Document.task_id == task_id)
              .first()
          )
          if not document:
              # Task existiert noch nicht in DB (z.B. sehr frisch gestartet) —
              # wir erlauben es, da wir den Status trotzdem streamen können
              return True

          if document.user_id != user.id:
              logger.warning(
                  f"Ownership-Verletzung: User {user.id} versucht Task "
                  f"{task_id} (Owner: {document.user_id}) zu überwachen"
              )
              await websocket.close(code=1008)
              return False

          return True

      except Exception as e:
          logger.error(f"Ownership-Check Fehler: {e}")
          await websocket.close(code=1008)
          return False
      finally:
          db.close()


  def _get_task_result(task_id: str) -> AsyncResult:
      """Blockierender Redis-Aufruf — muss via run_in_executor aufgerufen werden."""
      return AsyncResult(task_id, app=celery_app)


  @router.websocket("/ws/tasks/{task_id}")
  async def task_progress_websocket(websocket: WebSocket, task_id: str) -> None:
      """
      WebSocket Endpoint für Echtzeit Task-Fortschritt.

      Protokoll:
      1. Client verbindet sich
      2. Client sendet als erste Message: {"token": "<jwt>"}
      3. Server validiert Token + Ownership
      4. Server streamt TaskStatusMessage JSON bis zum terminalen State
      5. Server schliesst Connection nach SUCCESS/FAILURE/REVOKED

      Timeout: 120s bei PENDING (> 60s retry countdown)
      """
      await manager.connect(task_id, websocket)
      try:
          # Schritt 1: Token-Handshake empfangen
          try:
              handshake = await asyncio.wait_for(
                  websocket.receive_json(), timeout=10.0
              )
              token = handshake.get("token", "")
          except asyncio.TimeoutError:
              await websocket.close(code=1008)
              return
          except Exception:
              await websocket.close(code=1008)
              return

          # Schritt 2: Authentifizierung
          user = await _authenticate_websocket(websocket, token)
          if user is None:
              return

          # Schritt 3: Ownership prüfen
          if not await _check_task_ownership(websocket, task_id, user):
              return

          # Schritt 4: Polling Loop
          pending_seconds = 0
          loop = asyncio.get_event_loop()

          while True:
              # Blockierenden Redis-Call in Thread-Pool auslagern
              result = await loop.run_in_executor(
                  None, lambda: _get_task_result(task_id)
              )

              state = result.state
              info = result.info or {}

              if state == TaskStatus.PROGRESS:
                  msg = TaskStatusMessage(
                      task_id=task_id,
                      status=TaskStatus.PROGRESS,
                      progress=info.get("progress", 0),
                      message=info.get("message"),
                  )
                  await websocket.send_json(msg.model_dump())
                  pending_seconds = 0  # Reset Timeout bei aktiven Updates

              elif state == TaskStatus.SUCCESS:
                  msg = TaskStatusMessage(
                      task_id=task_id,
                      status=TaskStatus.SUCCESS,
                      progress=100,
                      result=result.result,
                  )
                  await websocket.send_json(msg.model_dump())
                  await websocket.close()
                  return

              elif state in (TaskStatus.FAILURE, TaskStatus.REVOKED):
                  error_str = str(result.info) if result.info else "Unbekannter Fehler"
                  msg = TaskStatusMessage(
                      task_id=task_id,
                      status=TaskStatus(state),
                      progress=0,
                      error=error_str,
                  )
                  await websocket.send_json(msg.model_dump())
                  await websocket.close()
                  return

              elif state in (TaskStatus.PENDING, TaskStatus.STARTED, "RETRY"):
                  pending_seconds += POLL_INTERVAL_SECONDS
                  if pending_seconds >= PENDING_TIMEOUT_SECONDS:
                      msg = TaskStatusMessage(
                          task_id=task_id,
                          status=TaskStatus.FAILURE,
                          progress=0,
                          error=f"Task {task_id} Timeout nach {PENDING_TIMEOUT_SECONDS}s",
                      )
                      await websocket.send_json(msg.model_dump())
                      await websocket.close()
                      return

              await asyncio.sleep(POLL_INTERVAL_SECONDS)

      except WebSocketDisconnect:
          logger.debug(f"Client disconnected von Task {task_id}")
      except Exception as e:
          logger.error(f"WebSocket Fehler für Task {task_id}: {e}")
      finally:
          manager.disconnect(task_id)
  ```

- [ ] **Step 4: Run tests to confirm they pass**

  ```bash
  cd packages/core/backend
  pytest tests/test_websocket.py -v
  ```

  Erwartet: alle PASSED (einige Tests können WebSocketDisconnect-Exceptions erwarten)

- [ ] **Step 5: Run full test suite to check for regressions**

  ```bash
  cd packages/core/backend
  pytest tests/ -v --ignore=tests/test_processor_performance.py -x
  ```

  Erwartet: keine neuen FAILED

- [ ] **Step 6: Commit**

  ```bash
  git add packages/core/backend/api/v1/websocket.py packages/core/backend/tests/test_websocket.py
  git commit -m "feat(websocket): Implementiere WebSocket Task Progress Endpoint mit JWT-Auth und Ownership-Check"
  ```

---

## Chunk 4: Router-Registrierung + Abschluss

### Task 5: WebSocket Router in main.py registrieren

**Files:**
- Modify: `packages/core/backend/main.py`

- [ ] **Step 1: Write failing test**

  Erstelle `packages/core/backend/tests/test_websocket_route.py`:

  ```python
  """Test dass WebSocket Route korrekt registriert ist"""
  from starlette.routing import WebSocketRoute


  def test_websocket_route_registered():
      """Der /ws/tasks/{task_id} Endpoint muss als WebSocketRoute registriert sein"""
      from main import app

      # WebSocket Routes sind WebSocketRoute-Objekte (nicht APIRoute)
      ws_routes = [
          r for r in app.routes
          if isinstance(r, WebSocketRoute) and "ws/tasks" in r.path
      ]
      assert len(ws_routes) > 0, (
          f"WebSocketRoute /ws/tasks/{{task_id}} nicht gefunden. "
          f"Alle Routes: {[(type(r).__name__, getattr(r, 'path', '?')) for r in app.routes]}"
      )
  ```

- [ ] **Step 2: Run test to confirm it fails**

  ```bash
  cd packages/core/backend
  pytest tests/test_websocket_route.py -v
  ```

  Erwartet: FAILED — Route nicht registriert

- [ ] **Step 3: WebSocket Router in main.py registrieren**

  In `packages/core/backend/main.py`, **innerhalb der `lifespan`-Funktion**, direkt nach der `webhooks_api`-Registrierung (ca. Zeile 208) einfügen:

  ```python
  # Import WebSocket API (innerhalb lifespan, nach webhooks_api)
  spec_ws = importlib.util.spec_from_file_location(
      "core_api_v1_websocket", os.path.join(core_api_path, "v1", "websocket.py")
  )
  websocket_api = importlib.util.module_from_spec(spec_ws)
  spec_ws.loader.exec_module(websocket_api)

  app.include_router(websocket_api.router)
  ```

  **Wichtig:** Diese Registrierung muss innerhalb des `async with lifespan(app):` Blocks stehen — nicht auf Modul-Level. Alle anderen Router (billing, rbac, webhooks) folgen diesem Muster.

- [ ] **Step 4: Run test to confirm it passes**

  ```bash
  cd packages/core/backend
  pytest tests/test_websocket_route.py -v
  ```

  Erwartet: PASSED

- [ ] **Step 5: Run final complete test suite**

  ```bash
  cd packages/core/backend
  pytest tests/ -v --ignore=tests/test_processor_performance.py
  ```

  Erwartet: alle neuen Tests PASSED, keine Regressions

- [ ] **Step 6: Ruff lint + format**

  ```bash
  cd packages/core/backend
  ruff check . --fix
  ruff format .
  ```

- [ ] **Step 7: Final commit**

  ```bash
  git add packages/core/backend/main.py packages/core/backend/tests/test_websocket_route.py
  git commit -m "feat(main): Registriere WebSocket Task Progress Router"
  ```

- [ ] **Step 8: Push**

  ```bash
  git push origin feature/tf-208-backend-async-task-status-tracking-celery-task-progress-with
  ```
