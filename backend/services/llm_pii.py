# core/backend/services/llm_pii.py
"""PII minimisation for every request to the LLM gateway (TF-749).

All LLM traffic leaves ExamCraft through the clients built in
``services.llm_gateway``. They send their requests through
``RedactingTransport``/``AsyncRedactingTransport``, which rewrite the JSON
body of chat-completion and embedding requests before it hits the network.
Doing this at the transport means the guarantee holds for every call site
(generation, grading, chat, wizard, portfolio, embeddings) including future
ones, without each caller having to remember a helper.

Scope is deliberately narrow: only direct identifiers that a regex can
recognise without false positives on exam content (e-mail addresses, Swiss
AHV numbers). Arbitrary names in free text need NER and are out of scope;
where a caller knows whom a prompt is about (grading, portfolio), it
removes that person's name with ``redact_known`` before the call. Redaction
is one-way: the placeholders carry no information the model needs to
grade or generate.
"""

from __future__ import annotations

import itertools
import json
import logging
import re
import unicodedata
from typing import Any, Iterable

import httpx

EMAIL_PLACEHOLDER = "[E-MAIL]"
AHV_PLACEHOLDER = "[AHV-NR]"
NAME_PLACEHOLDER = "[NAME]"

logger = logging.getLogger(__name__)

# The look-behind anchors the match at the start of a local part; without it a
# long run of local-part characters without "@" costs quadratic time.
_EMAIL_RE = re.compile(
    r"(?<![A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
)
# Swiss social security number (AHV/AVS): 756 + 10 digits, optionally grouped
# as 756.XXXX.XXXX.XX. The digit boundaries keep longer numbers untouched.
_AHV_RE = re.compile(r"(?<!\d)756[.\s]?\d{4}[.\s]?\d{4}[.\s]?\d{2}(?!\d)")

# Only these endpoints carry user content. Other POSTs pass unchanged but are
# logged, so a new endpoint (e.g. the Responses API) cannot slip by unnoticed.
_REDACTED_PATH_SUFFIXES = ("/chat/completions", "/embeddings")


def redact_text(text: str) -> str:
    """Replace e-mail addresses and AHV numbers with fixed placeholders."""
    text = unicodedata.normalize("NFC", text)
    text = _EMAIL_RE.sub(EMAIL_PLACEHOLDER, text)
    return _AHV_RE.sub(AHV_PLACEHOLDER, text)


def _name_pattern(name: str) -> re.Pattern | None:
    """Full name with the separators found in file names, case-insensitive.

    Matches "Jennifer Meyer", "Meyer, Jennifer", "jennifer_meyer",
    "JenniferMeyer", and for double names "anna_lena_meyer" or
    "Müller-Schmid, Hans". All token orders are tried for names of up to
    four parts, plus first + last part. Single-token names return ``None``:
    a lone "Koch" or "Weber" is just as likely an ordinary word, and
    redacting it would damage exam or portfolio content. A surname alone
    therefore stays in the text.
    """
    tokens = [t for t in re.split(r"[\s,\-]+", name) if len(t.strip(".")) >= 2]
    if len(tokens) < 2:
        return None
    sep = r"[\s_.,\-]*"
    if len(tokens) <= 4:
        orders = [list(p) for p in itertools.permutations(tokens)]
    else:
        orders = [tokens, list(reversed(tokens))]
    if len(tokens) > 2:
        orders += [[tokens[0], tokens[-1]], [tokens[-1], tokens[0]]]
    # Longest alternatives first, so "Ana Maria Garcia" wins over "Ana Garcia".
    orders.sort(key=lambda o: -len(o))
    alternatives = "|".join(sep.join(re.escape(t) for t in o) for o in orders)
    return re.compile(rf"(?<![^\W\d_])(?:{alternatives})(?![^\W\d_])", re.IGNORECASE)


def redact_known(text: str, identifiers: Iterable[str | None]) -> str:
    """Remove identifiers of a known data subject, then apply ``redact_text``.

    For prompts about one person whose name/e-mail the caller knows (e.g.
    the student of a graded answer or portfolio). E-mail identifiers are
    removed verbatim, names via ``_name_pattern``; other identifiers (e.g.
    a numeric Moodle user id) are left alone. Text and identifiers are
    compared in Unicode NFC, because macOS ZIP paths and some PDF
    extractors deliver decomposed umlauts.
    """
    text = unicodedata.normalize("NFC", text)
    for identifier in identifiers:
        identifier = unicodedata.normalize("NFC", (identifier or "").strip())
        if not identifier:
            continue
        if "@" in identifier:
            text = re.sub(re.escape(identifier), EMAIL_PLACEHOLDER, text, flags=re.I)
            continue
        pattern = _name_pattern(identifier)
        if pattern is not None:
            text = pattern.sub(NAME_PLACEHOLDER, text)
    return redact_text(text)


def _redact_content(content: Any) -> Any:
    if isinstance(content, str):
        return redact_text(content)
    if isinstance(content, list):
        return [
            {**part, "text": redact_text(part["text"])}
            if isinstance(part, dict) and isinstance(part.get("text"), str)
            else part
            for part in content
        ]
    return content


def _redact_message(message: Any) -> Any:
    if not isinstance(message, dict):
        return message
    out = dict(message)
    if "content" in out:
        out["content"] = _redact_content(out["content"])
    if isinstance(out.get("tool_calls"), list):
        out["tool_calls"] = [
            {
                **call,
                "function": {
                    **call["function"],
                    "arguments": redact_text(call["function"]["arguments"]),
                },
            }
            if isinstance(call, dict)
            and isinstance(call.get("function"), dict)
            and isinstance(call["function"].get("arguments"), str)
            else call
            for call in out["tool_calls"]
        ]
    return out


def redact_payload(payload: dict) -> dict:
    """Redact the user-content fields of an OpenAI-style request body.

    Covers ``messages[].content`` (string or list of text parts) and
    ``messages[].tool_calls[].function.arguments`` for chat completions and
    ``input`` (string or list of strings) for embeddings. Model names, tool
    schemas and sampling parameters stay untouched.
    """
    out = dict(payload)
    if isinstance(out.get("messages"), list):
        out["messages"] = [_redact_message(m) for m in out["messages"]]
    if "input" in out:
        inputs = out["input"]
        if isinstance(inputs, str):
            out["input"] = redact_text(inputs)
        elif isinstance(inputs, list):
            out["input"] = [
                redact_text(item) if isinstance(item, str) else item for item in inputs
            ]
    return out


def _redacted_request(request: httpx.Request) -> httpx.Request:
    """Redacted copy of ``request``; fails closed on unreadable LLM bodies."""
    if request.method != "POST":
        return request
    if not request.url.path.endswith(_REDACTED_PATH_SUFFIXES):
        logger.warning(
            "TF-749: LLM-Gateway-POST an %s wird nicht redigiert", request.url.path
        )
        return request
    try:
        payload = json.loads(request.content)
    except (ValueError, httpx.RequestNotRead) as exc:
        raise RuntimeError(
            f"TF-749: Request-Body an {request.url.path} nicht lesbar, "
            "Versand ohne PII-Redaction abgebrochen"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"TF-749: Unerwarteter Request-Body an {request.url.path}, "
            "Versand ohne PII-Redaction abgebrochen"
        )

    body = json.dumps(redact_payload(payload)).encode()
    headers = httpx.Headers(request.headers)
    headers["content-length"] = str(len(body))
    return httpx.Request(
        request.method,
        request.url,
        headers=headers,
        content=body,
        extensions=request.extensions,
    )


class RedactingTransport(httpx.BaseTransport):
    """Sync transport wrapper for ``openai.OpenAI`` (grading, embeddings)."""

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self._inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self._inner.handle_request(_redacted_request(request))

    def close(self) -> None:
        self._inner.close()


class AsyncRedactingTransport(httpx.AsyncBaseTransport):
    """Async transport wrapper for ``AsyncOpenAI`` (pydantic-ai models)."""

    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await self._inner.handle_async_request(_redacted_request(request))

    async def aclose(self) -> None:
        await self._inner.aclose()
