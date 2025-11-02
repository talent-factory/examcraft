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

    # Import Core models first (CRITICAL: Must be imported before Premium models!)
    try:
        from models.auth import User, Role, Institution, Session, AuditLog  # noqa: F401
        from models.document import Document, DocumentStatus  # noqa: F401
        from models.question_review import (  # noqa: F401
            QuestionReview,
            ReviewStatus,
            ReviewComment,
        )
        from models.rbac import (  # noqa: F401
            RBACRole,
            SubscriptionTier,
            Feature,
            RoleFeature,
            TierFeature,
            TierQuota,
        )

        print("✅ Core models imported (Auth + Documents + Question Review + RBAC)")
    except Exception as e:
        print(f"⚠️  Core models import error: {e}")
        import traceback

        traceback.print_exc()

    # Import Premium models (if available)
    # NOTE: We import Premium models using standard imports (not importlib.util)
    # to avoid double-registration issues with SQLAlchemy
    try:
        import os

        # Check if premium package is mounted (Docker: /app/premium)
        premium_models_path = "/app/premium/models"
        if not os.path.exists(premium_models_path):
            # Fallback for local development
            premium_models_path = os.path.join(
                os.path.dirname(__file__), "..", "..", "premium", "backend", "models"
            )

        if os.path.exists(premium_models_path):
            # Import Premium models using standard imports to avoid double-registration
            try:
                from premium.models.prompt import Prompt  # noqa: F401
                from premium.models.chat_db import ChatSession  # noqa: F401

                print("✅ Premium models imported (Prompt Knowledge Base + ChatBot)")
            except ImportError as ie:
                print(f"⚠️  Premium models import failed: {ie}")
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
