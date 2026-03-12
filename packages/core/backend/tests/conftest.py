"""
Pytest Configuration und Fixtures für ExamCraft AI Tests
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base
from main import app

# Test Database Configuration
# Verwende 'postgres' als Host im Docker-Netzwerk, 'localhost' außerhalb
POSTGRES_HOST = os.getenv(
    "POSTGRES_HOST", "postgres"
)  # Docker: postgres, Lokal: localhost
POSTGRES_PASSWORD = os.getenv(
    "POSTGRES_PASSWORD", "examcraft_dev"
)  # Match docker-compose.yml
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    f"postgresql://examcraft:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:5432/examcraft_test",
)


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
