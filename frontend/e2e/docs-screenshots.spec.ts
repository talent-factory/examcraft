/**
 * Documentation Screenshots — TF-341
 *
 * This is a SCREENSHOT GENERATOR, not an assertion test. It is gated behind the
 * CAPTURE_DOCS env var so it is skipped by CI and `just e2e` (which would otherwise
 * try to run it headless without a seeded stack and hang/fail).
 *
 * Run: cd core/frontend && CAPTURE_DOCS=1 npx playwright test docs-screenshots --headed --timeout=300000
 * Prerequisites: just dev-full && just seed && just seed-test-data
 */

import { test, chromium } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

const BASE_URL = 'http://localhost:3000';
const SCREENSHOTS_BASE = path.resolve(__dirname, '../../docs-site/docs/screenshots');
const ADMIN_EMAIL = 'admin@talent-factory.ch';
const ADMIN_PASSWORD = 'admin123'; // pragma: allowlist secret

function sc(folder: string, name: string): string {
  return path.join(SCREENSHOTS_BASE, folder, name);
}

// Tracks captures where the expected anchor element was missing, so a degraded
// run surfaces a non-zero summary instead of silently shipping wrong screenshots.
const suspectShots: string[] = [];

async function snap(page: any, filePath: string, anchor?: string): Promise<void> {
  const rel = path.relative(SCREENSHOTS_BASE, filePath);
  if (anchor) {
    const visible = await page
      .locator(anchor)
      .first()
      .isVisible({ timeout: 1500 })
      .catch(() => false);
    if (!visible) {
      suspectShots.push(rel);
      console.warn(`  ⚠️  Erwartetes Element nicht sichtbar (${anchor}) — Screenshot evtl. falsch: ${rel}`);
    }
  }
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  await page.screenshot({ path: filePath, fullPage: false });
  console.log('  📸', rel);
}

async function goto(page: any, url: string): Promise<void> {
  await page.goto(url, { timeout: 15000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);
}

async function clickTab(page: any, label: string): Promise<void> {
  await page.locator(`[role="tab"]:has-text("${label}")`).click({ timeout: 5000 });
  await page.waitForTimeout(1500);
}

async function tryClick(page: any, selector: string, wait = 800): Promise<boolean> {
  try {
    const el = page.locator(selector).first();
    if (await el.isVisible({ timeout: 1500 })) {
      await el.click();
      await page.waitForTimeout(wait);
      return true;
    }
    console.warn('  ⚠️  tryClick: Element nicht sichtbar —', selector);
  } catch (err) {
    console.warn('  ⚠️  tryClick fehlgeschlagen —', selector, String(err));
  }
  return false;
}

async function closeDialog(page: any): Promise<void> {
  await page.keyboard.press('Escape');
  await page.waitForTimeout(600);
}

test.describe.configure({ mode: 'serial' });

test('capture documentation screenshots', async () => {
  // Screenshot generator, not an assertion test — excluded from CI / `just e2e`.
  // Run manually against the seeded stack via CAPTURE_DOCS=1 (see file header).
  test.skip(
    !process.env.CAPTURE_DOCS,
    'Screenshot-Generator — nur manuell via CAPTURE_DOCS=1 ausführen (siehe Datei-Header).',
  );
  const browser = await chromium.launch({ headless: false });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    locale: 'de-CH',
    colorScheme: 'light',
  });
  const page = await context.newPage();
  try {
    await capture(page);
  } finally {
    await browser.close();
  }
  if (suspectShots.length > 0) {
    throw new Error(
      `${suspectShots.length} Screenshot(s) wurden ohne das erwartete Element aufgenommen ` +
        `und sind vermutlich falsch:\n  - ${suspectShots.join('\n  - ')}`,
    );
  }
  console.log('\n✅ Screenshot capture complete.');
});

async function capture(page: any): Promise<void> {
  // ── Login ──────────────────────────────────────────────────────────────────
  console.log('→ Login');
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1000);
  await page.fill('input[type="email"], #email', ADMIN_EMAIL);
  await page.fill('input[type="password"], #password', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/(dashboard|$)/, { timeout: 20000 });
  await page.waitForTimeout(2000);

  // Dismiss onboarding tour so it never overlaps screenshots
  await page.evaluate(() => {
    localStorage.setItem('ec_onboarding_modal_dismissed', 'true');
  });
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(1500);

  // ── Dashboard ──────────────────────────────────────────────────────────────
  console.log('→ Dashboard');
  await goto(page, `${BASE_URL}/dashboard`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('dashboard', 'dashboard-overview.png'));
  await page.evaluate(() => window.scrollTo(0, 400));
  await page.waitForTimeout(300);
  await snap(page, sc('dashboard', 'dashboard-statistics.png'));
  await page.evaluate(() => window.scrollTo(0, 800));
  await page.waitForTimeout(300);
  await snap(page, sc('dashboard', 'dashboard-recent-activity.png'));
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('aktivitaeten', 'dashboard-widget-link.png'));

  // ── Aktivitäten ────────────────────────────────────────────────────────────
  console.log('→ Aktivitäten');
  await goto(page, `${BASE_URL}/aktivitaeten`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  // Overview: no filters active (all chips selected = default = "show all")
  await snap(page, sc('aktivitaeten', 'aktivitaeten-overview.png'));

  // Filter screenshot: deactivate 3 chips so the others appear highlighted/active.
  // ACTIVITY_TYPES: document_uploaded, document_deleted, questions_generated,
  //   question_approved, question_rejected, exam_created, exam_deleted (all start active).
  // Deactivate document_deleted, question_rejected, exam_deleted →
  //   leaves document_uploaded, questions_generated, question_approved, exam_created active.
  await tryClick(page, '[data-testid="aktivitaeten-chip-document_deleted"]', 300);
  await tryClick(page, '[data-testid="aktivitaeten-chip-question_rejected"]', 300);
  await tryClick(page, '[data-testid="aktivitaeten-chip-exam_deleted"]', 300);
  await page.waitForTimeout(400);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('aktivitaeten', 'aktivitaeten-filter.png'));

  // ── Documents ──────────────────────────────────────────────────────────────
  console.log('→ Documents');
  await goto(page, `${BASE_URL}/documents`);
  await page.waitForTimeout(500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('documents', 'documents-overview.png'));

  // Open preview dialog via the "..." context menu on first document card
  // DocumentLibrary renders a Card per document with a MuiIconButton (MoreVert) in the top-right
  const menuOpened = await (async () => {
    // Try to click the MoreVert icon button inside the first document card
    const selectors = [
      '.MuiCard-root .MuiIconButton-root',
      '[class*="MuiCard"] [class*="MuiIconButton"]',
      'button[class*="MuiIconButton"]',
    ];
    for (const sel of selectors) {
      try {
        const btn = page.locator(sel).first();
        if (await btn.isVisible({ timeout: 1500 })) {
          await btn.click();
          await page.waitForTimeout(600);
          return true;
        }
      } catch { /* try next */ }
    }
    return false;
  })();

  if (menuOpened) {
    // Click "Vorschau" in the context menu
    const previewClicked = await tryClick(
      page,
      '[role="menuitem"]:has-text("Vorschau"), [role="menuitem"]:has-text("Preview"), [role="menuitem"]:has-text("Anzeigen")',
      1200
    );
    if (previewClicked) {
      await page.waitForTimeout(500);
      // Dialog opens on "Original" tab by default for processed documents.
      // Click "Metadaten" tab first to show document metadata view.
      await tryClick(page, '[role="tab"]:has-text("Metadaten")', 800);
      await snap(page, sc('documents', 'documents-preview-dialog.png'), '[role="dialog"]');

      // Switch to "Original" tab (shows embedded PDF/Markdown content)
      await tryClick(page, '[role="tab"]:has-text("Original")', 1000);
      await snap(page, sc('documents', 'documents-preview-original-pdf.png'));

      // Switch to "Chunks" tab (shows extracted text chunks for RAG)
      await tryClick(page, '[role="tab"]:has-text("Chunks")', 800);
      await snap(page, sc('documents', 'documents-preview-original-md.png'));

      await closeDialog(page);
    } else {
      await closeDialog(page);
      await snap(page, sc('documents', 'documents-preview-dialog.png'));
      await snap(page, sc('documents', 'documents-preview-original-pdf.png'));
      await snap(page, sc('documents', 'documents-preview-original-md.png'));
    }
  } else {
    await snap(page, sc('documents', 'documents-preview-dialog.png'));
    await snap(page, sc('documents', 'documents-preview-original-pdf.png'));
    await snap(page, sc('documents', 'documents-preview-original-md.png'));
  }

  // ── Exam Composer ──────────────────────────────────────────────────────────
  console.log('→ Exam Composer');
  await goto(page, `${BASE_URL}/exams/compose`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  // Overview: shows ExamListView with existing exams
  await snap(page, sc('exam-composer', 'exam-composer-overview.png'));

  // "Neue Prüfung erstellen" dialog
  await tryClick(
    page,
    'button:has-text("Neue Prüfung erstellen"), button:has-text("Prüfung erstellen"), button:has-text("Neu erstellen"), button:has-text("Neue Prüfung")',
    1000
  );
  await snap(page, sc('exam-composer', 'exam-composer-new.png'));
  await closeDialog(page);
  await page.waitForTimeout(500);

  // Enter the "Algorithmen & Datenstrukturen" exam builder by clicking its card
  const algorithmExamOpened = await tryClick(
    page,
    '.card.cursor-pointer:has-text("Algorithmen"), div.cursor-pointer:has-text("Algorithmen"), div[class*="cursor-pointer"]:has-text("Algorithmen")',
    2500
  );
  if (algorithmExamOpened) {
    await page.waitForSelector('[data-testid="exam-builder"]', { timeout: 5000 });
    await page.waitForTimeout(800);
    await page.evaluate(() => window.scrollTo(0, 0));

    // exam-composer-grading-scheme: Open the "Metadaten bearbeiten" dialog to show
    // the grading scheme selector. The edit button only shows for DRAFT exams.
    const editMetaClicked = await tryClick(
      page,
      'button:has-text("Metadaten bearbeiten")',
      1000
    );
    if (editMetaClicked) {
      await page.waitForTimeout(600);
      // Open the grading scheme Select dropdown
      const schemeDropdown = page.locator('[data-testid="grading-scheme-select"]');
      try {
        if (await schemeDropdown.isVisible({ timeout: 2000 })) {
          await schemeDropdown.click();
          await page.waitForTimeout(700);
          await snap(page, sc('exam-composer', 'exam-composer-grading-scheme.png'), '[data-testid="grading-scheme-select"]');
          await page.keyboard.press('Escape'); // close dropdown
          await page.waitForTimeout(300);
        } else {
          await snap(page, sc('exam-composer', 'exam-composer-grading-scheme.png'));
        }
      } catch {
        await snap(page, sc('exam-composer', 'exam-composer-grading-scheme.png'));
      }
      // Close the edit dialog
      await page.keyboard.press('Escape');
      await page.waitForTimeout(500);
    } else {
      await snap(page, sc('exam-composer', 'exam-composer-grading-scheme.png'));
    }

    // exam-composer-question-selection: Show the full builder layout — left panel (QuestionPoolPanel)
    // is visible on the left half, right panel (ExamQuestionsPanel) on the right
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(300);
    await snap(page, sc('exam-composer', 'exam-composer-question-selection.png'));

    // exam-composer-reorder: Scroll down to show the questions in both panels
    await page.evaluate(() => window.scrollTo(0, 200));
    await page.waitForTimeout(400);
    await snap(page, sc('exam-composer', 'exam-composer-reorder.png'));

    // Open export dialog for exam-composer-export screenshot
    const exportOpened = await tryClick(
      page,
      'button:has-text("Exportieren"), button:has-text("Export")',
      1000
    );
    await snap(page, sc('exam-composer', 'exam-composer-export.png'));
    await closeDialog(page);
    await page.waitForTimeout(400);

    // Finalize the exam (DRAFT → FINALIZED) so Auswertungen overview shows correct status
    const finalizeClicked = await tryClick(
      page,
      'button:has-text("Finalisieren")',
      2000
    );
    if (finalizeClicked) {
      await page.waitForTimeout(1200); // wait for finalization to complete
    }

    // exam-composer-builder: Fresh navigation back to list (instead of back button click)
    // so TanStack Query re-fetches and shows the updated "Finalisiert" status.
    await goto(page, `${BASE_URL}/exams/compose`);
    await page.evaluate(() => window.scrollTo(0, 0));
    await snap(page, sc('exam-composer', 'exam-composer-builder.png'));
  } else {
    // Fallback: take snapshots of current state
    await snap(page, sc('exam-composer', 'exam-composer-grading-scheme.png'));
    await snap(page, sc('exam-composer', 'exam-composer-question-selection.png'));
    await snap(page, sc('exam-composer', 'exam-composer-reorder.png'));
    await snap(page, sc('exam-composer', 'exam-composer-builder.png'));
    await snap(page, sc('exam-composer', 'exam-composer-export.png'));
  }

  // ── Subscription ───────────────────────────────────────────────────────────
  console.log('→ Subscription');
  await goto(page, `${BASE_URL}/subscription`);
  await snap(page, sc('subscription', 'subscription-page.png'));
  await goto(page, `${BASE_URL}/billing`);
  await snap(page, sc('subscription', 'billing-page.png'));

  // ── Admin ──────────────────────────────────────────────────────────────────
  console.log('→ Admin');
  await goto(page, `${BASE_URL}/admin`);
  try {
    const rolesTab = page.locator('[role="tab"]:has-text("Rollen"), [role="tab"]:has-text("Roles")');
    if (await rolesTab.isVisible({ timeout: 1000 })) {
      await rolesTab.click();
      await page.waitForTimeout(500);
    }
  } catch { /* no roles tab */ }
  await snap(page, sc('admin', 'admin-roles.png'));

  // ── Auswertungen overview ──────────────────────────────────────────────────
  console.log('→ Auswertungen');
  await goto(page, `${BASE_URL}/auswertungen`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('auswertungen', 'auswertungen-overview.png'));

  // Find the "Algorithmen & Datenstrukturen" exam (our seeded exam with real data)
  // Use the row with "Algorithmen" in the title for reliable exam ID discovery
  let examId = '';
  try {
    // The auswertungen table renders: <tr> with exam title in first cell and evaluate button
    const algorithmRow = page.locator('table tbody tr').filter({ hasText: 'Algorithmen' }).first();
    if (await algorithmRow.isVisible({ timeout: 2000 })) {
      const evalBtn = algorithmRow.locator('[data-testid$="-evaluate"]').first();
      const tid = await evalBtn.getAttribute('data-testid', { timeout: 2000 });
      examId = tid?.match(/exam-(\d+)-evaluate/)?.[1] ?? '';
    } else {
      // Fallback: use first evaluate button found
      const btn = page.locator('[data-testid^="exam-"][data-testid$="-evaluate"]').first();
      const tid = await btn.getAttribute('data-testid', { timeout: 3000 });
      examId = tid?.match(/exam-(\d+)-evaluate/)?.[1] ?? '';
    }
  } catch { /* handled below */ }
  if (!examId) {
    throw new Error(
      'Konnte die ID des Seed-Exams "Algorithmen & Datenstrukturen" nicht ermitteln. ' +
        'Wurde "just seed-test-data" ausgeführt? Ohne dieses Exam wären alle folgenden ' +
        'Auswertungs-, Statistik- und Notenexport-Screenshots ungültig.',
    );
  }
  console.log(`   examId: ${examId}`);

  // Import dialog — step 1 (CSV source selected, default state)
  // auswertungen-import-dialog: shows the dialog in default state (CSV)
  await tryClick(page, `[data-testid="exam-${examId}-import"]`, 1200);
  await page.waitForTimeout(500);
  await snap(page, sc('auswertungen', 'auswertungen-import-dialog.png'));

  // Advance to upload step to show different state
  await tryClick(
    page,
    'button:has-text("Weiter"), button:has-text("Next"), button:has-text("Fortfahren")',
    1000
  );
  await snap(page, sc('auswertungen', 'auswertungen-import-preview.png'));
  await closeDialog(page);

  // Navigate to exam detail → Submissions tab
  console.log('→ Auswertungen Exam Detail');
  await goto(page, `${BASE_URL}/auswertungen/${examId}/submissions`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await snap(page, sc('auswertungen', 'auswertungen-submissions-tab.png'));

  // Click first submission row → drawer
  const drawerOpened = await tryClick(page, 'table tbody tr', 1200);
  await snap(page, sc('auswertungen', 'auswertungen-submission-drawer.png'), '.MuiDrawer-root, [role="dialog"]');
  await closeDialog(page);
  await page.waitForTimeout(500);

  // ── Review Queue ──────────────────────────────────────────────────────────
  console.log('→ Review Queue');
  await clickTab(page, 'Review');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1000); // wait for ReviewQueue to load

  // review-queue-overview: full overview of review queue, scroll to top
  await snap(page, sc('review-grading', 'review-queue-overview.png'));

  // review-queue-filter: shows filter section (confidence range, question/student filters)
  // The filter controls are at the top of the ReviewQueue component
  // Interact with a filter to show it in active state
  await tryClick(page, '[data-testid="filter-question"]', 600);
  await page.waitForTimeout(300);
  await snap(page, sc('review-grading', 'review-queue-filter.png'));
  await page.keyboard.press('Escape'); // close any open dropdown
  await page.waitForTimeout(400);

  // review-queue-card: scroll to first review card to show it prominently
  await page.evaluate(() => window.scrollTo(0, 350));
  await page.waitForTimeout(500);
  await snap(page, sc('review-grading', 'review-queue-card.png'));

  // review-queue-bulk: select first item via checkbox to show bulk action bar
  const firstCheckbox = page.locator('[data-testid^="select-"]').first();
  try {
    if (await firstCheckbox.isVisible({ timeout: 2000 })) {
      await firstCheckbox.click();
      await page.waitForTimeout(500);
      await page.evaluate(() => window.scrollTo(0, 0));
      await snap(page, sc('review-grading', 'review-queue-bulk.png'));
      // Deselect by clicking again
      await firstCheckbox.click();
      await page.waitForTimeout(300);
    } else {
      await page.evaluate(() => window.scrollTo(0, 0));
      await snap(page, sc('review-grading', 'review-queue-bulk.png'));
    }
  } catch {
    await page.evaluate(() => window.scrollTo(0, 0));
    await snap(page, sc('review-grading', 'review-queue-bulk.png'));
  }

  // review-queue-override: open override dialog for first card
  await page.evaluate(() => window.scrollTo(0, 350));
  await page.waitForTimeout(400);
  const overrideOpened = await tryClick(page, '[data-testid^="override-"]', 1000);
  await snap(page, sc('review-grading', 'review-queue-override.png'), '[role="dialog"]');
  await closeDialog(page);

  // ── Statistik ─────────────────────────────────────────────────────────────
  console.log('→ Statistik');
  await clickTab(page, 'Statistik');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1500); // wait for statistics to load
  // statistik-kpis: KPI cards at the very top
  await snap(page, sc('statistik', 'statistik-kpis.png'));

  // statistik-histogramm: histogram section (scroll down past KPI cards)
  await page.evaluate(() => window.scrollTo(0, 300));
  await page.waitForTimeout(400);
  await snap(page, sc('statistik', 'statistik-histogramm.png'));

  // statistik-per-question: show table header + first rows (default position sort)
  await page.evaluate(() => window.scrollTo(0, 500));
  await page.waitForTimeout(400);
  await snap(page, sc('statistik', 'statistik-per-question.png'));

  // statistik-lerneffekt: sort by Erfolgsquote (success_rate) so the Lerneffekt
  // column values are sorted differently and the active sort column changes visually.
  // The per-question table has 4 sort labels: Position(0), Erfolgsquote(1), Schwierigkeit(2), Trennschärfe(3).
  try {
    const sortLabels = page.locator('[data-testid="per-question-table"] .MuiTableSortLabel-root');
    const successRateLabel = sortLabels.nth(1);
    if (await successRateLabel.isVisible({ timeout: 2000 })) {
      await successRateLabel.click();
      await page.waitForTimeout(500);
    }
  } catch { /* ignore */ }
  await page.evaluate(() => window.scrollTo(0, 500));
  await page.waitForTimeout(300);
  await snap(page, sc('statistik', 'statistik-lerneffekt.png'));

  // ── Notenexport ───────────────────────────────────────────────────────────
  console.log('→ Notenexport');
  await clickTab(page, 'Notenexport');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(800);

  // notenexport-blocked: real data — warning banner visible (pendingCount > 0),
  // CSV selected, download button disabled. Shows the "gesperrt" state for docs.
  await snap(page, sc('notenexport', 'notenexport-blocked.png'));

  // notenexport-format-selection + notenexport-pdf-preview: intercept the submissions
  // API to return pending_count=0 so the panel shows the unblocked state (no warning
  // banner, active download button). The real submission data is preserved.
  let pendingCountSeen = false;
  await page.route('**/api/v1/submissions*', async (route) => {
    const response = await route.fetch();
    const json = await response.json();
    if ('pending_count' in json) {
      pendingCountSeen = true;
      json.pending_count = 0;
    }
    await route.fulfill({ response, body: JSON.stringify(json) });
  });
  // Re-navigate to reload submission data with the mocked pending_count=0
  await goto(page, `${BASE_URL}/auswertungen/${examId}/submissions`);
  await clickTab(page, 'Notenexport');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(800);

  // If the submissions API no longer carries pending_count, the mock silently did
  // nothing and the panel still shows the BLOCKED state — capturing it would publish
  // a screenshot that contradicts the surrounding docs. Fail loudly instead.
  if (!pendingCountSeen) {
    await page.unroute('**/api/v1/submissions*');
    throw new Error(
      'Submissions-API enthielt kein "pending_count"-Feld — die Notenexport-Mock-Annahme ist ' +
        'gebrochen. Der "freigegeben"-Screenshot würde fälschlich den gesperrten Zustand zeigen. ' +
        'Mock in docs-screenshots.spec.ts an das neue API-Schema anpassen.',
    );
  }

  // notenexport-format-selection: unblocked state, CSV selected, no warning banner
  await snap(page, sc('notenexport', 'notenexport-format-selection.png'));

  // notenexport-pdf-preview: select PDF format in unblocked state
  await tryClick(
    page,
    '[data-testid="notenexport-format-pdf"], label:has-text("PDF Notenliste")',
    800
  );
  await snap(page, sc('notenexport', 'notenexport-pdf-preview.png'));

  // Remove route mock before continuing
  await page.unroute('**/api/v1/submissions*');

  // ── Moodle Sync Question IDs dialog ───────────────────────────────────────
  console.log('→ Moodle Sync');
  // The sync button is in the exam detail header/metadata area
  const syncOpened = await tryClick(page, '[data-testid="auswertungen-exam-sync-moodle"]', 1000);
  await snap(page, sc('moodle', 'moodle-sync-question-ids.png'), '[role="dialog"]');
  await closeDialog(page);

  // ── Moodle Import API (ImportDialog with Moodle API option) ───────────────
  console.log('→ Moodle Import API Dialog');
  await goto(page, `${BASE_URL}/auswertungen`);
  await page.waitForTimeout(500);
  // Intercept the Moodle connections probe so the "Moodle Web-Service-API" radio
  // appears enabled without a real Moodle server. Clicking the radio only sets
  // React state — no backend call happens at this point.
  await page.route('**/api/v1/admin/moodle-connections*', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [{ id: 1, institution_id: 1, base_url: 'https://moodle.example.com', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }],
          total: 1,
        }),
      });
    } else {
      await route.continue();
    }
  });
  await tryClick(page, `[data-testid="exam-${examId}-import"]`, 1200);
  await page.waitForTimeout(1500); // wait for connection probe to complete + React re-render
  // Click "Moodle Web-Service-API" label (enabled because mock returns a connection)
  await tryClick(page, 'label:has-text("Moodle Web-Service")', 800);
  await snap(page, sc('moodle', 'moodle-import-api.png'), '[role="dialog"]');
  await closeDialog(page);
  await page.unroute('**/api/v1/admin/moodle-connections*');

  // ── Admin Moodle connection form ──────────────────────────────────────────
  console.log('→ Admin Moodle');
  await goto(page, `${BASE_URL}/admin/integrations/moodle`);
  await page.waitForTimeout(500);
  await snap(page, sc('moodle', 'moodle-connection-form.png'));

  // ── Klassen ────────────────────────────────────────────────────────────────
  console.log('→ Klassen');
  await goto(page, `${BASE_URL}/auswertungen/klassen`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await snap(page, sc('klassen', 'klassen-liste.png'));

  try {
    const row = page.locator('table tbody tr, [data-testid^="class-row-"], .cursor-pointer').first();
    if (await row.isVisible({ timeout: 1500 })) {
      await row.click();
      await page.waitForURL(/\/klassen\/\d+/, { timeout: 5000 });
      await page.waitForTimeout(1500);
      await page.evaluate(() => window.scrollTo(0, 0));
      await snap(page, sc('klassen', 'klassen-detail.png'));
    } else {
      await snap(page, sc('klassen', 'klassen-detail.png'));
    }
  } catch { await snap(page, sc('klassen', 'klassen-detail.png')); }

  // ── Studierende ────────────────────────────────────────────────────────────
  console.log('→ Studierende');
  await goto(page, `${BASE_URL}/auswertungen/studierende`);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(500);
  await snap(page, sc('klassen', 'studierende-liste.png'));

  try {
    const row = page.locator('table tbody tr, [data-testid^="student-row-"], .cursor-pointer').first();
    if (await row.isVisible({ timeout: 1500 })) {
      await row.click();
      await page.waitForURL(/\/studierende\/\d+/, { timeout: 5000 });
      await page.waitForTimeout(1500);
      await page.evaluate(() => window.scrollTo(0, 0));
      await snap(page, sc('klassen', 'studierende-detail.png'));
    } else {
      await snap(page, sc('klassen', 'studierende-detail.png'));
    }
  } catch { await snap(page, sc('klassen', 'studierende-detail.png')); }
}
