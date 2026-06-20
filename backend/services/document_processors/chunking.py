"""
Geteilte Chunking-Logik für die Dokument-Prozessoren.

Wird sowohl vom Default-Prozessor (``pymupdf_processor``) als auch vom
Fallback (``legacy_processor``) genutzt, damit die Wort-Fenster-Logik und
die Zeichen-Obergrenze nur an *einer* Stelle gepflegt werden.

TF-445: Das Chunking schneidet wort-basiert (``text.split()``,
``chunk_size`` Wörter). Ein Block ohne Whitespace (Base64-Blob, Tabelle,
minifizierter Code) wird dabei zu *einem* einzigen Mega-Chunk. Beim
nachgelagerten Embedding kann ein solcher Chunk das Per-Input-Limit reissen
und musste bisher am Embedding-Boundary getrunct werden (TF-442) — der
gekürzte Chunk verliert dann Inhalt *für den Vektor*.

Lösung: Schon beim Chunking eine generische Zeichen-Obergrenze
(``max_chars``) durchsetzen und über-lange Inhalte in *mehrere vollständige*
Chunks splitten — inklusive hartem Zeichen-Split eines einzelnen über-langen
„Worts", das ``text.split()`` allein nicht teilt. Ergebnis: kein
Inhaltsverlust, jeder Chunk bekommt ein präzises eigenes Embedding; die
TF-442-Truncation greift nur noch als echtes Last-Resort-Sicherheitsnetz.

Layering: Diese Logik lebt in ``core/`` (MIT, öffentlich gespiegelt) und
kennt das Embedding-Modell / Token-Limit bewusst **nicht**. ``max_chars`` ist
daher als generischer „sane upper bound" formuliert, nicht als
OpenAI-spezifisches Token-Limit. Konsistent mit TF-441/TF-442 wird ohne
``tiktoken`` gearbeitet.
"""

import logging
from typing import Dict, List

from services.docling_service import DocumentChunk

logger = logging.getLogger(__name__)

# Generische Obergrenze an Zeichen pro Chunk (sane upper bound).
#
# Bewusst KEIN Embedding-/Token-Limit (Core kennt das Modell nicht), sondern
# eine Obergrenze, die normale Prosa nie zerschneidet (ein typischer
# 1000-Wort-Chunk liegt bei ~6-7k Zeichen) und gleichzeitig pathologische
# Blöcke ohne Whitespace zuverlässig zerlegt. Der Wert liegt klar unter dem
# Embedding-Truncation-Budget der Premium-Schicht (TF-442), damit jene
# Truncation zum echten Last-Resort wird.
DEFAULT_MAX_CHARS_PER_CHUNK = 12_000


def _split_to_char_limit(text: str, max_chars: int) -> List[str]:
    """Zerlege ``text`` in Stücke von je höchstens ``max_chars`` Zeichen.

    Bevorzugt Wortgrenzen; ein einzelnes Wort, das für sich genommen länger
    als ``max_chars`` ist (Base64-Blob, minifizierter Code), wird hart per
    Zeichen gesplittet. Der gesamte Inhalt bleibt erhalten — die Stücke
    aneinandergehängt ergeben den Eingabetext (Whitespace zwischen Wörtern
    wird wie im Wort-Fenster-Pfad zu einfachen Leerzeichen normalisiert).
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
        # Einzelnes über-langes Wort: Puffer leeren, dann hart per Zeichen
        # splitten. Volle Segmente werden direkt emittiert, der Rest wandert
        # in den Puffer und kann mit nachfolgenden Wörtern aufgefüllt werden.
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
            # Puffer ist voll — abschliessen und mit dem aktuellen Wort neu
            # beginnen.
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
    """Erzeuge Text-Chunks für RAG-Processing.

    Wort-basierte Fenster (``chunk_size`` Wörter, ``chunk_overlap`` Wörter
    Überlappung) wie bisher; zusätzlich wird pro emittiertem Chunk die
    Zeichen-Obergrenze ``max_chars`` durchgesetzt (TF-445). Die
    ``chunk_index``-Nummerierung läuft fortlaufend über *alle* emittierten
    Chunks — auch über die durch den Zeichen-Split entstandenen — damit die
    daraus abgeleiteten Qdrant-Point-IDs eindeutig bleiben.

    Hinweis: Passt der Text in ein einzelnes Wort-Fenster
    (``len(words) <= chunk_size``) und unter ``max_chars``, bleibt der
    Original-Whitespace erhalten; sobald gefenstert oder zeichen-gesplittet
    wird, wird Whitespace zwischen Wörtern zu einfachen Leerzeichen
    normalisiert (bestehendes Verhalten des ``" ".join``-Pfads).
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
            # Sollte nur bei pathologischen Inhalten (Whitespace-freie Blöcke)
            # auftreten — als Signal loggen, damit solche Dokumente sichtbar
            # werden.
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
                # 1-basiert ("Teil 1 von N"), bewusst anders als das 0-basierte
                # chunk_index.
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
        # Nach dem Fenster, das das Wort-Ende erreicht (end == len(words)), ist
        # alles emittiert — abbrechen, bevor ein reines Overlap-Fenster folgt.
        if start >= len(words) - chunk_overlap:
            break

    return chunks
