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
        from models.auth import (  # noqa: F401
            User,
            Role,
            Institution,
            UserSession,
            AuditLog,
            OAuthAccount,
        )
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
        from models.email_event import (  # noqa: F401
            EmailEvent,
            EmailSuppressionList,
        )

        print(
            "✅ Core models imported (Auth + Documents + Question Review + RBAC + Email)"
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise RuntimeError(f"Failed to import core models (cannot start): {e}") from e

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
                from premium.models.wizard import WizardSession, WizardMessage  # noqa: F401

                print(
                    "✅ Premium models imported (Prompt Knowledge Base + ChatBot + Wizard)"
                )
            except ImportError as ie:
                print(f"⚠️  Premium models import failed: {ie}")
        else:
            print("⚠️  Premium package not found - skipping premium models")
    except Exception as e:
        print(f"⚠️  Premium models not available: {e}")
        import traceback

        traceback.print_exc()

    # Migrationen ausfuehren (Alembic) oder Tabellen direkt erstellen (Fallback)
    _run_migrations_or_create_all()


def _run_migrations_or_create_all():
    """
    Fuehre Alembic-Migrationen aus oder erstelle Tabellen direkt.

    Verhalten je nach AUTO_MIGRATE env var:
    - AUTO_MIGRATE=true: Fuehre 'alembic upgrade head' aus (fuer Development)
    - AUTO_MIGRATE absent or not 'true': Nur pruefen ob Migrationen ausstehen und warnen
    - Fallback: Base.metadata.create_all() wenn Alembic nicht verfuegbar

    WICHTIG: In Production NIEMALS automatisch migrieren. Migrationen muessen
    dort manuell nach Review ausgefuehrt werden:
        alembic upgrade head
    """
    import os

    alembic_dir = os.path.join(os.path.dirname(__file__), "alembic")
    alembic_ini = os.path.join(os.path.dirname(__file__), "alembic.ini")
    auto_migrate = os.getenv("AUTO_MIGRATE", "false").lower() == "true"

    if os.path.exists(alembic_dir) and os.path.exists(alembic_ini):
        try:
            from alembic.config import Config
            from alembic import command
            from alembic.script import ScriptDirectory
            from alembic.runtime.migration import MigrationContext

            alembic_cfg = Config(alembic_ini)
            alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

            # Pruefe ob Migrationen ausstehen
            script = ScriptDirectory.from_config(alembic_cfg)
            head_rev = script.get_current_head()

            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()

            if current_rev == head_rev:
                print(f"✅ Database schema is up to date (revision: {current_rev})")
                return

            pending_msg = (
                f"Pending migrations: DB at {current_rev or 'None'}, head at {head_rev}"
            )

            if auto_migrate:
                print(f"🔄 {pending_msg} — running alembic upgrade head...")
                command.upgrade(alembic_cfg, "head")
                print("✅ Database migrations applied successfully")
                return
            else:
                print(f"⚠️  {pending_msg}")
                print("⚠️  Set AUTO_MIGRATE=true or run manually: alembic upgrade head")
                # Nicht abbrechen — App soll starten, aber Warnung ist sichtbar
                return

        except ImportError:
            # Alembic not installed — acceptable to fall back to create_all
            print("⚠️  Alembic not installed, falling back to create_all")
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"⚠️  CRITICAL: Alembic migration failed: {e}")
            print(
                "⚠️  The database schema may be inconsistent. Fix migrations before proceeding."
            )
            # Still create missing tables, but the warning is loud

    Base.metadata.create_all(bind=engine)
    print("Database tables created/verified (create_all fallback)")


if __name__ == "__main__":
    create_tables()
