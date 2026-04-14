"""Tests for docs URL converter."""

from services.docs_url_converter import convert_docs_path_to_url


def test_basic_german_path():
    result = convert_docs_path_to_url("core/docs-site/docs/user-guide/documents.md")
    assert result == "https://docs.examcraft.ch/user-guide/documents/"


def test_english_path():
    result = convert_docs_path_to_url("core/docs-site/docs/user-guide/documents.en.md")
    assert result == "https://docs.examcraft.ch/en/user-guide/documents/"


def test_index_file_german():
    result = convert_docs_path_to_url("core/docs-site/docs/user-guide/index.md")
    assert result == "https://docs.examcraft.ch/user-guide/"


def test_index_file_english():
    result = convert_docs_path_to_url("core/docs-site/docs/user-guide/index.en.md")
    assert result == "https://docs.examcraft.ch/en/user-guide/"


def test_root_index():
    result = convert_docs_path_to_url("core/docs-site/docs/index.md")
    assert result == "https://docs.examcraft.ch/"


def test_custom_base_url():
    result = convert_docs_path_to_url(
        "core/docs-site/docs/faq.md",
        base_url="https://custom.example.com",
    )
    assert result == "https://custom.example.com/faq/"


def test_nested_path():
    result = convert_docs_path_to_url(
        "core/docs-site/docs/admin/settings/permissions.md"
    )
    assert result == "https://docs.examcraft.ch/admin/settings/permissions/"


def test_custom_docs_site_path():
    result = convert_docs_path_to_url(
        "other/path/docs/guide.md",
        docs_site_path="other/path/docs",
    )
    assert result == "https://docs.examcraft.ch/guide/"


def test_path_without_docs_prefix_still_converted():
    """If path doesn't start with docs_site_path, still apply URL conversion rules."""
    result = convert_docs_path_to_url("random/file.md")
    assert result == "https://docs.examcraft.ch/random/file/"
