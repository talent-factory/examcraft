"""
Auto-Composition Engine for ExamCraft.

Greedy constraint-based algorithm that selects questions to match
distribution targets within point/duration budgets.
"""

from dataclasses import dataclass
from services.point_utils import suggest_points


@dataclass
class QuestionCandidate:
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: int | None
    estimated_time_minutes: int | None


@dataclass
class SelectedQuestion:
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: int | None
    estimated_time_minutes: int | None
    suggested_points: float


@dataclass
class DistributionResult:
    target_pct: float
    achieved_pct: float
    within_tolerance: bool  # +/-5%


@dataclass
class ConstraintReport:
    points_target: float | None
    points_achieved: float
    duration_target: int | None
    duration_achieved: int
    bloom_distribution: dict[int, DistributionResult]
    difficulty_distribution: dict[str, DistributionResult]
    overall_satisfaction: float  # 0-100%


@dataclass
class CompositionResult:
    questions: list[SelectedQuestion]
    total_points: float
    total_duration_minutes: int
    constraint_report: ConstraintReport


@dataclass
class CompositionConstraints:
    target_points: float | None = None
    target_duration_minutes: int | None = None
    bloom_distribution: dict[int, float] | None = None  # {1: 20, 2: 30, ...}
    difficulty_distribution: dict[str, float] | None = None  # {"easy": 30, ...}


def compose_questions(
    candidates: list[QuestionCandidate],
    constraints: CompositionConstraints,
) -> CompositionResult:
    """Select questions from candidates to satisfy constraints using greedy optimization."""
    selected: list[SelectedQuestion] = []
    remaining = list(candidates)

    while remaining:
        # Check if budget is exhausted
        if _budget_exhausted(selected, constraints):
            break

        # Score each remaining candidate
        best_candidate = None
        best_score = -1.0
        best_idx = -1

        for i, candidate in enumerate(remaining):
            pts = suggest_points(candidate.question_type, candidate.difficulty)
            time = candidate.estimated_time_minutes or 0

            # Skip if adding would exceed either active budget
            if _would_exceed_budget(selected, pts, time, constraints):
                continue

            score = _score_candidate(candidate, pts, selected, constraints)
            if score > best_score:
                best_score = score
                best_candidate = candidate
                best_idx = i

        if best_candidate is None:
            break  # No valid candidate found

        pts = suggest_points(best_candidate.question_type, best_candidate.difficulty)
        selected.append(
            SelectedQuestion(
                id=best_candidate.id,
                question_text=best_candidate.question_text,
                question_type=best_candidate.question_type,
                difficulty=best_candidate.difficulty,
                topic=best_candidate.topic,
                bloom_level=best_candidate.bloom_level,
                estimated_time_minutes=best_candidate.estimated_time_minutes,
                suggested_points=pts,
            )
        )
        remaining.pop(best_idx)

    total_points = sum(q.suggested_points for q in selected)
    total_duration = sum(q.estimated_time_minutes or 0 for q in selected)
    report = _build_report(selected, constraints)

    return CompositionResult(
        questions=selected,
        total_points=total_points,
        total_duration_minutes=total_duration,
        constraint_report=report,
    )


def _budget_exhausted(
    selected: list[SelectedQuestion],
    constraints: CompositionConstraints,
) -> bool:
    if constraints.target_points is not None:
        total_pts = sum(q.suggested_points for q in selected)
        if total_pts >= constraints.target_points:
            return True
    if constraints.target_duration_minutes is not None:
        total_dur = sum(q.estimated_time_minutes or 0 for q in selected)
        if total_dur >= constraints.target_duration_minutes:
            return True
    return False


def _would_exceed_budget(
    selected: list[SelectedQuestion],
    candidate_points: float,
    candidate_duration: int,
    constraints: CompositionConstraints,
) -> bool:
    if constraints.target_points is not None:
        total_pts = sum(q.suggested_points for q in selected) + candidate_points
        if total_pts > constraints.target_points:
            return True
    if constraints.target_duration_minutes is not None:
        total_dur = (
            sum(q.estimated_time_minutes or 0 for q in selected) + candidate_duration
        )
        if total_dur > constraints.target_duration_minutes:
            return True
    return False


def _score_candidate(
    candidate: QuestionCandidate,
    candidate_points: float,
    selected: list[SelectedQuestion],
    constraints: CompositionConstraints,
) -> float:
    """Score a candidate based on how much it improves constraint satisfaction.

    Higher score = better fit. Returns value >= 0.
    """
    score = 1.0  # Base score so every candidate has some value

    total_count = len(selected) + 1  # hypothetical count after adding

    # Bloom distribution scoring
    if constraints.bloom_distribution and candidate.bloom_level is not None:
        bloom_counts: dict[int, int] = {}
        for q in selected:
            if q.bloom_level is not None:
                bloom_counts[q.bloom_level] = bloom_counts.get(q.bloom_level, 0) + 1
        bloom_counts[candidate.bloom_level] = (
            bloom_counts.get(candidate.bloom_level, 0) + 1
        )

        bloom_score = 0.0
        for level, target_pct in constraints.bloom_distribution.items():
            achieved_pct = (bloom_counts.get(level, 0) / total_count) * 100
            bloom_score += max(0, 1.0 - abs(achieved_pct - target_pct) / 100)
        score += bloom_score

    # Difficulty distribution scoring
    if constraints.difficulty_distribution:
        diff_counts: dict[str, int] = {}
        for q in selected:
            diff_counts[q.difficulty] = diff_counts.get(q.difficulty, 0) + 1
        diff_counts[candidate.difficulty] = diff_counts.get(candidate.difficulty, 0) + 1

        diff_score = 0.0
        for diff, target_pct in constraints.difficulty_distribution.items():
            achieved_pct = (diff_counts.get(diff, 0) / total_count) * 100
            diff_score += max(0, 1.0 - abs(achieved_pct - target_pct) / 100)
        score += diff_score

    return score


def _build_report(
    selected: list[SelectedQuestion],
    constraints: CompositionConstraints,
) -> ConstraintReport:
    """Build the constraint satisfaction report."""
    total_points = sum(q.suggested_points for q in selected)
    total_duration = sum(q.estimated_time_minutes or 0 for q in selected)
    total_count = len(selected) or 1  # avoid division by zero

    # Bloom distribution report
    bloom_report: dict[int, DistributionResult] = {}
    if constraints.bloom_distribution:
        bloom_counts: dict[int, int] = {}
        for q in selected:
            if q.bloom_level is not None:
                bloom_counts[q.bloom_level] = bloom_counts.get(q.bloom_level, 0) + 1
        for level, target_pct in constraints.bloom_distribution.items():
            achieved_pct = (bloom_counts.get(level, 0) / total_count) * 100
            bloom_report[level] = DistributionResult(
                target_pct=target_pct,
                achieved_pct=round(achieved_pct, 1),
                within_tolerance=abs(achieved_pct - target_pct) <= 5.0,
            )

    # Difficulty distribution report
    diff_report: dict[str, DistributionResult] = {}
    if constraints.difficulty_distribution:
        diff_counts: dict[str, int] = {}
        for q in selected:
            diff_counts[q.difficulty] = diff_counts.get(q.difficulty, 0) + 1
        for diff, target_pct in constraints.difficulty_distribution.items():
            achieved_pct = (diff_counts.get(diff, 0) / total_count) * 100
            diff_report[diff] = DistributionResult(
                target_pct=target_pct,
                achieved_pct=round(achieved_pct, 1),
                within_tolerance=abs(achieved_pct - target_pct) <= 5.0,
            )

    # Overall satisfaction: average of (100 - abs_deviation) for all constraints
    satisfaction_scores: list[float] = []
    for dr in bloom_report.values():
        satisfaction_scores.append(max(0, 100 - abs(dr.achieved_pct - dr.target_pct)))
    for dr in diff_report.values():
        satisfaction_scores.append(max(0, 100 - abs(dr.achieved_pct - dr.target_pct)))
    if constraints.target_points is not None and constraints.target_points > 0:
        pts_dev = (
            abs(total_points - constraints.target_points)
            / constraints.target_points
            * 100
        )
        satisfaction_scores.append(max(0, 100 - pts_dev))
    if (
        constraints.target_duration_minutes is not None
        and constraints.target_duration_minutes > 0
    ):
        dur_dev = (
            abs(total_duration - constraints.target_duration_minutes)
            / constraints.target_duration_minutes
            * 100
        )
        satisfaction_scores.append(max(0, 100 - dur_dev))

    overall = (
        sum(satisfaction_scores) / len(satisfaction_scores)
        if satisfaction_scores
        else 100.0
    )

    return ConstraintReport(
        points_target=constraints.target_points,
        points_achieved=total_points,
        duration_target=constraints.target_duration_minutes,
        duration_achieved=total_duration,
        bloom_distribution=bloom_report,
        difficulty_distribution=diff_report,
        overall_satisfaction=round(overall, 1),
    )
