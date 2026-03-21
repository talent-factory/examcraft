# Fragen-Metadaten anreichern: Bloom-Level & Zeitschaetzung

## Ziel

Sicherstellen, dass alle generierten Fragen vollstaendige Metadaten haben (Bloom-Level, geschaetzte Bearbeitungszeit), damit die Auto-Composition Engine (TF-299) constraint-basiert arbeiten kann.

## Problem

`bloom_level` und `estimated_time_minutes` sind bei allen generierten Fragen NULL, obwohl die DB-Spalten existieren. Der RAG-Service setzt diese Felder bei der Generierung nicht.

## Betroffene Dateien

| Datei | Aenderung |
|---|---|
| `packages/premium/backend/services/rag_service.py` | RAGQuestion Dataclass erweitern, 3 Fallback-Templates mit bloom_level ergaenzen, _convert_to_rag_question() Bloom-Level auslesen |
| `packages/core/backend/tasks/question_tasks.py` | TIME_ESTIMATES Lookup-Tabelle, bloom_level + estimated_time_minutes beim Persistieren setzen |
| `packages/core/backend/api/exams.py` | ApprovedQuestionOut um estimated_time_minutes erweitern |
| `scripts/enrich_question_metadata.py` | Neues Batch-Script fuer bestehende Fragen |

## Design

### 1. RAG-Prompt & Dataclass (rag_service.py)

Die drei Fallback-Templates bekommen ein zusaetzliches Feld im JSON-Format:

```json
{
    "question": "...",
    "options": ["A) ...", "B) ..."],
    "correct_answer": "A",
    "explanation": "...",
    "bloom_level": 3
}
```

Die Prompt-Instruktion wird ergaenzt um:

```text
"bloom_level": Bloom-Taxonomie-Stufe als Zahl 1-6
  (1=Erinnern, 2=Verstehen, 3=Anwenden, 4=Analysieren, 5=Bewerten, 6=Erschaffen)
```

Die RAGQuestion Dataclass bekommt zwei neue Felder:

```python
bloom_level: Optional[int] = None
estimated_time_minutes: Optional[int] = None
```

`_convert_to_rag_question()` liest `bloom_level` aus der Claude-Antwort. `estimated_time_minutes` wird per Lookup berechnet (nicht von Claude).

### 2. Zeitschaetzung Lookup-Tabelle

Analog zur bestehenden `POINT_SUGGESTIONS` in exams.py:

```python
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

Diese Tabelle wird in `question_tasks.py` beim Persistieren verwendet.

### 3. Persistierung & API

**question_tasks.py** -- Zwei Felder zum QuestionReview-Konstruktor:

```python
bloom_level=question.bloom_level,
estimated_time_minutes=TIME_ESTIMATES.get(
    (question.question_type, question.difficulty), 3
),
```

**exams.py** -- ApprovedQuestionOut erweitern:

```python
estimated_time_minutes: Optional[int] = None
```

Keine DB-Migration noetig -- die Spalten existieren bereits.

### 4. Batch-Enrichment bestehender Fragen

Einmaliges Python-Script (`scripts/enrich_question_metadata.py`):

1. Alle QuestionReview-Eintraege mit `bloom_level=NULL` laden
2. Fragen in Batches (10 pro Aufruf) an Claude schicken:
   ```text
   Bestimme die Bloom-Taxonomie-Stufe (1-6) fuer jede Frage:
   1=Erinnern, 2=Verstehen, 3=Anwenden, 4=Analysieren, 5=Bewerten, 6=Erschaffen
   Antwort als JSON-Array: [{"id": 1, "bloom_level": 3}, ...]
   ```
3. Ergebnisse in DB aktualisieren (bloom_level + estimated_time_minutes via Lookup)
4. Fortschritt loggen, bei Fehlern weitermachen (idempotent)

Manuelle einmalige Ausfuehrung -- kein Alembic-Migration, kein Startup-Hook.

## Nicht betroffen

- DB-Schema: Spalten existieren bereits (`bloom_level Integer nullable`, `estimated_time_minutes Integer nullable`)
- Frontend: Keine Aenderungen
- Exam Composer: Liest bloom_level bereits aus ApprovedQuestionOut
