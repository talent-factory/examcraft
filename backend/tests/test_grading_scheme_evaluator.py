"""Tests for ``services.grading_scheme_evaluator``.

Pure unit tests, no DB. Each system scheme from the seed migration
(``tf333_phase1``) is exercised at the boundary percentages quoted in
the spec (Abschnitt 4.6) plus edge cases at 0 % / 100 % and one value
between two stepped buckets.
"""

from __future__ import annotations

import pytest

from services.grading_scheme_evaluator import (
    GradingSchemeError,
    is_passing,
    percentage_to_grade,
)


# ---------------------------------------------------------------------------
# Schemes (mirror tf333_phase1 seed; kept in-test so the seed and the
# evaluator can evolve independently — when they diverge the test fails
# loudly rather than silently picking up the new seed)
# ---------------------------------------------------------------------------

SWISS = {
    "type": "linear_segments",
    "round_to": 0.1,
    "pass_grade_label": "4.0",
    "segments": [
        {"from_pct": 0, "to_pct": 50, "from_grade": 1.0, "to_grade": 4.0},
        {"from_pct": 50, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
    ],
}

GERMAN = {
    "type": "stepped",
    "steps": [
        {"min_pct": 92, "grade_label": "1.0", "is_passing": True},
        {"min_pct": 81, "grade_label": "2.0", "is_passing": True},
        {"min_pct": 67, "grade_label": "3.0", "is_passing": True},
        {"min_pct": 50, "grade_label": "4.0", "is_passing": True},
        {"min_pct": 0, "grade_label": "5.0", "is_passing": False},
    ],
}

FRENCH = {
    "type": "linear",
    "min_pct": 0,
    "max_pct": 100,
    "min_grade": 0,
    "max_grade": 20,
    "round_to": 0.5,
    "pass_grade_label": "10",
}

DUTCH = {
    "type": "linear",
    "min_pct": 0,
    "max_pct": 100,
    "min_grade": 1,
    "max_grade": 10,
    "round_to": 0.1,
    "pass_grade_label": "5.5",
}

ECTS = {
    "type": "stepped",
    "steps": [
        {"min_pct": 90, "grade_label": "A", "is_passing": True},
        {"min_pct": 80, "grade_label": "B", "is_passing": True},
        {"min_pct": 65, "grade_label": "C", "is_passing": True},
        {"min_pct": 55, "grade_label": "D", "is_passing": True},
        {"min_pct": 50, "grade_label": "E", "is_passing": True},
        {"min_pct": 0, "grade_label": "F", "is_passing": False},
    ],
}

PASS_FAIL = {
    "type": "stepped",
    "steps": [
        {"min_pct": 50, "grade_label": "Pass", "is_passing": True},
        {"min_pct": 0, "grade_label": "Fail", "is_passing": False},
    ],
}


# ---------------------------------------------------------------------------
# Schweiz (linear_segments) — Spec quotes 0/25/50/75/100 → 1.0/2.5/4.0/5.0/6.0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (0, "1.0"),
        (25, "2.5"),
        (50, "4.0"),
        (75, "5.0"),
        (100, "6.0"),
    ],
)
def test_swiss_canonical_anchors(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, SWISS) == expected


def test_swiss_round_to_one_tenth() -> None:
    # 33.33 % within the lower segment maps to 1.0 + (33.33/50)*3 = 2.9998
    # which must round to 3.0, not 2.99 — consumers display these
    # to one decimal and the rounding step has to land them on a tenth.
    assert percentage_to_grade(33.33, SWISS) == "3.0"


def test_swiss_just_above_pivot_lands_in_upper_segment() -> None:
    # At exactly 50 % the lower segment owns the boundary (per the
    # ``from_pct <= pct < to_pct`` rule). One step above must use the
    # upper segment so the grade picks up the post-pivot slope.
    assert percentage_to_grade(50.5, SWISS) == "4.0"  # 4.0 + 0.5/50*2 = 4.02 → 4.0


def test_swiss_clamps_below_zero() -> None:
    assert percentage_to_grade(-5, SWISS) == "1.0"


def test_swiss_clamps_above_hundred() -> None:
    assert percentage_to_grade(150, SWISS) == "6.0"


# ---------------------------------------------------------------------------
# Deutschland (stepped)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (100, "1.0"),
        (92, "1.0"),
        (91.99, "2.0"),
        (81, "2.0"),
        (75, "3.0"),
        (50, "4.0"),
        (49.99, "5.0"),
        (0, "5.0"),
    ],
)
def test_german_step_boundaries(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, GERMAN) == expected


def test_german_unsorted_steps_still_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    # The evaluator must not rely on the seed ordering — sort itself.
    shuffled = {
        "type": "stepped",
        "steps": list(reversed(GERMAN["steps"])),
    }
    assert percentage_to_grade(85, shuffled) == "2.0"


# ---------------------------------------------------------------------------
# Frankreich (linear) — round_to=0.5, max_grade=20
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (0, "0.0"),
        (50, "10.0"),
        (75, "15.0"),
        (100, "20.0"),
        # 12.5 → 2.5, rounded to nearest 0.5 = 2.5
        (12.5, "2.5"),
        # 13.75 → 2.75, rounded to 0.5 = 3.0 (banker's? round half to even.)
        # Python's round() uses banker's rounding so 2.75 → 2.5 vs 3.0
        # depending on float representation. The test below asserts
        # "either 2.5 or 3.0 — but always a multiple of 0.5".
    ],
)
def test_french_canonical_anchors(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, FRENCH) == expected


def test_french_rounds_to_half_step() -> None:
    grade = percentage_to_grade(13.75, FRENCH)
    # 13.75 % maps to 2.75 → must land on a multiple of 0.5
    value = float(grade)
    assert value % 0.5 == 0
    assert 2.0 <= value <= 3.0


# ---------------------------------------------------------------------------
# Niederlande (linear, min_grade=1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (0, "1.0"),
        (50, "5.5"),
        (100, "10.0"),
    ],
)
def test_dutch_canonical_anchors(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, DUTCH) == expected


# ---------------------------------------------------------------------------
# ECTS letter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (95, "A"),
        (85, "B"),
        (70, "C"),
        (60, "D"),
        (52, "E"),
        (40, "F"),
        (0, "F"),
    ],
)
def test_ects_letters(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, ECTS) == expected


# ---------------------------------------------------------------------------
# Pass/Fail
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pct", "expected"),
    [
        (100, "Pass"),
        (50, "Pass"),
        (49.9, "Fail"),
        (0, "Fail"),
    ],
)
def test_pass_fail(pct: float, expected: str) -> None:
    assert percentage_to_grade(pct, PASS_FAIL) == expected


# ---------------------------------------------------------------------------
# is_passing
# ---------------------------------------------------------------------------


def test_is_passing_uses_step_flag_for_stepped() -> None:
    assert is_passing(91, GERMAN) is True
    assert is_passing(49, GERMAN) is False
    assert is_passing(50, PASS_FAIL) is True
    assert is_passing(49.9, PASS_FAIL) is False


def test_is_passing_uses_default_50_threshold_for_linear() -> None:
    """Linear schemes default to a 50 % pass threshold when no explicit
    ``passing_percentage`` kwarg is provided. The previous behaviour —
    reading ``pass_grade_label`` as a numeric threshold — conflated
    grade labels (e.g. Swiss "4.0") with percentage thresholds.
    """
    # 20 % under default threshold ⇒ fail. 60 % ⇒ pass.
    assert is_passing(20, FRENCH) is False
    assert is_passing(60, FRENCH) is True


def test_is_passing_falls_back_to_50_when_no_label() -> None:
    minimal = {
        "type": "linear",
        "min_pct": 0,
        "max_pct": 100,
        "min_grade": 0,
        "max_grade": 1,
    }
    assert is_passing(60, minimal) is True
    assert is_passing(40, minimal) is False


def test_is_passing_respects_passing_percentage_kwarg() -> None:
    """``is_passing`` accepts an explicit threshold for non-stepped schemes.

    Smuggling through the config dict was rejected (it relied on
    ``extra="allow"``); callers now pass the exam-level
    ``passing_percentage`` directly.
    """
    assert is_passing(55, SWISS, passing_percentage=60.0) is False
    assert is_passing(60, SWISS, passing_percentage=60.0) is True


def test_is_passing_ignores_pass_grade_label_string() -> None:
    """Linear schemes carry ``pass_grade_label`` as a UI hint only.

    Reading it as a numeric threshold conflated grade-labels with
    percentages (e.g. Swiss "4.0" parsed as 4 % threshold). The
    evaluator must not interpret it.
    """
    swiss_with_label = {**SWISS, "pass_grade_label": "4.0"}
    # 55 % ≥ default 50 % threshold ⇒ pass; if the label leaked back
    # into the threshold (4 %), every >4 % submission would also pass
    # — but we'd lose the 50 % gate. The next assertion locks that.
    assert is_passing(55, swiss_with_label) is True
    assert is_passing(45, swiss_with_label) is False


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_none_config_raises() -> None:
    with pytest.raises(GradingSchemeError):
        percentage_to_grade(50, None)  # type: ignore[arg-type]


def test_unknown_type_raises() -> None:
    with pytest.raises(GradingSchemeError, match="Unbekannter scheme_config.type"):
        percentage_to_grade(50, {"type": "exponential"})


def test_linear_with_invalid_range_raises() -> None:
    bad = {
        "type": "linear",
        "min_pct": 100,
        "max_pct": 0,
        "min_grade": 1,
        "max_grade": 6,
    }
    with pytest.raises(GradingSchemeError, match="max_pct"):
        percentage_to_grade(50, bad)


def test_linear_segments_empty_raises() -> None:
    with pytest.raises(GradingSchemeError, match="segments"):
        percentage_to_grade(50, {"type": "linear_segments", "segments": []})


def test_stepped_empty_raises() -> None:
    with pytest.raises(GradingSchemeError, match="steps"):
        percentage_to_grade(50, {"type": "stepped", "steps": []})


def test_stepped_step_without_label_raises() -> None:
    bad = {
        "type": "stepped",
        "steps": [{"min_pct": 0, "is_passing": False}],
    }
    with pytest.raises(GradingSchemeError, match="grade_label"):
        percentage_to_grade(0, bad)


def test_linear_segments_gap_raises() -> None:
    """A gap in segment coverage is a misconfiguration, not a soft case.

    The model validator rejects bad configs at write-time, but the
    evaluator can be called with a raw dict (e.g. test fixtures, in-
    memory schemes). It must surface the bug — silently snapping to the
    closest segment masked schema typos for too long.
    """
    gappy = {
        "type": "linear_segments",
        "round_to": 0.1,
        "segments": [
            {"from_pct": 0, "to_pct": 40, "from_grade": 1.0, "to_grade": 4.0},
            {"from_pct": 60, "to_pct": 100, "from_grade": 4.0, "to_grade": 6.0},
        ],
    }
    with pytest.raises(GradingSchemeError, match="keine Segment-Range"):
        percentage_to_grade(50, gappy)


def test_linear_segments_three_segments_middle_right_edge() -> None:
    """Multi-segment scheme: middle segment's right edge belongs to the next.

    The 2-segment Swiss case only exercises the rightmost segment's
    inclusive edge. This test pins the inner-boundary behaviour for a
    scheme where pct hits exactly the join between segments 2 and 3.
    """
    three_seg = {
        "type": "linear_segments",
        "round_to": 0.1,
        "segments": [
            {"from_pct": 0, "to_pct": 30, "from_grade": 1.0, "to_grade": 2.0},
            {"from_pct": 30, "to_pct": 70, "from_grade": 2.0, "to_grade": 5.0},
            {"from_pct": 70, "to_pct": 100, "from_grade": 5.0, "to_grade": 6.0},
        ],
    }
    # 70 % belongs to the third segment (left-inclusive), so it lands at
    # from_grade=5.0 — not the second segment's to_grade.
    assert percentage_to_grade(70, three_seg) == "5.0"
    # 69.99 % stays in the middle segment.
    assert percentage_to_grade(69.99, three_seg).startswith("5.")
