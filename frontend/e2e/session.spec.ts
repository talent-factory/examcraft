/**
 * E2E: Cookie-Session (EXAMCRAFT-137, Folgearbeit aus EXAMCRAFT-126)
 *
 * Ersetzt `token-refresh.spec.ts`: es gibt keinen Token-Refresh mehr, der
 * Zustand ergibt sich aus dem Session-Cookie. Geprüft werden
 * - abgelaufene Session führt auf `/login` (beim Reload still, bei einem 401 mitten
 *   in der Sitzung mit Hinweis),
 * - Logout in einem Tab beendet die Session in allen Tabs,
 * - Impersonation: Start, Banner nach Reload, Beenden,
 * - Step-up: ein veraltetes Login leitet auf den IdP-Login mit `reauth=true`.
 *
 * Der echte IdP-Flow ist nicht automatisierbar; die Anmeldung läuft über den
 * Test-Login (`E2E_TEST_LOGIN=true`). Die Impersonation-Tests brauchen den
 * Admin aus `setup_e2e_test_data.py` (`e2e-admin@example.com`).
 *
 * Grenzen des Backends für Impersonation: pro Admin höchstens eine offene
 * Sitzung (409 `impersonation_already_active`) und ein Rate-Limit je
 * Kalenderstunde bzw. UTC-Tag (Defaults 10 und 30, konfigurierbar über
 * `IMPERSONATION_RATE_LIMIT_PER_HOUR` und `_DAY`; auch Fehlversuche zählen).
 * Die Tests laufen deshalb seriell und beenden ihre Impersonation im
 * `afterEach`. Jeder Lauf verbraucht mindestens 2 Starts; sind die Limits
 * erschöpft, antwortet das Backend mit 429.
 */
import { test, expect, request as pwRequest, type Page } from '@playwright/test';
import {
  E2E_TEST_ADMIN,
  E2E_TEST_USER,
  E2E_TEST_USER_B,
  loginUser,
  testLoginApi,
} from './fixtures/auth';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

/** Id eines Seed-Benutzers; eigener Kontext, damit die Session des Tests unberührt bleibt. */
async function userIdOf(email: string): Promise<number> {
  const ctx = await pwRequest.newContext();
  try {
    await testLoginApi(ctx, email);
    const res = await ctx.get(`${API_URL}/api/auth/me`);
    expect(res.ok(), `/api/auth/me failed for ${email}: ${res.status()}`).toBeTruthy();
    return (await res.json()).id as number;
  } finally {
    await ctx.dispose();
  }
}

/** Öffnet im Benutzer-Tab des Admin-Panels den Dialog «Als Nutzer anmelden». */
async function openImpersonationDialog(
  page: Page,
  targetId: number,
  targetEmail: string,
): Promise<void> {
  await page.goto('/admin');
  // Die Liste zeigt 20 Benutzer pro Seite (Superuser: alle Institutionen); die
  // Suche holt das Ziel sicher auf die erste Seite. Das Feld ist das erste
  // Textfeld des Benutzer-Tabs (kein data-testid, Placeholder ist übersetzt).
  await page.locator('input[type="text"]').first().fill(targetEmail);
  await page.locator(`[data-testid="ul-actions-menu-trigger-${targetId}"]`).click();
  await page.locator(`[data-testid="ul-btn-impersonate-${targetId}"]`).click();
  await expect(page.locator('[data-testid="impersonation-dialog-backdrop"]')).toBeVisible();
}

test.describe('Session', () => {
  test('eine abgelaufene Session führt beim Reload still auf /login', async ({ page, context }) => {
    await loginUser(page, E2E_TEST_USER.email);

    // Das Cookie ist weg, der Tab merkt es erst bei der nächsten Anfrage.
    await context.clearCookies();
    await page.reload();

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
    // Ein Reload ohne Cookie ist ein stilles 401 auf /me: kein Hinweis.
    await expect(page.locator('[data-testid="login-notice"]')).toHaveCount(0);
  });

  test('ein 401 mitten in der Sitzung zeigt den Hinweis «Sitzung abgelaufen»', async ({ page, context }) => {
    await loginUser(page, E2E_TEST_USER.email);
    await page.waitForLoadState('networkidle');

    await context.clearCookies();
    // Kein Reload: der AuthContext bleibt im Speicher und erfährt vom Ende der
    // Session nur über das 401 der nächsten API-Anfrage. Absolute API-URL, damit
    // der fetch-Interceptor sie erkennt und kein CRA-Proxy nötig ist.
    await page.evaluate(
      (apiUrl) => fetch(`${apiUrl}/api/v1/documents/`, { credentials: 'include' }),
      API_URL,
    );

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    await expect(page.locator('[data-testid="login-notice"]')).toBeVisible();
  });

  test('ein Logout in einem Tab beendet die Session im zweiten Tab', async ({ page, context }) => {
    await loginUser(page, E2E_TEST_USER.email);
    await page.waitForLoadState('networkidle');

    const second = await context.newPage();
    await second.goto('/dashboard');
    await expect(second).toHaveURL(/\/dashboard/);

    await page.locator('[data-testid="user-menu"]').first().click();
    await page.click('[data-testid="logout-button"]');
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });

    // Der `storage`-Broadcast räumt den zweiten Tab ohne Reload ab.
    await expect(second).toHaveURL(/\/login/, { timeout: 10000 });
    // Und ohne Hinweis: der Benutzer hat sich selbst abgemeldet.
    await expect(second.locator('[data-testid="login-notice"]')).toHaveCount(0);
  });
});

test.describe('Impersonation', () => {
  // Pro Admin ist nur eine offene Impersonation erlaubt: nicht parallel.
  test.describe.configure({ mode: 'serial' });

  // Auch nach einem fehlgeschlagenen Test keine offene Sitzung hinterlassen,
  // sonst antwortet jeder weitere Start mit 409. Schlägt das Beenden fehl, weil
  // keine Impersonation läuft, ist das gewollt und wird ignoriert.
  test.afterEach(async ({ page }) => {
    await page.request.post(`${API_URL}/api/admin/impersonate/end`).catch(() => undefined);
  });

  test('Start, Banner nach Reload und Beenden', async ({ page }) => {
    const targetId = await userIdOf(E2E_TEST_USER_B.email);
    await loginUser(page, E2E_TEST_ADMIN.email);
    await openImpersonationDialog(page, targetId, E2E_TEST_USER_B.email);

    await page.locator('textarea').fill('E2E: Impersonation prüfen');
    await page.locator('form button[type="submit"]').click();

    const banner = page.locator('[data-testid="impersonation-banner"]');
    await expect(banner).toBeVisible({ timeout: 10000 });
    await expect(banner).toContainText(E2E_TEST_USER_B.email);

    // Das Banner überlebt den Reload (Hinweis im localStorage + Cookie).
    await page.reload();
    await expect(banner).toBeVisible({ timeout: 10000 });

    await banner.locator('button').click();
    await expect(banner).toHaveCount(0, { timeout: 10000 });
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('ein Logout während der Impersonation beendet nur die Impersonation', async ({ page }) => {
    const targetId = await userIdOf(E2E_TEST_USER_B.email);
    await loginUser(page, E2E_TEST_ADMIN.email);
    await openImpersonationDialog(page, targetId, E2E_TEST_USER_B.email);
    await page.locator('textarea').fill('E2E: Logout während Impersonation');
    await page.locator('form button[type="submit"]').click();
    await expect(page.locator('[data-testid="impersonation-banner"]')).toBeVisible({ timeout: 10000 });

    await page.locator('[data-testid="user-menu"]').first().click();
    await page.click('[data-testid="logout-button"]');

    await expect(page.locator('[data-testid="impersonation-banner"]')).toHaveCount(0, { timeout: 10000 });
    // Der Admin bleibt angemeldet und schreibt keinen Logout-Broadcast.
    await expect(page).not.toHaveURL(/\/login/);
    const broadcast = await page.evaluate(() => localStorage.getItem('examcraft_logout_broadcast'));
    expect(broadcast).toBeNull();
  });

  test('ein veraltetes Login leitet für den Step-up auf den IdP-Login mit reauth=true', async ({ page }) => {
    const targetId = await userIdOf(E2E_TEST_USER_B.email);
    await loginUser(page, E2E_TEST_ADMIN.email);

    // Das Backend akzeptiert ein frisches Test-Login immer; das veraltete Login
    // wird deshalb am Netz nachgestellt (403 `auth_reauth_required`).
    await page.route('**/api/admin/users/*/impersonate', (route) =>
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Reauth', error_code: 'auth_reauth_required' }),
      }),
    );
    // Den IdP-Login nicht wirklich verlassen: die Weiterleitung abfangen.
    const reauthRequest = page.waitForRequest(/\/api\/v1\/auth\/login\?.*reauth=true/);
    await page.route(/\/api\/v1\/auth\/login\?.*reauth=true/, (route) =>
      route.fulfill({ status: 200, contentType: 'text/html', body: '<html><body>idp</body></html>' }),
    );

    await openImpersonationDialog(page, targetId, E2E_TEST_USER_B.email);
    await page.locator('textarea').fill('E2E: Step-up');
    await page.locator('form button[type="submit"]').click();

    const request = await reauthRequest;
    expect(new URL(request.url()).searchParams.get('return_to')).toBe('/admin');
    // Trotz 403 wurde keine Impersonation gestartet (kein Banner), und das
    // Cookie-Jar handelt weiter als Admin. Die Prüfung der Anfrage oben
    // belegt den Step-up; `/api/auth/me` ist hier nur ein Sanity-Check, weil
    // das 403 per `page.route` gestubbt ist.
    await expect(page.locator('[data-testid="impersonation-banner"]')).toHaveCount(0);
    const me = await page.request.get(`${API_URL}/api/auth/me`);
    expect(me.ok()).toBeTruthy();
    expect((await me.json()).email).toBe(E2E_TEST_ADMIN.email);
  });
});
