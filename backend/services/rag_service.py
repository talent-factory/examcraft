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

from services.vector_service_factory import get_vector_service
from services.qdrant_vector_service import SearchResult
from services.claude_service import ClaudeService
from services.document_service import document_service
from services.prompt_service import PromptService
from database import SessionLocal

# Initialize vector service
vector_service = get_vector_service()

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
class PromptConfig:
    """Konfiguration für einen Prompt"""
    prompt_id: str
    variables: Optional[Dict[str, Any]] = None


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
    prompt_config: Optional[Dict[str, PromptConfig]] = None  # NEU: Prompt-Konfiguration pro Fragetyp


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
        self.min_context_similarity = 0.01  # Mindest-Similarity für Context (angepasst für Mock Embeddings)
        self.max_context_length = 4000  # Max Zeichen für Context

        # Initialize PromptService for dynamic prompt loading
        self.db = SessionLocal()
        self.prompt_service = PromptService(self.db)

        # Load templates from Knowledge Base (with fallback)
        self.question_templates = self._load_question_templates()

        logger.info("RAG Service initialized with dynamic prompt loading")

    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db'):
            self.db.close()
    
    def _load_question_templates(self) -> Dict[str, str]:
        """
        Lade Prompt-Templates dynamisch aus Knowledge Base.
        Falls back to hardcoded templates if not found.
        """
        templates = {}
        question_types = ["multiple_choice", "open_ended", "true_false"]

        for q_type in question_types:
            try:
                # Try to load from Knowledge Base
                prompt = self.prompt_service.get_prompt_for_use_case(
                    use_case=f"question_generation_{q_type}",
                    category="system_prompt"
                )

                if prompt:
                    logger.info(f"Loaded {q_type} template from KB: {prompt.name} (v{prompt.version})")
                    templates[q_type] = prompt.content

                    # Log usage
                    self.prompt_service.log_prompt_usage(
                        prompt=prompt,
                        use_case=f"question_generation_{q_type}"
                    )
                else:
                    logger.warning(f"No template found in KB for {q_type}, using fallback")
                    templates[q_type] = self._get_fallback_template(q_type)

            except Exception as e:
                logger.error(f"Failed to load {q_type} template from KB: {e}")
                templates[q_type] = self._get_fallback_template(q_type)

        return templates

    def _get_fallback_template(self, question_type: str) -> str:
        """Fallback templates wenn Knowledge Base nicht verfügbar"""
        fallback_templates = {
            "multiple_choice": """
Du bist ein Experte für die Erstellung von OpenBook-Prüfungsfragen für akademische Kurse.

KONTEXT AUS DOKUMENTEN:
{context}

AUFGABE:
Erstelle eine anspruchsvolle Multiple-Choice-Frage zum Thema "{topic}" basierend AUSSCHLIESSLICH auf dem obigen Kontext.

ANFORDERUNGEN FÜR OPENBOOK-PRÜFUNGEN:
- Die Frage muss SPEZIFISCHE Details, Konzepte oder Zusammenhänge aus dem Kontext abfragen
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- Vermeide generische Fragen wie "Was ist wichtig bei..." oder "Welche Aspekte sind relevant..."
- Fokussiere auf KONKRETE Fakten, Algorithmen, Formeln, Definitionen oder Prozesse aus dem Text
- Die Frage soll Verständnis und Anwendung prüfen, nicht nur Auswendiglernen

ANTWORTOPTIONEN:
- Erstelle 4 Optionen (A, B, C, D)
- Nur EINE korrekte Antwort
- Distraktoren müssen plausibel sein und häufige Missverständnisse widerspiegeln
- Vermeide offensichtlich falsche oder absurde Optionen
- Keine "Alle oben genannten" oder "Keine der genannten" Optionen
- WICHTIG: Code-Elemente (Funktionsnamen, Variablen, Klassen) MÜSSEN in Backticks gesetzt werden
  Beispiel: `self._distribute_elements(arr)` statt self._distribute_elements(arr)

FORMAT (JSON):
{{
    "question": "Konkrete, spezifische Frage basierend auf dem Kontext",
    "options": [
        "A) Spezifische Option mit konkreten Details (Code in `backticks`)",
        "B) Plausible Alternative mit ähnlichem Konzept",
        "C) Häufiges Missverständnis oder verwandtes Konzept",
        "D) Weitere plausible aber falsche Option"
    ],
    "correct_answer": "A",
    "explanation": "Detaillierte Erklärung mit Verweis auf den Kontext, warum A korrekt ist und warum die anderen Optionen falsch sind"
}}

BEISPIEL GUTER FRAGEN:
- "Welche Zeitkomplexität hat Heap-Sort im Worst-Case und warum?"
- "Was ist der entscheidende Unterschied zwischen Max-Heap und Min-Heap bei der Implementierung?"
- "In welcher Phase des Heap-Sort Algorithmus wird die Heap-Eigenschaft wiederhergestellt?"

BEISPIEL SCHLECHTER FRAGEN (VERMEIDE):
- "Was ist ein wichtiger Aspekt von Heap-Sort?" (zu generisch)
- "Welche der folgenden Aussagen ist korrekt?" (zu vage)
- "Was sollte man über Heap-Sort wissen?" (nicht spezifisch)
""",
            
            "open_ended": """
Du bist ein Experte für die Erstellung von OpenBook-Prüfungsfragen für akademische Kurse.

KONTEXT AUS DOKUMENTEN:
{context}

AUFGABE:
Erstelle eine anspruchsvolle offene Frage zum Thema "{topic}" basierend AUSSCHLIESSLICH auf dem obigen Kontext.

ANFORDERUNGEN FÜR OPENBOOK-PRÜFUNGEN:
- Die Frage muss TIEFES Verständnis und ANWENDUNG von Konzepten aus dem Kontext prüfen
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- Fördere kritisches Denken, Analyse und Synthese
- Vermeide reine Reproduktionsfragen ("Definieren Sie...", "Listen Sie auf...")
- Fokussiere auf Erklärungen, Vergleiche, Anwendungen oder Problemlösungen

FRAGETYPEN (wähle passend):
- Erklärungsfragen: "Erklären Sie, warum/wie..."
- Vergleichsfragen: "Vergleichen Sie X und Y hinsichtlich..."
- Anwendungsfragen: "Wie würden Sie X anwenden, um Problem Y zu lösen?"
- Analysefragen: "Analysieren Sie die Vor- und Nachteile von..."

FORMAT (JSON):
{{
    "question": "Konkrete, anspruchsvolle offene Frage",
    "sample_answer": "Detaillierte Musterantwort mit spezifischen Punkten aus dem Kontext",
    "evaluation_criteria": [
        "Kriterium 1: Spezifischer Aspekt der Antwort",
        "Kriterium 2: Weiterer wichtiger Punkt",
        "Kriterium 3: Tiefe des Verständnisses"
    ]
}}

BEISPIEL GUTER FRAGEN:
- "Erklären Sie den Heapify-Prozess und warum er für die Effizienz von Heap-Sort entscheidend ist."
- "Vergleichen Sie Heap-Sort mit Quick-Sort hinsichtlich Zeitkomplexität und Speicherbedarf."
- "Analysieren Sie, in welchen Szenarien Heap-Sort gegenüber anderen Sortieralgorithmen vorzuziehen ist."
""",
            
            "true_false": """
Du bist ein Experte für die Erstellung von OpenBook-Prüfungsfragen für akademische Kurse.

KONTEXT AUS DOKUMENTEN:
{context}

AUFGABE:
Erstelle eine anspruchsvolle Wahr/Falsch-Aussage zum Thema "{topic}" basierend AUSSCHLIESSLICH auf dem obigen Kontext.

ANFORDERUNGEN FÜR OPENBOOK-PRÜFUNGEN:
- Die Aussage muss SPEZIFISCHE Details oder Zusammenhänge aus dem Kontext prüfen
- Schwierigkeitsgrad: {difficulty}
- Sprache: {language}
- Vermeide triviale oder offensichtliche Aussagen
- Die Aussage sollte subtile Unterschiede oder häufige Missverständnisse adressieren
- Klare, eindeutige Formulierung ohne Mehrdeutigkeiten

GUTE AUSSAGEN:
- Enthalten spezifische technische Details aus dem Kontext
- Prüfen Verständnis von Zusammenhängen, nicht nur Fakten
- Sind nicht durch bloßes Raten lösbar

FORMAT (JSON):
{{
    "statement": "Präzise, spezifische Aussage basierend auf dem Kontext",
    "correct_answer": true,
    "explanation": "Detaillierte Erklärung mit Verweis auf den Kontext, warum die Aussage wahr/falsch ist"
}}

BEISPIEL GUTER AUSSAGEN:
- "Die Worst-Case-Zeitkomplexität von Heap-Sort ist O(n log n), unabhängig von der Eingabereihenfolge."
- "Bei einem Max-Heap ist der Wert jedes Knotens größer oder gleich den Werten seiner Kindknoten."
- "Heap-Sort ist ein stabiler Sortieralgorithmus, der die relative Reihenfolge gleicher Elemente beibehält."

BEISPIEL SCHLECHTER AUSSAGEN (VERMEIDE):
- "Heap-Sort ist ein Sortieralgorithmus." (zu trivial)
- "Heap-Sort ist wichtig." (zu vage)
- "Heap-Sort wird verwendet." (nicht spezifisch)
"""
        }

        return fallback_templates.get(question_type, fallback_templates["multiple_choice"])
    
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

            # DEBUG: Log search results
            logger.info(f"Vector search returned {len(search_results)} results for query '{query}'")
            if search_results:
                logger.info(f"Top result: score={search_results[0].similarity_score:.4f}, doc_id={search_results[0].document_id}")

            # Filtere nach Similarity
            filtered_results = [
                result for result in search_results
                if result.similarity_score >= min_sim
            ][:max_chunks]

            # DEBUG: Log filtered results
            logger.info(f"After filtering (min_sim={min_sim}): {len(filtered_results)} results")
            
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
        language: str = "de",
        # NEU: Prompt-Konfiguration
        prompt_id: Optional[str] = None,
        prompt_variables: Optional[Dict[str, Any]] = None
    ) -> RAGQuestion:
        """
        Generiere eine einzelne Frage basierend auf Kontext

        Args:
            topic: Thema der Frage
            context: RAG Kontext
            question_type: Art der Frage
            difficulty: Schwierigkeitsgrad
            language: Sprache
            prompt_id: Optional Prompt UUID (falls None, wird default Template verwendet)
            prompt_variables: Optional Template-Variablen für custom Prompt

        Returns:
            RAGQuestion Objekt
        """
        try:
            # Prüfe ob Kontext verfügbar
            if not context.retrieved_chunks:
                raise ValueError("No context available for question generation")

            context_text = self._prepare_context_text(context)

            # Bereite Prompt vor (mit custom Prompt oder default Template)
            if prompt_id:
                # Verwende custom Prompt aus Knowledge Base
                try:
                    # Merge default variables mit custom variables
                    variables = {
                        "context": context_text,
                        "topic": topic,
                        "difficulty": difficulty,
                        "language": language
                    }

                    if prompt_variables:
                        variables.update(prompt_variables)

                    # Rendere Prompt mit Jinja2
                    prompt = self.prompt_service.render_prompt_by_id(
                        prompt_id=prompt_id,
                        variables=variables,
                        strict=False  # Nicht-strikte Validierung für Backward-Compatibility
                    )

                    # Log usage
                    prompt_obj = self.prompt_service.get_prompt_by_id(prompt_id)
                    if prompt_obj:
                        self.prompt_service.log_prompt_usage(
                            prompt=prompt_obj,
                            use_case=f"question_generation_{question_type}"
                        )

                    logger.info(f"Using custom prompt {prompt_id} for {question_type}")

                except Exception as e:
                    logger.error(f"Failed to load custom prompt {prompt_id}: {e}")
                    logger.info(f"Falling back to default template for {question_type}")
                    # Fallback auf default Template
                    template = self.question_templates.get(question_type)
                    if not template:
                        raise ValueError(f"Unknown question type: {question_type}")

                    prompt = template.format(
                        context=context_text,
                        topic=topic,
                        difficulty=difficulty,
                        language=language
                    )
            else:
                # Verwende default Template
                template = self.question_templates.get(question_type)
                if not template:
                    raise ValueError(f"Unknown question type: {question_type}")

                prompt = template.format(
                    context=context_text,
                    topic=topic,
                    difficulty=difficulty,
                    language=language
                )

            # DEBUG: Log prompt to verify new template is used
            logger.info(f"=== QUESTION GENERATION PROMPT ===")
            logger.info(f"Question Type: {question_type}, Topic: {topic}, Difficulty: {difficulty}")
            logger.info(f"Prompt length: {len(prompt)} chars")
            logger.info(f"Prompt starts with: {prompt[:200]}...")
            logger.info(f"===================================")
            
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
                explanation=claude_question.get("evaluation_criteria", "Keine Erklärung verfügbar"),
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
                
                # Hole Prompt-Config für diesen Fragetyp (falls vorhanden)
                prompt_id = None
                prompt_variables = None

                if request.prompt_config and question_type in request.prompt_config:
                    config = request.prompt_config[question_type]
                    prompt_id = config.prompt_id
                    prompt_variables = config.variables
                    logger.info(f"Using custom prompt config for {question_type}: {prompt_id}")

                # Generiere Frage
                question = await self.generate_question(
                    topic=request.topic,
                    context=question_context,
                    question_type=question_type,
                    difficulty=request.difficulty,
                    language=request.language,
                    prompt_id=prompt_id,
                    prompt_variables=prompt_variables
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

# Force update threshold for existing instance (Hotfix)
rag_service.min_context_similarity = 0.01
