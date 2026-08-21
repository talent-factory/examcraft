"""Filenames and ``Content-Disposition`` headers for file downloads.

Every download built from user-supplied text (an exam title, say) has to
solve the same three problems, and getting any of them wrong is a bug that
only shows up with real-world data:

* **HTTP headers are latin-1.** A Unicode filename cannot be interpolated
  into one — a single em dash raises ``UnicodeEncodeError`` and turns the
  download into a 500. RFC 6266 solves this with two parameters: an
  ASCII-transliterated ``filename`` that every client understands, plus
  ``filename*`` carrying the exact name percent-encoded as UTF-8.
* **Header injection.** A title containing a quote or CRLF would otherwise
  terminate the parameter and let the rest smuggle in response headers.
* **Filesystem rules.** Windows rejects ``\\ / : * ? " < > |``, names that
  begin or end with a space or dot, and its reserved device names.

This module is the single place that answers all three. It deliberately
keeps spaces, capitals, ``&`` and accented characters: a download should be
named after the thing it contains, not after a slug of it.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

# Characters no filename may contain: Windows rejects these outright, and
# control characters (CR/LF included) must never reach an HTTP header.
_FORBIDDEN_RE = re.compile(r'[\\/:*?"<>|\x00-\x1f\x7f]')

# Device names Windows reserves; unusable as a filename with or without an
# extension.
_WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(1, 10)}
    | {f"LPT{i}" for i in range(1, 10)}
)

_FALLBACK_NAME = "export"


def sanitize_filename(name: str) -> str:
    """Strip what a filesystem or an HTTP header cannot carry.

    Forbidden characters collapse into a space rather than an underscore,
    so "Kapitel 3? Teil 2" reads as "Kapitel 3 Teil 2" instead of
    "Kapitel 3_ Teil 2". Leading and trailing spaces and dots are removed —
    Windows silently rejects names that start or end with either.
    """
    cleaned = _FORBIDDEN_RE.sub(" ", name or "")
    return re.sub(r"\s+", " ", cleaned).strip(" .")


def filename_stem(title: str, max_length: int = 80) -> str:
    """Build the filename stem for a title, without extension or suffixes.

    Capped at ``max_length`` so a long title cannot push the final name past
    a filesystem's ~255-byte limit once extension and suffixes are added.
    80 characters covers ordinary exam titles whole — 50 used to cut
    "… Semesterprüfung FS 2026" after "FS", silently dropping the year.

    When the cap does bite, the cut lands on the last word boundary that
    fits, so the name ends on a whole word rather than mid-syllable. A
    single word longer than the cap has no boundary to respect and is cut
    hard.
    """
    cleaned = sanitize_filename(title)
    if len(cleaned) > max_length:
        head = cleaned[:max_length]
        boundary = head.rfind(" ")
        cleaned = head[:boundary] if boundary > 0 else head

    stem = cleaned.strip(" .") or _FALLBACK_NAME
    if stem.upper() in _WINDOWS_RESERVED_NAMES:
        stem = f"Export_{stem}"
    return stem


def content_disposition(filename: str) -> str:
    """Build an ``attachment`` header carrying ``filename`` (RFC 6266).

    Re-sanitises rather than trusting the caller, so this stays the single
    gate on what reaches the header. The extension is held out of the
    transliteration so a title that is entirely non-ASCII ("試験") still
    yields a usable "export.pdf" instead of a bare ".pdf".

    NFKD transliteration can itself produce a forbidden character or a
    reserved device name that wasn't present before it ran — e.g. the
    fullwidth quotation mark "＂" decomposes to a literal '"', and
    "ÇÖÑ" collapses to "CON". Both guards run again after transliteration
    so it stays true to "the single gate" rather than a gate with a hole.
    """
    safe = sanitize_filename(filename)
    stem, dot, extension = safe.rpartition(".")
    if not dot:
        stem, extension = safe, ""

    ascii_stem = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode()
    ascii_stem = _FORBIDDEN_RE.sub(" ", ascii_stem)
    ascii_stem = re.sub(r"\s+", " ", ascii_stem).strip(" ._-") or _FALLBACK_NAME
    if ascii_stem.upper() in _WINDOWS_RESERVED_NAMES:
        ascii_stem = f"Export_{ascii_stem}"
    ascii_name = f"{ascii_stem}.{extension}" if extension else ascii_stem

    return (
        f'attachment; filename="{ascii_name}"; '
        f"filename*=UTF-8''{quote(safe, safe='')}"
    )
