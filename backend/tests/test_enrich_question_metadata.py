"""Tests: get_bloom_levels() in scripts/enrich_question_metadata.py (TF-440).

TF-440 migrierte diesen Ops-Skript-Kern von der rohen anthropic-SDK
(client.messages.create, response.content[0].text) auf den Gateway
(OpenAI-Wire: client.chat.completions.create, response.choices[0].message.
content) — genau die Art typo-anfälliger Rename, die ein billiger Unit-Test
abfängt. Das Skript selbst (main()) bleibt ungetestet (DB-Fixtures nötig,
Ops-Skript ohne Live-Request-Pfad) — nur der SDK-Wire-Shape-Kern wird hier
abgedeckt.
"""

import json
import types

import pytest

from scripts.enrich_question_metadata import get_bloom_levels


class _FakeChatCompletions:
    def __init__(self, response_text, *, fail_with=None):
        self._response_text = response_text
        self._fail_with = fail_with
        self.last_kwargs = None

    def create(self, **kwargs):
        if self._fail_with is not None:
            raise self._fail_with
        self.last_kwargs = kwargs
        message = types.SimpleNamespace(content=self._response_text)
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


def _fake_client(response_text=None, *, fail_with=None):
    completions = _FakeChatCompletions(response_text, fail_with=fail_with)
    client = types.SimpleNamespace(chat=types.SimpleNamespace(completions=completions))
    return client, completions


def test_get_bloom_levels_uses_gateway_alias_and_parses_response():
    from services import llm_gateway

    client, completions = _fake_client(
        '[{"id": 1, "bloom_level": 3}, {"id": 2, "bloom_level": 5}]'
    )

    results = get_bloom_levels(
        client,
        [
            {"id": 1, "question": "Was ist ein Stack?", "type": "open_ended"},
            {"id": 2, "question": "Bewerte diesen Algorithmus.", "type": "open_ended"},
        ],
    )

    assert completions.last_kwargs["model"] == llm_gateway.ALIAS_GENERATION
    assert results == [
        {"id": 1, "bloom_level": 3},
        {"id": 2, "bloom_level": 5},
    ]


def test_get_bloom_levels_strips_markdown_fence():
    client, _ = _fake_client('```json\n[{"id": 1, "bloom_level": 2}]\n```')
    results = get_bloom_levels(
        client, [{"id": 1, "question": "q", "type": "open_ended"}]
    )
    assert results == [{"id": 1, "bloom_level": 2}]


def test_get_bloom_levels_raises_on_non_list_json():
    client, _ = _fake_client('{"id": 1, "bloom_level": 2}')  # dict, not list
    with pytest.raises(ValueError, match="Expected list from Gateway"):
        get_bloom_levels(client, [{"id": 1, "question": "q", "type": "open_ended"}])


def test_get_bloom_levels_raises_on_empty_choices():
    client = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: types.SimpleNamespace(choices=[])
            )
        )
    )
    with pytest.raises(ValueError, match="keine Choices"):
        get_bloom_levels(client, [{"id": 1, "question": "q", "type": "open_ended"}])


def test_get_bloom_levels_propagates_json_decode_error():
    """main()'s except json.JSONDecodeError-Zweig (unverändert von TF-440)
    verlangt, dass ein wirklich unparsbares Ergebnis als JSONDecodeError
    durchschlägt, nicht als generische Exception."""
    client, _ = _fake_client("nicht mal ein bisschen JSON")
    with pytest.raises(json.JSONDecodeError):
        get_bloom_levels(client, [{"id": 1, "question": "q", "type": "open_ended"}])
