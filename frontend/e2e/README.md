# E2E Tests - ExamCraft Frontend

## Übersicht

End-to-End Tests mit **Playwright** für kritische User-Flows in ExamCraft.

### Warum E2E-Tests?

Nach dem Browser-Kompatibilitätsproblem beim Chat-Export (Oktober 2025) haben wir E2E-Tests implementiert, um:

1. **Regressions verhindern** - Automatische Erkennung von Problemen bei GUI-Änderungen
2. **Cross-Browser-Kompatibilität** - Tests laufen auf Chromium, Firefox und WebKit (Safari)
3. **Kritische Flows absichern** - Download-Funktionalität, Authentication, etc.

## Test-Struktur

```
frontend/e2e/
├── fixtures/
│   └── auth.ts              # Authentication helpers & fixtures
├── smoke.spec.ts            # Smoke tests (no auth required, fast)
├── auth.spec.ts             # Authentication E2E tests (Login, Logout, OAuth)
├── api-connectivity.spec.ts # API connectivity tests (URL fix verification)
├── chat-export.spec.ts      # Chat Export Tests (Markdown & JSON)
├── README.md                # Diese Datei
├── .auth/                   # Stored auth state (gitignored)
└── test-downloads/          # Temporäre Downloads (wird automatisch bereinigt)
```

## Tests ausführen

### Alle E2E-Tests

```bash
bun run test:e2e
```

### Mit UI (interaktiv)

```bash
bun run test:e2e:ui
```

### Mit sichtbarem Browser (Debugging)

```bash
bun run test:e2e:headed
```

### Debug-Modus (Step-by-Step)

```bash
bun run test:e2e:debug
```

### Spezifischer Test

```bash
npx playwright test chat-export.spec.ts
```

### Nur ein Browser

```bash
npx playwright test --project=chromium
npx playwright test --project=firefox
npx playwright test --project=webkit
```

## Voraussetzungen

### 1. Backend muss laufen

```bash
docker-compose up -d backend postgres redis
```

### 2. Frontend muss laufen

```bash
bun start
# oder
docker-compose up -d frontend
```

### 3. Test-Daten einrichten

```bash
cd packages/core/backend
python scripts/setup_e2e_test_data.py
```

Die Tests verwenden:
- E2E Test-User: `e2e-test@examcraft.test` / `E2ETestPassword123!`
- Test-Institution: E2E Test Institution (Professional Tier)
- Test-Dokument: e2e-test-document.pdf

### 4. Playwright Browser installieren (einmalig)

```bash
cd packages/core/frontend
npx playwright install
```

## Test-Abdeckung

### ✅ Smoke Tests (`smoke.spec.ts`)

- **Frontend Loading** - App lädt ohne Fehler
- **Login Page** - Form wird angezeigt
- **API Health** - Backend erreichbar
- **OpenAPI Docs** - Swagger UI verfügbar
- **Protected Routes** - Redirect zu Login
- **Static Assets** - Favicon, Manifest

### ✅ Authentication (`auth.spec.ts`)

- **Login Flow** - Email/Password authentication
- **OAuth Buttons** - Google & Microsoft visibility
- **Logout** - Session termination
- **Session Persistence** - Stays logged in after reload
- **Protected Routes** - Redirect to login

### ✅ API Connectivity (`api-connectivity.spec.ts`)

- **Health Check** - Backend reachability
- **Protected Endpoints** - 401 without auth
- **URL Configuration** - No hardcoded localhost in production
- **Question Generation** - BasicExamCreator API calls
- **Chat Download** - ChatInterface download API calls
- **Prompts API** - promptsApi service calls

### ✅ Chat Export (`chat-export.spec.ts`)

- **Markdown Export** - Korrekte Dateinamen, Inhalt validieren
- **JSON Export** - Struktur validieren, Dateinamen prüfen
- **Sonderzeichen** - Umlaute, Leerzeichen in Dateinamen
- **Auto-Extension** - `.md` / `.json` automatisch hinzufügen
- **Cross-Browser** - Chromium, Firefox, WebKit

### 🔜 Geplante Tests

- Document Upload & Management
- RAG Exam Creation
- Admin Features

## Debugging

### Test-Artefakte

Bei fehlgeschlagenen Tests werden automatisch erstellt:

- **Screenshots** - `test-results/screenshots/`
- **Videos** - `test-results/videos/`
- **Traces** - `test-results/traces/` (öffnen mit `npx playwright show-trace`)

### Trace Viewer

```bash
npx playwright show-trace test-results/traces/trace.zip
```

### Browser-Logs

```bash
npx playwright test --headed --debug
```

## CI/CD Integration

### GitLab CI

Die Tests sind in `.gitlab-ci.yml` integriert:

```yaml
test:e2e:
  stage: test
  image: mcr.microsoft.com/playwright:v1.40.0
  script:
    - cd frontend
    - bun install --frozen-lockfile
    - bun run test:e2e
  artifacts:
    when: on_failure
    paths:
      - frontend/test-results/
```

### GitHub Actions

```yaml
- name: Run E2E Tests
  run: |
    cd frontend
    bun install --frozen-lockfile
    npx playwright install --with-deps
    bun run test:e2e
```

## Best Practices

### 1. Test-Isolation

Jeder Test sollte unabhängig sein:
- Eigene Test-Daten erstellen
- Cleanup nach jedem Test
- Keine Abhängigkeiten zwischen Tests

### 2. Selektoren

Bevorzuge stabile Selektoren:
- ✅ `data-testid` Attribute
- ✅ `role` und `aria-label`
- ❌ CSS-Klassen (ändern sich oft)
- ❌ Text-Content (i18n-problematisch)

### 3. Waits

Verwende explizite Waits:
```typescript
await expect(page.locator('text=Success')).toBeVisible({ timeout: 10000 });
```

### 4. Error Handling

Teste auch Fehler-Szenarien:
```typescript
test('should show error on invalid input', async ({ page }) => {
  // ...
  await expect(page.locator('text=Error')).toBeVisible();
});
```

## Troubleshooting

### Problem: "Browser not found"

```bash
npx playwright install chromium
```

### Problem: "Connection refused"

Stelle sicher, dass Frontend läuft:
```bash
bun start
```

### Problem: "Test timeout"

Erhöhe Timeout in `playwright.config.ts`:
```typescript
timeout: 60 * 1000, // 60 Sekunden
```

### Problem: "Download failed"

Überprüfe Download-Ordner Permissions:
```bash
chmod 755 frontend/e2e/test-downloads
```

## Weitere Ressourcen

- [Playwright Dokumentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Guide](https://playwright.dev/docs/debug)
- [CI/CD Integration](https://playwright.dev/docs/ci)

## Kontakt

Bei Fragen zu den Tests:
- **Team**: Talent Factory
- **Projekt**: ExamCraft AI (TF-148)
- **Dokumentation**: `docs/browser-compatibility.md`
