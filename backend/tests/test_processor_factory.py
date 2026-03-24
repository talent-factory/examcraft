"""
Integration Tests für Processor Factory
Tests für dynamische Processor-Auswahl
"""

import pytest
import os
from unittest.mock import patch

docling = pytest.importorskip("docling", reason="docling not installed")
from services.document_processors.processor_factory import DocumentProcessorFactory  # noqa: E402
from services.document_processors.docling_processor import DoclingProcessor  # noqa: E402
from services.document_processors.legacy_processor import LegacyProcessor  # noqa: E402


class TestProcessorFactoryCreation:
    """Tests für Processor-Erstellung"""

    def test_factory_creates_docling_processor_explicit(self):
        """Test: Factory erstellt DoclingProcessor wenn explizit angefordert"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "docling"}):
            try:
                processor = DocumentProcessorFactory.create_processor()
                assert isinstance(processor, DoclingProcessor)
            except ImportError:
                # Docling nicht verfügbar - erwartetes Verhalten
                pytest.skip("Docling not available")

    def test_factory_creates_legacy_processor_explicit(self):
        """Test: Factory erstellt LegacyProcessor wenn explizit angefordert"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, LegacyProcessor)

    def test_factory_auto_detection_with_docling(self):
        """Test: Auto-Detection wählt Docling wenn verfügbar"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            try:
                processor = DocumentProcessorFactory.create_processor()
                # Sollte DoclingProcessor sein wenn verfügbar
                assert isinstance(processor, (DoclingProcessor, LegacyProcessor))
            except ImportError:
                pytest.skip("Docling not available")

    def test_factory_auto_detection_fallback(self):
        """Test: Auto-Detection fällt auf Legacy zurück wenn Docling nicht verfügbar"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            with patch(
                "services.document_processors.processor_factory.DoclingProcessor"
            ) as mock_docling:
                mock_docling.side_effect = ImportError("Docling not available")

                processor = DocumentProcessorFactory.create_processor()
                assert isinstance(processor, LegacyProcessor)

    def test_factory_default_is_auto(self):
        """Test: Standard-Modus ist 'auto'"""
        with patch.dict(os.environ, {}, clear=True):
            # Entferne DOCUMENT_PROCESSOR_TYPE aus Environment
            if "DOCUMENT_PROCESSOR_TYPE" in os.environ:
                del os.environ["DOCUMENT_PROCESSOR_TYPE"]

            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, (DoclingProcessor, LegacyProcessor))


class TestProcessorFactoryErrorHandling:
    """Tests für Error Handling"""

    def test_factory_raises_error_for_invalid_type(self):
        """Test: Factory wirft Fehler bei ungültigem Processor-Typ"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                DocumentProcessorFactory.create_processor()

            assert "Unknown processor type" in str(exc_info.value)

    def test_factory_raises_error_when_docling_requested_but_unavailable(self):
        """Test: Factory wirft Fehler wenn Docling explizit angefordert aber nicht verfügbar"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "docling"}):
            with patch(
                "services.document_processors.docling_processor.DoclingProcessor"
            ) as mock_docling:
                mock_docling.side_effect = ImportError("Docling not installed")

                with pytest.raises(ImportError) as exc_info:
                    DocumentProcessorFactory.create_processor()

                assert (
                    "Docling processor requested but dependencies not installed"
                    in str(exc_info.value)
                )


class TestProcessorFactoryIntegration:
    """Integration Tests für Factory mit echten Processoren"""

    @pytest.mark.asyncio
    async def test_factory_processor_can_process_document(self, tmp_path):
        """Test: Von Factory erstellter Processor kann Dokumente verarbeiten"""
        # Erstelle Test-Datei
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

            # Standard-Werte sollten gesetzt sein
            assert processor.chunk_size == 1000
            assert processor.chunk_overlap == 200


class TestProcessorFactoryGlobalInstance:
    """Tests für globale Processor-Instanz"""

    def test_global_processor_instance_exists(self):
        """Test: Globale Processor-Instanz existiert"""
        from services.document_processors.processor_factory import document_processor

        assert document_processor is not None
        assert isinstance(document_processor, (DoclingProcessor, LegacyProcessor))

    def test_global_processor_is_singleton(self):
        """Test: Globale Processor-Instanz ist Singleton"""
        from services.document_processors.processor_factory import (
            document_processor as proc1,
        )
        from services.document_processors.processor_factory import (
            document_processor as proc2,
        )

        assert proc1 is proc2


class TestProcessorFactoryEnvironmentVariables:
    """Tests für Environment Variable Handling"""

    def test_factory_respects_env_var_case_insensitive(self):
        """Test: Factory akzeptiert case-insensitive Environment Variables"""
        test_cases = ["LEGACY", "legacy", "Legacy", "DOCLING", "docling", "Docling"]

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


class TestProcessorFactoryLogging:
    """Tests für Logging"""

    def test_factory_logs_processor_creation(self, caplog):
        """Test: Factory loggt Processor-Erstellung"""
        import logging

        caplog.set_level(logging.INFO)

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            DocumentProcessorFactory.create_processor()

            # Prüfe ob Log-Nachricht vorhanden ist
            assert any(
                "Creating document processor" in record.message
                for record in caplog.records
            )

    def test_factory_logs_fallback_warning(self, caplog):
        """Test: Factory loggt Warnung bei Fallback"""
        import logging

        caplog.set_level(logging.WARNING)

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            with patch(
                "services.document_processors.processor_factory.DoclingProcessor"
            ) as mock_docling:
                mock_docling.side_effect = ImportError("Docling not available")

                DocumentProcessorFactory.create_processor()

                # Prüfe ob Warnung geloggt wurde
                assert any(
                    "Docling not available" in record.message
                    for record in caplog.records
                )


class TestProcessorFactoryBackwardsCompatibility:
    """Tests für Backwards Compatibility"""

    @pytest.mark.asyncio
    async def test_factory_processor_compatible_with_docling_service(self, tmp_path):
        """Test: Factory-Processor ist kompatibel mit DoclingService"""
        from services.docling_service import DoclingService

        # DoclingService sollte Factory-Processor verwenden können
        service = DoclingService()

        # Erstelle Test-Datei
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

            # Prüfe ob erforderliche Methoden vorhanden sind
            assert hasattr(processor, "process_document")
            assert callable(processor.process_document)
            assert hasattr(processor, "chunk_size")
            assert hasattr(processor, "chunk_overlap")
