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
    from models import (
        Document,
        QuestionReview,
        ReviewComment,
        ReviewHistory,
        User,
        Role,
        Institution,
        UserSession,
        AuditLog,
        OAuthAccount,
        Feature,
        RoleFeature,
        RBACRole,
        SubscriptionTier,
        TierQuota,
        TierFeature,
        Organization,
        ResourceUsage,
        PermissionAuditLog,
    )

    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully")


if __name__ == "__main__":
    create_tables()
