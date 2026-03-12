# Testing Strategy - ExamCraft AI

## Übersicht

Umfassende Test-Strategie für ExamCraft AI mit Unit-, Integration- und E2E-Tests.

## Test-Pyramide

```
        /\
       /  \
      / E2E \          <- Wenige, kritische User-Flows
     /--------\
    /          \
   / Integration \     <- API-Tests, Service-Tests
  /--------------\
 /                \
/   Unit Tests     \   <- Viele, schnelle Tests
--------------------
```

## 1. Unit Tests

### Backend (pytest)

**Location**: `backend/tests/`

**Coverage**: 80%+ erforderlich

**Beispiele**:
- `test_auth_service.py` - JWT Token Generation, Validation
- `test_chat_service.py` - Message Processing, Export Logic
- `test_document_service.py` - PDF Processing, Metadata Extraction

**Ausführen**:
```bash
cd backend
pytest tests/ -v --cov=. --cov-report=term-missing
```

### Frontend (Jest + React Testing Library)

**Location**: `frontend/src/**/__tests__/`

**Coverage**: 70%+ erforderlich

**Beispiele**:
- `ChatService.test.ts` - API Client Logic
- `AuthContext.test.tsx` - Authentication State Management
- `ChatInterface.test.tsx` - Component Rendering, User Interactions

**Ausführen**:
```bash
cd frontend
npm run test:unit
```

## 2. Integration Tests

### Backend API Tests

**Location**: `backend/tests/integration/`

**Scope**:
- API Endpoints mit echter Datenbank
- Service-zu-Service Kommunikation
- Claude API Integration (mit Mocks)

**Beispiele**:
- `test_chat_api.py` - Chat Session CRUD, Message Flow
- `test_document_api.py` - Upload, Processing, Retrieval
- `test_auth_api.py` - Login, Registration, Token Refresh

**Ausführen**:
```bash
docker-compose up -d postgres redis
cd backend
pytest tests/integration/ -v -m integration
```

### Frontend Integration Tests

**Location**: `frontend/src/__tests__/integration.test.tsx`

**Scope**:
- Multi-Component Workflows
- API Mocking mit MSW (Mock Service Worker)
- State Management Integration

**Ausführen**:
```bash
npm run test -- integration.test.tsx
```

## 3. E2E Tests (Playwright)

### Critical User Flows

**Location**: `frontend/e2e/`

**Browsers**: Chromium, Firefox, WebKit (Safari)

**Test-Szenarien**:

#### ✅ Chat Export (`chat-export.spec.ts`)
- Markdown Export mit korrektem Dateinamen
- JSON Export mit korrektem Dateinamen
- Sonderzeichen in Dateinamen
- Auto-Extension (.md/.json)
- Cross-Browser Kompatibilität

#### 🔜 Geplant
- `auth-flow.spec.ts` - Login, Logout, Token Refresh
- `document-upload.spec.ts` - Upload, Processing, Library
- `question-generation.spec.ts` - RAG Workflow
- `exam-creation.spec.ts` - Complete Exam Flow

**Ausführen**:
```bash
npm run test:e2e
npm run test:e2e:ui  # Interactive Mode
```

## 4. Test-Daten Management

### Test-Fixtures

**Backend**:
```python
# backend/tests/conftest.py
@pytest.fixture
def test_user(db):
    user = User(email="test@example.com", ...)
    db.add(user)
    db.commit()
    return user
```

**Frontend**:
```typescript
// frontend/src/setupTests.ts
export const createMockFile = (name: string, size: number, type: string): File => {
  return new File(['test content'], name, { type });
};
```

### Test-Datenbank

**PostgreSQL Test DB**:
```bash
DATABASE_URL=postgresql://examcraft:examcraft_dev@localhost:5432/examcraft_test
```

**Cleanup**:
```python
@pytest.fixture(autouse=True)
def cleanup_db(db):
    yield
    db.rollback()
```

## 5. CI/CD Integration

### GitLab CI Pipeline

**`.gitlab-ci.yml`**:
```yaml
stages:
  - test
  - build
  - deploy

test:backend:
  stage: test
  script:
    - pytest tests/ -v --cov=. --cov-report=term-missing
  coverage: '/TOTAL.*\s+(\d+%)$/'

test:frontend:
  stage: test
  script:
    - npm run test:unit -- --watchAll=false --coverage

test:e2e:
  stage: test
  script:
    - npm run test:e2e
  artifacts:
    when: on_failure
    paths:
      - frontend/test-results/
```

### Pre-Commit Hooks

**`.pre-commit-config.yaml`**:
```yaml
- id: run-backend-tests
  name: Run Backend Tests
  entry: bash -c 'cd backend && pytest tests/ -v --tb=short'
  language: system
  files: ^backend/.*\.py$
  pass_filenames: false
```

## 6. Test-Coverage Ziele

| Test-Typ | Ziel | Aktuell | Status |
|----------|------|---------|--------|
| Backend Unit | 80% | 75% | 🟡 In Progress |
| Frontend Unit | 70% | 60% | 🟡 In Progress |
| Integration | 60% | 50% | 🟡 In Progress |
| E2E Critical Flows | 100% | 25% | 🔴 Needs Work |

## 7. Test-Wartung

### Regelmäßige Reviews

- **Wöchentlich**: Flaky Tests identifizieren und fixen
- **Monatlich**: Test-Coverage Review
- **Quarterly**: Test-Strategie Update

### Flaky Test Handling

```typescript
// Retry-Strategie für instabile Tests
test.describe.configure({ retries: 2 });

test('flaky test', async ({ page }) => {
  // Test mit automatischem Retry
});
```

### Test-Performance

**Ziele**:
- Unit Tests: < 5 Sekunden
- Integration Tests: < 30 Sekunden
- E2E Tests: < 5 Minuten

**Optimierung**:
- Parallele Ausführung
- Test-Daten Caching
- Selective Test Runs (nur geänderte Files)

## 8. Lessons Learned

### Browser-Kompatibilitätsproblem (Oktober 2025)

**Problem**: Download-Dateinamen wurden in Safari nicht korrekt gesetzt

**Root Cause**: Blob-URLs ignorieren `download` Attribut in Safari

**Lösung**: Data-URLs statt Blob-URLs verwenden

**Prevention**: E2E-Tests auf allen Browsern (Chromium, Firefox, WebKit)

**Dokumentation**: `docs/browser-compatibility.md`

### Best Practices

1. **Test-First Development** - Tests vor Implementation schreiben
2. **Isolation** - Jeder Test unabhängig und wiederholbar
3. **Descriptive Names** - Test-Namen beschreiben Verhalten
4. **Fast Feedback** - Unit Tests schnell, E2E Tests selektiv
5. **Continuous Monitoring** - Coverage-Trends überwachen

## 9. Tools & Frameworks

### Backend
- **pytest** - Test Framework
- **pytest-cov** - Coverage Reporting
- **pytest-asyncio** - Async Test Support
- **httpx** - API Client Testing

### Frontend
- **Jest** - Test Framework
- **React Testing Library** - Component Testing
- **Playwright** - E2E Testing
- **MSW** - API Mocking

### CI/CD
- **GitLab CI** - Pipeline Automation
- **Pre-commit** - Git Hooks
- **Coverage.py** - Python Coverage
- **Istanbul** - JavaScript Coverage

## 10. Weitere Ressourcen

- [pytest Documentation](https://docs.pytest.org/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)
- [Test-Driven Development](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

## Kontakt

**Team**: Talent Factory
**Projekt**: ExamCraft AI (TF-148)
**Linear**: https://linear.app/talent-factory/project/examcraft-ai-6eebcff0
