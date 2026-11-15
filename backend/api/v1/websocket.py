"""
WebSocket endpoint for real-time task progress
Streams Celery task progress via WebSocket (pull-based via
services.generation_job_state.read_state)
"""

import asyncio
import logging
import os
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import joinedload

from database import SessionLocal
from models.auth import User, UserStatus
from models.document import Document
from schemas.task import TaskStatus, TaskStatusMessage
from services import session_service
from services.generation_job_state import CeleryUnknown, Progress, read_state
from services.rag_errors import (
    TASK_PENDING_TIMEOUT,
    TASK_STATUS_UNAVAILABLE,
    TASK_STREAM_ERROR,
)
from services.translation_service import DEFAULT_LOCALE, t

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


def _allowed_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


async def _authenticate_websocket(websocket: WebSocket) -> User | None:
    """
    Authenticates a WebSocket client via the session cookie (EXAMCRAFT-125).

    The browser sends the httpOnly ``session_id`` cookie with the handshake
    (same site). Replicates the logic of get_current_user() without FastAPI
    Depends.

    Returns:
        User object on success, None on failure (WebSocket already closed)
    """
    # Cross-site WebSocket hijacking: browsers always send Origin, and a
    # SameSite=Lax cookie is no protection on every browser. Same list as CORS.
    origin = websocket.headers.get("origin")
    if origin is not None and "*" not in _allowed_origins():
        if origin.rstrip("/") not in _allowed_origins():
            logger.warning("WebSocket Auth: Origin %r nicht erlaubt", origin)
            await websocket.close(code=1008)
            return None

    session_token = websocket.cookies.get(session_service.SESSION_COOKIE_NAME)
    impersonation_token = websocket.cookies.get(
        session_service.IMPERSONATION_COOKIE_NAME
    )
    if not session_token:
        logger.warning("WebSocket Auth: kein Session-Cookie")
        await websocket.close(code=1008)
        return None

    def _db_lookup() -> User | None:
        db = SessionLocal()
        try:
            auth_session = session_service.resolve_effective_session(
                db, session_token, impersonation_token
            )
            if auth_session is None:
                return None

            user = (
                db.query(User)
                .options(joinedload(User.roles))
                .filter(User.id == auth_session.user_id)
                .first()
            )
            # Same rule as get_current_user: only an impersonation may act as a
            # non-active user (support use case).
            if (
                user is not None
                and auth_session.impersonator_id is None
                and user.status != UserStatus.ACTIVE.value
            ):
                return None
            return user
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


async def _send_success(websocket: WebSocket, task_id: str, result: object) -> None:
    """Send SUCCESS with the task's result and close the socket.

    An optional user note (e.g. "only X of Y questions created", TF-358)
    travels along in ``result.quality_metrics`` and is read from there by the
    frontend, so no separate message channel is needed.
    """
    msg = TaskStatusMessage(
        task_id=task_id,
        status=TaskStatus.SUCCESS,
        progress=100,
        result=result,
    )
    await websocket.send_json(msg.model_dump())
    await websocket.close()


@router.websocket("/ws/tasks/{task_id}")
async def task_progress_websocket(websocket: WebSocket, task_id: str) -> None:
    """
    WebSocket endpoint for real-time task progress.

    Protocol:
    1. Client connects
    2. Client sends a first message (content ignored; authentication uses
       the httpOnly session cookie of the handshake)
    3. Server validates the session + ownership
    4. Server streams TaskStatusMessage JSON until the terminal state
    5. Server closes the connection after SUCCESS/FAILURE/REVOKED
    """
    await manager.connect(task_id, websocket)
    try:
        try:
            await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
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

        user = await _authenticate_websocket(websocket)
        if user is None:
            return

        if not await _check_task_ownership(websocket, task_id, user):
            return

        pending_seconds = 0
        redis_failures = 0
        max_redis_failures = 3
        loop = asyncio.get_running_loop()
        consult_db = False

        while True:
            state = await loop.run_in_executor(
                None, lambda: read_state(task_id, consult_db=consult_db)
            )

            if isinstance(state.celery, CeleryUnknown):
                cause = state.celery.cause
                logger.error(
                    f"Redis-Fehler beim Abrufen von Task {task_id}: "
                    f"{type(cause).__name__}: {cause!r}",
                    exc_info=cause,
                )
                redis_failures += 1
                if redis_failures >= max_redis_failures:
                    msg = TaskStatusMessage(
                        task_id=task_id,
                        status=TaskStatus.FAILURE,
                        progress=0,
                        error=t(TASK_STATUS_UNAVAILABLE, DEFAULT_LOCALE),
                        error_code=TASK_STATUS_UNAVAILABLE,
                    )
                    await websocket.send_json(msg.model_dump())
                    await websocket.close()
                    return
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                continue
            redis_failures = 0

            # TF-964: SUCCESS in the DB wins over any other Celery state (FAILURE/
            # REVOKED, or an expired entry that reads PENDING).
            if state.db_overrode_celery:
                await _send_success(websocket, task_id, state.result)
                return

            celery_status = state.celery_status

            if celery_status == TaskStatus.PROGRESS:
                progress = state.progress or Progress(0, None, None, None)
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus.PROGRESS,
                    progress=progress.percent,
                    message=progress.message,
                    message_code=progress.code,
                    message_params=progress.params,
                )
                await websocket.send_json(msg.model_dump())
                pending_seconds = 0
                consult_db = False

            elif celery_status == TaskStatus.SUCCESS:
                await _send_success(websocket, task_id, state.result)
                return

            elif celery_status in (TaskStatus.FAILURE, TaskStatus.REVOKED):
                # The real error was logged server-side by read_state; the
                # user only gets the safe, actionable message (TF-358).
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus(celery_status),
                    progress=0,
                    error=state.error.message,
                    error_code=state.error.code,
                )
                await websocket.send_json(msg.model_dump())
                await websocket.close()
                return

            elif celery_status in (TaskStatus.STARTED, TaskStatus.RETRY):
                pending_seconds = 0
                consult_db = False
                # TF-736: a code instead of a German text, like PROGRESS above.
                progress = state.progress
                msg = TaskStatusMessage(
                    task_id=task_id,
                    status=TaskStatus.PROGRESS,
                    progress=progress.percent,
                    message_code=progress.code,
                    message_params=progress.params,
                )
                await websocket.send_json(msg.model_dump())

            else:
                pending_seconds += POLL_INTERVAL_SECONDS
                if pending_seconds >= PENDING_TIMEOUT_SECONDS and not consult_db:
                    # TF-964: an expired Celery entry reads as PENDING; a
                    # job that finished in the DB is not a timeout. Ask the
                    # DB only now (not on every PENDING tick) and re-run the
                    # whole evaluation above, so a Celery state that changed
                    # meanwhile is handled like any other tick.
                    consult_db = True
                    continue
                if pending_seconds >= PENDING_TIMEOUT_SECONDS:
                    # A task that never starts points at a stuck broker or
                    # worker — log it with the task id so operations see it.
                    logger.error(
                        "Task %s still PENDING after %ss, reporting timeout to client",
                        task_id,
                        PENDING_TIMEOUT_SECONDS,
                    )
                    # Keep the task id out of user-facing text: it is an
                    # internal detail the user can do nothing with.
                    timeout_params = {"seconds": PENDING_TIMEOUT_SECONDS}
                    msg = TaskStatusMessage(
                        task_id=task_id,
                        status=TaskStatus.FAILURE,
                        progress=0,
                        error=t(TASK_PENDING_TIMEOUT, DEFAULT_LOCALE, **timeout_params),
                        error_code=TASK_PENDING_TIMEOUT,
                        error_params=timeout_params,
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
                error=t(TASK_STREAM_ERROR, DEFAULT_LOCALE),
                error_code=TASK_STREAM_ERROR,
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
