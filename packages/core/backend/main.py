"""
ExamCraft AI - FastAPI Backend
KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from contextlib import asynccontextmanager
import os
import logging
from dotenv import load_dotenv
from middleware.rate_limit import RateLimitMiddleware

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
        import subprocess

        result = subprocess.run(
            ["python", "scripts/seed_rbac_data.py"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            print("✅ RBAC data seeded successfully")
        else:
            print(f"⚠️  RBAC seed warning: {result.stderr}")
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
    else:
        print("ℹ️  Running in Core mode - Premium features disabled")

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

    spec_qr = importlib.util.spec_from_file_location(
        "core_api_question_review", os.path.join(core_api_path, "question_review.py")
    )
    question_review = importlib.util.module_from_spec(spec_qr)
    spec_qr.loader.exec_module(question_review)

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

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(gdpr.router)
    app.include_router(documents.router)
    app.include_router(rag_exams.router)
    app.include_router(rbac_api.router)
    app.include_router(question_review.router)
    app.include_router(billing_api.router, prefix="/api/v1/billing", tags=["billing"])
    app.include_router(webhooks_api.router, prefix="/api/v1/webhooks", tags=["webhooks"])

    # Sentry Test Router (only in development)
    if os.getenv("ENVIRONMENT", "development") == "development":
        app.include_router(sentry_test.router)

    # Premium/Enterprise Features: Load additional Premium APIs
    if is_full_deployment:
        # Premium: Chat API
        try:
            from premium.api.v1 import chat as chat_api

            app.include_router(chat_api.router)
            print("✅ Premium Chat API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Chat API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Chat API: {e}")

        # Premium: Prompts API
        try:
            from premium.api.v1 import prompts as prompts_api

            app.include_router(prompts_api.router)
            print("✅ Premium Prompts API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Prompts API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Prompts API: {e}")

        # Premium: Vector Search API
        try:
            from premium.api.v1 import vector_search as vector_search_api

            app.include_router(vector_search_api.router)
            print("✅ Premium Vector Search API loaded")
        except ImportError as e:
            print(f"⚠️  Premium Vector Search API not available: {e}")
        except Exception as e:
            print(f"❌ Error loading Premium Vector Search API: {e}")

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

    yield  # Application is running

    # Shutdown: Cleanup (if needed in the future)
    pass


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="ExamCraft AI API",
    description="KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Document ChatBot",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware - Production-ready configuration
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
)

# Sentry Context Middleware (must be added before other middlewares)
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


# Pydantic models
class ExamRequest(BaseModel):
    topic: str
    difficulty: str = "medium"  # easy, medium, hard
    question_count: int = 5
    question_types: List[str] = ["multiple_choice", "open_ended"]
    language: str = "de"


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
        "version": "1.0.0",
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
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Redis
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        r = redis.from_url(redis_url)
        r.ping()
        health_status["services"]["redis"] = "connected"
    except Exception as e:
        health_status["services"]["redis"] = f"error: {str(e)}"
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
        health_status["services"]["vector_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Claude API
    health_status["services"]["claude_api"] = (
        "configured" if os.getenv("CLAUDE_API_KEY") else "not_configured"
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
        health_status["services"]["document_processor"] = {
            "configured": processor_type,
            "active": "error",
            "error": str(e),
        }
        health_status["status"] = "degraded"

    return health_status


@app.get("/api/v1/claude/usage")
async def get_claude_usage():
    """Get Claude API usage statistics"""
    claude_service = get_claude_service()
    return claude_service.get_usage_stats()


@app.get("/api/v1/claude/health")
async def get_claude_health():
    """Get Claude API health status"""
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


# Demo endpoints for Workshop
@app.post("/api/v1/generate-exam", response_model=ExamResponse)
async def generate_exam(request: ExamRequest):
    """
    Generate an exam with AI-powered questions using Claude API
    Falls back to demo questions if Claude API is not available
    """
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
