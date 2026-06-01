"""
Integration Tests für Processor Factory
Tests für dynamische Processor-Auswahl (PyMuPDF / Legacy).
"""

import pytest
import os
from unittest.mock import patch

from services.document_processors.processor_factory import DocumentProcessorFactory
from services.document_processors.pymupdf_processor import PyMuPDFProcessor
from services.document_processors.legacy_processor import LegacyProcessor


class TestProcessorFactoryCreation:
    """Tests für Processor-Erstellung"""

    def test_factory_creates_pymupdf_processor_explicit(self):
        """Test: Factory erstellt PyMuPDFProcessor wenn explizit angefordert"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "pymupdf"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, PyMuPDFProcessor)

    def test_factory_creates_legacy_processor_explicit(self):
        """Test: Factory erstellt LegacyProcessor wenn explizit angefordert"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, LegacyProcessor)

    def test_factory_auto_detection_prefers_pymupdf(self):
        """Test: Auto-Detection bevorzugt PyMuPDF"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, (PyMuPDFProcessor, LegacyProcessor))

    def test_factory_auto_detection_fallback_to_legacy(self):
        """Test: Auto fällt auf Legacy zurück, wenn PyMuPDF nicht verfügbar ist"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            with patch(
                "services.document_processors.pymupdf_processor.PyMuPDFProcessor"
            ) as mock_pymupdf:
                mock_pymupdf.side_effect = ImportError("PyMuPDF not available")

                processor = DocumentProcessorFactory.create_processor()
                assert isinstance(processor, LegacyProcessor)

    def test_factory_default_is_pymupdf(self):
        """Test: Standard-Processor (ohne Env-Var) ist PyMuPDF"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DOCUMENT_PROCESSOR_TYPE", None)
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, (PyMuPDFProcessor, LegacyProcessor))


class TestProcessorFactoryErrorHandling:
    """Tests für Error Handling"""

    def test_factory_raises_error_for_invalid_type(self):
        """Test: Factory wirft Fehler bei ungültigem Processor-Typ"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                DocumentProcessorFactory.create_processor()

            assert "Unknown processor type" in str(exc_info.value)

    def test_factory_raises_error_when_pymupdf_requested_but_unavailable(self):
        """Test: Factory wirft Fehler wenn PyMuPDF explizit angefordert, aber nicht verfügbar"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "pymupdf"}):
            with patch(
                "services.document_processors.pymupdf_processor.PyMuPDFProcessor"
            ) as mock_pymupdf:
                mock_pymupdf.side_effect = ImportError("PyMuPDF not installed")

                with pytest.raises(ImportError) as exc_info:
                    DocumentProcessorFactory.create_processor()

                assert (
                    "PyMuPDF processor requested but dependencies not installed"
                    in str(exc_info.value)
                )


class TestProcessorFactoryIntegration:
    """Integration Tests für Factory mit echten Processoren"""

    @pytest.mark.asyncio
    async def test_factory_processor_can_process_document(self, tmp_path):
        """Test: Von Factory erstellter Processor kann Dokumente verarbeiten"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is a test document for integration testing.")

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()

            result = await processor.process_document(
                document_id=1,
                file_path=str(test_file),
                filename="test.txt",
                mime_type="text/plain",
            )

            assert result.document_id == 1
            assert result.filename == "test.txt"
            assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_factory_processor_maintains_configuration(self):
        """Test: Factory-Processor behält Konfiguration bei"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()

            assert processor.chunk_size == 1000
            assert processor.chunk_overlap == 200


class TestProcessorFactoryGlobalInstance:
    """Tests für globale Processor-Instanz"""

    def test_global_processor_instance_exists(self):
        """Test: Globale Processor-Instanz existiert"""
        from services.document_processors.processor_factory import document_processor

        assert document_processor is not None
        assert isinstance(document_processor, (PyMuPDFProcessor, LegacyProcessor))

    def test_global_processor_is_singleton(self):
        """Test: Globale Processor-Instanz ist Singleton"""
        from services.document_processors.processor_factory import (
            document_processor as proc1,
        )
        from services.document_processors.processor_factory import (
            document_processor as proc2,
        )

        assert proc1 is proc2


class TestProcessorFactoryGlobalInit:
    """Tests für _init_document_processor (TF-368).

    Eine Fehlkonfiguration darf den Worker NICHT still auf einen
    deprecateten Processor degradieren; ein echter Laufzeitfehler darf
    zwar zurückfallen, muss aber auf ERROR mit Original-Exception-Typ
    geloggt werden.
    """

    def test_init_fails_fast_on_misconfiguration(self):
        """Ungültiges DOCUMENT_PROCESSOR_TYPE → ValueError statt stillem Downgrade."""
        from services.document_processors.processor_factory import (
            _init_document_processor,
        )

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                _init_document_processor()

        assert "Unknown processor type" in str(exc_info.value)

    def test_init_logs_error_on_misconfiguration(self):
        """Die Fehlkonfiguration wird auf ERROR geloggt (operator-sichtbar).

        Wir prüfen den gemockten Modul-Logger statt caplog: die App
        rekonfiguriert Logging (Sentry-Integration u. a.), wodurch
        Propagation an caplog im Gesamt-Suite-Lauf nicht zuverlässig ist.
        """
        from services.document_processors import processor_factory as pf

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with patch.object(pf, "logger") as mock_logger:
                with pytest.raises(ValueError):
                    pf._init_document_processor()

        logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
        assert "DOCUMENT_PROCESSOR_TYPE" in logged

    def test_init_falls_back_with_error_log_on_runtime_failure(self):
        """Echter Laufzeitfehler → Fallback, aber ERROR-Log mit Exception-Typ."""
        from services.document_processors import processor_factory as pf

        with patch.object(
            pf.DocumentProcessorFactory,
            "create_processor",
            side_effect=RuntimeError("boom"),
        ):
            with patch.object(pf, "logger") as mock_logger:
                processor = pf._init_document_processor()

        # Fallback liefert PyMuPDF (im Test-Env verfügbar), kein stiller Abbruch.
        assert isinstance(processor, PyMuPDFProcessor)
        # Der Original-Exception-Typ wird als Logging-Argument mitgegeben.
        logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
        assert "RuntimeError" in logged


class TestProcessorFactoryEnvironmentVariables:
    """Tests für Environment Variable Handling"""

    def test_factory_respects_env_var_case_insensitive(self):
        """Test: Factory akzeptiert case-insensitive Environment Variables"""
        test_cases = ["LEGACY", "legacy", "Legacy", "PYMUPDF", "pymupdf", "PyMuPDF"]

        for test_case in test_cases:
            with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": test_case}):
                try:
                    processor = DocumentProcessorFactory.create_processor()
                    assert processor is not None
                except (ValueError, ImportError):
                    # ValueError für ungültige Typen, ImportError für fehlende Dependencies
                    pass

    def test_factory_handles_whitespace_in_env_var(self):
        """Test: Factory handhabt Whitespace in Environment Variables"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "  legacy  "}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, LegacyProcessor)


class TestProcessorFactoryBackwardsCompatibility:
    """Tests für Backwards Compatibility"""

    @pytest.mark.asyncio
    async def test_factory_processor_compatible_with_service_facade(self, tmp_path):
        """Test: Factory-Processor ist kompatibel mit der DoclingService-Fassade"""
        from services.docling_service import DoclingService

        # Die (historisch benannte) Fassade soll den Factory-Processor nutzen.
        service = DoclingService()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for backwards compatibility.")

        result = await service.process_document(
            document_id=1,
            file_path=str(test_file),
            filename="test.txt",
            mime_type="text/plain",
        )

        assert result.document_id == 1
        assert len(result.chunks) > 0

    def test_factory_processor_has_required_interface(self):
        """Test: Factory-Processor hat erforderliche Interface-Methoden"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()

            assert hasattr(processor, "process_document")
            assert callable(processor.process_document)
            assert hasattr(processor, "chunk_size")
            assert hasattr(processor, "chunk_overlap")
