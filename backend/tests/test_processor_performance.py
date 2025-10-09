"""
Performance Tests für Document Processors
Vergleich zwischen Docling und Legacy Processor
"""

import pytest
import time
import asyncio
from pathlib import Path
from unittest.mock import patch
from services.document_processors.docling_processor import DoclingProcessor
from services.document_processors.legacy_processor import LegacyProcessor


@pytest.fixture
def small_text_file(tmp_path):
    """Kleine Text-Datei (100 Wörter)"""
    text = " ".join([f"word{i}" for i in range(100)])
    file_path = tmp_path / "small.txt"
    file_path.write_text(text)
    return str(file_path)


@pytest.fixture
def medium_text_file(tmp_path):
    """Mittlere Text-Datei (1000 Wörter)"""
    text = " ".join([f"word{i}" for i in range(1000)])
    file_path = tmp_path / "medium.txt"
    file_path.write_text(text)
    return str(file_path)


@pytest.fixture
def large_text_file(tmp_path):
    """Große Text-Datei (10000 Wörter)"""
    text = " ".join([f"word{i}" for i in range(10000)])
    file_path = tmp_path / "large.txt"
    file_path.write_text(text)
    return str(file_path)


@pytest.fixture
def structured_markdown_file(tmp_path):
    """Strukturierte Markdown-Datei mit Sections"""
    content = []
    for i in range(20):
        content.append(f"# Section {i}\n\n")
        content.append(f"## Subsection {i}.1\n\n")
        content.append(" ".join([f"word{j}" for j in range(50)]))
        content.append("\n\n")
    
    file_path = tmp_path / "structured.md"
    file_path.write_text("".join(content))
    return str(file_path)


class TestLegacyProcessorPerformance:
    """Performance Tests für LegacyProcessor"""
    
    @pytest.mark.asyncio
    async def test_small_file_processing_time(self, small_text_file):
        """Test: Processing-Zeit für kleine Datei"""
        processor = LegacyProcessor()
        
        start = time.time()
        result = await processor.process_document(
            document_id=1,
            file_path=small_text_file,
            filename="small.txt",
            mime_type="text/plain"
        )
        duration = time.time() - start
        
        assert duration < 1.0  # Sollte < 1 Sekunde sein
        assert result.processing_time < 1.0
    
    @pytest.mark.asyncio
    async def test_medium_file_processing_time(self, medium_text_file):
        """Test: Processing-Zeit für mittlere Datei"""
        processor = LegacyProcessor()
        
        start = time.time()
        result = await processor.process_document(
            document_id=1,
            file_path=medium_text_file,
            filename="medium.txt",
            mime_type="text/plain"
        )
        duration = time.time() - start
        
        assert duration < 2.0  # Sollte < 2 Sekunden sein
        assert result.processing_time < 2.0
    
    @pytest.mark.asyncio
    async def test_large_file_processing_time(self, large_text_file):
        """Test: Processing-Zeit für große Datei"""
        processor = LegacyProcessor()
        
        start = time.time()
        result = await processor.process_document(
            document_id=1,
            file_path=large_text_file,
            filename="large.txt",
            mime_type="text/plain"
        )
        duration = time.time() - start
        
        assert duration < 5.0  # Sollte < 5 Sekunden sein
        assert result.processing_time < 5.0
    
    @pytest.mark.asyncio
    async def test_chunking_performance(self, large_text_file):
        """Test: Chunking-Performance"""
        processor = LegacyProcessor()
        
        result = await processor.process_document(
            document_id=1,
            file_path=large_text_file,
            filename="large.txt",
            mime_type="text/plain"
        )
        
        # Sollte mehrere Chunks erstellen
        assert result.total_chunks > 1
        
        # Jeder Chunk sollte Metadaten haben
        for chunk in result.chunks:
            assert chunk.chunk_index is not None
            assert chunk.metadata is not None


class TestDoclingProcessorPerformance:
    """Performance Tests für DoclingProcessor (wenn verfügbar)"""
    
    @pytest.mark.asyncio
    async def test_docling_small_file_processing(self, small_text_file):
        """Test: Docling Processing-Zeit für kleine Datei"""
        try:
            processor = DoclingProcessor()
        except ImportError:
            pytest.skip("Docling not available")
        
        # Mock DocumentConverter für Performance-Test
        with patch.object(processor.converter, 'convert') as mock_convert:
            from unittest.mock import MagicMock
            mock_result = MagicMock()
            mock_result.document.export_to_markdown.return_value = "Test content"
            mock_result.document.tables = []
            mock_convert.return_value = mock_result
            
            start = time.time()
            result = await processor.process_document(
                document_id=1,
                file_path=small_text_file,
                filename="small.txt",
                mime_type="text/plain"
            )
            duration = time.time() - start
            
            assert duration < 2.0  # Sollte < 2 Sekunden sein


class TestProcessorComparison:
    """Vergleichstests zwischen Processoren"""
    
    @pytest.mark.asyncio
    async def test_legacy_vs_docling_small_file(self, small_text_file):
        """Test: Vergleich Legacy vs Docling für kleine Datei"""
        legacy_processor = LegacyProcessor()
        
        # Legacy Processing
        legacy_start = time.time()
        legacy_result = await legacy_processor.process_document(
            document_id=1,
            file_path=small_text_file,
            filename="small.txt",
            mime_type="text/plain"
        )
        legacy_duration = time.time() - legacy_start
        
        # Docling Processing (wenn verfügbar)
        try:
            docling_processor = DoclingProcessor()
            
            with patch.object(docling_processor.converter, 'convert') as mock_convert:
                from unittest.mock import MagicMock
                mock_result = MagicMock()
                mock_result.document.export_to_markdown.return_value = legacy_result.chunks[0].content
                mock_result.document.tables = []
                mock_convert.return_value = mock_result
                
                docling_start = time.time()
                docling_result = await docling_processor.process_document(
                    document_id=1,
                    file_path=small_text_file,
                    filename="small.txt",
                    mime_type="text/plain"
                )
                docling_duration = time.time() - docling_start
                
                # Beide sollten schnell sein
                assert legacy_duration < 2.0
                assert docling_duration < 3.0
        except ImportError:
            pytest.skip("Docling not available for comparison")
    
    @pytest.mark.asyncio
    async def test_chunk_quality_comparison(self, structured_markdown_file):
        """Test: Vergleich der Chunk-Qualität"""
        legacy_processor = LegacyProcessor()
        
        legacy_result = await legacy_processor.process_document(
            document_id=1,
            file_path=structured_markdown_file,
            filename="structured.md",
            mime_type="text/markdown"
        )
        
        # Legacy sollte funktionale Chunks erstellen
        assert legacy_result.total_chunks > 0
        assert all(chunk.content for chunk in legacy_result.chunks)
        
        # Docling sollte semantische Chunks erstellen (wenn verfügbar)
        try:
            docling_processor = DoclingProcessor()
            
            with patch.object(docling_processor.converter, 'convert') as mock_convert:
                from unittest.mock import MagicMock
                
                # Lese tatsächlichen Content
                with open(structured_markdown_file, 'r') as f:
                    content = f.read()
                
                mock_result = MagicMock()
                mock_result.document.export_to_markdown.return_value = content
                mock_result.document.tables = []
                mock_convert.return_value = mock_result
                
                docling_result = await docling_processor.process_document(
                    document_id=1,
                    file_path=structured_markdown_file,
                    filename="structured.md",
                    mime_type="text/markdown"
                )
                
                # Docling könnte mehr oder weniger Chunks haben (semantisch)
                assert docling_result.total_chunks > 0
        except ImportError:
            pytest.skip("Docling not available for comparison")


class TestMemoryUsage:
    """Tests für Speicherverbrauch"""
    
    @pytest.mark.asyncio
    async def test_legacy_memory_efficiency(self, large_text_file):
        """Test: Legacy Processor Speicher-Effizienz"""
        import tracemalloc
        
        processor = LegacyProcessor()
        
        tracemalloc.start()
        
        result = await processor.process_document(
            document_id=1,
            file_path=large_text_file,
            filename="large.txt",
            mime_type="text/plain"
        )
        
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        # Peak Memory sollte < 50 MB sein für 10000 Wörter
        assert peak < 50 * 1024 * 1024  # 50 MB
    
    @pytest.mark.asyncio
    async def test_chunk_memory_overhead(self, large_text_file):
        """Test: Speicher-Overhead durch Chunking"""
        processor = LegacyProcessor()
        
        result = await processor.process_document(
            document_id=1,
            file_path=large_text_file,
            filename="large.txt",
            mime_type="text/plain"
        )
        
        # Berechne Gesamtgröße aller Chunks
        total_chunk_size = sum(len(chunk.content) for chunk in result.chunks)
        
        # Lese Original-Dateigröße
        with open(large_text_file, 'r') as f:
            original_size = len(f.read())
        
        # Overhead sollte < 50% sein (wegen Überlappung)
        overhead = (total_chunk_size - original_size) / original_size
        assert overhead < 0.5  # < 50% Overhead


class TestConcurrentProcessing:
    """Tests für gleichzeitige Verarbeitung"""
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self, small_text_file, medium_text_file):
        """Test: Gleichzeitige Verarbeitung mehrerer Dateien"""
        processor = LegacyProcessor()
        
        start = time.time()
        
        # Verarbeite beide Dateien gleichzeitig
        results = await asyncio.gather(
            processor.process_document(
                document_id=1,
                file_path=small_text_file,
                filename="small.txt",
                mime_type="text/plain"
            ),
            processor.process_document(
                document_id=2,
                file_path=medium_text_file,
                filename="medium.txt",
                mime_type="text/plain"
            )
        )
        
        duration = time.time() - start
        
        # Sollte schneller sein als sequentielle Verarbeitung
        assert len(results) == 2
        assert all(r.total_chunks > 0 for r in results)
        
        # Gesamtzeit sollte < 3 Sekunden sein
        assert duration < 3.0

