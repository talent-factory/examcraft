# E2E-Tests - Nächste Schritte

## Status

✅ **Playwright installiert und konfiguriert**
✅ **Browser heruntergeladen** (Chromium, Firefox, WebKit)
✅ **Test-Infrastruktur erstellt**
✅ **Unit-Tests funktionieren** (10/10 bestanden)

⚠️ **E2E-Tests benötigen noch Setup**

## Problem

Die E2E-Tests schlagen fehl, weil:

1. **Test-User fehlt** - `test@example.com` existiert nicht in der Datenbank
2. **Test-Daten fehlen** - Keine Dokumente für Chat-Tests
3. **Login-Flow** - Authentifizierung muss angepasst werden

## Lösung: Test-Setup Script

### 1. Test-Daten Script erstellen

```bash
# backend/scripts/setup_test_data.py
```

```python
import asyncio
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models.auth import User, Institution
from backend.models.document import Document
from backend.services.auth_service import AuthService
import bcrypt

async def setup_test_data():
    """Erstellt Test-User und Test-Dokumente für E2E-Tests"""
    db = next(get_db())

    try:
        # 1. Test-Institution erstellen
        institution = Institution(
            name="Test Institution",
            domain="test.example.com"
        )
        db.add(institution)
        db.commit()

        # 2. Test-User erstellen
        hashed_password = bcrypt.hashpw(
            "TestPassword123!".encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        test_user = User(
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User",
            institution_id=institution.id,
            is_active=True,
            is_verified=True
        )
        db.add(test_user)
        db.commit()

        # 3. Test-Dokument erstellen
        test_doc = Document(
            title="Test Document",
            filename="test-document.pdf",
            file_path="/tmp/test-document.pdf",
            status="processed",
            user_id=test_user.id
        )
        db.add(test_doc)
        db.commit()

        print("✅ Test-Daten erfolgreich erstellt!")
        print(f"   User: {test_user.email}")
        print(f"   Document: {test_doc.title}")

    except Exception as e:
        print(f"❌ Fehler beim Erstellen der Test-Daten: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(setup_test_data())
```

### 2. Test-Setup in Docker

```yaml
# docker-compose.test.yml
version: '3.8'

services:
  backend-test:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://examcraft:examcraft_test@postgres-test:5432/examcraft_test
      - REDIS_URL=redis://redis-test:6379
    depends_on:
      - postgres-test
      - redis-test
    command: >
      sh -c "
        python scripts/setup_test_data.py &&
        uvicorn main:app --host 0.0.0.0 --port 8000
      "

  postgres-test:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=examcraft_test
      - POSTGRES_USER=examcraft
      - POSTGRES_PASSWORD=examcraft_test

  redis-test:
    image: redis:7-alpine
```

### 3. E2E-Tests ausführen

```bash
# 1. Test-Environment starten
docker-compose -f docker-compose.test.yml up -d

# 2. E2E-Tests ausführen
cd frontend
bun run test:e2e

# 3. Cleanup
docker-compose -f docker-compose.test.yml down
```

## Alternative: Vereinfachte E2E-Tests

Für den Anfang können wir die E2E-Tests vereinfachen:

### Smoke Tests (ohne Login)

```typescript
// frontend/e2e/smoke.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('should load homepage', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/ExamCraft/);
  });

  test('should load login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('text=Login')).toBeVisible();
  });

  test('should show navigation', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('nav')).toBeVisible();
  });
});
```

### API Tests (ohne UI)

```typescript
// frontend/e2e/api.spec.ts
import { test, expect } from '@playwright/test';

test.describe('API Tests', () => {
  test('should return health check', async ({ request }) => {
    const response = await request.get('http://localhost:8000/health');
    expect(response.ok()).toBeTruthy();
  });

  test('should return 401 for protected endpoint', async ({ request }) => {
    const response = await request.get('http://localhost:8000/api/v1/chat/sessions');
    expect(response.status()).toBe(401);
  });
});
```

## Empfohlene Reihenfolge

1. **Jetzt**: Unit-Tests verwenden (funktionieren bereits!)
2. **Kurzfristig**: Smoke Tests implementieren (einfach, kein Setup)
3. **Mittelfristig**: Test-Daten Script erstellen
4. **Langfristig**: Vollständige E2E-Tests mit Authentication

## Unit-Tests sind bereits produktiv!

Die Unit-Tests funktionieren perfekt und bieten bereits guten Schutz:

```bash
bun run test:unit -- ChatService.test.ts
```

**Ergebnis**: ✅ 10/10 Tests bestanden

### Was wird getestet:
- ✅ Session-Erstellung
- ✅ Nachrichten senden
- ✅ Markdown Download
- ✅ JSON Download
- ✅ Error Handling
- ✅ URL-Encoding

## Fazit

**Aktueller Stand**:
- ✅ Test-Infrastruktur vollständig
- ✅ Unit-Tests funktionieren
- ⚠️ E2E-Tests benötigen Test-Daten

**Nächster Schritt**:
1. Test-Daten Script erstellen
2. Smoke Tests implementieren
3. Vollständige E2E-Tests aktivieren

**Empfehlung**:
Verwende vorerst die Unit-Tests - sie bieten bereits sehr guten Schutz gegen Regressions!
