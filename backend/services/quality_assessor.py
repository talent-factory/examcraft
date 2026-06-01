"""Deterministische Qualitäts-Bewertung der Dokumenten-Extraktion (TF-360).

Reine Funktionen ohne I/O: nehmen Extraktions-Statistiken entgegen und
liefern ein Verdict, ob die PyMuPDF-Extraktion ausreicht oder eine
OCR-Neuverarbeitung mit PyMuPDF/Tesseract nötig ist. Schwellwerte sind via
Env-Vars tunebar (bei jedem Aufruf gelesen, damit Konfig-Änderungen ohne
Modul-Reload greifen).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Literal

from services.docling_service import ProcessedDocument

# Geschlossene Wertemengen als Literal getypt — damit Tippfehler an den
# Aufrufstellen statisch auffallen und die Werte selbstdokumentierend sind.
QualityReason = Literal[
    "ok",
    "scanned_low_text",
    "single_chunk_large_file",
    "garbage_extraction",
    "ocr_pages_discarded",
]
EscalationState = Literal[
    "queued",
    "unavailable",
    "not_needed",
    "completed",
    "exhausted",
    "failed",
    "no_verdict",
]

# Default-Schwellwerte (Design-Spec). Via Env-Vars überschreibbar.
_DEFAULT_MIN_CHARS_PER_PAGE = 100
_DEFAULT_LOW_CHUNK_FILE_SIZE = 200 * 1024
_DEFAULT_LOW_CHUNK_MIN_PAGES = 2
_DEFAULT_MAX_GARBAGE_RATIO = 0.30
_DEFAULT_MAX_OCR_DISCARD_RATIO = 0.20


@dataclass(frozen=True)
class DocumentQualityStats:
    """Eingangs-Statistiken für die Bewertung."""

    page_count: int
    total_chars: int
    chunk_count: int
    garbage_char_ratio: float  # muss in [0.0, 1.0] liegen
    file_size: int
    ocr_pages_attempted: int = 0
    ocr_pages_discarded: int = 0

    def __post_init__(self) -> None:
        if not 0.0 <= self.garbage_char_ratio <= 1.0:
            raise ValueError(
                f"garbage_char_ratio muss in [0,1] liegen, war {self.garbage_char_ratio}"
            )
        if (
            min(
                self.page_count,
                self.total_chars,
                self.chunk_count,
                self.file_size,
                self.ocr_pages_attempted,
                self.ocr_pages_discarded,
            )
            < 0
        ):
            raise ValueError("Zähl-/Grössenfelder müssen >= 0 sein")


@dataclass(frozen=True)
class QualityVerdict:
    """Bewertungs-Ergebnis."""

    ok: bool
    reason: QualityReason
    signals: Dict[str, Any]


def compute_quality_stats(
    processed_doc: ProcessedDocument, file_size: int
) -> DocumentQualityStats:
    """Leite Statistiken aus einem ProcessedDocument + Dateigrösse ab."""
    text = "".join(chunk.content for chunk in processed_doc.chunks)
    total_chars = len(text)
    if total_chars:
        printable = sum(1 for ch in text if ch.isprintable() or ch in "\t\n\r")
        garbage_ratio = 1.0 - (printable / total_chars)
    else:
        garbage_ratio = 0.0

    meta = processed_doc.metadata or {}
    return DocumentQualityStats(
        page_count=processed_doc.total_pages or 0,
        total_chars=total_chars,
        chunk_count=processed_doc.total_chunks,
        garbage_char_ratio=garbage_ratio,
        file_size=file_size,
        ocr_pages_attempted=int(meta.get("ocr_pages_attempted", 0)),
        ocr_pages_discarded=int(meta.get("ocr_pages_discarded", 0)),
    )


def assess_quality(stats: DocumentQualityStats) -> QualityVerdict:
    """Bewerte die Extraktions-Qualität mit kombinierten Signalen."""
    min_chars_per_page = int(
        os.getenv("QUALITY_MIN_CHARS_PER_PAGE", str(_DEFAULT_MIN_CHARS_PER_PAGE))
    )
    low_chunk_file_size = int(
        os.getenv("QUALITY_LOW_CHUNK_FILE_SIZE", str(_DEFAULT_LOW_CHUNK_FILE_SIZE))
    )
    low_chunk_min_pages = int(
        os.getenv("QUALITY_LOW_CHUNK_MIN_PAGES", str(_DEFAULT_LOW_CHUNK_MIN_PAGES))
    )
    max_garbage_ratio = float(
        os.getenv("QUALITY_MAX_GARBAGE_RATIO", str(_DEFAULT_MAX_GARBAGE_RATIO))
    )
    max_ocr_discard_ratio = float(
        os.getenv("QUALITY_MAX_OCR_DISCARD_RATIO", str(_DEFAULT_MAX_OCR_DISCARD_RATIO))
    )

    chars_per_page = (
        stats.total_chars / stats.page_count
        if stats.page_count >= 1
        else float(stats.total_chars)
    )
    signals: Dict[str, Any] = {
        "chars_per_page": round(chars_per_page, 1),
        "chunk_count": stats.chunk_count,
        "garbage_char_ratio": round(stats.garbage_char_ratio, 3),
        "file_size": stats.file_size,
        "page_count": stats.page_count,
    }

    if stats.ocr_pages_attempted > 0:
        signals["ocr_pages_attempted"] = stats.ocr_pages_attempted
        signals["ocr_pages_discarded"] = stats.ocr_pages_discarded

    discard_ratio = (
        stats.ocr_pages_discarded / stats.ocr_pages_attempted
        if stats.ocr_pages_attempted
        else 0.0
    )
    if stats.ocr_pages_discarded >= 1 and discard_ratio > max_ocr_discard_ratio:
        return QualityVerdict(False, "ocr_pages_discarded", signals)

    # Zero usable extraction must never pass as "ok", auch wenn page_count
    # unbekannt (0) ist — z. B. ein gescanntes DOCX ohne <Pages>-Metadaten und
    # ohne Body-Bilder. Ohne diese Prüfung überspränge das ``page_count >= 1``-
    # Gate unten die Low-Text-Heuristik und liesse ein leeres Dokument still als
    # "Verarbeitet" durch (TF-367-Nachzügler).
    if stats.total_chars == 0 or stats.chunk_count == 0:
        return QualityVerdict(False, "scanned_low_text", signals)

    if stats.page_count >= 1 and chars_per_page < min_chars_per_page:
        return QualityVerdict(False, "scanned_low_text", signals)

    if (
        stats.chunk_count <= 1
        and stats.file_size > low_chunk_file_size
        and stats.page_count > low_chunk_min_pages
    ):
        return QualityVerdict(False, "single_chunk_large_file", signals)

    if stats.garbage_char_ratio > max_garbage_ratio:
        return QualityVerdict(False, "garbage_extraction", signals)

    return QualityVerdict(True, "ok", signals)
