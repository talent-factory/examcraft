# Review-Workflow Enhancement: Reviewer-Zuweisung und rollenbasierte Ansicht

**Datum:** 2026-03-18
**Status:** Approved
**Linear Issue:** TF-219 (Erweiterung)

## Zusammenfassung

Der Review-Workflow wird um drei Funktionen erweitert:
1. Reviewer-Name wird sichtbar angezeigt (aufgelöst aus User-ID)
2. Neue Detail-Seite mit rollenbasierter Ansicht (Editor-Tabs für Reviewer, Nur-Lesen für alle anderen)
3. Konfigurierbares Vier-Augen-Prinzip pro Institution

## Kontext

Aktuell sehen alle Benutzer die gleiche Ansicht in der Review Queue. Es gibt keine visuelle Unterscheidung zwischen dem zugewiesenen Reviewer und anderen Benutzern. Der QuestionEditor ist ein Modal-Dialog ohne Markdown-Vorschau. Das Vier-Augen-Prinzip ist nicht implementiert.

## Design

### 1. Backend-Änderungen

#### 1.1 Institution Model (`models/auth.py`)

Neues Feld auf `Institution`:

```python
require_second_reviewer = Column(Boolean, default=False)
```

Wenn `True`, darf der zugewiesene Reviewer (`reviewed_by`) die Frage nicht selbst approven. Ein anderer User mit `approve_questions`-Berechtigung muss final genehmigen.

#### 1.2 Question Review API (`api/question_review.py`)

**GET /questions/{id}/review erweitern:**
- Reviewer-User-Objekt (Vorname, Nachname, E-Mail) joinen statt nur ID zurückgeben
- Neues Response-Feld: `reviewer_info: { id, first_name, last_name, email }`

**PUT /questions/{id}/edit anpassen:**
- Wenn der aktuelle User der zugewiesene Reviewer ist (`current_user.id == question.reviewed_by`) und der Status `in_review` ist: Status bleibt `in_review` (nicht auf `edited` wechseln)
- Wenn ein anderer User editiert: Status wechselt auf `edited` (wie bisher)

**POST /questions/{id}/approve anpassen:**
- Vier-Augen-Check: Institution via `db.query(Institution).filter(Institution.id == question.institution_id)` laden. Wenn `institution_id` NULL ist, Vier-Augen-Check überspringen.
- Wenn `require_second_reviewer == True` und `current_user.id == question.reviewed_by`, dann 403 mit Meldung "Vier-Augen-Prinzip: Ein anderer Reviewer muss diese Frage genehmigen."
- Wenn `require_second_reviewer == False`: Approve wie bisher
- **Wichtig:** `reviewed_by` darf beim Approve NICHT überschrieben werden — es bleibt der ursprüngliche Reviewer. Neues Feld `approved_by` ist nicht nötig; der Approver wird in der `ReviewHistory` (action="approved", changed_by) festgehalten.

#### 1.3 Response-Modell Erweiterung

```python
class ReviewerInfo(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str

class QuestionReviewResponse(BaseModel):
    # ... bestehende Felder ...
    reviewed_by: Optional[int]
    reviewer_info: Optional[ReviewerInfo]  # NEU
```

### 2. Frontend-Änderungen

#### 2.1 QuestionReviewCard (`QuestionReviewCard.tsx`)

- Zeigt "Reviewer: {Vorname Nachname}" unterhalb des Status-Chips wenn `reviewer_info` vorhanden
- Karte erhält "Details"-Link/Button (navigiert zu `/questions/review/:id`). Nicht die gesamte Karte klickbar machen, da verschachtelte Buttons (Approve/Reject/Edit) `stopPropagation` erfordern würden.
- Approve/Reject Buttons bleiben in der Karte für schnelle Aktionen
- "Review starten" Button bleibt (setzt `reviewed_by` und navigiert zur Detail-Seite)

#### 2.2 Neue Detail-Seite (`QuestionReviewDetail.tsx`)

Neue Route: `/questions/review/:id`

**Rollenbasierte Ansicht:**

| Bedingung | Ansicht |
|-----------|---------|
| `currentUser.id === question.reviewed_by` | Tabs: "Bearbeiten" + "Vorschau". Aktionen: Speichern, Approve, Reject |
| Alle anderen Benutzer | Nur gerenderte Ansicht (Vorschau-Tab). Kommentarfeld zum Feedback geben |

**Layout der Detail-Seite:**

```
┌──────────────────────────────────────────────────┐
│ ← Zurück zur Queue    Question #42 · Open Ended  │
│                                      [IN_REVIEW] │
├──────────────────────────────────────────────────┤
│ Reviewer: Daniel Senften                         │
├──────────────────────────────────────────────────┤
│ [BEARBEITEN]  [VORSCHAU]          (nur Reviewer) │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ <textarea> oder <MarkdownRenderer>           │ │
│ │                                              │ │
│ │ Frage-Text (Markdown)                        │ │
│ │                                              │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ Musterlösung / Explanation (Markdown)        │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ ┌──────────────────────────────────────────────┐ │
│ │ Metadaten: Difficulty, Bloom Level, Zeit     │ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ [Speichern]  [Approve]  [Reject]                 │
├──────────────────────────────────────────────────┤
│ Kommentare (alle Benutzer können kommentieren)   │
│ ┌──────────────────────────────────────────────┐ │
│ │ Kommentar hinzufügen...              [Senden]│ │
│ └──────────────────────────────────────────────┘ │
│                                                  │
│ - Daniel S.: "Formulierung in Aufgabe 2..."      │
│ - System: "Review gestartet"                     │
└──────────────────────────────────────────────────┘
```

**Bearbeiten-Tab (nur Reviewer):**
- `<textarea>` mit Monospace-Font für Markdown-Bearbeitung (wie PromptEditor)
- Separate Textareas für: `question_text`, `correct_answer`, `explanation`
- Dropdown für `difficulty`, Number-Input für `bloom_level` und `estimated_time_minutes`

**Vorschau-Tab (alle Benutzer):**
- MarkdownRenderer für `question_text`, `correct_answer`, `explanation`
- Optionen-Liste für Multiple Choice (korrekte Antwort hervorgehoben)
- Qualitätsindikatoren (Confidence Score, Bloom Level, etc.)
- Source-Dokumente

#### 2.3 Router-Anpassung

Neue Route in App.tsx:
```tsx
<Route path="/questions/review/:id" element={<QuestionReviewDetail />} />
```

#### 2.4 ReviewService Erweiterung

```typescript
interface ReviewerInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

// getQuestionDetail(id) - lädt einzelne Frage mit reviewer_info
```

#### 2.5 TypeScript-Typen

`QuestionReview` Interface erweitern:
```typescript
reviewer_info?: {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
};
```

### 3. Vier-Augen-Prinzip

**Konfiguration:** `institution.require_second_reviewer` (Boolean, Default: `false`)

**Verhalten wenn aktiv:**
- Reviewer (User A) kann: Review starten, Frage editieren, Reject
- Reviewer (User A) kann NICHT: eigene Review approven
- Anderer User (User B) mit `approve_questions` Berechtigung: kann approven
- API gibt 403 zurück mit klarer Meldung

**Verhalten wenn inaktiv:**
- Reviewer kann alles selbst: editieren, approven, rejecten

**Admin-UI:** Checkbox in der Institution-Verwaltung. Erfordert:
- `api/admin.py`: Institution-Update-Endpoint um `require_second_reviewer` erweitern
- Admin-Frontend: Checkbox im Institution-Formular

### 4. Bugfixes (im Rahmen dieser Arbeit)

Diese bestehenden Probleme werden als Teil der Implementierung behoben:

1. **`reviewed_by` wird bei Approve/Reject nicht mehr überschrieben** — der ursprüngliche Reviewer bleibt erhalten, der Approver wird nur in ReviewHistory erfasst
2. **Kommentar-Autor wird aus `current_user` abgeleitet** — `author` und `author_role` in CommentCreate werden serverseitig aus dem authentifizierten User gesetzt, nicht vom Client gesendet
3. **`ReviewActionRequest.reviewer_id` entfernen** — ungenutzt, wird durch `current_user` ersetzt
4. **Frontend-Typ `reviewed_by` von `string` auf `number` korrigieren**

### 5. Fehlerbehandlung Detail-Seite

- **Laden:** Spinner (CircularProgress) wie in ReviewQueue
- **404:** Alert "Frage nicht gefunden" mit Link zurück zur Queue
- **Keine Berechtigung:** Alert "Keine Berechtigung" (kein Redirect)
- **Netzwerkfehler:** Alert mit Retry-Button

### 6. Datenfluss

```
Pending
  → "Review starten" (User A)
  → In Review (reviewed_by = A)
      → User A öffnet Detail-Seite → sieht Editor-Tabs
      → User A editiert + speichert → bleibt In Review
      → Vier-Augen AUS: User A klickt "Approve" → Approved
      → Vier-Augen AN:  User A klickt "Approve" → 403 Fehler
                         User B klickt "Approve" → Approved
```

### 7. Betroffene Dateien

| Datei | Änderung | Aufwand |
|-------|----------|---------|
| `models/auth.py` | `require_second_reviewer` Feld | Klein |
| `api/question_review.py` | Reviewer-Join, Edit-Status-Logik, Vier-Augen-Check, Approve nicht mehr `reviewed_by` überschreiben, Kommentar-Autor serverseitig | Mittel |
| `api/admin.py` | Institution-Update um `require_second_reviewer` erweitern | Klein |
| `QuestionReviewCard.tsx` | Reviewer-Name, Details-Link | Klein |
| `QuestionReviewDetail.tsx` | **NEU** — Detail-Seite mit Tabs | Gross |
| `ReviewQueue.tsx` | `handleStartReview` navigiert nach Review-Start zur Detail-Seite | Klein |
| `ReviewService.ts` | `getQuestionDetail()`, `startReview` return, `ReviewerInfo` Typ | Klein |
| `App.tsx` / Router | Neue Route | Klein |
| `types/review.ts` | `reviewer_info` Typ, `reviewed_by: number` Fix | Klein |
| Admin-Frontend | Checkbox für `require_second_reviewer` | Klein |

### 8. Nicht im Scope

- Reviewer-Zuweisung an andere Personen (aktuell: wer "Review starten" klickt, ist der Reviewer)
- Multi-Reviewer-Support (mehrere Reviewer pro Frage)
- Echtzeit-Kollaboration (gleichzeitiges Editieren)
- Reviewer-Workload-Tracking
- E-Mail-Benachrichtigungen bei Zuweisung

### 9. Migration

- Alembic-Migration für `require_second_reviewer` auf `institutions` Tabelle
- Default `False` — keine Verhaltensänderung für bestehende Institutionen
- Keine Datenmigration nötig (bestehende `reviewed_by` Werte sind bereits User-IDs)
