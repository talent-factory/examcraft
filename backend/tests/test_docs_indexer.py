"""Tests for DocsIndexerService (TF-308)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.docs_indexer_service import DocsIndexerService


def test_parse_markdown_into_chunks():
    service = DocsIndexerService.__new__(DocsIndexerService)
    content = (
        "# Title\n\nFirst paragraph with enough content to pass the length check.\n\n"
        "## Section 2\n\nSecond paragraph with enough content to pass the length check."
    )
    chunks = service._parse_markdown(content, "test.md", "de")

    assert len(chunks) >= 2
    assert chunks[0]["section_title"] == "Title"
    assert "First paragraph" in chunks[0]["content"]


def test_detect_language_from_filename():
    service = DocsIndexerService.__new__(DocsIndexerService)
    assert service._detect_language("docs.en.md") == "en"
    assert service._detect_language("docs.md") == "de"
    assert service._detect_language("guide.en.md") == "en"


def test_parse_empty_content_returns_no_chunks():
    service = DocsIndexerService.__new__(DocsIndexerService)
    chunks = service._parse_markdown("", "empty.md", "de")
    assert chunks == []


def test_parse_short_sections_skipped():
    service = DocsIndexerService.__new__(DocsIndexerService)
    content = (
        "# Title\n\nOK\n\n## Section\n\nThis is a longer paragraph with enough content."
    )
    chunks = service._parse_markdown(content, "test.md", "de")
    # "OK" has < 20 chars so it's skipped
    assert all(len(c["content"]) >= 20 for c in chunks)


@pytest.mark.asyncio
async def test_full_scan_clears_collection_before_indexing():
    """full_scan=True must delete all points from docs_help before re-indexing."""
    mock_db = MagicMock()
    # HelpIndexState query returns None → triggers full_scan
    mock_db.query.return_value.first.return_value = None
    mock_db.add = MagicMock()
    mock_db.commit = MagicMock()

    service = DocsIndexerService(mock_db)

    mock_client = MagicMock()
    mock_vector_service = MagicMock()
    mock_vector_service.client = mock_client
    mock_vector_service.create_embeddings = AsyncMock(return_value=[])

    with (
        patch(
            "services.docs_indexer_service.DocsIndexerService._get_all_md_files",
            return_value=[],
        ),
        patch(
            "services.docs_indexer_service.DocsIndexerService._get_current_sha",
            return_value="abc123" * 6 + "abcd",
        ),
        patch(
            "services.vector_service_factory.vector_service",
            mock_vector_service,
        ),
    ):
        await service.run_index(full_scan=True)

    # Verify collection was cleared
    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args
    assert call_kwargs[1]["collection_name"] == "docs_help"


@pytest.mark.asyncio
async def test_incremental_scan_does_not_clear_collection():
    """full_scan=False should NOT delete all points."""
    mock_db = MagicMock()
    mock_state = MagicMock()
    mock_state.last_indexed_sha = "a" * 40
    mock_db.query.return_value.first.return_value = mock_state
    mock_db.commit = MagicMock()

    service = DocsIndexerService(mock_db)

    mock_client = MagicMock()
    mock_vector_service = MagicMock()
    mock_vector_service.client = mock_client

    with (
        patch(
            "services.docs_indexer_service.DocsIndexerService._get_changed_files",
            return_value=([], []),
        ),
        patch(
            "services.docs_indexer_service.DocsIndexerService._get_current_sha",
            return_value="b" * 40,
        ),
        patch(
            "services.vector_service_factory.vector_service",
            mock_vector_service,
        ),
    ):
        await service.run_index(full_scan=False)

    # delete should NOT have been called (no full clear)
    mock_client.delete.assert_not_called()


def test_invalid_sha_falls_back_to_full_scan():
    service = DocsIndexerService.__new__(DocsIndexerService)
    with patch.object(
        service, "_get_all_md_files", return_value=["a.md", "b.md"]
    ) as mock_all:
        changed, deleted = service._get_changed_files("not-a-valid-sha; rm -rf /")
        assert changed == ["a.md", "b.md"]
        assert deleted == []
        mock_all.assert_called_once()
