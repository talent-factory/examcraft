# Auto-Composition Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add constraint-based auto-composition to the Exam Composer that selects questions to match Bloom/difficulty distribution targets within a point/duration budget, with preview support.

**Architecture:** New `auto_compose_service.py` encapsulates the greedy optimization algorithm. The existing `auto-fill` endpoint in `exams.py` gains composition mode (detected by `target_points`/`target_duration_minutes` fields) and a `preview` flag. Frontend extends the auto-fill dialog with a composition mode toggle and preview step.

**Tech Stack:** Python/FastAPI/Pydantic (backend), React 18/TypeScript/MUI/Tailwind (frontend), pytest (tests)

**Spec:** `docs/superpowers/specs/2026-03-22-auto-composition-engine-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `packages/core/backend/services/point_utils.py` | Create | Extracted `suggest_points()` and `POINT_SUGGESTIONS` (shared by API + service) |
| `packages/core/backend/services/auto_compose_service.py` | Create | Greedy composition algorithm, scoring, constraint report generation |
| `packages/core/backend/tests/test_auto_compose_service.py` | Create | Unit tests for composition algorithm |
| `packages/core/backend/api/exams.py` | Modify | Enhanced schemas, composition mode routing in auto-fill endpoint, import from point_utils |
| `packages/core/backend/tests/test_exam_api.py` | Modify | Integration tests for preview + composition mode |
| `packages/core/frontend/src/types/composer.ts` | Modify | New TypeScript types for preview/report |
| `packages/core/frontend/src/services/ComposerService.ts` | Modify | Updated autoFill with preview support |
| `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx` | Modify | Composition mode UI + preview step |

---

### Task 0: Extract suggest_points to Shared Utility

**Files:**
- Create: `packages/core/backend/services/point_utils.py`
- Modify: `packages/core/backend/api/exams.py`

This avoids a circular import: `auto_compose_service.py` needs `suggest_points()`, but it lives in `api/exams.py` which will import from the service. Extract to a shared utility first.

- [ ] **Step 1: Create point_utils.py**

Create `packages/core/backend/services/point_utils.py`:

```python
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
```

- [ ] **Step 2: Update exams.py to import from point_utils**

In `packages/core/backend/api/exams.py`, replace the `POINT_SUGGESTIONS` dict and `suggest_points` function (lines 39-54) with:

```python
from services.point_utils import POINT_SUGGESTIONS, suggest_points
```

- [ ] **Step 3: Run existing tests to verify no breakage**

Run: `cd packages/core/backend && python -m pytest tests/test_exam_api.py -x -q`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/services/point_utils.py packages/core/backend/api/exams.py
git commit -m "refactor: extract suggest_points to shared utility (TF-299)"
```

---

### Task 1: Auto-Compose Service - Core Algorithm

**Files:**
- Create: `packages/core/backend/services/auto_compose_service.py`
- Create: `packages/core/backend/tests/test_auto_compose_service.py`

- [ ] **Step 1: Write failing test for basic point-budget composition**

In `packages/core/backend/tests/test_auto_compose_service.py`:

```python
"""Unit tests for the auto-composition engine."""

import pytest
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
            _candidate(1, "open_ended", "medium"),   # 6 pts
            _candidate(2, "open_ended", "easy"),      # 3 pts
            _candidate(3, "open_ended", "hard"),      # 10 pts
            _candidate(4, "multiple_choice", "easy"), # 2 pts
        ]
        constraints = CompositionConstraints(target_points=12.0)
        result = compose_questions(candidates, constraints)

        assert result.total_points <= 12.0
        assert result.total_points > 0
        assert len(result.questions) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/core/backend && python -m pytest tests/test_auto_compose_service.py::TestComposeQuestions::test_basic_point_budget -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write the auto_compose_service module**

Create `packages/core/backend/services/auto_compose_service.py`:

```python
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
    bloom_distribution: dict[int, float] | None = None       # {1: 20, 2: 30, ...}
    difficulty_distribution: dict[str, float] | None = None   # {"easy": 30, ...}


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
        selected.append(SelectedQuestion(
            id=best_candidate.id,
            question_text=best_candidate.question_text,
            question_type=best_candidate.question_type,
            difficulty=best_candidate.difficulty,
            topic=best_candidate.topic,
            bloom_level=best_candidate.bloom_level,
            estimated_time_minutes=best_candidate.estimated_time_minutes,
            suggested_points=pts,
        ))
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
        total_dur = sum(q.estimated_time_minutes or 0 for q in selected) + candidate_duration
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
        bloom_counts[candidate.bloom_level] = bloom_counts.get(candidate.bloom_level, 0) + 1

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
        pts_dev = abs(total_points - constraints.target_points) / constraints.target_points * 100
        satisfaction_scores.append(max(0, 100 - pts_dev))
    if constraints.target_duration_minutes is not None and constraints.target_duration_minutes > 0:
        dur_dev = abs(total_duration - constraints.target_duration_minutes) / constraints.target_duration_minutes * 100
        satisfaction_scores.append(max(0, 100 - dur_dev))

    overall = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 100.0

    return ConstraintReport(
        points_target=constraints.target_points,
        points_achieved=total_points,
        duration_target=constraints.target_duration_minutes,
        duration_achieved=total_duration,
        bloom_distribution=bloom_report,
        difficulty_distribution=diff_report,
        overall_satisfaction=round(overall, 1),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/core/backend && python -m pytest tests/test_auto_compose_service.py::TestComposeQuestions::test_basic_point_budget -v`
Expected: PASS

- [ ] **Step 5: Add remaining unit tests**

Add these tests to `test_auto_compose_service.py`:

```python
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
            _candidate(1, "open_ended", "hard", estimated_time_minutes=20),  # 10 pts, 20 min
            _candidate(2, "open_ended", "easy", estimated_time_minutes=3),   # 3 pts, 3 min
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
            _candidate(1, "open_ended", "hard"),    # 10 pts
            _candidate(2, "multiple_choice", "easy"), # 2 pts
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
```

- [ ] **Step 6: Run all unit tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auto_compose_service.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add packages/core/backend/services/auto_compose_service.py packages/core/backend/tests/test_auto_compose_service.py
git commit -m "feat(backend): add auto-composition engine with greedy algorithm (TF-299)"
```

---

### Task 2: Enhanced API Schemas and Endpoint

**Files:**
- Modify: `packages/core/backend/api/exams.py` (lines 675-754 for auto-fill, lines 57-98 for schemas)

- [ ] **Step 1: Add new Pydantic schemas to exams.py**

After the existing `AutoFillRequest` class (line 681), add the new schemas. Also modify `AutoFillRequest` to support composition mode:

Replace the existing `AutoFillRequest` (lines 675-681) with:

```python
class AutoFillRequest(BaseModel):
    # Existing fields (simple mode)
    count: Optional[int] = Field(None, ge=1, le=20)
    topic: Optional[str] = None
    difficulty: Optional[List[str]] = None
    bloom_level_min: Optional[int] = Field(None, ge=1, le=6)
    question_types: Optional[List[str]] = None
    exclude_question_ids: Optional[List[int]] = None

    # New constraint fields (composition mode)
    target_points: Optional[float] = Field(None, gt=0)
    target_duration_minutes: Optional[int] = Field(None, gt=0)
    bloom_distribution: Optional[dict[int, float]] = None
    difficulty_distribution: Optional[dict[str, float]] = None
    preview: bool = False

    @property
    def is_composition_mode(self) -> bool:
        return self.target_points is not None or self.target_duration_minutes is not None


class DistributionResultOut(BaseModel):
    target_pct: float
    achieved_pct: float
    within_tolerance: bool


class ConstraintReportOut(BaseModel):
    points_target: Optional[float]
    points_achieved: float
    duration_target: Optional[int]
    duration_achieved: int
    bloom_distribution: dict[int, DistributionResultOut]
    difficulty_distribution: dict[str, DistributionResultOut]
    overall_satisfaction: float


class ProposedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    estimated_time_minutes: Optional[int]
    suggested_points: float


class AutoComposePreview(BaseModel):
    questions: List[ProposedQuestionOut]
    total_points: float
    total_duration_minutes: int
    constraint_report: ConstraintReportOut
```

- [ ] **Step 2: Modify the auto-fill endpoint to support composition mode**

Replace the `auto_fill_questions` function (lines 684-754) with the enhanced version. The key changes:
- Detect composition mode via `request.is_composition_mode`
- In composition mode: filter candidates, exclude NULL metadata, call `compose_questions()`, handle preview/apply
- In simple mode: preserve existing behavior with `count` defaulting to 5
- Add validation for distribution sums

```python
@router.post("/{exam_id}/auto-fill")
async def auto_fill_questions(
    exam_id: int,
    request: AutoFillRequest,
    current_user: User = Depends(require_permission("exams:create")),
    db: Session = Depends(get_db),
):
    """Auto-fill exam with questions matching criteria.

    Simple mode: random selection by count (legacy behavior).
    Composition mode: constraint-based greedy optimization with optional preview.
    """
    exam = _get_exam_or_404(exam_id, db, current_user)
    _require_draft(exam)

    if request.is_composition_mode:
        return _auto_compose(exam, request, current_user, db)
    else:
        return _auto_fill_simple(exam, request, current_user, db)


def _validate_distribution(dist: dict, name: str, valid_keys: set | None = None):
    """Validate that distribution values sum to ~100."""
    total = sum(dist.values())
    if abs(total - 100) > 1.0:
        raise HTTPException(
            status_code=422,
            detail=f"{name} must sum to 100 (got {total})",
        )
    if valid_keys:
        invalid = set(dist.keys()) - valid_keys
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {name} keys: {invalid}",
            )


def _auto_compose(exam: Exam, request: AutoFillRequest, current_user: User, db: Session):
    """Composition mode: constraint-based greedy optimization."""
    from services.auto_compose_service import (
        compose_questions,
        QuestionCandidate,
        CompositionConstraints,
    )

    # Validate distributions
    if request.bloom_distribution:
        _validate_distribution(
            request.bloom_distribution, "bloom_distribution",
            valid_keys={1, 2, 3, 4, 5, 6},
        )
    if request.difficulty_distribution:
        _validate_distribution(
            request.difficulty_distribution, "difficulty_distribution",
            valid_keys={"easy", "medium", "hard"},
        )

    # Query candidates
    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    # Exclude already-added and user-excluded questions
    existing_qids = {eq.question_id for eq in exam.questions}
    exclude_ids = existing_qids | set(request.exclude_question_ids or [])
    if exclude_ids:
        query = query.filter(QuestionReview.id.notin_(exclude_ids))

    # Apply filters
    if request.topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{request.topic}%"))
    if request.difficulty:
        query = query.filter(QuestionReview.difficulty.in_(request.difficulty))
    if request.bloom_level_min:
        query = query.filter(QuestionReview.bloom_level >= request.bloom_level_min)
    if request.question_types:
        query = query.filter(QuestionReview.question_type.in_(request.question_types))

    # Exclude NULL metadata when corresponding constraints are active
    if request.bloom_distribution:
        query = query.filter(QuestionReview.bloom_level.isnot(None))
    if request.target_duration_minutes:
        query = query.filter(QuestionReview.estimated_time_minutes.isnot(None))

    all_candidates = query.all()
    if not all_candidates:
        raise HTTPException(status_code=404, detail="No matching questions found")

    candidates = [
        QuestionCandidate(
            id=q.id,
            question_text=q.question_text,
            question_type=q.question_type,
            difficulty=q.difficulty,
            topic=q.topic,
            bloom_level=q.bloom_level,
            estimated_time_minutes=q.estimated_time_minutes,
        )
        for q in all_candidates
    ]

    constraints = CompositionConstraints(
        target_points=request.target_points,
        target_duration_minutes=request.target_duration_minutes,
        bloom_distribution=request.bloom_distribution,
        difficulty_distribution=request.difficulty_distribution,
    )

    result = compose_questions(candidates, constraints)

    if not result.questions:
        raise HTTPException(
            status_code=404,
            detail="No questions fit within the specified constraints",
        )

    # Preview mode: return proposal without modifying exam
    if request.preview:
        return AutoComposePreview(
            questions=[
                ProposedQuestionOut(
                    id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    topic=q.topic,
                    bloom_level=q.bloom_level,
                    estimated_time_minutes=q.estimated_time_minutes,
                    suggested_points=q.suggested_points,
                )
                for q in result.questions
            ],
            total_points=result.total_points,
            total_duration_minutes=result.total_duration_minutes,
            constraint_report=ConstraintReportOut(
                points_target=result.constraint_report.points_target,
                points_achieved=result.constraint_report.points_achieved,
                duration_target=result.constraint_report.duration_target,
                duration_achieved=result.constraint_report.duration_achieved,
                bloom_distribution={
                    k: DistributionResultOut(
                        target_pct=v.target_pct,
                        achieved_pct=v.achieved_pct,
                        within_tolerance=v.within_tolerance,
                    )
                    for k, v in result.constraint_report.bloom_distribution.items()
                },
                difficulty_distribution={
                    k: DistributionResultOut(
                        target_pct=v.target_pct,
                        achieved_pct=v.achieved_pct,
                        within_tolerance=v.within_tolerance,
                    )
                    for k, v in result.constraint_report.difficulty_distribution.items()
                },
                overall_satisfaction=result.constraint_report.overall_satisfaction,
            ),
        )

    # Apply mode: add questions to exam
    max_pos = max((eq.position for eq in exam.questions), default=0)
    for q in result.questions:
        max_pos += 1
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=max_pos,
            points=q.suggested_points,
        )
        db.add(eq)

    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in auto_compose for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=409, detail="Conflict. Please reload and try again.")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in auto_compose for exam %s: %s", exam_id, exc)
        raise HTTPException(status_code=500, detail="Database error. Please try again.")

    return _exam_detail_to_out(exam)


def _auto_fill_simple(exam: Exam, request: AutoFillRequest, current_user: User, db: Session):
    """Simple mode: random selection by count (legacy behavior)."""
    count = request.count or 5

    tenant_context = get_tenant_context(current_user)
    query = db.query(QuestionReview).filter(
        QuestionReview.review_status == ReviewStatus.APPROVED.value
    )
    query = TenantFilter.filter_by_tenant(query, QuestionReview, tenant_context)

    existing_qids = {eq.question_id for eq in exam.questions}
    exclude_ids = existing_qids | set(request.exclude_question_ids or [])
    if exclude_ids:
        query = query.filter(QuestionReview.id.notin_(exclude_ids))

    if request.topic:
        query = query.filter(QuestionReview.topic.ilike(f"%{request.topic}%"))
    if request.difficulty:
        query = query.filter(QuestionReview.difficulty.in_(request.difficulty))
    if request.bloom_level_min:
        query = query.filter(QuestionReview.bloom_level >= request.bloom_level_min)
    if request.question_types:
        query = query.filter(QuestionReview.question_type.in_(request.question_types))

    candidates = query.order_by(sa_func.random()).limit(count).all()
    if not candidates:
        raise HTTPException(status_code=404, detail="No matching questions found")

    max_pos = max((eq.position for eq in exam.questions), default=0)
    for q in candidates:
        max_pos += 1
        eq = ExamQuestion(
            exam_id=exam.id,
            question_id=q.id,
            position=max_pos,
            points=suggest_points(q.question_type, q.difficulty),
        )
        db.add(eq)

    try:
        db.flush()
        db.refresh(exam)
        exam.recalculate_total_points()
        db.commit()
        db.refresh(exam)
    except IntegrityError as exc:
        db.rollback()
        logger.error("IntegrityError in auto_fill for exam %s: %s", exam.id, exc)
        raise HTTPException(status_code=409, detail="Conflict. Please reload and try again.")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database error in auto_fill for exam %s: %s", exam.id, exc)
        raise HTTPException(status_code=500, detail="Database error. Please try again.")

    return _exam_detail_to_out(exam)
```

- [ ] **Step 3: Run existing auto-fill tests to confirm backward compatibility**

Run: `cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestAutoFillQuestions -v`
Expected: All existing tests PASS

- [ ] **Step 4: Add integration tests for composition mode**

Append to `test_exam_api.py` a new test class:

```python
class TestAutoComposeQuestions(
    _make_exam_test_class_fixtures("compose-uni", "compose@test.com")
):
    """Tests for POST /{exam_id}/auto-fill in composition mode."""

    def _seed_diverse_questions(self, exam_db, institution_id, user_id):
        """Create a diverse set of questions with metadata."""
        questions = []
        configs = [
            ("multiple_choice", "easy", 1, 1),
            ("multiple_choice", "medium", 2, 2),
            ("multiple_choice", "hard", 3, 3),
            ("open_ended", "easy", 1, 3),
            ("open_ended", "medium", 2, 5),
            ("open_ended", "hard", 3, 8),
            ("true_false", "easy", 1, 1),
            ("true_false", "medium", 2, 1),
            ("true_false", "hard", 3, 2),
        ]
        for i, (qtype, diff, bloom, time) in enumerate(configs):
            q = QuestionReview(
                question_text=f"Compose question {i}",
                question_type=qtype,
                difficulty=diff,
                topic="Compose Topic",
                bloom_level=bloom,
                estimated_time_minutes=time,
                language="de",
                review_status=ReviewStatus.APPROVED.value,
                institution_id=institution_id,
                created_by=user_id,
            )
            exam_db.add(q)
            questions.append(q)
        exam_db.flush()
        return questions

    def test_preview_returns_proposal_without_modifying(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Preview Test"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"target_points": 20.0, "preview": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "constraint_report" in data
        assert data["total_points"] <= 20.0

        # Exam should be unchanged
        exam_resp = exam_client.get(f"/api/v1/exams/{exam_id}")
        assert len(exam_resp.json()["questions"]) == 0

    def test_composition_adds_questions(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Compose Apply"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"target_points": 20.0, "preview": False},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) > 0
        assert data["total_points"] > 0

    def test_backward_compat_simple_mode(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Simple Compat"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={"count": 3},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["questions"]) <= 3

    def test_distribution_validation_rejects_bad_sum(self, exam_client):
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Bad Sum"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 50.0,
                "bloom_distribution": {"1": 50, "2": 20},
            },
        )
        assert response.status_code == 422

    def test_null_bloom_excluded_when_distribution_active(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        """Questions with NULL bloom_level excluded when bloom_distribution is set."""
        # Create questions: some with bloom, one without
        for i, bloom in enumerate([1, 2, None]):
            q = QuestionReview(
                question_text=f"Null test q{i}",
                question_type="open_ended",
                difficulty="medium",
                topic="NullTest",
                bloom_level=bloom,
                estimated_time_minutes=5,
                language="de",
                review_status=ReviewStatus.APPROVED.value,
                institution_id=exam_institution.id,
                created_by=exam_user.id,
            )
            exam_db.add(q)
        exam_db.flush()

        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Null Bloom"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 50.0,
                "bloom_distribution": {"1": 50, "2": 50},
                "preview": True,
            },
        )
        assert response.status_code == 200
        data = response.json()
        # NULL-bloom question should not appear in results
        for q in data["questions"]:
            assert q["bloom_level"] is not None

    def test_constraint_report_in_preview(
        self, exam_client, exam_db, exam_institution, exam_user
    ):
        self._seed_diverse_questions(exam_db, exam_institution.id, exam_user.id)
        create_resp = exam_client.post("/api/v1/exams/", json={"title": "Report Test"})
        exam_id = create_resp.json()["id"]

        response = exam_client.post(
            f"/api/v1/exams/{exam_id}/auto-fill",
            json={
                "target_points": 30.0,
                "bloom_distribution": {"1": 33, "2": 34, "3": 33},
                "preview": True,
            },
        )
        assert response.status_code == 200
        report = response.json()["constraint_report"]
        assert "points_target" in report
        assert "bloom_distribution" in report
        assert "overall_satisfaction" in report
        assert report["points_achieved"] <= 30.0
```

- [ ] **Step 5: Run all auto-fill and auto-compose tests**

Run: `cd packages/core/backend && python -m pytest tests/test_exam_api.py::TestAutoFillQuestions tests/test_exam_api.py::TestAutoComposeQuestions -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/exams.py packages/core/backend/tests/test_exam_api.py
git commit -m "feat(api): enhance auto-fill with composition mode and preview (TF-299)"
```

---

### Task 3: Frontend Types and Service Layer

**Files:**
- Modify: `packages/core/frontend/src/types/composer.ts`
- Modify: `packages/core/frontend/src/services/ComposerService.ts`

- [ ] **Step 1: Add new TypeScript types to composer.ts**

Append to `packages/core/frontend/src/types/composer.ts`:

```typescript
export interface DistributionResult {
  target_pct: number;
  achieved_pct: number;
  within_tolerance: boolean;
}

export interface ConstraintReport {
  points_target: number | null;
  points_achieved: number;
  duration_target: number | null;
  duration_achieved: number;
  bloom_distribution: Record<number, DistributionResult>;
  difficulty_distribution: Record<string, DistributionResult>;
  overall_satisfaction: number;
}

export interface ProposedQuestion {
  id: number;
  question_text: string;
  question_type: string;
  difficulty: string;
  topic: string;
  bloom_level: number | null;
  estimated_time_minutes: number | null;
  suggested_points: number;
}

export interface AutoComposePreview {
  questions: ProposedQuestion[];
  total_points: number;
  total_duration_minutes: number;
  constraint_report: ConstraintReport;
}
```

Also update the existing `AutoFillRequest` interface:

```typescript
export interface AutoFillRequest {
  count?: number;
  topic?: string;
  difficulty?: string[];
  bloom_level_min?: number;
  question_types?: string[];
  exclude_question_ids?: number[];
  // Composition mode fields
  target_points?: number;
  target_duration_minutes?: number;
  bloom_distribution?: Record<number, number>;
  difficulty_distribution?: Record<string, number>;
  preview?: boolean;
}
```

- [ ] **Step 2: Update ComposerService.ts**

Modify the `autoFill` method and add imports:

In the import block, add `AutoComposePreview` to the type imports:
```typescript
import type {
  Exam,
  ExamDetail,
  ExamListResponse,
  CreateExamRequest,
  UpdateExamRequest,
  ApprovedQuestionsResponse,
  AutoFillRequest,
  AutoComposePreview,
} from '../types/composer';
```

Replace the `autoFill` method:
```typescript
  static async autoFill(
    examId: number,
    request: AutoFillRequest
  ): Promise<ExamDetail | AutoComposePreview> {
    const response = await apiClient.post(`/api/v1/exams/${examId}/auto-fill`, request);
    return response.data;
  }
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/types/composer.ts packages/core/frontend/src/services/ComposerService.ts
git commit -m "feat(frontend): add auto-composition TypeScript types and service (TF-299)"
```

---

### Task 4: Frontend Composition Mode UI

**Files:**
- Modify: `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx`

- [ ] **Step 1: Add composition mode state and form types**

At the top of `QuestionPoolPanel.tsx`, add the composition form interface and preset data:

```typescript
import type { ApprovedQuestion, AutoFillRequest, AutoComposePreview, ProposedQuestion } from '../../types/composer';

interface CompositionForm {
  target_points: string;
  target_duration_minutes: string;
  bloom_distribution: Record<number, string>;
  difficulty_distribution: Record<string, string>;
  topic: string;
  question_types: string[];
}

const BLOOM_LABELS: Record<number, string> = {
  1: 'Erinnern',
  2: 'Verstehen',
  3: 'Anwenden',
  4: 'Analysieren',
  5: 'Bewerten',
  6: 'Erschaffen',
};

const PRESETS: Record<string, {
  bloom: Record<number, number>;
  difficulty: Record<string, number>;
  label: string;
}> = {
  balanced: {
    label: 'Ausgewogen',
    bloom: { 1: 15, 2: 25, 3: 25, 4: 20, 5: 10, 6: 5 },
    difficulty: { easy: 30, medium: 40, hard: 30 },
  },
  application: {
    label: 'Anwendungsfokus',
    bloom: { 1: 10, 2: 15, 3: 35, 4: 25, 5: 10, 6: 5 },
    difficulty: { easy: 20, medium: 40, hard: 40 },
  },
};
```

- [ ] **Step 2: Add state variables for composition mode**

Inside the `QuestionPoolPanel` component, add new state:

```typescript
  const [compositionMode, setCompositionMode] = useState(false);
  const [compositionForm, setCompositionForm] = useState<CompositionForm>({
    target_points: '',
    target_duration_minutes: '',
    bloom_distribution: { 1: '', 2: '', 3: '', 4: '', 5: '', 6: '' },
    difficulty_distribution: { easy: '', medium: '', hard: '' },
    topic: '',
    question_types: [],
  });
  const [preview, setPreview] = useState<AutoComposePreview | null>(null);
  const [lastPreviewRequest, setLastPreviewRequest] = useState<AutoFillRequest | null>(null);
```

- [ ] **Step 3: Add composition mutation and handlers**

```typescript
  const composeMutation = useMutation({
    mutationFn: (req: AutoFillRequest) => ComposerService.autoFill(examId, req),
    onSuccess: (data) => {
      if ('constraint_report' in data) {
        setPreview(data as AutoComposePreview);
        setAutoFillError(null);
      } else {
        setPreview(null);
        setAutoFillOpen(false);
        setAutoFillError(null);
        onInvalidate();
      }
    },
    onError: (err) => {
      setAutoFillError(getErrorMessage(err, 'Komposition fehlgeschlagen.'));
    },
  });

  const handleCompose = () => {
    const bloomDist: Record<number, number> = {};
    let hasBloom = false;
    for (const [k, v] of Object.entries(compositionForm.bloom_distribution)) {
      const num = parseFloat(v);
      if (num > 0) {
        bloomDist[parseInt(k)] = num;
        hasBloom = true;
      }
    }

    const diffDist: Record<string, number> = {};
    let hasDiff = false;
    for (const [k, v] of Object.entries(compositionForm.difficulty_distribution)) {
      const num = parseFloat(v);
      if (num > 0) {
        diffDist[k] = num;
        hasDiff = true;
      }
    }

    const req: AutoFillRequest = {
      target_points: parseFloat(compositionForm.target_points) || undefined,
      target_duration_minutes: parseInt(compositionForm.target_duration_minutes) || undefined,
      bloom_distribution: hasBloom ? bloomDist : undefined,
      difficulty_distribution: hasDiff ? diffDist : undefined,
      topic: compositionForm.topic || undefined,
      question_types: compositionForm.question_types.length > 0 ? compositionForm.question_types : undefined,
      exclude_question_ids: Array.from(addedQuestionIds),
      preview: true,
    };
    setLastPreviewRequest(req);
    composeMutation.mutate(req);
  };

  const handleAcceptPreview = () => {
    if (!lastPreviewRequest) return;
    // Replay exact same request with preview=false
    composeMutation.mutate({ ...lastPreviewRequest, preview: false });
  };

  const applyPreset = (presetKey: string) => {
    const preset = PRESETS[presetKey];
    if (!preset) return;
    const bloomDist: Record<number, string> = { 1: '', 2: '', 3: '', 4: '', 5: '', 6: '' };
    for (const [k, v] of Object.entries(preset.bloom)) {
      bloomDist[parseInt(k)] = v.toString();
    }
    const diffDist: Record<string, string> = { easy: '', medium: '', hard: '' };
    for (const [k, v] of Object.entries(preset.difficulty)) {
      diffDist[k] = v.toString();
    }
    setCompositionForm((f) => ({ ...f, bloom_distribution: bloomDist, difficulty_distribution: diffDist }));
  };
```

- [ ] **Step 4: Update the dialog JSX**

Replace the Dialog (lines 209-292) with the enhanced version. The dialog has three views controlled by `compositionMode` and `preview` state:

```tsx
      <Dialog
        open={autoFillOpen}
        onClose={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <div className="flex gap-2">
            <button
              onClick={() => { setCompositionMode(false); setPreview(null); }}
              className={`px-3 py-1 rounded-lg text-sm ${!compositionMode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              Einfach
            </button>
            <button
              onClick={() => { setCompositionMode(true); setPreview(null); }}
              className={`px-3 py-1 rounded-lg text-sm ${compositionMode ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600'}`}
            >
              Komposition
            </button>
          </div>
        </DialogTitle>
        <DialogContent>
          {!compositionMode ? (
            /* --- Simple mode (existing) --- */
            <div className="space-y-4 mt-2">
              <TextField label="Anzahl Fragen" type="number" fullWidth
                inputProps={{ min: 1, max: 20 }} value={autoFillForm.count}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, count: e.target.value })} />
              <TextField label="Thema (optional)" fullWidth value={autoFillForm.topic}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, topic: e.target.value })} />
              <div>
                <p className="text-sm text-gray-600 mb-1">Schwierigkeitsgrad</p>
                <div className="flex gap-2">
                  {(['easy', 'medium', 'hard'] as const).map((d) => (
                    <button key={d} type="button" onClick={() => toggleAutoFillDifficulty(d)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        autoFillForm.difficulty.includes(d) ? DIFFICULTY_COLORS[d] + ' border-current font-semibold' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{DIFFICULTY_LABELS[d]}</button>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-1">Fragetypen</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((t) => (
                    <button key={t} type="button" onClick={() => toggleAutoFillType(t)}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        autoFillForm.question_types.includes(t) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[t]}</button>
                  ))}
                </div>
              </div>
              <TextField label="Min. Bloom-Level (1-6, optional)" type="number" fullWidth
                inputProps={{ min: 1, max: 6 }} value={autoFillForm.bloom_level_min}
                onChange={(e) => setAutoFillForm({ ...autoFillForm, bloom_level_min: e.target.value })} />
            </div>
          ) : preview ? (
            /* --- Preview panel --- */
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-3 gap-2 text-center text-sm">
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Punkte</div>
                  <div className="font-semibold">{preview.total_points} / {preview.constraint_report.points_target ?? '–'}</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Dauer</div>
                  <div className="font-semibold">{preview.total_duration_minutes} / {preview.constraint_report.duration_target ?? '–'} min</div>
                </div>
                <div className="p-2 bg-gray-50 rounded">
                  <div className="text-gray-500">Zufriedenheit</div>
                  <div className={`font-semibold ${preview.constraint_report.overall_satisfaction >= 80 ? 'text-green-600' : 'text-yellow-600'}`}>
                    {preview.constraint_report.overall_satisfaction}%
                  </div>
                </div>
              </div>
              {/* Distribution reports */}
              {Object.keys(preview.constraint_report.bloom_distribution).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Bloom-Verteilung</p>
                  <div className="space-y-1">
                    {Object.entries(preview.constraint_report.bloom_distribution).map(([level, dr]) => (
                      <div key={level} className="flex items-center gap-2 text-xs">
                        <span className="w-24 text-gray-600">B{level} {BLOOM_LABELS[parseInt(level)] || ''}</span>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${dr.within_tolerance ? 'bg-green-500' : 'bg-yellow-500'}`}
                            style={{ width: `${Math.min(dr.achieved_pct, 100)}%` }} />
                        </div>
                        <span className="w-20 text-right">{dr.achieved_pct}% / {dr.target_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {Object.keys(preview.constraint_report.difficulty_distribution).length > 0 && (
                <div>
                  <p className="text-sm font-medium text-gray-700 mb-1">Schwierigkeitsverteilung</p>
                  <div className="space-y-1">
                    {Object.entries(preview.constraint_report.difficulty_distribution).map(([diff, dr]) => (
                      <div key={diff} className="flex items-center gap-2 text-xs">
                        <span className="w-24 text-gray-600">{DIFFICULTY_LABELS[diff] || diff}</span>
                        <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full ${dr.within_tolerance ? 'bg-green-500' : 'bg-yellow-500'}`}
                            style={{ width: `${Math.min(dr.achieved_pct, 100)}%` }} />
                        </div>
                        <span className="w-20 text-right">{dr.achieved_pct}% / {dr.target_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* Proposed questions */}
              <div>
                <p className="text-sm font-medium text-gray-700 mb-1">{preview.questions.length} Fragen vorgeschlagen</p>
                <div className="max-h-48 overflow-y-auto space-y-1">
                  {preview.questions.map((q) => (
                    <div key={q.id} className="p-2 bg-gray-50 rounded text-xs flex items-center justify-between">
                      <span className="line-clamp-1 flex-1 mr-2">{q.question_text}</span>
                      <div className="flex gap-1 flex-shrink-0">
                        <span className={`px-1.5 py-0.5 rounded-full ${DIFFICULTY_COLORS[q.difficulty] || 'bg-gray-100'}`}>
                          {DIFFICULTY_LABELS[q.difficulty] || q.difficulty}
                        </span>
                        {q.bloom_level && <span className="px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">B{q.bloom_level}</span>}
                        <span className="px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">{q.suggested_points}P</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            /* --- Composition form --- */
            <div className="space-y-4 mt-2">
              <div className="grid grid-cols-2 gap-3">
                <TextField label="Zielpunkte" type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_points}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_points: e.target.value })} />
                <TextField label="Zieldauer (Min.)" type="number" fullWidth
                  inputProps={{ min: 1 }} value={compositionForm.target_duration_minutes}
                  onChange={(e) => setCompositionForm({ ...compositionForm, target_duration_minutes: e.target.value })} />
              </div>
              <TextField label="Thema (optional)" fullWidth value={compositionForm.topic}
                onChange={(e) => setCompositionForm({ ...compositionForm, topic: e.target.value })} />
              {/* Presets */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Vorlagen</p>
                <div className="flex gap-2">
                  {Object.entries(PRESETS).map(([key, preset]) => (
                    <button key={key} type="button" onClick={() => applyPreset(key)}
                      className="text-xs px-3 py-1 rounded-full border border-indigo-300 text-indigo-700 hover:bg-indigo-50">
                      {preset.label}
                    </button>
                  ))}
                </div>
              </div>
              {/* Bloom distribution */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Bloom-Verteilung (%)</p>
                <div className="grid grid-cols-3 gap-2">
                  {([1, 2, 3, 4, 5, 6] as const).map((level) => (
                    <TextField key={level} label={`B${level} ${BLOOM_LABELS[level]}`} type="number"
                      size="small" inputProps={{ min: 0, max: 100 }}
                      value={compositionForm.bloom_distribution[level]}
                      onChange={(e) => setCompositionForm((f) => ({
                        ...f, bloom_distribution: { ...f.bloom_distribution, [level]: e.target.value },
                      }))} />
                  ))}
                </div>
              </div>
              {/* Difficulty distribution */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Schwierigkeitsverteilung (%)</p>
                <div className="grid grid-cols-3 gap-2">
                  {(['easy', 'medium', 'hard'] as const).map((d) => (
                    <TextField key={d} label={DIFFICULTY_LABELS[d]} type="number"
                      size="small" inputProps={{ min: 0, max: 100 }}
                      value={compositionForm.difficulty_distribution[d]}
                      onChange={(e) => setCompositionForm((f) => ({
                        ...f, difficulty_distribution: { ...f.difficulty_distribution, [d]: e.target.value },
                      }))} />
                  ))}
                </div>
              </div>
              {/* Question type filter */}
              <div>
                <p className="text-sm text-gray-600 mb-1">Fragetypen</p>
                <div className="flex gap-2 flex-wrap">
                  {(['multiple_choice', 'true_false', 'open_ended'] as const).map((t) => (
                    <button key={t} type="button"
                      onClick={() => setCompositionForm((f) => ({
                        ...f, question_types: f.question_types.includes(t)
                          ? f.question_types.filter((x) => x !== t)
                          : [...f.question_types, t],
                      }))}
                      className={`text-xs px-2 py-1 rounded-full border transition-colors ${
                        compositionForm.question_types.includes(t) ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-600 border-gray-300'
                      }`}>{TYPE_ABBREV[t]}</button>
                  ))}
                </div>
              </div>
            </div>
          )}
          {autoFillError && <p className="text-red-500 text-sm mt-2">{autoFillError}</p>}
        </DialogContent>
        <DialogActions>
          {compositionMode && preview ? (
            <>
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}>Abbrechen</Button>
              <Button onClick={() => setPreview(null)}>Zurueck</Button>
              <Button onClick={handleAcceptPreview} variant="contained"
                disabled={composeMutation.isPending}>
                {composeMutation.isPending ? 'Fuege hinzu...' : 'Uebernehmen'}
              </Button>
            </>
          ) : (
            <>
              <Button onClick={() => { setAutoFillOpen(false); setAutoFillError(null); setPreview(null); }}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                Abbrechen
              </Button>
              <Button variant="contained"
                onClick={compositionMode ? handleCompose : handleAutoFill}
                disabled={compositionMode ? composeMutation.isPending : autoFillMutation.isPending}>
                {compositionMode
                  ? (composeMutation.isPending ? 'Generiere...' : 'Vorschau generieren')
                  : (autoFillMutation.isPending ? 'Fuelle...' : 'Auto-Fill starten')}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
```

- [ ] **Step 5: Verify the component renders without errors**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No TypeScript errors

- [ ] **Step 6: Commit**

```bash
git add packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx
git commit -m "feat(frontend): add composition mode UI with preview to QuestionPoolPanel (TF-299)"
```

---

### Task 5: End-to-End Verification and Cleanup

- [ ] **Step 1: Run all backend tests**

Run: `cd packages/core/backend && python -m pytest tests/test_auto_compose_service.py tests/test_exam_api.py -v`
Expected: All PASS

- [ ] **Step 2: Run frontend type check**

Run: `cd packages/core/frontend && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Run linting**

Run: `ruff check packages/core/backend/ && ruff format --check packages/core/backend/`
Expected: No errors

- [ ] **Step 4: Fix any lint issues**

Run: `ruff check packages/core/backend/ --fix && ruff format packages/core/backend/`

- [ ] **Step 5: Final commit if lint fixes needed**

```bash
git add -u
git commit -m "style: fix lint issues"
```
