# Question Metadata Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure all generated questions have complete bloom_level (1-6) and estimated_time_minutes metadata for the Auto-Composition Engine (TF-299).

**Architecture:** Add bloom_level to Claude's JSON output format in fallback templates, extract it in the conversion layer, compute estimated_time via lookup table, persist both fields. Batch-enrich existing questions via a one-time script.

**Tech Stack:** Python, SQLAlchemy, Anthropic Claude API, PostgreSQL

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `packages/premium/backend/services/rag_service.py` | Modify (lines 47-59, 207-296, 613-648) | Add bloom_level to dataclass, prompts, and converter |
| `packages/core/backend/tasks/question_tasks.py` | Modify (lines 87-103) | Add TIME_ESTIMATES lookup, persist bloom_level + estimated_time |
| `packages/core/backend/api/exams.py` | Modify (lines 270-281) | Add estimated_time_minutes to ApprovedQuestionOut |
| `scripts/enrich_question_metadata.py` | Create | One-time batch enrichment of existing questions |

---

### Task 1: Extend RAGQuestion dataclass

**Files:**
- Modify: `packages/premium/backend/services/rag_service.py:47-59`

- [ ] **Step 1: Add bloom_level and estimated_time_minutes fields to RAGQuestion**

After line 59 (`confidence_score: float = 0.0`), add:

```python
    bloom_level: Optional[int] = None  # Bloom's Taxonomy 1-6
    estimated_time_minutes: Optional[int] = None
```

The `Optional` import is already present at the top of the file.

- [ ] **Step 2: Verify the file parses correctly**

Run: `cd packages/core/backend && python -c "from premium.services.rag_service import RAGQuestion; print('OK')" 2>&1`

- [ ] **Step 3: Commit**

```bash
git add packages/premium/backend/services/rag_service.py
git commit -m "feat(rag): add bloom_level and estimated_time_minutes to RAGQuestion dataclass"
```

---

### Task 2: Add bloom_level to fallback prompt templates

**Files:**
- Modify: `packages/premium/backend/services/rag_service.py:207-296`

- [ ] **Step 1: Add bloom_level instruction and field to multiple_choice template**

In the multiple_choice template, add the bloom_level instruction after the ANTWORTOPTIONEN section (after line 205) and before FORMAT:

```text
BLOOM-TAXONOMIE:
- Bestimme die Bloom-Taxonomie-Stufe der Frage als Zahl 1-6:
  1=Erinnern, 2=Verstehen, 3=Anwenden, 4=Analysieren, 5=Bewerten, 6=Erschaffen
```

In the FORMAT JSON block (lines 208-218), add the bloom_level field after "explanation":

```json
    "bloom_level": 3
```

So the full JSON format becomes:

```json
{{
    "question": "Konkrete, spezifische Frage basierend auf dem Kontext",
    "options": [
        "A) Spezifische Option mit konkreten Details (Code in `backticks`)",
        "B) Plausible Alternative mit aehnlichem Konzept",
        "C) Haeufiges Missverstaendnis oder verwandtes Konzept",
        "D) Weitere plausible aber falsche Option"
    ],
    "correct_answer": "A",
    "explanation": "Detaillierte Erklaerung mit Verweis auf den Kontext, warum A korrekt ist und warum die anderen Optionen falsch sind",
    "bloom_level": 3
}}
```

- [ ] **Step 2: Add bloom_level to open_ended template**

Same pattern: add BLOOM-TAXONOMIE instruction and `"bloom_level": 4` to the JSON format (lines 253-262).

The open_ended JSON format becomes:

```json
{{
    "question": "Konkrete, anspruchsvolle offene Frage",
    "sample_answer": "Detaillierte Musterantwort mit spezifischen Punkten aus dem Kontext",
    "evaluation_criteria": [
        "Kriterium 1: Spezifischer Aspekt der Antwort",
        "Kriterium 2: Weiterer wichtiger Punkt",
        "Kriterium 3: Tiefe des Verstaendnisses"
    ],
    "bloom_level": 4
}}
```

- [ ] **Step 3: Add bloom_level to true_false template**

Same pattern: add BLOOM-TAXONOMIE instruction and `"bloom_level": 2` to the JSON format (lines 291-296).

The true_false JSON format becomes:

```json
{{
    "statement": "Praezise, spezifische Aussage basierend auf dem Kontext",
    "correct_answer": true,
    "explanation": "Detaillierte Erklaerung mit Verweis auf den Kontext, warum die Aussage wahr/falsch ist",
    "bloom_level": 2
}}
```

- [ ] **Step 4: Commit**

```bash
git add packages/premium/backend/services/rag_service.py
git commit -m "feat(rag): add bloom_level to all fallback prompt templates"
```

---

### Task 3: Extract bloom_level in _convert_to_rag_question

**Files:**
- Modify: `packages/premium/backend/services/rag_service.py:613-648`

- [ ] **Step 1: Add bloom_level extraction to all three question type branches**

In each of the three `RAGQuestion(...)` constructor calls inside `_convert_to_rag_question()`, add:

```python
bloom_level=claude_question.get("bloom_level"),
```

This goes after the `confidence_score=confidence_score,` line in each branch (multiple_choice at line 623, open_ended at line 635, true_false at line 647).

If Claude does not return bloom_level, it defaults to `None` via the dataclass default.

- [ ] **Step 2: Commit**

```bash
git add packages/premium/backend/services/rag_service.py
git commit -m "feat(rag): extract bloom_level from Claude response in converter"
```

---

### Task 4: Add TIME_ESTIMATES and persist metadata in question_tasks.py

**Files:**
- Modify: `packages/core/backend/tasks/question_tasks.py:87-103`

- [ ] **Step 1: Add TIME_ESTIMATES lookup table**

Add after the imports section (after line 18), before the `_persist_questions` function:

```python
# Time estimation lookup table (minutes) based on question type and difficulty
TIME_ESTIMATES = {
    ("multiple_choice", "easy"): 1,
    ("multiple_choice", "medium"): 2,
    ("multiple_choice", "hard"): 3,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 1,
    ("true_false", "hard"): 2,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 5,
    ("open_ended", "hard"): 8,
}
```

- [ ] **Step 2: Add bloom_level and estimated_time_minutes to QuestionReview constructor**

In the `QuestionReview(...)` constructor call (lines 87-103), add two new fields after `institution_id=institution_id,` (line 102):

```python
                bloom_level=getattr(question, 'bloom_level', None),
                estimated_time_minutes=TIME_ESTIMATES.get(
                    (question.question_type, question.difficulty), 3
                ),
```

Using `getattr` with default `None` ensures backward compatibility if the Core RAGQuestion stub (which lacks bloom_level) is used instead of the Premium one.

- [ ] **Step 3: Verify compilation**

Run: `cd packages/core/backend && python -c "from tasks.question_tasks import _persist_questions; print('OK')" 2>&1`

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/tasks/question_tasks.py
git commit -m "feat(questions): persist bloom_level and estimated_time_minutes on generation"
```

---

### Task 5: Add estimated_time_minutes to ApprovedQuestionOut schema

**Files:**
- Modify: `packages/core/backend/api/exams.py:270-281`

- [ ] **Step 1: Add estimated_time_minutes field to ApprovedQuestionOut**

Add after `bloom_level: Optional[int]` (line 276):

```python
    estimated_time_minutes: Optional[int] = None
```

The full schema becomes:

```python
class ApprovedQuestionOut(BaseModel):
    id: int
    question_text: str
    question_type: str
    difficulty: str
    topic: str
    bloom_level: Optional[int]
    estimated_time_minutes: Optional[int] = None
    options: Optional[list]
    usage_count: int = 0

    class Config:
        from_attributes = True
```

Since `from_attributes = True` is set, SQLAlchemy will auto-map the `estimated_time_minutes` column from the `QuestionReview` model.

- [ ] **Step 2: Commit**

```bash
git add packages/core/backend/api/exams.py
git commit -m "feat(exams): expose estimated_time_minutes in approved questions API"
```

---

### Task 6: Create batch enrichment script

**Files:**
- Create: `scripts/enrich_question_metadata.py`

- [ ] **Step 1: Create the enrichment script**

Create `scripts/enrich_question_metadata.py`:

```python
"""
One-time script to enrich existing questions with bloom_level and estimated_time_minutes.
Bloom-level is determined by Claude API in batches.
Estimated time is computed via a lookup table.

Usage:
    cd packages/core/backend
    python ../../../scripts/enrich_question_metadata.py

Requires:
    - DATABASE_URL env var (or .env file)
    - ANTHROPIC_API_KEY env var (or .env file)
"""

import json
import logging
import os
import sys

from dotenv import load_dotenv

# Add backend to path so we can import models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "core", "backend"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import anthropic
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.question_review import QuestionReview

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TIME_ESTIMATES = {
    ("multiple_choice", "easy"): 1,
    ("multiple_choice", "medium"): 2,
    ("multiple_choice", "hard"): 3,
    ("true_false", "easy"): 1,
    ("true_false", "medium"): 1,
    ("true_false", "hard"): 2,
    ("open_ended", "easy"): 3,
    ("open_ended", "medium"): 5,
    ("open_ended", "hard"): 8,
}

BATCH_SIZE = 10


def get_bloom_levels(client: anthropic.Anthropic, questions: list[dict]) -> list[dict]:
    """Ask Claude to determine bloom levels for a batch of questions."""
    questions_text = json.dumps(questions, ensure_ascii=False, indent=2)

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": f"""Bestimme die Bloom-Taxonomie-Stufe (1-6) fuer jede Frage:
1=Erinnern, 2=Verstehen, 3=Anwenden, 4=Analysieren, 5=Bewerten, 6=Erschaffen

Fragen:
{questions_text}

Antwort als JSON-Array (NUR das Array, kein Markdown):
[{{"id": 1, "bloom_level": 3}}, ...]""",
            }
        ],
    )

    text = response.content[0].text.strip()
    # Handle potential markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    return json.loads(text)


def main():
    database_url = os.getenv("DATABASE_URL", "postgresql://examcraft:examcraft_dev@localhost:5432/examcraft")
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    client = anthropic.Anthropic(api_key=api_key)

    # Find questions missing bloom_level
    questions_to_enrich = (
        db.query(QuestionReview)
        .filter(QuestionReview.bloom_level.is_(None))
        .all()
    )

    total = len(questions_to_enrich)
    logger.info(f"Found {total} questions to enrich")

    if total == 0:
        logger.info("Nothing to do")
        return

    enriched = 0
    for i in range(0, total, BATCH_SIZE):
        batch = questions_to_enrich[i : i + BATCH_SIZE]

        batch_data = [
            {"id": q.id, "question": q.question_text, "type": q.question_type}
            for q in batch
        ]

        try:
            results = get_bloom_levels(client, batch_data)
            bloom_map = {r["id"]: r["bloom_level"] for r in results}

            for q in batch:
                bloom = bloom_map.get(q.id)
                if bloom and 1 <= bloom <= 6:
                    q.bloom_level = bloom

                if q.estimated_time_minutes is None:
                    q.estimated_time_minutes = TIME_ESTIMATES.get(
                        (q.question_type, q.difficulty), 3
                    )

            db.commit()
            enriched += len(batch)
            logger.info(f"Progress: {enriched}/{total} questions enriched")

        except Exception as e:
            logger.error(f"Batch {i}-{i + BATCH_SIZE} failed: {e}")
            db.rollback()
            continue

    logger.info(f"Done. Enriched {enriched}/{total} questions.")
    db.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify script syntax**

Run: `python -c "import ast; ast.parse(open('scripts/enrich_question_metadata.py').read()); print('OK')"`

- [ ] **Step 3: Commit**

```bash
git add scripts/enrich_question_metadata.py
git commit -m "feat(scripts): add one-time batch enrichment for question metadata (TF-300)"
```

---

### Task 7: Final verification

- [ ] **Step 1: Verify backend starts without errors**

Run: `cd packages/core/backend && python -c "from api.exams import ApprovedQuestionOut; print(ApprovedQuestionOut.model_fields.keys())" 2>&1`

Expected: Shows all fields including `estimated_time_minutes`

- [ ] **Step 2: Verify RAGQuestion has new fields**

Run: `cd packages/core/backend && python -c "from premium.services.rag_service import RAGQuestion; q = RAGQuestion(question_text='test', question_type='mc', bloom_level=3, estimated_time_minutes=5); print(q.bloom_level, q.estimated_time_minutes)" 2>&1`

Expected: `3 5`

- [ ] **Step 3: Final commit if any fixes were needed**

Only if previous steps required adjustments.
