"""
Database Configuration für ExamCraft AI
SQLAlchemy Setup und Session Management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Database URL - für Development verwenden wir PostgreSQL aus Docker
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://examcraft:examcraft_dev@localhost:5432/examcraft"
)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()


def get_db():
    """
    Dependency für FastAPI um Database Session zu bekommen
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Erstelle alle Tabellen in der Datenbank

    WICHTIG: Importiert alle Models, damit sie bei Base registriert sind
    """
    # Import all models to register them with Base
    # This must be done before create_all() is called

    # Import Core models first
    try:
        from models.auth import User, Role, Institution, UserSession, AuditLog
        from models.document import Document, DocumentStatus
        from models.question_review import QuestionReview, ReviewStatus
        print("✅ Core models imported (Auth + Documents + Question Review)")
    except Exception as e:
        print(f"⚠️  Core models import error: {e}")
        import traceback
        traceback.print_exc()

    # Import Premium models (if available)
    try:
        import os
        import importlib.util

        # Check if premium package is mounted (Docker: /app/premium)
        premium_models_path = "/app/premium/models"
        if not os.path.exists(premium_models_path):
            # Fallback for local development
            premium_models_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "premium", "backend", "models"
            )

        if os.path.exists(premium_models_path):
            # Import prompt models directly
            prompt_spec = importlib.util.spec_from_file_location(
                "premium_prompt_models", os.path.join(premium_models_path, "prompt.py")
            )
            prompt_module = importlib.util.module_from_spec(prompt_spec)
            prompt_spec.loader.exec_module(prompt_module)

            # Import chat database models directly (chat_db.py contains SQLAlchemy models)
            chat_spec = importlib.util.spec_from_file_location(
                "premium_chat_models", os.path.join(premium_models_path, "chat_db.py")
            )
            chat_module = importlib.util.module_from_spec(chat_spec)
            chat_spec.loader.exec_module(chat_module)

            print("✅ Premium models imported (Prompt Knowledge Base + ChatBot)")
        else:
            print("⚠️  Premium package not found - skipping premium models")
    except Exception as e:
        print(f"⚠️  Premium models not available: {e}")
        import traceback

        traceback.print_exc()

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    create_tables()
