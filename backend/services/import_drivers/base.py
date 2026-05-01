"""Abstract base for import drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Protocol

from services.import_drivers.payloads import ImportPayload


class ExamLike(Protocol):
    """Minimal exam interface needed by a driver.

    Decouples drivers from the SQLAlchemy class so tests can pass tiny
    stubs.
    """

    id: int
    questions: list[Any]  # ExamQuestion-like: .id, .position


class ImportDriverError(Exception):
    """Hard failure: source is not parseable or structurally unsuitable.

    Driver errors abort the import (job ``status='failed'``, no
    persistence). Per-row issues go into ``ImportPayload.errors``
    instead.
    """


class EmptyCsvError(ImportDriverError):
    """CSV contains no data rows."""


class MissingColumnError(ImportDriverError):
    """A required column (e.g. external_id) is missing from the header."""


class UnparseableCsvError(ImportDriverError):
    """CSV is binary-corrupt or has an unknown encoding."""


class BaseImportDriver(ABC):
    """Contract for all drivers.

    Implementation expectations:

    * **Stateless**: each ``parse()`` call is self-contained. No
      module-level caches that survive between calls.
    * **Thread-safe**: drivers are registered as singletons in
      ``ImportService.DRIVERS``; ``parse()`` may be called concurrently
      and must not mutate driver state.
    * **Idempotent**: re-parsing the same source must produce the same
      ``ImportPayload`` (same ``source_attempt_id`` per attempt).
    * **Pro-row tolerance**: malformed rows go to ``payload.errors``.
      Structural failures raise an ``ImportDriverError`` subclass.

    ``name`` must be unique across registered drivers and match the
    DB CHECK constraint on ``import_jobs.driver_name``.
    """

    name: ClassVar[str]

    @abstractmethod
    def parse(self, source: bytes | str, *, exam: ExamLike) -> ImportPayload:
        """Turn the source into an ``ImportPayload``.

        Args:
            source: file bytes (uploads) or string (tests).
            exam: target exam (column-to-question mapping via
                ``position``).

        Returns:
            Complete payload incl. warnings + per-row errors.

        Raises:
            ImportDriverError: hard failures
                (Empty/Missing/Unparseable).
        """
        ...
