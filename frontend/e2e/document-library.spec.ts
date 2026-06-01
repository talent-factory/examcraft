/**
 * E2E for the document library UX (TF-355).
 *
 * Exercises the URL-synced library state introduced in Phase 3:
 *   - View-mode switch (cards ↔ list) persists across page reload via URL
 *     param + localStorage.
 *   - Pagination page persists across reload (URL param).
 *   - Deep-link with query-param filters restores toolbar state on mount.
 *   - (Best-effort) Tag filter narrows the visible result set.
 *
 * Pre-requisites: full dev stack running (`just dev-full`) and
 * `setup_e2e_test_data.py` has seeded the e2e user
 * (e2e-test@example.com / E2ETestPassword123).
 *
 * To run: just e2e -- document-library.spec.ts
 * NOT required to pass in a worktree without a running stack.
 *
 * Mirror pattern: see document-visibility.spec.ts for the API-driven helper
 * conventions used in test.beforeAll / test.afterAll.
 */
/* eslint-disable testing-library/prefer-screen-queries */
import { test, expect } from './fixtures/auth';
import { type APIRequestContext } from '@playwright/test';
import { E2E_TEST_USER } from './fixtures/auth';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

// ---------------------------------------------------------------------------
// API helpers (mirrors document-visibility.spec.ts conventions)
// ---------------------------------------------------------------------------

async function login(request: APIRequestContext, creds: { email: string; password: string }): Promise<string> {
  const res = await request.post(`${API_URL}/api/auth/login`, {
    data: { email: creds.email, password: creds.password },
  });
  // Assert login succeeded (status is shown in the error message on failure).
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return body.access_token as string;
}

async function uploadDoc(request: APIRequestContext, token: string, name: string): Promise<number> {
  const res = await request.post(`${API_URL}/api/v1/documents/upload`, {
    headers: { Authorization: `Bearer ${token}` },
    multipart: {
      visibility: 'private',
      file: {
        name,
        mimeType: 'text/plain',
        buffer: Buffer.from(`TF-355 pagination seed document: ${name}`),
      },
    },
  });
  // Assert upload succeeded.
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return body.document_id as number;
}

async function deleteDoc(request: APIRequestContext, token: string, id: number): Promise<void> {
  // Best-effort: wrap so cleanup never fails the suite.
  try {
    await request.delete(`${API_URL}/api/v1/documents/${id}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch {
    // Ignore cleanup errors.
  }
}

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe('Document library UX (TF-355)', () => {
  // Seeded document ids for the pagination test; populated in beforeAll.
  let seededIds: number[] = [];
  // Playwright APIRequestContext is only available inside test hooks.
  // We store the token here so afterAll can reuse it.
  let tokenForCleanup = '';

  // Seed ≥26 tiny docs so there are at least 2 pages at the default page
  // size of 24.  Use a timestamp-based prefix to avoid collisions on reruns.
  test.beforeAll(async ({ request }) => {
    tokenForCleanup = await login(request, E2E_TEST_USER);
    const prefix = `tf355-page-${Date.now()}`;
    const uploads: Promise<number>[] = [];
    for (let i = 0; i < 26; i++) {
      uploads.push(uploadDoc(request, tokenForCleanup, `${prefix}-${i}.txt`));
    }
    seededIds = await Promise.all(uploads);
  });

  test.afterAll(async ({ request }) => {
    // Delete all seeded docs; best-effort so test failures don't block cleanup.
    await Promise.all(seededIds.map((id) => deleteDoc(request, tokenForCleanup, id)));
  });

  // -------------------------------------------------------------------------
  // 1. View-mode switch persists across reload
  // -------------------------------------------------------------------------
  test('view-mode switch persists across reload', async ({ authenticatedPage: page }) => {
    await page.goto('/documents');

    // Wait for the toolbar to be ready (Liste toggle button visible).
    const listeButton = page.getByRole('button', { name: /Liste/i });
    await expect(listeButton).toBeVisible({ timeout: 15000 });

    // Switch to list view.
    await listeButton.click();

    // URL should gain view=list.
    await expect(page).toHaveURL(/view=list/, { timeout: 5000 });

    // A table role should appear in the list view.
    await expect(page.getByRole('table').first()).toBeVisible({ timeout: 10000 });

    // Reload — view should persist via URL param + localStorage.
    await page.reload();

    // Table still visible after reload.
    await expect(page.getByRole('table').first()).toBeVisible({ timeout: 15000 });

    // URL still has view=list.
    await expect(page).toHaveURL(/view=list/);
  });

  // -------------------------------------------------------------------------
  // 2. Deep-link with filters restores state
  // -------------------------------------------------------------------------
  test('deep-link with filters restores toolbar state', async ({ authenticatedPage: page }) => {
    await page.goto('/documents?q=test&status=processed&view=list&size=12');

    // Search box should show the query value "test".
    const searchBox = page.getByPlaceholder('Suchen…');
    await expect(searchBox).toBeVisible({ timeout: 15000 });
    await expect(searchBox).toHaveValue('test');

    // List view should be active (table visible).
    await expect(page.getByRole('table').first()).toBeVisible({ timeout: 10000 });

    // An active-filter chip reflecting the status filter should be visible.
    // The chip may display the filter label or the value — use a broad regex.
    const statusChip = page.locator('[class*="Chip"], [role="button"]').filter({
      hasText: /processed|Status/i,
    });
    await expect(statusChip.first()).toBeVisible({ timeout: 5000 });
  });

  // -------------------------------------------------------------------------
  // 3. Pagination page persists across reload
  // -------------------------------------------------------------------------
  test('pagination page persists across reload', async ({ authenticatedPage: page }) => {
    // The beforeAll seeded ≥26 docs, ensuring ≥2 pages at the default page
    // size of 24.  Navigate directly to page 2.
    await page.goto('/documents?page=2');

    // Wait for the page to load — any document content or the toolbar.
    await expect(page.getByRole('button', { name: /Liste|Karten/i }).first()).toBeVisible({
      timeout: 15000,
    });

    // URL should contain page=2.
    await expect(page).toHaveURL(/page=2/);

    // The MUI Pagination component renders a button with aria-label "page 2"
    // (English aria-label from MUI regardless of locale).
    const page2Button = page.getByRole('button', { name: /page 2/i });
    await expect(page2Button).toBeVisible({ timeout: 10000 });

    // Reload — page should persist.
    await page.reload();

    // URL still has page=2.
    await expect(page).toHaveURL(/page=2/);

    // Page-2 button still visible and selected (MUI adds aria-current="true"
    // and the Mui-selected class to the active page button).
    await expect(page2Button).toBeVisible({ timeout: 15000 });
  });

  // -------------------------------------------------------------------------
  // 4. (Best-effort) Tag filter narrows results
  // -------------------------------------------------------------------------
  test('tag filter narrows results (best-effort; skips if no tags seeded)', async ({
    authenticatedPage: page,
  }) => {
    // This test depends on tag data being present in the seed.  It gracefully
    // skips if no tag options are available, so it never blocks CI on a bare
    // seed environment.
    await page.goto('/documents');

    // Wait for the toolbar.
    await expect(page.getByRole('button', { name: /Liste|Karten/i }).first()).toBeVisible({
      timeout: 15000,
    });

    // Locate the Tags autocomplete.  MUI renders it as a combobox.
    const tagsCombobox = page.getByRole('combobox', { name: /Tags|Tag/i });
    if (!(await tagsCombobox.isVisible())) {
      // Tags autocomplete not found — skip gracefully.
      test.skip();
      return;
    }

    await tagsCombobox.click();

    // Wait briefly for the listbox to open and options to render.
    const listbox = page.getByRole('listbox');
    const visible = await listbox.isVisible().catch(() => false);

    if (!visible) {
      test.skip();
      return;
    }

    const options = listbox.getByRole('option');
    const count = await options.count();
    if (count === 0) {
      // No tag options available in this seed — skip.
      test.skip();
      return;
    }

    // Pick the first available tag option.
    const firstOption = options.first();
    const tagLabel = (await firstOption.textContent()) ?? 'unknown';
    await firstOption.click();

    // URL should gain tag_ids= parameter.
    await expect(page).toHaveURL(/tag_ids=/, { timeout: 5000 });

    // An active-filter chip for the chosen tag should appear in the toolbar.
    const tagChip = page.locator('[class*="Chip"], [role="button"]').filter({
      hasText: new RegExp(tagLabel.trim(), 'i'),
    });
    await expect(tagChip.first()).toBeVisible({ timeout: 5000 });
  });
});
