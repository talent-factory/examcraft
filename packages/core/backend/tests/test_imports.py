"""
Import Tests für ExamCraft AI Backend
Stellt sicher, dass alle Module korrekt importiert werden können
"""

import pytest
import sys
from pathlib import Path

# Füge Backend-Verzeichnis zu Python Path hinzu
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class TestCriticalImports:
    """Tests für kritische Imports, die häufig Probleme verursachen"""

    def test_numpy_import(self):
        """Numpy muss immer verfügbar sein"""
        import numpy as np

        assert np is not None
        assert hasattr(np, "ndarray")

    def test_fastapi_import(self):
        """FastAPI Core muss verfügbar sein"""
        from fastapi import FastAPI

        assert FastAPI is not None

    def test_pydantic_import(self):
        """Pydantic muss verfügbar sein"""
        from pydantic import BaseModel

        assert BaseModel is not None

    def test_sqlalchemy_import(self):
        """SQLAlchemy muss verfügbar sein"""
        from sqlalchemy import create_engine

        assert create_engine is not None

    def test_qdrant_client_import(self):
        """Qdrant Client muss verfügbar sein"""
        try:
            from qdrant_client import QdrantClient

            assert QdrantClient is not None
        except ImportError:
            pytest.skip("Qdrant client not installed")


class TestServiceImports:
    """Tests für Service-Module"""

    def test_qdrant_vector_service_import(self):
        """Qdrant Vector Service module muss importierbar sein"""
        import services.qdrant_vector_service as qdrant_mod

        assert qdrant_mod is not None
        # Core package has SearchResult placeholder, not QdrantVectorService class
        assert hasattr(qdrant_mod, "SearchResult")

    def test_vector_service_factory_import(self):
        """Vector Service Factory muss importierbar sein"""
        from services.vector_service_factory import get_vector_service

        assert get_vector_service is not None

    def test_document_service_import(self):
        """Document Service muss importierbar sein"""
        from services.document_service import DocumentService

        assert DocumentService is not None

    def test_docling_service_import(self):
        """Docling Service muss importierbar sein"""
        from services.docling_service import DoclingService

        assert DoclingService is not None


class TestAPIImports:
    """Tests für API-Module"""

    def test_documents_api_import(self):
        """Documents API muss importierbar sein"""
        from api import documents

        assert documents is not None

    def test_rag_exams_api_import(self):
        """RAG Exams API muss importierbar sein"""
        from api import rag_exams

        assert rag_exams is not None


class TestMainAppImport:
    """Test für Haupt-Application"""

    def test_main_app_import(self):
        """main.py muss importierbar sein"""
        import main

        assert main is not None
        assert hasattr(main, "app")

    def test_app_is_fastapi_instance(self):
        """App muss FastAPI-Instanz sein"""
        from fastapi import FastAPI
        import main

        assert isinstance(main.app, FastAPI)


class TestNumpyAvailability:
    """Spezielle Tests für numpy-Verfügbarkeit in Services"""

    def test_numpy_available(self):
        """Numpy muss verfügbar sein"""
        import numpy as np

        assert np is not None


class TestOptionalDependencies:
    """Tests für optionale Dependencies"""

    def test_sentence_transformers_optional(self):
        """Sentence Transformers ist optional"""
        try:
            from sentence_transformers import SentenceTransformer

            # Wenn verfügbar, sollte es funktionieren
            assert SentenceTransformer is not None
        except ImportError:
            # Wenn nicht verfügbar, ist das OK
            pass

    def test_qdrant_client_optional(self):
        """Qdrant Client ist optional (nur in Premium)"""
        try:
            from qdrant_client import QdrantClient

            assert QdrantClient is not None
        except ImportError:
            # Wenn nicht verfügbar, ist das OK (Core Package)
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
