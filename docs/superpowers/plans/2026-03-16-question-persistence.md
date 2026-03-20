# TF-219: Auto-Persistierung generierter Fragen Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** After question generation, automatically persist questions to the `question_reviews` table and redirect the user to the review workflow instead of showing questions inline.

**Architecture:** The `generate-exam` endpoint in `rag_exams.py` gets a post-generation persistence step that creates `QuestionReview` + `ReviewHistory` records. The response model gains `review_question_ids`. The frontend `RAGExamCreator` replaces its Step 4 (results with download) with a summary card + "Zum Review" navigation button.

**Tech Stack:** FastAPI, SQLAlchemy, React 18, MUI, TypeScript

**Spec:** `docs/superpowers/specs/2026-03-16-question-persistence-design.md`

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `packages/core/backend/api/rag_exams.py` | Modify | Add quota check, persist questions, extend response model |
| `packages/core/backend/tests/test_rag_api.py` | Modify | Add tests for persistence, quota check, history entries |
| `packages/core/frontend/src/types/document.ts` | Modify | Add `review_question_ids` to `RAGExamResponse` interface |
| `packages/premium/frontend/src/components/RAGExamCreator.tsx` | Modify | Replace Step 4 results with summary + review redirect |
| `packages/premium/frontend/src/components/RAGExamCreator.test.tsx` | Modify | Update tests for new Step 4 behavior |

---

## Task 1: Backend — Persist generated questions

**Files:**
- Modify: `packages/core/backend/tests/test_rag_api.py`
- Modify: `packages/core/backend/api/rag_exams.py`

### Step 1.1: Write failing test for question persistence

- [ ] Add test to `test_rag_api.py` that verifies questions are saved to `question_reviews` after generation.

The existing tests mock auth away implicitly. For our persistence test, we need a mock `current_user` with `id` and `institution_id` since the endpoint writes these to the DB. Follow the `test_api_documents.py` pattern using `app.dependency_overrides`.

```python
# Add at the top of test_rag_api.py, after existing imports:
from models.question_review import QuestionReview, ReviewHistory

class TestRAGQuestionPersistence:
    """Tests for auto-persistence of generated questions to question_reviews"""

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user with institution"""
        mock_institution = Mock()
        mock_institution.id = 1
        mock_institution.name = "Test University"
        mock_institution.slug = "test-university"
        mock_institution.subscription_tier = "professional"
        mock_institution.max_users = 100
        mock_institution.max_documents = 1000
        mock_institution.max_questions_per_month = -1  # unlimited

        user = Mock()
        user.id = 42
        user.email = "dozent@example.com"
        user.institution_id = 1
        user.institution = mock_institution
        user.has_permission = Mock(return_value=True)
        user.is_superuser = False
        user.roles = []
        return user

    @pytest.fixture
    def auth_client(self, mock_user):
        """TestClient with mocked auth dependencies"""
        from utils.auth_utils import get_current_user, get_current_active_user

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_user] = lambda: mock_user

        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()

    @pytest.fixture
    def sample_rag_response(self):
        """Reuse existing fixture pattern"""
        context = RAGContext(
            query="Test Topic",
            retrieved_chunks=[],
            total_similarity_score=1.5,
            source_documents=[{"id": 1, "filename": "test.txt", "chunks_used": 2}],
            context_length=150,
        )
        return RAGExamResponse(
            exam_id="persist_test_exam_001",
            topic="Test Topic",
            questions=[
                RAGQuestion(
                    question_text="Was ist Unit Testing?",
                    question_type="multiple_choice",
                    options=["A) Spass", "B) Qualitaet", "C) Zeitverschwendung", "D) Kunst"],
                    correct_answer="B",
                    explanation="Unit Testing sichert Qualitaet",
                    difficulty="medium",
                    source_chunks=["chunk_1"],
                    source_documents=["test.txt"],
                    confidence_score=0.85,
                ),
                RAGQuestion(
                    question_text="Erklaeren Sie TDD.",
                    question_type="open_ended",
                    correct_answer="TDD ist test-getriebene Entwicklung...",
                    explanation="Vollstaendigkeit und Verstaendnis",
                    difficulty="medium",
                    source_chunks=["chunk_2"],
                    source_documents=["test.txt"],
                    confidence_score=0.78,
                ),
            ],
            context_summary=context,
            generation_time=2.5,
            quality_metrics={"total_questions": 2, "average_confidence": 0.815},
        )

    def test_generate_exam_returns_review_question_ids(
        self, auth_client, sample_rag_response
    ):
        """Generated questions must be persisted and their IDs returned"""
        with (
            patch("api.rag_exams.document_service") as mock_doc_svc,
            patch("services.rag_service.rag_service") as mock_rag_svc,
        ):
            mock_doc_svc.get_document_by_id.return_value = None  # no doc validation
            mock_rag_svc.generate_rag_exam = AsyncMock(return_value=sample_rag_response)

            response = auth_client.post(
                "/api/v1/rag/generate-exam",
                json={"topic": "Test Topic", "question_count": 2},
            )

        assert response.status_code == 200
        data = response.json()
        assert "review_question_ids" in data
        assert len(data["review_question_ids"]) == 2
        assert all(isinstance(qid, int) for qid in data["review_question_ids"])

    def test_generate_exam_persists_question_reviews(
        self, mock_user, sample_rag_response
    ):
        """QuestionReview records must exist in DB after generation"""
        from utils.auth_utils import get_current_user, get_current_active_user
        from database import get_db

        # Create a mock DB session that captures add() calls
        mock_db = Mock()
        added_objects = []
        mock_db.add = lambda obj: added_objects.append(obj)
        mock_db.commit = Mock()
        mock_db.flush = Mock()

        # Override FastAPI dependencies (correct pattern for DI)
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_current_active_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: mock_db

        try:
            with (
                patch("api.rag_exams.document_service") as mock_doc_svc,
                patch("services.rag_service.rag_service") as mock_rag_svc,
            ):
                mock_doc_svc.get_document_by_id.return_value = None
                mock_rag_svc.generate_rag_exam = AsyncMock(return_value=sample_rag_response)

                client = TestClient(app)
                response = client.post(
                    "/api/v1/rag/generate-exam",
                    json={"topic": "Test Topic", "question_count": 2},
                )
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200

        # Verify QuestionReview objects were added
        question_reviews = [o for o in added_objects if isinstance(o, QuestionReview)]
        assert len(question_reviews) == 2

        # Verify fields mapped correctly
        q1 = question_reviews[0]
        assert q1.question_text == "Was ist Unit Testing?"
        assert q1.question_type == "multiple_choice"
        assert q1.review_status == "pending"
        assert q1.topic == "Test Topic"
        assert q1.exam_id == "persist_test_exam_001"
        assert q1.created_by == 42
        assert q1.institution_id == 1

        # Verify ReviewHistory objects were added
        history_entries = [o for o in added_objects if isinstance(o, ReviewHistory)]
        assert len(history_entries) == 2
        assert all(h.action == "created" for h in history_entries)
```

### Step 1.2: Run test to verify it fails

- [ ] Run: `cd packages/core/backend && python -m pytest tests/test_rag_api.py::TestRAGQuestionPersistence -v`

Expected: FAIL — `review_question_ids` not in response, no `QuestionReview` objects added.

### Step 1.3: Implement persistence in rag_exams.py

- [ ] Add imports and extend `RAGExamResponseModel`, then add persistence logic after line 202.

Add these imports at the top of `rag_exams.py` (after existing imports):

```python
from models.question_review import QuestionReview, ReviewHistory, ReviewStatus
```

Extend `RAGExamResponseModel` (add field after `quality_metrics`):

```python
class RAGExamResponseModel(BaseModel):
    """Response Model für RAG-Prüfung"""

    exam_id: str
    topic: str
    questions: List[RAGQuestionResponse]
    context_summary: RAGContextResponse
    generation_time: float
    quality_metrics: Dict[str, Any]
    review_question_ids: List[int] = []
```

In `generate_rag_exam()`, add quota check **before** the RAG service call (before the `rag_request = RAGExamRequest(...)` block). The `check_question_limit` method already raises `HTTPException(403)` directly, so no try/except wrapper is needed -- it will propagate to the existing `except HTTPException: raise` handler at the end of the function:

```python
        # Quota-Check vor Generierung (verhindert unnoetige Claude-API-Kosten)
        from utils.tenant_utils import SubscriptionLimits
        SubscriptionLimits.check_question_limit(current_user.institution, db)
```

After `rag_response = await rag_service_module.rag_service.generate_rag_exam(rag_request)` (line 202), add persistence before the response conversion loop:

```python
        # Persistiere generierte Fragen in question_reviews
        review_question_ids = []
        for question in rag_response.questions:
            question_review = QuestionReview(
                question_text=question.question_text,
                question_type=question.question_type,
                options=question.options,
                correct_answer=question.correct_answer,
                explanation=question.explanation if isinstance(question.explanation, str) else str(question.explanation) if question.explanation else None,
                difficulty=question.difficulty,
                topic=request.topic,
                language=request.language,
                source_chunks=question.source_chunks,
                source_documents=question.source_documents,
                confidence_score=question.confidence_score,
                review_status=ReviewStatus.PENDING.value,
                exam_id=rag_response.exam_id,
                created_by=current_user.id,
                institution_id=current_user.institution_id,
            )
            db.add(question_review)
            db.flush()  # Get the auto-generated ID

            history = ReviewHistory(
                question_id=question_review.id,
                action="created",
                new_status=ReviewStatus.PENDING.value,
                changed_by=str(current_user.id),
                change_reason="Auto-generated via RAG exam generation",
            )
            db.add(history)
            review_question_ids.append(question_review.id)

        db.commit()
```

**Note on `explanation` field:** The `RAGQuestion.explanation` field can be either a `str` or a `list` (e.g. `["Verstaendnis", "Vollstaendigkeit"]` for open-ended questions). The `isinstance` check with `str()` fallback produces a Python repr like `"['a', 'b']"` in the DB. This is a pre-existing type inconsistency in the RAG response -- acceptable for now but worth a follow-up cleanup.

Update the response construction (around line 229) to include `review_question_ids`:

```python
        response = RAGExamResponseModel(
            exam_id=rag_response.exam_id,
            topic=rag_response.topic,
            questions=questions_response,
            context_summary=context_response,
            generation_time=rag_response.generation_time,
            quality_metrics=rag_response.quality_metrics,
            review_question_ids=review_question_ids,
        )
```

### Step 1.4: Run tests to verify they pass

- [ ] Run: `cd packages/core/backend && python -m pytest tests/test_rag_api.py::TestRAGQuestionPersistence -v`

Expected: PASS

- [ ] Also run existing tests to ensure no regression: `cd packages/core/backend && python -m pytest tests/test_rag_api.py -v`

Expected: All existing tests still PASS. The `review_question_ids` field defaults to `[]` so existing response assertions are unaffected.

### Step 1.5: Commit

- [ ] Commit backend changes:

```bash
git add packages/core/backend/api/rag_exams.py packages/core/backend/tests/test_rag_api.py
git commit -m "feat(TF-219): Auto-persist generated questions to question_reviews

After RAG exam generation, questions are automatically saved to the
question_reviews table with status 'pending'. Each question gets a
ReviewHistory 'created' entry. Quota check runs before Claude API call.
Response now includes review_question_ids for frontend navigation."
```

---

## Task 2: Frontend — Replace results with summary + review redirect

**Files:**
- Modify: `packages/premium/frontend/src/components/RAGExamCreator.tsx`
- Modify: `packages/premium/frontend/src/components/RAGExamCreator.test.tsx`

### Step 2.1: Check existing test file

- [ ] Read `packages/premium/frontend/src/components/RAGExamCreator.test.tsx` to understand existing test patterns.

### Step 2.2: Replace Step 4 in RAGExamCreator.tsx

- [ ] Replace the Step 4 content (lines 665-758) with a summary card + review redirect. Remove the `showExamDisplay` state, `handleExportExam` function, `RAGExamDisplay` import, and `Download` icon import.

Remove from imports:
- `Download` from `@mui/icons-material`
- `import RAGExamDisplay from './RAGExamDisplay';`

Remove state/functions:
- `const [showExamDisplay, setShowExamDisplay] = useState(false);`
- The entire `handleExportExam` function (lines 271-288)
- The `showExamDisplay && generatedExam` early return block (lines 308-317)

Add import for navigation:
```typescript
import { useNavigate } from 'react-router-dom';
```

Add `useNavigate` inside the component (after `const [activeStep, setActiveStep] = useState(0);`):
```typescript
const navigate = useNavigate();
```

Replace Step 4 content (the `{generatedExam && (...)}` block inside `<StepContent>`) with:

```tsx
              {generatedExam && (
                <Box>
                  <Alert severity="success" sx={{ mb: 2 }}>
                    <Typography variant="h6">
                      Pruefung erfolgreich generiert!
                    </Typography>
                    <Typography variant="body2">
                      {generatedExam.questions.length} Fragen wurden generiert und zur Ueberpruefung gespeichert.
                    </Typography>
                  </Alert>

                  {/* Summary Stats */}
                  <Card sx={{ mb: 2 }}>
                    <CardContent>
                      <Grid container spacing={2}>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Generierte Fragen
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {generatedExam.questions.length}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Generierungsdauer
                          </Typography>
                          <Typography variant="h6" color="primary">
                            {generatedExam.generation_time.toFixed(1)}s
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Thema
                          </Typography>
                          <Typography variant="h6" color="primary" noWrap>
                            {generatedExam.topic}
                          </Typography>
                        </Grid>
                        <Grid item xs={6} md={3}>
                          <Typography variant="body2" color="text.secondary">
                            Status
                          </Typography>
                          <Typography variant="h6" color="warning.main">
                            Pending Review
                          </Typography>
                        </Grid>
                      </Grid>
                    </CardContent>
                  </Card>

                  <Alert severity="info" sx={{ mb: 2 }}>
                    Die Fragen befinden sich im Status <strong>Pending</strong> und
                    muessen im Review-Workflow ueberprueft und genehmigt werden.
                  </Alert>

                  {/* Actions */}
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Button
                      variant="contained"
                      size="large"
                      onClick={() => navigate(`/questions/review?exam_id=${generatedExam.exam_id}`)}
                    >
                      Zum Review-Workflow
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={() => {
                        setActiveStep(0);
                        setGeneratedExam(null);
                        setContextPreview(null);
                      }}
                    >
                      Neue Pruefung erstellen
                    </Button>
                  </Box>
                </Box>
              )}
```

### Step 2.3: Update RAGExamResponse type

- [ ] Add `review_question_ids` to the `RAGExamResponse` interface in `packages/core/frontend/src/types/document.ts:102-117`.

The type is imported by the premium component via `import { ... RAGExamResponse ... } from '@examcraft/core';`. The field is optional for backwards compatibility.

Change in `packages/core/frontend/src/types/document.ts`:

```typescript
export interface RAGExamResponse {
  exam_id: string;
  topic: string;
  questions: RAGQuestion[];
  context_summary: RAGContextSummary;
  generation_time: number;
  quality_metrics: {
    total_questions: number;
    average_confidence: number;
    source_coverage: number;
    question_type_distribution: Record<string, number>;
    context_chunks_used: number;
    total_context_length: number;
    average_similarity_score: number;
  };
  review_question_ids?: number[];
}
```

### Step 2.4: Update frontend tests

- [ ] In `packages/premium/frontend/src/components/RAGExamCreator.test.tsx`, update the tests for the new Step 4 behavior. The existing `describe('Export Functionality')` and `describe('Fix #12: State Management for Exam Display')` test blocks test removed functionality and must be replaced.

First, add `review_question_ids` to the mock response (around line 104):

```typescript
const mockRAGExamResponse: RAGExamResponse = {
  // ... existing fields stay the same ...
  review_question_ids: [1, 2, 3],
};
```

Then add `MemoryRouter` to imports and wrap the test component (the `useNavigate` hook requires a router context):

```typescript
import { MemoryRouter } from 'react-router-dom';

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <MemoryRouter>
    <ThemeProvider theme={theme}>
      {children}
    </ThemeProvider>
  </MemoryRouter>
);
```

Replace the `describe('Export Functionality')` block (lines 550-648) with:

```typescript
  describe('Review Redirect', () => {
    const navigateToResultStep = async () => {
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      render(
        <TestWrapper>
          <RAGExamCreator />
        </TestWrapper>
      );

      await waitFor(() => {
        const documentCard = screen.getByText('test-document.pdf').closest('[role="button"]');
        fireEvent.click(documentCard!);
        fireEvent.click(screen.getByText('Weiter'));
      });

      const topicInput = screen.getByLabelText('Pruefungsthema');
      fireEvent.change(topicInput, { target: { value: 'Test Topic' } });
      fireEvent.click(screen.getByText('Weiter'));

      const mockContextPreview = {
        context: mockRAGExamResponse.context_summary,
        preview_text: 'Test preview text',
        estimated_questions: 3
      };
      mockRAGService.previewContext.mockResolvedValue(mockContextPreview);

      const previewButton = screen.getByText('Kontext-Vorschau laden');
      fireEvent.click(previewButton);

      await waitFor(() => {
        const generateButton = screen.getByText('Pruefung generieren');
        fireEvent.click(generateButton);
      });

      await waitFor(() => {
        expect(screen.getByText(/erfolgreich generiert/)).toBeInTheDocument();
      });
    };

    it('shows summary card instead of question list', async () => {
      await navigateToResultStep();
      expect(screen.getByText('Generierte Fragen')).toBeInTheDocument();
      expect(screen.getByText('Generierungsdauer')).toBeInTheDocument();
      expect(screen.getByText('Pending Review')).toBeInTheDocument();
    });

    it('shows "Zum Review-Workflow" button', async () => {
      await navigateToResultStep();
      expect(screen.getByText('Zum Review-Workflow')).toBeInTheDocument();
    });

    it('does NOT show export buttons', async () => {
      await navigateToResultStep();
      expect(screen.queryByText('Als JSON exportieren')).not.toBeInTheDocument();
      expect(screen.queryByText('Als Markdown exportieren')).not.toBeInTheDocument();
      expect(screen.queryByText('Pruefung anzeigen')).not.toBeInTheDocument();
    });

    it('allows creating a new exam', async () => {
      await navigateToResultStep();
      fireEvent.click(screen.getByText('Neue Pruefung erstellen'));
      expect(screen.getByText('Dokumente auswaehlen')).toBeInTheDocument();
    });
  });
```

Remove the `describe('Fix #12: State Management for Exam Display')` block entirely (lines 764-859) -- it tests `RAGExamDisplay` and `showExamDisplay` which are removed.

Update the success message assertion in `describe('Exam Generation')` test `it('generates RAG exam successfully')` to match the new text:

```typescript
    it('generates RAG exam successfully', async () => {
      await navigateToExamGeneration();
      mockRAGService.generateRAGExam.mockResolvedValue(mockRAGExamResponse);

      const generateButton = screen.getByText('Pruefung generieren');
      fireEvent.click(generateButton);

      await waitFor(() => {
        expect(mockRAGService.generateRAGExam).toHaveBeenCalled();
        expect(screen.getByText(/erfolgreich generiert/)).toBeInTheDocument();
      });
    });
```

Remove the `it('shows quality metrics after generation')` test -- quality metrics card is removed in the new UI.

### Step 2.5: Run frontend tests

- [ ] Run: `cd packages/premium/frontend && bun test -- --watchAll=false`

Expected: All tests PASS.

### Step 2.6: Commit

- [ ] Commit frontend changes:

```bash
git add packages/core/frontend/src/types/document.ts packages/premium/frontend/src/components/RAGExamCreator.tsx packages/premium/frontend/src/components/RAGExamCreator.test.tsx
git commit -m "feat(TF-219): Replace question display with review redirect

After generation, RAGExamCreator shows a summary card with stats
(count, duration, topic, status) and a 'Zum Review-Workflow' button
that navigates to /questions/review?exam_id={id}. Removes inline
question display, export buttons, and RAGExamDisplay dependency."
```

---

## Task 3: Integration verification

### Step 3.1: Run full backend test suite

- [ ] Run: `cd packages/core/backend && python -m pytest tests/ -v --tb=short`

Expected: All tests PASS with no regressions.

### Step 3.2: Run ruff checks

- [ ] Run: `ruff check packages/core/backend/api/rag_exams.py && ruff format --check packages/core/backend/api/rag_exams.py`

Expected: No issues.

### Step 3.3: Final commit with Linear issue reference

- [ ] If any formatting fixes were needed, commit them:

```bash
git commit -m "chore(TF-219): Format and lint fixes"
```
