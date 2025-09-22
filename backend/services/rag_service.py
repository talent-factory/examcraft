"""
RAG (Retrieval-Augmented Generation) Service für ExamCraft AI
Kombiniert Vector Search mit Claude API für dokumentenbasierte Fragenerstellung
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio
import json
from datetime import datetime

from services.vector_service_mock import vector_service, SearchResult
from services.claude_service import ClaudeService
from services.document_service import document_service

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Kontext-Informationen für RAG-basierte Fragenerstellung"""
    query: str
    retrieved_chunks: List[SearchResult]
    total_similarity_score: float
    source_documents: List[Dict[str, Any]]
    context_length: int


@dataclass
class RAGQuestion:
    """Eine RAG-generierte Prüfungsfrage mit Quellenangaben"""
    question_text: str
    question_type: str  # "multiple_choice", "open_ended", "true_false"
    options: Optional[List[str]] = None  # Für Multiple Choice
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: str = "medium"  # "easy", "medium", "hard"
    source_chunks: List[str] = None  # Chunk IDs als Quellen
    source_documents: List[str] = None  # Document Namen
    confidence_score: float = 0.0


@dataclass
class RAGExamRequest:
    """Request für RAG-basierte Prüfungserstellung"""
    topic: str
    document_ids: Optional[List[int]] = None  # Spezifische Dokumente
    question_count: int = 5
    question_types: List[str] = None  # ["multiple_choice", "open_ended"]
    difficulty: str = "medium"
    language: str = "de"
    context_chunks_per_question: int = 3


@dataclass
class RAGExamResponse:
    """Response für RAG-basierte Prüfung"""
    exam_id: str
    topic: str
    questions: List[RAGQuestion]
    context_summary: RAGContext
    generation_time: float
    quality_metrics: Dict[str, Any]


class RAGService:
    """Service für Retrieval-Augmented Generation von Prüfungsfragen"""
    
    def __init__(self):
        """Initialisiere RAG Service"""
        self.claude_service = ClaudeService()
        self.min_context_similarity = 0.3  # Mindest-Similarity für Context
        self.max_context_length = 4000  # Max Zeichen für Context
        self.question_templates = self._load_question_templates()
        
        logger.info("RAG Service initialized")
    
    def _load_question_templates(self) -> Dict[str, str]:
        """Lade Prompt-Templates für verschiedene Fragetypen"""
        return {
            "multiple_choice": """
Basierend auf dem folgenden Kontext, erstelle eine Multiple-Choice-Frage:

KONTEXT:
{context}

ANFORDERUNGEN:
- Erstelle eine präzise Frage zum Thema: {topic}
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- 4 Antwortoptionen (A, B, C, D)
- Nur eine korrekte Antwort
- Plausible Distraktoren
- Kurze Erklärung der korrekten Antwort

FORMAT (JSON):
{{
    "question": "Fragetext hier",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A",
    "explanation": "Erklärung warum A korrekt ist"
}}
""",
            
            "open_ended": """
Basierend auf dem folgenden Kontext, erstelle eine offene Frage:

KONTEXT:
{context}

ANFORDERUNGEN:
- Erstelle eine durchdachte offene Frage zum Thema: {topic}
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- Frage sollte kritisches Denken fördern
- Musterlösung mit Bewertungskriterien

FORMAT (JSON):
{{
    "question": "Fragetext hier",
    "sample_answer": "Beispiel einer guten Antwort",
    "evaluation_criteria": ["Kriterium 1", "Kriterium 2", "Kriterium 3"]
}}
""",
            
            "true_false": """
Basierend auf dem folgenden Kontext, erstelle eine Wahr/Falsch-Frage:

KONTEXT:
{context}

ANFORDERUNGEN:
- Erstelle eine eindeutige Wahr/Falsch-Aussage zum Thema: {topic}
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- Klare, eindeutige Aussage
- Begründung für die korrekte Antwort

FORMAT (JSON):
{{
    "statement": "Aussage hier",
    "correct_answer": true,
    "explanation": "Erklärung warum die Aussage wahr/falsch ist"
}}
"""
        }
    
    async def retrieve_context(
        self,
        query: str,
        document_ids: Optional[List[int]] = None,
        max_chunks: int = 5,
        min_similarity: Optional[float] = None
    ) -> RAGContext:
        """
        Hole relevanten Kontext aus der Vector Database
        
        Args:
            query: Suchanfrage für Kontext
            document_ids: Optional spezifische Dokumente
            max_chunks: Maximale Anzahl Chunks
            min_similarity: Mindest-Similarity Score
            
        Returns:
            RAGContext mit relevanten Informationen
        """
        min_sim = min_similarity or self.min_context_similarity
        
        try:
            # Vector Search durchführen
            search_results = await vector_service.similarity_search(
                query=query,
                n_results=max_chunks * 2,  # Mehr holen für Filterung
                document_ids=document_ids
            )
            
            # Filtere nach Similarity
            filtered_results = [
                result for result in search_results 
                if result.similarity_score >= min_sim
            ][:max_chunks]
            
            if not filtered_results:
                logger.warning(f"No relevant context found for query: {query}")
                return RAGContext(
                    query=query,
                    retrieved_chunks=[],
                    total_similarity_score=0.0,
                    source_documents=[],
                    context_length=0
                )
            
            # Sammle Source Documents
            source_docs = {}
            for result in filtered_results:
                doc_id = result.document_id
                if doc_id not in source_docs:
                    # Hole Document Info aus Database
                    from database import get_db
                    db = next(get_db())
                    try:
                        document = document_service.get_document_by_id(doc_id, db)
                        if document:
                            source_docs[doc_id] = {
                                "id": doc_id,
                                "filename": document.original_filename,
                                "mime_type": document.mime_type,
                                "chunks_used": 0
                            }
                    finally:
                        db.close()
                
                if doc_id in source_docs:
                    source_docs[doc_id]["chunks_used"] += 1
            
            # Berechne Metriken
            total_similarity = sum(r.similarity_score for r in filtered_results)
            context_text = "\n\n".join([r.content for r in filtered_results])
            context_length = len(context_text)
            
            logger.info(f"Retrieved {len(filtered_results)} chunks for query: {query}")
            
            return RAGContext(
                query=query,
                retrieved_chunks=filtered_results,
                total_similarity_score=total_similarity,
                source_documents=list(source_docs.values()),
                context_length=context_length
            )
            
        except Exception as e:
            logger.error(f"Context retrieval failed: {str(e)}")
            raise
    
    def _prepare_context_text(self, context: RAGContext) -> str:
        """Bereite Kontext-Text für Prompt vor"""
        if not context.retrieved_chunks:
            return "Kein relevanter Kontext verfügbar."
        
        context_parts = []
        for i, chunk in enumerate(context.retrieved_chunks, 1):
            # Füge Source-Info hinzu
            source_info = f"[Quelle {i}]"
            if context.source_documents:
                for doc in context.source_documents:
                    if doc["id"] == chunk.document_id:
                        source_info = f"[Quelle {i}: {doc['filename']}]"
                        break
            
            context_parts.append(f"{source_info}\n{chunk.content}")
        
        full_context = "\n\n---\n\n".join(context_parts)
        
        # Kürze wenn zu lang
        if len(full_context) > self.max_context_length:
            full_context = full_context[:self.max_context_length] + "\n\n[Kontext gekürzt...]"
        
        return full_context
    
    async def generate_question(
        self,
        topic: str,
        context: RAGContext,
        question_type: str = "multiple_choice",
        difficulty: str = "medium",
        language: str = "de"
    ) -> RAGQuestion:
        """
        Generiere eine einzelne Frage basierend auf Kontext
        
        Args:
            topic: Thema der Frage
            context: RAG Kontext
            question_type: Art der Frage
            difficulty: Schwierigkeitsgrad
            language: Sprache
            
        Returns:
            RAGQuestion Objekt
        """
        try:
            # Prüfe ob Kontext verfügbar
            if not context.retrieved_chunks:
                raise ValueError("No context available for question generation")
            
            # Bereite Prompt vor
            template = self.question_templates.get(question_type)
            if not template:
                raise ValueError(f"Unknown question type: {question_type}")
            
            context_text = self._prepare_context_text(context)
            
            prompt = template.format(
                context=context_text,
                topic=topic,
                difficulty=difficulty,
                language=language
            )
            
            # Generiere mit Claude API
            response = await self.claude_service.generate_exam_async({
                "topic": topic,
                "difficulty": difficulty,
                "question_count": 1,
                "question_types": [question_type],
                "language": language,
                "custom_prompt": prompt
            })
            
            # Parse Response
            if response and response.get("questions"):
                claude_question = response["questions"][0]
                
                # Konvertiere zu RAGQuestion
                rag_question = self._convert_to_rag_question(
                    claude_question,
                    question_type,
                    context,
                    difficulty
                )
                
                logger.info(f"Generated {question_type} question for topic: {topic}")
                return rag_question
            
            else:
                raise ValueError("No question generated by Claude API")
                
        except Exception as e:
            logger.error(f"Question generation failed: {str(e)}")
            # Fallback: Einfache Frage ohne Claude
            return self._generate_fallback_question(topic, context, question_type, difficulty)
    
    def _convert_to_rag_question(
        self,
        claude_question: Dict[str, Any],
        question_type: str,
        context: RAGContext,
        difficulty: str
    ) -> RAGQuestion:
        """Konvertiere Claude Response zu RAGQuestion"""
        
        # Extrahiere Source-Informationen
        source_chunks = [chunk.chunk_id for chunk in context.retrieved_chunks]
        source_documents = [doc["filename"] for doc in context.source_documents]
        
        # Berechne Confidence Score basierend auf Context Quality
        confidence_score = min(1.0, context.total_similarity_score / len(context.retrieved_chunks))
        
        if question_type == "multiple_choice":
            return RAGQuestion(
                question_text=claude_question.get("question", ""),
                question_type=question_type,
                options=claude_question.get("options", []),
                correct_answer=claude_question.get("correct_answer", ""),
                explanation=claude_question.get("explanation", ""),
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=confidence_score
            )
        
        elif question_type == "open_ended":
            return RAGQuestion(
                question_text=claude_question.get("question", ""),
                question_type=question_type,
                correct_answer=claude_question.get("sample_answer", ""),
                explanation=claude_question.get("evaluation_criteria", []),
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=confidence_score
            )
        
        elif question_type == "true_false":
            return RAGQuestion(
                question_text=claude_question.get("statement", ""),
                question_type=question_type,
                correct_answer=str(claude_question.get("correct_answer", False)),
                explanation=claude_question.get("explanation", ""),
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=confidence_score
            )
        
        else:
            raise ValueError(f"Unknown question type: {question_type}")
    
    def _generate_fallback_question(
        self,
        topic: str,
        context: RAGContext,
        question_type: str,
        difficulty: str
    ) -> RAGQuestion:
        """Generiere Fallback-Frage wenn Claude API nicht verfügbar"""
        
        source_chunks = [chunk.chunk_id for chunk in context.retrieved_chunks]
        source_documents = [doc["filename"] for doc in context.source_documents]
        
        if question_type == "multiple_choice":
            return RAGQuestion(
                question_text=f"Welche Aussage über {topic} ist basierend auf den Dokumenten korrekt?",
                question_type=question_type,
                options=[
                    "A) Fallback-Option 1",
                    "B) Fallback-Option 2", 
                    "C) Fallback-Option 3",
                    "D) Fallback-Option 4"
                ],
                correct_answer="A",
                explanation="Fallback-Frage generiert (Claude API nicht verfügbar)",
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=0.5
            )
        
        elif question_type == "open_ended":
            return RAGQuestion(
                question_text=f"Erläutern Sie die wichtigsten Aspekte von {topic} basierend auf den bereitgestellten Dokumenten.",
                question_type=question_type,
                correct_answer="Fallback-Antwort basierend auf Dokumenteninhalt",
                explanation="Fallback-Frage generiert",
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=0.5
            )
        
        else:
            return RAGQuestion(
                question_text=f"Fallback-Frage zu {topic}",
                question_type=question_type,
                correct_answer="Fallback",
                explanation="Fallback-Frage generiert",
                difficulty=difficulty,
                source_chunks=source_chunks,
                source_documents=source_documents,
                confidence_score=0.3
            )
    
    async def generate_rag_exam(self, request: RAGExamRequest) -> RAGExamResponse:
        """
        Generiere vollständige RAG-basierte Prüfung
        
        Args:
            request: RAG Exam Request
            
        Returns:
            RAGExamResponse mit generierten Fragen
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Hole Kontext für das Thema
            context = await self.retrieve_context(
                query=request.topic,
                document_ids=request.document_ids,
                max_chunks=request.context_chunks_per_question * request.question_count
            )
            
            if not context.retrieved_chunks:
                raise ValueError(f"No relevant context found for topic: {request.topic}")
            
            # Generiere Fragen
            questions = []
            question_types = request.question_types or ["multiple_choice", "open_ended"]
            
            for i in range(request.question_count):
                # Wähle Fragetyp (rotierend)
                question_type = question_types[i % len(question_types)]
                
                # Erstelle spezifischen Kontext für diese Frage
                chunk_start = i * request.context_chunks_per_question
                chunk_end = min(
                    chunk_start + request.context_chunks_per_question,
                    len(context.retrieved_chunks)
                )
                
                question_context = RAGContext(
                    query=context.query,
                    retrieved_chunks=context.retrieved_chunks[chunk_start:chunk_end],
                    total_similarity_score=sum(
                        r.similarity_score for r in context.retrieved_chunks[chunk_start:chunk_end]
                    ),
                    source_documents=context.source_documents,
                    context_length=sum(
                        len(r.content) for r in context.retrieved_chunks[chunk_start:chunk_end]
                    )
                )
                
                # Generiere Frage
                question = await self.generate_question(
                    topic=request.topic,
                    context=question_context,
                    question_type=question_type,
                    difficulty=request.difficulty,
                    language=request.language
                )
                
                questions.append(question)
            
            end_time = asyncio.get_event_loop().time()
            generation_time = end_time - start_time
            
            # Berechne Quality Metrics
            quality_metrics = self._calculate_quality_metrics(questions, context)
            
            # Erstelle Response
            exam_id = f"rag_exam_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            response = RAGExamResponse(
                exam_id=exam_id,
                topic=request.topic,
                questions=questions,
                context_summary=context,
                generation_time=generation_time,
                quality_metrics=quality_metrics
            )
            
            logger.info(f"Generated RAG exam with {len(questions)} questions in {generation_time:.2f}s")
            return response
            
        except Exception as e:
            logger.error(f"RAG exam generation failed: {str(e)}")
            raise
    
    def _calculate_quality_metrics(
        self,
        questions: List[RAGQuestion],
        context: RAGContext
    ) -> Dict[str, Any]:
        """Berechne Qualitätsmetriken für generierte Prüfung"""
        
        if not questions:
            return {"error": "No questions to analyze"}
        
        # Confidence Scores
        confidence_scores = [q.confidence_score for q in questions]
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        
        # Source Coverage
        all_source_chunks = set()
        for question in questions:
            if question.source_chunks:
                all_source_chunks.update(question.source_chunks)
        
        source_coverage = len(all_source_chunks) / len(context.retrieved_chunks) if context.retrieved_chunks else 0
        
        # Question Type Distribution
        question_types = {}
        for question in questions:
            qtype = question.question_type
            question_types[qtype] = question_types.get(qtype, 0) + 1
        
        return {
            "total_questions": len(questions),
            "average_confidence": round(avg_confidence, 3),
            "source_coverage": round(source_coverage, 3),
            "question_type_distribution": question_types,
            "context_chunks_used": len(context.retrieved_chunks),
            "total_context_length": context.context_length,
            "average_similarity_score": round(
                context.total_similarity_score / len(context.retrieved_chunks), 3
            ) if context.retrieved_chunks else 0
        }


# Globale Service Instanz
rag_service = RAGService()
