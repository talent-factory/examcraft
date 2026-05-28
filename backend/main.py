"""
ExamCraft AI - FastAPI Backend
KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
"""

import asyncio

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from middleware.rate_limit import RateLimitMiddleware
from database import get_db
from models.auth import User
from utils.auth_utils import get_current_active_user

# Setup logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Sentry (must be done before FastAPI app creation)
from config.sentry import init_sentry  # noqa: E402

init_sentry()

# Initialize Celery App (for async task processing)
try:
    from celery_app import celery_app  # noqa: F401

    logger.info("✅ Celery app initialized for async document processing")
except Exception as e:
    logger.warning(f"⚠️  Celery initialization warning: {str(e)}")

# Lazy-loaded services (to reduce memory at startup)
_claude_service = None

# Strong references to fire-and-forget background tasks.
# Without this, asyncio.create_task() only holds a weak reference to the task,
# which may be garbage-collected mid-run (CPython gotcha; see stdlib asyncio docs).
_background_tasks: set[asyncio.Task] = set()


def _log_task_exception(task: asyncio.Task) -> None:
    """Log unhandled exceptions from fire-and-forget tasks.

    Handles the three failure modes of bare `lambda t: t.exception() and logger.error(...)`:
    - `task.cancelled()` must be checked first; `task.exception()` raises
      `CancelledError` on cancelled tasks instead of returning it.
    - `CancelledError` is `BaseException` (not `Exception`), so the inner
      `try/except Exception` inside the task body does not catch it.
    - Without proper exception retrieval, asyncio emits "Task exception was
      never retrieved" warnings to stderr, bypassing our logger and Sentry.
    """
    if task.cancelled():
        logger.warning("Background task cancelled (likely app shutdown)")
        return
    exc = task.exception()
    if exc is not None:
        logger.error("Background task raised: %s", exc, exc_info=exc)


def get_claude_service():
    """Lazy-load Claude service only when needed"""
    global _claude_service
    if _claude_service is None:
        from services.claude_service import ClaudeService

        _claude_service = ClaudeService()
    return _claude_service


# Lifespan event handler (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown events.
    Replaces deprecated @app.on_event("startup") and @app.on_event("shutdown")
    """
    # Detect deployment mode
    deployment_mode = os.getenv("DEPLOYMENT_MODE", "core")
    is_full_deployment = deployment_mode == "full"

    print("\n" + "=" * 60)
    print(f"🚀 ExamCraft AI - Starting ({deployment_mode.upper()} mode)")
    print("=" * 60 + "\n")

    # Startup: Initialize database tables
    from database import create_tables, SessionLocal

    create_tables()

    # Startup: Seed default roles
    try:
        from utils.seed_roles import seed_default_roles

        db = SessionLocal()
        try:
            created, updated = seed_default_roles(db)
            print(f"✅ Roles seeded: {created} created, {updated} updated")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error seeding roles: {str(e)}")

    # Startup: Seed RBAC data (Features, Tiers, Quotas)
    try:
        from scripts.seed_rbac_data import main as seed_rbac_data

        seed_rbac_data()
        print("✅ RBAC data seeded successfully")
    except Exception as e:
        print(f"❌ Error seeding RBAC data: {str(e)}")

    # Startup: Seed default prompts (Premium/Enterprise feature)
    if is_full_deployment:
        try:
            from utils.seed_prompts import seed_prompts

            seed_prompts()
            print("✅ Premium prompts seeded")
        except ImportError:
            print("⚠️  Premium package not available, skipping prompt seeding")
        except Exception as e:
            print(f"❌ Error seeding prompts: {str(e)}")

        # Startup: Auto-index documentation into Qdrant (Full Replace)
        # Runs asynchronously as a fire-and-forget task so FastAPI can serve
        # /health immediately. Synchronous indexing of the full docs corpus
        # plus cold-start vector-backend initialisation (model download or
        # remote warm-up) would exceed Fly.io's health-check grace period
        # (see fly.toml: [checks.health].grace_period).
        async def _index_docs_background():
            try:
                from services.vector_service_factory import vector_service

                if not (
                    hasattr(vector_service, "client")
                    and vector_service.client is not None
                ):
                    # In full deployment mode this is an error state:
                    # the operator expected Qdrant to be reachable.
                    logger.error(
                        "Qdrant client is None in full deployment mode — "
                        "indexing skipped. Check QDRANT_URL and factory init logs."
                    )
                    return

                from services.docs_indexer_service import (
                    DocsIndexerService,
                    IndexingInProgressError,
                )

                db = SessionLocal()
                try:
                    service = DocsIndexerService(db)
                    result = await service.run_index(full_scan=True)
                    print(f"✅ Docs indexing completed: {result['indexed']} files")
                except IndexingInProgressError:
                    # Only realistic on overlapping container rollovers; next
                    # startup or admin call will catch up.
                    logger.info(
                        "Docs indexing lock held by another run; skipping startup indexing."
                    )
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Docs indexing failed: {e}", exc_info=True)

        docs_index_task = asyncio.create_task(_index_docs_background())
        # Keep a strong reference (GC safety) and remove it when done.
        _background_tasks.add(docs_index_task)
        docs_index_task.add_done_callback(_background_tasks.discard)
        # Safety net for exceptions that escape the inner try/except
        # (primarily CancelledError during shutdown, plus any import-time
        # errors above the try block). This is not duplication of the inner
        # handler — it catches a strictly disjoint set of failure modes.
        docs_index_task.add_done_callback(_log_task_exception)
        print("🔄 Docs indexing started in background")
    else:
        print("ℹ️  Running in Core mode - Premium features disabled")

    # Startup: Initialize i18n translations
    from services.translation_service import init_translations

    init_translations()
    print("✅ i18n translations initialized")

    # Startup: Seed help context hints
    try:
        from utils.seed_help_hints import seed_help_hints

        db = SessionLocal()
        try:
            created = seed_help_hints(db)
            print(f"✅ Help hints seeded: {created} created")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error seeding help hints: {str(e)}")

    # Premium/Enterprise Features: Replace Core placeholders BEFORE loading routers
    if is_full_deployment:
        print("\n🌟 Loading Premium/Enterprise Features...")

        # Premium: RAG Service (replace Core placeholder with Premium implementation)
        # IMPORTANT: This must happen BEFORE loading API routers that use rag_service
        try:
            from premium.services.rag_service import RAGService
            import services.rag_service as core_rag_module

            # Replace Core RAG service singleton with Premium implementation
            core_rag_module.rag_service = RAGService()
            print("✅ Premium RAG Service loaded")
            logger.info("✅ Premium RAG Service loaded and replaced Core placeholder")
        except ImportError as e:
            print(f"⚠️  Premium RAG Service not available: {e}")
            logger.warning(f"Premium RAG Service not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium RAG Service: {e}")
            logger.error(f"Error loading Premium RAG Service: {e}", exc_info=True)

    # Startup: Load API routers (Core Package)
    # Premium features (vector_search, chat, prompts) are available in Premium package
    # Import from core.api explicitly to avoid conflicts with premium.api
    import importlib
    import sys

    # Get the core backend path
    core_api_path = os.path.join(os.path.dirname(__file__), "api")

    # Import core API modules directly
    spec_documents = importlib.util.spec_from_file_location(
        "core_api_documents", os.path.join(core_api_path, "documents.py")
    )
    documents = importlib.util.module_from_spec(spec_documents)
    spec_documents.loader.exec_module(documents)

    spec_rag = importlib.util.spec_from_file_location(
        "core_api_rag_exams", os.path.join(core_api_path, "rag_exams.py")
    )
    rag_exams = importlib.util.module_from_spec(spec_rag)
    spec_rag.loader.exec_module(rag_exams)

    # TF-320 hotfix: load tags BEFORE question_review and exams because both
    # do ``from api.tags import TagOut``. Register as "api.tags" (same pattern
    # as api.activity below) so the absolute import resolves through
    # sys.modules — the importlib.spec_from_file_location loader machinery
    # breaks the bare filesystem-based package lookup that would otherwise
    # find /app/api/tags.py via sys.path.
    spec_tags = importlib.util.spec_from_file_location(
        "api.tags", os.path.join(core_api_path, "tags.py")
    )
    tags_api = importlib.util.module_from_spec(spec_tags)
    sys.modules["api.tags"] = tags_api
    spec_tags.loader.exec_module(tags_api)

    spec_qr = importlib.util.spec_from_file_location(
        "core_api_question_review", os.path.join(core_api_path, "question_review.py")
    )
    question_review = importlib.util.module_from_spec(spec_qr)
    spec_qr.loader.exec_module(question_review)

    spec_exams = importlib.util.spec_from_file_location(
        "core_api_exams", os.path.join(core_api_path, "exams.py")
    )
    exams_api = importlib.util.module_from_spec(spec_exams)
    spec_exams.loader.exec_module(exams_api)

    spec_submissions = importlib.util.spec_from_file_location(
        "core_api_submissions", os.path.join(core_api_path, "submissions.py")
    )
    submissions_api = importlib.util.module_from_spec(spec_submissions)
    spec_submissions.loader.exec_module(submissions_api)

    # TF-336: Klassen-CRUD + Mitglieder.
    spec_student_classes = importlib.util.spec_from_file_location(
        "core_api_student_classes",
        os.path.join(core_api_path, "student_classes.py"),
    )
    student_classes_api = importlib.util.module_from_spec(spec_student_classes)
    spec_student_classes.loader.exec_module(student_classes_api)

    # TF-336: Studi-Verlauf-Endpoints.
    spec_students = importlib.util.spec_from_file_location(
        "core_api_students",
        os.path.join(core_api_path, "students.py"),
    )
    students_api = importlib.util.module_from_spec(spec_students)
    spec_students.loader.exec_module(students_api)

    # TF-336: Moodle-Connections (Token-verschlüsselt).
    spec_moodle_connections = importlib.util.spec_from_file_location(
        "core_api_moodle_connections",
        os.path.join(core_api_path, "moodle_connections.py"),
    )
    moodle_connections_api = importlib.util.module_from_spec(spec_moodle_connections)
    spec_moodle_connections.loader.exec_module(moodle_connections_api)

    # TF-336: Question-ID-Round-Trip (Export → Sync → API-Re-Import).
    spec_moodle_roundtrip = importlib.util.spec_from_file_location(
        "core_api_moodle_roundtrip",
        os.path.join(core_api_path, "moodle_roundtrip.py"),
    )
    moodle_roundtrip_api = importlib.util.module_from_spec(spec_moodle_roundtrip)
    spec_moodle_roundtrip.loader.exec_module(moodle_roundtrip_api)

    spec_grades = importlib.util.spec_from_file_location(
        "core_api_grades", os.path.join(core_api_path, "grades.py")
    )
    grades_api = importlib.util.module_from_spec(spec_grades)
    spec_grades.loader.exec_module(grades_api)

    spec_grading_schemes = importlib.util.spec_from_file_location(
        "core_api_grading_schemes",
        os.path.join(core_api_path, "grading_schemes.py"),
    )
    grading_schemes_api = importlib.util.module_from_spec(spec_grading_schemes)
    spec_grading_schemes.loader.exec_module(grading_schemes_api)

    spec_stats = importlib.util.spec_from_file_location(
        "core_api_stats", os.path.join(core_api_path, "stats.py")
    )
    stats_api = importlib.util.module_from_spec(spec_stats)
    spec_stats.loader.exec_module(stats_api)

    spec_grade_export = importlib.util.spec_from_file_location(
        "core_api_grade_export",
        os.path.join(core_api_path, "grade_export.py"),
    )
    grade_export_api = importlib.util.module_from_spec(spec_grade_export)
    spec_grade_export.loader.exec_module(grade_export_api)

    # TF-337: paginated activity endpoint (own / institution scope).
    # Loaded BEFORE dashboard because dashboard.py imports ActivityType from it.
    # Registered as "api.activity" so the absolute import in dashboard.py resolves.
    spec_activity = importlib.util.spec_from_file_location(
        "api.activity", os.path.join(core_api_path, "activity.py")
    )
    activity_api = importlib.util.module_from_spec(spec_activity)
    sys.modules["api.activity"] = activity_api
    spec_activity.loader.exec_module(activity_api)

    spec_dashboard = importlib.util.spec_from_file_location(
        "core_api_dashboard", os.path.join(core_api_path, "dashboard.py")
    )
    dashboard_api = importlib.util.module_from_spec(spec_dashboard)
    spec_dashboard.loader.exec_module(dashboard_api)

    spec_auth = importlib.util.spec_from_file_location(
        "core_api_auth", os.path.join(core_api_path, "auth.py")
    )
    auth = importlib.util.module_from_spec(spec_auth)
    spec_auth.loader.exec_module(auth)

    spec_admin = importlib.util.spec_from_file_location(
        "core_api_admin", os.path.join(core_api_path, "admin.py")
    )
    admin = importlib.util.module_from_spec(spec_admin)
    spec_admin.loader.exec_module(admin)

    spec_gdpr = importlib.util.spec_from_file_location(
        "core_api_gdpr", os.path.join(core_api_path, "gdpr.py")
    )
    gdpr = importlib.util.module_from_spec(spec_gdpr)
    spec_gdpr.loader.exec_module(gdpr)

    spec_sentry = importlib.util.spec_from_file_location(
        "core_api_sentry_test", os.path.join(core_api_path, "sentry_test.py")
    )
    sentry_test = importlib.util.module_from_spec(spec_sentry)
    spec_sentry.loader.exec_module(sentry_test)

    # Import RBAC API
    spec_rbac = importlib.util.spec_from_file_location(
        "core_api_v1_rbac", os.path.join(core_api_path, "v1", "rbac.py")
    )
    rbac_api = importlib.util.module_from_spec(spec_rbac)
    spec_rbac.loader.exec_module(rbac_api)

    # Import Billing API
    spec_billing = importlib.util.spec_from_file_location(
        "core_api_v1_billing", os.path.join(core_api_path, "v1", "billing.py")
    )
    billing_api = importlib.util.module_from_spec(spec_billing)
    spec_billing.loader.exec_module(billing_api)

    # Import Webhooks API
    spec_webhooks = importlib.util.spec_from_file_location(
        "core_api_v1_webhooks", os.path.join(core_api_path, "v1", "webhooks.py")
    )
    webhooks_api = importlib.util.module_from_spec(spec_webhooks)
    spec_webhooks.loader.exec_module(webhooks_api)

    # Import WebSocket API (for task progress streaming)
    spec_ws = importlib.util.spec_from_file_location(
        "core_api_v1_websocket", os.path.join(core_api_path, "v1", "websocket.py")
    )
    websocket_api = importlib.util.module_from_spec(spec_ws)
    spec_ws.loader.exec_module(websocket_api)

    # Import Help API (Smart Help Widget — TF-308)
    spec_help = importlib.util.spec_from_file_location(
        "core_api_v1_help", os.path.join(core_api_path, "v1", "help.py")
    )
    help_api = importlib.util.module_from_spec(spec_help)
    spec_help.loader.exec_module(help_api)

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(gdpr.router)
    app.include_router(documents.router)
    app.include_router(rag_exams.router)
    app.include_router(rbac_api.router)
    app.include_router(question_review.router)
    app.include_router(tags_api.router)
    app.include_router(exams_api.router)
    app.include_router(submissions_api.router)
    app.include_router(submissions_api.exams_alias_router)
    app.include_router(student_classes_api.router)
    app.include_router(students_api.router)
    app.include_router(moodle_connections_api.router)
    app.include_router(moodle_roundtrip_api.router)
    app.include_router(grades_api.router_grades)
    app.include_router(grades_api.router_exams_review_queue)
    app.include_router(grading_schemes_api.router)
    app.include_router(stats_api.router_exam_stats)
    app.include_router(stats_api.router_submission_stats)
    app.include_router(grade_export_api.router)
    app.include_router(dashboard_api.router)
    app.include_router(activity_api.router)
    app.include_router(billing_api.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(
        webhooks_api.router, prefix="/api/v1/webhooks", tags=["webhooks"]
    )
    app.include_router(websocket_api.router)
    app.include_router(help_api.router)

    # Email Webhooks (Resend)
    try:
        from webhooks import resend_router

        app.include_router(resend_router)
        print("✅ Email webhooks loaded (Resend)")
    except ImportError as e:
        print(f"⚠️  Email webhooks not available: {e}")
    except Exception as e:
        print(f"❌ Error loading email webhooks: {e}")

    # Sentry Test Router (only in development)
    if os.getenv("ENVIRONMENT", "development") == "development":
        app.include_router(sentry_test.router)

    # SuperAdmin Sentry worker-pipeline trigger (TF-359): registered in ALL
    # environments so the worker -> Sentry path can be verified in production.
    # Access is locked to SuperAdmins via get_current_superuser.
    app.include_router(sentry_test.admin_router)

    # Premium/Enterprise Features: Load additional Premium APIs
    if is_full_deployment:
        # Create premium tables if they don't exist
        try:
            from premium.models.chat_db import ChatSession, ChatMessage  # noqa: F401
            from premium.models.prompt import Prompt, PromptTemplate, PromptUsageLog  # noqa: F401
            from database import engine
            from database import Base

            Base.metadata.create_all(bind=engine)
            print("✅ Premium database tables created/verified")
        except ImportError as e:
            print(f"⚠️  Premium models not available: {e}")
        except Exception as e:
            print(f"❌ Error creating premium tables: {e}")

        # Premium: Prompts API
        try:
            from premium.api.v1 import prompts as prompts_api

            app.include_router(prompts_api.router)
            print("✅ Premium Prompts API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Prompts API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Prompts API: {e}")

        # Premium: Chat API (Document ChatBot)
        try:
            from premium.api.v1 import chat as chat_api

            app.include_router(chat_api.router)
            print("✅ Premium Chat API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Chat API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Chat API: {e}")

        # Premium: Wizard API
        try:
            from premium.api.v1 import wizard as wizard_api

            app.include_router(wizard_api.router)
            print("✅ Premium Wizard API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Wizard API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Wizard API: {e}")

        # Premium: MCP Facade Server (Fly.io Management Tools)
        try:
            from premium.mcp import create_mcp_app
            from premium.mcp.auth import (
                oauth_protected_resource,
                oauth_authorization_server,
            )

            mcp_app = create_mcp_app()
            app.mount("/mcp", mcp_app)

            # Redirect /mcp → /mcp/ (FastAPI mount only handles /mcp/*)
            @app.api_route("/mcp", methods=["GET", "POST", "DELETE"])
            async def mcp_redirect(request: Request):
                from starlette.responses import RedirectResponse

                url = str(request.url).replace("/mcp", "/mcp/", 1)
                # Respect X-Forwarded-Proto from reverse proxy (e.g. Fly.io TLS termination)
                proto = request.headers.get("x-forwarded-proto", "")
                if proto == "https" and url.startswith("http://"):
                    url = url.replace("http://", "https://", 1)
                return RedirectResponse(url=url, status_code=307)

            # Expose well-known endpoints at root level for MCP discovery (RFC 9728)
            # Clients try /.well-known/oauth-protected-resource/mcp before /mcp/.well-known/...
            app.get("/.well-known/oauth-protected-resource/mcp")(
                oauth_protected_resource
            )
            app.get("/.well-known/oauth-protected-resource")(oauth_protected_resource)
            app.get("/.well-known/oauth-authorization-server/mcp")(
                oauth_authorization_server
            )
            app.get("/.well-known/oauth-authorization-server")(
                oauth_authorization_server
            )
            print("✅ Premium MCP Facade Server mounted at /mcp/")
        except ImportError as e:
            print(f"⚠️  Premium MCP Server not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium MCP Server: {e}")

        print("")
    else:
        print("ℹ️  Core mode - Premium/Enterprise APIs not loaded")

    # Startup: Reset any documents stuck in PROCESSING status
    # (happens when backend restarts during document processing)
    try:
        from models.document import Document, DocumentStatus

        db = SessionLocal()
        try:
            processing_docs = (
                db.query(Document)
                .filter(Document.status == DocumentStatus.PROCESSING)
                .all()
            )

            if processing_docs:
                print(
                    f"⚠️  Found {len(processing_docs)} documents stuck in PROCESSING status"
                )
                for doc in processing_docs:
                    print(f"   - Resetting {doc.original_filename} (ID: {doc.id})")
                    doc.status = DocumentStatus.UPLOADED
                    doc.doc_metadata = doc.doc_metadata or {}
                    if isinstance(doc.doc_metadata, dict):
                        doc.doc_metadata["reset_at_startup"] = True

                db.commit()
                print(f"✅ Reset {len(processing_docs)} documents to UPLOADED status")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error resetting processing documents: {str(e)}")

    # Startup: Reap stuck ImportJob rows. A worker kill/OOM/deploy
    # mid-pipeline leaves ``import_jobs.status='running'`` forever
    # because no code path ever transitions out without the pipeline
    # finishing. Mark anything older than 30 minutes as FAILED so the
    # job-list UI shows a terminal state instead of a zombie.
    try:
        from datetime import datetime, timedelta, timezone

        from enums import ImportJobStatus
        from models.submission import ImportJob

        db = SessionLocal()
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            stuck = (
                db.query(ImportJob)
                .filter(
                    ImportJob.status == ImportJobStatus.RUNNING.value,
                    ImportJob.started_at < cutoff,
                )
                .all()
            )
            for job in stuck:
                job.status = ImportJobStatus.FAILED.value
                job.finished_at = datetime.now(timezone.utc)
                existing = list(job.error_log or [])
                existing.append(
                    {
                        "row_index": 0,
                        "reason": (
                            "Worker wahrscheinlich vor Abschluss beendet "
                            "(OOM/Deploy/Kill)."
                        ),
                        "step": "watchdog",
                        "exception_type": "WatchdogTimeout",
                    }
                )
                job.error_log = existing
            if stuck:
                db.commit()
                print(f"✅ Reaped {len(stuck)} stuck import_jobs")
        finally:
            db.close()
    except Exception as e:
        print(f"❌ Error reaping stuck import jobs: {str(e)}")

    yield  # Application is running

    # Shutdown: Give in-flight docs indexing a bounded chance to finish so
    # that Qdrant isn't left in partial state (cleared but not re-populated).
    # If the task is still running after 30s, proceed — the next startup
    # will full-scan again and self-heal.
    for task in list(_background_tasks):
        if task.done():
            continue
        try:
            await asyncio.wait_for(asyncio.shield(task), timeout=30)
        except asyncio.TimeoutError:
            logger.warning(
                "Shutdown: background task did not complete within 30s; "
                "Qdrant docs_help may be in partial state until next startup."
            )
        except asyncio.CancelledError:
            logger.warning("Shutdown: background task cancelled during grace window.")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="ExamCraft AI API",
    description="KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Document ChatBot",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent 307 redirects to HTTP behind proxy
)

# Sentry Context Middleware
from middleware.sentry_context import SentryContextMiddleware  # noqa: E402

app.add_middleware(SentryContextMiddleware)

# Rate Limiting middleware
rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
requests_per_minute = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
requests_per_hour = int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=requests_per_minute,
    requests_per_hour=requests_per_hour,
    enabled=rate_limit_enabled,
)

# i18n Middleware - resolves locale from Accept-Language header
from middleware.i18n_middleware import I18nMiddleware  # noqa: E402

app.add_middleware(I18nMiddleware)

# CORS middleware - must be added LAST so it becomes the outermost layer.
# In Starlette, add_middleware() prepends — last added = outermost.
# This ensures CORS headers are present on ALL responses, including 429s
# from RateLimitMiddleware, preventing net::ERR_FAILED in the browser.
cors_origins_str = os.getenv(
    "CORS_ORIGINS", "http://localhost:3000,http://localhost:8000"
)
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

# Wenn "*" in den Origins ist, setze allow_credentials auf False
# (CORS-Konflikt: allow_credentials=True und allow_origins="*" sind nicht kompatibel)
allow_credentials = "*" not in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


# Pydantic models
class ExamRequest(BaseModel):
    topic: str
    difficulty: str = "medium"  # easy, medium, hard
    question_count: int = 5
    question_types: List[str] = ["multiple_choice", "open_ended"]
    language: str = "de"
    tag_ids: Optional[List[int]] = None  # TF-320 Iter2: Tags für generierte Fragen


class Question(BaseModel):
    id: str
    type: str
    question: str
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str
    topic: str


class ExamResponse(BaseModel):
    exam_id: str
    topic: str
    questions: List[Question]
    created_at: str
    metadata: dict


# Health check endpoint
@app.get("/")
async def root():
    """Root endpoint - Health check"""
    return {
        "message": "ExamCraft AI API",
        "status": "running",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with version and deployment info"""
    from datetime import datetime
    import tomllib
    from pathlib import Path

    # Read version from pyproject.toml
    version = "unknown"
    try:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)
            version = pyproject.get("project", {}).get("version", "unknown")
    except Exception:
        # Fallback to default version
        version = "0.1.0"

    # Get processor type
    processor_type = os.getenv("DOCUMENT_PROCESSOR_TYPE", "auto")

    # Get actual processor in use
    try:
        from services.document_processors.processor_factory import document_processor

        processor_class = document_processor.__class__.__name__
    except Exception:
        processor_class = "unknown"

    # Build timestamp (set during Docker build)
    build_timestamp = os.getenv("BUILD_TIMESTAMP", "unknown")

    return {
        "status": "healthy",
        "service": "ExamCraft AI Backend",
        "version": version,
        "environment": os.getenv("ENVIRONMENT", "development"),
        "build_timestamp": build_timestamp,
        "processor": {"configured": processor_type, "active": processor_class},
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/v1/health")
async def api_health_check():
    """Detailed health check endpoint for production monitoring"""
    from services.vector_service_factory import vector_service
    import redis
    from database import engine

    health_status = {
        "status": "healthy",
        "version": os.getenv("APP_VERSION", "1.1.0"),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "services": {},
    }

    # Check Database
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        health_status["services"]["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["services"]["database"] = "error"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url)
        r.ping()
        health_status["services"]["redis"] = "connected"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["services"]["redis"] = "error"
        health_status["status"] = "degraded"

    # Check Vector Database
    try:
        # get_collection_stats() ist nicht async, gibt dict zurück
        stats = vector_service.get_collection_stats()
        if stats and isinstance(stats, dict):
            health_status["services"]["vector_db"] = "connected"
            health_status["services"]["vector_db_type"] = os.getenv(
                "VECTOR_SERVICE_TYPE", "qdrant"
            )
        else:
            health_status["services"]["vector_db"] = "available"
    except Exception as e:
        logger.error(f"Vector DB health check failed: {e}")
        health_status["services"]["vector_db"] = "error"
        health_status["status"] = "degraded"

    # Check Claude API
    health_status["services"]["claude_api"] = (
        "configured" if os.getenv("ANTHROPIC_API_KEY") else "not_configured"
    )

    # Check Document Processor
    processor_type = os.getenv("DOCUMENT_PROCESSOR_TYPE", "auto")
    try:
        from services.document_processors.processor_factory import document_processor

        processor_class = document_processor.__class__.__name__
        health_status["services"]["document_processor"] = {
            "configured": processor_type,
            "active": processor_class,
        }
    except Exception as e:
        logger.error(f"Document processor health check failed: {e}")
        health_status["services"]["document_processor"] = {
            "configured": processor_type,
            "active": "error",
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/v1/claude/usage")
async def get_claude_usage():
    """Get Claude API usage statistics (development only)"""
    if os.getenv("ENVIRONMENT", "development") != "development":
        raise HTTPException(status_code=404, detail="Not found")
    claude_service = get_claude_service()
    return claude_service.get_usage_stats()


@app.get("/api/v1/claude/health")
async def get_claude_health():
    """Get Claude API health status (development only)"""
    if os.getenv("ENVIRONMENT", "development") != "development":
        raise HTTPException(status_code=404, detail="Not found")
    claude_service = get_claude_service()
    stats = claude_service.get_usage_stats()
    return {
        "status": "healthy" if not stats["demo_mode"] else "demo_mode",
        "service": "Claude API",
        "demo_mode": stats["demo_mode"],
        "api_key_configured": bool(claude_service.api_key),
        "model": claude_service.model,
        "usage": stats,
    }


# Demo endpoints for Workshop (development only)
@app.post("/api/v1/generate-exam", response_model=ExamResponse)
async def generate_exam(request: ExamRequest):
    """
    Generate an exam with AI-powered questions using Claude API
    Falls back to demo questions if Claude API is not available
    (development only - disabled in production)
    """
    if os.getenv("ENVIRONMENT", "development") != "development":
        raise HTTPException(status_code=404, detail="Not found")
    try:
        # Use Claude service to generate questions
        claude_service = get_claude_service()
        question_data = await claude_service.generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            question_count=request.question_count,
            question_types=request.question_types,
            language=request.language,
        )

        # Convert to Question objects
        questions = []
        for i, q_data in enumerate(question_data):
            question = Question(
                id=q_data.get("id", f"q{i + 1}"),
                type=q_data.get("type", "multiple_choice"),
                question=q_data.get("question", ""),
                options=q_data.get("options"),
                correct_answer=q_data.get("correct_answer"),
                explanation=q_data.get("explanation"),
                difficulty=q_data.get("difficulty", request.difficulty),
                topic=q_data.get("topic", request.topic),
            )
            questions.append(question)

        exam_response = ExamResponse(
            exam_id=f"exam_{hash(request.topic + str(request.question_count))}",
            topic=request.topic,
            questions=questions,
            created_at="2025-09-22T12:53:00Z",
            metadata={
                "difficulty": request.difficulty,
                "question_count": len(questions),
                "language": request.language,
                "generated_by": "ExamCraft AI with Claude"
                if get_claude_service().api_key
                else "ExamCraft AI Demo",
            },
        )

        return exam_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating exam: {str(e)}")


class GenerateQuestionsRequest(BaseModel):
    topic: str
    num_questions: int = Field(default=5, ge=1, le=20)
    difficulty: str = "medium"
    document_ids: Optional[List[int]] = None
    tag_ids: Optional[List[int]] = None  # TF-320 Iter2


@app.post("/api/v1/questions/generate")
async def generate_questions_endpoint(
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Fragen generieren und optional Tags zuweisen (TF-320 Iter2)."""
    from models.question_review import QuestionReview, ReviewStatus
    from models.tag import Tag, QuestionTag as _QuestionTag

    claude_service = get_claude_service()
    try:
        question_data = await claude_service.generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            question_count=request.num_questions,
            question_types=["multiple_choice", "open_ended"],
            language="de",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler bei Generierung: {str(e)}")

    review_ids = []
    for q_data in question_data:
        review = QuestionReview(
            question_text=q_data.get("question", ""),
            question_type=q_data.get("type", "open_ended"),
            options=q_data.get("options"),
            correct_answer=q_data.get("correct_answer"),
            explanation=q_data.get("explanation"),
            difficulty=q_data.get("difficulty", request.difficulty),
            topic=q_data.get("topic", request.topic),
            language="de",
            review_status=ReviewStatus.PENDING.value,
            institution_id=current_user.institution_id,
            created_by=current_user.id,
        )
        db.add(review)
        db.flush()
        review_ids.append(review.id)

    if request.tag_ids and review_ids:
        valid_tags = (
            db.query(Tag)
            .filter(
                Tag.id.in_(request.tag_ids),
                Tag.is_archived == False,  # noqa: E712
                (Tag.institution_id == current_user.institution_id)
                | (Tag.scope == "global"),
            )
            .all()
        )
        for rid in review_ids:
            for tag in valid_tags:
                db.add(_QuestionTag(question_id=rid, tag_id=tag.id))

    db.commit()
    return {"task_id": None, "question_ids": review_ids, "count": len(review_ids)}


@app.get("/api/v1/topics")
async def get_available_topics():
    """Get list of available topics for exam generation"""
    return {
        "topics": [
            "Python Programmierung",
            "Datenstrukturen und Algorithmen",
            "Webentwicklung",
            "Datenbanken",
            "Machine Learning",
            "Softwarearchitektur",
            "Projektmanagement",
            "Cybersecurity",
        ]
    }


@app.get("/api/v1/exam/{exam_id}")
async def get_exam(exam_id: str):
    """Retrieve a specific exam by ID"""
    # Demo implementation
    if exam_id == "demo_exam_001":
        return {
            "exam_id": exam_id,
            "status": "completed",
            "topic": "Demo Topic",
            "created_at": "2025-09-22T12:53:00Z",
        }
    else:
        raise HTTPException(status_code=404, detail="Exam not found")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
