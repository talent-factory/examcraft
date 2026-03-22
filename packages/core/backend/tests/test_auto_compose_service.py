"""Unit tests for the auto-composition engine."""

from services.auto_compose_service import (
    compose_questions,
    QuestionCandidate,
    CompositionConstraints,
)


def _candidate(
    id: int,
    question_type: str = "open_ended",
    difficulty: str = "medium",
    bloom_level: int = 2,
    estimated_time_minutes: int = 5,
) -> QuestionCandidate:
    return QuestionCandidate(
        id=id,
        question_text=f"Question {id}",
        question_type=question_type,
        difficulty=difficulty,
        topic="Test",
        bloom_level=bloom_level,
        estimated_time_minutes=estimated_time_minutes,
    )


class TestComposeQuestions:
    def test_basic_point_budget(self):
        """Selects questions until point budget is reached."""
        candidates = [
            _candidate(1, "open_ended", "medium"),  # 6 pts
            _candidate(2, "open_ended", "easy"),  # 3 pts
            _candidate(3, "open_ended", "hard"),  # 10 pts
            _candidate(4, "multiple_choice", "easy"),  # 2 pts
        ]
        constraints = CompositionConstraints(target_points=12.0)
        result = compose_questions(candidates, constraints)

        assert result.total_points <= 12.0
        assert result.total_points > 0
        assert len(result.questions) >= 1

    def test_duration_budget(self):
        """Selects questions until duration budget is reached."""
        candidates = [
            _candidate(1, estimated_time_minutes=5),
            _candidate(2, estimated_time_minutes=3),
            _candidate(3, estimated_time_minutes=8),
        ]
        constraints = CompositionConstraints(target_duration_minutes=10)
        result = compose_questions(candidates, constraints)

        assert result.total_duration_minutes <= 10
        assert result.total_duration_minutes > 0

    def test_combined_budgets_stops_at_first(self):
        """Stops when either budget is reached."""
        candidates = [
            _candidate(
                1, "open_ended", "hard", estimated_time_minutes=20
            ),  # 10 pts, 20 min
            _candidate(
                2, "open_ended", "easy", estimated_time_minutes=3
            ),  # 3 pts, 3 min
        ]
        constraints = CompositionConstraints(
            target_points=100.0,
            target_duration_minutes=5,
        )
        result = compose_questions(candidates, constraints)

        # Duration budget (5 min) should prevent adding the 20-min question
        assert result.total_duration_minutes <= 5

    def test_bloom_distribution_targeting(self):
        """Questions are selected to match Bloom distribution targets."""
        candidates = [
            _candidate(1, bloom_level=1),
            _candidate(2, bloom_level=1),
            _candidate(3, bloom_level=3),
            _candidate(4, bloom_level=3),
            _candidate(5, bloom_level=5),
            _candidate(6, bloom_level=5),
        ]
        constraints = CompositionConstraints(
            target_points=50.0,
            bloom_distribution={1: 33, 3: 34, 5: 33},
        )
        result = compose_questions(candidates, constraints)

        bloom_levels = [q.bloom_level for q in result.questions]
        # Should pick a mix, not all from one level
        assert len(set(bloom_levels)) > 1

    def test_difficulty_distribution_targeting(self):
        """Questions are selected to match difficulty distribution targets."""
        candidates = [
            _candidate(1, difficulty="easy"),
            _candidate(2, difficulty="easy"),
            _candidate(3, difficulty="medium"),
            _candidate(4, difficulty="medium"),
            _candidate(5, difficulty="hard"),
            _candidate(6, difficulty="hard"),
        ]
        constraints = CompositionConstraints(
            target_points=50.0,
            difficulty_distribution={"easy": 33, "medium": 34, "hard": 33},
        )
        result = compose_questions(candidates, constraints)

        difficulties = [q.difficulty for q in result.questions]
        assert len(set(difficulties)) > 1

    def test_empty_candidates(self):
        """Empty candidate pool returns empty result with report."""
        constraints = CompositionConstraints(target_points=50.0)
        result = compose_questions([], constraints)

        assert result.questions == []
        assert result.total_points == 0
        assert result.constraint_report.overall_satisfaction >= 0

    def test_single_candidate(self):
        """Single candidate is selected if it fits the budget."""
        candidates = [_candidate(1, "open_ended", "medium")]  # 6 pts
        constraints = CompositionConstraints(target_points=10.0)
        result = compose_questions(candidates, constraints)

        assert len(result.questions) == 1
        assert result.questions[0].id == 1

    def test_budget_overshoot_prevention(self):
        """Does not select questions that would exceed budget."""
        candidates = [
            _candidate(1, "open_ended", "hard"),  # 10 pts
            _candidate(2, "multiple_choice", "easy"),  # 2 pts
        ]
        constraints = CompositionConstraints(target_points=5.0)
        result = compose_questions(candidates, constraints)

        # Only the 2-point question fits within budget
        assert result.total_points <= 5.0
        assert len(result.questions) == 1
        assert result.questions[0].suggested_points == 2.0

    def test_constraint_report_tolerance(self):
        """Constraint report correctly flags within/outside tolerance."""
        candidates = [
            _candidate(1, bloom_level=1),
            _candidate(2, bloom_level=1),
            _candidate(3, bloom_level=2),
        ]
        constraints = CompositionConstraints(
            target_points=50.0,
            bloom_distribution={1: 50, 2: 50},
        )
        result = compose_questions(candidates, constraints)
        report = result.constraint_report

        # Check bloom report has entries
        assert 1 in report.bloom_distribution
        assert 2 in report.bloom_distribution
        # Each entry has target and achieved
        for dr in report.bloom_distribution.values():
            assert dr.target_pct >= 0
            assert dr.achieved_pct >= 0

    def test_null_bloom_gets_base_score_only(self):
        """Candidates with None bloom_level get base score when bloom constraints active."""
        candidates = [
            _candidate(1, bloom_level=1),
            _candidate(2, bloom_level=None),  # NULL bloom
            _candidate(3, bloom_level=3),
        ]
        # Need to set bloom_level=None manually since _candidate default is 2
        candidates[1] = QuestionCandidate(
            id=2,
            question_text="Question 2",
            question_type="open_ended",
            difficulty="medium",
            topic="Test",
            bloom_level=None,
            estimated_time_minutes=5,
        )
        constraints = CompositionConstraints(
            target_points=50.0,
            bloom_distribution={1: 50, 3: 50},
        )
        result = compose_questions(candidates, constraints)

        # NULL-bloom candidate may still be selected (gets base score)
        # but bloom-matching candidates should be preferred
        ids = [q.id for q in result.questions]
        assert 1 in ids  # bloom=1 matches target
        assert 3 in ids  # bloom=3 matches target

    def test_deterministic_results(self):
        """Same input produces same output (no randomness)."""
        candidates = [
            _candidate(1, "open_ended", "easy", bloom_level=1),
            _candidate(2, "open_ended", "medium", bloom_level=2),
            _candidate(3, "open_ended", "hard", bloom_level=3),
        ]
        constraints = CompositionConstraints(
            target_points=20.0,
            bloom_distribution={1: 33, 2: 34, 3: 33},
        )
        result1 = compose_questions(candidates, constraints)
        result2 = compose_questions(candidates, constraints)

        ids1 = [q.id for q in result1.questions]
        ids2 = [q.id for q in result2.questions]
        assert ids1 == ids2
