"""
Unit Tests für RAG Service
"""

import pytest
import tempfile
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from services.rag_service import (
    RAGService, RAGContext, RAGQuestion, RAGExamRequest, RAGExamResponse,
    rag_service
)
from services.vector_service_mock import SearchResult


class TestRAGService:
    """Test Suite für RAG Service"""
    
    @pytest.fixture
    def rag_service_instance(self):
        """RAG Service Instanz für Tests"""
        return RAGService()
    
    @pytest.fixture
    def sample_search_results(self):
        """Sample Search Results für Tests"""
        return [
            SearchResult(
                chunk_id="doc_1_chunk_0",
                document_id=1,
                content="ExamCraft AI ist ein intelligentes System für die Erstellung von Prüfungen.",
                similarity_score=0.85,
                metadata={
                    "document_id": 1,
                    "filename": "examcraft_info.txt",
                    "chunk_index": 0,
                    "word_count": 11
                },
                chunk_index=0
            ),
            SearchResult(
                chunk_id="doc_1_chunk_1",
                document_id=1,
                content="Das System verwendet Vector Search und RAG-Technologien für bessere Fragen.",
                similarity_score=0.72,
                metadata={
                    "document_id": 1,
                    "filename": "examcraft_info.txt",
                    "chunk_index": 1,
                    "word_count": 10
                },
                chunk_index=1
            ),
            SearchResult(
                chunk_id="doc_2_chunk_0",
                document_id=2,
                content="Machine Learning Algorithmen helfen bei der automatischen Fragenerstellung.",
                similarity_score=0.68,
                metadata={
                    "document_id": 2,
                    "filename": "ml_concepts.txt",
                    "chunk_index": 0,
                    "word_count": 8
                },
                chunk_index=0
            )
        ]
    
    @pytest.fixture
    def sample_rag_context(self, sample_search_results):
        """Sample RAG Context für Tests"""
        return RAGContext(
            query="ExamCraft AI System",
            retrieved_chunks=sample_search_results,
            total_similarity_score=2.25,  # 0.85 + 0.72 + 0.68
            source_documents=[
                {"id": 1, "filename": "examcraft_info.txt", "chunks_used": 2},
                {"id": 2, "filename": "ml_concepts.txt", "chunks_used": 1}
            ],
            context_length=200
        )
    
    def test_init(self, rag_service_instance):
        """Test RAG Service Initialisierung"""
        assert rag_service_instance.claude_service is not None
        assert rag_service_instance.min_context_similarity == 0.3
        assert rag_service_instance.max_context_length == 4000
        assert len(rag_service_instance.question_templates) == 3
        assert "multiple_choice" in rag_service_instance.question_templates
        assert "open_ended" in rag_service_instance.question_templates
        assert "true_false" in rag_service_instance.question_templates
    
    def test_load_question_templates(self, rag_service_instance):
        """Test Question Templates Loading"""
        templates = rag_service_instance.question_templates
        
        # Prüfe dass alle Templates vorhanden sind
        required_templates = ["multiple_choice", "open_ended", "true_false"]
        for template_type in required_templates:
            assert template_type in templates
            assert len(templates[template_type]) > 100  # Templates sollten substantiell sein
            assert "{context}" in templates[template_type]
            assert "{topic}" in templates[template_type]
            assert "{difficulty}" in templates[template_type]
            assert "{language}" in templates[template_type]
    
    @pytest.mark.asyncio
    @patch('services.rag_service.vector_service')
    @patch('services.rag_service.document_service')
    async def test_retrieve_context_success(self, mock_doc_service, mock_vector_service, rag_service_instance, sample_search_results):
        """Test erfolgreiche Context Retrieval"""
        
        # Mock Vector Service
        mock_vector_service.similarity_search = AsyncMock(return_value=sample_search_results)
        
        # Mock Document Service
        mock_document = Mock()
        mock_document.original_filename = "test_document.txt"
        mock_document.mime_type = "text/plain"
        mock_doc_service.get_document_by_id.return_value = mock_document
        
        # Mock Database
        with patch('services.rag_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db
            mock_db.__next__ = Mock(return_value=mock_db)
            mock_db.close = Mock()
            
            context = await rag_service_instance.retrieve_context(
                query="ExamCraft AI",
                document_ids=[1, 2],
                max_chunks=5
            )
        
        # Assertions
        assert isinstance(context, RAGContext)
        assert context.query == "ExamCraft AI"
        assert len(context.retrieved_chunks) == 3
        assert context.total_similarity_score == 2.25
        assert len(context.source_documents) == 2
        assert context.context_length > 0
        
        # Verify service calls
        mock_vector_service.similarity_search.assert_called_once_with(
            query="ExamCraft AI",
            n_results=10,  # max_chunks * 2
            document_ids=[1, 2]
        )
    
    @pytest.mark.asyncio
    @patch('services.rag_service.vector_service')
    async def test_retrieve_context_no_results(self, mock_vector_service, rag_service_instance):
        """Test Context Retrieval ohne Ergebnisse"""
        
        mock_vector_service.similarity_search = AsyncMock(return_value=[])
        
        context = await rag_service_instance.retrieve_context(
            query="Nonexistent topic",
            max_chunks=5
        )
        
        assert isinstance(context, RAGContext)
        assert context.query == "Nonexistent topic"
        assert len(context.retrieved_chunks) == 0
        assert context.total_similarity_score == 0.0
        assert len(context.source_documents) == 0
        assert context.context_length == 0
    
    @pytest.mark.asyncio
    @patch('services.rag_service.vector_service')
    async def test_retrieve_context_low_similarity_filter(self, mock_vector_service, rag_service_instance):
        """Test Context Retrieval mit Similarity-Filter"""
        
        # Mock Results mit niedrigen Similarity Scores
        low_similarity_results = [
            SearchResult(
                chunk_id="doc_1_chunk_0",
                document_id=1,
                content="Irrelevant content",
                similarity_score=0.1,  # Unter min_similarity (0.3)
                metadata={"document_id": 1, "filename": "test.txt"},
                chunk_index=0
            )
        ]
        
        mock_vector_service.similarity_search = AsyncMock(return_value=low_similarity_results)
        
        context = await rag_service_instance.retrieve_context(
            query="Test query",
            max_chunks=5
        )
        
        # Sollte gefiltert werden wegen niedriger Similarity
        assert len(context.retrieved_chunks) == 0
    
    def test_prepare_context_text(self, rag_service_instance, sample_rag_context):
        """Test Context Text Preparation"""
        
        context_text = rag_service_instance._prepare_context_text(sample_rag_context)
        
        assert isinstance(context_text, str)
        assert len(context_text) > 0
        assert "ExamCraft AI ist ein intelligentes System" in context_text
        assert "[Quelle 1:" in context_text
        assert "[Quelle 2:" in context_text
        assert "---" in context_text  # Separator zwischen Chunks
    
    def test_prepare_context_text_empty(self, rag_service_instance):
        """Test Context Text Preparation mit leerem Context"""
        
        empty_context = RAGContext(
            query="test",
            retrieved_chunks=[],
            total_similarity_score=0.0,
            source_documents=[],
            context_length=0
        )
        
        context_text = rag_service_instance._prepare_context_text(empty_context)
        
        assert context_text == "Kein relevanter Kontext verfügbar."
    
    def test_prepare_context_text_truncation(self, rag_service_instance):
        """Test Context Text Truncation bei zu langem Content"""
        
        # Erstelle sehr langen Content
        long_content = "A" * 5000  # Länger als max_context_length (4000)
        
        long_chunks = [
            SearchResult(
                chunk_id="long_chunk",
                document_id=1,
                content=long_content,
                similarity_score=0.8,
                metadata={"document_id": 1, "filename": "long.txt"},
                chunk_index=0
            )
        ]
        
        long_context = RAGContext(
            query="test",
            retrieved_chunks=long_chunks,
            total_similarity_score=0.8,
            source_documents=[{"id": 1, "filename": "long.txt", "chunks_used": 1}],
            context_length=5000
        )
        
        context_text = rag_service_instance._prepare_context_text(long_context)
        
        assert len(context_text) <= rag_service_instance.max_context_length + 100  # +100 für Metadata
        assert "[Kontext gekürzt...]" in context_text
    
    @pytest.mark.asyncio
    async def test_generate_question_multiple_choice(self, rag_service_instance, sample_rag_context):
        """Test Multiple Choice Frage Generation"""
        
        # Mock Claude Service Response
        mock_claude_response = {
            "questions": [{
                "question": "Was ist ExamCraft AI?",
                "options": ["A) Ein CMS", "B) Ein Prüfungssystem", "C) Ein Browser", "D) Ein Editor"],
                "correct_answer": "B",
                "explanation": "ExamCraft AI ist ein intelligentes Prüfungssystem"
            }]
        }
        
        with patch.object(rag_service_instance.claude_service, 'generate_exam_async', return_value=mock_claude_response):
            question = await rag_service_instance.generate_question(
                topic="ExamCraft AI",
                context=sample_rag_context,
                question_type="multiple_choice",
                difficulty="medium",
                language="de"
            )
        
        assert isinstance(question, RAGQuestion)
        assert question.question_text == "Was ist ExamCraft AI?"
        assert question.question_type == "multiple_choice"
        assert len(question.options) == 4
        assert question.correct_answer == "B"
        assert question.explanation == "ExamCraft AI ist ein intelligentes Prüfungssystem"
        assert question.difficulty == "medium"
        assert len(question.source_chunks) == 3
        assert len(question.source_documents) == 2
        assert 0.0 <= question.confidence_score <= 1.0
    
    @pytest.mark.asyncio
    async def test_generate_question_open_ended(self, rag_service_instance, sample_rag_context):
        """Test Open-Ended Frage Generation"""
        
        mock_claude_response = {
            "questions": [{
                "question": "Erläutern Sie die Funktionsweise von ExamCraft AI.",
                "sample_answer": "ExamCraft AI verwendet KI-Technologien...",
                "evaluation_criteria": ["Verständnis", "Vollständigkeit", "Beispiele"]
            }]
        }
        
        with patch.object(rag_service_instance.claude_service, 'generate_exam_async', return_value=mock_claude_response):
            question = await rag_service_instance.generate_question(
                topic="ExamCraft AI",
                context=sample_rag_context,
                question_type="open_ended"
            )
        
        assert question.question_type == "open_ended"
        assert "Erläutern Sie" in question.question_text
        assert question.correct_answer == "ExamCraft AI verwendet KI-Technologien..."
        assert question.explanation == ["Verständnis", "Vollständigkeit", "Beispiele"]
    
    @pytest.mark.asyncio
    async def test_generate_question_true_false(self, rag_service_instance, sample_rag_context):
        """Test True/False Frage Generation"""
        
        mock_claude_response = {
            "questions": [{
                "statement": "ExamCraft AI ist ein intelligentes System.",
                "correct_answer": True,
                "explanation": "Laut Dokumentation ist ExamCraft AI tatsächlich ein intelligentes System."
            }]
        }
        
        with patch.object(rag_service_instance.claude_service, 'generate_exam_async', return_value=mock_claude_response):
            question = await rag_service_instance.generate_question(
                topic="ExamCraft AI",
                context=sample_rag_context,
                question_type="true_false"
            )
        
        assert question.question_type == "true_false"
        assert "ExamCraft AI ist ein intelligentes System" in question.question_text
        assert question.correct_answer == "True"
    
    @pytest.mark.asyncio
    async def test_generate_question_no_context(self, rag_service_instance):
        """Test Frage Generation ohne Context"""
        
        empty_context = RAGContext(
            query="test",
            retrieved_chunks=[],
            total_similarity_score=0.0,
            source_documents=[],
            context_length=0
        )
        
        with pytest.raises(ValueError, match="No context available"):
            await rag_service_instance.generate_question(
                topic="Test Topic",
                context=empty_context
            )
    
    @pytest.mark.asyncio
    async def test_generate_question_invalid_type(self, rag_service_instance, sample_rag_context):
        """Test Frage Generation mit ungültigem Typ"""
        
        with pytest.raises(ValueError, match="Unknown question type"):
            await rag_service_instance.generate_question(
                topic="Test Topic",
                context=sample_rag_context,
                question_type="invalid_type"
            )
    
    @pytest.mark.asyncio
    async def test_generate_question_claude_failure_fallback(self, rag_service_instance, sample_rag_context):
        """Test Fallback bei Claude API Failure"""
        
        # Mock Claude Service Failure
        with patch.object(rag_service_instance.claude_service, 'generate_exam_async', side_effect=Exception("API Error")):
            question = await rag_service_instance.generate_question(
                topic="Test Topic",
                context=sample_rag_context,
                question_type="multiple_choice"
            )
        
        # Sollte Fallback-Frage erstellen
        assert isinstance(question, RAGQuestion)
        assert question.question_type == "multiple_choice"
        assert "Test Topic" in question.question_text
        assert question.confidence_score == 0.5  # Fallback confidence
        assert len(question.options) == 4
    
    def test_convert_to_rag_question_multiple_choice(self, rag_service_instance, sample_rag_context):
        """Test Konvertierung Claude Response zu RAGQuestion (Multiple Choice)"""
        
        claude_question = {
            "question": "Test question?",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "explanation": "Test explanation"
        }
        
        rag_question = rag_service_instance._convert_to_rag_question(
            claude_question,
            "multiple_choice",
            sample_rag_context,
            "medium"
        )
        
        assert rag_question.question_text == "Test question?"
        assert rag_question.question_type == "multiple_choice"
        assert rag_question.options == ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"]
        assert rag_question.correct_answer == "A"
        assert rag_question.explanation == "Test explanation"
        assert rag_question.difficulty == "medium"
        assert len(rag_question.source_chunks) == 3
        assert len(rag_question.source_documents) == 2
    
    def test_generate_fallback_question_multiple_choice(self, rag_service_instance, sample_rag_context):
        """Test Fallback Question Generation (Multiple Choice)"""
        
        fallback_question = rag_service_instance._generate_fallback_question(
            "Test Topic",
            sample_rag_context,
            "multiple_choice",
            "hard"
        )
        
        assert fallback_question.question_type == "multiple_choice"
        assert "Test Topic" in fallback_question.question_text
        assert len(fallback_question.options) == 4
        assert fallback_question.correct_answer == "A"
        assert "Fallback" in fallback_question.explanation
        assert fallback_question.difficulty == "hard"
        assert fallback_question.confidence_score == 0.5
    
    def test_generate_fallback_question_open_ended(self, rag_service_instance, sample_rag_context):
        """Test Fallback Question Generation (Open Ended)"""
        
        fallback_question = rag_service_instance._generate_fallback_question(
            "Machine Learning",
            sample_rag_context,
            "open_ended",
            "easy"
        )
        
        assert fallback_question.question_type == "open_ended"
        assert "Machine Learning" in fallback_question.question_text
        assert "Erläutern Sie" in fallback_question.question_text
        assert fallback_question.difficulty == "easy"
    
    @pytest.mark.asyncio
    @patch('services.rag_service.rag_service.retrieve_context')
    @patch('services.rag_service.rag_service.generate_question')
    async def test_generate_rag_exam_success(self, mock_generate_question, mock_retrieve_context, rag_service_instance, sample_rag_context):
        """Test vollständige RAG Exam Generation"""
        
        # Mock Context Retrieval
        mock_retrieve_context.return_value = sample_rag_context
        
        # Mock Question Generation
        mock_questions = [
            RAGQuestion(
                question_text="Test Question 1?",
                question_type="multiple_choice",
                options=["A) 1", "B) 2", "C) 3", "D) 4"],
                correct_answer="A",
                difficulty="medium",
                source_chunks=["chunk_1"],
                source_documents=["doc1.txt"],
                confidence_score=0.8
            ),
            RAGQuestion(
                question_text="Test Question 2?",
                question_type="open_ended",
                correct_answer="Sample answer",
                difficulty="medium",
                source_chunks=["chunk_2"],
                source_documents=["doc1.txt"],
                confidence_score=0.7
            )
        ]
        mock_generate_question.side_effect = mock_questions
        
        # Test Request
        request = RAGExamRequest(
            topic="Test Topic",
            question_count=2,
            question_types=["multiple_choice", "open_ended"],
            difficulty="medium"
        )
        
        response = await rag_service_instance.generate_rag_exam(request)
        
        # Assertions
        assert isinstance(response, RAGExamResponse)
        assert response.topic == "Test Topic"
        assert len(response.questions) == 2
        assert response.questions[0].question_type == "multiple_choice"
        assert response.questions[1].question_type == "open_ended"
        assert response.generation_time > 0
        assert "total_questions" in response.quality_metrics
        assert response.quality_metrics["total_questions"] == 2
    
    @pytest.mark.asyncio
    @patch('services.rag_service.rag_service.retrieve_context')
    async def test_generate_rag_exam_no_context(self, mock_retrieve_context, rag_service_instance):
        """Test RAG Exam Generation ohne Context"""
        
        # Mock leeren Context
        empty_context = RAGContext(
            query="test",
            retrieved_chunks=[],
            total_similarity_score=0.0,
            source_documents=[],
            context_length=0
        )
        mock_retrieve_context.return_value = empty_context
        
        request = RAGExamRequest(
            topic="Nonexistent Topic",
            question_count=1
        )
        
        with pytest.raises(ValueError, match="No relevant context found"):
            await rag_service_instance.generate_rag_exam(request)
    
    def test_calculate_quality_metrics(self, rag_service_instance, sample_rag_context):
        """Test Quality Metrics Calculation"""
        
        questions = [
            RAGQuestion(
                question_text="Q1",
                question_type="multiple_choice",
                confidence_score=0.8,
                source_chunks=["chunk_1", "chunk_2"],
                source_documents=["doc1.txt"]
            ),
            RAGQuestion(
                question_text="Q2", 
                question_type="open_ended",
                confidence_score=0.6,
                source_chunks=["chunk_2", "chunk_3"],
                source_documents=["doc1.txt"]
            )
        ]
        
        metrics = rag_service_instance._calculate_quality_metrics(questions, sample_rag_context)
        
        assert metrics["total_questions"] == 2
        assert metrics["average_confidence"] == 0.7  # (0.8 + 0.6) / 2
        assert metrics["question_type_distribution"]["multiple_choice"] == 1
        assert metrics["question_type_distribution"]["open_ended"] == 1
        assert metrics["context_chunks_used"] == 3
        assert metrics["total_context_length"] == 200
        assert "average_similarity_score" in metrics
    
    def test_calculate_quality_metrics_empty(self, rag_service_instance, sample_rag_context):
        """Test Quality Metrics mit leerer Fragenliste"""
        
        metrics = rag_service_instance._calculate_quality_metrics([], sample_rag_context)
        
        assert "error" in metrics
        assert metrics["error"] == "No questions to analyze"


class TestRAGDataClasses:
    """Test Suite für RAG Data Classes"""
    
    def test_rag_context_creation(self):
        """Test RAGContext Erstellung"""
        context = RAGContext(
            query="test query",
            retrieved_chunks=[],
            total_similarity_score=1.5,
            source_documents=[{"id": 1, "filename": "test.txt"}],
            context_length=100
        )
        
        assert context.query == "test query"
        assert context.retrieved_chunks == []
        assert context.total_similarity_score == 1.5
        assert len(context.source_documents) == 1
        assert context.context_length == 100
    
    def test_rag_question_creation(self):
        """Test RAGQuestion Erstellung"""
        question = RAGQuestion(
            question_text="Test question?",
            question_type="multiple_choice",
            options=["A) 1", "B) 2"],
            correct_answer="A",
            explanation="Test explanation",
            difficulty="medium",
            source_chunks=["chunk_1"],
            source_documents=["doc1.txt"],
            confidence_score=0.85
        )
        
        assert question.question_text == "Test question?"
        assert question.question_type == "multiple_choice"
        assert len(question.options) == 2
        assert question.correct_answer == "A"
        assert question.explanation == "Test explanation"
        assert question.difficulty == "medium"
        assert question.source_chunks == ["chunk_1"]
        assert question.source_documents == ["doc1.txt"]
        assert question.confidence_score == 0.85
    
    def test_rag_exam_request_creation(self):
        """Test RAGExamRequest Erstellung"""
        request = RAGExamRequest(
            topic="Machine Learning",
            document_ids=[1, 2, 3],
            question_count=10,
            question_types=["multiple_choice", "open_ended"],
            difficulty="hard",
            language="en",
            context_chunks_per_question=5
        )
        
        assert request.topic == "Machine Learning"
        assert request.document_ids == [1, 2, 3]
        assert request.question_count == 10
        assert request.question_types == ["multiple_choice", "open_ended"]
        assert request.difficulty == "hard"
        assert request.language == "en"
        assert request.context_chunks_per_question == 5
    
    def test_rag_exam_response_creation(self):
        """Test RAGExamResponse Erstellung"""
        context = RAGContext(
            query="test",
            retrieved_chunks=[],
            total_similarity_score=0.0,
            source_documents=[],
            context_length=0
        )
        
        response = RAGExamResponse(
            exam_id="test_exam_123",
            topic="Test Topic",
            questions=[],
            context_summary=context,
            generation_time=1.5,
            quality_metrics={"total_questions": 0}
        )
        
        assert response.exam_id == "test_exam_123"
        assert response.topic == "Test Topic"
        assert response.questions == []
        assert response.context_summary == context
        assert response.generation_time == 1.5
        assert response.quality_metrics["total_questions"] == 0
