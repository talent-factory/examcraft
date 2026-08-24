"""
Unit tests for LegacyProcessor
Tests for fallback document processing
"""

import pytest
from services.document_processors.legacy_processor import LegacyProcessor
from services.docling_service import ProcessedDocument


@pytest.fixture
def legacy_processor():
    """Fixture for LegacyProcessor"""
    return LegacyProcessor(chunk_size=1000, chunk_overlap=200)


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Fixture for a temporary PDF file"""
    pdf_file = tmp_path / "test.pdf"
    # Minimal PDF with text
    pdf_content = b"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> /MediaBox [0 0 612 792] /Contents 4 0 R >>
endobj
4 0 obj
<< /Length 44 >>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<< /Size 5 /Root 1 0 R >>
startxref
410
%%EOF"""
    pdf_file.write_bytes(pdf_content)
    return str(pdf_file)


@pytest.fixture
def sample_text_path(tmp_path):
    """Fixture for a temporary text file"""
    text_file = tmp_path / "test.txt"
    text_file.write_text(
        "This is a test document.\nWith multiple lines.\nAnd some content."
    )
    return str(text_file)


@pytest.fixture
def sample_markdown_path(tmp_path):
    """Fixture for a temporary markdown file"""
    md_file = tmp_path / "test.md"
    md_file.write_text("# Test Document\n\n## Section 1\n\nSome **bold** text.")
    return str(md_file)


class TestLegacyProcessorInitialization:
    """Tests for processor initialization"""

    def test_processor_initialization(self, legacy_processor):
        """Test: processor is initialized correctly"""
        assert legacy_processor.chunk_size == 1000
        assert legacy_processor.chunk_overlap == 200
        assert len(legacy_processor.supported_types) > 0

    def test_supported_mime_types(self, legacy_processor):
        """Test: supported MIME types"""
        assert "application/pdf" in legacy_processor.supported_types
        assert "text/plain" in legacy_processor.supported_types
        assert "text/markdown" in legacy_processor.supported_types


class TestLegacyProcessorPDFProcessing:
    """Tests for PDF processing"""

    @pytest.mark.asyncio
    async def test_process_pdf_success(self, legacy_processor, sample_pdf_path):
        """Test: successful PDF processing"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_pdf_path,
            filename="test.pdf",
            mime_type="application/pdf",
        )

        assert isinstance(result, ProcessedDocument)
        assert result.document_id == 1
        assert result.filename == "test.pdf"
        assert result.mime_type == "application/pdf"
        assert result.total_chunks > 0
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_pdf_metadata_extraction(self, legacy_processor, sample_pdf_path):
        """Test: PDF metadata extraction"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_pdf_path,
            filename="test.pdf",
            mime_type="application/pdf",
        )

        assert "pages" in result.metadata
        assert result.total_pages is not None


class TestLegacyProcessorTextProcessing:
    """Tests for text processing"""

    @pytest.mark.asyncio
    async def test_process_text_success(self, legacy_processor, sample_text_path):
        """Test: successful text processing"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert isinstance(result, ProcessedDocument)
        assert result.document_id == 1
        assert result.filename == "test.txt"
        assert result.mime_type == "text/plain"
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_text_metadata(self, legacy_processor, sample_text_path):
        """Test: text metadata"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert "lines" in result.metadata
        assert "words" in result.metadata
        assert "characters" in result.metadata
        assert "encoding" in result.metadata


class TestLegacyProcessorMarkdownProcessing:
    """Tests for markdown processing"""

    @pytest.mark.asyncio
    async def test_process_markdown_success(
        self, legacy_processor, sample_markdown_path
    ):
        """Test: successful markdown processing"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_markdown_path,
            filename="test.md",
            mime_type="text/markdown",
        )

        assert isinstance(result, ProcessedDocument)
        assert result.document_id == 1
        assert result.filename == "test.md"
        assert len(result.chunks) > 0

    @pytest.mark.asyncio
    async def test_markdown_to_plain_text(self, legacy_processor, sample_markdown_path):
        """Test: markdown is converted to plain text"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_markdown_path,
            filename="test.md",
            mime_type="text/markdown",
        )

        # Markdown formatting should be removed
        content = result.chunks[0].content
        assert "Test Document" in content
        assert "Section 1" in content


class TestLegacyProcessorChunking:
    """Tests for text chunking"""

    def test_create_chunks_small_text(self, legacy_processor):
        """Test: chunking with small text"""
        text = "This is a small test document."
        chunks = legacy_processor._create_chunks(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_create_chunks_large_text(self, legacy_processor):
        """Test: chunking with large text"""
        # Create text with 2000 words
        text = " ".join([f"word{i}" for i in range(2000)])
        chunks = legacy_processor._create_chunks(text)

        assert len(chunks) > 1

        # Check chunk sizes
        for chunk in chunks:
            word_count = len(chunk.content.split())
            assert word_count <= legacy_processor.chunk_size

    def test_chunk_overlap(self, legacy_processor):
        """Test: chunk overlap"""
        # Create text with 1500 words
        text = " ".join([f"word{i}" for i in range(1500)])
        chunks = legacy_processor._create_chunks(text)

        if len(chunks) > 1:
            # Check whether overlap exists
            first_chunk_words = chunks[0].content.split()
            second_chunk_words = chunks[1].content.split()

            # The last words of the first chunk should be in the second chunk
            overlap_words = first_chunk_words[-legacy_processor.chunk_overlap :]
            second_chunk_start = second_chunk_words[: legacy_processor.chunk_overlap]

            # At least some words should overlap
            assert any(word in second_chunk_start for word in overlap_words)

    def test_empty_text_chunking(self, legacy_processor):
        """Test: chunking with empty text"""
        chunks = legacy_processor._create_chunks("")
        assert len(chunks) == 0


class TestLegacyProcessorErrorHandling:
    """Tests for error handling"""

    @pytest.mark.asyncio
    async def test_unsupported_mime_type(self, legacy_processor, tmp_path):
        """Test: Unsupported MIME Type"""
        test_file = tmp_path / "test.xyz"
        test_file.write_text("test content")

        with pytest.raises(ValueError) as exc_info:
            await legacy_processor.process_document(
                document_id=1,
                file_path=str(test_file),
                filename="test.xyz",
                mime_type="application/octet-stream",
            )

        assert "Unsupported MIME type" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_nonexistent_file(self, legacy_processor):
        """Test: nonexistent file"""
        with pytest.raises(Exception):
            await legacy_processor.process_document(
                document_id=1,
                file_path="/nonexistent/file.pdf",
                filename="nonexistent.pdf",
                mime_type="application/pdf",
            )


class TestLegacyProcessorPerformance:
    """Tests for performance"""

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, legacy_processor, sample_text_path):
        """Test: processing time is recorded"""
        result = await legacy_processor.process_document(
            document_id=1,
            file_path=sample_text_path,
            filename="test.txt",
            mime_type="text/plain",
        )

        assert result.processing_time is not None
        assert result.processing_time > 0

    @pytest.mark.asyncio
    async def test_large_document_performance(self, legacy_processor, tmp_path):
        """Test: performance with a large document"""
        # Create a large text file (10000 words)
        large_text = " ".join([f"word{i}" for i in range(10000)])
        large_file = tmp_path / "large.txt"
        large_file.write_text(large_text)

        result = await legacy_processor.process_document(
            document_id=1,
            file_path=str(large_file),
            filename="large.txt",
            mime_type="text/plain",
        )

        # Should create multiple chunks
        assert result.total_chunks > 1
        assert len(result.chunks) > 1

        # Processing should be fast (< 5 seconds)
        assert result.processing_time < 5.0


class TestLegacyProcessorEncodingFallback:
    """Tests: encoding fallback for .txt and .md (UTF-8 -> Latin-1)."""

    @pytest.mark.asyncio
    async def test_text_latin1_fallback(self, legacy_processor, tmp_path):
        """Latin-1 encoded .txt must decode without crashing."""
        txt_file = tmp_path / "umlaute.txt"
        txt_file.write_bytes("Über Ärger und Öl".encode("latin-1"))

        result = await legacy_processor.process_document(
            document_id=1,
            file_path=str(txt_file),
            filename="umlaute.txt",
            mime_type="text/plain",
        )

        full_text = " ".join(c.content for c in result.chunks)
        assert "Über" in full_text
        assert result.metadata["encoding"] == "latin-1"

    @pytest.mark.asyncio
    async def test_markdown_latin1_fallback(self, legacy_processor, tmp_path):
        """Latin-1 encoded .md must not raise (regression: previously hard UTF-8)."""
        md_file = tmp_path / "umlaute.md"
        md_file.write_bytes("# Überschrift\n\nÄÖÜ ßeispieltext.\n".encode("latin-1"))

        result = await legacy_processor.process_document(
            document_id=2,
            file_path=str(md_file),
            filename="umlaute.md",
            mime_type="text/markdown",
        )

        full_text = " ".join(c.content for c in result.chunks)
        assert "Überschrift" in full_text
        assert result.metadata["encoding"] == "latin-1"

    @pytest.mark.asyncio
    async def test_binary_renamed_as_md_is_rejected(self, legacy_processor, tmp_path):
        """A binary file renamed `.md` must not silently vectorize as mojibake."""
        md_file = tmp_path / "fake.md"
        # Random-ish binary: predominantly control bytes that Latin-1 maps to
        # control characters → fails the printable-character ratio check.
        md_file.write_bytes(bytes(range(256)) * 4)

        with pytest.raises(ValueError, match="(?i)not.*text|binary"):
            await legacy_processor.process_document(
                document_id=3,
                file_path=str(md_file),
                filename="fake.md",
                mime_type="text/markdown",
            )
