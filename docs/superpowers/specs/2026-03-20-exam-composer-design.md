# Exam Composer — Design Specification

**Date:** 2026-03-20
**Status:** Draft
**Author:** Daniel + Claude
**Linear Issue:** TF-56 (Exam Composition & Export)

## Overview

The Exam Composer enables instructors to assemble complete exams from approved questions, configure metadata and point values, and export in multiple formats. It fills the gap between the existing Review Queue (where questions get approved) and the final exam delivery.

### MVP Scope

- Curate exams from the pool of approved questions (manual + AI-assisted selection)
- Configure exam metadata (title, course, date, time limit, aids, instructions, passing threshold)
- Assign points per question (auto-suggested by difficulty, manually overridable)
- Reorder questions via drag and drop
- Export to Markdown, JSON, and Moodle XML

### Out of Scope (Future Phases)

- LMS integration (direct Moodle API push)
- PDF export with cover page
- Exam variants (A/B shuffling)
- Student answer import and auto-grading
- Collaborative editing

## Data Model

### New Table: `exams`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| title | String(300), NOT NULL | Exam title |
| course | String(200), nullable | Module/course name |
| exam_date | Date, nullable | Scheduled exam date |
| time_limit_minutes | Integer, nullable | Time limit in minutes |
| allowed_aids | Text, nullable | Permitted aids (free text, OpenBook context) |
| instructions | Text, nullable | Instructions for students |
| passing_percentage | Float, default 50.0 | Passing threshold in percent |
| total_points | Float, default 0.0 | Auto-calculated sum of question points |
| status | String(20), default "draft" | `draft`, `finalized`, `exported` |
| language | String(10), default "de" | Language code |
| institution_id | FK → institutions, NOT NULL | Multi-tenancy |
| created_by | FK → users, NOT NULL | Creator |
| created_at | DateTime, server_default now() | Creation timestamp |
| updated_at | DateTime, onupdate now() | Last modification |

**Constraints:**
- CHECK: `status IN ('draft', 'finalized', 'exported')`
- INDEX on `institution_id`, `created_by`, `status`

### New Table: `exam_questions`

| Column | Type | Description |
|--------|------|-------------|
| id | Integer PK | Auto-increment |
| exam_id | FK → exams(id), ON DELETE CASCADE | Parent exam |
| question_id | FK → question_reviews(id), ON DELETE CASCADE | Referenced approved question |
| position | Integer, NOT NULL | Order within the exam |
| points | Float, NOT NULL | Points for this question in this exam |
| section | String(100), nullable | Optional grouping (e.g., "Part A: Multiple Choice") |

**Constraints:**
- UNIQUE(exam_id, question_id) — no duplicate questions per exam
- UNIQUE(exam_id, position) — unique ordering
- INDEX on `exam_id`

### Existing Model Impact

- `QuestionReview.exam_id` field remains unchanged for backward compatibility but is not used by the new Composer
- No changes to existing tables

## API Design

### New Router: `/api/v1/exams`

All endpoints require the `exams:create` permission. This is intentional for the MVP — a single permission controls full access to the Exam Composer feature. Finer-grained permissions (e.g., separate `exams:export`, `exams:delete`) can be introduced later if needed.

#### CRUD

| Method | Path | Description |
|--------|------|-------------|
| POST | `/` | Create a new exam (metadata only) |
| GET | `/` | List own exams (filter by status, search by title, pagination) |
| GET | `/{exam_id}` | Get exam with all questions (joined) |
| PUT | `/{exam_id}` | Update exam metadata |
| DELETE | `/{exam_id}` | Delete exam (only `draft` status) |

#### Question Management

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{exam_id}/questions` | Add questions (batch: list of question_ids) |
| PUT | `/{exam_id}/questions/{eq_id}` | Update position/points of a single question |
| DELETE | `/{exam_id}/questions/{eq_id}` | Remove question from exam |
| POST | `/{exam_id}/reorder` | Batch reorder (list of {eq_id, position}) |

#### AI-Assisted Selection

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{exam_id}/auto-fill` | Suggest questions based on criteria |
| GET | `/approved-questions` | Browse approved question pool with filters |

**Auto-Fill Request:**
```json
{
  "count": 5,
  "topic": "Heapsort",
  "difficulty": ["medium", "hard"],
  "bloom_level_min": 3,
  "question_types": ["multiple_choice", "open_ended"],
  "exclude_question_ids": [1, 2, 3]
}
```

Auto-fill is purely database-driven: filtered query + weighted random selection for type/difficulty diversity. No AI API calls required.

#### Workflow

| Method | Path | Description |
|--------|------|-------------|
| POST | `/{exam_id}/finalize` | Set status to `finalized` (validates all questions still approved) |
| POST | `/{exam_id}/unfinalize` | Revert to `draft` |

#### Export

| Method | Path | Description |
|--------|------|-------------|
| GET | `/{exam_id}/export/{format}` | Export exam (format: `md`, `json`, `moodle`) |

Query parameters for markdown export:
- `include_solutions` (bool, default false) — include correct answers and explanations

**Approved Questions Endpoint** (`GET /approved-questions`):
- Filters: `topic`, `difficulty`, `bloom_level`, `question_type`, `search` (full-text on question_text)
- Pagination: `limit`, `offset`
- Returns usage count (how many exams include each question)
- Scoped to user's institution

### Point Auto-Suggestion

When adding questions, points are auto-suggested based on difficulty and question type:

| Difficulty | MC | True/False | Open-Ended |
|-----------|-----|-----------|------------|
| easy | 2 | 1 | 3 |
| medium | 4 | 2 | 6 |
| hard | 6 | 3 | 10 |

The `total_points` field on `exams` is recalculated on every question add/remove/update.

## Frontend Design

### Page Structure

The route `/exams/compose` renders `ExamComposer` (replaces the current `<Exams />` reuse).

```
ExamComposer (Page)
├── ExamListView                    — Default: list of own exams
│   ├── ExamCard                    — Single exam (title, status, date, question count)
│   └── CreateExamDialog            — Modal for new exam (metadata input)
│
└── ExamBuilderView                 — Two-Panel builder (after selecting/creating an exam)
    ├── ExamMetadataBar             — Top bar: title, stats, edit metadata, export button
    ├── QuestionPoolPanel (left)    — Searchable pool of approved questions
    │   ├── QuestionPoolFilters     — Search + filter chips (type, difficulty, bloom)
    │   ├── AutoFillButton          — AI-assisted question suggestions
    │   └── PoolQuestionCard        — Single question with "+ Add" button
    └── ExamQuestionsPanel (right)  — Exam composition
        ├── ExamQuestionItem        — Question with drag handle, number, points input, remove
        └── DropZone                — "Drag questions here or add from pool"
```

### Layout: Two-Panel

- **Top:** ExamMetadataBar — collapsible panel showing exam title, stats (question count, total points, time limit), "Edit Metadata" button, and "Export" button
- **Left panel:** QuestionPoolPanel — search field, filter chips, scrollable list of approved questions with badges (difficulty, type, bloom level). Already-added questions appear dimmed with a checkmark.
- **Right panel:** ExamQuestionsPanel — ordered list of exam questions with drag handles, inline point editing, position numbers, and remove buttons. Drop zone at the bottom.

### Technology

- **Drag & Drop:** `@dnd-kit/core` + `@dnd-kit/sortable` (lightweight, accessible, React-native)
- **Server State:** TanStack Query (consistent with existing app)
- **UI:** Tailwind CSS + MUI Dialogs (consistent with existing component mix)

### Interaction Flow

1. User navigates to `/exams/compose` → sees **ExamListView** with existing exams
2. Click "Neue Prüfung" → **CreateExamDialog** opens (title, course, date, etc.)
3. After creation or clicking an existing exam → **ExamBuilderView**
4. In builder: search/filter questions in left panel → click "+ Add" or drag to right panel
5. Adjust points per question (inline input), reorder via drag and drop
6. Click "Export" in MetadataBar → format selection dialog → file download

## Export Formats

### Markdown

Two files generated:
- `exam_{title}.md` — Questions only (for students)
- `exam_{title}_solutions.md` — With correct answers and explanations

Structure: cover section (title, date, time, aids, instructions, total points, passing threshold) followed by numbered questions with point values and type-appropriate formatting (checkboxes for MC, W/F markers for true/false, answer space for open-ended).

### JSON

Complete exam data as structured JSON including exam metadata, ordered questions with all fields, and correct answers. Designed to be re-importable.

### Moodle XML

Standard Moodle XML format with `<question>` elements using types `multichoice`, `truefalse`, and `essay`. Directly importable via Moodle's "Import" function.

## Error Handling & Edge Cases

1. **Question rejected after being added to exam:** ExamQuestionItem shows a warning badge. Finalize is blocked with a message listing affected questions. User must remove or replace them.

2. **Question deleted:** FK CASCADE removes the `exam_questions` row. `total_points` recalculated on next load.

3. **Empty exam export:** Export button disabled when no questions are present.

4. **Finalize validation:** Checks that all referenced questions still have `review_status = 'approved'`. Blocks with specific error if any don't.

5. **Finalized exam protection:** Finalized exams cannot be edited (questions added/removed/reordered, metadata changed). Must be reverted to `draft` first via `unfinalize`.

6. **Multi-tenancy:** All queries scoped to `institution_id`. Instructors only see questions and exams from their institution.

7. **Concurrent access:** Optimistic locking via `updated_at`. The client must include the `updated_at` value in the PUT request body. The server compares it against the current DB value — if they differ, a 409 Conflict is returned. This prevents silent overwrites when two users edit the same exam.

## Permissions

Uses the existing `exams:create` permission already defined in the RBAC system and navigation. No new permissions required.

## Migration Plan

1. Create Alembic migration for `exams` and `exam_questions` tables
2. Update `/exams/compose` route to render new `ExamComposer` instead of `<Exams />`
3. Add new API router to FastAPI app
4. Install `@dnd-kit/core` and `@dnd-kit/sortable` frontend dependencies
