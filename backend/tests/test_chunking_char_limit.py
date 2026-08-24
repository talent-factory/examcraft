"""Tests for the split chunking logic with a character upper limit (TF-445).

Ensures that oversized content is split during chunking, content-preserving,
into multiple complete chunks — instead of being truncated at the embedding
boundary (TF-442) —, that the ``chunk_index`` numbering stays
sequential/unique (Qdrant point ID safety), and that both processors
(default + legacy) enforce the upper limit.
"""

import pytest

from services.document_processors.chunking import (
    DEFAULT_MAX_CHARS_PER_CHUNK,
    _split_to_char_limit,
    create_chunks,
)
from services.document_processors.legacy_processor import LegacyProcessor
from services.document_processors.pymupdf_processor import PyMuPDFProcessor


def _strip_ws(text: str) -> str:
    """Content without whitespace — a robust "no content loss" invariant.

    The word-window/split path normalizes whitespace between words to
    single spaces; the whitespace-free content is therefore what gets
    compared.
    """
    return "".join(text.split())


class TestSplitToCharLimit:
    def test_short_text_returned_unchanged(self):
        assert _split_to_char_limit("hello world", 100) == ["hello world"]

    def test_single_oversized_word_hard_split_by_chars(self):
        # A block without whitespace (Base64 blob / minified code) is ONE
        # "word" and must be hard-split by character.
        word = "A" * 250
        pieces = _split_to_char_limit(word, 100)

        assert [len(p) for p in pieces] == [100, 100, 50]
        assert all(len(p) <= 100 for p in pieces)
        assert "".join(pieces) == word  # no content loss whatsoever

    def test_word_boundaries_preferred_over_hard_split(self):
        text = " ".join(["word"] * 50)  # 50*4 + 49 spaces = 249 characters
        pieces = _split_to_char_limit(text, 100)

        assert all(len(p) <= 100 for p in pieces)
        # No word is cut in the middle.
        for piece in pieces:
            assert all(token == "word" for token in piece.split())
        assert _strip_ws("".join(pieces)) == _strip_ws(text)

    def test_mixed_blob_and_words_preserves_content(self):
        blob = "B" * 250
        text = f"{blob} hello world"
        pieces = _split_to_char_limit(text, 100)

        assert all(len(p) <= 100 for p in pieces)
        assert _strip_ws("".join(pieces)) == _strip_ws(text)

    def test_word_exactly_at_limit_is_not_hard_split(self):
        # Guard is `len(word) > max_chars`, so a word of length exactly
        # max_chars stays undivided.
        word = "C" * 100
        assert _split_to_char_limit(word, 100) == [word]

    def test_empty_text_returns_empty_list(self):
        assert _split_to_char_limit("", 100) == []

    def test_max_chars_below_one_raises(self):
        with pytest.raises(ValueError):
            _split_to_char_limit("anything", 0)


class TestCreateChunksCharLimit:
    def test_oversized_blob_split_into_multiple_full_chunks(self):
        blob = "Q" * 5000
        chunks = create_chunks(blob, chunk_size=1000, chunk_overlap=200, max_chars=1000)

        assert len(chunks) == 5
        assert all(len(c.content) <= 1000 for c in chunks)
        # No content loss — unlike embedding truncation.
        assert "".join(c.content for c in chunks) == blob

    def test_chunk_index_sequential_and_unique(self):
        # A unique, sequential chunk_index is mandatory: generate_point_id
        # derives a deterministic UUID from it — collisions would cause
        # chunks in Qdrant to overwrite each other.
        blob = "Z" * 5000
        chunks = create_chunks(blob, 1000, 200, max_chars=1000)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))
        assert len(indices) == len(set(indices))

    def test_early_return_path_is_also_capped(self):
        # words <= chunk_size (a single mega-word) previously flowed unchecked
        # into a single giant chunk.
        blob = "x" * 3000
        chunks = create_chunks(blob, chunk_size=1000, chunk_overlap=200, max_chars=1000)

        assert len(chunks) == 3
        assert all(len(c.content) <= 1000 for c in chunks)

    def test_normal_text_below_cap_unchanged(self):
        text = "the quick brown fox jumps over the lazy dog"
        chunks = create_chunks(text, 1000, 200, max_chars=12000)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0
        # No split → no split markers in the metadata.
        assert "char_split_part" not in chunks[0].metadata

    def test_split_metadata_marks_parts(self):
        blob = "y" * 2500
        chunks = create_chunks(blob, 1000, 200, max_chars=1000)

        assert [c.metadata["char_split_part"] for c in chunks] == [1, 2, 3]
        assert all(c.metadata["char_split_parts"] == 3 for c in chunks)
        assert all(c.metadata["char_count"] == len(c.content) for c in chunks)

    def test_empty_and_whitespace_text_yields_no_chunks(self):
        assert create_chunks("", 1000, 200) == []
        assert create_chunks("   \n\t ", 1000, 200) == []

    def test_multiword_document_with_embedded_oversized_word(self):
        # > chunk_size words (overlap path) AND a mega-word in the middle:
        # all chunks must stay under the cap and the indices must be gapless.
        words = ["alpha"] * 1500
        words[700] = "M" * 3000
        text = " ".join(words)

        chunks = create_chunks(text, chunk_size=1000, chunk_overlap=200, max_chars=1000)

        assert all(len(c.content) <= 1000 for c in chunks)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_multiwindow_no_overlap_preserves_all_content(self):
        # Multiple word windows (overlap=0, i.e. no duplication) WITH a
        # mega-word: the multi-window path must not lose content, either at
        # the window boundary or during the character split.
        words = ["alpha"] * 1500
        words[700] = "M" * 3000
        text = " ".join(words)

        chunks = create_chunks(text, chunk_size=1000, chunk_overlap=0, max_chars=1000)

        assert all(len(c.content) <= 1000 for c in chunks)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
        assert _strip_ws("".join(c.content for c in chunks)) == _strip_ws(text)

    def test_word_count_invariant_holds_after_windowing(self):
        # Existing guarantee: word_count <= chunk_size per chunk. Multi-word
        # document above the window size, below the character cap (no char split).
        text = " ".join(["lorem"] * 2500)
        chunks = create_chunks(
            text, chunk_size=1000, chunk_overlap=200, max_chars=12000
        )

        assert len(chunks) > 1
        assert all(c.metadata["word_count"] <= 1000 for c in chunks)


class TestProcessorsEnforceCharLimit:
    @pytest.mark.parametrize("processor_cls", [PyMuPDFProcessor, LegacyProcessor])
    def test_processor_splits_oversized_blob(self, processor_cls):
        processor = processor_cls(
            chunk_size=1000, chunk_overlap=200, max_chars_per_chunk=1000
        )
        blob = "W" * 5000
        chunks = processor._create_chunks(blob)

        assert len(chunks) == 5
        assert all(len(c.content) <= 1000 for c in chunks)
        assert [c.chunk_index for c in chunks] == list(range(5))
        assert "".join(c.content for c in chunks) == blob

    @pytest.mark.parametrize("processor_cls", [PyMuPDFProcessor, LegacyProcessor])
    def test_processor_default_cap(self, processor_cls):
        assert processor_cls().max_chars_per_chunk == DEFAULT_MAX_CHARS_PER_CHUNK
