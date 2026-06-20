"""Tests für die geteilte Chunking-Logik mit Zeichen-Obergrenze (TF-445).

Stellt sicher, dass über-lange Inhalte beim Chunking inhaltserhaltend in
mehrere vollständige Chunks gesplittet werden — statt am Embedding-Boundary
getrunct zu werden (TF-442) —, dass die ``chunk_index``-Nummerierung
fortlaufend/eindeutig bleibt (Qdrant-Point-ID-Sicherheit) und dass beide
Prozessoren (Default + Legacy) die Obergrenze durchsetzen.
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
    """Inhalt ohne Whitespace — robuste „kein Inhaltsverlust"-Invariante.

    Der Wort-Fenster-/Split-Pfad normalisiert Whitespace zwischen Wörtern zu
    einfachen Leerzeichen; verglichen wird daher der whitespace-freie Inhalt.
    """
    return "".join(text.split())


class TestSplitToCharLimit:
    def test_short_text_returned_unchanged(self):
        assert _split_to_char_limit("hello world", 100) == ["hello world"]

    def test_single_oversized_word_hard_split_by_chars(self):
        # Ein Block ohne Whitespace (Base64-Blob / minifizierter Code) ist EIN
        # „Wort" und muss hart per Zeichen gesplittet werden.
        word = "A" * 250
        pieces = _split_to_char_limit(word, 100)

        assert [len(p) for p in pieces] == [100, 100, 50]
        assert all(len(p) <= 100 for p in pieces)
        assert "".join(pieces) == word  # keinerlei Inhaltsverlust

    def test_word_boundaries_preferred_over_hard_split(self):
        text = " ".join(["word"] * 50)  # 50*4 + 49 Spaces = 249 Zeichen
        pieces = _split_to_char_limit(text, 100)

        assert all(len(p) <= 100 for p in pieces)
        # Kein Wort wird mitten zerschnitten.
        for piece in pieces:
            assert all(token == "word" for token in piece.split())
        assert _strip_ws("".join(pieces)) == _strip_ws(text)

    def test_mixed_blob_and_words_preserves_content(self):
        blob = "B" * 250
        text = f"{blob} hello world"
        pieces = _split_to_char_limit(text, 100)

        assert all(len(p) <= 100 for p in pieces)
        assert _strip_ws("".join(pieces)) == _strip_ws(text)


class TestCreateChunksCharLimit:
    def test_oversized_blob_split_into_multiple_full_chunks(self):
        blob = "Q" * 5000
        chunks = create_chunks(blob, chunk_size=1000, chunk_overlap=200, max_chars=1000)

        assert len(chunks) == 5
        assert all(len(c.content) <= 1000 for c in chunks)
        # Kein Inhaltsverlust — anders als bei der Embedding-Truncation.
        assert "".join(c.content for c in chunks) == blob

    def test_chunk_index_sequential_and_unique(self):
        # Eindeutige, fortlaufende chunk_index ist Pflicht: generate_point_id
        # leitet daraus eine deterministische UUID ab — Kollisionen würden
        # Chunks in Qdrant gegenseitig überschreiben.
        blob = "Z" * 5000
        chunks = create_chunks(blob, 1000, 200, max_chars=1000)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))
        assert len(indices) == len(set(indices))

    def test_early_return_path_is_also_capped(self):
        # words <= chunk_size (ein einziges Mega-Wort) lief früher ungeprüft in
        # einen einzigen Riesen-Chunk.
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
        # Kein Split → keine Split-Marker in den Metadaten.
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
        # > chunk_size Wörter (Overlap-Pfad) UND ein Mega-Wort mittendrin:
        # alle Chunks müssen unter dem Cap bleiben und die Indizes lückenlos.
        words = ["alpha"] * 1500
        words[700] = "M" * 3000
        text = " ".join(words)

        chunks = create_chunks(text, chunk_size=1000, chunk_overlap=200, max_chars=1000)

        assert all(len(c.content) <= 1000 for c in chunks)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_word_count_invariant_holds_after_split(self):
        # Bestehende Zusage: word_count <= chunk_size pro Chunk.
        blob = "w" * 5000
        chunks = create_chunks(blob, chunk_size=1000, chunk_overlap=200, max_chars=1000)

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
