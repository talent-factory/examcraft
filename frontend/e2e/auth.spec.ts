/**
 * E2E Tests for Authentication Flow (EXAMCRAFT-126)
 *
 * Der Login läuft über das Backend (OIDC-BFF gegen tessera/Zitadel); es gibt
 * keine Login-, Registrierungs- und Reset-Masken mehr. Der echte IdP-Flow ist
 * nicht automatisierbar, deshalb melden die Tests über den Test-Login
 * (`E2E_TEST_LOGIN=true`) an und prüfen Login-Seite, Fehleranzeige, Session
 * und Logout.
 */

import { test, expect } from '@playwright/test';
import { E2E_TEST_USER, loginUser, clearAuthState } from './fixtures/auth';

test.describe('Authentication', () => {

  test.beforeEach(async () => {
    // Clear auth state before each test for isolation
    clearAuthState();
  });

  test('should display the login page with a single sign-in button', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[data-testid="login-button"]')).toBeVisible({ timeout: 10000 });
    // No local credential form any more.
    await expect(page.locator('input[type="password"]')).toHaveCount(0);
  });

  test('should show a message for a backend login error', async ({ page }) => {
    await page.goto('/login?error=idp_unavailable');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('[role="alert"]')).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('should login successfully via the test login', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email);

    await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 });
  });

  test('should logout successfully', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email);
    await page.waitForLoadState('networkidle');

    await page.locator('[data-testid="user-menu"]').first().click();
    await page.click('[data-testid="logout-button"]');

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/dashboard');

    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should persist session after page reload', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email);

    await page.reload();
    await page.waitForLoadState('networkidle');

    await expect(page).not.toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should keep no tokens in localStorage', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email);
    await page.waitForLoadState('networkidle');

    const keys = await page.evaluate(() => Object.keys(window.localStorage));
    expect(keys).not.toContain('examcraft_access_token');
    expect(keys).not.toContain('examcraft_refresh_token');
  });
});

// TF-657: Das Hilfe-Widget hängt ausserhalb von <Routes> und war deshalb auch
// unangemeldet sichtbar. HelpWidgetGate gated am Auth-Status.
//
// Selektiert wird über data-testid, NICHT über aria-label: das Label kommt aus
// i18n und ist sprachabhängig ("Hilfe" auf de, "Help" auf en). Playwright-
// Chromium läuft mit en-US, eine Negativ-Assertion auf [aria-label="Hilfe"]
// wäre hier also immer grün — auch gegen den ungefixten Code. Genau das ist
// beim ersten Lauf passiert.
test.describe('Help Widget — Public Routes', () => {

  const HELP_FAB = '[data-testid="help-fab"]';

  const PUBLIC_ROUTES = ['/login', '/privacy', '/terms', '/imprint'];

  test.beforeEach(async () => {
    clearAuthState();
  });

  for (const route of PUBLIC_ROUTES) {
    test(`should not render the help FAB on ${route}`, async ({ page }) => {
      await page.goto(route);
      await page.waitForLoadState('networkidle');

      await expect(page.locator(HELP_FAB)).toHaveCount(0);
    });
  }

  test('should not fire help API requests on the login page', async ({ page }) => {
    const helpRequests: string[] = [];
    page.on('request', (request) => {
      if (request.url().includes('/api/v1/help/')) {
        helpRequests.push(request.url());
      }
    });

    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    expect(helpRequests).toEqual([]);
  });

  test('should not open the help panel via Ctrl+/ on the login page', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    await page.keyboard.press('Control+/');
    await page.keyboard.press('Meta+/');

    await expect(page.locator(HELP_FAB)).toHaveCount(0);
    // By test id, not aria-label: a negative assertion on a translated label
    // would pass vacuously once the label text changes.
    await expect(page.locator('[data-testid="help-panel-close"]')).toHaveCount(0);
  });

  test('should render the help FAB again after login', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email);
    await page.waitForLoadState('networkidle');

    await expect(page.locator(HELP_FAB)).toBeVisible({ timeout: 15000 });
  });
});
