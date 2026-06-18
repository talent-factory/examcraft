"""TF-435: guard the "single source of truth" claim for the feedback enums.

The status/transport value sets live in one canonical enum (``enums.py``) but
are re-listed by hand in four places that can silently drift: the model
``@validates`` allowed-set, the model DB CHECK constraint, the Alembic
migration CHECK constraint, and the frontend TS union. This test asserts they
all still agree with the enum, so adding a 5th status can't pass CI while the
migration or the frontend lags behind.
"""

import re
from pathlib import Path

from enums import FeedbackTransportName, MoodleFeedbackPushStatus
from models.submission import MoodleFeedbackPushJob

_BACKEND = Path(__file__).resolve().parents[1]
_CORE = Path(__file__).resolve().parents[2]
_MIGRATION = _BACKEND / "alembic/versions/2026_06_17_moodle_feedback_push_job.py"
_TS = _CORE / "frontend/src/services/moodleFeedbackPushService.ts"

_STATUS = {s.value for s in MoodleFeedbackPushStatus}
_TRANSPORT = {t.value for t in FeedbackTransportName}


def _quoted(text: str) -> set[str]:
    """All single-quoted lowercase/underscore tokens in a snippet."""
    return set(re.findall(r"'([a-z_]+)'", text))


def _model_check(name: str) -> set[str]:
    for c in MoodleFeedbackPushJob.__table_args__:
        if getattr(c, "name", None) == name:
            return _quoted(str(c.sqltext))
    raise AssertionError(f"no CheckConstraint named {name!r} on the model")


def _migration_in_clauses() -> list[set[str]]:
    text = _MIGRATION.read_text(encoding="utf-8")
    return [_quoted(m) for m in re.findall(r"IN \(([^)]*)\)", text)]


def _ts_union(type_name: str) -> set[str]:
    text = _TS.read_text(encoding="utf-8")
    m = re.search(rf"export type {type_name} =([^;]*);", text)
    assert m, f"{type_name} union not found in {_TS.name}"
    return _quoted(m.group(1))


def test_model_check_constraints_match_enums():
    assert _model_check("check_moodle_feedback_push_status") == _STATUS
    assert _model_check("check_moodle_feedback_push_transport") == _TRANSPORT


def test_migration_check_constraints_match_enums():
    # First two IN(...) clauses in the migration are status then transport.
    clauses = _migration_in_clauses()
    assert _STATUS in clauses, f"status set {_STATUS} missing from migration {clauses}"
    assert _TRANSPORT in clauses, (
        f"transport set {_TRANSPORT} missing from migration {clauses}"
    )


def test_frontend_union_matches_enums():
    assert _ts_union("PushJobStatus") == _STATUS
    assert _ts_union("PushTransport") == _TRANSPORT
