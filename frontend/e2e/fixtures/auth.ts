/**
 * Authentication Fixtures for E2E Tests
 *
 * Provides reusable authentication logic for Playwright tests.
 * Must match credentials in backend/scripts/setup_e2e_test_data.py
 */

import { test as base, expect, Page, BrowserContext, Browser } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// E2E Test credentials - must match setup_e2e_test_data.py
export const E2E_TEST_USER = {
  email: 'e2e-test@example.com',
  password: 'E2ETestPassword123',  // pragma: allowlist secret
  firstName: 'E2E',
  lastName: 'Testuser',
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

/**
 * Login helper function
 */
export async function loginUser(page: Page, email: string, password: string): Promise<void> {
  await page.goto('/login');

  // Wait for login form to be ready
  await expect(page.locator('form')).toBeVisible({ timeout: 10000 });

  // Fill in credentials (using id selectors as the form uses id, not name)
  await page.fill('#email, input[name="email"], input[type="email"]', email);
  await page.fill('#password, input[name="password"], input[type="password"]', password);

  // Submit form
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard or main page
  await expect(page).toHaveURL(/\/(dashboard|document-chat|home|$)/, { timeout: 15000 });
}

/**
 * Logout helper function
 */
export async function logoutUser(page: Page): Promise<void> {
  // Click user menu or avatar
  const userMenu = page.locator('[data-testid="user-menu"], [aria-label="User menu"], button:has-text("Logout")');
  await userMenu.first().click();

  // Click logout button
  await page.click('text=Logout, text=Abmelden, [data-testid="logout-button"]');

  // Wait for redirect to login
  await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
}

/**
 * Check if user is logged in
 */
export async function isLoggedIn(page: Page): Promise<boolean> {
  try {
    // Check for elements that indicate logged-in state
    const loggedInIndicator = page.locator('[data-testid="user-menu"], nav a[href="/dashboard"], [aria-label="User menu"]');
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
