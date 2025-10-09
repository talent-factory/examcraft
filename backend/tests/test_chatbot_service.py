"""
Unit Tests für ChatBot Service
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from services.chatbot_service import DocumentChatBotService


class TestDocumentChatBotService:
    """Test Suite für ChatBot Service"""
    
    @pytest.fixture
    def chatbot_service(self):
        """ChatBot Service Instanz für Tests"""
        return DocumentChatBotService()
    
    @pytest.fixture
    def sample_chat_history(self):
        """Sample Chat-Historie"""
        return [
            {"role": "user", "content": "Was ist Heap-Sort?"},
            {"role": "assistant", "content": "Heap-Sort ist ein Sortieralgorithmus..."}
        ]
    
    @pytest.fixture
    def sample_rag_sources(self):
        """Sample RAG Sources"""
        return [
            {
                "document_id": 1,
                "chunk_id": "chunk_1",
                "score": 0.85,
                "metadata": {"title": "Algorithmik Buch", "page": 142}
            },
            {
                "document_id": 1,
                "chunk_id": "chunk_2",
                "score": 0.78,
                "metadata": {"title": "Algorithmik Buch", "page": 145}
            }
        ]
    
    def test_chatbot_service_initialization(self, chatbot_service):
        """Test ChatBot Service Initialisierung"""
        assert chatbot_service is not None
        assert chatbot_service.vector_service is not None
    
    def test_demo_mode_when_no_api_key(self):
        """Test Demo-Modus wenn kein API Key vorhanden"""
        with patch.dict('os.environ', {}, clear=True):
            service = DocumentChatBotService()
            assert service.demo_mode is True
            assert service.agent is None
    
    def test_system_prompt_generation(self, chatbot_service):
        """Test System Prompt Generierung"""
        if not chatbot_service.demo_mode:
            prompt = chatbot_service._build_system_prompt()
            
            assert "Dokument" in prompt
            assert "Quellen" in prompt
            assert "Markdown" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_response_demo_mode(self):
        """Test Antwortgenerierung im Demo-Modus"""
        with patch.dict('os.environ', {}, clear=True):
            service = DocumentChatBotService()
            
            response = await service.generate_response(
                user_message="Test Frage",
                document_ids=[1],
                chat_history=[],
                max_context_chunks=5
            )
            
            assert response is not None
            assert "content" in response
            assert "sources" in response
            assert "confidence" in response
            assert response["confidence"] == 0.0
            assert "Demo-Modus" in response["content"]
    
    @pytest.mark.asyncio
    async def test_retrieve_relevant_context(self, chatbot_service, sample_rag_sources):
        """Test RAG Context Retrieval"""
        # Mock Vector Service
        mock_search_results = [
            Mock(
                content="Heap-Sort ist ein Sortieralgorithmus mit O(n log n) Zeitkomplexität.",
                document_id=1,
                chunk_id="chunk_1",
                similarity_score=0.85,
                metadata={"title": "Algorithmik Buch", "page": 142}
            ),
            Mock(
                content="Der Heapify-Prozess stellt die Heap-Eigenschaft wieder her.",
                document_id=1,
                chunk_id="chunk_2",
                similarity_score=0.78,
                metadata={"title": "Algorithmik Buch", "page": 145}
            )
        ]
        
        with patch.object(chatbot_service.vector_service, 'similarity_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_search_results
            
            context, sources = await chatbot_service.retrieve_relevant_context(
                query="Heap-Sort",
                document_ids=[1],
                max_chunks=5
            )
            
            # Verify context was retrieved
            assert context is not None
            assert len(context) > 0
            assert "Heap-Sort" in context
            
            # Verify sources
            assert len(sources) == 2
            assert sources[0]["document_id"] == 1
            assert sources[0]["score"] == 0.85
            
            # Verify vector service was called correctly
            mock_search.assert_called_once()
            call_kwargs = mock_search.call_args[1]
            assert call_kwargs["query"] == "Heap-Sort"
            assert call_kwargs["document_ids"] == [1]
            assert call_kwargs["top_k"] == 5
    
    def test_format_chat_history(self, chatbot_service, sample_chat_history):
        """Test Chat-Historie Formatierung"""
        formatted = chatbot_service._format_chat_history(sample_chat_history)
        
        assert len(formatted) == 2
        assert formatted[0] == ("user", "Was ist Heap-Sort?")
        assert formatted[1] == ("assistant", "Heap-Sort ist ein Sortieralgorithmus...")
    
    def test_build_enhanced_prompt(self, chatbot_service, sample_rag_sources):
        """Test Enhanced Prompt Building"""
        context = "Heap-Sort ist ein Sortieralgorithmus..."
        
        prompt = chatbot_service._build_enhanced_prompt(
            user_message="Erkläre Heap-Sort",
            document_context=context,
            sources=sample_rag_sources
        )
        
        assert "DOKUMENTENKONTEXT" in prompt
        assert "VERFÜGBARE QUELLEN" in prompt
        assert "BENUTZERFRAGE" in prompt
        assert "Erkläre Heap-Sort" in prompt
        assert context in prompt
    
    def test_enrich_sources(self, chatbot_service, sample_rag_sources):
        """Test Source Enrichment"""
        citations = [
            {"source_number": 1, "text": "Quelle 1"},
            {"source_number": 2, "text": "Quelle 2"}
        ]
        
        enriched = chatbot_service._enrich_sources(citations, sample_rag_sources)
        
        assert len(enriched) == 2
        assert enriched[0]["document_id"] == 1
        assert enriched[0]["score"] == 0.85
    
    def test_enrich_sources_fallback(self, chatbot_service, sample_rag_sources):
        """Test Source Enrichment Fallback wenn keine Citations"""
        enriched = chatbot_service._enrich_sources([], sample_rag_sources)
        
        # Should use RAG sources as fallback
        assert len(enriched) == 2
        assert enriched[0]["document_id"] == 1
    
    @pytest.mark.asyncio
    async def test_error_handling_in_generate_response(self, chatbot_service):
        """Test Error Handling bei Antwortgenerierung"""
        # Mock Vector Service to raise error
        with patch.object(chatbot_service.vector_service, 'similarity_search', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Vector search failed")
            
            response = await chatbot_service.generate_response(
                user_message="Test",
                document_ids=[1],
                chat_history=[],
                max_context_chunks=5
            )
            
            # Should fall back to demo response
            assert response is not None
            assert "content" in response
            assert response["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_retrieve_context_with_no_results(self, chatbot_service):
        """Test Context Retrieval wenn keine Ergebnisse"""
        with patch.object(chatbot_service.vector_service, 'similarity_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []
            
            context, sources = await chatbot_service.retrieve_relevant_context(
                query="Nonexistent Topic",
                document_ids=[1],
                max_chunks=5
            )
            
            assert "Keine relevanten Informationen" in context
            assert len(sources) == 0

