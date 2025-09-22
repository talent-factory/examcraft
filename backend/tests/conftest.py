"""
Pytest Configuration und Fixtures für ExamCraft AI Tests
"""

import pytest
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from database import Base
from main import app

# Test Database Setup
@pytest.fixture(scope="session")
def test_engine():
    """Erstelle Test-Database Engine"""
    # Verwende SQLite für Tests
    engine = create_engine("sqlite:///./test.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    # Cleanup
    os.remove("./test.db")

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Erstelle Test-Database Session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()
    yield session
    session.close()

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
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
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
        filename="test_document.txt",
        file=file_obj,
        size=len(content)
    )
    
    return upload_file
