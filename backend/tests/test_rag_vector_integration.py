"""
Integration Tests für RAG Service mit Vector Service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.rag_service import rag_service, RAGContext
from services.qdrant_vector_service import SearchResult


class TestRAGVectorIntegration:
    """Test Suite für RAG Service + Vector Service Integration"""
    
    @pytest.fixture
    def mock_vector_service(self):
        """Mock Vector Service für Tests"""
        mock_service = Mock()
        mock_service.similarity_search = AsyncMock()
        return mock_service
    
    @pytest.fixture
    def sample_search_results(self):
        """Sample Search Results"""
        return [
            SearchResult(
                chunk_id="chunk_1",
                document_id=1,
                content="Heap-Sort ist ein Sortieralgorithmus mit O(n log n) Zeitkomplexität.",
                similarity_score=0.85
            ),
            SearchResult(
                chunk_id="chunk_2",
                document_id=1,
                content="Der Heapify-Prozess stellt die Heap-Eigenschaft wieder her.",
                similarity_score=0.78
            ),
            SearchResult(
                chunk_id="chunk_3",
                document_id=1,
                content="Ein Max-Heap hat den größten Wert an der Wurzel.",
                similarity_score=0.72
            )
        ]
    
    @pytest.mark.asyncio
    async def test_rag_service_uses_real_vector_service(self, mock_vector_service, sample_search_results):
        """Test dass RAG Service den echten Vector Service verwendet"""
        mock_vector_service.similarity_search.return_value = sample_search_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            context = await rag_service.retrieve_context(
                query="Heap-Sort",
                document_ids=[1],
                max_chunks=3,
                min_similarity=0.5
            )
            
            # Verify vector service was called
            mock_vector_service.similarity_search.assert_called_once()
            call_args = mock_vector_service.similarity_search.call_args
            assert call_args[1]['query'] == "Heap-Sort"
            assert call_args[1]['document_ids'] == [1]
            
            # Verify context was created correctly
            assert context.query == "Heap-Sort"
            assert len(context.retrieved_chunks) == 3
            assert context.total_similarity_score > 0
    
    @pytest.mark.asyncio
    async def test_rag_service_filters_by_similarity(self, mock_vector_service, sample_search_results):
        """Test dass RAG Service nach Similarity Score filtert"""
        mock_vector_service.similarity_search.return_value = sample_search_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            # Set high similarity threshold
            context = await rag_service.retrieve_context(
                query="Heap-Sort",
                document_ids=[1],
                max_chunks=5,
                min_similarity=0.80  # Only first result should pass
            )
            
            # Should only return results with similarity >= 0.80
            assert len(context.retrieved_chunks) == 1
            assert context.retrieved_chunks[0].similarity_score >= 0.80
    
    @pytest.mark.asyncio
    async def test_rag_service_handles_no_results(self, mock_vector_service):
        """Test dass RAG Service leere Ergebnisse korrekt behandelt"""
        mock_vector_service.similarity_search.return_value = []
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            context = await rag_service.retrieve_context(
                query="Nonexistent Topic",
                document_ids=[1],
                max_chunks=5,
                min_similarity=0.5
            )
            
            # Should return empty context
            assert context.query == "Nonexistent Topic"
            assert len(context.retrieved_chunks) == 0
            assert context.total_similarity_score == 0.0
            assert len(context.source_documents) == 0
    
    @pytest.mark.asyncio
    async def test_rag_service_respects_max_chunks(self, mock_vector_service):
        """Test dass RAG Service max_chunks Limit respektiert"""
        # Create 10 search results
        many_results = [
            SearchResult(
                chunk_id=f"chunk_{i}",
                document_id=1,
                content=f"Content {i}",
                similarity_score=0.9 - (i * 0.05)
            )
            for i in range(10)
        ]
        mock_vector_service.similarity_search.return_value = many_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            context = await rag_service.retrieve_context(
                query="Test",
                document_ids=[1],
                max_chunks=3,  # Limit to 3
                min_similarity=0.0
            )
            
            # Should only return 3 chunks
            assert len(context.retrieved_chunks) <= 3
    
    @pytest.mark.asyncio
    async def test_rag_service_aggregates_source_documents(self, mock_vector_service):
        """Test dass RAG Service Source Documents korrekt aggregiert"""
        # Results from multiple documents
        multi_doc_results = [
            SearchResult(chunk_id="c1", document_id=1, content="Content 1", similarity_score=0.9),
            SearchResult(chunk_id="c2", document_id=2, content="Content 2", similarity_score=0.85),
            SearchResult(chunk_id="c3", document_id=1, content="Content 3", similarity_score=0.8),
            SearchResult(chunk_id="c4", document_id=3, content="Content 4", similarity_score=0.75)
        ]
        mock_vector_service.similarity_search.return_value = multi_doc_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            with patch('services.rag_service.get_db'):
                context = await rag_service.retrieve_context(
                    query="Test",
                    max_chunks=10,
                    min_similarity=0.0
                )
                
                # Should have chunks from 3 different documents
                doc_ids = set(chunk.document_id for chunk in context.retrieved_chunks)
                assert len(doc_ids) == 3
                assert doc_ids == {1, 2, 3}
    
    @pytest.mark.asyncio
    async def test_rag_service_calculates_total_similarity(self, mock_vector_service, sample_search_results):
        """Test dass RAG Service total_similarity_score korrekt berechnet"""
        mock_vector_service.similarity_search.return_value = sample_search_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            context = await rag_service.retrieve_context(
                query="Heap-Sort",
                max_chunks=10,
                min_similarity=0.0
            )
            
            # Calculate expected total
            expected_total = sum(r.similarity_score for r in sample_search_results)
            
            assert abs(context.total_similarity_score - expected_total) < 0.01
    
    @pytest.mark.asyncio
    async def test_rag_service_without_document_filter(self, mock_vector_service, sample_search_results):
        """Test RAG Service ohne document_ids Filter"""
        mock_vector_service.similarity_search.return_value = sample_search_results
        
        with patch('services.rag_service.vector_service', mock_vector_service):
            context = await rag_service.retrieve_context(
                query="Heap-Sort",
                document_ids=None,  # No filter
                max_chunks=5,
                min_similarity=0.5
            )
            
            # Verify vector service was called without document filter
            call_args = mock_vector_service.similarity_search.call_args
            assert call_args[1]['document_ids'] is None
            
            # Should still return results
            assert len(context.retrieved_chunks) > 0

