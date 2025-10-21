"""
Integration Tests für RAG System
Tests für die vollständige Integration von RAG Service, Vector Service und Claude API
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from services.rag_service import rag_service, RAGExamRequest
from services.vector_service_mock import vector_service, SearchResult
from services.document_service import document_service
from services.claude_service import ClaudeService
from models.document import Document, DocumentStatus
from database import get_db


class TestRAGIntegration:
    """Integration Tests für RAG System"""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock Database Session"""
        session = Mock(spec=Session)
        session.close = Mock()
        return session
    
    @pytest.fixture
    def sample_document(self):
        """Sample Document für Tests"""
        doc = Mock(spec=Document)
        doc.id = 1
        doc.original_filename = "integration_test.txt"
        doc.mime_type = "text/plain"
        doc.status = DocumentStatus.PROCESSED
        doc.user_id = "demo_user"
        doc.vector_collection = "test_collection"
        doc.doc_metadata = {
            "total_chunks": 3,
            "embedding_model": "mock-model",
            "processing_time": 1.5
        }
        return doc
    
    @pytest.fixture
    def sample_vector_chunks(self):
        """Sample Vector Chunks für Tests"""
        return [
            SearchResult(
                chunk_id="doc_1_chunk_0",
                document_id=1,
                content="ExamCraft AI ist ein intelligentes System zur automatischen Erstellung von Prüfungen. Es nutzt moderne KI-Technologien.",
                similarity_score=0.89,
                metadata={
                    "document_id": 1,
                    "filename": "integration_test.txt",
                    "chunk_index": 0,
                    "page_number": 1,
                    "word_count": 15
                },
                chunk_index=0
            ),
            SearchResult(
                chunk_id="doc_1_chunk_1", 
                document_id=1,
                content="Das System verwendet Vector Search und Retrieval-Augmented Generation (RAG) für bessere Fragenerstellung.",
                similarity_score=0.82,
                metadata={
                    "document_id": 1,
                    "filename": "integration_test.txt",
                    "chunk_index": 1,
                    "page_number": 1,
                    "word_count": 13
                },
                chunk_index=1
            ),
            SearchResult(
                chunk_id="doc_1_chunk_2",
                document_id=1,
                content="Machine Learning Algorithmen analysieren Dokumenteninhalte und generieren kontextbasierte Prüfungsfragen.",
                similarity_score=0.75,
                metadata={
                    "document_id": 1,
                    "filename": "integration_test.txt",
                    "chunk_index": 2,
                    "page_number": 1,
                    "word_count": 11
                },
                chunk_index=2
            )
        ]
    
    @pytest.mark.asyncio
    async def test_full_rag_pipeline_success(self, mock_db_session, sample_document, sample_vector_chunks):
        """Test vollständige RAG Pipeline - Success Case"""
        
        # Mock Vector Service
        with patch.object(vector_service, 'similarity_search', return_value=sample_vector_chunks):
            
            # Mock Document Service
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                # Mock Database
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    # Mock Claude Service Response
                    mock_claude_response = {
                        "questions": [
                            {
                                "question": "Was ist ExamCraft AI?",
                                "options": [
                                    "A) Ein Content Management System",
                                    "B) Ein intelligentes Prüfungssystem", 
                                    "C) Ein Web Browser",
                                    "D) Ein Text Editor"
                                ],
                                "correct_answer": "B",
                                "explanation": "ExamCraft AI ist laut Dokumentation ein intelligentes System zur automatischen Erstellung von Prüfungen."
                            },
                            {
                                "question": "Erläutern Sie die Funktionsweise von ExamCraft AI.",
                                "sample_answer": "ExamCraft AI verwendet Vector Search und RAG-Technologien, um aus Dokumenteninhalten kontextbasierte Prüfungsfragen zu generieren.",
                                "evaluation_criteria": ["Verständnis der KI-Technologien", "Erklärung des RAG-Prozesses", "Beispiele für Anwendungen"]
                            }
                        ]
                    }
                    
                    with patch.object(rag_service.claude_service, 'generate_exam_async', return_value=mock_claude_response):
                        
                        # Erstelle RAG Request
                        request = RAGExamRequest(
                            topic="ExamCraft AI System",
                            document_ids=[1],
                            question_count=2,
                            question_types=["multiple_choice", "open_ended"],
                            difficulty="medium",
                            language="de",
                            context_chunks_per_question=2
                        )
                        
                        # Führe RAG Exam Generation durch
                        response = await rag_service.generate_rag_exam(request)
                        
                        # Assertions
                        assert response.topic == "ExamCraft AI System"
                        assert len(response.questions) == 2
                        
                        # Prüfe Multiple Choice Frage
                        mc_question = response.questions[0]
                        assert mc_question.question_type == "multiple_choice"
                        assert "Was ist ExamCraft AI?" in mc_question.question_text
                        assert len(mc_question.options) == 4
                        assert mc_question.correct_answer == "B"
                        assert len(mc_question.source_chunks) > 0
                        assert len(mc_question.source_documents) > 0
                        assert mc_question.confidence_score > 0.5
                        
                        # Prüfe Open-Ended Frage
                        oe_question = response.questions[1]
                        assert oe_question.question_type == "open_ended"
                        assert "Erläutern Sie" in oe_question.question_text
                        assert "Vector Search" in oe_question.correct_answer
                        assert isinstance(oe_question.explanation, list)
                        
                        # Prüfe Context Summary
                        assert response.context_summary.query == "ExamCraft AI System"
                        assert len(response.context_summary.retrieved_chunks) > 0
                        assert response.context_summary.total_similarity_score > 2.0
                        assert len(response.context_summary.source_documents) == 1
                        
                        # Prüfe Quality Metrics
                        assert response.quality_metrics["total_questions"] == 2
                        assert response.quality_metrics["average_confidence"] > 0.5
                        assert response.quality_metrics["source_coverage"] > 0.0
                        assert "multiple_choice" in response.quality_metrics["question_type_distribution"]
                        assert "open_ended" in response.quality_metrics["question_type_distribution"]
                        
                        # Prüfe Generation Time
                        assert response.generation_time > 0
                        assert response.exam_id.startswith("rag_exam_")
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_with_vector_service_failure(self, mock_db_session, sample_document):
        """Test RAG Pipeline mit Vector Service Failure"""
        
        # Mock Vector Service Failure
        with patch.object(vector_service, 'similarity_search', side_effect=Exception("Vector Service Error")):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    request = RAGExamRequest(
                        topic="Test Topic",
                        document_ids=[1],
                        question_count=1
                    )
                    
                    # Sollte Exception werfen
                    with pytest.raises(Exception, match="Vector Service Error"):
                        await rag_service.generate_rag_exam(request)
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_with_claude_service_fallback(self, mock_db_session, sample_document, sample_vector_chunks):
        """Test RAG Pipeline mit Claude Service Fallback"""
        
        with patch.object(vector_service, 'similarity_search', return_value=sample_vector_chunks):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    # Mock Claude Service Failure
                    with patch.object(rag_service.claude_service, 'generate_exam_async', side_effect=Exception("Claude API Error")):
                        
                        request = RAGExamRequest(
                            topic="Fallback Test",
                            document_ids=[1],
                            question_count=1,
                            question_types=["multiple_choice"]
                        )
                        
                        response = await rag_service.generate_rag_exam(request)
                        
                        # Sollte Fallback-Fragen generieren
                        assert len(response.questions) == 1
                        question = response.questions[0]
                        assert question.question_type == "multiple_choice"
                        assert "Fallback Test" in question.question_text
                        assert question.confidence_score == 0.5  # Fallback confidence
                        assert len(question.options) == 4
                        assert "Fallback" in question.explanation
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_no_relevant_context(self, mock_db_session, sample_document):
        """Test RAG Pipeline ohne relevanten Context"""
        
        # Mock Vector Service mit leeren Results
        with patch.object(vector_service, 'similarity_search', return_value=[]):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    request = RAGExamRequest(
                        topic="Irrelevant Topic",
                        document_ids=[1],
                        question_count=1
                    )
                    
                    # Sollte ValueError werfen wegen fehlendem Context
                    with pytest.raises(ValueError, match="No relevant context found"):
                        await rag_service.generate_rag_exam(request)
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_low_similarity_filtering(self, mock_db_session, sample_document):
        """Test RAG Pipeline mit Low Similarity Filtering"""
        
        # Mock Vector Results mit niedrigen Similarity Scores
        low_similarity_chunks = [
            SearchResult(
                chunk_id="low_sim_chunk",
                document_id=1,
                content="Irrelevant content with low similarity",
                similarity_score=0.1,  # Unter min_similarity (0.3)
                metadata={"document_id": 1, "filename": "test.txt"},
                chunk_index=0
            )
        ]
        
        with patch.object(vector_service, 'similarity_search', return_value=low_similarity_chunks):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    request = RAGExamRequest(
                        topic="Test Topic",
                        document_ids=[1],
                        question_count=1
                    )
                    
                    # Sollte ValueError werfen wegen gefiltertem Context
                    with pytest.raises(ValueError, match="No relevant context found"):
                        await rag_service.generate_rag_exam(request)
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_multiple_documents(self, mock_db_session, sample_vector_chunks):
        """Test RAG Pipeline mit mehreren Dokumenten"""
        
        # Mock mehrere Dokumente
        doc1 = Mock(spec=Document)
        doc1.id = 1
        doc1.original_filename = "doc1.txt"
        doc1.mime_type = "text/plain"
        doc1.status = DocumentStatus.PROCESSED
        
        doc2 = Mock(spec=Document)
        doc2.id = 2
        doc2.original_filename = "doc2.txt"
        doc2.mime_type = "text/plain"
        doc2.status = DocumentStatus.PROCESSED
        
        # Mock Vector Results von mehreren Dokumenten
        multi_doc_chunks = sample_vector_chunks + [
            SearchResult(
                chunk_id="doc_2_chunk_0",
                document_id=2,
                content="Zusätzlicher Content aus zweitem Dokument für besseren Context.",
                similarity_score=0.78,
                metadata={
                    "document_id": 2,
                    "filename": "doc2.txt",
                    "chunk_index": 0
                },
                chunk_index=0
            )
        ]
        
        def mock_get_document_by_id(doc_id, db):
            if doc_id == 1:
                return doc1
            elif doc_id == 2:
                return doc2
            return None
        
        with patch.object(vector_service, 'similarity_search', return_value=multi_doc_chunks):
            
            with patch.object(document_service, 'get_document_by_id', side_effect=mock_get_document_by_id):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    mock_claude_response = {
                        "questions": [{
                            "question": "Multi-Document Question?",
                            "options": ["A) Yes", "B) No", "C) Maybe", "D) Unknown"],
                            "correct_answer": "A",
                            "explanation": "Based on multiple documents"
                        }]
                    }
                    
                    with patch.object(rag_service.claude_service, 'generate_exam_async', return_value=mock_claude_response):
                        
                        request = RAGExamRequest(
                            topic="Multi-Document Test",
                            document_ids=[1, 2],
                            question_count=1,
                            question_types=["multiple_choice"]
                        )
                        
                        response = await rag_service.generate_rag_exam(request)
                        
                        # Prüfe dass Context von beiden Dokumenten verwendet wird
                        assert len(response.context_summary.source_documents) == 2
                        source_filenames = [doc["filename"] for doc in response.context_summary.source_documents]
                        assert "doc1.txt" in source_filenames
                        assert "doc2.txt" in source_filenames
                        
                        # Prüfe dass Frage generiert wurde
                        assert len(response.questions) == 1
                        question = response.questions[0]
                        assert len(question.source_documents) > 0
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_different_question_types(self, mock_db_session, sample_document, sample_vector_chunks):
        """Test RAG Pipeline mit verschiedenen Fragetypen"""
        
        with patch.object(vector_service, 'similarity_search', return_value=sample_vector_chunks):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    # Mock verschiedene Claude Responses für verschiedene Fragetypen
                    def mock_claude_generate(request_data):
                        custom_prompt = request_data.get("custom_prompt", "")
                        
                        if "Multiple-Choice-Frage" in custom_prompt:
                            return {
                                "questions": [{
                                    "question": "MC Question?",
                                    "options": ["A) 1", "B) 2", "C) 3", "D) 4"],
                                    "correct_answer": "A",
                                    "explanation": "MC Explanation"
                                }]
                            }
                        elif "offene Frage" in custom_prompt:
                            return {
                                "questions": [{
                                    "question": "Open Question?",
                                    "sample_answer": "Open Answer",
                                    "evaluation_criteria": ["Criterion 1", "Criterion 2"]
                                }]
                            }
                        elif "Wahr/Falsch-Frage" in custom_prompt:
                            return {
                                "questions": [{
                                    "statement": "True/False Statement",
                                    "correct_answer": True,
                                    "explanation": "TF Explanation"
                                }]
                            }
                        
                        return {"questions": []}
                    
                    with patch.object(rag_service.claude_service, 'generate_exam_async', side_effect=mock_claude_generate):
                        
                        request = RAGExamRequest(
                            topic="Question Types Test",
                            document_ids=[1],
                            question_count=3,
                            question_types=["multiple_choice", "open_ended", "true_false"]
                        )
                        
                        response = await rag_service.generate_rag_exam(request)
                        
                        # Prüfe dass alle Fragetypen generiert wurden
                        assert len(response.questions) == 3
                        
                        question_types = [q.question_type for q in response.questions]
                        assert "multiple_choice" in question_types
                        assert "open_ended" in question_types
                        assert "true_false" in question_types
                        
                        # Prüfe Quality Metrics
                        type_distribution = response.quality_metrics["question_type_distribution"]
                        assert type_distribution["multiple_choice"] == 1
                        assert type_distribution["open_ended"] == 1
                        assert type_distribution["true_false"] == 1
    
    @pytest.mark.asyncio
    async def test_rag_pipeline_performance_metrics(self, mock_db_session, sample_document, sample_vector_chunks):
        """Test RAG Pipeline Performance Metrics"""
        
        with patch.object(vector_service, 'similarity_search', return_value=sample_vector_chunks):
            
            with patch.object(document_service, 'get_document_by_id', return_value=sample_document):
                
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_get_db.return_value = mock_db_session
                    mock_db_session.__next__ = Mock(return_value=mock_db_session)
                    
                    mock_claude_response = {
                        "questions": [{
                            "question": "Performance Test Question?",
                            "options": ["A) Fast", "B) Slow", "C) Medium", "D) Unknown"],
                            "correct_answer": "A",
                            "explanation": "Performance is good"
                        }]
                    }
                    
                    with patch.object(rag_service.claude_service, 'generate_exam_async', return_value=mock_claude_response):
                        
                        import time
                        start_time = time.time()
                        
                        request = RAGExamRequest(
                            topic="Performance Test",
                            document_ids=[1],
                            question_count=1
                        )
                        
                        response = await rag_service.generate_rag_exam(request)
                        
                        end_time = time.time()
                        actual_time = end_time - start_time
                        
                        # Prüfe dass Generation Time gemessen wird
                        assert response.generation_time > 0
                        assert response.generation_time <= actual_time + 0.1  # Kleine Toleranz
                        
                        # Prüfe Quality Metrics
                        metrics = response.quality_metrics
                        assert "average_confidence" in metrics
                        assert "source_coverage" in metrics
                        assert "context_chunks_used" in metrics
                        assert "total_context_length" in metrics
                        assert "average_similarity_score" in metrics
                        
                        # Prüfe dass Metriken sinnvolle Werte haben
                        assert 0.0 <= metrics["average_confidence"] <= 1.0
                        assert 0.0 <= metrics["source_coverage"] <= 1.0
                        assert metrics["context_chunks_used"] > 0
                        assert metrics["total_context_length"] > 0
                        assert metrics["average_similarity_score"] > 0.0


class TestRAGServiceIntegrationEdgeCases:
    """Edge Cases für RAG Service Integration"""
    
    @pytest.mark.asyncio
    async def test_context_truncation_integration(self):
        """Test Context Truncation in vollständiger Pipeline"""
        
        # Erstelle sehr lange Chunks
        long_chunks = []
        for i in range(10):
            long_content = "A" * 1000  # Jeder Chunk 1000 Zeichen
            chunk = SearchResult(
                chunk_id=f"long_chunk_{i}",
                document_id=1,
                content=long_content,
                similarity_score=0.8,
                metadata={"document_id": 1, "filename": "long.txt"},
                chunk_index=i
            )
            long_chunks.append(chunk)
        
        mock_doc = Mock()
        mock_doc.original_filename = "long_document.txt"
        mock_doc.mime_type = "text/plain"
        
        with patch.object(vector_service, 'similarity_search', return_value=long_chunks):
            with patch.object(document_service, 'get_document_by_id', return_value=mock_doc):
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    mock_db.__next__ = Mock(return_value=mock_db)
                    mock_db.close = Mock()
                    
                    # Teste Context Retrieval
                    context = await rag_service.retrieve_context(
                        query="Long Content Test",
                        max_chunks=10
                    )
                    
                    # Context sollte gekürzt werden
                    context_text = rag_service._prepare_context_text(context)
                    assert len(context_text) <= rag_service.max_context_length + 100
                    assert "[Kontext gekürzt...]" in context_text
    
    @pytest.mark.asyncio
    async def test_concurrent_rag_requests(self):
        """Test gleichzeitige RAG Requests"""
        
        mock_chunks = [
            SearchResult(
                chunk_id="concurrent_chunk",
                document_id=1,
                content="Concurrent test content",
                similarity_score=0.8,
                metadata={"document_id": 1, "filename": "concurrent.txt"},
                chunk_index=0
            )
        ]
        
        mock_doc = Mock()
        mock_doc.original_filename = "concurrent.txt"
        mock_doc.mime_type = "text/plain"
        
        async def run_rag_request():
            with patch.object(vector_service, 'similarity_search', return_value=mock_chunks):
                with patch.object(document_service, 'get_document_by_id', return_value=mock_doc):
                    with patch('services.rag_service.get_db') as mock_get_db:
                        mock_db = Mock()
                        mock_get_db.return_value = mock_db
                        mock_db.__next__ = Mock(return_value=mock_db)
                        mock_db.close = Mock()
                        
                        context = await rag_service.retrieve_context(
                            query=f"Concurrent Test {asyncio.current_task().get_name()}",
                            max_chunks=1
                        )
                        return len(context.retrieved_chunks)
        
        # Führe mehrere gleichzeitige Requests aus
        tasks = [run_rag_request() for _ in range(3)]
        results = await asyncio.gather(*tasks)
        
        # Alle Requests sollten erfolgreich sein
        assert all(result == 1 for result in results)
    
    @pytest.mark.asyncio
    async def test_memory_usage_large_context(self):
        """Test Memory Usage bei großem Context"""
        
        # Erstelle viele Chunks
        many_chunks = []
        for i in range(100):
            chunk = SearchResult(
                chunk_id=f"memory_chunk_{i}",
                document_id=1,
                content=f"Memory test content chunk {i} with some additional text to make it longer.",
                similarity_score=0.5 + (i % 50) / 100,  # Variiere Similarity
                metadata={"document_id": 1, "filename": "memory_test.txt", "chunk_index": i},
                chunk_index=i
            )
            many_chunks.append(chunk)
        
        mock_doc = Mock()
        mock_doc.original_filename = "memory_test.txt"
        mock_doc.mime_type = "text/plain"
        
        with patch.object(vector_service, 'similarity_search', return_value=many_chunks):
            with patch.object(document_service, 'get_document_by_id', return_value=mock_doc):
                with patch('services.rag_service.get_db') as mock_get_db:
                    mock_db = Mock()
                    mock_get_db.return_value = mock_db
                    mock_db.__next__ = Mock(return_value=mock_db)
                    mock_db.close = Mock()
                    
                    # Teste mit verschiedenen max_chunks Werten
                    for max_chunks in [5, 10, 20]:
                        context = await rag_service.retrieve_context(
                            query="Memory Test",
                            max_chunks=max_chunks,
                            min_similarity=0.3
                        )
                        
                        # Sollte nicht mehr als max_chunks zurückgeben
                        assert len(context.retrieved_chunks) <= max_chunks
                        
                        # Alle Chunks sollten über min_similarity liegen
                        for chunk in context.retrieved_chunks:
                            assert chunk.similarity_score >= 0.3
