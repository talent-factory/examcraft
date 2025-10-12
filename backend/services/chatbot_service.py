"""
ChatBot Service mit PydanticAI für dokumentbasierte Konversationen
"""

from pydantic_ai import Agent
from pydantic_ai.models.anthropic import AnthropicModel
from typing import List, Dict, Any, Optional, Tuple
import logging
import os

from models.chat import ChatBotResponse
from services.qdrant_vector_service import QdrantVectorService
from services.prompt_service import PromptService
from database import SessionLocal

logger = logging.getLogger(__name__)


class DocumentChatBotService:
    """
    ChatBot Service mit PydanticAI für dokumentbasierte Konversationen
    
    Features:
    - RAG-basierte Antwortgenerierung aus selektierten Dokumenten
    - Quellenreferenzen mit Similarity Scores
    - Chat-Historie-Management
    - Konfidenz-Tracking
    """
    
    def __init__(self):
        # Anthropic Claude Model mit PydanticAI
        api_key = os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            logger.warning("No Claude API key found, ChatBot will use demo mode")
            self.demo_mode = True
            self.agent = None
        else:
            self.demo_mode = False
            self.model = AnthropicModel(
                model_name=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514"),
                api_key=api_key
            )

            # Initialize PromptService for dynamic prompt loading
            self.db = SessionLocal()
            self.prompt_service = PromptService(self.db)

            # Load system prompt from Knowledge Base
            system_prompt = self._load_system_prompt_from_kb()

            # PydanticAI Agent mit dynamischem System Prompt
            self.agent = Agent(
                model=self.model,
                system_prompt=system_prompt,
                result_type=ChatBotResponse
            )

        # Vector Service für RAG
        from services.vector_service_factory import get_vector_service
        self.vector_service = get_vector_service()

    def __del__(self):
        """Cleanup database session"""
        if hasattr(self, 'db'):
            self.db.close()

    def _load_system_prompt_from_kb(self) -> str:
        """
        Load system prompt dynamically from Knowledge Base.
        Falls back to hardcoded prompt if not found.
        """
        try:
            # Try to load from Knowledge Base
            prompt = self.prompt_service.get_prompt_for_use_case(
                use_case="chatbot_document_qa",
                category="system_prompt"
            )

            if prompt:
                logger.info(f"Loaded system prompt from KB: {prompt.name} (v{prompt.version})")

                # Log usage
                self.prompt_service.log_prompt_usage(
                    prompt=prompt,
                    use_case="chatbot_document_qa"
                )

                return prompt.content
            else:
                logger.warning("No system prompt found in KB, using fallback")
                return self._build_fallback_system_prompt()

        except Exception as e:
            logger.error(f"Failed to load system prompt from KB: {e}")
            return self._build_fallback_system_prompt()

    def _build_fallback_system_prompt(self) -> str:
        """Fallback System Prompt wenn Knowledge Base nicht verfügbar"""
        return """Du bist ein hilfreicher Assistent, der Fragen zu hochgeladenen Dokumenten beantwortet.

Deine Aufgaben:
- Beantworte Fragen präzise basierend auf den bereitgestellten Dokumenten
- Zitiere IMMER die Quellen mit Seitenzahlen/Kapiteln wenn verfügbar
- Erkenne Zusammenhänge zwischen verschiedenen Dokumenten
- Weise auf Widersprüche oder fehlende Informationen hin
- Bleibe faktisch und spekuliere nicht über Inhalte außerhalb der Dokumente
- Formatiere Antworten strukturiert mit Markdown

Antwortstil:
- Klar und prägnant
- Akademisch korrekt
- Mit Quellenreferenzen
- Strukturiert mit Absätzen und Listen wo sinnvoll

Wenn du dir bei einer Antwort unsicher bist, sage das ehrlich und gib einen niedrigeren Konfidenz-Score.
"""
    
    async def generate_response(
        self,
        user_message: str,
        document_ids: List[int],
        chat_history: List[Dict[str, str]],
        max_context_chunks: int = 5
    ) -> Dict[str, Any]:
        """
        Generiert KI-Antwort basierend auf Dokumentenkontext
        
        Args:
            user_message: Benutzerfrage
            document_ids: Liste der Dokument-IDs für Kontext
            chat_history: Bisherige Konversation [{"role": "user|assistant", "content": "..."}]
            max_context_chunks: Maximale Anzahl RAG-Chunks
            
        Returns:
            dict mit 'content', 'sources' und 'confidence'
        """
        
        # Demo Mode Fallback
        if self.demo_mode:
            return self._generate_demo_response(user_message)
        
        try:
            # 1. RAG Context Retrieval
            document_context, sources = await self.retrieve_relevant_context(
                query=user_message,
                document_ids=document_ids,
                max_chunks=max_context_chunks
            )
            
            # 2. Build enhanced user prompt with context and history
            enhanced_prompt = self._build_enhanced_prompt(
                user_message=user_message,
                document_context=document_context,
                sources=sources,
                chat_history=chat_history
            )

            # 3. PydanticAI Agent ausführen (ohne message_history Parameter)
            result = await self.agent.run(
                user_prompt=enhanced_prompt
            )
            
            return {
                "content": result.data.response,
                "sources": self._enrich_sources(result.data.citations, sources),
                "confidence": result.data.confidence
            }
            
        except Exception as e:
            logger.error(f"ChatBot generation failed: {e}", exc_info=True)
            # Fallback zu Demo-Modus bei Fehler
            return self._generate_demo_response(user_message, error=str(e))
    
    def _build_enhanced_prompt(
        self,
        user_message: str,
        document_context: str,
        sources: List[Dict[str, Any]],
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Baut erweiterten Prompt mit Dokumentenkontext und Chat-Historie"""

        # Quellenübersicht
        source_overview = "\n".join([
            f"- Quelle {i+1}: {s.get('metadata', {}).get('title', 'Unbekannt')} "
            f"(Relevanz: {s.get('score', 0):.0%})"
            for i, s in enumerate(sources)
        ])

        # Chat-Historie formatieren (falls vorhanden)
        history_text = ""
        if chat_history and len(chat_history) > 0:
            history_lines = []
            for msg in chat_history[-5:]:  # Nur letzte 5 Nachrichten
                role = "Benutzer" if msg["role"] == "user" else "Assistent"
                history_lines.append(f"{role}: {msg['content'][:200]}...")  # Gekürzt
            history_text = f"""**BISHERIGE KONVERSATION:**
{chr(10).join(history_lines)}

"""

        prompt = f"""{history_text}**DOKUMENTENKONTEXT:**

{document_context}

**VERFÜGBARE QUELLEN:**
{source_overview}

**BENUTZERFRAGE:**
{user_message}

**ANWEISUNGEN:**
Beantworte die Frage basierend auf dem obigen Dokumentenkontext.
Zitiere die Quellen in deiner Antwort (z.B. "Laut Quelle 1...").
Gib einen Konfidenz-Score zwischen 0.0 und 1.0 an, wie sicher du dir bei der Antwort bist.
"""
        return prompt

    async def retrieve_relevant_context(
        self,
        query: str,
        document_ids: List[int],
        max_chunks: int = 5
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Nutzt bestehendes RAG System für Kontext-Retrieval
        
        Returns:
            (combined_context, source_references)
        """
        try:
            # Semantic Search in selektierten Dokumenten
            search_results = await self.vector_service.similarity_search(
                query=query,
                document_ids=document_ids,
                n_results=max_chunks
            )
            
            # Kombiniere Chunks zu Context
            context_chunks = []
            sources = []
            
            for i, result in enumerate(search_results):
                # Formatiere Chunk mit Quellenmarkierung
                chunk_text = f"[Quelle {i+1}]\n{result.content}\n"
                context_chunks.append(chunk_text)
                
                sources.append({
                    "document_id": result.document_id,
                    "chunk_id": result.chunk_id,
                    "score": result.similarity_score,
                    "metadata": result.metadata or {}
                })
            
            combined_context = "\n---\n\n".join(context_chunks)
            
            if not combined_context:
                combined_context = "Keine relevanten Informationen in den Dokumenten gefunden."
            
            return combined_context, sources
            
        except Exception as e:
            logger.error(f"RAG context retrieval failed: {e}", exc_info=True)
            return "Fehler beim Abrufen des Dokumentenkontexts.", []
    
    def _enrich_sources(
        self,
        citations: List[Dict[str, Any]],
        rag_sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Reichert Citations mit RAG-Metadaten an"""
        enriched = []
        
        for citation in citations:
            # Versuche Citation mit RAG-Source zu matchen
            source_num = citation.get('source_number', 0)
            if 0 <= source_num - 1 < len(rag_sources):
                rag_source = rag_sources[source_num - 1]
                enriched.append({
                    **citation,
                    **rag_source
                })
            else:
                enriched.append(citation)
        
        # Falls keine Citations, nutze alle RAG-Sources
        if not enriched and rag_sources:
            enriched = rag_sources
        
        return enriched
    
    def _generate_demo_response(
        self,
        user_message: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generiert Demo-Antwort wenn Claude API nicht verfügbar"""
        
        if error:
            content = f"""⚠️ **Demo-Modus aktiv** (API-Fehler: {error[:100]})

Ich habe deine Frage verstanden: "{user_message}"

In der Produktionsversion würde ich jetzt:
1. Die relevanten Dokumentabschnitte durchsuchen
2. Eine präzise Antwort basierend auf den Quellen generieren
3. Quellenreferenzen mit Seitenzahlen angeben

Bitte konfiguriere einen gültigen Claude API Key für die volle Funktionalität.
"""
        else:
            content = f"""ℹ️ **Demo-Modus aktiv**

Deine Frage: "{user_message}"

Dies ist eine Demo-Antwort. In der Produktionsversion würde der ChatBot:
- Relevante Abschnitte aus deinen Dokumenten finden
- Eine fundierte Antwort basierend auf den Quellen geben
- Quellenreferenzen mit Similarity Scores anzeigen

Konfiguriere einen Claude API Key für die volle ChatBot-Funktionalität.
"""
        
        return {
            "content": content,
            "sources": [],
            "confidence": 0.0
        }


# Global Service Instance
chatbot_service = DocumentChatBotService()

