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


# Modul-Level-Singleton — korrekt für Single-Instance-Deployment
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str) -> None:
        self.active_connections.pop(task_id, None)


manager = ConnectionManager()

PENDING_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 1


async def _authenticate_websocket(websocket: WebSocket, token: str) -> User | None:
    """
    Authentifiziert einen WebSocket-Client via JWT Token.
    Repliziert die Logik von get_current_user() ohne FastAPI Depends.
    """
    db = SessionLocal()
    try:
        payload = AuthService.decode_token(token)
        if not payload:
            await websocket.close(code=1008)
            return None

        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008)
            return None

        token_jti = payload.get("jti")
        if token_jti and AuthService.is_token_revoked(token_jti, db):
            await websocket.close(code=1008)
            return None

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


async def _check_task_ownership(websocket: WebSocket, task_id: str, user: User) -> bool:
    """
    Prüft ob der authentifizierte User der Owner des Tasks ist.
    Lookup via Document.task_id Spalte.
    """
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.task_id == task_id).first()
        if not document:
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
    """
    await manager.connect(task_id, websocket)
    try:
        try:
            handshake = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            token = handshake.get("token", "")
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return
        except Exception:
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
            result = await loop.run_in_executor(None, lambda: _get_task_result(task_id))

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
                pending_seconds = 0

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
        logger.error(f"WebSocket Fehler für Task {task_id}: {e}")
    finally:
        manager.disconnect(task_id)
