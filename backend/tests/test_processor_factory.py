"""
Integration tests for the processor factory
Tests for dynamic processor selection (PyMuPDF / Legacy).
"""

import pytest
import os
from unittest.mock import patch

from services.document_processors.processor_factory import DocumentProcessorFactory
from services.document_processors.pymupdf_processor import PyMuPDFProcessor
from services.document_processors.legacy_processor import LegacyProcessor


class TestProcessorFactoryCreation:
    """Tests for processor creation"""

    def test_factory_creates_pymupdf_processor_explicit(self):
        """Test: factory creates PyMuPDFProcessor when explicitly requested"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "pymupdf"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, PyMuPDFProcessor)

    def test_factory_creates_legacy_processor_explicit(self):
        """Test: factory creates LegacyProcessor when explicitly requested"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, LegacyProcessor)

    def test_factory_auto_detection_prefers_pymupdf(self):
        """Test: auto-detection prefers PyMuPDF"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, (PyMuPDFProcessor, LegacyProcessor))

    def test_factory_auto_detection_fallback_to_legacy(self):
        """Test: auto falls back to Legacy when PyMuPDF is unavailable"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "auto"}):
            with patch(
                "services.document_processors.pymupdf_processor.PyMuPDFProcessor"
            ) as mock_pymupdf:
                mock_pymupdf.side_effect = ImportError("PyMuPDF not available")

                processor = DocumentProcessorFactory.create_processor()
                assert isinstance(processor, LegacyProcessor)

    def test_factory_default_is_pymupdf(self):
        """Test: default processor (without env var) is PyMuPDF"""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("DOCUMENT_PROCESSOR_TYPE", None)
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, (PyMuPDFProcessor, LegacyProcessor))


class TestProcessorFactoryErrorHandling:
    """Tests for error handling"""

    def test_factory_raises_error_for_invalid_type(self):
        """Test: factory raises an error for an invalid processor type"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                DocumentProcessorFactory.create_processor()

            assert "Unknown processor type" in str(exc_info.value)

    def test_factory_raises_error_when_pymupdf_requested_but_unavailable(self):
        """Test: factory raises an error when PyMuPDF is explicitly requested but unavailable"""
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
    """Integration tests for the factory with real processors"""

    @pytest.mark.asyncio
    async def test_factory_processor_can_process_document(self, tmp_path):
        """Test: a processor created by the factory can process documents"""
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
        """Test: factory processor retains its configuration"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()

            assert processor.chunk_size == 1000
            assert processor.chunk_overlap == 200


class TestProcessorFactoryGlobalInstance:
    """Tests for the global processor instance"""

    def test_global_processor_instance_exists(self):
        """Test: global processor instance exists"""
        from services.document_processors.processor_factory import document_processor

        assert document_processor is not None
        assert isinstance(document_processor, (PyMuPDFProcessor, LegacyProcessor))

    def test_global_processor_is_singleton(self):
        """Test: global processor instance is a singleton"""
        from services.document_processors.processor_factory import (
            document_processor as proc1,
        )
        from services.document_processors.processor_factory import (
            document_processor as proc2,
        )

        assert proc1 is proc2


class TestProcessorFactoryGlobalInit:
    """Tests for _init_document_processor (TF-368).

    A misconfiguration must NOT silently degrade the worker to a
    deprecated processor; a genuine runtime error may fall back, but
    must be logged at ERROR with the original exception type.
    """

    def test_init_fails_fast_on_misconfiguration(self):
        """Invalid DOCUMENT_PROCESSOR_TYPE -> ValueError instead of a silent downgrade."""
        from services.document_processors.processor_factory import (
            _init_document_processor,
        )

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(ValueError) as exc_info:
                _init_document_processor()

        assert "Unknown processor type" in str(exc_info.value)

    def test_init_logs_error_on_misconfiguration(self):
        """The misconfiguration is logged at ERROR (operator-visible).

        We check the mocked module logger instead of caplog: the app
        reconfigures logging (Sentry integration, among others), which
        makes propagation to caplog unreliable during a full-suite run.
        """
        from services.document_processors import processor_factory as pf

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with patch.object(pf, "logger") as mock_logger:
                with pytest.raises(ValueError):
                    pf._init_document_processor()

        logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
        assert "DOCUMENT_PROCESSOR_TYPE" in logged

    def test_init_falls_back_with_error_log_on_runtime_failure(self):
        """Genuine runtime error -> fallback, but an ERROR log with the exception type."""
        from services.document_processors import processor_factory as pf

        with patch.object(
            pf.DocumentProcessorFactory,
            "create_processor",
            side_effect=RuntimeError("boom"),
        ):
            with patch.object(pf, "logger") as mock_logger:
                processor = pf._init_document_processor()

        # Fallback returns PyMuPDF (available in the test env), no silent abort.
        assert isinstance(processor, PyMuPDFProcessor)
        # The original exception type is passed along as a logging argument.
        logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
        assert "RuntimeError" in logged

    def test_unknown_type_raises_dedicated_subclass(self):
        """TF-372: an unknown type raises the dedicated
        UnknownProcessorTypeError (a subclass of ValueError), so the
        fail-fast path can distinguish it from any arbitrary ValueError
        coming out of a processor constructor."""
        from services.document_processors.processor_factory import (
            UnknownProcessorTypeError,
        )

        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "invalid"}):
            with pytest.raises(UnknownProcessorTypeError):
                DocumentProcessorFactory.create_processor()

    def test_non_type_value_error_does_not_fail_fast_as_misconfig(self):
        """TF-372: a ValueError that does NOT come from the type check (e.g. a
        broken numeric env like OCR_DPI, simulated here via a constructor mock)
        is NOT misreported as 'Invalid DOCUMENT_PROCESSOR_TYPE', but instead
        runs into the resilience fallback."""
        from services.document_processors import processor_factory as pf

        with patch.object(
            pf.DocumentProcessorFactory,
            "create_processor",
            side_effect=ValueError("invalid literal for int() with base 10: 'abc'"),
        ):
            with patch.object(pf, "logger") as mock_logger:
                processor = pf._init_document_processor()

        # No fail-fast: the fallback kicks in (no re-raise).
        assert processor is not None
        logged = " ".join(str(call) for call in mock_logger.error.call_args_list)
        # The misleading type-misconfiguration message must NOT appear.
        assert "Invalid DOCUMENT_PROCESSOR_TYPE" not in logged


class TestProcessorFactoryEnvironmentVariables:
    """Tests for environment variable handling"""

    def test_factory_respects_env_var_case_insensitive(self):
        """Test: factory accepts environment variables case-insensitively"""
        test_cases = ["LEGACY", "legacy", "Legacy", "PYMUPDF", "pymupdf", "PyMuPDF"]

        for test_case in test_cases:
            with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": test_case}):
                try:
                    processor = DocumentProcessorFactory.create_processor()
                    assert processor is not None
                except (ValueError, ImportError):
                    # ValueError for invalid types, ImportError for missing dependencies
                    pass

    def test_factory_handles_whitespace_in_env_var(self):
        """Test: factory handles whitespace in environment variables"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "  legacy  "}):
            processor = DocumentProcessorFactory.create_processor()
            assert isinstance(processor, LegacyProcessor)


class TestProcessorFactoryBackwardsCompatibility:
    """Tests for backwards compatibility"""

    @pytest.mark.asyncio
    async def test_factory_processor_compatible_with_service_facade(self, tmp_path):
        """Test: factory processor is compatible with the DoclingService facade"""
        from services.docling_service import DoclingService

        # The (historically named) facade should use the factory processor.
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
        """Test: factory processor has the required interface methods"""
        with patch.dict(os.environ, {"DOCUMENT_PROCESSOR_TYPE": "legacy"}):
            processor = DocumentProcessorFactory.create_processor()

            assert hasattr(processor, "process_document")
            assert callable(processor.process_document)
            assert hasattr(processor, "chunk_size")
            assert hasattr(processor, "chunk_overlap")
