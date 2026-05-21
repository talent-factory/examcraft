/**
 * E2E Tests for transparent Token Refresh
 *
 * Tests:
 * - API calls succeed after simulated access token expiry (silent refresh)
 * - Redirect to /login when refresh token is missing or rejected
 */

import { test, expect } from '@playwright/test';
import { E2E_TEST_USER, loginUser, clearAuthState } from './fixtures/auth';

test.describe('Token Refresh', () => {
  test.beforeEach(async () => {
    clearAuthState();
  });

  test('API-Calls funktionieren nach simuliertem Token-Ablauf', async ({ page }) => {
    // Login with valid credentials
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

    // Navigate to app root and wait for idle network
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // Replace access token with an expired JWT (exp 60 seconds in the past)
    await page.evaluate(() => {
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 60 }))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
      const expiredToken = `eyJhbGciOiJIUzI1NiJ9.${expiredPayload}.sig`;
      localStorage.setItem('examcraft_access_token', expiredToken);
    });

    // Track whether the refresh endpoint is called
    let refreshCalled = false;
    await page.route('**/api/auth/refresh', async (route) => {
      refreshCalled = true;
      await route.continue();
    });

    // Trigger an API call by navigating to a protected page
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // No visible "Failed to Fetch" error
    const failedFetch = page.locator('text=Failed to Fetch');
    await expect(failedFetch).not.toBeVisible({ timeout: 3000 });

    // No visible credentials validation error
    const credError = page.locator('text=Could not validate credentials');
    await expect(credError).not.toBeVisible({ timeout: 3000 });

    // User must still be logged in — not redirected to /login
    expect(page.url()).not.toContain('/login');

    // The whole point of this test: refresh must actually have fired.
    expect(refreshCalled).toBe(true);
  });

  test('Redirect zu /login bei fehlendem Refresh-Token', async ({ page }) => {
    // Login first to get a valid session
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

    // Replace access token with expired JWT and remove refresh token
    await page.evaluate(() => {
      const expiredPayload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) - 60 }))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=+$/, '');
      localStorage.setItem('examcraft_access_token', `eyJ.${expiredPayload}.sig`);
      localStorage.removeItem('examcraft_refresh_token');
    });

    // Stub refresh endpoint to return 401
    await page.route('**/api/auth/refresh', (route) => {
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Refresh token expired' }),
      });
    });

    // Navigate to a protected page
    await page.goto('/documents');

    // Expect redirect to /login OR a visible auth error. Either is an
    // acceptable end-state — but the test must fail if NEITHER happens.
    await Promise.race([
      page.waitForURL('**/login', { timeout: 10000 }),
      page.locator('text=Could not validate').waitFor({ timeout: 10000 }),
      page.locator('[data-testid="error"]').waitFor({ timeout: 10000 }),
    ]);

    const isOnLogin = page.url().includes('/login');
    const hasError =
      (await page.locator('text=Could not validate').count()) > 0 ||
      (await page.locator('[data-testid="error"]').count()) > 0;

    expect(isOnLogin || hasError).toBe(true);
  });
});
