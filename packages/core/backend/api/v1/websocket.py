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


# Modul-Level-Singleton — nur für Single-Instance-Deployment.
# Bei horizontaler Skalierung muss ConnectionManager durch Redis Pub/Sub ersetzt werden.
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        existing = self.active_connections.get(task_id)
        if existing:
            try:
                await existing.close(code=1001)
            except Exception:
                pass
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str) -> None:
        self.active_connections.pop(task_id, None)


manager = ConnectionManager()

# 120s > process_document retry countdown (60s), damit der WebSocket
# nicht timeout bevor ein Retry-Versuch beginnt.
PENDING_TIMEOUT_SECONDS = 120
# 1s balanciert Responsivität mit Redis-Last; Progress-Updates sind schritt-basiert.
POLL_INTERVAL_SECONDS = 1


async def _authenticate_websocket(websocket: WebSocket, token: str) -> User | None:
    """
    Authentifiziert einen WebSocket-Client via JWT Token.
    Repliziert die Logik von get_current_user() ohne FastAPI Depends.

    Returns:
        User-Objekt bei Erfolg, None bei Fehler (WebSocket bereits geschlossen)
    """
    payload = AuthService.decode_token(token)
    if not payload:
        await websocket.close(code=1008)
        return None

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return None

    def _db_lookup() -> User | None:
        db = SessionLocal()
        try:
            token_jti = payload.get("jti")
            if token_jti and AuthService.is_token_revoked(token_jti, db):
                return None

            return (
                db.query(User)
                .options(joinedload(User.roles))
                .filter(User.id == int(user_id))
                .first()
            )
        finally:
            db.close()

    try:
        loop = asyncio.get_running_loop()
        user = await loop.run_in_executor(None, _db_lookup)
        if not user:
            await websocket.close(code=1008)
            return None
        return user
    except Exception as e:
        logger.error(
            f"WebSocket Auth: Unerwarteter Fehler: {type(e).__name__}: {e}",
            exc_info=True,
        )
        await websocket.close(code=1011)
        return None


async def _check_task_ownership(websocket: WebSocket, task_id: str, user: User) -> bool:
    """
    Prüft ob der authentifizierte User der Owner des Tasks ist.
    Prüft Document.task_id (Dokument-Tasks) und QuestionGenerationJob.task_id
    (Fragen-Tasks). Unbekannte task_ids werden abgelehnt.
    """
    from models.question_generation_job import QuestionGenerationJob

    def _db_check() -> str:
        """Returns 'ok', 'denied', or 'unknown'. Runs in executor to avoid blocking."""
        db = SessionLocal()
        try:
            document = db.query(Document).filter(Document.task_id == task_id).first()
            if document:
                if document.user_id != user.id:
                    logger.warning(
                        f"Ownership-Verletzung (Dokument): User {user.id} versucht Task "
                        f"{task_id} (Owner: {document.user_id}) zu überwachen"
                    )
                    return "denied"
                return "ok"

            job = (
                db.query(QuestionGenerationJob)
                .filter(QuestionGenerationJob.task_id == task_id)
                .first()
            )
            if job:
                if job.user_id != user.id:
                    logger.warning(
                        f"Ownership-Verletzung (Fragen): User {user.id} versucht Task "
                        f"{task_id} (Owner: {job.user_id}) zu überwachen"
                    )
                    return "denied"
                return "ok"

            # Unbekannte task_id — ablehnen (kein legitimer Fall, da Job vor apply_async erstellt wird)
            logger.warning(
                f"Unbekannte task_id {task_id!r} von User {user.id} abgelehnt"
            )
            return "unknown"
        finally:
            db.close()

    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, _db_check)
        if result != "ok":
            await websocket.close(code=1008)
            return False
        return True
    except Exception as e:
        logger.error(
            f"Ownership-Check Fehler: {type(e).__name__}: {e}",
            exc_info=True,
        )
        await websocket.close(code=1011)
        return False


def _get_task_result(task_id: str) -> dict:
    """
    Blockierender Redis-Aufruf — muss via run_in_executor aufgerufen werden.
    Liest state, info und result in einem einzigen Executor-Aufruf,
    damit kein blocking I/O auf dem Event-Loop stattfindet.

    Bei Redis-Verbindungsfehlern wird ein PENDING-äquivalenter State zurückgegeben,
    damit der Polling-Loop weiterlaufen kann (transiente Redis-Ausfälle).
    """
    try:
        result = AsyncResult(task_id, app=celery_app)
        state = result.state
        return {
            "state": state,
            "info": result.info,
            "result": result.result if state == "SUCCESS" else None,
        }
    except Exception as e:
        logger.warning(
            f"Redis-Fehler beim Abrufen von Task {task_id}: {type(e).__name__}: {e}"
        )
        return {"state": "PENDING", "info": None, "result": None}


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
    """
    await manager.connect(task_id, websocket)
    try:
        try:
            handshake = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            token = handshake.get("token", "")
        except asyncio.TimeoutError:
            logger.warning(f"WebSocket Handshake-Timeout für Task {task_id}")
            await websocket.close(code=1008)
            return
        except Exception as e:
            logger.warning(
                f"WebSocket Handshake-Fehler für Task {task_id}: {type(e).__name__}: {e}"
            )
            await websocket.close(code=1008)
            return

        user = await _authenticate_websocket(websocket, token)
        if user is None:
            return

        if not await _check_task_ownership(websocket, task_id, user):
            return

        pending_seconds = 0
        loop = asyncio.get_running_loop()

        while True:
            task_data = await loop.run_in_executor(
                None, lambda: _get_task_result(task_id)
            )

            state = task_data["state"]
            info = task_data["info"] or {}

            if state == TaskStatus.PROGRESS:
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus.PROGRESS,
                    progress=info.get("progress", 0),
                    message=info.get("message"),
                )
                await websocket.send_json(msg.model_dump())
                pending_seconds = 0

            elif state == TaskStatus.SUCCESS:
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus.SUCCESS,
                    progress=100,
                    result=task_data["result"],
                )
                await websocket.send_json(msg.model_dump())
                await websocket.close()
                return

            elif state in (TaskStatus.FAILURE, TaskStatus.REVOKED):
                raw_info = task_data["info"]
                error_str = str(raw_info) if raw_info else "Unbekannter Fehler"
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus(state),
                    progress=0,
                    error=error_str,
                )
                await websocket.send_json(msg.model_dump())
                await websocket.close()
                return

            else:
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
        logger.error(
            f"WebSocket Fehler für Task {task_id}: {type(e).__name__}: {e}",
            exc_info=True,
        )
        try:
            error_msg = TaskStatusMessage(
                task_id=task_id,
                status=TaskStatus.FAILURE,
                progress=0,
                error="Interner Server-Fehler bei der Fortschritts-Übertragung",
            )
            await websocket.send_json(error_msg.model_dump())
            await websocket.close(code=1011)
        except Exception as cleanup_err:
            logger.warning(
                f"WebSocket Cleanup fehlgeschlagen für Task {task_id}: "
                f"{type(cleanup_err).__name__}: {cleanup_err}"
            )
    finally:
        manager.disconnect(task_id)
