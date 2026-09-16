"""
Unit tests for the internal HelpService methods that existing help test
files don't exercise directly: `_try_faq_cache`, `_search_docs`, the
no-JSON-match / error branches of `_call_claude`, the `answer_question`
error-handling branches, and the locale-message helpers.

`vector_service` is patched at both import sites (`services.help_service`
for the module-level import used by `_try_faq_cache`, and
`services.vector_service_factory` for `_search_docs`'s local re-import).
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.help_service import ClaudeAPIError, HelpService, VectorSearchError


def _patched_vector_service(mock):
    return (
        patch("services.help_service.vector_service", mock),
        patch("services.vector_service_factory.vector_service", mock),
    )


@pytest.fixture
def db():
    return MagicMock()


@pytest.fixture
def service(db):
    return HelpService(db)


class TestTryFaqCache:
    @pytest.mark.asyncio
    async def test_no_client_returns_none(self, service):
        mock_vs = SimpleNamespace(client=None)
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Wie logge ich mich ein?", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_embeddings_returns_none(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[])
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_no_points_returns_none(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[])
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_low_score_returns_none(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        point = SimpleNamespace(score=0.5, payload={"faq_id": 1})
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_missing_faq_id_returns_none(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        point = SimpleNamespace(score=0.99, payload={})
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_faq_not_found_in_db_returns_none(self, service, db):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        point = SimpleNamespace(score=0.99, payload={"faq_id": 42})
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])
        db.query.return_value.filter.return_value.first.return_value = None
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None

    @pytest.mark.asyncio
    async def test_hit_increments_count_and_returns_answer_de(self, service, db):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        point = SimpleNamespace(score=0.99, payload={"faq_id": 42})
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])

        faq = SimpleNamespace(
            hit_count=3,
            answer_de="Deutsche Antwort",
            answer_en="English answer",
            docs_links=["/docs/a"],
        )
        db.query.return_value.filter.return_value.first.return_value = faq

        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")

        assert faq.hit_count == 4
        db.commit.assert_called_once()
        assert result == {
            "answer": "Deutsche Antwort",
            "confidence": 1.0,
            "sources": [],
            "docs_links": ["/docs/a"],
            "escalate": False,
            "from_cache": True,
        }

    @pytest.mark.asyncio
    async def test_hit_returns_answer_en_for_en_locale(self, service, db):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[MagicMock()])
        point = SimpleNamespace(score=0.99, payload={"faq_id": 1})
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])

        faq = SimpleNamespace(
            hit_count=None,
            answer_de="Deutsche Antwort",
            answer_en="English answer",
            docs_links=None,
        )
        db.query.return_value.filter.return_value.first.return_value = faq

        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Question", "en")

        assert faq.hit_count == 1
        assert result["answer"] == "English answer"
        assert result["docs_links"] == []

    @pytest.mark.asyncio
    async def test_exception_is_caught_and_returns_none(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(side_effect=RuntimeError("qdrant down"))
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._try_faq_cache("Frage", "de")
        assert result is None


class TestSearchDocs:
    @pytest.mark.asyncio
    async def test_no_client_raises_vector_search_error(self, service):
        mock_vs = SimpleNamespace(client=None)
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            with pytest.raises(VectorSearchError):
                await service._search_docs("Frage")

    @pytest.mark.asyncio
    async def test_empty_embeddings_returns_empty_list(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(return_value=[])
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._search_docs("Frage")
        assert result == []

    @pytest.mark.asyncio
    async def test_success_maps_points_to_chunks(self, service):
        mock_vs = MagicMock(client=MagicMock())
        embedding = MagicMock()
        embedding.tolist.return_value = [0.1, 0.2]
        mock_vs.create_embeddings = AsyncMock(return_value=[embedding])
        point = SimpleNamespace(
            score=0.87,
            payload={
                "content_preview": "Inhalt",
                "source_file": "docs/a.md",
                "section_title": "Abschnitt",
                "language": "de",
            },
        )
        mock_vs.client.query_points.return_value = SimpleNamespace(points=[point])

        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            result = await service._search_docs("Frage")

        assert result == [
            {
                "content": "Inhalt",
                "source_file": "docs/a.md",
                "section": "Abschnitt",
                "language": "de",
                "score": 0.87,
            }
        ]

    @pytest.mark.asyncio
    async def test_exception_reraised_as_vector_search_error(self, service):
        mock_vs = MagicMock(client=MagicMock())
        mock_vs.create_embeddings = AsyncMock(side_effect=RuntimeError("boom"))
        p1, p2 = _patched_vector_service(mock_vs)
        with p1, p2:
            with pytest.raises(VectorSearchError):
                await service._search_docs("Frage")


class TestCallClaudeEdgeCases:
    @pytest.mark.asyncio
    async def test_no_json_in_response_returns_raw_text(self, service, monkeypatch):
        from pydantic_ai.models.test import TestModel
        import services.llm_gateway as gw

        monkeypatch.setattr(
            gw,
            "make_pydantic_model",
            lambda alias, **_k: TestModel(
                custom_output_text="Das ist eine reine Textantwort ohne JSON."
            ),
        )

        result = await service._call_claude(
            question="Frage",
            chunks=[
                {
                    "content": "Inhalt",
                    "source_file": "docs/a.md",
                    "section": "Abschnitt",
                    "language": "de",
                    "score": 0.9,
                }
            ],
            user_role="teacher",
            user_tier="free",
            route="/help",
            history=None,
            locale="de",
        )

        assert result["answer"] == "Das ist eine reine Textantwort ohne JSON."
        assert result["confidence"] == 0.5
        assert result["docs_links"] == []
        assert result["sources"][0]["file"] == "docs/a.md"
        assert result["sources"][0]["section"] == "Abschnitt"

    @pytest.mark.asyncio
    async def test_agent_failure_raises_claude_api_error(self, service, monkeypatch):
        import services.llm_gateway as gw

        def boom(_alias, **_kwargs):
            raise RuntimeError("gateway unreachable")

        monkeypatch.setattr(gw, "make_pydantic_model", boom)

        with pytest.raises(ClaudeAPIError):
            await service._call_claude(
                question="Frage",
                chunks=[
                    {
                        "content": "Inhalt",
                        "source_file": "docs/a.md",
                        "section": "Abschnitt",
                        "language": "de",
                        "score": 0.9,
                    }
                ],
                user_role="teacher",
                user_tier="free",
                route="/help",
                history=None,
                locale="de",
            )


class TestAnswerQuestionErrorBranches:
    @pytest.mark.asyncio
    async def test_returns_cached_answer_without_search(self, service):
        cached = {
            "answer": "Gecachte Antwort",
            "confidence": 1.0,
            "sources": [],
            "docs_links": [],
            "escalate": False,
            "from_cache": True,
        }
        with patch.object(service, "_try_faq_cache", AsyncMock(return_value=cached)):
            with patch.object(service, "_search_docs") as mock_search:
                result = await service.answer_question(
                    question="Frage",
                    user_role="teacher",
                    user_tier="free",
                    route="/help",
                )

        assert result == cached
        mock_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_vector_search_error_returns_service_error_message(self, service):
        with patch.object(service, "_try_faq_cache", AsyncMock(return_value=None)):
            with patch.object(
                service,
                "_search_docs",
                AsyncMock(side_effect=VectorSearchError("down")),
            ):
                result = await service.answer_question(
                    question="Frage",
                    user_role="teacher",
                    user_tier="free",
                    route="/help",
                    locale="en",
                )

        assert result["confidence"] == 0.0
        assert result["escalate"] is False
        assert "temporarily unavailable" in result["answer"]

    @pytest.mark.asyncio
    async def test_claude_api_error_returns_service_error_message(self, service):
        chunks = [
            {
                "content": "x",
                "source_file": "a.md",
                "section": "s",
                "language": "de",
                "score": 0.9,
            }
        ]
        with patch.object(service, "_try_faq_cache", AsyncMock(return_value=None)):
            with patch.object(service, "_search_docs", AsyncMock(return_value=chunks)):
                with patch.object(
                    service,
                    "_call_claude",
                    AsyncMock(side_effect=ClaudeAPIError("boom")),
                ):
                    result = await service.answer_question(
                        question="Frage",
                        user_role="teacher",
                        user_tier="free",
                        route="/help",
                        locale="de",
                    )

        assert result["confidence"] == 0.0
        assert "vorübergehend nicht verfügbar" in result["answer"]


class TestMessageHelpers:
    def test_no_answer_message_english(self, service):
        assert "couldn't find" in service._no_answer_message("en")

    def test_no_answer_message_german(self, service):
        assert "keine passende Antwort" in service._no_answer_message("de")

    def test_service_error_message_german(self, service):
        assert "vorübergehend nicht verfügbar" in service._service_error_message("de")

    def test_service_error_message_english(self, service):
        assert "temporarily unavailable" in service._service_error_message("en")

    def test_error_message_german(self, service):
        assert "Fehler aufgetreten" in service._error_message("de")

    def test_error_message_english(self, service):
        assert "error occurred" in service._error_message("en")
