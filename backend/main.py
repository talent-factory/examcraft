"""
ExamCraft AI - FastAPI Backend
KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import os
from dotenv import load_dotenv
from services.claude_service import ClaudeService
from api import documents, vector_search, rag_exams
from api.documents import router as documents_router
from api.v1 import chat as chat_api
from database import create_tables

# Load environment variables
load_dotenv()

# Initialize services
claude_service = ClaudeService()

# Initialize FastAPI app
app = FastAPI(
    title="ExamCraft AI API",
    description="KI-gestützte Plattform zur automatischen Generierung von Prüfungsaufgaben für OpenBook-Prüfungen mit Document ChatBot",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware - Production-ready configuration
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
create_tables()

# Include routers
app.include_router(documents.router)
app.include_router(vector_search.router)
app.include_router(rag_exams.router)
app.include_router(chat_api.router)  # Chat API

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
        "docs": "/docs"
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
    except Exception as e:
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
        "processor": {
            "configured": processor_type,
            "active": processor_class
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
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
        "services": {}
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
            health_status["services"]["vector_db_type"] = os.getenv("VECTOR_SERVICE_TYPE", "qdrant")
        else:
            health_status["services"]["vector_db"] = "available"
    except Exception as e:
        health_status["services"]["vector_db"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check Claude API
    health_status["services"]["claude_api"] = "configured" if os.getenv("CLAUDE_API_KEY") else "not_configured"

    return health_status

@app.get("/api/v1/claude/usage")
async def get_claude_usage():
    """Get Claude API usage statistics"""
    return claude_service.get_usage_stats()

@app.get("/api/v1/claude/health")
async def get_claude_health():
    """Get Claude API health status"""
    stats = claude_service.get_usage_stats()
    return {
        "status": "healthy" if not stats["demo_mode"] else "demo_mode",
        "service": "Claude API",
        "demo_mode": stats["demo_mode"],
        "api_key_configured": bool(claude_service.api_key),
        "model": claude_service.model,
        "usage": stats
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
        question_data = await claude_service.generate_questions(
            topic=request.topic,
            difficulty=request.difficulty,
            question_count=request.question_count,
            question_types=request.question_types,
            language=request.language
        )
        
        # Convert to Question objects
        questions = []
        for i, q_data in enumerate(question_data):
            question = Question(
                id=q_data.get("id", f"q{i+1}"),
                type=q_data.get("type", "multiple_choice"),
                question=q_data.get("question", ""),
                options=q_data.get("options"),
                correct_answer=q_data.get("correct_answer"),
                explanation=q_data.get("explanation"),
                difficulty=q_data.get("difficulty", request.difficulty),
                topic=q_data.get("topic", request.topic)
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
                "generated_by": "ExamCraft AI with Claude" if claude_service.api_key else "ExamCraft AI Demo"
            }
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
            "Cybersecurity"
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
            "created_at": "2025-09-22T12:53:00Z"
        }
    else:
        raise HTTPException(status_code=404, detail="Exam not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
