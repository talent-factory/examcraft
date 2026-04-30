"""
Tests for the Document.title resolver chain (TF-331).

The resolver decides what label users see for each document. The choice
matters for findability — Office apps frequently set ``metadata.title`` to
defaults like "1", "Untitled", or "Document1" that are useless to the
uploader. The resolver order is:

1. ``display_name`` (user override) → wins unconditionally when set
2. ``doc_metadata['title']`` → only when meaningful (filtered)
3. ``original_filename`` (without extension) → always-present fallback
"""

import pytest

from models.document import Document, DocumentStatus, _is_meaningful_title


# ---------------------------------------------------------------------------
# _is_meaningful_title — pure function tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "",
        None,
        "  ",
        "a",  # too short
        "ab",  # too short
        "1",  # numeric placeholder Word leaves behind
        "2024",  # year-only
        "Untitled",
        "untitled document",
        "Document",
        "Dokument",
        "Document1",
        "dokument 42",
        "doc 7",
        "Datei1",
        "file 99",
        # Excel / PowerPoint defaults across DE/EN locales
        "Presentation",
        "Präsentation",
        "Presentation1",
        "Präsentation 3",
        "Workbook",
        "Arbeitsmappe",
        "Mappe1",
        "Mappe 2",
        "Book1",
        "Book 2",
        "Tabelle1",
        "Tabelle 7",
        "Sheet1",
        "Sheet 3",
    ],
)
def test_blocked_titles_are_not_meaningful(value):
    assert _is_meaningful_title(value) is False


@pytest.mark.parametrize(
    "value",
    [
        "Pareto-Prinzip",
        "Praktische Algorithmik mit Python",
        "Q4 Reporting 2025",
        "ISO 27001 Audit",
        "Mein Plan",  # 9 chars, not in blocklist
    ],
)
def test_meaningful_titles_pass(value):
    assert _is_meaningful_title(value) is True


# ---------------------------------------------------------------------------
# Document.title property — full resolver
# ---------------------------------------------------------------------------


def _doc(
    *,
    original_filename: str,
    metadata_title: str | None = None,
    display_name: str | None = None,
) -> Document:
    """Build an unsaved Document for property testing."""
    return Document(
        filename="x.docx",
        original_filename=original_filename,
        file_path="/tmp/x",
        file_size=1,
        mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        status=DocumentStatus.PROCESSED,
        doc_metadata={"title": metadata_title} if metadata_title is not None else None,
        display_name=display_name,
    )


def test_display_name_wins_over_metadata_and_filename():
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="Pareto-Prinzip",
        display_name="Mein Pareto-Dokument",
    )
    assert doc.title == "Mein Pareto-Dokument"


def test_meaningful_metadata_title_used_when_no_display_name():
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="Pareto-Prinzip",
    )
    assert doc.title == "Pareto-Prinzip"


def test_blocked_metadata_title_falls_back_to_filename():
    """The "1" case — the very bug TF-331 surfaces."""
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="1",
    )
    assert doc.title == "Pareto-Prinzip"


def test_untitled_metadata_falls_back_to_filename():
    doc = _doc(
        original_filename="Quartalsbericht.pdf",
        metadata_title="Untitled",
    )
    assert doc.title == "Quartalsbericht"


def test_no_metadata_uses_filename_stem():
    doc = _doc(original_filename="report.docx")
    assert doc.title == "report"


def test_filename_without_extension_returns_as_is():
    doc = _doc(original_filename="README")
    assert doc.title == "README"


def test_empty_display_name_treated_as_unset():
    """A whitespace-only display_name must not blank out the user-visible title."""
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="Pareto-Prinzip",
        display_name="   ",
    )
    assert doc.title == "Pareto-Prinzip"


def test_display_name_strips_whitespace():
    doc = _doc(
        original_filename="x.docx",
        display_name="  Mein Doc  ",
    )
    assert doc.title == "Mein Doc"


def test_to_dict_includes_both_resolved_title_and_raw_display_name():
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="1",
        display_name="Pareto Cheatsheet",
    )
    payload = doc.to_dict()
    assert payload["title"] == "Pareto Cheatsheet"
    assert payload["display_name"] == "Pareto Cheatsheet"
    assert payload["original_filename"] == "Pareto-Prinzip.docx"


def test_to_dict_display_name_null_when_unset():
    doc = _doc(
        original_filename="Pareto-Prinzip.docx",
        metadata_title="Pareto-Prinzip",
    )
    payload = doc.to_dict()
    assert payload["title"] == "Pareto-Prinzip"
    assert payload["display_name"] is None
