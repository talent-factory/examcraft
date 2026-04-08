"""Tests for DocsIndexerService (TF-308)."""

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
