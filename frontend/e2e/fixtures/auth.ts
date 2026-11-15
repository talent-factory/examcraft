/**
 * Authentication Fixtures for E2E Tests
 *
 * Provides reusable authentication logic for Playwright tests.
 * Must match credentials in backend/scripts/setup_e2e_test_data.py
 */

import { test as base, expect, Page, BrowserContext, Browser, APIRequestContext } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// E2E Test users - must match setup_e2e_test_data.py. Login is by e-mail via
// the test login; `password` is unused and only kept for the seed script.
export const E2E_TEST_USER = {
  email: 'e2e-test@example.com',
  password: 'E2ETestPassword123',  // pragma: allowlist secret
  firstName: 'E2E',
  lastName: 'Testuser',
};

// Colleague in the SAME institution as E2E_TEST_USER (TF-354 visibility E2E).
export const E2E_TEST_USER_B = {
  email: 'e2e-test-b@example.com',
  password: 'E2ETestPassword123',  // pragma: allowlist secret
};

// User in a DIFFERENT institution (cross-institution isolation).
export const E2E_TEST_USER_C = {
  email: 'e2e-test-c@example.com',
  password: 'E2ETestPassword123',  // pragma: allowlist secret
};

// Storage state file for authenticated sessions
const AUTH_STATE_PATH = path.join(__dirname, '../.auth/user.json');

/**
 * Custom test fixture that provides authenticated page
 */
export const test = base.extend<{
  authenticatedPage: Page;
}>({
  authenticatedPage: async ({ browser }, use) => {
    // Create context with stored auth state if available
    let context: BrowserContext;

    if (fs.existsSync(AUTH_STATE_PATH)) {
      context = await browser.newContext({ storageState: AUTH_STATE_PATH });
    } else {
      context = await browser.newContext();
      const page = await context.newPage();
      await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);
      // Save auth state for reuse
      await ensureAuthDir();
      await context.storageState({ path: AUTH_STATE_PATH });
    }

    const page = await context.newPage();
    await use(page);
    await context.close();
  },
});

/**
 * Ensure auth directory exists
 */
async function ensureAuthDir() {
  const authDir = path.dirname(AUTH_STATE_PATH);
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true });
  }
}

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

/**
 * Log in through the E2E-only `POST /api/v1/auth/test-login` (EXAMCRAFT-126).
 * The backend exposes it only with `E2E_TEST_LOGIN=true` outside production;
 * the session cookie lands in the cookie jar of `request`.
 */
export async function testLoginApi(request: APIRequestContext, email: string): Promise<void> {
  const res = await request.post(`${API_URL}/api/v1/auth/test-login`, { data: { email } });
  expect(res.status(), `test-login failed for ${email}: ${res.status()}`).toBe(204);
}

/**
 * Login helper function. There is no password form any more (the real login
 * runs through Zitadel); the browser context gets the session cookie from the
 * test login. `_password` stays for the existing call sites.
 */
export async function loginUser(page: Page, email: string, _password?: string): Promise<void> {
  await testLoginApi(page.request, email);
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15000 });
}

/**
 * Logout helper function
 */
export async function logoutUser(page: Page): Promise<void> {
  // Both the trigger's aria-label and the logout button's text are
  // translated (t('layout.navigationBar.userMenu'), t('nav.logout')), so
  // only the language-independent data-testid can be matched here.
  await page.locator('[data-testid="user-menu"]').first().click();
  await page.click('[data-testid="logout-button"]');

  // Wait for redirect to login
  await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    // Check for elements that indicate logged-in state. data-testid is
    // language-independent; the user menu's aria-label is translated, so it
    // cannot be matched as a fixed English string here.
    const loggedInIndicator = page.locator('[data-testid="user-menu"], nav a[href="/dashboard"]');
    return await loggedInIndicator.first().isVisible({ timeout: 3000 });
  } catch {
    return false;
  }
}

/**
 * Setup function for global authentication
 * Run this before all tests that need auth
 */
export async function globalSetup(browser: Browser) {
  const context = await browser.newContext();
  const page = await context.newPage();

  // Login
  await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

  // Save storage state
  await ensureAuthDir();
  await context.storageState({ path: AUTH_STATE_PATH });

  await context.close();
}

/**
 * Clear auth state (for cleanup between test runs)
 */
export function clearAuthState(): void {
  if (fs.existsSync(AUTH_STATE_PATH)) {
    fs.unlinkSync(AUTH_STATE_PATH);
  }
}

// Re-export expect from Playwright
export { expect };
