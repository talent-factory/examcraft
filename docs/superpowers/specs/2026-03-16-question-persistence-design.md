# Auto-Persistierung generierter Fragen + UI-Redirect zum Review-Workflow

**Linear Issue:** TF-219
**Status:** Approved
**Estimate:** 3 SP

## Problem

Generierte Fragen unter `/api/v1/rag/generate-exam` werden direkt als Response zurückgegeben und im Frontend angezeigt, aber nicht in der Datenbank gespeichert. Bei Browserschliessung oder Navigation gehen die Fragen verloren. Der bestehende Review-Workflow (`/questions/review`) ist vollständig implementiert, aber erhält keine Fragen aus der Generierung.

## Loesung

Die `generate-exam`-Response wird nach der Claude-API-Antwort um eine DB-Persistierung erweitert. Jede generierte Frage wird als `QuestionReview`-Eintrag mit Status `pending` gespeichert. Das Frontend zeigt nach Generierung eine Summary-Card mit Navigation zum Review-Workflow.

## Backend-Aenderungen

### 1. Response-Model erweitern (`rag_exams.py`)

`RAGExamResponseModel` erhaelt ein neues Feld:

```python
review_question_ids: List[int] = []
```

### 2. Persistierung im generate-exam Endpoint (`rag_exams.py`)

Nach Zeile 202 (`rag_service.generate_rag_exam()`), vor der Response-Konvertierung:

1. **Quota-Check**: `SubscriptionLimits.check_question_limit(current_user.institution, db)` -- verhindert Generierung ueber Limit
2. **Fragen speichern**: Fuer jede Frage aus `rag_response.questions` wird ein `QuestionReview` erstellt
3. **History-Eintraege**: Fuer jede Frage ein `ReviewHistory` mit `action="created"`
4. **Einzelner Commit**: Alle Fragen und History-Eintraege in einer Transaktion

### Feld-Mapping RAG Response zu QuestionReview

| Quelle | Feld | Ziel |
|--------|------|------|
| `question` | `question_text` | `question_text` |
| `question` | `question_type` | `question_type` |
| `question` | `options` | `options` |
| `question` | `correct_answer` | `correct_answer` |
| `question` | `explanation` | `explanation` |
| `question` | `difficulty` | `difficulty` |
| `question` | `source_chunks` | `source_chunks` |
| `question` | `source_documents` | `source_documents` |
| `question` | `confidence_score` | `confidence_score` |
| `request` | `topic` | `topic` |
| `request` | `language` | `language` |
| `rag_response` | `exam_id` | `exam_id` |
| `current_user` | `id` | `created_by` |
| `current_user` | `institution_id` | `institution_id` |
| (hardcoded) | `"pending"` | `review_status` |

### Fehlerbehandlung

- Bei DB-Fehler: Rollback, Fragen sind verloren aber Claude-Kosten bereits angefallen -- akzeptables Risiko
- Bei Quota-Ueberschreitung: HTTPException 403 **vor** der Claude-API-Anfrage (Quota-Check wird an den Anfang des Endpoints verschoben, vor Zeile 200)

## Frontend-Aenderungen

### RAGExamCreator (Premium-Komponente)

Nach erfolgreicher Generierung:

1. **Entfernen**: Direkte Fragen-Anzeige, JSON/Markdown-Download-Buttons
2. **Hinzufuegen**: Summary-Card mit:
   - Anzahl generierter Fragen (`questions.length`)
   - Generierungsdauer (`generation_time`)
   - Topic und Difficulty
   - Button "Zum Review" navigiert zu `/questions/review?exam_id={exam_id}`

Die `exam_id`-Filterung ist bereits im `ReviewQueue`-Component implementiert.

## Betroffene Dateien

| Datei | Aenderung |
|-------|-----------|
| `packages/core/backend/api/rag_exams.py` | Persistierung + Response-Erweiterung |
| `packages/premium/frontend/src/components/RAGExamCreator.tsx` | Summary statt Fragen-Liste |

## Out of Scope

- Keine neuen DB-Tabellen (nutzt `question_reviews`, `review_history`)
- Keine WebSocket/Async-Progress (TF-208, in Bearbeitung durch Raffaele)
- Keine Collaborative Review Features (TF-130, Future)
- Keine Aenderungen am Review-Workflow (API, UI, Service)
- Keine Aenderungen am RAG-Service selbst

## Acceptance Criteria

- Generierte Fragen erscheinen in `question_reviews` mit Status `pending`
- `exam_id` wird korrekt gesetzt fuer Batch-Filterung im Review
- `created_by` und `institution_id` werden aus `current_user` uebernommen
- Quota-Check greift vor der Claude-API-Anfrage
- Response enthaelt `review_question_ids`
- Frontend zeigt Summary statt Fragen-Liste
- "Zum Review"-Button navigiert zu `/questions/review?exam_id={exam_id}`
- Backend-Test: Persistierung und History-Eintraege werden erstellt
- Frontend-Test: Summary-Anzeige nach Generierung
