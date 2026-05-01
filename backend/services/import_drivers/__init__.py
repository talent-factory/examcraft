"""Results-import drivers.

A driver wraps reading a source (CSV file, Moodle Web Service, …) and
returns a uniform ``ImportPayload``. ``ImportService`` is
source-agnostic and only operates on the payload.
"""

from services.import_drivers.base import (
    BaseImportDriver,
    ImportDriverError,
    EmptyCsvError,
    MissingColumnError,
    UnparseableCsvError,
)
from services.import_drivers.moodle_csv_driver import MoodleCsvDriver
from services.import_drivers.payloads import (
    AnswerRecord,
    AttemptRecord,
    ImportPayload,
    ImportRowError,
    StudentRef,
)

__all__ = [
    "BaseImportDriver",
    "ImportDriverError",
    "EmptyCsvError",
    "MissingColumnError",
    "UnparseableCsvError",
    "MoodleCsvDriver",
    "ImportPayload",
    "StudentRef",
    "AttemptRecord",
    "AnswerRecord",
    "ImportRowError",
]
