"""Tests for scripts/flatten_structured_answers.py with a fake DB session.

Covers what the one-off data fix must guarantee: only open_ended rows change,
dry-run writes nothing, --apply records old/new values in review_history, and
missing or non-open_ended IDs are reported with a non-zero exit code.
"""

import json
import types

import pytest

from scripts import flatten_structured_answers as script

RUBRIC = json.dumps(
    {"total_points": 5, "criteria": [{"aspect": "A", "points": 5, "description": "d"}]}
)
RENDERED = "**Gesamtpunkte: 5**\n\n**Bewertungskriterien:**\n\n- **A** (5 Punkte): d"


class _FakeSession:
    def __init__(self, rows):
        self._rows = rows
        self.added = []
        self.committed = False
        self.rolled_back = False

    def query(self, _model):
        rows = self._rows

        class _Query:
            def filter(self, *_args):
                return self

            def order_by(self, *_args):
                return self

            def all(self):
                return rows

        return _Query()

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def _row(id_, question_type, correct_answer, explanation=None):
    return types.SimpleNamespace(
        id=id_,
        question_type=question_type,
        review_status="pending",
        correct_answer=correct_answer,
        explanation=explanation,
    )


@pytest.fixture
def session(monkeypatch):
    import database

    holder = {}

    def factory(rows):
        holder["session"] = _FakeSession(rows)
        monkeypatch.setattr(database, "SessionLocal", lambda: holder["session"])
        return holder["session"]

    return factory


def test_dry_run_reports_but_writes_nothing(session):
    row = _row(1, "open_ended", "Text", RUBRIC)
    db = session([row])

    assert script.flatten([1], apply=False) == 0

    assert db.rolled_back and not db.committed


def test_apply_rewrites_and_records_history(session):
    row = _row(1, "open_ended", "Text", RUBRIC)
    db = session([row])

    assert script.flatten([1], apply=True) == 0

    assert db.committed
    assert row.explanation == RENDERED
    assert row.correct_answer == "Text"
    (history,) = db.added
    assert history.question_id == 1
    assert history.changed_by == script.CHANGED_BY
    assert history.changed_fields == {"explanation": {"old": RUBRIC, "new": RENDERED}}


def test_multiple_choice_is_never_touched(session):
    row = _row(2, "multiple_choice", '["A", "B"]', RUBRIC)
    db = session([row])

    assert script.flatten([2], apply=True) == 1

    assert row.correct_answer == '["A", "B"]'
    assert row.explanation == RUBRIC
    assert db.added == []


def test_missing_ids_return_non_zero(session):
    db = session([_row(1, "open_ended", "Text")])

    assert script.flatten([1, 99], apply=True) == 1

    assert db.added == []


def test_second_run_changes_nothing(session):
    row = _row(1, "open_ended", "Text", RENDERED)
    db = session([row])

    assert script.flatten([1], apply=True) == 0

    assert db.added == []
    assert row.explanation == RENDERED
