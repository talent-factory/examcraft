import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class VectorSearchError(Exception):
    pass


class ClaudeAPIError(Exception):
    pass


class HelpService:
    def __init__(self, db: Session):
        self.db = db

    async def answer_question(
        self,
        question: str,
        user_role: str,
        user_tier: str,
        route: str,
        conversation_history: Optional[List[Dict]] = None,
        locale: str = "de",
    ) -> Dict[str, Any]:
        cached = await self._try_faq_cache(question, locale)
        if cached:
            return cached

        try:
            chunks = await self._search_docs(question)
        except VectorSearchError:
            return {
                "answer": self._service_error_message(locale),
                "confidence": 0.0,
                "sources": [],
                "docs_links": [],
                "escalate": False,
            }

        if not chunks or chunks[0]["score"] < 0.3:
            return {
                "answer": self._no_answer_message(locale),
                "confidence": 0.0,
                "sources": [],
                "docs_links": [],
                "escalate": True,
            }

        try:
            result = await self._call_claude(
                question, chunks, user_role, user_tier, route, conversation_history, locale
            )
            if result["confidence"] < 0.6:
                result = await self._call_claude(
                    question,
                    chunks,
                    user_role,
                    user_tier,
                    route,
                    conversation_history,
                    locale,
                    model="sonnet",
                )
        except ClaudeAPIError:
            return {
                "answer": self._service_error_message(locale),
                "confidence": 0.0,
                "sources": [],
                "docs_links": [],
                "escalate": False,
            }

        result["escalate"] = result["confidence"] < 0.5
        return result

    async def _try_faq_cache(
        self, question: str, locale: str
    ) -> Optional[Dict[str, Any]]:
        # Phase 2 feature: FAQ Qdrant collection not yet implemented
        # Returns None so all questions go to Standard Path (Claude)
        return None

    async def _search_docs(self, question: str) -> List[Dict[str, Any]]:
        try:
            from services.vector_service_factory import vector_service

            if not hasattr(vector_service, "client") or vector_service.client is None:
                return []

            embeddings = await vector_service.create_embeddings([question])
            if len(embeddings) == 0:
                return []

            search_results = vector_service.client.query_points(
                collection_name="docs_help",
                query=embeddings[0].tolist(),
                limit=5,
                with_payload=True,
            )
            return [
                {
                    "content": r.payload.get("content_preview", ""),
                    "source_file": r.payload.get("source_file", ""),
                    "section": r.payload.get("section_title", ""),
                    "language": r.payload.get("language", "de"),
                    "score": r.score,
                }
                for r in search_results.points
            ]
        except Exception as e:
            logger.error(f"Qdrant search failed: {e}", exc_info=True)
            raise VectorSearchError(str(e)) from e

    async def _call_claude(
        self,
        question: str,
        chunks: List[Dict],
        user_role: str,
        user_tier: str,
        route: str,
        history: Optional[List[Dict]],
        locale: str,
        model: str = "haiku",
    ) -> Dict[str, Any]:
        import json
        import re
        from services.docs_url_converter import convert_docs_path_to_url

        context = "\n\n---\n\n".join(
            f"[{c['source_file']} > {c['section']}]\n{c['content']}" for c in chunks[:5]
        )
        system_prompt = (
            "You are ExamCraft AI's help assistant. Answer questions about using ExamCraft. "
            "Base answers ONLY on the provided documentation context. "
            f"User role: '{user_role}', tier: '{user_tier}', current page: '{route}'. "
            "Always respond in the language of the user's question. "
            "Include confidence (0.0-1.0) based on how well the docs cover the question. "
            'Respond in JSON: {"answer": "...", "confidence": 0.X, "docs_links": ["/path"]}'
        )
        messages = []
        if history:
            for msg in history[-10:]:
                if isinstance(msg, dict):
                    messages.append({"role": msg["role"], "content": msg["content"]})
                else:
                    messages.append({"role": msg.role, "content": msg.content})
        messages.append(
            {
                "role": "user",
                "content": f"Documentation context:\n{context}\n\nQuestion: {question}",
            }
        )

        try:
            from services.claude_service import get_claude_service

            claude_service = get_claude_service()
            model_id = (
                "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"
            )
            payload = {
                "model": model_id,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": messages,
            }
            result_raw = await claude_service._make_api_request_with_retry(payload)
            text = result_raw["content"][0]["text"]
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(), strict=False)
                raw_links = parsed.get("docs_links", [])
                converted_links = [
                    convert_docs_path_to_url(link) if not link.startswith("http") else link
                    for link in raw_links
                ]
                sources = [
                    {
                        "file": c["source_file"],
                        "section": c["section"],
                        "url": convert_docs_path_to_url(c["source_file"]),
                    }
                    for c in chunks[:3]
                ]
                return {
                    "answer": parsed.get("answer", text),
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "sources": sources,
                    "docs_links": converted_links,
                }
            return {
                "answer": text,
                "confidence": 0.5,
                "sources": [
                    {
                        "file": c["source_file"],
                        "section": c["section"],
                        "url": convert_docs_path_to_url(c["source_file"]),
                    }
                    for c in chunks[:3]
                ],
                "docs_links": [],
            }
        except Exception as e:
            logger.error(f"Claude API call failed: {e}", exc_info=True)
            raise ClaudeAPIError(str(e)) from e

    def _no_answer_message(self, locale: str) -> str:
        if locale == "de":
            return (
                "Ich konnte leider keine passende Antwort in der Dokumentation finden. "
                "Möchtest du den Support kontaktieren?"
            )
        return (
            "I couldn't find a matching answer in the documentation. "
            "Would you like to contact support?"
        )

    def _service_error_message(self, locale: str) -> str:
        if locale == "de":
            return (
                "Der Dienst ist vorübergehend nicht verfügbar. "
                "Bitte versuche es später erneut oder besuche unsere Dokumentation."
            )
        return (
            "The service is temporarily unavailable. "
            "Please try again later or visit our documentation."
        )

    def _error_message(self, locale: str) -> str:
        if locale == "de":
            return (
                "Bei der Verarbeitung ist ein Fehler aufgetreten. "
                "Bitte versuche es erneut oder besuche unsere Dokumentation."
            )
        return "An error occurred while processing your request. Please try again or visit our documentation."
