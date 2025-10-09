"""
Chat Export Service für verschiedene Formate
"""

from typing import List, Dict, Any
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ChatExportService:
    """Service für Chat-Export in verschiedene Formate"""
    
    def export_as_markdown(
        self,
        session_title: str,
        created_at: datetime,
        documents: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Exportiert Chat als Markdown-Dokument
        
        Format:
        # Chat-Session: [Titel]
        
        ## Dokumente
        - Dokument 1
        - Dokument 2
        
        ## Konversation
        
        **User**: Frage...
        
        **Assistant**: Antwort...
        
        ---
        Quellen: [...]
        """
        
        markdown_content = f"# Chat-Session: {session_title}\n\n"
        markdown_content += f"**Erstellt am**: {created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Dokumente auflisten
        markdown_content += "## Verwendete Dokumente\n\n"
        for doc in documents:
            markdown_content += f"- {doc.get('title', 'Unbekannt')}\n"
        
        markdown_content += "\n## Konversation\n\n"
        
        # Messages
        for msg in messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            markdown_content += f"**{role}**: {msg['content']}\n\n"
            
            if msg.get("sources"):
                markdown_content += "_Quellen:_ "
                sources = [
                    s.get('metadata', {}).get('title', 'Unbekannt')
                    for s in msg["sources"]
                ]
                markdown_content += ", ".join(sources)
                markdown_content += "\n\n"
            
            markdown_content += "---\n\n"
        
        return markdown_content
    
    def export_as_json(
        self,
        session_id: str,
        session_title: str,
        created_at: datetime,
        documents: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> str:
        """Exportiert Chat als JSON"""
        
        export_data = {
            "session_id": str(session_id),
            "title": session_title,
            "created_at": created_at.isoformat(),
            "documents": documents,
            "messages": [
                {
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"].isoformat() if isinstance(msg["timestamp"], datetime) else msg["timestamp"],
                    "sources": msg.get("sources"),
                    "confidence": msg.get("confidence")
                }
                for msg in messages
            ],
            "message_count": len(messages)
        }
        
        return json.dumps(export_data, indent=2, ensure_ascii=False)
    
    def convert_chat_to_document_content(
        self,
        session_title: str,
        created_at: datetime,
        documents: List[Dict[str, Any]],
        messages: List[Dict[str, Any]]
    ) -> str:
        """
        Konvertiert Chat-Session in strukturiertes Dokument für RAG
        
        - Formatiert als Q&A-Dokument
        - Fügt Metadaten hinzu
        - Optimiert für Vector Embedding
        """
        
        document_content = f"""# Wissensdokumentation: {session_title}

Erstellt aus Chat-Session am {created_at.strftime('%d.%m.%Y %H:%M')}

## Basisdokumente

"""
        
        # Quelldokumente auflisten
        for doc in documents:
            document_content += f"- {doc.get('title', 'Unbekannt')}\n"
        
        document_content += "\n## Erkenntnisse und Antworten\n\n"
        
        # Q&A Paare extrahieren
        qa_pairs = self._extract_qa_pairs(messages)
        
        for i, (question, answer, sources) in enumerate(qa_pairs, 1):
            document_content += f"### Frage {i}\n\n{question}\n\n"
            document_content += f"**Antwort**: {answer}\n\n"
            
            if sources:
                document_content += f"**Quellen**: {', '.join(sources)}\n\n"
        
        return document_content
    
    def _extract_qa_pairs(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[tuple]:
        """Extrahiert Q&A Paare aus Chat-Historie"""
        
        qa_pairs = []
        
        for i in range(len(messages) - 1):
            if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                question = messages[i]["content"]
                answer = messages[i + 1]["content"]
                
                # Extrahiere Quellen
                sources = []
                if messages[i + 1].get("sources"):
                    sources = [
                        s.get('metadata', {}).get('title', 'Unbekannt')
                        for s in messages[i + 1]["sources"]
                    ]
                
                qa_pairs.append((question, answer, sources))
        
        return qa_pairs


# Global Service Instance
chat_export_service = ChatExportService()

