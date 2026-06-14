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
    # ExamQuestion-like: .id, .position, optional .external_refs (dict,
    # may carry ``moodle_slot``) and .question.options (list) — the
    # Moodle drivers read these defensively via getattr.
    questions: list[Any]


class ImportDriverError(Exception):
    """Hard failure: source is not parseable or structurally unsuitable.

    Driver errors abort the import (job ``status='failed'``, no
    persistence). Per-row issues go into ``ImportPayload.errors``
    instead.
    """


class ColumnMappingError(ImportDriverError):
    """Answers cannot be safely mapped onto the exam's questions.

    Raised when the structural integrity of the answer->question mapping
    is in doubt -- e.g. a JSON ``frageN`` text matches 0 or >1 exam
    questions, or two ``frageN`` columns resolve to the same question.
    Aborting beats silently grading answers against the wrong questions.
    (TF-422, TF-423)
    """


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
    def parse(
        self,
        source: bytes | str,
        *,
        exam: ExamLike,
        db: Any | None = None,
    ) -> ImportPayload:
        """Turn the source into an ``ImportPayload``.

        Args:
            source: file bytes (uploads), JSON-encoded params, or
                a quiz id (depending on the driver).
            exam: target exam. How answers map onto its questions is
                driver-specific (the JSON driver matches by question
                text; the API driver by Moodle slot).
            db: optional SQLAlchemy session for drivers that need to
                load institution-scoped state (e.g. the API driver
                resolves ``moodle_connections``). The file-upload
                drivers ignore this argument.

        Returns:
            Complete payload incl. warnings + per-row errors.

        Raises:
            ImportDriverError: hard failures
                (Empty/Missing/Unparseable).
        """
        ...
