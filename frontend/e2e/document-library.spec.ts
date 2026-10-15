/**
 * E2E for the document library UX (TF-355).
 *
 * Exercises the URL-synced library state introduced in Phase 3:
 *   - View-mode switch (cards ↔ list) persists across page reload via URL
 *     param + localStorage.
 *   - Pagination page persists across reload (URL param).
 *   - Deep-link with query-param filters restores toolbar state on mount.
 *   - Tag filter narrows the visible result set to the tagged document.
 *
 * Pre-requisites: full dev stack running (`just dev-full`) and
 * `setup_e2e_test_data.py` has seeded the e2e user
 * (e2e-test@example.com / E2ETestPassword123). The suite seeds its own
 * documents and tag through the API, so it needs no further fixtures.
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

async function createUserTag(request: APIRequestContext, token: string, name: string): Promise<number> {
  const res = await request.post(`${API_URL}/api/v1/documents/tags`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name, scope: 'user' },
  });
  if (!res.ok()) {
    throw new Error(`Seed: creating document tag ${name} failed: HTTP ${res.status()} ${await res.text()}`);
  }
  const body = await res.json();
  return body.id as number;
}

async function attachTag(request: APIRequestContext, token: string, docId: number, tagId: number): Promise<void> {
  const res = await request.post(`${API_URL}/api/v1/documents/${docId}/tags`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { tag_ids: [tagId] },
  });
  if (!res.ok()) {
    throw new Error(`Seed: attaching tag ${tagId} to document ${docId} failed: HTTP ${res.status()} ${await res.text()}`);
  }
}

async function deleteTag(request: APIRequestContext, token: string, id: number): Promise<void> {
  // Best-effort, like deleteDoc. Only archived tags can be deleted.
  try {
    const headers = { Authorization: `Bearer ${token}` };
    await request.post(`${API_URL}/api/v1/tags/${id}/archive`, { headers });
    await request.delete(`${API_URL}/api/v1/tags/${id}`, { headers });
  } catch {
    // Ignore cleanup errors.
  }
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
  // One worker for the whole block: with fullyParallel every worker would run
  // its own beforeAll and multiply the seed. The API's per-IP rate limit
  // (60/min, RATE_LIMIT_PER_MINUTE) also covers the seed calls, which is why
  // the seed stays small. 'default' still runs every test if one fails.
  test.describe.configure({ mode: 'default' });

  // The UI language follows the browser context (en-US here, unless an account
  // or localStorage says otherwise), so the selectors below avoid visible text:
  // the view toggle is addressed by its value attribute. The onboarding modal
  // would otherwise sit on top of the library and swallow clicks.
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.addInitScript(() => {
      localStorage.setItem('ec_onboarding_modal_dismissed', 'true');
    });
  });

  // Seeded document ids for the pagination test; populated in beforeAll.
  let seededIds: number[] = [];
  // Playwright APIRequestContext is only available inside test hooks.
  // We store the token here so afterAll can reuse it.
  let tokenForCleanup = '';
  // Unique per run; names the seeded documents and the seeded tag.
  const prefix = `tf355-page-${Date.now()}`;
  // Tag attached to the first seeded document only (tag-filter test).
  const tagName = `${prefix}-tag`;
  let seededTagId: number | undefined;

  // Seed 13 tiny docs so there are at least 2 pages at the smallest page
  // size of 12.  Use a timestamp-based prefix to avoid collisions on reruns.
  test.beforeAll(async ({ request }) => {
    tokenForCleanup = await login(request, E2E_TEST_USER);
    const uploads: Promise<number>[] = [];
    for (let i = 0; i < 13; i++) {
      uploads.push(uploadDoc(request, tokenForCleanup, `${prefix}-${i}.txt`));
    }
    seededIds = await Promise.all(uploads);

    seededTagId = await createUserTag(request, tokenForCleanup, tagName);
    await attachTag(request, tokenForCleanup, seededIds[0], seededTagId);
  });

  test.afterAll(async ({ request }) => {
    // Delete all seeded docs; best-effort so test failures don't block cleanup.
    await Promise.all(seededIds.map((id) => deleteDoc(request, tokenForCleanup, id)));
    if (seededTagId !== undefined) {
      await deleteTag(request, tokenForCleanup, seededTagId);
    }
  });

  // -------------------------------------------------------------------------
  // 1. View-mode switch persists across reload
  // -------------------------------------------------------------------------
  test('view-mode switch persists across reload', async ({ authenticatedPage: page }) => {
    await page.goto('/documents');

    // Wait for the toolbar to be ready (list toggle button visible).
    const listButton = page.locator('button[value="list"]');
    await expect(listButton).toBeVisible({ timeout: 15000 });

    // Switch to list view.
    await listButton.click();

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

    // The search box (first toolbar input) should show the query value "test".
    await expect(page.locator('button[value="list"]')).toBeVisible({ timeout: 15000 });
    await expect(page.locator('input[value="test"]')).toBeVisible();

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
    // The beforeAll seeded 13 docs, ensuring ≥2 pages at page size 12.
    // Navigate directly to page 2.
    await page.goto('/documents?page=2&size=12');

    // Wait for the page to load — any document content or the toolbar.
    await expect(page.locator('button[value="list"]')).toBeVisible({ timeout: 15000 });

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
  // 4. Tag filter narrows results
  // -------------------------------------------------------------------------
  test('tag filter narrows results to the tagged document', async ({ authenticatedPage: page }) => {
    // List rows start with the title, which drops the extension. Anchored with
    // a trailing space so `-1` does not also match `-10` … `-12`; the prefix
    // only contains [a-z0-9-], so it needs no escaping.
    const tagged = new RegExp(`^${prefix}-0 `);
    const untagged = new RegExp(`^${prefix}-1 `);

    // Search for this run's seed so other documents of the e2e user don't
    // matter; list view shows one table row per document.
    await page.goto(`/documents?q=${prefix}&view=list`);
    await expect(page.getByRole('row', { name: untagged })).toBeVisible({ timeout: 15000 });

    // MUI Autocomplete: typing filters the options to the seeded tag.
    const tagsCombobox = page.getByRole('combobox', { name: 'Tags' });
    await tagsCombobox.fill(tagName);
    await page.getByRole('option', { name: tagName, exact: true }).click();

    await expect(page).toHaveURL(new RegExp(`tag_ids=${seededTagId}`), { timeout: 5000 });
    await expect(page.getByRole('row', { name: tagged })).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('row', { name: untagged })).toHaveCount(0);
  });
});
