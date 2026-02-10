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
├── chat-export.spec.ts    # Chat Export Tests (Markdown & JSON)
├── README.md              # Diese Datei
└── test-downloads/        # Temporäre Downloads (wird automatisch bereinigt)
```

## Tests ausführen

### Alle E2E-Tests

```bash
npm run test:e2e
```

### Mit UI (interaktiv)

```bash
npm run test:e2e:ui
```

### Mit sichtbarem Browser (Debugging)

```bash
npm run test:e2e:headed
```

### Debug-Modus (Step-by-Step)

```bash
npm run test:e2e:debug
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
npm start
# oder
docker-compose up -d frontend
```

### 3. Test-Daten

Die Tests erwarten:
- Einen Test-User: `test@example.com` / `TestPassword123!`
- Mindestens ein hochgeladenes Dokument in der Datenbank

## Test-Abdeckung

### ✅ Chat Export (`chat-export.spec.ts`)

- **Markdown Export** - Korrekte Dateinamen, Inhalt validieren
- **JSON Export** - Struktur validieren, Dateinamen prüfen
- **Sonderzeichen** - Umlaute, Leerzeichen in Dateinamen
- **Auto-Extension** - `.md` / `.json` automatisch hinzufügen
- **Cross-Browser** - Chromium, Firefox, WebKit

### 🔜 Geplante Tests

- Authentication Flow (Login, Logout, Token Refresh)
- Document Upload & Management
- Question Generation Workflow
- RAG Exam Creation

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
    - npm ci
    - npm run test:e2e
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
    npm ci
    npx playwright install --with-deps
    npm run test:e2e
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
npm start
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
