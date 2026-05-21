"""Pure function: percentage → grade label.

Three config variants share the same evaluator:

* ``linear`` — single linear interpolation between ``min_grade`` and
  ``max_grade`` (Frankreich 0–20, Niederlande 1–10, Prozent).
* ``linear_segments`` — piecewise linear with a pivot at the passing
  boundary (Schweiz 1.0–6.0 with pivot at 50 %).
* ``stepped`` — discrete buckets sorted descending by ``min_pct``
  (Deutschland 1.0–5.0, ECTS A–F, Pass/Fail).

Why a pure function (no ORM, no session): grade evaluation is hot —
called once per submission for the final notenexport and once per cell
in the per-question stats — and any DB lookup here defeats the
in-memory caching the export service does on the scheme dict. Pass the
loaded ``GradingScheme.config`` dict in; the evaluator never touches a
``Session``.

The output is a string because schemes mix numeric (``"4.0"``), letter
(``"A"``), and pass/fail (``"Pass"``) labels in the same column of the
notenexport. Rounding decimals is the caller's concern only when the
config sets ``round_to`` — for stepped schemes the ``grade_label`` is
already canonical and is returned verbatim.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class GradingSchemeError(ValueError):
    """Raised when the scheme config cannot be evaluated.

    Subclass of ``ValueError`` so existing API handlers that translate
    ValueError → 422 keep working without bespoke catches.
    """


def percentage_to_grade(percentage: float, scheme_config: dict[str, Any]) -> str:
    """Map ``percentage`` (0–100) to the scheme's grade label.

    Out-of-range percentages (< 0 or > 100) are clamped — float drift
    from aggregate calculations should not surface as a "no matching
    step" crash on the export path. Severe drift is logged once so
    upstream data corruption stays visible.
    """
    if scheme_config is None:
        raise GradingSchemeError("scheme_config darf nicht None sein")

    pct = _clamp_with_warn(percentage, "percentage_to_grade")
    scheme_type = scheme_config.get("type")

    if scheme_type == "linear":
        return _evaluate_linear(pct, scheme_config)
    if scheme_type == "linear_segments":
        return _evaluate_linear_segments(pct, scheme_config)
    if scheme_type == "stepped":
        return _evaluate_stepped(pct, scheme_config)
    raise GradingSchemeError(
        f"Unbekannter scheme_config.type {scheme_type!r} — "
        "erwartet: linear, linear_segments, stepped"
    )


def is_passing(
    percentage: float,
    scheme_config: dict[str, Any],
    *,
    passing_percentage: float = 50.0,
) -> bool:
    """Return True when the percentage maps to a passing grade.

    Stepped schemes carry the canonical pass/fail per step — the
    matching step's ``is_passing`` flag is authoritative.

    For linear and linear_segments schemes the caller (typically the
    statistics service or the export service) passes the exam's
    ``passing_percentage`` as the threshold. The scheme's
    ``pass_grade_label`` is a UI hint only and is intentionally NOT
    interpreted as a threshold — for Swiss-style schemes the label is
    a *grade* (``"4.0"``), not a percentage.
    """
    pct = _clamp_with_warn(percentage, "is_passing")
    scheme_type = scheme_config.get("type")

    if scheme_type == "stepped":
        step = _find_step(pct, scheme_config)
        return bool(step.get("is_passing", False))

    return pct >= passing_percentage


# ---------------------------------------------------------------------------
# Variant evaluators
# ---------------------------------------------------------------------------


def _evaluate_linear(pct: float, config: dict[str, Any]) -> str:
    min_pct = _required_float(config, "min_pct")
    max_pct = _required_float(config, "max_pct")
    min_grade = _required_float(config, "min_grade")
    max_grade = _required_float(config, "max_grade")
    if max_pct <= min_pct:
        raise GradingSchemeError(
            f"linear: max_pct ({max_pct}) muss grösser min_pct ({min_pct}) sein"
        )

    ratio = (pct - min_pct) / (max_pct - min_pct)
    ratio = _clamp(ratio, 0.0, 1.0)
    raw_grade = min_grade + ratio * (max_grade - min_grade)
    return _format_numeric(raw_grade, config.get("round_to"))


def _evaluate_linear_segments(pct: float, config: dict[str, Any]) -> str:
    segments = config.get("segments") or []
    if not segments:
        raise GradingSchemeError("linear_segments: segments darf nicht leer sein")

    # Find the segment whose [from_pct, to_pct] range contains pct. The
    # rightmost segment owns ``to_pct`` so 100 % lands on its to_grade.
    # The model validator guarantees segments cover [0, 100] continuously,
    # so a missing match means the scheme was bypassed (e.g. a raw dict
    # built in test code) — raise rather than silently snapping to the
    # closest segment, which masks the misconfiguration.
    ordered = sorted(segments, key=lambda s: _required_float(s, "from_pct"))
    chosen: dict[str, Any] | None = None
    for index, seg in enumerate(ordered):
        from_pct = _required_float(seg, "from_pct")
        to_pct = _required_float(seg, "to_pct")
        is_last = index == len(ordered) - 1
        in_range = from_pct <= pct < to_pct or (is_last and pct == to_pct)
        if in_range:
            chosen = seg
            break

    if chosen is None:
        raise GradingSchemeError(
            f"linear_segments: keine Segment-Range deckt {pct:.2f}% — "
            "Scheme-Config ist ungültig (segments müssen [0, 100] "
            "lückenlos abdecken)"
        )

    from_pct = _required_float(chosen, "from_pct")
    to_pct = _required_float(chosen, "to_pct")
    from_grade = _required_float(chosen, "from_grade")
    to_grade = _required_float(chosen, "to_grade")
    if to_pct <= from_pct:
        raise GradingSchemeError(
            f"linear_segments: to_pct ({to_pct}) muss grösser from_pct "
            f"({from_pct}) sein"
        )

    ratio = (pct - from_pct) / (to_pct - from_pct)
    ratio = _clamp(ratio, 0.0, 1.0)
    raw_grade = from_grade + ratio * (to_grade - from_grade)
    return _format_numeric(raw_grade, config.get("round_to"))


def _evaluate_stepped(pct: float, config: dict[str, Any]) -> str:
    step = _find_step(pct, config)
    label = step.get("grade_label")
    if label is None:
        raise GradingSchemeError(f"stepped: step ohne grade_label: {step}")
    return str(label)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_step(pct: float, config: dict[str, Any]) -> dict[str, Any]:
    steps = config.get("steps") or []
    if not steps:
        raise GradingSchemeError("stepped: steps darf nicht leer sein")

    # Sort descending by min_pct: the first step we hit is the highest
    # threshold the percentage clears. This tolerates seed/import
    # orderings that aren't already sorted.
    sorted_steps = sorted(
        steps, key=lambda s: _required_float(s, "min_pct"), reverse=True
    )
    for step in sorted_steps:
        if pct >= _required_float(step, "min_pct"):
            return step
    # Below every threshold: return the lowest step (last after sort).
    return sorted_steps[-1]


def _format_numeric(value: float, round_to: Any) -> str:
    step = _coerce_float(round_to)
    if step is None or step <= 0:
        # No rounding requested: keep one decimal so "4.0" stays "4.0"
        # in the export rather than "4" — display formats expect the
        # explicit decimal for numeric schemes.
        return f"{value:.1f}"

    rounded = round(value / step) * step
    decimals = _decimals_in_step(step)
    return f"{rounded:.{decimals}f}"


def _decimals_in_step(step: float) -> int:
    text = f"{step:.10f}".rstrip("0").rstrip(".")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def _required_float(mapping: dict[str, Any], key: str) -> float:
    if key not in mapping:
        raise GradingSchemeError(f"Fehlender Pflicht-Key: {key!r} in {mapping!r}")
    value = _coerce_float(mapping[key])
    if value is None:
        raise GradingSchemeError(
            f"Key {key!r} in {mapping!r} ist nicht in float konvertierbar"
        )
    return value


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# Drift up to 1 percentage point is normal float arithmetic — anything
# beyond that points at a real data bug and should leave a trace.
_CLAMP_LOG_THRESHOLD = 1.0


def _clamp_with_warn(value: float, source: str) -> float:
    """Clamp to [0, 100] and log when the input was meaningfully out of range."""
    if value < -_CLAMP_LOG_THRESHOLD or value > 100.0 + _CLAMP_LOG_THRESHOLD:
        logger.warning(
            "%s: percentage %.4f out of [0, 100] — clamping. "
            "Inspect upstream aggregation for data bug.",
            source,
            value,
        )
    return _clamp(value, 0.0, 100.0)
