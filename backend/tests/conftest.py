"""
Pytest Configuration und Fixtures für ExamCraft AI Tests
"""

import pytest
import tempfile
import os

# Disable rate limiting for tests before importing the app
os.environ["RATE_LIMIT_ENABLED"] = "false"

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base
from main import app

# Ensure all models are registered with Base before create_all() is called.
# Models that use lazy imports in services/api must be explicitly imported here.
import models.auth  # noqa: F401
import models.document  # noqa: F401
import models.question_review  # noqa: F401
import models.rbac  # noqa: F401
import models.email_event  # noqa: F401
import models.help  # noqa: F401

# Skip test files that need major fixture updates for current DB schema
collect_ignore_glob = [
    "test_rbac.py",
    "test_rbac_api.py",
    "test_multi_tenancy.py",
    "test_document_model.py",
]

# Test Database Configuration
# CI sets DATABASE_URL with localhost; Docker uses 'postgres' as host
POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST", "localhost"
)  # Docker: postgres, CI/Lokal: localhost
POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD", "examcraft_dev"
)  # Match docker-compose.yml
_default_db_url = (
    f"postgresql://examcraft:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/examcraft_test"
)
# Allow override via TEST_DATABASE_URL or derive from DATABASE_URL
_base_url = os.getenv("DATABASE_URL", "")
if _base_url and not os.getenv("TEST_DATABASE_URL"):
    # Derive test DB URL from DATABASE_URL by replacing the database name
    _test_db_url = _base_url.rsplit("/", 1)[0] + "/examcraft_test"
else:
    _test_db_url = _default_db_url
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", _test_db_url)


# Test Database Setup
@pytest.fixture(scope="session")
def test_engine():
    """
    Erstelle Test-Database Engine mit PostgreSQL

    Verwendet eine separate Test-Datenbank um Produktionsdaten zu schützen.
    Die Datenbank wird vor jedem Test-Run neu erstellt.
    """
    # Erstelle Engine für postgres Database (um Test-DB zu erstellen/löschen)
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")

    # Extrahiere Test-DB Namen
    test_db_name = TEST_DATABASE_URL.split("/")[-1]

    # Lösche Test-DB falls vorhanden und erstelle neu
    with admin_engine.connect() as conn:
        # Beende alle Verbindungen zur Test-DB
        conn.execute(
            text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{test_db_name}'
            AND pid <> pg_backend_pid()
        """)
        )

        # Lösche Test-DB
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))

        # Erstelle Test-DB
        conn.execute(text(f"CREATE DATABASE {test_db_name}"))

    admin_engine.dispose()

    # Erstelle Engine für Test-DB
    engine = create_engine(TEST_DATABASE_URL)

    # Erstelle alle Tabellen
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup: Lösche Test-DB nach allen Tests
    engine.dispose()

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(
            text(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{test_db_name}'
            AND pid <> pg_backend_pid()
        """)
        )
        conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
    admin_engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine):
    """
    Erstelle Test-Database Session mit Transaction Rollback

    Jeder Test läuft in einer eigenen Transaction die nach dem Test
    zurückgerollt wird. Dadurch bleiben Tests isoliert.
    """
    connection = test_engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=connection
    )
    session = TestingSessionLocal()

    yield session

    # Rollback Transaction nach Test
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client():
    """FastAPI Test Client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
def temp_upload_dir():
    """Temporäres Upload-Verzeichnis für Tests"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def sample_text_file():
    """Erstelle temporäre Test-Textdatei"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("Dies ist ein Test-Dokument für Unit Tests.\n")
        f.write("Es enthält mehrere Zeilen Text.\n")
        f.write("Perfekt für Testing-Zwecke.")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture(scope="function")
def sample_pdf_content():
    """Mock PDF-Inhalt für Tests"""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"


@pytest.fixture(scope="function")
def mock_upload_file():
    """Mock UploadFile für Tests"""
    from io import BytesIO
    from fastapi import UploadFile

    content = b"Test file content for upload testing"
    file_obj = BytesIO(content)

    upload_file = UploadFile(
        filename="test_document.txt", file=file_obj, size=len(content)
    )

    return upload_file


@pytest.fixture(scope="function")
def test_institution(test_db):
    """Erstelle Test-Institution für Subscription Limit Tests"""
    from models.auth import Institution

    institution = Institution(
        id=1,
        name="Test University",
        slug="test-university",  # Required field
        subscription_tier="professional",
        max_users=10,
        max_documents=100,
        max_questions_per_month=1000,
    )
    test_db.add(institution)
    test_db.commit()
    test_db.refresh(institution)

    return institution


# === Help Widget Shared Fixtures (TF-308) ===


def _make_mock_user(is_admin: bool = False):
    """Create a mock user for help API tests."""
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = 999
    user.email = "testuser@example.com"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_active = True
    user.institution = None
    role = MagicMock()
    role.name = "admin" if is_admin else "teacher"
    user.roles = [role]
    return user


@pytest.fixture(scope="function")
def help_db(test_engine):
    """DB session for help tests with seeded Institution + User for FK constraints."""
    from sqlalchemy.orm import sessionmaker
    from models.auth import Institution, User

    TestSession = sessionmaker(bind=test_engine)
    db = TestSession()

    # Create institution (required by User.institution_id NOT NULL)
    institution = Institution(
        id=998,
        name="Help Test University",
        slug="help-test-university",
        subscription_tier="free",
        max_users=10,
        max_documents=50,
        max_questions_per_month=100,
    )
    db.merge(institution)
    db.flush()

    # Create user with id=999 to match mock_user.id
    user = User(
        id=999,
        email="testuser@example.com",
        first_name="Test",
        last_name="User",
        institution_id=998,
        status="active",
    )
    db.merge(user)
    db.commit()

    yield db
    db.rollback()
    db.close()


@pytest.fixture(scope="function")
def help_client(help_db):
    """TestClient with teacher user override."""
    from main import app
    from utils.auth_utils import get_current_user, get_current_active_user
    from database import get_db
    import api.v1.help as help_module
    from fastapi.testclient import TestClient

    app.include_router(help_module.router)

    mock_user = _make_mock_user(is_admin=False)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: help_db

    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_client(help_db):
    """TestClient with admin user override."""
    from main import app
    from utils.auth_utils import get_current_user, get_current_active_user
    from database import get_db
    import api.v1.help as help_module
    from fastapi.testclient import TestClient

    app.include_router(help_module.router)

    mock_user = _make_mock_user(is_admin=True)

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_active_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: help_db

    client = TestClient(app, raise_server_exceptions=True)
    yield client
    app.dependency_overrides.clear()
