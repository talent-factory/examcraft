# Review-Workflow Enhancement Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reviewer name display, rollenbasierte Detail-Seite mit Markdown-Editor/Vorschau Tabs, und konfigurierbares Vier-Augen-Prinzip.

**Architecture:** Backend-first (Model + API), dann Frontend (Typen, Service, Komponenten). Jede Task produziert lauffaehigen, testbaren Code mit Commit.

**Tech Stack:** FastAPI, SQLAlchemy, React 18, TypeScript, MUI, MarkdownRenderer (besteht bereits)

**Spec:** `docs/superpowers/specs/2026-03-18-review-workflow-enhancement-design.md`

---

## File Structure

| File | Responsibility |
|------|----------------|
| `packages/core/backend/models/auth.py` | `require_second_reviewer` Feld auf Institution |
| `packages/core/backend/api/question_review.py` | Reviewer-Join, Edit-Status-Logik, Vier-Augen-Check, Bugfixes |
| `packages/core/backend/api/admin.py` | Institution-Update erweitern |
| `packages/core/backend/tests/test_question_review.py` | **NEU** — Tests fuer Review-Workflow |
| `packages/core/frontend/src/types/review.ts` | `reviewer_info` Typ, `reviewed_by: number` Fix |
| `packages/core/frontend/src/services/ReviewService.ts` | `getQuestionDetail()` Methode |
| `packages/core/frontend/src/components/QuestionReviewCard.tsx` | Reviewer-Name, Details-Link |
| `packages/core/frontend/src/components/QuestionReviewDetail.tsx` | **NEU** — Detail-Seite |
| `packages/core/frontend/src/components/ReviewQueue.tsx` | Start-Review navigiert zur Detail-Seite |
| `packages/core/frontend/src/AppWithAuth.tsx` | Neue Route |

---

### Task 1: Institution Model — `require_second_reviewer` Feld

**Files:**
- Modify: `packages/core/backend/models/auth.py` (Institution class)

- [ ] **Step 1: Feld hinzufuegen**

In `packages/core/backend/models/auth.py`, nach dem letzten Feld der Institution-Klasse (vor `__table_args__` oder Relationships):

```python
# Review-Workflow
require_second_reviewer = Column(Boolean, default=False)
```

- [ ] **Step 2: Verifizieren**

Run: `cd packages/core/backend && python -c "from models.auth import Institution; print(hasattr(Institution, 'require_second_reviewer'))"`
Expected: `True`

- [ ] **Step 3: Commit**

```bash
git add packages/core/backend/models/auth.py
git commit -m "feat: require_second_reviewer Feld auf Institution Model"
```

---

### Task 2: Backend Bugfixes — ReviewActionRequest, Approve/Reject reviewed_by, Kommentar-Autor

**Files:**
- Modify: `packages/core/backend/api/question_review.py:61-67` (ReviewActionRequest)
- Modify: `packages/core/backend/api/question_review.py:69-78` (CommentCreate)
- Modify: `packages/core/backend/api/question_review.py:553-620` (approve_question)
- Modify: `packages/core/backend/api/question_review.py:622-700` (reject_question)
- Modify: `packages/core/backend/api/question_review.py:710-750` (add_comment)

- [ ] **Step 1: ReviewActionRequest vereinfachen**

Ersetze `ReviewActionRequest` (Zeile 61-66):

```python
class ReviewActionRequest(BaseModel):
    """Request Model fuer Review Actions (Approve/Reject)"""
    comment: Optional[str] = Field(None, max_length=2000)
    reason: Optional[str] = Field(None, max_length=500)
```

Entferne `reviewer_id` — wird nicht benoetigt, `current_user` ist massgebend.

- [ ] **Step 2: CommentCreate vereinfachen**

Ersetze `CommentCreate` (Zeile 69-77):

```python
class CommentCreate(BaseModel):
    """Request Model fuer neuen Comment"""
    comment_text: str = Field(..., min_length=1, max_length=2000)
    comment_type: str = Field(
        default="general", pattern="^(general|suggestion|issue|approval_note)$"
    )
```

Entferne `author` und `author_role` — werden serverseitig aus `current_user` gesetzt.

- [ ] **Step 3: Approve — reviewed_by nicht ueberschreiben**

In `approve_question` (ca. Zeile 575-580), aendere:

```python
# VORHER:
question.review_status = ReviewStatus.APPROVED.value
question.reviewed_by = current_user.id
question.reviewed_at = datetime.utcnow()

# NACHHER:
question.review_status = ReviewStatus.APPROVED.value
# reviewed_by bleibt unveraendert (urspruenglicher Reviewer)
question.reviewed_at = datetime.utcnow()
```

Gleiche Aenderung in `reject_question`.

- [ ] **Step 4: Kommentar-Endpunkt — Autor serverseitig setzen**

In `add_comment` Endpunkt, aendere den Comment-Erstellungscode:

```python
comment = ReviewComment(
    question_id=question.id,
    comment_text=request.comment_text,
    comment_type=request.comment_type,
    author=f"{current_user.first_name} {current_user.last_name}",
    author_role="reviewer" if current_user.id == question.reviewed_by else "user",
)
```

Gleich bei Approve/Reject Comments (ca. Zeile 596 und 676):

```python
comment = ReviewComment(
    question_id=question.id,
    comment_text=request.comment,
    comment_type="approval_note",  # oder "issue" bei reject
    author=f"{current_user.first_name} {current_user.last_name}",
    author_role="reviewer",
)
```

- [ ] **Step 5: Verifizieren**

Run: `cd packages/core/backend && python -c "from api.question_review import ReviewActionRequest; print(ReviewActionRequest.model_fields.keys())"`
Expected: `dict_keys(['comment', 'reason'])` (kein `reviewer_id`)

- [ ] **Step 6: Commit**

```bash
git add packages/core/backend/api/question_review.py
git commit -m "fix: Bugfixes im Review-Workflow (reviewed_by, Kommentar-Autor, ReviewActionRequest)"
```

---

### Task 3: Backend — Reviewer-Info Join und Response-Modell

**Files:**
- Modify: `packages/core/backend/api/question_review.py:80-106` (QuestionReviewResponse)
- Modify: `packages/core/backend/api/question_review.py:161-240` (get_review_queue)
- Modify: `packages/core/backend/api/question_review.py:290-325` (get_question_review_detail)

- [ ] **Step 1: ReviewerInfo Response-Modell hinzufuegen**

Nach `QuestionReviewResponse` (Zeile 107), fuege hinzu:

```python
class ReviewerInfo(BaseModel):
    """Reviewer User Info"""
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True
```

Und erweitere `QuestionReviewResponse`:

```python
class QuestionReviewResponse(BaseModel):
    # ... bestehende Felder ...
    reviewed_by: Optional[int]
    reviewer_info: Optional[ReviewerInfo] = None  # NEU
    reviewed_at: Optional[datetime]
    # ... rest ...
```

- [ ] **Step 2: Helper-Funktion fuer Reviewer-Info Join**

Am Anfang des Moduls (nach Imports), fuege hinzu:

```python
def _attach_reviewer_info(question: QuestionReview, db: Session) -> dict:
    """Convert QuestionReview to dict with reviewer_info joined."""
    data = {
        "id": question.id,
        "question_text": question.question_text,
        "question_type": question.question_type,
        "options": question.options,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "difficulty": question.difficulty,
        "topic": question.topic,
        "language": question.language,
        "source_chunks": question.source_chunks,
        "source_documents": question.source_documents,
        "confidence_score": question.confidence_score,
        "bloom_level": question.bloom_level,
        "estimated_time_minutes": question.estimated_time_minutes,
        "quality_tier": question.quality_tier,
        "review_status": question.review_status,
        "reviewed_by": question.reviewed_by,
        "reviewed_at": question.reviewed_at,
        "exam_id": question.exam_id,
        "created_at": question.created_at,
        "updated_at": question.updated_at,
    }
    if question.reviewed_by:
        reviewer = db.query(User).filter(User.id == question.reviewed_by).first()
        if reviewer:
            data["reviewer_info"] = {
                "id": reviewer.id,
                "first_name": reviewer.first_name,
                "last_name": reviewer.last_name,
                "email": reviewer.email,
            }
    return data
```

- [ ] **Step 3: get_review_queue — reviewer_info in Response einbauen**

In `get_review_queue`, ersetze die direkte `return question` Zeilen durch:

```python
questions = [_attach_reviewer_info(q, db) for q in question_list]
```

Und im Return:

```python
return ReviewQueueResponse(
    total=total,
    pending=pending,
    approved=approved,
    rejected=rejected,
    in_review=in_review,
    questions=questions,
)
```

- [ ] **Step 4: get_question_review_detail — reviewer_info einbauen**

Analog Step 3.

- [ ] **Step 5: approve/reject/start-review — reviewer_info im Return**

In allen drei Endpunkten, ersetze `return question` durch:

```python
return _attach_reviewer_info(question, db)
```

- [ ] **Step 6: Verifizieren**

Run: `cd packages/core/backend && python -c "from api.question_review import ReviewerInfo; print(ReviewerInfo.model_fields.keys())"`
Expected: `dict_keys(['id', 'first_name', 'last_name', 'email'])`

- [ ] **Step 7: Commit**

```bash
git add packages/core/backend/api/question_review.py
git commit -m "feat: reviewer_info Join in Review-API Responses"
```

---

### Task 4: Backend — Vier-Augen-Prinzip und Edit-Status-Logik

**Files:**
- Modify: `packages/core/backend/api/question_review.py` (approve_question, edit_question)

- [ ] **Step 1: Vier-Augen-Check in approve_question**

Nach dem Question-Lookup, vor dem Status-Update, fuege ein:

```python
# Vier-Augen-Prinzip Check
if question.institution_id and question.reviewed_by:
    from models.auth import Institution
    institution = db.query(Institution).filter(
        Institution.id == question.institution_id
    ).first()
    if (
        institution
        and institution.require_second_reviewer
        and current_user.id == question.reviewed_by
    ):
        raise HTTPException(
            status_code=403,
            detail="Vier-Augen-Prinzip: Ein anderer Reviewer muss diese Frage genehmigen.",
        )
```

- [ ] **Step 2: Edit-Status-Logik anpassen**

In `edit_question`, aendere den Status-Block (ca. Zeile 451-453):

```python
# VORHER:
if changed_fields:
    question.review_status = ReviewStatus.EDITED.value

# NACHHER:
if changed_fields:
    # Reviewer-eigene Edits bleiben in_review
    if (
        question.review_status == ReviewStatus.IN_REVIEW.value
        and current_user.id == question.reviewed_by
    ):
        pass  # Status bleibt in_review
    else:
        question.review_status = ReviewStatus.EDITED.value
```

- [ ] **Step 3: Verifizieren (Syntax-Check)**

Run: `cd packages/core/backend && python -c "from api.question_review import router; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add packages/core/backend/api/question_review.py
git commit -m "feat: Vier-Augen-Prinzip und Edit-Status-Logik fuer Reviewer"
```

---

### Task 5: Backend — Admin-Endpoint fuer require_second_reviewer

**Files:**
- Modify: `packages/core/backend/api/admin.py`

- [ ] **Step 1: Institution-Update erweitern**

Suche den Institution-Update-Endpoint in `admin.py`. Fuege `require_second_reviewer` zum Request-Model und Update-Logik hinzu:

```python
# Im InstitutionUpdateRequest (oder aehnlich):
require_second_reviewer: Optional[bool] = None

# In der Update-Logik:
if request.require_second_reviewer is not None:
    institution.require_second_reviewer = request.require_second_reviewer
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/backend/api/admin.py
git commit -m "feat: require_second_reviewer in Institution Admin-API"
```

---

### Task 6: Frontend — TypeScript-Typen und ReviewService

**Files:**
- Modify: `packages/core/frontend/src/types/review.ts` (oder `document.ts` wo QuestionReview definiert ist)
- Modify: `packages/core/frontend/src/services/ReviewService.ts`

- [ ] **Step 1: ReviewerInfo Typ und QuestionReview erweitern**

Suche die `QuestionReview` Interface-Definition. Fuege hinzu:

```typescript
export interface ReviewerInfo {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
}

// In QuestionReview Interface:
export interface QuestionReview {
  // ... bestehende Felder ...
  reviewed_by?: number;  // Fix: war string, ist int
  reviewer_info?: ReviewerInfo;  // NEU
  // ...
}
```

- [ ] **Step 2: ReviewService.getQuestionDetail()**

In `ReviewService.ts`, fuege hinzu:

```typescript
static async getQuestionDetail(questionId: number): Promise<QuestionReview> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/questions/${questionId}/review`,
    { headers: this.getAuthHeaders() }
  );

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `Failed to load question: ${response.statusText}`);
  }

  return response.json();
}
```

- [ ] **Step 3: ReviewActionRequest anpassen**

Entferne `reviewer_id` aus dem Frontend-Typ:

```typescript
export interface ReviewActionRequest {
  comment?: string;
  reason?: string;
}
```

Und in `CommentCreate`:

```typescript
export interface CommentCreate {
  comment_text: string;
  comment_type?: string;
}
```

- [ ] **Step 4: Commit**

```bash
git add packages/core/frontend/src/types/ packages/core/frontend/src/services/ReviewService.ts
git commit -m "feat: ReviewerInfo Typ und getQuestionDetail im ReviewService"
```

---

### Task 7: Frontend — QuestionReviewCard Anpassungen

**Files:**
- Modify: `packages/core/frontend/src/components/QuestionReviewCard.tsx`

- [ ] **Step 1: Reviewer-Name anzeigen**

Nach dem Status-Chip, fuege hinzu:

```tsx
{question.reviewer_info && (
  <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
    Reviewer: {question.reviewer_info.first_name} {question.reviewer_info.last_name}
  </Typography>
)}
```

- [ ] **Step 2: Details-Link hinzufuegen**

Importiere `useNavigate` und fuege einen "Details"-Button in den CardActions hinzu:

```tsx
import { useNavigate } from 'react-router-dom';
// ...
const navigate = useNavigate();
// ...
// In CardActions, nach den Approve/Reject Buttons:
<Tooltip title="Details anzeigen">
  <IconButton
    onClick={() => navigate(`/questions/review/${question.id}`)}
    size="small"
  >
    <Visibility />
  </IconButton>
</Tooltip>
```

Importiere `Visibility` von `@mui/icons-material`.

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/components/QuestionReviewCard.tsx
git commit -m "feat: Reviewer-Name und Details-Link in QuestionReviewCard"
```

---

### Task 8: Frontend — QuestionReviewDetail Seite (NEU)

**Files:**
- Create: `packages/core/frontend/src/components/QuestionReviewDetail.tsx`

- [ ] **Step 1: Grundstruktur mit Loading/Error States**

```tsx
import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box, Typography, Paper, Button, Tabs, Tab, TextField,
  Alert, CircularProgress, Chip, Grid, Card, CardContent,
  FormControl, InputLabel, Select, MenuItem, Divider,
} from '@mui/material';
import { ArrowBack, Save, CheckCircle, Cancel } from '@mui/icons-material';
import { ReviewService } from '../services/ReviewService';
import { useAuth } from '../contexts/AuthContext';
import MarkdownRenderer from './MarkdownRenderer';
import { QuestionReview, ReviewStatus } from '../types/review';

const QuestionReviewDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user: currentUser } = useAuth();

  const [question, setQuestion] = useState<QuestionReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(0);

  // Editable fields (only for reviewer)
  const [editData, setEditData] = useState({
    question_text: '',
    correct_answer: '',
    explanation: '',
    difficulty: 'medium',
    bloom_level: undefined as number | undefined,
    estimated_time_minutes: undefined as number | undefined,
  });

  // Comment
  const [commentText, setCommentText] = useState('');

  const isReviewer = currentUser && question
    && currentUser.id === question.reviewed_by;

  const loadQuestion = useCallback(async () => {
    if (!id) return;
    try {
      setLoading(true);
      setError(null);
      const data = await ReviewService.getQuestionDetail(parseInt(id));
      setQuestion(data);
      setEditData({
        question_text: data.question_text,
        correct_answer: data.correct_answer || '',
        explanation: data.explanation || '',
        difficulty: data.difficulty,
        bloom_level: data.bloom_level ?? undefined,
        estimated_time_minutes: data.estimated_time_minutes ?? undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Frage nicht gefunden');
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadQuestion();
  }, [loadQuestion]);

  const handleSave = async () => {
    if (!question) return;
    try {
      setSaving(true);
      setError(null);
      await ReviewService.editQuestion(question.id, editData);
      setSuccess('Aenderungen gespeichert');
      await loadQuestion();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Speichern');
    } finally {
      setSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!question) return;
    try {
      setSaving(true);
      await ReviewService.approveQuestion(question.id, {});
      setSuccess('Frage genehmigt');
      await loadQuestion();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Genehmigen');
    } finally {
      setSaving(false);
    }
  };

  const handleReject = async () => {
    if (!question) return;
    try {
      setSaving(true);
      await ReviewService.rejectQuestion(question.id, {});
      setSuccess('Frage abgelehnt');
      await loadQuestion();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ablehnen');
    } finally {
      setSaving(false);
    }
  };

  const handleAddComment = async () => {
    if (!question || !commentText.trim()) return;
    try {
      await ReviewService.addComment(question.id, {
        comment_text: commentText.trim(),
        comment_type: 'general',
      });
      setCommentText('');
      await loadQuestion();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fehler beim Kommentieren');
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error && !question) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={() => navigate('/questions/review')}>
            Zurueck zur Queue
          </Button>
        }>
          {error}
        </Alert>
      </Box>
    );
  }

  if (!question) return null;

  return (
    <Box sx={{ maxWidth: 1000, mx: 'auto', p: 3 }}>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/questions/review')}>
            Zurueck
          </Button>
          <Typography variant="h5">
            Question #{question.id} · {question.question_type.replace('_', ' ')}
          </Typography>
        </Box>
        <Chip
          label={question.review_status.toUpperCase()}
          color={
            question.review_status === ReviewStatus.APPROVED ? 'success' :
            question.review_status === ReviewStatus.REJECTED ? 'error' :
            question.review_status === ReviewStatus.IN_REVIEW ? 'info' :
            'warning'
          }
        />
      </Box>

      {/* Reviewer Info */}
      {question.reviewer_info && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Reviewer: {question.reviewer_info.first_name} {question.reviewer_info.last_name}
        </Typography>
      )}

      {/* Alerts */}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      {/* Main Content */}
      <Paper sx={{ p: 3, mb: 3 }}>
        {isReviewer ? (
          <>
            <Tabs value={activeTab} onChange={(_, v) => setActiveTab(v)} sx={{ mb: 2 }}>
              <Tab label="Bearbeiten" />
              <Tab label="Vorschau" />
            </Tabs>

            {activeTab === 0 ? (
              /* Edit Tab */
              <Box>
                <Typography variant="subtitle2" sx={{ mb: 1 }}>Fragetext (Markdown)</Typography>
                <TextField
                  fullWidth multiline minRows={6}
                  value={editData.question_text}
                  onChange={(e) => setEditData(prev => ({ ...prev, question_text: e.target.value }))}
                  sx={{ mb: 3, '& textarea': { fontFamily: 'monospace', fontSize: '0.9rem' } }}
                />

                <Typography variant="subtitle2" sx={{ mb: 1 }}>Musterantwort (Markdown)</Typography>
                <TextField
                  fullWidth multiline minRows={3}
                  value={editData.correct_answer}
                  onChange={(e) => setEditData(prev => ({ ...prev, correct_answer: e.target.value }))}
                  sx={{ mb: 3, '& textarea': { fontFamily: 'monospace', fontSize: '0.9rem' } }}
                />

                <Typography variant="subtitle2" sx={{ mb: 1 }}>Erklaerung (Markdown)</Typography>
                <TextField
                  fullWidth multiline minRows={3}
                  value={editData.explanation}
                  onChange={(e) => setEditData(prev => ({ ...prev, explanation: e.target.value }))}
                  sx={{ mb: 3, '& textarea': { fontFamily: 'monospace', fontSize: '0.9rem' } }}
                />

                <Divider sx={{ my: 2 }} />

                <Grid container spacing={2}>
                  <Grid item xs={4}>
                    <FormControl fullWidth size="small">
                      <InputLabel>Schwierigkeit</InputLabel>
                      <Select
                        value={editData.difficulty}
                        label="Schwierigkeit"
                        onChange={(e) => setEditData(prev => ({ ...prev, difficulty: e.target.value }))}
                      >
                        <MenuItem value="easy">Einfach</MenuItem>
                        <MenuItem value="medium">Mittel</MenuItem>
                        <MenuItem value="hard">Schwer</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                  <Grid item xs={4}>
                    <TextField
                      fullWidth size="small" type="number"
                      label="Bloom Level (1-6)"
                      value={editData.bloom_level ?? ''}
                      onChange={(e) => setEditData(prev => ({
                        ...prev,
                        bloom_level: e.target.value ? parseInt(e.target.value) : undefined,
                      }))}
                      inputProps={{ min: 1, max: 6 }}
                    />
                  </Grid>
                  <Grid item xs={4}>
                    <TextField
                      fullWidth size="small" type="number"
                      label="Geschaetzte Zeit (Min)"
                      value={editData.estimated_time_minutes ?? ''}
                      onChange={(e) => setEditData(prev => ({
                        ...prev,
                        estimated_time_minutes: e.target.value ? parseInt(e.target.value) : undefined,
                      }))}
                      inputProps={{ min: 1, max: 180 }}
                    />
                  </Grid>
                </Grid>
              </Box>
            ) : (
              /* Preview Tab */
              <Box>
                <MarkdownRenderer content={question.question_text} />
                {question.correct_answer && (
                  <Alert severity="success" sx={{ mt: 2 }}>
                    <Typography variant="subtitle2">Musterantwort</Typography>
                    <MarkdownRenderer content={question.correct_answer} />
                  </Alert>
                )}
                {question.explanation && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2">Erklaerung</Typography>
                    <MarkdownRenderer content={question.explanation} />
                  </Box>
                )}
              </Box>
            )}
          </>
        ) : (
          /* Read-only view for non-reviewers */
          <Box>
            <MarkdownRenderer content={question.question_text} />
            {question.correct_answer && (
              <Alert severity="success" sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Musterantwort</Typography>
                <MarkdownRenderer content={question.correct_answer} />
              </Alert>
            )}
            {question.explanation && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Erklaerung</Typography>
                <MarkdownRenderer content={question.explanation} />
              </Box>
            )}
          </Box>
        )}
      </Paper>

      {/* Actions (reviewer only) */}
      {isReviewer && (
        <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
          <Button variant="contained" startIcon={<Save />} onClick={handleSave} disabled={saving}>
            Speichern
          </Button>
          <Button
            variant="contained" color="success" startIcon={<CheckCircle />}
            onClick={handleApprove} disabled={saving || question.review_status === ReviewStatus.APPROVED}
          >
            Approve
          </Button>
          <Button
            variant="contained" color="error" startIcon={<Cancel />}
            onClick={handleReject} disabled={saving || question.review_status === ReviewStatus.REJECTED}
          >
            Reject
          </Button>
        </Box>
      )}

      {/* Comments Section (all users) */}
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>Kommentare</Typography>

        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth size="small"
            placeholder="Kommentar hinzufuegen..."
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleAddComment()}
          />
          <Button variant="contained" onClick={handleAddComment} disabled={!commentText.trim()}>
            Senden
          </Button>
        </Box>

        {question.comments?.map((comment: any) => (
          <Card key={comment.id} variant="outlined" sx={{ mb: 1 }}>
            <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
              <Typography variant="body2">
                <strong>{comment.author}</strong> · {new Date(comment.created_at).toLocaleString('de-CH')}
              </Typography>
              <Typography variant="body2">{comment.comment_text}</Typography>
            </CardContent>
          </Card>
        ))}
      </Paper>
    </Box>
  );
};

export default QuestionReviewDetail;
```

- [ ] **Step 2: Commit**

```bash
git add packages/core/frontend/src/components/QuestionReviewDetail.tsx
git commit -m "feat: QuestionReviewDetail Seite mit rollenbasierter Ansicht"
```

---

### Task 9: Frontend — Route und Navigation

**Files:**
- Modify: `packages/core/frontend/src/AppWithAuth.tsx`
- Modify: `packages/core/frontend/src/components/ReviewQueue.tsx`

- [ ] **Step 1: Route hinzufuegen**

In `AppWithAuth.tsx`, nach der bestehenden `/questions/review` Route:

```tsx
import QuestionReviewDetail from './components/QuestionReviewDetail';

// Nach der /questions/review Route:
<Route
  path="/questions/review/:id"
  element={
    <ProtectedRoute>
      <AppLayout>
        <QuestionReviewDetail />
      </AppLayout>
    </ProtectedRoute>
  }
/>
```

- [ ] **Step 2: Start-Review navigiert zur Detail-Seite**

In `ReviewQueue.tsx`, aendere `handleStartReview`:

```tsx
const handleStartReview = async (questionId: number) => {
  try {
    setLoading(true);
    await ReviewService.startReview(questionId);
    navigate(`/questions/review/${questionId}`);
  } catch (err) {
    setError(err instanceof Error ? err.message : 'Fehler beim Starten des Reviews');
  } finally {
    setLoading(false);
  }
};
```

Importiere `useNavigate`:

```tsx
import { useNavigate, useSearchParams } from 'react-router-dom';
const navigate = useNavigate();
```

- [ ] **Step 3: Commit**

```bash
git add packages/core/frontend/src/AppWithAuth.tsx packages/core/frontend/src/components/ReviewQueue.tsx
git commit -m "feat: Route und Navigation fuer QuestionReviewDetail"
```

---

### Task 10: Manueller E2E-Test

- [ ] **Step 1: Docker-Stack neustarten**

```bash
./start-dev.sh --full
```

- [ ] **Step 2: Workflow durchspielen**

1. Frage generieren via Question Generation
2. Review Queue oeffnen — Frage ist PENDING
3. "Review starten" klicken — Status wechselt auf IN_REVIEW, navigiert zur Detail-Seite
4. Detail-Seite: Tabs "Bearbeiten" / "Vorschau" sichtbar
5. Markdown editieren und speichern — Status bleibt IN_REVIEW
6. "Approve" klicken — Status wechselt auf APPROVED
7. Zurueck zur Queue — Reviewer-Name wird in der Karte angezeigt

- [ ] **Step 3: Vier-Augen-Prinzip testen (optional)**

1. Admin: Institution `require_second_reviewer = true` setzen
2. User A: Review starten + editieren + Approve klicken → 403 erwartet
3. User B: Approve klicken → erfolgreich
