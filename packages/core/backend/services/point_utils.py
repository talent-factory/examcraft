"""Shared point suggestion utility for exam questions."""

POINT_SUGGESTIONS = {
    ("multiple_choice", "easy"): 2,
    ("multiple_choice", "medium"): 4,
    ("multiple_choice", "hard"): 6,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 2,
    ("true_false", "hard"): 3,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 6,
    ("open_ended", "hard"): 10,
}


def suggest_points(question_type: str, difficulty: str) -> float:
    return float(POINT_SUGGESTIONS.get((question_type, difficulty), 4))
