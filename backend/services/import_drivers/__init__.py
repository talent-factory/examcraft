"""Results-import drivers.

A driver wraps reading a source (JSON file, Moodle Web Service, …) and
returns a uniform ``ImportPayload``. ``ImportService`` is
source-agnostic and only operates on the payload.
"""

from services.import_drivers.base import (
    BaseImportDriver,
    ColumnMappingError,
    ImportDriverError,
)
from services.import_drivers.moodle_api_driver import (
    MoodleApiAuthError,
    MoodleApiDriver,
    MoodleApiSchemaError,
    MoodleConnectionMissingError,
)
from services.import_drivers.moodle_json_driver import MoodleJsonDriver
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
    "ColumnMappingError",
    "MoodleJsonDriver",
    "MoodleApiDriver",
    "MoodleApiAuthError",
    "MoodleApiSchemaError",
    "MoodleConnectionMissingError",
    "ImportPayload",
    "StudentRef",
    "AttemptRecord",
    "AnswerRecord",
    "ImportRowError",
]
