"""
WebSocket endpoint for real-time task progress
Streams Celery task progress via WebSocket (pull-based via AsyncResult)
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
from services.rag_errors import GENERIC_TASK_ERROR, user_facing_task_error

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


# Module-level singleton — only for single-instance deployment.
# For horizontal scaling, ConnectionManager must be replaced with Redis Pub/Sub.
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket) -> None:
        existing = self.active_connections.get(task_id)
        if existing:
            try:
                await existing.close(code=1001)
            except (WebSocketDisconnect, RuntimeError):
                pass  # Connection already closed — expected
            except Exception as e:
                logger.warning(
                    f"Fehler beim Schliessen der bestehenden WebSocket-Verbindung "
                    f"für Task {task_id}: {type(e).__name__}: {e}"
                )
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str) -> None:
        self.active_connections.pop(task_id, None)


manager = ConnectionManager()

# 120s is a compromise threshold for both task types this endpoint
# serves:
#   - process_document: countdown=60 s (always < 120 s, retry starts
#     in time).
#   - generate_questions_task: retry_backoff=30, retry_backoff_max=300
#     with retry_jitter=True. First retry typically at ~30-60 s,
#     up to 150 s in the worst case. Past 120 s we hand off to the
#     TF-329 watchdog, which sets the DB status; the client must reconnect.
PENDING_TIMEOUT_SECONDS = 120
# 1s balances responsiveness against Redis load; progress updates are step-based.
POLL_INTERVAL_SECONDS = 1


async def _authenticate_websocket(websocket: WebSocket, token: str) -> User | None:
    """
    Authenticates a WebSocket client via JWT token.
    Replicates the logic of get_current_user() without FastAPI Depends.

    Returns:
        User object on success, None on failure (WebSocket already closed)
    """
    payload = AuthService.decode_token(token)
    if not payload:
        logger.warning("WebSocket Auth: Token decode fehlgeschlagen")
        await websocket.close(code=1008)
        return None

    user_id = payload.get("sub")
    if not user_id:
        logger.warning("WebSocket Auth: Token enthält kein 'sub' Claim")
        await websocket.close(code=1008)
        return None

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        logger.warning(f"WebSocket Auth: Ungültige user_id im Token: {user_id!r}")
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
                .filter(User.id == user_id_int)
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
    Checks whether the authenticated user is the owner of the task.
    Checks Document.task_id (document tasks) and QuestionGenerationJob.task_id
    (question tasks). Unknown task_ids are rejected.
    """
    from models.question_generation_job import QuestionGenerationJob

    def _db_check() -> str:
        """Returns 'ok', 'denied', or 'unknown'. Runs in executor to avoid blocking."""
        db = SessionLocal()
        try:
            from services.audit_service import AuditService

            document = db.query(Document).filter(Document.task_id == task_id).first()
            if document:
                if document.user_id == user.id:
                    return "ok"
                if user.is_superuser:
                    AuditService.log_superuser_bypass(
                        db=db,
                        superuser=user,
                        resource_type="document",
                        resource_id=document.id,
                        action="ws_subscribe",
                        owner_user_id=document.user_id,
                    )
                    return "ok"
                logger.warning(
                    f"Ownership-Verletzung (Dokument): User {user.id} versucht Task "
                    f"{task_id} (Owner: {document.user_id}) zu überwachen"
                )
                return "denied"

            job = (
                db.query(QuestionGenerationJob)
                .filter(QuestionGenerationJob.task_id == task_id)
                .first()
            )
            if job:
                if job.user_id == user.id:
                    return "ok"
                if user.is_superuser:
                    AuditService.log_superuser_bypass(
                        db=db,
                        superuser=user,
                        resource_type="question_generation_job",
                        resource_id=job.id,
                        action="ws_subscribe",
                        owner_user_id=job.user_id,
                    )
                    return "ok"
                logger.warning(
                    f"Ownership-Verletzung (Fragen): User {user.id} versucht Task "
                    f"{task_id} (Owner: {job.user_id}) zu überwachen"
                )
                return "denied"

            # Unknown task_id — reject (not a legitimate case, since the job is created before apply_async)
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
    Blocking Redis call — must be invoked via run_in_executor.
    Reads state, info and result in a single executor call so that
    no blocking I/O happens on the event loop.

    On Redis connection errors, a PENDING-equivalent state is returned
    so the polling loop can keep running (transient Redis outages).
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
        logger.error(
            f"Redis-Fehler beim Abrufen von Task {task_id}: {type(e).__name__}: {e}"
        )
        return {"state": "PENDING", "info": None, "result": None, "_redis_error": True}


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_websocket(websocket: WebSocket, task_id: str) -> None:
    """
    WebSocket endpoint for real-time task progress.

    Protocol:
    1. Client connects
    2. Client sends as first message: {"token": "<jwt>"}
    3. Server validates token + ownership
    4. Server streams TaskStatusMessage JSON until the terminal state
    5. Server closes the connection after SUCCESS/FAILURE/REVOKED
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
        redis_failures = 0
        max_redis_failures = 3
        loop = asyncio.get_running_loop()

        while True:
            task_data = await loop.run_in_executor(
                None, lambda: _get_task_result(task_id)
            )

            if task_data.get("_redis_error"):
                redis_failures += 1
                if redis_failures >= max_redis_failures:
                    msg = TaskStatusMessage(
                        task_id=task_id,
                        status=TaskStatus.FAILURE,
                        progress=0,
                        error="Task-Status kann nicht abgerufen werden (Verbindungsfehler). "
                        "Bitte versuch es später erneut.",
                    )
                    await websocket.send_json(msg.model_dump())
                    await websocket.close()
                    return
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            redis_failures = 0

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
                # An optional user note (e.g. "only X of Y questions created",
                # TF-358) travels along in result.quality_metrics and is read
                # from there by the frontend — no separate message channel needed.
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
                user_message = user_facing_task_error(raw_info)
                # Log the real error fully server-side (with traceback, if
                # available); send the user only the safe, actionable
                # message — no raw internals/PII (TF-358). Explicitly flag
                # unknown error classes (generic fallback) so alerting is
                # possible for new, unmapped errors.
                unmapped = user_message == GENERIC_TASK_ERROR
                logger.error(
                    "Task %s failed (%s): %r",
                    task_id,
                    "unmapped error class" if unmapped else "mapped error",
                    raw_info,
                    exc_info=raw_info if isinstance(raw_info, BaseException) else None,
                )
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus(state),
                    progress=0,
                    error=user_message,
                )
                await websocket.send_json(msg.model_dump())
                await websocket.close()
                return

            elif state in (TaskStatus.STARTED, TaskStatus.RETRY):
                pending_seconds = 0
                message = (
                    "Task gestartet..."
                    if state == TaskStatus.STARTED
                    else "Task wird erneut versucht..."
                )
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus.PROGRESS,
                    progress=info.get("progress", 0) if isinstance(info, dict) else 0,
                    message=message,
                )
                await websocket.send_json(msg.model_dump())

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
