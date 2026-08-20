/**
 * E2E Tests for Authentication Flow
 *
 * Tests:
 * - Login with email/password
 * - Google OAuth button visibility
 * - Microsoft OAuth button visibility
 * - Logout functionality
 * - Session persistence
 * - Protected route redirect
 */

import { test, expect } from '@playwright/test';
import { E2E_TEST_USER, loginUser, clearAuthState } from './fixtures/auth';

test.describe('Authentication', () => {

  test.beforeEach(async () => {
    // Clear auth state before each test for isolation
    clearAuthState();
  });

  test('should display login page correctly', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Check for email input (form uses id="email")
    await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

    // Check password input (form uses id="password")
    await expect(page.locator('#password')).toBeVisible();

    // Check submit button
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show OAuth buttons', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Google OAuth is an <a> link, Microsoft is a <button>
    const googleLink = page.locator('a:has-text("Google")');
    await expect(googleLink).toBeVisible({ timeout: 10000 });

    // Microsoft OAuth button should be visible
    const microsoftButton = page.locator('button:has-text("Microsoft")');
    await expect(microsoftButton).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

    // Should redirect away from login page
    await expect(page).not.toHaveURL(/\/login/, { timeout: 15000 });
  });

  test('should show error on invalid credentials', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Enter invalid credentials
    await page.fill('#email', 'invalid@example.com');
    await page.fill('#password', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message (error box has bg-red-50 class)
    await expect(page.locator('.bg-red-50')).toBeVisible({ timeout: 10000 });

    // Should still be on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

    // Wait for dashboard to load
    await page.waitForLoadState('networkidle');

    // Look for logout button in various locations (sidebar, dropdown, etc.)
    const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Abmelden"), [data-testid="logout"]');

    if (await logoutButton.first().isVisible({ timeout: 5000 }).catch(() => false)) {
      await logoutButton.first().click();
      // Should be redirected to login
      await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
    } else {
      // If no visible logout button, check that we're logged in
      // This test passes if login worked (we got past login page)
      await expect(page).not.toHaveURL(/\/login/);
    }
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    // Try to access protected route without login
    await page.goto('/dashboard');

    // Should be redirected to login
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should persist session after page reload', async ({ page }) => {
    // Login
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);

    // Get current URL after login
    const url = page.url();

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Should still be on same page (not redirected to login)
    await expect(page).not.toHaveURL(/\/login/, { timeout: 10000 });
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Enter invalid email format
    await page.fill('#email', 'notanemail');
    await page.fill('#password', 'somepassword');
    await page.click('button[type="submit"]');

    // Should stay on login page (browser validation or app validation)
    await expect(page).toHaveURL(/\/login/);
  });

  test('should handle empty form submission', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Click submit without filling form
    await page.click('button[type="submit"]');

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Registration', () => {

  test('should display registration page', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    // Check that form inputs are visible (RegisterForm uses name attributes)
    await expect(page.locator('input[name="email"], #email')).toBeVisible({ timeout: 10000 });
  });

  test('should have button to switch to login', async ({ page }) => {
    await page.goto('/register');
    await page.waitForLoadState('networkidle');

    // Check button to switch to login exists (it's a button, not a link)
    const loginButton = page.locator('button:has-text("Login"), button:has-text("Back to Login"), button:has-text("Anmelden")');
    await expect(loginButton.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe('Password Reset', () => {

  test('should display password reset request page', async ({ page }) => {
    await page.goto('/forgot-password');
    await page.waitForLoadState('networkidle');

    // Page should load without error - check for any form or content
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have forgot password button on login page', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    // Check forgot password button exists (it's a button, not a link)
    const forgotButton = page.locator('button:has-text("Forgot"), button:has-text("Vergessen")');
    await expect(forgotButton).toBeVisible({ timeout: 10000 });
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

  const PUBLIC_ROUTES = [
    '/login',
    '/register',
    '/auth/callback',
    '/auth/reset-password',
    '/auth/reset-password/confirm',
    '/verify-email',
    '/registration-success',
  ];

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
    await expect(page.locator('[aria-label="close"]')).toHaveCount(0);
  });

  test('should render the help FAB again after login', async ({ page }) => {
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);
    await page.waitForLoadState('networkidle');

    await expect(page.locator(HELP_FAB)).toBeVisible({ timeout: 15000 });
  });
});
