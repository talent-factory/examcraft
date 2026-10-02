# core/backend/tests/test_llm_pii_redaction.py
"""TF-749: direct identifiers never leave ExamCraft in an LLM request.

Every gateway client (``make_openai_client`` / ``make_pydantic_model``) sends
its requests through a redacting transport, so the guarantee holds for all
call sites (generation, grading, chat, wizard, portfolio, embeddings) without
touching each caller. The tests capture the bytes that would reach the
gateway and assert on them, not on an intermediate prompt string.
"""

import asyncio
import json
import re
import unicodedata

import httpx
import pytest

import services.llm_gateway as gw
from services import llm_pii

EMAIL = "anna.muster@schule-beispiel.ch"
AHV = "756.1234.5678.97"


def _chat_completion_body() -> dict:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 0,
        "model": "examcraft/grading",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "ok"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


def _embedding_body(n: int) -> dict:
    return {
        "object": "list",
        "model": "tf/embedding-small",
        "data": [
            {"object": "embedding", "index": i, "embedding": [0.0, 1.0]}
            for i in range(n)
        ],
        "usage": {"prompt_tokens": 1, "total_tokens": 1},
    }


def _handler(seen: list):
    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/embeddings"):
            body = json.loads(request.content)
            inputs = body["input"]
            n = len(inputs) if isinstance(inputs, list) else 1
            return httpx.Response(200, json=_embedding_body(n))
        return httpx.Response(200, json=_chat_completion_body())

    return handle


@pytest.fixture
def captured(monkeypatch):
    """Route the gateway clients' network layer into a recording mock."""
    monkeypatch.setenv("LLM_GATEWAY_URL", "http://gw:4000")
    monkeypatch.setenv("LLM_GATEWAY_API_KEY", "sk-test")
    seen: list[httpx.Request] = []
    monkeypatch.setattr(
        gw, "_network_transport", lambda: httpx.MockTransport(_handler(seen))
    )
    monkeypatch.setattr(
        gw,
        "_async_network_transport",
        lambda: httpx.MockTransport(_handler(seen)),
    )
    return seen


# --- redact_text ----------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        f"Bitte an {EMAIL} senden.",
        "Kontakt: Max.Meier+test@sub.example.org!",
        "MAILTO:LEHRER@SCHULE.DE",
    ],
)
def test_redact_text_removes_email_addresses(raw):
    out = llm_pii.redact_text(raw)
    assert "@" not in out
    assert llm_pii.EMAIL_PLACEHOLDER in out


@pytest.mark.parametrize("ahv", [AHV, "7561234567897", "756 1234 5678 97"])
def test_redact_text_removes_swiss_ahv_numbers(ahv):
    out = llm_pii.redact_text(f"AHV-Nr. {ahv} der Lernenden")
    assert "1234" not in out
    assert llm_pii.AHV_PLACEHOLDER in out


@pytest.mark.parametrize(
    "text",
    [
        "Berechnen Sie 3.14 * 2 = 6.28 und 1'234.50 CHF.",
        "Der Termin ist am 12.03.2026 um 14:30.",
        "Ein Python-Decorator wie @property oder @staticmethod.",
        "Die Telefonnummer 0791234567 ist fiktiv.",
        "Bestellnummer 7561234 und Zahl 756123456789012345.",
    ],
)
def test_redact_text_leaves_regular_exam_content_unchanged(text):
    assert llm_pii.redact_text(text) == text


def test_redact_payload_covers_chat_and_embedding_shapes():
    payload = {
        "model": "examcraft/chat",
        "messages": [
            {"role": "system", "content": f"System {EMAIL}"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Teil {EMAIL}"},
                    {"type": "image_url", "image_url": {"url": "data:x"}},
                ],
            },
            {"role": "tool", "tool_call_id": "t1", "content": f"Tool {AHV}"},
        ],
    }
    out = llm_pii.redact_payload(payload)
    dumped = json.dumps(out)
    assert EMAIL not in dumped and AHV not in dumped
    assert out["model"] == "examcraft/chat"
    assert out["messages"][1]["content"][1] == payload["messages"][1]["content"][1]

    emb = llm_pii.redact_payload({"model": "m", "input": [EMAIL, "frei"]})
    assert emb["input"] == [llm_pii.EMAIL_PLACEHOLDER, "frei"]
    assert llm_pii.redact_payload({"model": "m", "input": EMAIL})["input"] == (
        llm_pii.EMAIL_PLACEHOLDER
    )


# --- end-to-end through the gateway factories -----------------------------


def test_openai_client_chat_request_contains_no_identifiers(captured):
    client = gw.make_openai_client()
    client.chat.completions.create(
        model=gw.ALIAS_GRADING,
        messages=[
            {"role": "system", "content": "Bewerte die Antwort."},
            {
                "role": "user",
                "content": f"Antwort: Ich bin erreichbar unter {EMAIL}, AHV {AHV}.",
            },
        ],
    )
    assert len(captured) == 1
    body = captured[0].content.decode()
    assert EMAIL not in body
    assert AHV not in body
    assert llm_pii.EMAIL_PLACEHOLDER in body
    # Content-Length must match the rewritten body, not the original one.
    assert int(captured[0].headers["content-length"]) == len(captured[0].content)


def test_openai_client_embedding_request_contains_no_identifiers(captured):
    client = gw.make_openai_client()
    client.embeddings.create(
        model=gw.ALIAS_EMBEDDING, input=[f"Chunk mit {EMAIL}", "harmlos"]
    )
    body = captured[0].content.decode()
    assert EMAIL not in body
    assert "harmlos" in body


def test_pydantic_model_request_contains_no_identifiers(captured):
    from pydantic_ai import Agent

    agent = Agent(gw.make_pydantic_model(gw.ALIAS_CHAT), system_prompt="Hilf.")
    result = asyncio.run(agent.run(f"Meine Adresse ist {EMAIL}"))
    assert result.output == "ok"
    assert captured, "no request reached the transport"
    for request in captured:
        assert EMAIL not in request.content.decode()


def test_non_json_requests_pass_through_unchanged(captured):
    transport = llm_pii.RedactingTransport(httpx.MockTransport(_handler(captured)))
    with httpx.Client(transport=transport) as client:
        client.post("http://gw:4000/v1/files", content=b"raw " + EMAIL.encode())
    assert captured[0].content == b"raw " + EMAIL.encode()


# --- redact_known: identifiers of the data subject known to the caller -----


@pytest.mark.parametrize(
    "text",
    [
        "Ich, Jennifer Meyer, habe das Projekt geleitet.",
        "MEYER, JENNIFER — Abschlussbericht",
        "portfolio/jennifer_meyer/Bericht.pdf",
        "Phase1/JenniferMeyer-Reflexion.docx",
        "Kontakt: jennifer.meyer@schule.ch",
    ],
)
def test_redact_known_removes_full_name_variants(text):
    out = llm_pii.redact_known(text, ["Jennifer Meyer", "jennifer.meyer@schule.ch"])
    assert "jennifer" not in out.lower()
    assert "meyer" not in out.lower()


def test_redact_known_keeps_single_name_tokens_and_unrelated_text():
    """Single tokens are not redacted: 'Koch' or 'Weber' are also words."""
    text = "Der Koch kocht. Max Weber war Soziologe."
    assert llm_pii.redact_known(text, ["Anna Koch"]) == text


def test_redact_known_ignores_empty_and_single_token_identifiers():
    text = "Antwort von Test."
    assert llm_pii.redact_known(text, [None, "", "Test", "  "]) == text


def test_redact_known_also_applies_generic_rules():
    out = llm_pii.redact_known(f"Mail {EMAIL}, AHV {AHV}", [])
    assert EMAIL not in out and AHV not in out


# --- review follow-ups (PR #381) -------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # macOS ZIP paths and some PDF extractors use decomposed umlauts (NFD).
        unicodedata.normalize("NFD", "Portfolio/Jürg_Müller/Bericht.pdf"),
        "JÜRG MÜLLER: Reflexion",
    ],
)
def test_redact_known_matches_umlaut_names_in_any_unicode_form(text):
    out = llm_pii.redact_known(text, ["Jürg Müller"])
    folded = unicodedata.normalize("NFC", out).lower()
    assert "müller" not in folded and "jürg" not in folded


@pytest.mark.parametrize(
    "name, text",
    [
        ("Anna-Lena Meyer", "anna_lena_meyer/bericht.pdf"),
        ("Anna-Lena Meyer", "Meyer Anna-Lena"),
        ("Hans Müller-Schmid", "Müller-Schmid, Hans"),
        ("Ana Maria Garcia", "Garcia Ana Maria"),
        ("Ana Maria Garcia", "Ana Garcia"),
    ],
)
def test_redact_known_handles_multi_part_names(name, text):
    out = llm_pii.redact_known(text, [name])
    assert out.strip() in {
        llm_pii.NAME_PLACEHOLDER,
        f"{llm_pii.NAME_PLACEHOLDER}/bericht.pdf",
    }


def test_email_regex_stays_linear_on_long_tokens():
    import time

    blob = "a" * 100_000
    start = time.perf_counter()
    assert llm_pii.redact_text(blob) == blob
    assert time.perf_counter() - start < 0.5


def test_redacts_tool_call_arguments():
    payload = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "t1",
                        "type": "function",
                        "function": {"name": "f", "arguments": f'{{"m": "{EMAIL}"}}'},
                    }
                ],
            }
        ]
    }
    out = llm_pii.redact_payload(payload)
    assert EMAIL not in json.dumps(out)
    assert out["messages"][0]["tool_calls"][0]["function"]["name"] == "f"


def test_unparsable_body_on_redacted_path_fails_closed(captured):
    transport = llm_pii.RedactingTransport(httpx.MockTransport(_handler(captured)))
    with httpx.Client(transport=transport) as client, pytest.raises(RuntimeError):
        client.post(
            "http://gw:4000/v1/chat/completions", content=b"not json " + EMAIL.encode()
        )
    assert captured == []


def test_unknown_post_path_logs_warning(captured, monkeypatch):
    warnings = []
    monkeypatch.setattr(llm_pii.logger, "warning", lambda *a, **k: warnings.append(a))
    transport = llm_pii.RedactingTransport(httpx.MockTransport(_handler(captured)))
    with httpx.Client(transport=transport) as client:
        client.post("http://gw:4000/v1/files", content=b"x")
    assert warnings and "/v1/files" in str(warnings[0])


def test_no_llm_client_is_built_outside_the_gateway_factories():
    """Redaction lives in the factories; a direct client would bypass it."""
    import pathlib

    repo = pathlib.Path(__file__).resolve().parents[3]
    pattern = re.compile(r"\b(?:Async)?OpenAI\(|\b(?:Async)?Anthropic\(")
    offenders = []
    for tier in ("core", "premium", "enterprise"):
        root = repo / tier / "backend"
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            rel = path.relative_to(repo).as_posix()
            if "/tests/" in rel or rel.endswith("services/llm_gateway.py"):
                continue
            if pattern.search(path.read_text(encoding="utf-8", errors="ignore")):
                offenders.append(rel)
    assert offenders == []
