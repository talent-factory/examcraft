"""
Shared chunking logic for the document processors.

Used by both the default processor (``pymupdf_processor``) and the
fallback (``legacy_processor``), so the word-window logic and the
character upper bound are maintained in only *one* place.

TF-445: Chunking splits on word boundaries (``text.split()``,
``chunk_size`` words). A block without whitespace (base64 blob, table,
minified code) then becomes *one single* mega-chunk. During downstream
embedding, such a chunk could exceed the per-input limit and previously
had to be truncated at the embedding boundary (TF-442) — the truncated
chunk then loses content *for the vector*.

Solution: enforce a generic character upper bound (``max_chars``) already
during chunking, and split over-long content into *multiple complete*
chunks — including a hard character split of a single over-long "word"
that ``text.split()`` alone won't break up. Result: no content loss, each
chunk gets its own precise embedding; the TF-442 truncation now only
kicks in as a genuine last-resort safety net.

Layering: this logic lives in ``core/`` (MIT, mirrored publicly) and
deliberately does **not** know the embedding model / token limit.
``max_chars`` is therefore phrased as a generic "sane upper bound" rather
than an OpenAI-specific token limit. Consistent with TF-441/TF-442, this
works without ``tiktoken``.
"""

import logging
from typing import Dict, List

from services.docling_service import DocumentChunk

logger = logging.getLogger(__name__)

# Generic upper bound on characters per chunk (sane upper bound).
#
# Deliberately NOT an embedding/token limit (core doesn't know the model),
# but an upper bound that never cuts through normal prose (a typical
# 1000-word chunk is ~6-7k characters) while reliably breaking up
# pathological blocks without whitespace. The value sits clearly below the
# embedding truncation budget of the premium layer (TF-442), so that
# truncation becomes a genuine last resort.
DEFAULT_MAX_CHARS_PER_CHUNK = 12_000


def _split_to_char_limit(text: str, max_chars: int) -> List[str]:
    """Split ``text`` into pieces of at most ``max_chars`` characters each.

    Prefers word boundaries; a single word that is by itself longer than
    ``max_chars`` (base64 blob, minified code) gets hard-split by
    character. All content is preserved — the pieces concatenated together
    reproduce the input text (whitespace between words is normalized to
    single spaces, as in the word-window path).
    """
    if max_chars < 1:
        raise ValueError(f"max_chars must be >= 1, got {max_chars}")
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    pieces: List[str] = []
    buffer = ""

    for word in text.split():
        # Single over-long word: flush the buffer, then hard-split by
        # character. Full segments are emitted directly, the remainder goes
        # into the buffer and can be topped up with subsequent words.
        if len(word) > max_chars:
            if buffer:
                pieces.append(buffer)
                buffer = ""
            for offset in range(0, len(word), max_chars):
                segment = word[offset : offset + max_chars]
                if len(segment) == max_chars:
                    pieces.append(segment)
                else:
                    buffer = segment
            continue

        candidate = word if not buffer else f"{buffer} {word}"
        if len(candidate) > max_chars:
            # Buffer is full — flush it and start over with the current
            # word.
            pieces.append(buffer)
            buffer = word
        else:
            buffer = candidate

    if buffer:
        pieces.append(buffer)

    return pieces


def create_chunks(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    max_chars: int = DEFAULT_MAX_CHARS_PER_CHUNK,
) -> List[DocumentChunk]:
    """Produce text chunks for RAG processing.

    Word-based windows (``chunk_size`` words, ``chunk_overlap`` words of
    overlap) as before; additionally, the character upper bound
    ``max_chars`` is enforced per emitted chunk (TF-445). The
    ``chunk_index`` numbering runs contiguously across *all* emitted
    chunks — including those produced by the character split — so the
    Qdrant point IDs derived from it stay unique.

    Note: if the text fits into a single word window
    (``len(words) <= chunk_size``) and under ``max_chars``, the original
    whitespace is preserved; as soon as windowing or character-splitting
    kicks in, whitespace between words is normalized to single spaces
    (existing behavior of the ``" ".join`` path).
    """
    if not text or not text.strip():
        return []

    chunks: List[DocumentChunk] = []
    running_index = 0

    def _emit(window_text: str, base_metadata: Dict[str, int]) -> None:
        nonlocal running_index
        pieces = _split_to_char_limit(window_text, max_chars)
        total_parts = len(pieces)
        if total_parts > 1:
            # Should only happen for pathological content (whitespace-free
            # blocks) — log it as a signal so such documents become
            # visible.
            logger.warning(
                "Chunk content exceeded max_chars=%d; split into %d sub-chunks "
                "to keep each chunk within the limit",
                max_chars,
                total_parts,
            )
        for part_no, piece in enumerate(pieces, start=1):
            metadata: Dict[str, int] = dict(base_metadata)
            metadata["word_count"] = len(piece.split())
            metadata["char_count"] = len(piece)
            if total_parts > 1:
                # 1-based ("part 1 of N"), deliberately different from the
                # 0-based chunk_index.
                metadata["char_split_part"] = part_no
                metadata["char_split_parts"] = total_parts
            chunks.append(
                DocumentChunk(
                    content=piece,
                    chunk_index=running_index,
                    metadata=metadata,
                )
            )
            running_index += 1

    words = text.split()

    if len(words) <= chunk_size:
        _emit(text, {})
        return chunks

    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        chunk_text = " ".join(chunk_words)

        _emit(chunk_text, {"start_word": start, "end_word": end})

        start = end - chunk_overlap
        # After the window that reaches the end of the words (end ==
        # len(words)), everything has been emitted — stop before a
        # pure-overlap window follows.
        if start >= len(words) - chunk_overlap:
            break

    return chunks
