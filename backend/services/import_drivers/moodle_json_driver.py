"""Moodle **JSON** results import driver (TF-423).

Unlike the bare ``Antworten`` CSV — which carries only positional
``Antwort N`` columns and therefore mis-maps answers whenever the Moodle
quiz order differs from ExamCraft's (variants, reordered quizzes) — the
JSON export produced by the Moodle plugin/report pairs **each answer with
its question text** (``frageN``/``antwortN``). The driver therefore maps
answers to exam questions by **content** (normalised text match), not by
position. This resolves the reorder failure mode the CSV driver could only
*detect* (TF-422), and incidentally removes the CSV quoting/delimiter
fragility (TF-419/TF-411) since JSON has no such ambiguity.

Mapping strategy per ``frageN`` (with a hard uniqueness guardrail):

1. **Normalise** both sides identically: ``html.unescape`` → strip HTML
   tags → soft-strip Markdown markers → collapse whitespace → casefold.
   ExamCraft stores question text as Markdown while the JSON ``frageN`` is
   Moodle-rendered plain (sometimes HTML-entity-encoded); normalising both
   to the same plain form makes them converge.
2. **Match**: exact → two-way containment → high-threshold Jaccard token
   overlap for minor drift. Containment is checked in *both* directions:
   the MC export renders the options inline after the stem (ExamCraft stem
   ⊂ JSON ``frageN``), but Moodle can also render a shorter stem than the
   stored question (JSON ``frageN`` ⊂ ExamCraft stem), so the symmetric
   check is deliberate.
3. **Guardrail**: 0 or >1 candidates for any ``frageN`` aborts the import
   with a clear ``ColumnMappingError`` — never silently misassign.

The column→question mapping is resolved **per row, keyed on that row's own
``frageN`` layout** (memoised, so a row-homogeneous export resolves it once
and reuses it). A/B exam variants and per-attempt question shuffles produce
several layouts in one file; mapping each row by *its own* question texts
means a variant's answers can never land on another variant's questions.
A row whose ``frageN`` layout cannot be resolved is diverted to
``payload.errors`` (per-row tolerance) rather than poisoning the others.

Expected source shape (Moodle plugin export)::

    [[ {"nachname": ..., "vorname": ..., "e-mail-adresse": ...,
        "begonnen": ..., "beendet": ...,
        "frage1": ..., "antwort1": ..., "frage2": ..., ... }, ... ]]

A flat top-level list (without the outer wrapper) is also accepted.
"""

from __future__ import annotations

import hashlib
import html
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, ClassVar

from services.import_drivers.base import (
    BaseImportDriver,
    ColumnMappingError,
    ExamLike,
    ImportDriverError,
)
from services.import_drivers.payloads import (
    AnswerRecord,
    AttemptRecord,
    ImportPayload,
    ImportRowError,
    StudentRef,
)

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------
# Date parsing (locale-independent; shared shape with the legacy CSV driver)
# --------------------------------------------------------------------------
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%y, %H:%M",
    "%d/%m/%Y, %H:%M",
    "%d.%m.%Y, %H:%M",
    "%d.%m.%y %H:%M",
    "%d %B %Y, %H:%M",
    "%d %B %Y, %I:%M %p",
)

# German long-form dates ("12. Juni 2026 11:55") are mapped by hand so
# parsing is locale-independent and thread-safe (no ``setlocale``). (TF-411)
_GERMAN_MONTHS: dict[str, int] = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}

# "<weekday>, 12. Juni 2026, 11:55" / "12. Juni 2026 11:55:30" — weekday
# prefix, comma before the time, and seconds are all optional.
_GERMAN_LONG_DATE_RE = re.compile(
    r"^(?:\w+,\s*)?"
    r"(\d{1,2})\.\s+"
    r"([A-Za-zäöüÄÖÜ]+)\s+"
    r"(\d{4})"
    r",?\s+"
    r"(\d{1,2}):(\d{2})"
    r"(?::(\d{2}))?$"
)


def _parse_german_long_date(value: str) -> datetime | None:
    match = _GERMAN_LONG_DATE_RE.match(value)
    if not match:
        return None
    day, month_name, year, hour, minute, second = match.groups()
    month = _GERMAN_MONTHS.get(month_name.lower())
    if month is None:
        return None
    try:
        return datetime(
            int(year),
            month,
            int(day),
            int(hour),
            int(minute),
            int(second) if second else 0,
        )
    except ValueError:
        return None


def _parse_datetime(raw: str | None) -> datetime | None:
    """Parse known Moodle date formats; always returns tz-aware UTC or None.

    Naïve formats are assumed UTC at source — the column never carries the
    offset, and ``source_attempt_id`` embeds ``isoformat()`` in the
    idempotency key, so mixing naïve/aware values would silently change the
    key for the same wall-clock instant.
    """
    if not raw:
        return None
    value = str(raw).strip()
    if not value:
        return None
    parsed: datetime | None = None
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(value, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        parsed = _parse_german_long_date(value)
    if parsed is None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


# --------------------------------------------------------------------------
# Text matching
# --------------------------------------------------------------------------
_JACCARD_THRESHOLD = 0.85
_MIN_CONTAINMENT_LEN = 3
_MARKDOWN_MARKERS = re.compile(r"[*_`#>]+")
_HTML_TAG = re.compile(r"<[^>]+>")


def _normalize_text(text: object) -> str:
    """Collapse a question/answer string to a comparable plain form.

    Order matters: unescape entities first so ``&lt;p&gt;`` becomes a real
    tag that the tag-stripper can then remove. Markdown emphasis/heading/
    quote markers are soft-stripped so ExamCraft's Markdown stem converges
    with Moodle's rendered plain text.
    """
    s = html.unescape(str(text))
    s = _HTML_TAG.sub(" ", s)
    s = s.replace("\xa0", " ")
    s = _MARKDOWN_MARKERS.sub(" ", s)
    return " ".join(s.split()).casefold()


def _tokens(normalized: str) -> frozenset[str]:
    return frozenset(re.findall(r"\w+", normalized))


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _answer_matches_option(given: str, norm_options: tuple[str, ...]) -> bool:
    """True if ``given`` plausibly is one of ``norm_options``.

    ``norm_options`` are already normalised (see ``_QuestionEntry``). Two-way
    containment tolerates Moodle rendering quirks (e.g. response "Wahr" vs
    option "A) Wahr"). Gated on ``_MIN_CONTAINMENT_LEN`` so a one/two-char
    option can't be a substring of arbitrary free text.
    """
    normalized = _normalize_text(given)
    if not normalized:
        return False
    for opt in norm_options:
        if len(opt) < _MIN_CONTAINMENT_LEN:
            if opt and opt == normalized:
                return True
            continue
        if opt in normalized or normalized in opt:
            return True
    return False


@dataclass(frozen=True, slots=True)
class _QuestionEntry:
    """Pre-normalised exam question for matching.

    Frozen + derived: ``norm``/``tokens``/``norm_options`` are all computed
    from the raw question text and options in :meth:`build`, so the
    ``tokens == _tokens(norm)`` invariant cannot drift after construction.
    ``norm_options`` is pre-normalised here (not per-answer in the hot loop).
    """

    eq_id: int
    norm: str
    tokens: frozenset[str]
    norm_options: tuple[str, ...]

    @classmethod
    def build(cls, eq_id: int, text: str, options: list[str]) -> _QuestionEntry:
        norm = _normalize_text(text)
        norm_options = tuple(
            normed
            for normed in (_normalize_text(o) for o in options if o is not None)
            if normed
        )
        return cls(
            eq_id=eq_id, norm=norm, tokens=_tokens(norm), norm_options=norm_options
        )


def _match_question_id(frage: str, index: list[_QuestionEntry]) -> int | None:
    """Return the unique exam_question_id for ``frage`` or None.

    None signals *either* no candidate *or* an ambiguous tie — both abort
    the import via the caller's guardrail.
    """
    norm = _normalize_text(frage)
    if not norm:
        return None
    tokens = _tokens(norm)

    exact = [e.eq_id for e in index if e.norm == norm]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None

    contained = [
        e.eq_id for e in index if e.norm and (e.norm in norm or norm in e.norm)
    ]
    if len(contained) == 1:
        return contained[0]
    if len(contained) > 1:
        return None

    scored = sorted(
        ((e.eq_id, _jaccard(tokens, e.tokens)) for e in index),
        key=lambda pair: pair[1],
        reverse=True,
    )
    scored = [(eq, s) for eq, s in scored if s >= _JACCARD_THRESHOLD]
    if not scored:
        return None
    if len(scored) > 1 and abs(scored[0][1] - scored[1][1]) < 1e-9:
        return None
    return scored[0][0]


_FRAGE_KEY_RE = re.compile(r"^frage(\d+)$")


class MoodleJsonDriver(BaseImportDriver):
    """Map Moodle JSON responses onto exam questions by question text."""

    name: ClassVar[str] = "moodle_json"

    def parse(
        self,
        source: bytes | str,
        *,
        exam: ExamLike,
        db: Any | None = None,
    ) -> ImportPayload:
        rows, dropped_non_dict = self._load_rows(source)
        if not rows:
            raise ImportDriverError("JSON enthält keine Datenzeilen.")

        index = self._build_index(exam)
        if not index:
            raise ImportDriverError(
                "Die Prüfung enthält keine Fragen, denen Antworten "
                "zugeordnet werden könnten."
            )

        options_by_eq = {e.eq_id: e.norm_options for e in index}
        students: dict[str, StudentRef] = {}
        # One row == one attempt; number them per student in row order so a
        # student with several attempts doesn't collide on the
        # (submission_id, attempt_number) unique constraint.
        attempt_counters: dict[str, int] = {}
        attempts: list[AttemptRecord] = []
        warnings: list[str] = []
        errors: list[ImportRowError] = []
        # Aggregate the per-answer "matches no option" sanity-net signal per
        # column: a systematically-off column yields ONE warning, not one per
        # student (which would bury every other signal on a large import).
        no_option_hits: dict[int, int] = {}

        if dropped_non_dict:
            # Surface silently-skipped non-object entries (e.g. a stray null
            # from a partially-failed export) rather than dropping them mute.
            warnings.append(
                f"{dropped_non_dict} Eintrag/Einträge ohne Objektstruktur "
                "übersprungen (keine Studierenden-Datensätze)."
            )

        # Resolve the column->question mapping per row, keyed on that row's
        # own frageN layout. ``_layout_signature`` is the cache key; the first
        # resolvable layout's failure aborts hard (signals wrong exam / corrupt
        # export), later divergent layouts that fail divert their rows to
        # ``errors`` (per-row tolerance). See module docstring.
        mapping_cache: dict[frozenset[tuple[int, str]], dict[int, int]] = {}
        self._seed_reference_mapping(rows, index, mapping_cache)

        for row_index, raw in enumerate(rows):
            row = self._normalize_keys(raw)
            external_id = (row.get("e-mail-adresse") or "").strip()
            # Per-row tolerance: a row without the identity column
            # (e-mail-adresse) is skipped with an error instead of being
            # imported under a synthetic id — mirrors the legacy CSV
            # contract and keeps anonymous junk rows out of the data.
            if not external_id:
                errors.append(
                    ImportRowError(
                        row_index=row_index,
                        reason="Zeile ohne E-Mail-Adresse (external_id) übersprungen.",
                    )
                )
                continue

            # Map this row by ITS OWN frageN texts (reorder-robust per row).
            column_map = self._row_column_map(row, index, mapping_cache)
            if column_map is None:
                errors.append(
                    ImportRowError(
                        row_index=row_index,
                        reason=(
                            "Fragetexte dieser Zeile konnten keiner Prüfungsfrage "
                            "eindeutig zugeordnet werden — übersprungen."
                        ),
                    )
                )
                continue

            display_name = (
                " ".join(
                    part
                    for part in (
                        (row.get("vorname") or "").strip(),
                        (row.get("nachname") or "").strip(),
                    )
                    if part
                )
                or None
            )

            if external_id not in students:
                # Optional class hint drives TF-336 auto-class-assignment.
                # The plugin emits ``klasse`` (German) or ``class`` when the
                # institution configures the field; absent/blank → None.
                class_hint = (
                    str(row.get("klasse") or row.get("class") or "").strip() or None
                )
                students[external_id] = StudentRef(
                    external_id=external_id,
                    display_name=display_name,
                    class_hint=class_hint,
                )

            started_at = _parse_datetime(row.get("begonnen"))
            submitted_at = _parse_datetime(row.get("beendet"))

            answers: list[AnswerRecord] = []
            for col, eq_id in column_map.items():
                given = row.get(f"antwort{col}")
                given_str = None if given is None else str(given)
                answers.append(
                    AnswerRecord(exam_question_id=eq_id, given_answer=given_str)
                )
                # Secondary sanity net: a choice question whose answer
                # matches no option is suspicious (surfaced, not fatal —
                # text identity already established the mapping). Counted per
                # column; collapsed into one warning each after the loop.
                norm_opts = options_by_eq.get(eq_id) or ()
                if (
                    norm_opts
                    and given_str
                    and given_str.strip()
                    and not _answer_matches_option(given_str, norm_opts)
                ):
                    no_option_hits[col] = no_option_hits.get(col, 0) + 1

            attempt_number = attempt_counters.get(external_id, 0) + 1
            attempt_counters[external_id] = attempt_number
            attempts.append(
                AttemptRecord(
                    student_external_id=external_id,
                    attempt_number=attempt_number,
                    started_at=started_at,
                    submitted_at=submitted_at,
                    source_attempt_id=self._compose_source_attempt_id(
                        external_id, started_at, attempt_number, answers
                    ),
                    answers=answers,
                )
            )

        # Collapse the per-column sanity-net counts into one warning each so
        # the signal is visible without one line per student.
        for col in sorted(no_option_hits):
            warnings.append(
                f"{no_option_hits[col]} Antwort(en) auf Frage {col} passten zu "
                "keiner Antwortoption (zur Kontrolle)."
            )

        return ImportPayload(
            exam_id=exam.id,
            driver_name=self.name,
            students=list(students.values()),
            attempts=attempts,
            warnings=warnings,
            errors=errors,
            source_metadata={"mapping_basis": "question_text"},
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _load_rows(source: bytes | str) -> tuple[list[dict[str, Any]], int]:
        """Decode + parse the source. Returns ``(rows, dropped_non_dict)``.

        ``dropped_non_dict`` counts list entries that were not JSON objects
        (e.g. a stray ``null`` from a partially-failed export) so the caller
        can surface them instead of silently discarding data.
        """
        if isinstance(source, bytes):
            try:
                text = source.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    text = source.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise ImportDriverError(
                        "JSON-Datei ist nicht UTF-8-kodiert."
                    ) from exc
        else:
            text = source
        if not text.strip():
            raise ImportDriverError("Die Datei ist leer.")
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ImportDriverError("Quelle ist kein gültiges JSON.") from exc

        if isinstance(data, list) and data and isinstance(data[0], list):
            data = data[0]  # unwrap the plugin's outer [[ ... ]] envelope
        if not isinstance(data, list):
            raise ImportDriverError(
                "JSON-Wurzel muss eine Liste von Studierenden sein."
            )
        rows = [r for r in data if isinstance(r, dict)]
        return rows, len(data) - len(rows)

    @staticmethod
    def _normalize_keys(raw: dict[str, Any]) -> dict[str, Any]:
        return {str(k).strip().lower(): v for k, v in raw.items()}

    @staticmethod
    def _build_index(exam: ExamLike) -> list[_QuestionEntry]:
        index: list[_QuestionEntry] = []
        for q in getattr(exam, "questions", []) or []:
            question = getattr(q, "question", None)
            text = getattr(question, "question_text", None)
            if not text:
                continue
            raw_opts = getattr(question, "options", None) or []
            options = [str(o) for o in raw_opts if o is not None]
            index.append(_QuestionEntry.build(int(q.id), str(text), options))
        return index

    def _seed_reference_mapping(
        self,
        rows: list[dict[str, Any]],
        index: list[_QuestionEntry],
        cache: dict[frozenset[tuple[int, str]], dict[int, int]],
    ) -> None:
        """Resolve the first row that carries ``frageN`` and cache it.

        The reference layout's failure is a *hard* abort (raises
        ``ColumnMappingError``) because a first row that maps to nothing
        signals the wrong exam / a corrupt export — better to fail the whole
        import loudly than to soft-skip every row. Later divergent layouts
        (A/B variants) are resolved lazily in :meth:`_row_column_map` and
        only soft-fail. If no row carries ``frageN`` at all, abort hard.
        """
        for raw in rows:
            row = self._normalize_keys(raw)
            frage_texts = self._extract_row_frage_texts(row)
            if frage_texts:
                sig = self._layout_signature(frage_texts)
                cache[sig] = self._resolve_column_map(frage_texts, index)
                return
        raise ColumnMappingError(
            "Im JSON-Export fehlen die Fragetexte (Schlüssel 'frageN'); "
            "ohne sie ist keine inhaltliche Zuordnung möglich."
        )

    def _row_column_map(
        self,
        row: dict[str, Any],
        index: list[_QuestionEntry],
        cache: dict[frozenset[tuple[int, str]], dict[int, int]],
    ) -> dict[int, int] | None:
        """Column->question map for ``row`` keyed on its own ``frageN`` layout.

        Memoised per layout signature: a row-homogeneous export resolves once
        (reference) and every other row is a cache hit; A/B variants resolve
        their own layout once each. Returns ``None`` when the row carries no
        ``frageN`` or its layout cannot be uniquely resolved — the caller
        diverts such a row to ``errors`` (per-row tolerance).
        """
        frage_texts = self._extract_row_frage_texts(row)
        if not frage_texts:
            return None
        sig = self._layout_signature(frage_texts)
        if sig not in cache:
            try:
                cache[sig] = self._resolve_column_map(frage_texts, index)
            except ColumnMappingError:
                return None
        return cache[sig]

    @staticmethod
    def _resolve_column_map(
        frage_texts: dict[int, str], index: list[_QuestionEntry]
    ) -> dict[int, int]:
        """Resolve ``Antwort N`` column -> exam_question_id (uniqueness-gated).

        Raises ``ColumnMappingError`` if any column maps to 0/>1 questions
        (``unresolved``) or two columns map to the same question
        (``duplicates``) — never silently misassign.
        """
        mapping: dict[int, int] = {}
        unresolved: list[int] = []
        for col, text in sorted(frage_texts.items()):
            eq_id = _match_question_id(text, index)
            if eq_id is None:
                unresolved.append(col)
            else:
                mapping[col] = eq_id

        duplicates = [
            eq_id
            for eq_id in set(mapping.values())
            if list(mapping.values()).count(eq_id) > 1
        ]
        if unresolved or duplicates:
            parts = []
            if unresolved:
                cols = ", ".join(f"Frage {c}" for c in sorted(unresolved))
                parts.append(
                    f"{cols} konnte(n) keiner Prüfungsfrage eindeutig zugeordnet werden"
                )
            if duplicates:
                parts.append("mehrere JSON-Fragen zeigen auf dieselbe Prüfungsfrage")
            raise ColumnMappingError(
                "Zuordnung der JSON-Fragen zu den Prüfungsfragen "
                f"fehlgeschlagen: {'; '.join(parts)}. Bitte prüfen, ob der "
                "Export zur richtigen Prüfung gehört und die Fragetexte "
                "unverändert sind."
            )
        return mapping

    @staticmethod
    def _extract_row_frage_texts(row: dict[str, Any]) -> dict[int, str]:
        """Collect the ``frageN`` texts carried by a single (key-normalised) row."""
        frage_texts: dict[int, str] = {}
        for key, value in row.items():
            match = _FRAGE_KEY_RE.match(key)
            if match and value is not None and str(value).strip():
                frage_texts[int(match.group(1))] = str(value)
        return frage_texts

    @staticmethod
    def _layout_signature(frage_texts: dict[int, str]) -> frozenset[tuple[int, str]]:
        """Cache key for a row's ``frageN`` layout: (column, normalised text).

        Two rows with the same questions in the same columns share a key (one
        resolution); a reordered variant produces a different key and is
        resolved independently.
        """
        return frozenset(
            (col, _normalize_text(text)) for col, text in frage_texts.items()
        )

    @staticmethod
    def _compose_source_attempt_id(
        external_id: str,
        started_at: datetime | None,
        attempt_number: int,
        answers: list[AnswerRecord],
    ) -> str:
        """Deterministic idempotency key over (student, start, attempt).

        Persisted in ``attempts.source_attempt_id`` and used for the
        ``(institution_id, source, source_attempt_id)`` duplicate check on
        re-import — its format must stay stable.

        When ``started_at`` is present the key is ``email|isoformat|N``. When
        it is **missing** the ``attempt_number`` is the only distinguishing
        component, and it is assigned from row order — which is *not* stable
        across Moodle re-exports, so a purely positional key could renumber
        attempts and skip a genuinely new one as a duplicate. In that case we
        fall back to a content hash of the answers: stable under reordering
        and distinct per distinct answer set. (Two timestamp-less attempts
        with identical answers are then indistinguishable and dedup to one —
        the safe choice, since nothing in the source tells them apart.)
        """
        if started_at:
            return f"{external_id}|{started_at.isoformat()}|{attempt_number}"
        digest = hashlib.sha256()
        for answer in answers:
            digest.update(
                f"{answer.exam_question_id}\x1f{answer.given_answer or ''}\x1e".encode()
            )
        return f"{external_id}|h:{digest.hexdigest()[:16]}"
