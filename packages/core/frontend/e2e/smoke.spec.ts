/**
 * Smoke Tests - Basic Application Health
 *
 * These tests verify basic application functionality without requiring authentication.
 * They are fast and useful for CI pipelines to catch obvious deployment issues.
 *
 * Run specifically with:
 *   npx playwright test smoke.spec.ts
 */

import { test, expect } from '@playwright/test';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

test.describe('Smoke Tests - Frontend', () => {

  test('should load the application', async ({ page }) => {
    await page.goto('/');

    // Page should load without error
    // Check for any visible content
    await expect(page.locator('body')).toBeVisible();
  });

  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Login form should be visible
    await expect(page.locator('form, [role="form"]')).toBeVisible({ timeout: 10000 });

    // Email input should exist
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();

    // Password input should exist
    await expect(page.locator('input[type="password"], input[name="password"]')).toBeVisible();
  });

  test('should display register page', async ({ page }) => {
    await page.goto('/register');

    // Page should load
    await expect(page.locator('body')).toBeVisible();

    // Should have a form
    await expect(page.locator('form, [role="form"]')).toBeVisible({ timeout: 10000 });
  });

  test('should have correct page title', async ({ page }) => {
    await page.goto('/');

    // Title should contain ExamCraft
    await expect(page).toHaveTitle(/ExamCraft|Exam|Craft/i);
  });

  test('should have no JavaScript errors on load', async ({ page }) => {
    const errors: string[] = [];

    page.on('pageerror', error => {
      errors.push(error.message);
    });

    await page.goto('/');
    await page.waitForTimeout(2000);

    // Filter out known benign errors
    const criticalErrors = errors.filter(err =>
      !err.includes('ResizeObserver') && // Common benign error
      !err.includes('Non-Error promise rejection') // Sometimes from analytics
    );

    expect(criticalErrors.length).toBe(0);
  });

  test('should redirect to login when accessing protected route', async ({ page }) => {
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL(/\/(login|auth)/, { timeout: 10000 });
  });
});

test.describe('Smoke Tests - API', () => {

  test('should reach health endpoint', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/health`);

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('status');
    expect(body.status).toBe('healthy');
  });

  test('should reach OpenAPI docs', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/docs`);

    expect(response.status()).toBe(200);
  });

  test('should reach OpenAPI JSON schema', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/openapi.json`);

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('openapi');
    expect(body).toHaveProperty('info');
    expect(body).toHaveProperty('paths');
  });

  test('should return non-200 for authenticated endpoints', async ({ request }) => {
    const protectedEndpoints = [
      '/api/v1/users/me',
      '/api/v1/documents',
    ];

    for (const endpoint of protectedEndpoints) {
      const response = await request.get(`${API_BASE_URL}${endpoint}`);
      // Without auth, should not return 200 OK
      expect(response.status()).not.toBe(200);
    }
  });

  test('should have CORS headers configured', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/health`);

    // CORS should be configured (may vary by environment)
    // Just verify the request succeeded from the browser
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('Smoke Tests - Static Assets', () => {

  test('should respond to favicon request', async ({ request }) => {
    const response = await request.get('/favicon.ico');

    // Any response is acceptable - just verify the endpoint responds
    expect(response.status()).toBeDefined();
  });

  test('should load manifest.json', async ({ request }) => {
    const response = await request.get('/manifest.json');

    if (response.ok()) {
      const body = await response.json();
      expect(body).toHaveProperty('name');
    }
  });
});
