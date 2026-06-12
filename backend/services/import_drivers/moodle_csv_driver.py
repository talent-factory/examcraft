"""Moodle CSV driver (Spec section 5.2).

Processes the "Quiz Responses Export" (Detailed attempt report) from
Moodle. Tolerant of:

* DE/EN column names (``Vorname``/``First name`` etc.)
* ``;``, ``,``, and ``\\t`` separators (auto-detected via ``csv.Sniffer``)
* UTF-8 with/without BOM, Latin-1 fallback
* missing optional columns (e.g. ``Versuch``)

Answer columns match ``^(Antwort|Response)\\s*\\d+$`` and are mapped
position-based onto ``ExamQuestion.position``.

Per-row tolerance: malformed individual rows land in ``payload.errors``
and don't abort the import. Structural problems (missing header,
missing external_id column) raise ``ImportDriverError`` subclasses.

Visibility: the driver records non-fatal degradations (encoding
fallback, sniffer fallback, unparseable dates, non-numeric attempt
numbers) into ``payload.warnings`` and ``payload.errors`` so the
operator can diagnose silent data quirks via the import job rather
than via server logs alone.
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections import defaultdict
from datetime import datetime, timezone
from typing import ClassVar

from pydantic import ValidationError

from services.import_drivers.base import (
    BaseImportDriver,
    EmptyCsvError,
    ExamLike,
    MissingColumnError,
    UnparseableCsvError,
)
from services.import_drivers.payloads import (
    AnswerRecord,
    AttemptRecord,
    ImportPayload,
    ImportRowError,
    StudentRef,
)


logger = logging.getLogger(__name__)


# Surplus fields — a row with more fields than the header (e.g. an extra
# exported column, a stray delimiter, or broken quoting) — are collected
# by ``csv.DictReader`` under its ``restkey``. The default is ``None``,
# which then fails ``AttemptRecord.raw_payload`` (``dict[str, Any]``
# rejects a non-string key); the row surfaced as a row-level error and
# was not imported. We give the restkey an explicit string name so the
# key is always valid and the overflow can be surfaced as a per-row
# warning while the row is still imported. The full original row —
# including the overflow values — is preserved in ``raw_payload`` under
# this key, so a misaligned row stays recoverable. (TF-411)
_OVERFLOW_KEY = "_unmapped_columns"


# Date formats encountered in Moodle exports. Try-order matters: the
# first match wins, so list the most specific/common variants first.
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


# German long-form dates ("12. Juni 2026 11:55") never parsed via
# ``strptime``/``%B``: that directive is locale-bound and only matches
# English month names under the container's C locale. We map the names
# ourselves so parsing is locale-independent and thread-safe (no
# ``setlocale``, which mutates global process state). (TF-411)
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
    """Parse a German long-form date locale-independently.

    Returns a naïve datetime (caller normalises to UTC, consistent with
    the other naïve formats) or ``None`` if the shape or month name does
    not match.
    """
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
        # Out-of-range day/time (e.g. "31. Februar") — treat as unparseable.
        return None


def _parse_datetime(raw: str | None) -> datetime | None:
    """Try known Moodle formats; return ``None`` on miss.

    Result is always tz-aware UTC. Naïve formats (``%Y-%m-%d %H:%M:%S``,
    ``%d.%m.%Y, %H:%M`` etc.) are assumed to be UTC at source — Moodle
    exports use the site timezone but the column never carries the
    offset, so we normalise rather than mix naïve/aware values.

    Why UTC normalisation matters:
    * the ORM column is ``DateTime(timezone=True)`` — Postgres silently
      coerces naïve values, which then compare-crash against aware ones
      from the ISO fallback (``min``/``max`` raises ``TypeError``);
    * ``_compose_source_attempt_id`` uses ``isoformat()`` in the
      idempotency key — naïve and aware values produce different keys
      for the same wall-clock instant and silently bypass the duplicate
      check on re-import.
    """
    if not raw:
        return None
    value = raw.strip()
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
        # German long-form ("12. Juni 2026 11:55") — locale-independent.
        parsed = _parse_german_long_date(value)
    if parsed is None:
        # ISO-8601 fallback (with/without timezone, ``Z`` suffix etc.)
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalise_header(name: str) -> str:
    """Whitespace + case normalisation for header comparison."""
    return " ".join(name.split()).strip().lower()


class MoodleCsvDriver(BaseImportDriver):
    """Reads Moodle "Quiz Responses Export" CSVs."""

    name: ClassVar[str] = "moodle_csv"

    # Column aliases (case-insensitive). Order = priority.
    EMAIL_COLUMNS: ClassVar[tuple[str, ...]] = (
        "e-mail-adresse",
        "email address",
        "email",
        "e-mail",
    )
    FIRST_NAME_COLUMNS: ClassVar[tuple[str, ...]] = ("vorname", "first name")
    LAST_NAME_COLUMNS: ClassVar[tuple[str, ...]] = (
        "nachname",
        "surname",
        "last name",
    )
    STARTED_COLUMNS: ClassVar[tuple[str, ...]] = (
        "begonnen am",
        "started",
        "started on",
    )
    SUBMITTED_COLUMNS: ClassVar[tuple[str, ...]] = (
        "beendet",
        "completed",
        "finished",
    )
    STATUS_COLUMNS: ClassVar[tuple[str, ...]] = ("status", "state")
    ATTEMPT_COLUMNS: ClassVar[tuple[str, ...]] = ("versuch", "attempt")
    # TF-336: Optional class hint column. ImportService reads this to
    # auto-attach the student to a StudentClass with the same name.
    CLASS_COLUMNS: ClassVar[tuple[str, ...]] = (
        "klasse",
        "class",
        "kurs",
        "course",
        "group",
        "gruppe",
    )

    ANSWER_COLUMN_REGEX: ClassVar[re.Pattern[str]] = re.compile(
        r"^(antwort|response)\s*(\d+)$",
        re.IGNORECASE,
    )

    def parse(
        self,
        source: bytes | str,
        *,
        exam: ExamLike,
        db=None,  # unused: CSV is self-contained.
    ) -> ImportPayload:
        text, encoding = self._decode(source)
        if not text.strip():
            raise EmptyCsvError("CSV ist leer")

        dialect, sniffer_fallback = self._sniff_dialect(text)
        reader = csv.DictReader(
            io.StringIO(text), dialect=dialect, restkey=_OVERFLOW_KEY
        )

        raw_headers = reader.fieldnames or []
        if not raw_headers:
            raise UnparseableCsvError("CSV hat keinen Header")

        header_index = {_normalise_header(h): h for h in raw_headers}

        email_col = self._find_column(header_index, self.EMAIL_COLUMNS)
        if not email_col:
            raise MissingColumnError(
                "Pflichtspalte für external_id (E-Mail-Adresse / Email "
                "address) fehlt im CSV-Header"
            )

        first_name_col = self._find_column(header_index, self.FIRST_NAME_COLUMNS)
        last_name_col = self._find_column(header_index, self.LAST_NAME_COLUMNS)
        started_col = self._find_column(header_index, self.STARTED_COLUMNS)
        submitted_col = self._find_column(header_index, self.SUBMITTED_COLUMNS)
        attempt_col = self._find_column(header_index, self.ATTEMPT_COLUMNS)
        class_col = self._find_column(header_index, self.CLASS_COLUMNS)

        answer_columns = self._find_answer_columns(raw_headers)
        questions_by_position: dict[int, int] = {
            q.position: q.id for q in exam.questions
        }

        rows = list(reader)
        if not rows:
            raise EmptyCsvError("CSV enthält keine Datenzeilen")

        payload = ImportPayload(
            exam_id=exam.id,
            driver_name=self.name,
            source_metadata={
                "delimiter": dialect.delimiter,
                "header_count": len(raw_headers),
                "answer_column_count": len(answer_columns),
                "row_count": len(rows),
                "encoding": encoding,
                "sniffer_fallback": sniffer_fallback,
            },
        )

        # Surface non-fatal degradations as warnings so the UI shows
        # them. Latin-1 always decodes any byte input — mojibake from
        # a non-UTF-8 export would silently flow through unless flagged.
        if encoding in ("cp1252", "latin-1"):
            logger.warning(
                "MoodleCsvDriver: %s-Fallback aktiv — Umlaute prüfen. exam_id=%s",
                encoding,
                exam.id,
            )
            payload.warnings.append(
                f"Encoding-Fallback auf {encoding} — Umlaute prüfen "
                f"(Quelle scheint nicht UTF-8 zu sein)"
            )
        if sniffer_fallback:
            logger.warning(
                "MoodleCsvDriver: csv.Sniffer fehlgeschlagen — Fallback "
                "auf Komma-Trennung. exam_id=%s",
                exam.id,
            )
            payload.warnings.append(
                "Trenner-Erkennung fehlgeschlagen — Fallback auf Komma. "
                "Wenn die CSV ;-getrennt ist, prüfe das Quoting."
            )

        if not answer_columns:
            payload.warnings.append(
                "Keine Antwort-Spalten gefunden "
                "(erwartet: 'Antwort N' oder 'Response N')"
            )
        elif len(answer_columns) != len(questions_by_position):
            payload.warnings.append(
                f"Spaltenanzahl ({len(answer_columns)}) passt nicht zur "
                f"Fragenanzahl der Prüfung ({len(questions_by_position)})"
            )

        # Answer columns without a matching exam question — emit once
        # rather than per row.
        for col, position in answer_columns:
            if position not in questions_by_position:
                payload.warnings.append(
                    f"Spalte '{col}' (Position {position}) hat keine "
                    f"zugehörige Frage in der Prüfung"
                )

        students_by_id: dict[str, StudentRef] = {}
        attempt_counters: dict[str, int] = defaultdict(int)

        for row_idx, row in enumerate(rows, start=2):  # 1 = header
            try:
                self._process_row(
                    row=row,
                    row_idx=row_idx,
                    payload=payload,
                    students_by_id=students_by_id,
                    attempt_counters=attempt_counters,
                    email_col=email_col,
                    first_name_col=first_name_col,
                    last_name_col=last_name_col,
                    started_col=started_col,
                    submitted_col=submitted_col,
                    attempt_col=attempt_col,
                    class_col=class_col,
                    answer_columns=answer_columns,
                    questions_by_position=questions_by_position,
                )
            except ValidationError as exc:
                payload.errors.append(
                    ImportRowError(
                        row_index=row_idx,
                        reason=f"Pydantic-Validierung: {exc}",
                    )
                )
            except (ValueError, KeyError, TypeError) as exc:
                payload.errors.append(
                    ImportRowError(row_index=row_idx, reason=str(exc))
                )
            # No bare ``except Exception`` here: unexpected errors
            # (AttributeError from a model rename, NotImplementedError
            # from a partially-stubbed driver subclass, …) must reach
            # ``ImportService._fail_job`` so the operator sees a job
            # failure with a traceback rather than 100 mystery row
            # warnings that "mostly worked".

        # If the sniffer fell back AND most rows failed for the same
        # reason, the delimiter is almost certainly wrong. Prepend an
        # actionable hint so the operator doesn't chase per-row errors.
        if (
            sniffer_fallback
            and len(rows) > 0
            and len(payload.errors) >= max(3, int(len(rows) * 0.5))
        ):
            reasons = {e.reason for e in payload.errors}
            if len(reasons) <= 2:
                payload.warnings.insert(
                    0,
                    "Vermutlich falscher Trenner erkannt: "
                    f"{len(payload.errors)} von {len(rows)} Zeilen melden "
                    f"denselben Fehler ({next(iter(reasons))!r}). "
                    "Prüfe, ob die CSV ;-getrennt ist.",
                )

        return payload

    @staticmethod
    def _decode(source: bytes | str) -> tuple[str, str]:
        """Decode bytes; return (text, encoding) so callers can flag
        non-UTF-8 fallbacks.

        Order matters: UTF-8 (with/without BOM) wins, then cp1252 for
        Windows-Excel exports, then Latin-1 as the universal fallback.
        Latin-1 always succeeds on any byte sequence so binary input
        masquerading as CSV would silently decode to garbage — we sniff
        for a high ratio of non-printable bytes first and reject obvious
        binaries with a clear error.
        """
        if isinstance(source, str):
            return source, "str"

        non_printable = sum(
            1 for b in source[:4096] if b < 9 or (13 < b < 32 and b != 27)
        )
        if non_printable > len(source[:4096]) * 0.10:
            raise UnparseableCsvError(
                "CSV-Bytes wirken binär — wurde versehentlich eine "
                "Excel/PDF-Datei statt CSV hochgeladen?"
            )

        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return source.decode(encoding), encoding
            except UnicodeDecodeError:
                continue
        raise UnparseableCsvError("CSV-Bytes konnten nicht dekodiert werden")

    @staticmethod
    def _sniff_dialect(text: str) -> tuple[type[csv.Dialect] | csv.Dialect, bool]:
        """Sniff CSV dialect; return (dialect, fallback_used).

        ``fallback_used=True`` means csv.Sniffer raised — usually because
        the sample is too uniform or quoting confuses the heuristic.
        Caller surfaces this as a warning so the operator can spot a
        misparsed semicolon CSV.
        """
        sample = text[:8192]
        try:
            return csv.Sniffer().sniff(sample, delimiters=";,\t"), False
        except csv.Error:
            return csv.excel, True

    @staticmethod
    def _find_column(
        header_index: dict[str, str], aliases: tuple[str, ...]
    ) -> str | None:
        for alias in aliases:
            if alias in header_index:
                return header_index[alias]
        return None

    @classmethod
    def _find_answer_columns(cls, headers: list[str]) -> list[tuple[str, int]]:
        """List of ``(col_name, position)`` sorted by position."""
        matches: list[tuple[str, int]] = []
        for header in headers:
            match = cls.ANSWER_COLUMN_REGEX.match(header.strip())
            if match:
                matches.append((header, int(match.group(2))))
        matches.sort(key=lambda item: item[1])
        return matches

    @staticmethod
    def _compose_display_name(
        row: dict[str, str],
        first_name_col: str | None,
        last_name_col: str | None,
    ) -> str | None:
        first = (row.get(first_name_col) or "").strip() if first_name_col else ""
        last = (row.get(last_name_col) or "").strip() if last_name_col else ""
        full = " ".join(part for part in (first, last) if part)
        return full or None

    @staticmethod
    def _compose_source_attempt_id(
        external_id: str,
        started_at: datetime | None,
        attempt_number: int,
    ) -> str:
        """Deterministic over (external_id, started_at, attempt_number).

        Re-importing the same CSV yields identical keys and therefore
        idempotency. When ``started_at`` is missing, the literal
        ``no-start`` is used and uniqueness depends on
        ``attempt_number`` — sort the CSV by row before re-import to
        keep that stable.

        This format is **persisted** in ``attempts.source_attempt_id``
        and joined with the unique constraint
        ``(institution_id, source, source_attempt_id)``. Changing the
        format silently breaks idempotency for existing rows — treat
        any change as a data-migration boundary.

        Note (TF-411): rows imported *before* German long-date parsing
        worked had ``started_at=None`` (→ ``no-start`` key). Re-importing
        the same CSV now resolves a real ``started_at`` and therefore a
        *different* key, so such rows insert as new attempts rather than
        deduplicating. Expected for fresh imports; re-running a pre-fix
        partial import may create duplicates for the affected rows.
        """
        ts = started_at.isoformat() if started_at else "no-start"
        return f"{external_id}|{ts}|{attempt_number}"

    def _process_row(
        self,
        *,
        row: dict[str, str],
        row_idx: int,
        payload: ImportPayload,
        students_by_id: dict[str, StudentRef],
        attempt_counters: dict[str, int],
        email_col: str,
        first_name_col: str | None,
        last_name_col: str | None,
        started_col: str | None,
        submitted_col: str | None,
        attempt_col: str | None,
        class_col: str | None,
        answer_columns: list[tuple[str, int]],
        questions_by_position: dict[int, int],
    ) -> None:
        external_id = (row.get(email_col) or "").strip()
        if not external_id:
            raise ValueError("Leere external_id (E-Mail)")

        class_hint = (row.get(class_col) or "").strip() if class_col else ""
        class_hint = class_hint or None

        if external_id not in students_by_id:
            student = StudentRef(
                external_id=external_id,
                display_name=self._compose_display_name(
                    row, first_name_col, last_name_col
                ),
                class_hint=class_hint,
            )
            students_by_id[external_id] = student
            payload.students.append(student)
        elif class_hint and not students_by_id[external_id].class_hint:
            # Same student, multiple rows: keep the first non-empty hint
            # rather than overwriting (the first row tends to be the
            # canonical one in Moodle's grouped exports).
            students_by_id[external_id].class_hint = class_hint

        attempt_number, attempt_warning = self._extract_attempt_number(row, attempt_col)
        if attempt_warning:
            payload.warnings.append(
                f"Zeile {row_idx}: {attempt_warning} — Auto-Increment verwendet"
            )
        if attempt_number is None:
            attempt_counters[external_id] += 1
            attempt_number = attempt_counters[external_id]

        started_raw = row.get(started_col) if started_col else None
        submitted_raw = row.get(submitted_col) if submitted_col else None
        started_at = _parse_datetime(started_raw)
        submitted_at = _parse_datetime(submitted_raw)
        if started_raw and started_raw.strip() and started_at is None:
            payload.warnings.append(
                f"Zeile {row_idx}: 'Begonnen am' nicht parsbar "
                f"({started_raw!r}) — wird als NULL persistiert"
            )
        if submitted_raw and submitted_raw.strip() and submitted_at is None:
            payload.warnings.append(
                f"Zeile {row_idx}: 'Beendet' nicht parsbar "
                f"({submitted_raw!r}) — wird als NULL persistiert"
            )

        # Surplus fields beyond the header (see _OVERFLOW_KEY). The row is
        # still imported, but a stray delimiter *early* in the row shifts
        # every named column right, so the answers (and even external_id)
        # of this row may be misaligned — not merely a harmless trailing
        # value. Warn loudly enough that the operator verifies the row
        # rather than dismissing it; the full original row is kept in
        # raw_payload[_OVERFLOW_KEY] so it stays recoverable.
        overflow = row.get(_OVERFLOW_KEY)
        if overflow:
            payload.warnings.append(
                f"Zeile {row_idx}: {len(overflow)} überzählige Spalte(n) "
                f"ohne Header — mögliche Spaltenverschiebung; "
                f"Antwort-Zuordnung dieser Zeile prüfen "
                f"(Quoting/Trenner der Quelle prüfen)"
            )

        answers: list[AnswerRecord] = []
        for col, position in answer_columns:
            question_id = questions_by_position.get(position)
            if question_id is None:
                continue
            given = (row.get(col) or "").strip() or None
            answers.append(
                AnswerRecord(
                    exam_question_id=question_id,
                    given_answer=given,
                )
            )

        payload.attempts.append(
            AttemptRecord(
                student_external_id=external_id,
                attempt_number=attempt_number,
                started_at=started_at,
                submitted_at=submitted_at,
                source_attempt_id=self._compose_source_attempt_id(
                    external_id, started_at, attempt_number
                ),
                answers=answers,
                raw_payload=dict(row),
            )
        )

    @staticmethod
    def _extract_attempt_number(
        row: dict[str, str], attempt_col: str | None
    ) -> tuple[int | None, str | None]:
        """Return ``(attempt_number, warning)``.

        ``warning`` is non-None when the column was present but
        unparseable — caller surfaces it so the operator notices their
        explicit attempt numbers were ignored.
        """
        if not attempt_col:
            return None, None
        raw = row.get(attempt_col)
        if not raw:
            return None, None
        try:
            return int(str(raw).strip()), None
        except (TypeError, ValueError):
            return (
                None,
                f"'Versuch'-Spalte enthält nicht-numerischen Wert {raw!r}",
            )
