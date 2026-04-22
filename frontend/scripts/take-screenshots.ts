/**
 * ExamCraft AI — Dokumentations-Screenshots
 *
 * Erstellt alle Screenshots für core/docs-site/docs/screenshots/
 * Voraussetzung: App läuft auf http://localhost:3000
 * Credentials: SCREENSHOT_EMAIL + SCREENSHOT_PASSWORD in .env
 *
 * Verwendung:
 *   bun run scripts/take-screenshots.ts --check   # Erst prüfen
 *   bun run scripts/take-screenshots.ts           # Screenshots aufnehmen
 */

import { chromium, type Page, type ConsoleMessage } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

// .env aus Repo-Root laden
const envPath = path.resolve(import.meta.dir, '../../../.env');
// Bun ignoriert dotenv override — .env manuell lesen und process.env direkt setzen
if (fs.existsSync(envPath)) {
  const envContent = fs.readFileSync(envPath, 'utf-8');
  for (const line of envContent.split('\n')) {
    const match = line.match(/^([A-Z_][A-Z0-9_]*)=(.*)$/);
    if (match) {
      process.env[match[1]] = match[2].replace(/^["']|["']$/g, '');
    }
  }
}

const BASE_URL = 'http://localhost:3000';
const DOCS_SCREENSHOTS = path.resolve(
  import.meta.dir,
  '../../docs-site/docs/screenshots'
);
const VIEWPORT = { width: 1440, height: 900 };
const ANIMATION_PAUSE_MS = 300;
const ACTION_PAUSE_MS = 500;
// Pause between screenshots to stay within rate limit (60 req/min default).
// Each page.goto() triggers auth/me + page API calls (~3 req).
// 17 screenshots × 3s = +51s; total ~80s for ~50 requests = ~37 req/min.
const INTER_SCREENSHOT_PAUSE_MS = 3000;
const CHAT_RESPONSE_WAIT_MS = 3000;
const PAGE_TIMEOUT_MS = 15000;
const MAX_ERROR_LENGTH = 150;
const MAX_ALERT_LENGTH = 100;
const SELECTOR_TIMEOUT_MS = 10000;
const CHECK_SLOW_MO = 50;
const SCREENSHOT_SLOW_MO = 100;
const WIZARD_CONTEXT_WAIT_MS = 3000;
const WIZARD_GENERATE_TIMEOUT_MS = 60000;
const CHECK_MODE = process.argv.includes('--check');

// --only flag: nur bestimmte Screenshots aufnehmen (Komma-getrennt, ohne .png)
// Beispiel: bun run scripts/take-screenshots.ts --only dashboard-recent-activity,exam-composer-builder

const EMAIL = process.env.SCREENSHOT_EMAIL;
const PASSWORD = process.env.SCREENSHOT_PASSWORD;

if (!EMAIL || !PASSWORD) {
  console.error('❌ SCREENSHOT_EMAIL und SCREENSHOT_PASSWORD müssen in .env gesetzt sein');
  process.exit(1);
}

// --- Typen ---

interface ScreenshotDef {
  route: string;
  file: string;
  dir: string;
  label: string;
  requiresAuth?: boolean;
  requiresFreshLogin?: boolean; // Re-Login vor dieser Route erzwingen
  waitFor?: string;
  clip?: { x: number; y: number; width: number; height: number };
  clipFn?: (page: Page) => Promise<{ x: number; y: number; width: number; height: number } | null>;
  action?: (page: Page, dataStatus?: DataStatus) => Promise<void>;
  skipAutoShot?: boolean;
  /** Sub-Screenshots die von der action() erzeugt werden (für --only Filter). */
  subFiles?: string[];
}

const ONLY_IDX = process.argv.indexOf('--only');
const ONLY_FILES: Set<string> = (ONLY_IDX >= 0 && process.argv[ONLY_IDX + 1])
  ? new Set(process.argv[ONLY_IDX + 1].split(',').map((f) => f.trim().replace(/\.png$/, '')).filter(Boolean))
  : new Set();

/** Gibt true zurück wenn der Sub-Screenshot aufgenommen werden soll. */
function shouldCapture(filename: string): boolean {
  if (ONLY_FILES.size === 0) return true;
  return ONLY_FILES.has(filename.replace(/\.png$/, ''));
}

/** Gibt true zurück wenn dieser SCREENSHOTS-Eintrag ausgeführt werden soll. */
function isInScope(def: ScreenshotDef): boolean {
  if (ONLY_FILES.size === 0) return true;
  const key = def.file.replace(/\.png$/, '');
  if (ONLY_FILES.has(key)) return true;
  return def.subFiles?.some((f) => ONLY_FILES.has(f.replace(/\.png$/, ''))) ?? false;
}

interface CheckResult {
  route: string;
  label: string;
  ok: boolean;
  issues: string[];
}

interface DataStatus {
  hasDocuments: boolean;
  hasReviewQuestions: boolean;
  hasChatSessions: boolean;
  hasExams: boolean;
}

// --- Data-Preflight-Prüfung ---

async function runDataPreflight(page: Page): Promise<DataStatus> {
  console.log('\nData-Preflight-Check…');

  const status: DataStatus = {
    hasDocuments: false,
    hasReviewQuestions: false,
    hasChatSessions: false,
    hasExams: false,
  };

  // Token einmalig aus Browser-localStorage holen
  const token: string | null = await page.evaluate(() =>
    localStorage.getItem('examcraft_access_token')
  );
  if (!token) {
    console.warn('  ⚠ Preflight: kein Auth-Token — alle datenabhängigen Screenshots werden übersprungen');
    return status;
  }

  const BACKEND = 'http://localhost:8000';
  const headers = { Authorization: `Bearer ${token}` };

  // Dokumente prüfen (direkt aus Bun-Prozess — kein CORS)
  try {
    const r = await fetch(`${BACKEND}/api/v1/documents/?limit=1`, { headers });
    if (!r.ok) {
      console.warn(`  ⚠ Preflight Dokumente: HTTP ${r.status}`);
    } else {
      const data = await r.json();
      const count = Array.isArray(data.documents) ? data.documents.length : (Array.isArray(data) ? data.length : 0);
      status.hasDocuments = count > 0;
      console.log(`  ${status.hasDocuments ? '✓' : '✗'} Dokumente: ${count}`);
    }
  } catch (err) {
    console.warn(`  ⚠ Preflight Dokumente: ${(err as Error).message}`);
  }

  // Review-Fragen prüfen
  try {
    const r = await fetch(`${BACKEND}/api/v1/questions/review?limit=1`, { headers });
    if (!r.ok) {
      console.warn(`  ⚠ Preflight Review-Fragen: HTTP ${r.status}`);
    } else {
      const data = await r.json();
      const count = Array.isArray(data.questions) ? data.questions.length : (Array.isArray(data) ? data.length : 0);
      status.hasReviewQuestions = count > 0;
      console.log(`  ${status.hasReviewQuestions ? '✓' : '✗'} Review-Fragen: ${count}`);
    }
  } catch (err) {
    console.warn(`  ⚠ Preflight Review-Fragen: ${(err as Error).message}`);
  }

  // Chat-Sessions prüfen
  try {
    const r = await fetch(`${BACKEND}/api/v1/chat/sessions`, { headers });
    if (!r.ok) {
      console.warn(`  ⚠ Preflight Chat-Sessions: HTTP ${r.status}`);
    } else {
      const data = await r.json();
      const count = Array.isArray(data) ? data.length : 0;
      status.hasChatSessions = count > 0;
      console.log(`  ${status.hasChatSessions ? '✓' : '✗'} Chat-Sessions: ${count}`);
    }
  } catch (err) {
    console.warn(`  ⚠ Preflight Chat-Sessions: ${(err as Error).message}`);
  }

  // Exams prüfen (für Exam-Composer)
  try {
    const r = await fetch(`${BACKEND}/api/v1/exams/`, { headers });
    if (!r.ok) {
      console.warn(`  ⚠ Preflight Exams: HTTP ${r.status}`);
    } else {
      const data = await r.json();
      const count = Array.isArray(data.exams) ? data.exams.length : (Array.isArray(data) ? data.length : 0);
      status.hasExams = count > 0;
      console.log(`  ${status.hasExams ? '✓' : '✗'} Exams: ${count}`);
    }
  } catch (err) {
    console.warn(`  ⚠ Preflight Exams: ${(err as Error).message}`);
  }

  return status;
}

// --- Hilfsfunktionen für Screenshots ---

async function clickAdminTab(page: Page, label: string): Promise<void> {
  const tab = page.locator(`button:has-text("${label}")`).first();
  await tab.waitFor({ state: 'visible', timeout: SELECTOR_TIMEOUT_MS });
  await tab.click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(ACTION_PAUSE_MS);
}

// --- Screenshot-Definitionen ---

const SCREENSHOTS: ScreenshotDef[] = [
  // Auth (kein Login nötig)
  {
    route: '/login',
    file: 'login.png',
    dir: 'auth',
    label: 'Login-Seite',
    requiresAuth: false,
    waitFor: 'form',
  },
  {
    route: '/register',
    file: 'register.png',
    dir: 'auth',
    label: 'Registrierungsseite',
    requiresAuth: false,
    waitFor: 'form',
  },

  // Dashboard
  {
    route: '/dashboard',
    file: 'dashboard-overview.png',
    dir: 'dashboard',
    label: 'Dashboard Übersicht',
    waitFor: 'main',
  },
  {
    route: '/dashboard',
    file: 'dashboard-statistics.png',
    dir: 'dashboard',
    label: 'Dashboard Statistiken',
    waitFor: 'main',
    clipFn: async (page) => {
      const h2 = page.locator('h2').filter({ hasText: /Statistiken|statistics/i }).first();
      const section = h2.locator('xpath=..');
      const bbox = await section.boundingBox().catch(() => null);
      if (!bbox) return null;
      return { x: 0, y: Math.max(0, bbox.y - 8), width: VIEWPORT.width, height: bbox.height + 16 };
    },
  },
  {
    route: '/dashboard',
    file: 'dashboard-recent-activity.png',
    dir: 'dashboard',
    label: 'Dashboard Letzte Aktivitäten',
    waitFor: 'main',
    skipAutoShot: true,
    action: async (page) => {
      // clipFn-Ansatz funktioniert nicht für Elemente unterhalb des Viewports
      // (boundingBox liefert Viewport-relative Koordinaten — ausserhalb des Viewports = leerer Clip).
      // Lösung: element.screenshot() scrollt automatisch und schneidet exakt den Abschnitt aus.
      const h2 = page.locator('h2').filter({ hasText: /Letzte Aktivitäten|recent activity/i }).first();
      const section = h2.locator('xpath=..');
      await section.scrollIntoViewIfNeeded();
      await page.waitForTimeout(300);
      await section.screenshot({
        path: path.join(DOCS_SCREENSHOTS, 'dashboard', 'dashboard-recent-activity.png'),
      });
      console.log('  ✓ dashboard-recent-activity.png');
    },
  },

  // Dokumente
  {
    route: '/documents',
    file: 'documents-overview.png',
    dir: 'documents',
    label: 'Dokumentenverwaltung',
    waitFor: 'main',
  },

  // Fragengenerierung — 4-Schritt-Wizard (alle Shots in einer Session)
  {
    route: '/questions/generate',
    file: 'questions-step1-document-selection.png',
    dir: 'questions',
    label: 'Fragengenerierung Wizard (4 Schritte)',
    waitFor: 'main',
    skipAutoShot: true,
    subFiles: ['questions-generate.png', 'questions-step2-parameters.png', 'questions-step3-context-preview.png', 'questions-step4-generated.png'],
    action: async (page, dataStatus) => {
      const wizardDir = path.join(DOCS_SCREENSHOTS, 'questions');
      ensureDir(wizardDir);

      // Warten bis Seite und erste Dokument-Karte geladen
      await page.waitForSelector('main', { timeout: SELECTOR_TIMEOUT_MS });
      await page.waitForSelector('.MuiStepContent-root .MuiCard-root', { timeout: SELECTOR_TIMEOUT_MS }).catch(() => null);
      await page.waitForTimeout(ANIMATION_PAUSE_MS);

      // Shot 0: Übersicht (vor Selektion, volle Seite)
      if (shouldCapture('questions-generate.png')) {
        await page.screenshot({
          path: path.join(wizardDir, 'questions-generate.png'),
          fullPage: true,
        });
        console.log('  ✓ questions-generate.png');
      }

      // Schritte 2–4 benötigen Dokumente
      if (!dataStatus?.hasDocuments) {
        // Auch Step 1 nehmen wir auf (leere Ansicht ist ok)
        if (shouldCapture('questions-step1-document-selection.png')) {
          await page.screenshot({
            path: path.join(wizardDir, 'questions-step1-document-selection.png'),
            fullPage: true,
          });
          console.log('  ✓ questions-step1-document-selection.png');
        }
        console.warn('  ⚠ SKIP questions-step2/3/4 — keine Testdaten: Dokumente fehlen');
        return;
      }

      // Erstes Dokument-Card auswählen (blaue Umrandung erscheint)
      const firstDocCard = page.locator('.MuiStepContent-root .MuiCard-root').first();
      if (await firstDocCard.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
        await firstDocCard.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
      } else {
        console.warn('  ⚠ SKIP questions-step1/2/3/4 — keine Dokument-Karte klickbar');
        return;
      }

      // Shot 1: nach Doc-Click → Dokument ist selektiert (blaue Umrandung)
      if (shouldCapture('questions-step1-document-selection.png')) {
        await page.screenshot({
          path: path.join(wizardDir, 'questions-step1-document-selection.png'),
          fullPage: true,
        });
        console.log('  ✓ questions-step1-document-selection.png');
      }

      // "Weiter" klicken → Schritt 2 (Config)
      const weiterBtn = page.locator('button:has-text("Weiter")').first();
      if (await weiterBtn.isVisible().catch(() => false) && await weiterBtn.isEnabled().catch(() => false)) {
        await weiterBtn.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
      } else {
        console.warn('  ⚠ SKIP questions-step2/3/4 — "Weiter" Button nicht aktiviert');
        return;
      }

      // Schritt 2: Thema + Anzahl Fragen (=1) eintragen, dann Screenshot
      const topicInput = page.locator('.MuiStepContent-root .MuiTextField-root input').first();
      if (await topicInput.isVisible().catch(() => false)) {
        await topicInput.fill('Algorithmen und Datenstrukturen');
        await page.waitForTimeout(ACTION_PAUSE_MS);
      }
      // Anzahl Fragen auf 1 setzen (weniger generierte Fragen → Review Queue übersichtlich)
      const countInput = page.locator('.MuiStepContent-root input[type="number"]').first();
      if (await countInput.isVisible().catch(() => false)) {
        await countInput.fill('1');
        await page.waitForTimeout(ACTION_PAUSE_MS);
      }

      if (shouldCapture('questions-step2-parameters.png')) {
        await page.screenshot({
          path: path.join(wizardDir, 'questions-step2-parameters.png'),
          fullPage: true,
        });
        console.log('  ✓ questions-step2-parameters.png');
      }

      // Schritt 2 → 3: "Weiter" klicken
      const weiterStep2 = page.locator('button:has-text("Weiter")').first();
      if (await weiterStep2.isVisible().catch(() => false) && await weiterStep2.isEnabled().catch(() => false)) {
        await weiterStep2.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
      } else {
        console.warn('  ⚠ SKIP questions-step3/4 — "Weiter" Button in Schritt 2 nicht aktiviert');
        return;
      }

      // Schritt 3: "Kontext-Vorschau laden" klicken + warten
      const previewBtn = page.locator('button:has-text("Kontext-Vorschau")').first();
      if (await previewBtn.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
        await previewBtn.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(WIZARD_CONTEXT_WAIT_MS);
      } else {
        console.warn('  ⚠ SKIP questions-step3 — "Kontext-Vorschau" Button nicht sichtbar');
        return;
      }
      if (shouldCapture('questions-step3-context-preview.png')) {
        await page.screenshot({
          path: path.join(wizardDir, 'questions-step3-context-preview.png'),
          fullPage: true,
        });
        console.log('  ✓ questions-step3-context-preview.png');
      }

      // Schritt 4: "Prüfung generieren" → Hintergrundtask → TaskBar-Click → Schritt 4
      const generateBtn = page.locator('button:has-text("Generieren")').first();
      if (await generateBtn.isVisible().catch(() => false) && await generateBtn.isEnabled().catch(() => false)) {
        await generateBtn.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
        const successTask = page.locator('[data-testid="generation-task-success"]').first();
        const found = await successTask.waitFor({ state: 'visible', timeout: WIZARD_GENERATE_TIMEOUT_MS }).catch(() => false);
        if (found !== false) {
          await successTask.click();
          await page.waitForSelector('text=Prüfung erfolgreich generiert', { timeout: SELECTOR_TIMEOUT_MS }).catch(() => null);
          await page.waitForTimeout(ACTION_PAUSE_MS);
        } else {
          console.warn('  ⚠ SKIP questions-step4 — Task nicht innerhalb 60s abgeschlossen');
          return;
        }
      } else {
        console.warn('  ⚠ SKIP questions-step4 — "Generieren" Button nicht sichtbar/aktiviert');
        return;
      }
      if (shouldCapture('questions-step4-generated.png')) {
        await page.screenshot({
          path: path.join(wizardDir, 'questions-step4-generated.png'),
          fullPage: true,
        });
        console.log('  ✓ questions-step4-generated.png');
      }
    },
  },

  // Review Queue
  {
    route: '/questions/review',
    file: 'review-queue-overview.png',
    dir: 'review-queue',
    label: 'Review Queue Übersicht',
    waitFor: 'main',
    action: async (page) => {
      await page.waitForLoadState('networkidle');
      await page.waitForFunction(
        () => !document.querySelector('.animate-spin'),
        { timeout: 8000 }
      ).catch(() => null);
      await page.waitForTimeout(ACTION_PAUSE_MS);
    },
  },

  // Exam Composer — alle Sub-Ansichten in einer Session
  {
    route: '/exams/compose',
    file: 'exam-composer-overview.png',
    dir: 'exam-composer',
    label: 'Exam Composer (alle Sub-Ansichten)',
    waitFor: 'main',
    requiresFreshLogin: true,
    skipAutoShot: true,
    subFiles: ['exam-composer-new.png', 'exam-composer-builder.png', 'exam-composer-reorder.png', 'exam-composer-question-selection.png', 'exam-composer-export.png'],
    action: async (page, dataStatus) => {
      const composerDir = path.join(DOCS_SCREENSHOTS, 'exam-composer');
      ensureDir(composerDir);

      // Warten bis Liste geladen
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(ACTION_PAUSE_MS);

      // Shot 1: Übersicht (Liste der Prüfungen)
      if (shouldCapture('exam-composer-overview.png')) {
        await page.screenshot({
          path: path.join(composerDir, 'exam-composer-overview.png'),
          fullPage: true,
        });
        console.log('  ✓ exam-composer-overview.png');
      }

      // Shot 2: Dialog "Neue Prüfung" mit Test-Daten
      if (shouldCapture('exam-composer-new.png')) {
        const newBtn = page
          .locator('button:has-text("+ Neue Prüfung"), button:has-text("Neue Prüfung"), [data-testid="new-exam-btn"]')
          .first();
        if (await newBtn.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
          await newBtn.click();
          await page.waitForSelector('[role="dialog"], .MuiDialog-root', { timeout: SELECTOR_TIMEOUT_MS }).catch(() => null);
          await page.waitForTimeout(ACTION_PAUSE_MS);

          // Test-Daten in Felder eintragen
          const titleInput = page.locator('[role="dialog"] input').nth(0);
          if (await titleInput.isVisible().catch(() => false)) {
            await titleInput.fill('Midterm Informatik FS25');
          }
          const courseInput = page.locator('[role="dialog"] input').nth(1);
          if (await courseInput.isVisible().catch(() => false)) {
            await courseInput.fill('Informatik Grundlagen');
          }
          const dateInput = page.locator('[role="dialog"] input[type="date"]').first();
          if (await dateInput.isVisible().catch(() => false)) {
            await dateInput.fill('2025-06-15');
          }
          const timeInput = page.locator('[role="dialog"] input[type="number"]').first();
          if (await timeInput.isVisible().catch(() => false)) {
            await timeInput.fill('90');
          }
          await page.waitForTimeout(ACTION_PAUSE_MS);

          await page.screenshot({
            path: path.join(composerDir, 'exam-composer-new.png'),
            fullPage: true,
          });
          console.log('  ✓ exam-composer-new.png');

          // Dialog schliessen
          const cancelBtn = page
            .locator('button:has-text("Abbrechen"), button:has-text("Cancel"), [aria-label="close"]')
            .first();
          if (await cancelBtn.isVisible().catch(() => false)) {
            await cancelBtn.click();
          } else {
            await page.keyboard.press('Escape');
          }
          await page.waitForTimeout(ACTION_PAUSE_MS);
        } else {
          console.warn('  ⚠ SKIP exam-composer-new — "+ Neue Prüfung" Button nicht sichtbar');
        }
      }

      // Shots 3–5 brauchen ein bestehendes Exam
      const needsBuilder =
        shouldCapture('exam-composer-builder.png') ||
        shouldCapture('exam-composer-reorder.png') ||
        shouldCapture('exam-composer-question-selection.png') ||
        shouldCapture('exam-composer-export.png');
      if (!needsBuilder) return;

      if (!dataStatus?.hasExams) {
        console.warn('  ⚠ SKIP exam-composer-builder/question-selection — keine Exams vorhanden');
        return;
      }

      // Auf erstes Exam klicken → Builder-Ansicht
      const firstExamCard = page
        .locator('.card.cursor-pointer, [data-testid="exam-card"]')
        .first();
      if (!await firstExamCard.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
        console.warn('  ⚠ SKIP exam-composer-builder — keine Exams in der Liste');
        return;
      }
      await firstExamCard.click();
      // Warten bis ExamBuilderView gerendert ist (React-State-Wechsel, kein URL-Wechsel)
      await page.waitForSelector('[data-testid="exam-builder"]', { timeout: SELECTOR_TIMEOUT_MS }).catch(() => null);
      await page.waitForTimeout(ACTION_PAUSE_MS);
      // Sicherheitsprüfung: nicht auf Login gelandet?
      if (new URL(page.url()).pathname.startsWith('/login')) {
        console.warn('  ⚠ SKIP exam-composer-builder — Login-Redirect nach Karten-Klick');
        return;
      }

      // Shot 3: Builder-Ansicht (sofort nach Render)
      if (shouldCapture('exam-composer-builder.png')) {
        await page.screenshot({
          path: path.join(composerDir, 'exam-composer-builder.png'),
          fullPage: true,
        });
        console.log('  ✓ exam-composer-builder.png');
      }

      // Shot 3b: Reihenfolge-Ansicht (gleiche Ansicht wie Builder — eigener Screenshot für Doku-Schritt 4)
      if (shouldCapture('exam-composer-reorder.png')) {
        await page.screenshot({
          path: path.join(composerDir, 'exam-composer-reorder.png'),
          fullPage: true,
        });
        console.log('  ✓ exam-composer-reorder.png');
      }

      // Shot 4: Question-Selection — warten bis Pool geladen (+ Hinzufügen sichtbar)
      if (shouldCapture('exam-composer-question-selection.png')) {
        const addBtn = page.locator('button:has-text("Hinzufügen")').first();
        if (await addBtn.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
          await page.screenshot({
            path: path.join(composerDir, 'exam-composer-question-selection.png'),
            fullPage: true,
          });
          console.log('  ✓ exam-composer-question-selection.png');
        } else {
          console.warn('  ⚠ SKIP exam-composer-question-selection — kein "+ Hinzufügen" Button sichtbar');
        }
      }

      // Shot 5: Export-Dialog
      if (shouldCapture('exam-composer-export.png')) {
        const exportBtn = page.locator('button:has-text("Exportieren")').first();
        if (await exportBtn.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
          await exportBtn.click();
          await page.waitForSelector('[role="dialog"]', { timeout: SELECTOR_TIMEOUT_MS }).catch(() => null);
          await page.waitForTimeout(ACTION_PAUSE_MS);
          await page.screenshot({
            path: path.join(composerDir, 'exam-composer-export.png'),
            fullPage: true,
          });
          console.log('  ✓ exam-composer-export.png');
          // Dialog schliessen
          const cancelBtn = page.locator('[role="dialog"] button:has-text("Abbrechen")').first();
          if (await cancelBtn.isVisible().catch(() => false)) {
            await cancelBtn.click();
          } else {
            await page.keyboard.press('Escape');
          }
          await page.waitForTimeout(ACTION_PAUSE_MS);
        } else {
          console.warn('  ⚠ SKIP exam-composer-export — "Exportieren" Button nicht sichtbar');
        }
      }
    },
  },

  // Prompt Library
  {
    route: '/prompts',
    file: 'prompt-library-overview.png',
    dir: 'prompt-library',
    label: 'Prompt Library Übersicht',
    waitFor: 'main',
  },
  {
    route: '/prompts',
    file: 'prompt-library-editor.png',
    dir: 'prompt-library',
    label: 'Prompt Library Editor',
    waitFor: 'main',
    action: async (page) => {
      const editBtn = page
        .locator('button:has-text("Bearbeiten"), button:has-text("Edit"), [data-testid="edit-prompt-btn"]')
        .first();
      const newBtn = page
        .locator('button:has-text("Neuer Prompt"), button:has-text("New Prompt"), [data-testid="new-prompt-btn"]')
        .first();
      if (await editBtn.isVisible()) {
        await editBtn.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
      } else if (await newBtn.isVisible()) {
        await newBtn.click();
        await page.waitForTimeout(ACTION_PAUSE_MS);
      }
    },
  },

  // Profile
  {
    route: '/profile',
    file: 'profile-page.png',
    dir: 'profile',
    label: 'Profilseite',
    waitFor: 'main',
  },

  // Subscription
  {
    route: '/subscription',
    file: 'subscription-page.png',
    dir: 'subscription',
    label: 'Abonnement-Seite',
    waitFor: 'main',
    action: async (page) => {
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(ACTION_PAUSE_MS);
    },
  },
  {
    route: '/billing',
    file: 'billing-page.png',
    dir: 'subscription',
    label: 'Rechnungsseite',
    waitFor: 'main',
  },

  // Admin — alle 5 Tabs in einer Session (verhindert Session-Verlust durch wiederholte Navigationen)
  {
    route: '/admin',
    file: 'admin-user-mgmt.png',
    dir: 'admin',
    label: 'Admin (alle 5 Tabs)',
    waitFor: 'main',
    requiresFreshLogin: true,
    skipAutoShot: true,
    action: async (page) => {
      const adminDir = path.join(DOCS_SCREENSHOTS, 'admin');
      ensureDir(adminDir);

      // Tab 1: Benutzerverwaltung — warten bis Daten geladen oder Fehler sichtbar
      // Bei Fehler: einmal reload, dann weitermachen (transiente Netzwerkfehler abfangen)
      for (let attempt = 1; attempt <= 2; attempt++) {
        await page.waitForLoadState('networkidle');
        await page.waitForFunction(
          () => !document.querySelector('.animate-spin'),
          { timeout: 8000 }
        ).catch(() => null);
        await page.waitForTimeout(ACTION_PAUSE_MS);
        const hasErr = await page.locator('text="Failed to fetch"').isVisible().catch(() => false);
        if (!hasErr) break; // Daten geladen
        if (attempt < 2) {
          console.warn(`  ↺ admin-user-mgmt: Fehler sichtbar — Seite neu laden (Versuch ${attempt})…`);
          await page.reload({ waitUntil: 'load' });
          await page.waitForFunction(
            () => !document.querySelector('.animate-spin'),
            { timeout: 8000 }
          ).catch(() => null);
        } else {
          console.warn('  ⚠ admin-user-mgmt: API-Fehler nach Reload — Backend erreichbar?');
        }
      }
      await page.screenshot({
        path: path.join(adminDir, 'admin-user-mgmt.png'),
        fullPage: true,
      });
      console.log('  ✓ admin-user-mgmt.png');

      // Tab 2: Institutionen
      await clickAdminTab(page, 'Institutionen').catch(() =>
        console.warn('  ⚠ admin-institutions: Tab nicht gefunden')
      );
      await page.screenshot({
        path: path.join(adminDir, 'admin-institutions.png'),
        fullPage: true,
      });
      console.log('  ✓ admin-institutions.png');

      // Tab 3: Rollen & Berechtigungen
      await clickAdminTab(page, 'Rollen & Berechtigungen').catch(() =>
        console.warn('  ⚠ admin-roles: Tab nicht gefunden')
      );
      await page.screenshot({
        path: path.join(adminDir, 'admin-roles.png'),
        fullPage: true,
      });
      console.log('  ✓ admin-roles.png');

      // Tab 4: Audit Logs
      await clickAdminTab(page, 'Audit Logs').catch(() =>
        console.warn('  ⚠ admin-audit: Tab nicht gefunden')
      );
      await page.screenshot({
        path: path.join(adminDir, 'admin-audit.png'),
        fullPage: true,
      });
      console.log('  ✓ admin-audit.png');

      // Tab 5: Abonnement
      await clickAdminTab(page, 'Abonnement').catch(() =>
        console.warn('  ⚠ admin-subscription: Tab nicht gefunden')
      );
      await page.screenshot({
        path: path.join(adminDir, 'admin-subscription.png'),
        fullPage: true,
      });
      console.log('  ✓ admin-subscription.png');
    },
  },

  // Chatbot — beide Screenshots in einer Session (verhindert Session-Verlust)
  {
    route: '/chat',
    file: 'chatbot-interface.png',
    dir: 'chatbot',
    label: 'Chatbot (beide Ansichten)',
    waitFor: 'main',
    requiresFreshLogin: true,
    skipAutoShot: true,
    action: async (page, dataStatus) => {
      const chatDir = path.join(DOCS_SCREENSHOTS, 'chatbot');
      ensureDir(chatDir);

      // Prüfen ob /chat erreichbar ist (Professional-Plan + document_chatbot Permission nötig)
      const currentPath = new URL(page.url()).pathname;
      if (currentPath.startsWith('/unauthorized')) {
        console.warn('  ⚠ SKIP chatbot — Professional-Plan oder document_chatbot-Permission fehlt');
        return;
      }
      if (currentPath.startsWith('/login')) {
        console.warn('  ⚠ SKIP chatbot — nicht authentifiziert nach Navigation zu /chat');
        return;
      }

      // Shot 1: Chatbot Interface (Übersicht)
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(ACTION_PAUSE_MS);
      await page.screenshot({
        path: path.join(chatDir, 'chatbot-interface.png'),
        fullPage: true,
      });
      console.log('  ✓ chatbot-interface.png');

      // Shot 2: Bestehende Session öffnen
      if (!dataStatus?.hasChatSessions) {
        console.warn('  ⚠ SKIP chatbot-example-conversation — keine Chat-Sessions vorhanden');
        return;
      }
      const firstSession = page.locator('[data-testid="chat-session-item"]').first();
      if (await firstSession.isVisible({ timeout: SELECTOR_TIMEOUT_MS }).catch(() => false)) {
        await firstSession.click();
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(ACTION_PAUSE_MS);
      } else {
        console.warn('  ⚠ chatbot-example-conversation: Session-Karte nicht gefunden');
      }
      await page.screenshot({
        path: path.join(chatDir, 'chatbot-example-conversation.png'),
        fullPage: true,
      });
      console.log('  ✓ chatbot-example-conversation.png');
    },
  },
];

// --- Login ---

// Verhindert, dass React Auth-Token aus localStorage löscht (CORS-Fehler dürfen Session nicht invalidieren)
async function protectLocalStorageTokens(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const _removeItem = localStorage.removeItem.bind(localStorage);
    const PROTECTED = ['examcraft_access_token', 'examcraft_refresh_token', 'examcraft_user'];
    (localStorage as any).removeItem = (key: string) => {
      if (PROTECTED.includes(key)) return; // Session-Schutz
      _removeItem(key);
    };
  });
}

async function login(page: Page): Promise<void> {
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'load' });
  await page.waitForTimeout(ANIMATION_PAUSE_MS);

  // Warten bis Auth-Spinner verschwindet (AuthContext verifiziert Token async)
  await page.waitForFunction(
    () => !document.querySelector('.animate-spin'),
    { timeout: 8000 }
  ).catch(() => null);
  await page.waitForTimeout(ANIMATION_PAUSE_MS);

  // Wenn React bereits zur Dashboard-Seite umgeleitet hat → bereits eingeloggt
  if (!new URL(page.url()).pathname.startsWith('/login')) {
    console.log(`✓ Bereits eingeloggt (${new URL(page.url()).pathname})`);
    return;
  }

  // Formular ausfüllen und absenden
  // locator().fill() triggert React onChange zuverlässiger als page.fill() mit kommaseparierten Selektoren
  await page.waitForSelector('form', { timeout: PAGE_TIMEOUT_MS });
  const emailInput = page.locator('#email').first();
  await emailInput.waitFor({ state: 'visible', timeout: SELECTOR_TIMEOUT_MS });
  await emailInput.click();
  await emailInput.fill(EMAIL!);
  const passwordInput = page.locator('#password').first();
  await passwordInput.click();
  await passwordInput.fill(PASSWORD!);
  await page.waitForTimeout(ACTION_PAUSE_MS);
  await page.click('button[type="submit"]');
  // Warten bis die URL nicht mehr /login ist (React Router, kein full-page reload)
  await page.waitForFunction(
    () => !window.location.pathname.startsWith('/login'),
    null,
    { timeout: PAGE_TIMEOUT_MS }
  );
  await page.waitForTimeout(ACTION_PAUSE_MS);
  console.log(`✓ Login erfolgreich (${new URL(page.url()).pathname})`);
}

// --- Verzeichnis sicherstellen ---

function ensureDir(dir: string): void {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

// --- Check-Modus ---

async function runCheck(): Promise<void> {
  console.log('\nExamCraft AI — Seiten-Check (--check)');
  console.log('======================================');

  const browser = await chromium.launch({ headless: false, slowMo: CHECK_SLOW_MO });
  const results: CheckResult[] = [];

  try {
    // Auth-Seiten (kein Login nötig)
    const authCtx = await browser.newContext({ viewport: VIEWPORT });
    const authPage = await authCtx.newPage();
    for (const def of SCREENSHOTS.filter((s) => s.requiresAuth === false)) {
      results.push(await checkPage(authPage, def.route, def.label));
    }
    await authCtx.close();

    // Alle anderen Seiten (eingeloggt, /chat kommt zuletzt)
    const appCtx = await browser.newContext({ viewport: VIEWPORT });
    const page = await appCtx.newPage();
    await protectLocalStorageTokens(page);
    await login(page);
    for (const def of SCREENSHOTS.filter((s) => s.requiresAuth !== false)) {
      results.push(await checkPage(page, def.route, def.label));
    }
    await appCtx.close();
  } finally {
    await browser.close();
  }

  console.log('\nResultat:');
  let hasErrors = false;
  for (const r of results) {
    if (r.ok) {
      console.log(`  ✅ ${r.route}  — ${r.label}`);
    } else {
      console.log(`  ❌ ${r.route}  — ${r.label}`);
      for (const issue of r.issues) {
        console.log(`       ⚠ ${issue}`);
      }
      hasErrors = true;
    }
  }

  if (hasErrors) {
    console.log('\n❌ Probleme gefunden — bitte beheben, dann erneut prüfen.');
    process.exit(1);
  } else {
    console.log('\n✅ Alle Seiten OK — Screenshots können aufgenommen werden.');
  }
}

async function checkPage(page: Page, route: string, label: string): Promise<CheckResult> {
  const issues: string[] = [];
  const consoleErrors: string[] = [];

  const handler = (msg: ConsoleMessage) => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text().slice(0, MAX_ERROR_LENGTH));
    }
  };
  page.on('console', handler);

  try {
    // 'load' statt 'networkidle': Hintergrund-API-Calls lösen keinen Logout aus
    await page.goto(`${BASE_URL}${route}`, { waitUntil: 'load', timeout: PAGE_TIMEOUT_MS });
    await page.waitForTimeout(ANIMATION_PAUSE_MS);
  } catch {
    issues.push('Seite nicht erreichbar oder Timeout');
    page.off('console', handler);
    return { route, label, ok: false, issues };
  }

  let currentPath = new URL(page.url()).pathname;
  // Session verloren → einmalig re-login und nochmals navigieren
  if (currentPath.startsWith('/login') && !route.startsWith('/login') && !route.startsWith('/register')) {
    console.warn(`  ↺ Session abgelaufen bei ${route} — re-login…`);
    await login(page).catch(() => null);
    try {
      await page.goto(`${BASE_URL}${route}`, { waitUntil: 'load', timeout: PAGE_TIMEOUT_MS });
      await page.waitForTimeout(ANIMATION_PAUSE_MS);
    } catch {
      issues.push('Seite nach Re-Login nicht erreichbar');
      page.off('console', handler);
      return { route, label, ok: false, issues };
    }
    currentPath = new URL(page.url()).pathname;
  }
  const expectedBase = route.replace(/:[^/]+.*$/, '');
  if (!currentPath.startsWith(expectedBase) && expectedBase !== '/') {
    issues.push(`Redirect zu ${currentPath}`);
  }

  const errorVisible = await page
    .locator('[role="alert"]:visible')
    .first()
    .isVisible()
    .catch(() => false);
  if (errorVisible) {
    const text = await page
      .locator('[role="alert"]:visible')
      .first()
      .textContent()
      .catch(() => '');
    // Informationsmeldungen (leer, kein Inhalt) sind keine Fehler
    const isRealError = text &&
      (text.includes('Error') || text.includes('Fehler') || text.includes('failed') || text.includes('fehlgeschlagen'));
    if (isRealError) {
      issues.push(`Alert sichtbar: "${text.trim().slice(0, MAX_ALERT_LENGTH)}"`);
    }
  }

  const relevantErrors = consoleErrors.filter(
    (e) =>
      !e.includes('favicon') &&
      !e.includes('ResizeObserver') &&
      !e.includes('Non-Error') &&
      // Hintergrund-API-Calls: Resource-Loading-Fehler ignorieren
      !e.includes('Failed to load resource') &&
      !e.includes('ERR_FAILED') &&
      !e.includes('net::ERR') &&
      // CORS-Fehler bei Hintergrund-API-Calls ignorieren (Backend-Sache, nicht Seite)
      !e.includes('Access-Control-Allow') &&
      !e.includes('CORS policy') &&
      !e.includes('blocked by CORS') &&
      // Proxy-Fehler von CRA Dev-Proxy ignorieren
      !e.includes('Proxy erro') &&
      !e.includes('is not valid JSON') &&
      // Bekannte Folge-Fehler von Session-Verlust oder Hintergrund-Diensten
      !e.includes('Token verification failed') &&
      !e.includes('Token refresh failed') &&
      !e.includes('Failed to recover active tasks') &&
      !e.includes('Failed to load documents') &&
      !e.includes('Failed to detect package tier') &&
      !e.includes('Error loading payment methods') &&
      !e.includes('Login error') &&
      !e.includes('Login failed')
  );
  if (relevantErrors.length > 0) {
    issues.push(`JS-Fehler: ${relevantErrors.slice(0, 2).join(' | ')}`);
  }

  page.off('console', handler);
  return { route, label, ok: issues.length === 0, issues };
}

// --- Screenshot-Modus ---

async function runScreenshots(): Promise<void> {
  console.log('\nExamCraft AI — Dokumentations-Screenshots');
  console.log('==========================================');
  console.log(`App:  ${BASE_URL}`);
  console.log(`Ziel: ${DOCS_SCREENSHOTS}\n`);

  const browser = await chromium.launch({ headless: false, slowMo: SCREENSHOT_SLOW_MO });

  try {
    let done = 0;
    let failed = 0;

    // Auth-Seiten (kein Login nötig)
    const authCtx = await browser.newContext({ viewport: VIEWPORT });
    const authPage = await authCtx.newPage();
    for (const def of SCREENSHOTS.filter((s) => s.requiresAuth === false && isInScope(s))) {
      (await takeScreenshot(authPage, def)) ? done++ : failed++;
    }
    await authCtx.close();

    // Alle anderen Seiten (eingeloggt, /chat kommt zuletzt)
    const appCtx = await browser.newContext({ viewport: VIEWPORT });
    const page = await appCtx.newPage();
    // Netzwerk-Fehler-Listener: zeigt exakt welche Requests scheitern und warum
    page.on('requestfailed', (request) => {
      const url = request.url();
      if (url.includes('localhost:8000') || url.includes('/api/')) {
        console.warn(`  ✗ Netzwerkfehler: ${request.method()} ${url} — ${request.failure()?.errorText ?? 'unbekannt'}`);
      }
    });
    await protectLocalStorageTokens(page);
    await login(page);
    const dataStatus = await runDataPreflight(page);
    const authenticatedDefs = SCREENSHOTS.filter((s) => s.requiresAuth !== false && isInScope(s));
    for (let i = 0; i < authenticatedDefs.length; i++) {
      if (i > 0) await page.waitForTimeout(INTER_SCREENSHOT_PAUSE_MS);
      (await takeScreenshot(page, authenticatedDefs[i], dataStatus)) ? done++ : failed++;
    }
    await appCtx.close();

    const totalInScope = SCREENSHOTS.filter(isInScope).length;
    console.log(`\n${done}/${totalInScope} Screenshots erstellt${ONLY_FILES.size > 0 ? ` (--only: ${[...ONLY_FILES].join(', ')})` : ''}`);
    if (failed > 0) {
      console.log(`${failed} fehlgeschlagen — manuell nacharbeiten`);
    }
  } finally {
    await browser.close();
  }
}

async function takeScreenshot(page: Page, def: ScreenshotDef, dataStatus?: DataStatus): Promise<boolean> {
  const outDir = path.join(DOCS_SCREENSHOTS, def.dir);
  ensureDir(outDir);
  const outFile = path.join(outDir, def.file);

  try {
    // Optionaler Re-Login vor der Navigation (für Routen mit Permission-Guards)
    if (def.requiresFreshLogin) {
      await login(page).catch((err) => {
        console.warn(`  ⚠ requiresFreshLogin: Re-Login fehlgeschlagen — ${(err as Error).message}`);
      });
    }

    // Bis zu 3 Navigations-Versuche mit Backoff
    let navOk = false;
    for (let attempt = 1; attempt <= 3 && !navOk; attempt++) {
      if (attempt > 1) {
        console.warn(`  ↺ Session abgelaufen bei ${def.route} — Versuch ${attempt}…`);
        await page.waitForTimeout(attempt * 1500); // Backoff: 1.5s, 3s
      }
      await page.goto(`${BASE_URL}${def.route}`, { waitUntil: 'load' });
      // Auth-Spinner abwarten: AuthContext verifiziert Token async, Spinner zeigt isLoading: true
      await page.waitForFunction(
        () => !document.querySelector('.animate-spin'),
        { timeout: 5000 }
      ).catch(() => null);
      await page.waitForTimeout(ANIMATION_PAUSE_MS);
      const pathname = new URL(page.url()).pathname;
      if (!pathname.startsWith('/login') || def.requiresAuth === false) {
        navOk = true;
      }
    }
    // Letzter Ausweg: Re-Login
    if (!navOk && def.requiresAuth !== false) {
      console.warn(`  ↺ Versuche Re-Login für ${def.route}…`);
      try {
        await login(page);
        await page.goto(`${BASE_URL}${def.route}`, { waitUntil: 'load' });
        await page.waitForTimeout(ANIMATION_PAUSE_MS);
      } catch {
        // Login fehlgeschlagen — unten wird geprüft
      }
      const postLoginPath = new URL(page.url()).pathname;
      if (postLoginPath.startsWith('/login')) {
        console.warn(`  ⚠ SKIP ${def.file} — Session konnte nicht wiederhergestellt werden`);
        return false;
      }
    }

    if (def.waitFor) {
      await page.waitForSelector(def.waitFor, { timeout: SELECTOR_TIMEOUT_MS }).catch(() => {
        console.warn(`  ⚠ Selektor nicht gefunden: ${def.waitFor} — fahre fort`);
      });
    }

    if (def.action) {
      await def.action(page, dataStatus);
    }

    await page.waitForTimeout(ANIMATION_PAUSE_MS);

    if (def.skipAutoShot) {
      // action hat bereits alle Screenshots gespeichert
    } else {
      let effectiveClip = def.clip ?? null;
      if (def.clipFn) {
        effectiveClip = (await def.clipFn(page)) ?? effectiveClip;
      }
      if (effectiveClip) {
        await page.screenshot({ path: outFile, clip: effectiveClip });
      } else {
        await page.screenshot({ path: outFile, fullPage: true });
      }
    }

    console.log(`✓ ${def.file}  (${def.label})`);
    return true;
  } catch (err) {
    console.error(`✗ ${def.file}  — ${(err as Error).message}`);
    return false;
  }
}

// --- Einstieg ---

if (CHECK_MODE) {
  runCheck().catch((err) => {
    console.error(err);
    process.exit(1);
  });
} else {
  runScreenshots().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}
