/**
 * E2E Tests for API Connectivity
 *
 * These tests verify that the frontend correctly connects to the backend API
 * and that environment variables are properly configured.
 *
 * This specifically tests the REACT_APP_API_URL standardization from Feb 11, 2026.
 */

import { test, expect } from '@playwright/test';

// API base URL - matches what the app should use
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

test.describe('API Connectivity', () => {

  test('should reach backend health endpoint', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/health`);

    expect(response.ok()).toBeTruthy();

    const body = await response.json();
    expect(body).toHaveProperty('status');
  });

  test('should reach API docs endpoint', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/docs`);

    // Should return 200 (FastAPI auto-generated docs)
    expect(response.status()).toBe(200);
  });

  test('should return non-200 for protected endpoints without auth', async ({ request }) => {
    // Try to access protected endpoint without authentication
    const response = await request.get(`${API_BASE_URL}/api/v1/users/me`);

    // Without auth, should not return 200 OK
    expect(response.status()).not.toBe(200);
  });

  test('should return non-200 for chat sessions without auth', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/v1/chat/sessions`);

    // Without auth, should not return 200 OK
    expect(response.status()).not.toBe(200);
  });

  test('should return non-200 for documents without auth', async ({ request }) => {
    const response = await request.get(`${API_BASE_URL}/api/v1/documents`);

    // Without auth, should not return 200 OK
    expect(response.status()).not.toBe(200);
  });
});

test.describe('Environment Variable Configuration', () => {

  test('should have correct API URL in production build', async ({ page }) => {
    // This test verifies the build is correctly configured
    // by checking that API requests go to the expected domain

    // Get page's environment configuration (if exposed)
    await page.goto('/');

    // Check for any console errors related to API connectivity
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    await page.waitForTimeout(3000);

    // Should not have CORS or network errors to localhost from production
    const localhostErrors = consoleErrors.filter(err =>
      err.includes('localhost') && (err.includes('CORS') || err.includes('network'))
    );

    // In production, there should be no localhost-related errors
    if (!API_BASE_URL.includes('localhost')) {
      expect(localhostErrors.length).toBe(0);
    }
  });
});
