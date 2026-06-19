"""
Claude API Service for ExamCraft AI
Handles communication with Anthropic's Claude API for intelligent question generation
"""

import os
import httpx
import json
import asyncio
import time
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


# Process-local active-model override (TF-438). Startup validation and runtime
# fallback record the working model here so that freshly constructed
# ClaudeService instances — RAGService builds one per Celery task — start from
# the validated model instead of each repeatedly hitting (and alerting on) a
# retired primary. Bounded per worker process: the first task pays at most one
# 404, every subsequent instance starts clean.
_active_model_override: Optional[str] = None


class ModelUnavailableError(Exception):
    """Raised when every model in the configured fallback chain returns a 404
    ``not_found_error`` (TF-438).

    A retired model is a *permanent* condition, so callers — notably the Celery
    question-generation task — must treat this as non-retryable instead of
    looping forever like the TF-437 incident. It is the fail-fast that PR #149
    (TF-437) explicitly deferred to this ticket.
    """


class ClaudeService:
    """Service for interacting with Claude API with full production features"""

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.api_base_url = "https://api.anthropic.com/v1"
        self.base_url = f"{self.api_base_url}/messages"
        # Default model. Override per deployment via the CLAUDE_MODEL env var.
        # claude-sonnet-4-6 is the current Sonnet drop-in; the previous default
        # (claude-sonnet-4-20250514) was retired by Anthropic on 2026-06-15 and
        # now returns a 404 not_found_error (TF-437). Keep this in sync with the
        # active model list and the CLAUDE_MODEL secrets in prod.
        # A process-local override set by startup validation / runtime fallback
        # takes precedence so new instances skip a known-retired primary (TF-438).
        self.model = _active_model_override or os.getenv(
            "CLAUDE_MODEL", "claude-sonnet-4-6"
        )

        # TF-438: ordered fallback chain. When the active model returns a 404
        # not_found_error (Anthropic retired it), requests transparently fall
        # through to the next model instead of looping (TF-437). Deliberately
        # curated, NOT auto-latest: a model swap changes quality/cost/token
        # behaviour, so the chain is explicit. CLAUDE_MODEL_FALLBACK is a
        # comma-separated, ordered list; the default is one known-good model.
        fallback_env = os.getenv("CLAUDE_MODEL_FALLBACK", "claude-sonnet-4-5")
        self.fallback_models = [m.strip() for m in fallback_env.split(",") if m.strip()]
        # Full candidate list: primary first, then fallbacks, order-preserving
        # de-dup so an operator can repeat the primary in the fallback list
        # without it being tried twice.
        self.model_chain = list(dict.fromkeys([self.model, *self.fallback_models]))

        # Rate limiting configuration
        self.max_requests_per_minute = int(os.getenv("CLAUDE_MAX_RPM", "50"))
        self.max_tokens_per_request = int(os.getenv("CLAUDE_MAX_TOKENS", "4000"))

        # Retry configuration
        self.max_retries = int(os.getenv("CLAUDE_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("CLAUDE_RETRY_DELAY", "1.0"))
        # Timeout for API requests (default 120s for large prompts with context)
        self.request_timeout = float(os.getenv("CLAUDE_REQUEST_TIMEOUT", "120.0"))
        # Short, separate timeout for the lightweight Models-API startup check.
        # The check is awaited inline at boot, so a slow Models endpoint can delay
        # startup by at most model_check_timeout seconds, not the 120s request
        # timeout (TF-438).
        self.model_check_timeout = float(
            os.getenv("CLAUDE_MODEL_CHECK_TIMEOUT", "10.0")
        )

        # Cost tracking
        self.cost_per_input_token = 0.003 / 1000  # $3 per million input tokens
        self.cost_per_output_token = 0.015 / 1000  # $15 per million output tokens

        # Demo mode fallback.
        # TF-439: Der Gateway-Pfad braucht KEINEN direkten ANTHROPIC_API_KEY.
        # Ist der Gateway aktiv, darf ein fehlender Key NICHT in den Demo-Modus
        # fallen (sonst raisen generate_questions/generate_exam_async, bevor der
        # Gateway-Zweig erreicht wird, und der Schalter ist wirkungslos).
        from services import llm_gateway

        self.demo_mode = (
            not self.api_key and not llm_gateway.gateway_enabled()
        ) or os.getenv("CLAUDE_DEMO_MODE", "false").lower() == "true"

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

    def _api_headers(self) -> Dict[str, str]:
        """Shared Anthropic API headers (messages + models endpoints)."""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    def _activate_model(self, model: str, reason: str) -> None:
        """Promote ``model`` to the active model so subsequent requests — and
        newly constructed instances in this process — skip a dead primary
        (TF-438)."""
        if model == self.model:
            return
        global _active_model_override
        logger.warning(
            f"Switching active Claude model '{self.model}' -> '{model}' ({reason})"
        )
        self.model = model
        _active_model_override = model

    def _alert_model_retired(
        self, retired_model: str, next_model: Optional[str]
    ) -> None:
        """Emit a WARN/ERROR log + Sentry alert when a model returns 404 (TF-438)."""
        if next_model:
            message = (
                f"Claude model '{retired_model}' returned 404 not_found_error — "
                f"falling back to '{next_model}' (TF-438)"
            )
            level = "warning"
            logger.warning(message)
        else:
            message = (
                f"Claude model '{retired_model}' returned 404 not_found_error and "
                f"the fallback chain is exhausted — generation unavailable (TF-438)"
            )
            level = "error"
            logger.error(message)

        try:
            from config.sentry import capture_message_with_context

            capture_message_with_context(
                message,
                level=level,
                extra_context={
                    "retired_model": retired_model,
                    "next_model": next_model,
                    "model_chain": self.model_chain,
                },
                tags={"component": "claude_service", "issue": "TF-438"},
            )
        except Exception:  # pragma: no cover - alerting must not break requests
            logger.debug("Could not emit Sentry alert for retired model", exc_info=True)

    async def _make_api_request_with_retry(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Make an API request with retry logic and curated model fallback (TF-438).

        Transient errors (network, 5xx, 429) are retried against the *same*
        model with exponential backoff — they are also retryable upstream
        (Celery). A 404 ``not_found_error`` is permanent for that model
        (Anthropic retired it), so instead of burning retries we switch to the
        next model in the curated fallback chain. When every model returns 404,
        a :class:`ModelUnavailableError` is raised so the caller fails fast
        instead of looping (the fail-fast TF-437 deferred here).
        """
        # Try the currently-active model first, then the remaining chain.
        candidates = [self.model] + [m for m in self.model_chain if m != self.model]
        last_exception = None

        for model_index, model in enumerate(candidates):
            payload = {**payload, "model": model}
            model_retired = False

            for attempt in range(self.max_retries):
                try:
                    # Check rate limit
                    if not self._check_rate_limit():
                        wait_time = 60 - (time.time() - min(self.request_timestamps))
                        logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                        await asyncio.sleep(wait_time)

                    self._add_request_timestamp()

                    async with httpx.AsyncClient(
                        timeout=self.request_timeout
                    ) as client:
                        response = await client.post(
                            self.base_url,
                            headers=self._api_headers(),
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
                            f"Claude API call successful (model={model}) - "
                            f"Cost: ${cost:.4f}, Tokens: {input_tokens}+{output_tokens}"
                        )
                        # Promote a working fallback for subsequent requests
                        # (no-op when the primary itself succeeded).
                        if model != self.model:
                            self._activate_model(model, reason="runtime 404 fallback")
                        return result

                    elif response.status_code == 429:  # Rate limited
                        retry_after = int(
                            response.headers.get("retry-after", self.retry_delay)
                        )
                        # Record so a 429-only exhaustion surfaces the real cause
                        # (rate limiting) rather than a context-less generic error.
                        last_exception = Exception(
                            f"Claude API rate limited (429) for model '{model}'"
                        )
                        logger.warning(f"Rate limited by API, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue

                    elif response.status_code == 404:
                        # Permanent for this model — do NOT retry the same model.
                        last_exception = ModelUnavailableError(
                            f"Claude model '{model}' returned 404 not_found_error: "
                            f"{response.text}"
                        )
                        model_retired = True
                        break

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
                        wait_time = self.retry_delay * (2**attempt)  # backoff
                        logger.warning(
                            f"Claude API attempt {attempt + 1} failed (model={model}): "
                            f"{error_detail}, retrying in {wait_time}s"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"Claude API failed after {self.max_retries} attempts "
                            f"(model={model}): {error_detail}"
                        )
                        # Log full traceback for debugging
                        import traceback

                        logger.error(f"Full traceback:\n{traceback.format_exc()}")

            if model_retired:
                has_next = model_index < len(candidates) - 1
                next_model = candidates[model_index + 1] if has_next else None
                self._alert_model_retired(model, next_model)
                if has_next:
                    continue  # try the next model in the chain
                # Chain exhausted: permanent, non-retryable failure.
                raise last_exception
            else:
                # Transient exhaustion for this model. The model itself is fine,
                # so do NOT switch models — re-raise so Celery can retry.
                raise last_exception or Exception("Claude API request failed")

        # Defensive: empty candidate list should never happen.
        raise last_exception or Exception("Claude API request failed")

    async def _is_model_available(self, model: str) -> Optional[bool]:
        """Query ``GET /v1/models/{id}`` for a single model (TF-438).

        Returns ``True`` if the model is still served, ``False`` on a 404
        (retired), and ``None`` when the result is indeterminate (network
        error, timeout, or any other status) so the caller can fail open.
        """
        try:
            async with httpx.AsyncClient(timeout=self.model_check_timeout) as client:
                response = await client.get(
                    f"{self.api_base_url}/models/{model}",
                    headers=self._api_headers(),
                )
        except Exception as e:  # network/timeout — indeterminate
            logger.warning(f"Claude Models API check failed for '{model}': {e}")
            return None

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        logger.warning(
            f"Claude Models API returned {response.status_code} for '{model}'; "
            "treating as indeterminate"
        )
        return None

    async def validate_active_model(self) -> str:
        """Validate the active model against the Models API at startup (TF-438).

        Called once at FastAPI/Celery boot so a model retirement is caught at
        deploy/restart time instead of on the first customer request. Walks the
        curated chain and activates the first available model; emits an
        error-log + Sentry alert for each retired model.

        Fail-open: a missing API key, demo mode, or an unreachable Models API
        never raises — the per-request fallback in
        :meth:`_make_api_request_with_retry` remains the safety net. Returns the
        active model after validation.
        """
        if self.demo_mode or not self.api_key:
            logger.info(
                "Skipping Claude model startup validation (demo mode / no API key)"
            )
            return self.model

        candidates = [self.model] + [m for m in self.model_chain if m != self.model]

        for idx, model in enumerate(candidates):
            available = await self._is_model_available(model)

            if available is None:
                # Indeterminate — fail open and rely on per-request fallback.
                logger.warning(
                    f"Claude model startup validation inconclusive for '{model}' "
                    "(Models API unreachable); assuming available"
                )
                return self.model

            if available:
                if model != self.model:
                    self._activate_model(model, reason="startup validation fallback")
                else:
                    logger.info(
                        f"Claude model '{model}' validated as available at startup"
                    )
                return model

            # Retired (404) — alert and move to the next candidate.
            next_model = candidates[idx + 1] if idx + 1 < len(candidates) else None
            self._alert_model_retired(model, next_model)

        # Whole chain reported unavailable; keep the configured model so the
        # per-request path can surface a clean ModelUnavailableError later.
        return self.model

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
            question_types: Types of questions (single_choice, open_ended, etc.)
            language: Language for questions (de, en)

        Returns:
            List of generated questions
        """

        if self.demo_mode:
            raise RuntimeError(
                "Claude API is not configured (ANTHROPIC_API_KEY missing or CLAUDE_DEMO_MODE=true). "
                "Cannot generate questions."
            )

        prompt = self._build_prompt(
            topic, difficulty, question_count, question_types, language
        )

        # TF-439: Gateway-Pfad (typisierter Output) oder Legacy-httpx.
        from services import llm_gateway

        if llm_gateway.gateway_enabled():
            from services.gateway_generator import generate_questions_via_gateway

            return await generate_questions_via_gateway(prompt)

        payload = {
            "model": self.model,
            "max_tokens": min(self.max_tokens_per_request, 4000),
            "messages": [{"role": "user", "content": prompt}],
        }

        result = await self._make_api_request_with_retry(payload)
        content = result["content"][0]["text"]
        return self._parse_claude_response(content, topic, difficulty)

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
            question_types = exam_request.get("question_types", ["single_choice"])
            context = exam_request.get("context", "")
            language = exam_request.get("language", "de")
            custom_prompt = exam_request.get("custom_prompt")

            # Use custom prompt if provided (from Prompt Knowledge Base)
            if custom_prompt:
                logger.info(
                    f"Using custom prompt template ({len(custom_prompt)} chars)"
                )

                if self.demo_mode:
                    raise RuntimeError(
                        "Claude API is not configured. Cannot generate questions."
                    )

                from services import llm_gateway

                if llm_gateway.gateway_enabled():
                    from pydantic_ai.exceptions import ModelHTTPError

                    from services.gateway_generator import (
                        generate_questions_via_gateway,
                        generate_raw_via_gateway,
                    )

                    try:
                        questions = await generate_questions_via_gateway(custom_prompt)
                    # Transport-/Modellfehler durchreichen (TF-438-Klassifizierung):
                    # ModelUnavailableError = permanent (fail-fast),
                    # ModelHTTPError = transient (retrybar). Nur ein echtes
                    # Typed-Output-/Parsing-Versagen darf auf Roh-Markdown
                    # zurückfallen — sonst maskiert der Fallback eine 5xx-Blip.
                    except (ModelUnavailableError, ModelHTTPError):
                        raise
                    except Exception as e:  # typisierter Output fehlgeschlagen
                        logger.warning(
                            f"Gateway typed parse failed, returning raw Markdown: {e}"
                        )
                        content = await generate_raw_via_gateway(custom_prompt)
                        questions = [
                            {
                                "question": content,
                                "type": "markdown",
                                "raw_output": True,
                            }
                        ]
                else:
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
                        questions = self._parse_claude_response(
                            content, topic, difficulty
                        )
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
            logger.error(f"Exam generation failed: {e}", exc_info=True)
            raise

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
      "type": "single_choice",
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
            raise ValueError(f"Failed to parse Claude response: {e}") from e

    # NOTE: Only one _parse_claude_response method should exist - using the first one above


_claude_service_instance = None


def get_claude_service() -> "ClaudeService":
    global _claude_service_instance
    if _claude_service_instance is None:
        _claude_service_instance = ClaudeService()
    return _claude_service_instance


async def validate_claude_model_on_startup() -> None:
    """Startup hook to validate the active Claude model against the Models API
    and fall back if it has been retired (TF-438).

    Wired into both the FastAPI lifespan and the Celery worker boot. Fail-open:
    it never raises, so a flaky Models API or a transient error can never crash
    startup (it may delay it by at most model_check_timeout). Set
    ``CLAUDE_SKIP_MODEL_VALIDATION=true`` to disable (tests set this to avoid an
    external call at boot).
    """
    if os.getenv("CLAUDE_SKIP_MODEL_VALIDATION", "false").lower() == "true":
        logger.info(
            "Claude model startup validation disabled (CLAUDE_SKIP_MODEL_VALIDATION)"
        )
        return

    from services import llm_gateway

    if llm_gateway.gateway_enabled():
        logger.info(
            "Claude model startup validation skipped (Gateway aktiv; "
            "Gateway besitzt eigene Health/Fallback) — TF-439"
        )
        return

    try:
        service = get_claude_service()
        await service.validate_active_model()
    except Exception:  # pragma: no cover - startup must never crash on this
        logger.warning(
            "Claude model startup validation errored (ignored)", exc_info=True
        )
