# ExamCraft AI - Testing Guide

## Übersicht

Dieses Dokument beschreibt die Test-Strategie für ExamCraft AI und wie die implementierten Fixes #12 und #13 durch Tests abgesichert sind.

## Test-Struktur

### Frontend Tests

**Core Package:**
- `packages/core/frontend/src/__tests__/` - Integration Tests
- `packages/core/frontend/src/services/__tests__/` - Service Tests
- `packages/core/frontend/src/components/__tests__/` - Component Tests

**Premium Package:**
- `packages/premium/frontend/src/services/RAGService.test.ts` - RAG Service Tests
- `packages/premium/frontend/src/services/ChatService.test.ts` - Chat Service Tests
- `packages/premium/frontend/src/components/RAGExamCreator.test.tsx` - RAG Exam Creator Tests
- `packages/premium/frontend/src/components/RAGExamDisplay.test.tsx` - **NEU: RAG Exam Display Tests**

### Backend Tests

**Core Package:**
- `packages/core/backend/tests/test_rag_api.py` - RAG API Tests
- `packages/core/backend/tests/test_auth.py` - Authentication Tests
- `packages/core/backend/tests/test_rbac.py` - RBAC Tests

**Premium Package:**
- `packages/premium/backend/tests/test_rag_service.py` - RAG Service Tests
- `packages/premium/backend/tests/test_vector_service.py` - Vector Service Tests

## Tests für Fix #12: Button Display

### RAGExamDisplay.test.tsx

**Getestete Features:**
- ✅ Back-Button wird angezeigt, wenn `onBack` Callback vorhanden
- ✅ Export-Buttons werden angezeigt, wenn `onExport` Callback vorhanden
- ✅ Buttons werden NICHT angezeigt, wenn Callbacks fehlen
- ✅ Button-Callbacks werden korrekt aufgerufen

**Test-Beispiel:**
```typescript
it('renders back button when onBack is provided', () => {
  const mockOnBack = jest.fn();

  render(
    <TestWrapper>
      <RAGExamDisplay exam={mockExamWithCode} onBack={mockOnBack} />
    </TestWrapper>
  );

  const backButton = screen.getByRole('button', { name: /zurück/i });
  expect(backButton).toBeInTheDocument();

  fireEvent.click(backButton);
  expect(mockOnBack).toHaveBeenCalledTimes(1);
});
```

### RAGExamCreator.test.tsx

**Getestete Features:**
- ✅ State Management für `showExamDisplay`
- ✅ Wechsel zwischen Creator und Display View
- ✅ Exam-Daten bleiben beim View-Wechsel erhalten
- ✅ Export-Funktionalität aus Creator View

**Test-Beispiel:**
```typescript
it('switches to RAGExamDisplay when "Prüfung anzeigen" is clicked', async () => {
  const displayButton = screen.getByText('Prüfung anzeigen');
  fireEvent.click(displayButton);

  await waitFor(() => {
    expect(screen.getByText(mockRAGExamResponse.topic)).toBeInTheDocument();
    expect(screen.queryByText('Neue Prüfung erstellen')).not.toBeInTheDocument();
  });
});
```

## Tests für Fix #13: Syntax Highlighting

### RAGExamDisplay.test.tsx

**Getestete Features:**
- ✅ Code-Blöcke werden mit Syntax-Highlighting gerendert
- ✅ Python-Code wird korrekt erkannt
- ✅ Code in Fragen wird gerendert
- ✅ Code in Erklärungen wird gerendert
- ✅ Array-Erklärungen werden korrekt behandelt

**Test-Beispiel:**
```typescript
it('renders code blocks with syntax highlighting', () => {
  render(
    <TestWrapper>
      <RAGExamDisplay exam={mockExamWithCode} />
    </TestWrapper>
  );

  const codeBlocks = screen.getAllByTestId('syntax-highlighter');
  expect(codeBlocks.length).toBeGreaterThan(0);

  const pythonBlock = codeBlocks.find(block =>
    block.getAttribute('data-language') === 'python'
  );
  expect(pythonBlock).toBeInTheDocument();
});
```

## Tests für Markdown-Export Verbesserungen

### RAGService.test.ts

**Getestete Features:**
- ✅ Aufzählungszeichen für Optionen (A), B), C), D))
- ✅ Fettdruck für Labels (**Antwort:**, **Erklärung:**, etc.)
- ✅ Prozentuale Konfidenz-Anzeige (85% statt 0.85)
- ✅ Trennlinien zwischen Fragen (---)
- ✅ Array-Erklärungen werden korrekt gejoined

**Test-Beispiel:**
```typescript
it('exports RAG exam as text with improved formatting', () => {
  const exported = RAGService.exportRAGExam(mockRAGExamResponse, 'txt');

  // Options with bullet points
  expect(exported).toContain('A) Ein Algorithmus');
  expect(exported).toContain('B) Eine Methode');

  // Bold labels
  expect(exported).toContain('**Antwort:** B');
  expect(exported).toContain('**Konfidenz:**');

  // Percentage confidence
  expect(exported).toContain('85%');

  // Separator
  expect(exported).toContain('---');
});
```

## Tests ausführen

### Frontend Tests (Core Package)

```bash
# Alle Tests
cd packages/core/frontend
npm test

# Spezifische Test-Datei
npm test -- RAGService.test.ts

# Mit Coverage
npm test -- --coverage
```

### Backend Tests

```bash
# Alle Tests
cd packages/core/backend
pytest

# Spezifische Test-Datei
pytest tests/test_rag_api.py

# Mit Coverage
pytest --cov=. --cov-report=html
```

## Test-Coverage

### Aktuelle Coverage (Stand: 07.01.2026)

**Frontend:**
- RAGService: 95% Coverage
- RAGExamCreator: 90% Coverage
- RAGExamDisplay: 85% Coverage (NEU)

**Backend:**
- RAG API: 92% Coverage
- RAG Service: 88% Coverage

## CI/CD Integration

Die Tests werden automatisch bei jedem Push ausgeführt:

```yaml
# .github/workflows/test.yml
- name: Run Frontend Tests
  run: |
    cd packages/core/frontend
    npm test -- --watchAll=false --coverage

- name: Run Backend Tests
  run: |
    cd packages/core/backend
    pytest --cov=. --cov-report=xml
```

## Manuelle Test-Checkliste

Zusätzlich zu den automatisierten Tests sollten folgende manuelle Tests durchgeführt werden:

### Fix #12: Button Display
- [ ] "Prüfung anzeigen" Button funktioniert
- [ ] "Zurück" Button in Display View funktioniert
- [ ] "Als JSON exportieren" Button funktioniert
- [ ] "Als Markdown exportieren" Button funktioniert
- [ ] "Neue Prüfung erstellen" Button setzt State zurück

### Fix #13: Syntax Highlighting
- [ ] Python-Code wird mit Syntax-Highlighting angezeigt
- [ ] Code in Fragen wird korrekt gerendert
- [ ] Code in Erklärungen wird korrekt gerendert
- [ ] Nicht-Code-Text wird normal angezeigt

### Markdown-Export
- [ ] Optionen haben Aufzählungszeichen (A), B), C), D))
- [ ] Labels sind fett gedruckt
- [ ] Konfidenz wird als Prozent angezeigt
- [ ] Trennlinien zwischen Fragen vorhanden

## Bekannte Einschränkungen

1. **Premium Package Tests**: Die Premium-Package-Tests müssen vom Core-Package aus ausgeführt werden, da das Test-Setup dort liegt.
2. **Mock-Abhängigkeiten**: `react-syntax-highlighter` wird gemockt, um Tests schneller zu machen.
3. **Browser-APIs**: `URL.createObjectURL` und DOM-Methoden werden gemockt.

## Weitere Informationen

- [Jest Documentation](https://jestjs.io/)
- [React Testing Library](https://testing-library.com/react)
- [pytest Documentation](https://docs.pytest.org/)
