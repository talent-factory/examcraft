"""Tests for the shared download-filename helper.

Both the exam export (``api/exams.py``) and the grade export
(``api/grade_export.py``) build ``Content-Disposition`` headers from a
user-supplied exam title. They used to do it with two independent
implementations that disagreed; these tests pin the single shared one.
"""

from urllib.parse import unquote

import pytest

from utils.download_filename import (
    content_disposition,
    filename_stem,
    sanitize_filename,
)


def _names(disposition: str) -> tuple[str, str]:
    """Return ``(ascii_filename, decoded_filename_star)``."""
    import re

    ascii_name = re.search(r'filename="([^"]*)"', disposition).group(1)
    encoded = re.search(r"filename\*=UTF-8''(\S+)", disposition).group(1)
    return ascii_name, unquote(encoded)


class TestSanitizeFilename:
    @pytest.mark.parametrize("forbidden", list('\\/:*?"<>|'))
    def test_removes_characters_windows_forbids(self, forbidden):
        assert forbidden not in sanitize_filename(f"a{forbidden}b")

    def test_keeps_spaces_capitals_ampersand_and_accents(self):
        assert sanitize_filename("Algorithmen & Größe — Prüfung") == (
            "Algorithmen & Größe — Prüfung"
        )

    def test_collapses_runs_of_whitespace(self):
        assert sanitize_filename("a   \t b") == "a b"

    def test_strips_leading_and_trailing_spaces_and_dots(self):
        assert sanitize_filename("  .Randfall.  ") == "Randfall"

    def test_removes_control_characters_and_newlines(self):
        # The quote, CRLF and colon go; the hyphen is harmless and stays.
        assert sanitize_filename('ev"il\r\nX-Injected: yes') == "ev il X-Injected yes"


class TestFilenameStem:
    def test_truncates_to_the_configured_length(self):
        assert len(filename_stem("A" * 200, max_length=50)) == 50

    def test_a_realistic_exam_title_survives_intact(self):
        """55 characters is an ordinary exam title. The old 50-char cap cut
        it after "FS", silently dropping the year."""
        title = "Algorithmen & Datenstrukturen — Semesterprüfung FS 2026"
        assert filename_stem(title) == title

    def test_overlong_titles_are_cut_at_a_word_boundary(self):
        title = (
            "Einführung in die Algorithmen und Datenstrukturen für Studierende "
            "des dritten Semesters"
        )
        stem = filename_stem(title)
        assert len(stem) <= 80
        # No word is cut in half.
        assert title.startswith(stem)
        assert title[len(stem)] == " "

    def test_a_single_overlong_word_is_still_cut_hard(self):
        """Without a space there is no boundary to respect — the cap wins."""
        assert len(filename_stem("A" * 200)) == 80

    def test_empty_title_falls_back(self):
        assert filename_stem("   ...   ") == "export"

    @pytest.mark.parametrize("reserved", ["CON", "nul", "Com1", "LPT9"])
    def test_windows_device_names_are_prefixed(self, reserved):
        stem = filename_stem(reserved)
        assert stem.upper() != reserved.upper()
        assert reserved.lower() in stem.lower()

    def test_a_title_merely_containing_a_device_name_is_untouched(self):
        assert filename_stem("Console Grundlagen") == "Console Grundlagen"


class TestContentDisposition:
    def test_emits_both_filename_parameters(self):
        ascii_name, real_name = _names(content_disposition("Prüfung & Co.pdf"))
        assert ascii_name == "Prufung & Co.pdf"
        assert real_name == "Prüfung & Co.pdf"

    def test_header_is_latin1_encodable(self):
        # HTTP headers are latin-1; an em dash would otherwise raise.
        content_disposition("Kapitel — Eins.pdf").encode("latin-1")

    def test_non_ascii_only_title_keeps_a_usable_ascii_name(self):
        ascii_name, real_name = _names(content_disposition("試験.pdf"))
        assert ascii_name == "export.pdf"
        assert real_name == "試験.pdf"

    def test_name_without_extension_is_handled(self):
        ascii_name, _ = _names(content_disposition("Prüfung"))
        assert ascii_name == "Prufung"

    def test_quotes_and_crlf_cannot_escape_the_header(self):
        disposition = content_disposition('ev"il\r\nX-Injected: yes.pdf')
        assert "\r" not in disposition and "\n" not in disposition
        assert disposition.count('"') == 2

    def test_fullwidth_quote_cannot_escape_the_header_after_transliteration(self):
        """NFKD decomposes lookalikes like the fullwidth quotation mark
        (U+FF02) to a literal ``"`` *after* the forbidden-character filter
        has already run, so the filter must catch it again post-NFKD too."""
        disposition = content_disposition("Pr＂fung＼x.pdf")
        assert disposition.count('"') == 2
        ascii_name, _ = _names(disposition)
        assert '"' not in ascii_name
        assert "\\" not in ascii_name

    def test_transliterated_reserved_device_name_is_prefixed(self):
        """Accented characters that fully collapse to a Windows-reserved
        device name under NFKD transliteration must be caught in the ASCII
        fallback too, not just checked against the pre-transliteration
        stem (which never equals a bare reserved name here)."""
        ascii_name, _ = _names(content_disposition("ÇÖÑ.pdf"))
        assert ascii_name.upper() != "CON.PDF"
