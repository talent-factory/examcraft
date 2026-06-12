"""Shared point suggestion utility for exam questions."""

import logging

logger = logging.getLogger(__name__)

POINT_SUGGESTIONS = {
    ("single_choice", "easy"): 2,
    ("single_choice", "medium"): 4,
    ("single_choice", "hard"): 6,
    ("multiple_choice", "easy"): 3,
    ("multiple_choice", "medium"): 5,
    ("multiple_choice", "hard"): 8,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 2,
    ("true_false", "hard"): 3,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 6,
    ("open_ended", "hard"): 10,
}

DEFAULT_POINTS = 4.0


def suggest_points(question_type: str, difficulty: str) -> float:
    """Return suggested point value for a question based on type and difficulty.

    Falls back to DEFAULT_POINTS for unrecognized type/difficulty combinations.
    """
    pts = POINT_SUGGESTIONS.get((question_type, difficulty))
    if pts is None:
        logger.warning(
            "No point suggestion for (%s, %s), falling back to %.1f",
            question_type,
            difficulty,
            DEFAULT_POINTS,
        )
        return DEFAULT_POINTS
    return float(pts)
