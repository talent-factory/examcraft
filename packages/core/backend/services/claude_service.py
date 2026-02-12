"""
Claude API Service for ExamCraft AI
Handles communication with Anthropic's Claude API for intelligent question generation
"""

import os
import httpx
import json
import asyncio
import time
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class ClaudeService:
    """Service for interacting with Claude API with full production features"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.base_url = "https://api.anthropic.com/v1/messages"
        # Using Claude Sonnet 4 (latest stable model as of 2025)
        # Previous models (claude-3-*) are being deprecated
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

        # Rate limiting configuration
        self.max_requests_per_minute = int(os.getenv("CLAUDE_MAX_RPM", "50"))
        self.max_tokens_per_request = int(os.getenv("CLAUDE_MAX_TOKENS", "4000"))

        # Retry configuration
        self.max_retries = int(os.getenv("CLAUDE_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("CLAUDE_RETRY_DELAY", "1.0"))
        # Timeout for API requests (default 120s for large prompts with context)
        self.request_timeout = float(os.getenv("CLAUDE_REQUEST_TIMEOUT", "120.0"))

        # Cost tracking
        self.cost_per_input_token = 0.003 / 1000  # $3 per million input tokens
        self.cost_per_output_token = 0.015 / 1000  # $15 per million output tokens

        # Demo mode fallback
        self.demo_mode = (
            not self.api_key or os.getenv("CLAUDE_DEMO_MODE", "false").lower() == "true"
        )

        # Rate limiting tracking
        self.request_timestamps = []
        self.total_cost = 0.0
        self.total_input_tokens = 0
        self.total_output_tokens = 0

        if self.demo_mode:
            logger.warning("Claude API running in DEMO MODE - using mock responses")
            if not self.api_key:
                logger.warning("ANTHROPIC_API_KEY environment variable is not set!")
        else:
            # Log API key status (masked for security)
            key_preview = (
                f"{self.api_key[:10]}...{self.api_key[-4:]}"
                if self.api_key and len(self.api_key) > 14
                else "INVALID_KEY"
            )
            logger.info(
                f"Claude API initialized: model={self.model}, timeout={self.request_timeout}s, key={key_preview}"
            )

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits"""
        now = time.time()
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps if now - ts < 60
        ]

        if len(self.request_timestamps) >= self.max_requests_per_minute:
            return False
        return True

    def _add_request_timestamp(self):
        """Add current timestamp to rate limit tracking"""
        self.request_timestamps.append(time.time())

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for API call"""
        input_cost = input_tokens * self.cost_per_input_token
        output_cost = output_tokens * self.cost_per_output_token
        total_cost = input_cost + output_cost

        # Update totals
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += total_cost

        return total_cost

    async def _make_api_request_with_retry(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make API request with retry logic"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                # Check rate limit
                if not self._check_rate_limit():
                    wait_time = 60 - (time.time() - min(self.request_timestamps))
                    logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                    await asyncio.sleep(wait_time)

                self._add_request_timestamp()

                async with httpx.AsyncClient(timeout=self.request_timeout) as client:
                    response = await client.post(
                        self.base_url,
                        headers={
                            "Content-Type": "application/json",
                            "x-api-key": self.api_key,
                            "anthropic-version": "2023-06-01",
                        },
                        json=payload,
                    )

                    if response.status_code == 200:
                        result = response.json()

                        # Track usage and cost
                        usage = result.get("usage", {})
                        input_tokens = usage.get("input_tokens", 0)
                        output_tokens = usage.get("output_tokens", 0)
                        cost = self._calculate_cost(input_tokens, output_tokens)

                        logger.info(
                            f"Claude API call successful - Cost: ${cost:.4f}, Tokens: {input_tokens}+{output_tokens}"
                        )
                        return result

                    elif response.status_code == 429:  # Rate limited
                        retry_after = int(
                            response.headers.get("retry-after", self.retry_delay)
                        )
                        logger.warning(f"Rate limited by API, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    else:
                        error_msg = (
                            f"Claude API error {response.status_code}: {response.text}"
                        )
                        logger.error(error_msg)
                        raise Exception(error_msg)

            except Exception as e:
                last_exception = e
                # Get detailed error info including exception type
                error_type = type(e).__name__
                error_msg = str(e) if str(e) else repr(e)
                error_detail = f"{error_type}: {error_msg}"

                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Claude API attempt {attempt + 1} failed: {error_detail}, retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"Claude API failed after {self.max_retries} attempts: {error_detail}"
                    )
                    # Log full traceback for debugging
                    import traceback

                    logger.error(f"Full traceback:\n{traceback.format_exc()}")

        raise last_exception or Exception("Claude API request failed")

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get current usage statistics"""
        return {
            "total_cost": round(self.total_cost, 4),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "requests_last_minute": len(self.request_timestamps),
            "demo_mode": self.demo_mode,
        }

    async def generate_questions(
        self,
        topic: str,
        difficulty: str = "medium",
        question_count: int = 5,
        question_types: List[str] = None,
        language: str = "de",
    ) -> List[Dict[str, Any]]:
        """
        Generate exam questions using Claude API with full production features

        Args:
            topic: The subject/topic for the questions
            difficulty: easy, medium, or hard
            question_count: Number of questions to generate
            question_types: Types of questions (multiple_choice, open_ended, etc.)
            language: Language for questions (de, en)

        Returns:
            List of generated questions
        """

        # Use demo mode if API key not available or explicitly enabled
        if self.demo_mode:
            logger.info("Using demo mode for question generation")
            return self._generate_demo_questions(
                topic, difficulty, question_count, language
            )

        try:
            prompt = self._build_prompt(
                topic, difficulty, question_count, question_types, language
            )

            payload = {
                "model": self.model,
                "max_tokens": min(self.max_tokens_per_request, 4000),
                "messages": [{"role": "user", "content": prompt}],
            }

            # Use new retry logic
            result = await self._make_api_request_with_retry(payload)
            content = result["content"][0]["text"]
            return self._parse_claude_response(content, topic, difficulty)

        except Exception as e:
            logger.error(f"Claude API failed, falling back to demo mode: {str(e)}")
            return self._generate_demo_questions(
                topic, difficulty, question_count, language
            )

    async def generate_exam_async(self, exam_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate exam questions asynchronously for RAG integration

        Args:
            exam_request: Dictionary with exam parameters
                - topic: str
                - difficulty: str
                - question_count: int
                - question_types: List[str]
                - context: str (optional)
                - language: str
                - custom_prompt: str (optional) - Custom prompt template to use instead of default

        Returns:
            Dictionary with generated questions
        """
        try:
            topic = exam_request.get("topic", "")
            difficulty = exam_request.get("difficulty", "medium")
            question_count = exam_request.get("question_count", 1)
            question_types = exam_request.get("question_types", ["multiple_choice"])
            context = exam_request.get("context", "")
            language = exam_request.get("language", "de")
            custom_prompt = exam_request.get("custom_prompt")

            # Use custom prompt if provided (from Prompt Knowledge Base)
            if custom_prompt:
                logger.info(
                    f"Using custom prompt template ({len(custom_prompt)} chars)"
                )

                # Use demo mode if API key not available
                if self.demo_mode:
                    logger.info("Demo mode: returning demo questions for custom prompt")
                    return {
                        "questions": self._generate_demo_questions(
                            topic, difficulty, question_count, language
                        ),
                        "topic": topic,
                        "difficulty": difficulty,
                        "question_count": question_count,
                        "context_used": bool(context),
                        "custom_prompt_used": True,
                    }

                # Send custom prompt directly to Claude API
                payload = {
                    "model": self.model,
                    "max_tokens": min(self.max_tokens_per_request, 4000),
                    "messages": [{"role": "user", "content": custom_prompt}],
                }

                result = await self._make_api_request_with_retry(payload)
                content = result["content"][0]["text"]

                # Custom prompts können Markdown oder JSON zurückgeben
                # Versuche JSON zu parsen, aber akzeptiere auch Markdown
                try:
                    questions = self._parse_claude_response(content, topic, difficulty)
                except Exception as e:
                    logger.warning(
                        f"Could not parse as JSON, returning raw Markdown: {e}"
                    )
                    # Wenn JSON-Parsing fehlschlägt, gib Markdown als einzelne "Frage" zurück
                    questions = [
                        {
                            "question": content,
                            "type": "markdown",
                            "raw_output": True,
                        }
                    ]

                return {
                    "questions": questions,
                    "topic": topic,
                    "difficulty": difficulty,
                    "question_count": len(questions),
                    "context_used": bool(context),
                    "custom_prompt_used": True,
                }

            # Default flow: Build enhanced prompt with context
            if context:
                enhanced_topic = f"{topic}\n\nKontext:\n{context}"
            else:
                enhanced_topic = topic

            # Generate questions using existing method
            questions = await self.generate_questions(
                topic=enhanced_topic,
                difficulty=difficulty,
                question_count=question_count,
                question_types=question_types,
                language=language,
            )

            return {
                "questions": questions,
                "topic": topic,
                "difficulty": difficulty,
                "question_count": len(questions),
                "context_used": bool(context),
            }

        except Exception as e:
            import traceback

            error_type = type(e).__name__
            error_msg = str(e) if str(e) else repr(e)
            error_detail = f"{error_type}: {error_msg}"
            logger.error(f"Exam generation failed: {error_detail}")
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            # Return fallback structure with detailed error
            return {
                "questions": self._generate_demo_questions(
                    exam_request.get("topic", "Fallback"),
                    exam_request.get("difficulty", "medium"),
                    exam_request.get("question_count", 1),
                    exam_request.get("language", "de"),
                ),
                "topic": exam_request.get("topic", "Fallback"),
                "difficulty": exam_request.get("difficulty", "medium"),
                "question_count": exam_request.get("question_count", 1),
                "context_used": False,
                "error": error_detail,
            }

    def _build_prompt(
        self,
        topic: str,
        difficulty: str,
        question_count: int,
        question_types: List[str],
        language: str,
    ) -> str:
        """Build the prompt for Claude API"""

        lang_instruction = "auf Deutsch" if language == "de" else "in English"
        difficulty_map = {
            "easy": "einfach" if language == "de" else "easy",
            "medium": "mittel" if language == "de" else "medium",
            "hard": "schwer" if language == "de" else "hard",
        }

        prompt = f"""
Erstelle {question_count} Prüfungsfragen zum Thema "{topic}" {lang_instruction}.

Anforderungen:
- Schwierigkeitsgrad: {difficulty_map.get(difficulty, difficulty)}
- Mischung aus Multiple-Choice und offenen Fragen
- Jede Frage soll lehrreich und praxisbezogen sein
- Für Multiple-Choice: 4 Antwortoptionen mit einer korrekten Antwort
- Für offene Fragen: Klare Fragestellung mit Bewertungskriterien

WICHTIG für Code-Formatierung:
- Code-Elemente (Funktionsnamen, Variablen, Klassen, Code-Snippets) MÜSSEN in Backticks gesetzt werden
- Beispiel: `self._distribute_elements(arr)` statt self._distribute_elements(arr)
- Dies gilt für Fragen, Optionen und Erklärungen

Format als JSON:
{{
  "questions": [
    {{
      "id": "q1",
      "type": "multiple_choice",
      "question": "Fragetext hier (Code in `backticks`)",
      "options": ["Option A (Code in `backticks`)", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A (Code in `backticks`)",
      "explanation": "Erklärung warum diese Antwort korrekt ist (Code in `backticks`)",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }},
    {{
      "id": "q2",
      "type": "open_ended",
      "question": "Offene Fragestellung hier",
      "options": null,
      "correct_answer": null,
      "explanation": "Bewertungskriterien und Musterlösung",
      "difficulty": "{difficulty}",
      "topic": "{topic}"
    }}
  ]
}}

Wichtig: Antworte nur mit dem JSON, keine zusätzlichen Erklärungen.
"""
        return prompt

    def _parse_claude_response(
        self, content: str, topic: str, difficulty: str
    ) -> List[Dict[str, Any]]:
        """Parse Claude's JSON response with multiple format support"""
        import re

        # Log raw response for debugging (truncated)
        logger.debug(f"Claude raw response (first 500 chars): {content[:500]}")

        try:
            # Strategy 1: Try to find and parse a JSON object with "questions" key
            start_idx = content.find("{")
            end_idx = content.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = content[start_idx:end_idx]
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and "questions" in data:
                        questions = data.get("questions", [])
                        logger.info(
                            f"Successfully parsed {len(questions)} questions from JSON object"
                        )
                        return questions
                    elif isinstance(data, dict):
                        # Single question object, wrap in list
                        logger.info("Parsed single question object, wrapping in list")
                        return [data]
                except json.JSONDecodeError:
                    logger.debug("JSON object parsing failed, trying array format")

            # Strategy 2: Try to find and parse a JSON array directly
            array_match = re.search(r"\[[\s\S]*\]", content)
            if array_match:
                try:
                    questions = json.loads(array_match.group())
                    if isinstance(questions, list):
                        logger.info(
                            f"Successfully parsed {len(questions)} questions from JSON array"
                        )
                        return questions
                except json.JSONDecodeError:
                    logger.debug("JSON array parsing failed")

            # Strategy 3: Try to clean up markdown code blocks
            code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
            if code_block_match:
                clean_json = code_block_match.group(1).strip()
                try:
                    data = json.loads(clean_json)
                    if isinstance(data, dict) and "questions" in data:
                        logger.info("Successfully parsed questions from code block")
                        return data.get("questions", [])
                    elif isinstance(data, list):
                        logger.info("Successfully parsed array from code block")
                        return data
                except json.JSONDecodeError:
                    logger.debug("Code block JSON parsing failed")

            # No valid JSON found - könnte Markdown sein (bei Custom Prompts normal)
            logger.warning(
                f"No valid JSON found in Claude response. Content preview: {content[:200]}..."
            )
            # Raise exception statt Demo-Fragen zurückzugeben
            # Der Caller kann entscheiden, ob Markdown akzeptiert wird
            raise ValueError("No valid JSON found in Claude response")

        except ValueError:
            # ValueError wird nach oben propagiert (für Custom Prompt Handler)
            raise
        except Exception as e:
            logger.error(f"Failed to parse Claude response: {type(e).__name__}: {e}")
            logger.error(f"Response content preview: {content[:300]}...")
            return self._generate_demo_questions(topic, difficulty, 3, "de")

    def _generate_demo_questions(
        self, topic: str, difficulty: str, question_count: int, language: str = "de"
    ) -> List[Dict[str, Any]]:
        """Generate demo questions when Claude API is not available"""

        demo_questions = []

        # Multiple Choice Question
        demo_questions.append(
            {
                "id": "demo_q1",
                "type": "multiple_choice",
                "question": f"Was ist ein wichtiger Aspekt von {topic}?",
                "options": [
                    "Option A: Grundlegendes Verständnis",
                    "Option B: Praktische Anwendung",
                    "Option C: Theoretische Fundierung",
                    "Option D: Alle oben genannten",
                ],
                "correct_answer": "Option D: Alle oben genannten",
                "explanation": f"Bei {topic} sind alle genannten Aspekte wichtig: Grundlegendes Verständnis bildet die Basis, praktische Anwendung zeigt die Relevanz, und theoretische Fundierung sorgt für tieferes Verständnis. Eine ganzheitliche Betrachtung ist daher am sinnvollsten.",
                "difficulty": difficulty,
                "topic": topic,
            }
        )

        # Open Ended Question
        demo_questions.append(
            {
                "id": "demo_q2",
                "type": "open_ended",
                "question": f"Erklären Sie die praktische Bedeutung von {topic} in der realen Welt. Geben Sie konkrete Beispiele.",
                "options": None,
                "correct_answer": None,
                "explanation": f"Eine vollständige Antwort zu {topic} sollte folgende Elemente enthalten: 1) Praktische Anwendungsbereiche mit konkreten Beispielen, 2) Relevanz für verschiedene Branchen oder Lebensbereiche, 3) Vorteile und mögliche Herausforderungen. Bewertungskriterien: Fachliches Verständnis (40%), Konkrete Beispiele (30%), Strukturierte Darstellung (30%).",
                "difficulty": difficulty,
                "topic": topic,
            }
        )

        # Additional questions based on count
        if question_count > 2:
            demo_questions.append(
                {
                    "id": "demo_q3",
                    "type": "multiple_choice",
                    "question": f"Welche Herausforderung ist typisch beim Erlernen von {topic}?",
                    "options": [
                        "Option A: Komplexität der Konzepte",
                        "Option B: Mangel an Praxisbezug",
                        "Option C: Schnelle Entwicklung des Fachgebiets",
                        "Option D: Alle genannten Punkte",
                    ],
                    "correct_answer": "Option D: Alle genannten Punkte",
                    "explanation": "Beim Erlernen komplexer Themen treten oft mehrere Herausforderungen gleichzeitig auf.",
                    "difficulty": difficulty,
                    "topic": topic,
                }
            )

        return demo_questions[:question_count]

    # NOTE: Only one _parse_claude_response method should exist - using the first one above
