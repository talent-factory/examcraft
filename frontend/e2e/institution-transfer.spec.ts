/**
 * E2E for the SuperAdmin institution-transfer flow (TF-352).
 *
 * Pre-requisites for execution: dev stack running (`just dev-full`); seed
 * data includes a SuperAdmin, ≥2 institutions, and a non-self user with
 * documents in the source institution.
 *
 * To run: just e2e -- institution-transfer.spec.ts
 */
import { test, expect } from '@playwright/test';
import { testLoginApi } from './fixtures/auth';

const SUPERADMIN_EMAIL =
  process.env.E2E_SUPERADMIN_EMAIL ?? 'admin@talent-factory.ch';

test.describe('SuperAdmin Institution-Transfer', () => {
  test.beforeEach(async ({ page }) => {
    // EXAMCRAFT-126: session cookie via the E2E-only test login (no password form).
    await testLoginApi(page.request, SUPERADMIN_EMAIL);
    await page.goto('/dashboard');
    await page.waitForURL(/dashboard|admin|home/, { timeout: 15_000 });
  });

  test('SuperAdmin sees "Institution wechseln" button in user edit dialog', async ({
    page,
  }) => {
    await page.goto('/admin/users');
    await page.waitForLoadState('networkidle');

    // Click the first user's edit button
    const editButtons = page.getByRole('button', {
      name: /bearbeiten|edit/i,
    });
    await editButtons.first().click();

    await expect(
      page.getByRole('button', {
        name: /institution wechseln|move institution/i,
      }),
    ).toBeVisible({ timeout: 5_000 });
  });

  test('opens transfer dialog, loads preview, completes transfer', async ({
    page,
  }) => {
    await page.goto('/admin/users');
    await page.waitForLoadState('networkidle');

    // Open user edit dialog
    const editButtons = page.getByRole('button', {
      name: /bearbeiten|edit/i,
    });
    await editButtons.first().click();

    // Open transfer dialog
    await page
      .getByRole('button', { name: /institution wechseln|move institution/i })
      .click();

    // Verify dialog title is visible
    await expect(
      page.getByRole('heading', {
        name: /institution wechseln|move institution/i,
      }),
    ).toBeVisible();

    // Pick a target institution from the dropdown
    const select = page.getByRole('combobox');
    const optionValues = await select.locator('option').evaluateAll(
      (els) =>
        els
          .map((e) => (e as HTMLOptionElement).value)
          .filter((v) => v),
    );
    expect(optionValues.length).toBeGreaterThan(0);
    await select.selectOption(optionValues[0]);

    // Wait for the document-count preview to render
    await expect(page.getByText(/dokumente|documents/i)).toBeVisible({
      timeout: 10_000,
    });

    // Advance to confirmation step
    await page.getByRole('button', { name: /weiter|next/i }).click();
    await expect(
      page.getByRole('heading', {
        name: /transfer bestätigen|confirm transfer/i,
      }),
    ).toBeVisible();

    // Execute the transfer
    await page
      .getByRole('button', { name: /transfer ausführen|execute/i })
      .click();

    // Confirmation dialog should disappear after success
    await expect(
      page.getByRole('heading', {
        name: /transfer bestätigen|confirm transfer/i,
      }),
    ).not.toBeVisible({ timeout: 10_000 });
  });

  test('proceed button stays disabled when no valid target institution exists', async ({
    page,
  }) => {
    /**
     * Smoke check: even when no valid target exists, the dropdown still
     * renders. The "Next" button should remain disabled.
     *
     * This test is intentionally permissive — it does not assert on the
     * exact number of institutions. It only verifies the disabled-state
     * invariant of the proceed button when no option has been selected.
     */
    await page.goto('/admin/users');
    await page.waitForLoadState('networkidle');

    const editButtons = page.getByRole('button', {
      name: /bearbeiten|edit/i,
    });
    await editButtons.first().click();

    await page
      .getByRole('button', { name: /institution wechseln|move institution/i })
      .click();

    // Without selecting a target, the "Next" / "Weiter" button must be disabled
    const nextBtn = page.getByRole('button', { name: /weiter|next/i });
    await expect(nextBtn).toBeDisabled();
  });
});
