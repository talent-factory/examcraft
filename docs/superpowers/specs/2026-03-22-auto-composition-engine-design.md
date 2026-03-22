# Auto-Composition Engine Design Specification

**Task:** TF-299
**Date:** 2026-03-22
**Status:** Approved

## Goal

Upgrade the existing auto-fill endpoint in the Exam Composer to a constraint-based composition engine that automatically selects questions matching configurable distribution targets for Bloom level, difficulty, total points, and duration.

## Context

The Exam Composer (TF-56) has a basic auto-fill (`POST /{exam_id}/auto-fill`) that randomly selects approved questions with simple filters (topic, difficulty, bloom_level_min, question_types). TF-300 (completed) enriched all questions with `bloom_level` (1-6) and `estimated_time_minutes` metadata, unblocking constraint-based composition.

## Design Decisions

- **Endpoint strategy:** Enhance existing auto-fill endpoint (backward-compatible) rather than creating a new endpoint. Mode is detected by presence of `target_points` or `target_duration_minutes` fields.
- **Budget-driven selection:** Algorithm determines question count from point/duration budgets rather than requiring a fixed count.
- **Best-effort with report:** When constraints can't be fully satisfied, the algorithm fills as close as possible and returns a constraint satisfaction report showing deviations.
- **Preview mode:** A `preview: bool` flag returns the proposed selection without adding questions to the exam, allowing users to review before accepting.
- **Deterministic algorithm:** Greedy scoring (no randomness) ensures reproducible results for the same input.

## API Contract

### Enhanced AutoFillRequest

All new fields are optional for backward compatibility. Existing simple auto-fill requests continue to work unchanged.

```python
class AutoFillRequest(BaseModel):
    # Existing fields (simple mode)
    count: int | None = None
    topic: str | None = None
    difficulty: list[str] | None = None
    bloom_level_min: int | None = None
    question_types: list[str] | None = None
    exclude_question_ids: list[int] | None = None

    # New constraint fields (composition mode)
    target_points: float | None = None
    target_duration_minutes: int | None = None
    bloom_distribution: dict[int, float] | None = None
    difficulty_distribution: dict[str, float] | None = None
    preview: bool = False
```

**Mode detection:** If `target_points` or `target_duration_minutes` is set, composition mode activates. Otherwise, legacy count-driven behavior applies.

**Validation:**
- `bloom_distribution` values must sum to 100 (keys: 1-6)
- `difficulty_distribution` values must sum to 100 (keys: "easy", "medium", "hard")
- At least one budget constraint (`target_points` or `target_duration_minutes`) required in composition mode

### Preview Response

```python
class AutoComposePreview(BaseModel):
    questions: list[ProposedQuestionOut]
    total_points: float
    total_duration_minutes: int
    constraint_report: ConstraintReport

class ProposedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: int | None
    estimated_time_minutes: int | None
    suggested_points: float

class ConstraintReport(BaseModel):
    points_target: float | None
    points_achieved: float
    duration_target: int | None
    duration_achieved: int
    bloom_distribution: dict[str, DistributionResult]
    difficulty_distribution: dict[str, DistributionResult]
    overall_satisfaction: float  # 0-100%

class DistributionResult(BaseModel):
    target_pct: float
    achieved_pct: float
    within_tolerance: bool  # +/-5%
```

When `preview=False` (default), the endpoint behaves as before: questions are added to the exam and the updated `ExamDetailOut` is returned. When `preview=True`, the `AutoComposePreview` response is returned instead.

## Composition Algorithm

Located in `services/auto_compose_service.py`.

### Steps

1. **Filter candidates** -- Query approved questions matching topic, question_types, and exclude filters. Apply institution-level multi-tenancy. Exclude questions already in the exam.

2. **Score each candidate** -- For each candidate question, calculate a composite score based on how much adding it would improve constraint satisfaction:
   - Bloom distribution delta: how much closer the selection moves to Bloom targets
   - Difficulty distribution delta: how much closer to difficulty targets
   - Budget fit: whether the question's points/duration fit within remaining budget

3. **Greedy selection loop:**
   ```
   selected = []
   while budget_remaining(selected) > 0:
       score each remaining candidate
       pick highest-scoring candidate
       if adding it would exceed both budgets: skip
       add to selected
       if no candidate improves score: break
   ```

4. **Budget enforcement:**
   - Points: stop when total_points >= target_points
   - Duration: stop when total_duration >= target_duration_minutes
   - If both specified, stop when either is reached
   - Points assigned via existing `POINT_SUGGESTIONS` lookup table

5. **Generate constraint report** -- Calculate achieved distributions vs targets, flag deviations beyond +/-5% tolerance.

### Characteristics

- Deterministic: highest score wins, no randomness
- Complexity: O(n * m) where n = candidate pool, m = selected count
- Sufficient for typical question banks (< 1000 questions)

## Frontend Changes

### QuestionPoolPanel.tsx

The existing auto-fill dialog is extended with a composition mode:

- **Mode toggle** at top of dialog: "Simple" (current) vs "Composition" (new)
- **Simple mode** stays as-is: count + filters
- **Composition mode** reveals:
  - Target points input (number field)
  - Target duration input (minutes)
  - Bloom distribution: 6 percentage inputs (B1-B6) with visual bar, must sum to 100
  - Difficulty distribution: 3 percentage inputs (easy/medium/hard) with visual bar, must sum to 100
  - Preset buttons for common distributions ("Balanced", "Application-heavy")

### Preview Step

In composition mode, clicking "Generate" triggers `preview=true`:

- Dialog transitions to a preview panel showing proposed questions with points, bloom level, difficulty tags
- Constraint satisfaction summary with target vs achieved, green/yellow color indicators
- Three action buttons: "Accept" (adds questions), "Retry" (re-runs), "Cancel" (closes)

### ComposerService.ts

- `autoFill()` method updated to handle both response types based on preview flag
- New return type union: `ExamDetail | AutoComposePreview`

### composer.ts (Types)

New TypeScript interfaces: `AutoComposePreview`, `ConstraintReport`, `DistributionResult`, `ProposedQuestionOut`.

## Files Modified

| File | Change |
|------|--------|
| `packages/core/backend/api/exams.py` | Enhance auto-fill endpoint, add preview response path, new schemas |
| `packages/core/backend/services/auto_compose_service.py` | **New file** -- greedy composition algorithm |
| `packages/core/frontend/src/components/composer/QuestionPoolPanel.tsx` | Composition mode UI, preview step |
| `packages/core/frontend/src/services/ComposerService.ts` | Updated autoFill with preview handling |
| `packages/core/frontend/src/types/composer.ts` | New TypeScript types |

## Files Unchanged

ExamBuilderView, ExamQuestionsPanel, ExamMetadataBar, ExportDialog, database models, Alembic migrations (no schema changes).

## Testing Strategy

### Backend Unit Tests (auto_compose_service)

- Basic composition with point budget only
- Duration budget constraint only
- Combined point + duration budgets
- Bloom distribution targeting and tolerance check
- Difficulty distribution targeting
- Insufficient questions: best-effort with report
- Edge cases: empty pool, single question, all constraints impossible
- Budget overshoot prevention

### Backend Integration Tests (exam API)

- Preview mode returns proposal without modifying exam
- Composition mode adds questions correctly after preview accepted
- Backward compatibility: existing simple auto-fill unchanged
- Constraint report accuracy
- Validation errors: distribution not summing to 100, missing budget

### Frontend Tests

- Extend QuestionPoolPanel tests for composition mode toggle
- Preview rendering with constraint report

**Estimated total: 15-20 new test cases**
