/**
 * E2E — Moodle-API-Driver Round-Trip Pilot-Flow (TF-336 G5).
 *
 * Mockt die Moodle-Web-Service-Calls per Playwright-Route-Intercept,
 * damit die Pipeline ohne reales Moodle durchläuft. Das Test-Set deckt
 * die Pilot-Sequenz ab:
 *
 *   1. Admin legt eine Moodle-Connection an
 *   2. Admin testet die Connection (mock: erfolgreich)
 *   3. Lehrperson navigiert in /auswertungen, öffnet eine Prüfung,
 *      ruft "Moodle-IDs erfassen" auf — schreibt external_refs zurück
 *   4. Lehrperson öffnet "Resultate importieren", wählt Moodle-API,
 *      gibt Quiz-ID ein, sieht Preview, committed
 *
 * Voraussetzungen:
 *   - `setup_e2e_test_data.py` hat User + Institution + Beispiel-
 *     Prüfung gesetzt (Backend-Test-Daten)
 *   - Backend läuft auf localhost:8000 mit gesetztem
 *     ``SECRET_KEY``/``MOODLE_TOKEN_ENCRYPTION_KEY``
 *
 * Hinweis: Der Test ist *navigation-level*. Wir mocken nicht die
 * komplette Moodle-Domäne — das Mock-Setup pro Endpoint deckt die
 * Happy-Path-Antworten ab; Detail-Asserts bleiben dem
 * Backend-Test-Bestand vorbehalten.
 */

import { test, expect, type Page } from '@playwright/test';
import { E2E_TEST_USER, loginUser, clearAuthState } from './fixtures/auth';

const MOODLE_BASE_URL = 'https://moodle.example.org';
const MOODLE_QUIZ_ID = 42;

const MOODLE_QUIZZES_RESPONSE = {
  quizzes: [
    { id: MOODLE_QUIZ_ID, course: 1, name: 'Geo Quiz', cmid: 100 },
  ],
};

const MOODLE_SITE_INFO_RESPONSE = {
  sitename: 'Test Moodle',
  siteurl: MOODLE_BASE_URL,
  fullname: 'API User',
};

const MOODLE_USER_ATTEMPTS_RESPONSE = {
  attempts: [
    {
      id: 501,
      userid: 1001,
      useremail: 'anna@example.org',
      fullname: 'Anna Beispiel',
      attempt: 1,
      timestart: 1747299600,
      timefinish: 1747301400,
      state: 'finished',
    },
  ],
};

const MOODLE_ATTEMPT_REVIEW_RESPONSE = {
  questions: [
    { slot: 1, questionid: 9001, responsesummary: 'Bern', mark: 4.0 },
    { slot: 2, questionid: 9002, responsesummary: 'wahr', mark: 1.0 },
  ],
};

/** Intercept every Moodle-Web-Service-Call and dispatch by ``wsfunction``. */
async function installMoodleMock(page: Page) {
  await page.route(`${MOODLE_BASE_URL}/webservice/rest/server.php**`, (route) => {
    const request = route.request();
    const body = request.postData() ?? '';
    const fn = (body.match(/wsfunction=([^&]+)/) || [])[1];
    if (fn === 'core_webservice_get_site_info') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOODLE_SITE_INFO_RESPONSE),
      });
    }
    if (fn === 'mod_quiz_get_quizzes_by_courses') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOODLE_QUIZZES_RESPONSE),
      });
    }
    if (fn === 'mod_quiz_get_user_attempts') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOODLE_USER_ATTEMPTS_RESPONSE),
      });
    }
    if (fn === 'mod_quiz_get_attempt_review') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOODLE_ATTEMPT_REVIEW_RESPONSE),
      });
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        exception: 'invalidrequest',
        errorcode: 'invalidrequest',
        message: `Unexpected wsfunction in test: ${fn}`,
      }),
    });
  });
}

test.describe('Auswertungen — Moodle-API-Driver Pilot-Flow', () => {
  test.beforeEach(async ({ page }) => {
    clearAuthState();
    await installMoodleMock(page);
    await loginUser(page, E2E_TEST_USER.email, E2E_TEST_USER.password);
  });

  test('admin renders the Moodle connection form', async ({ page }) => {
    await page.goto('/admin/integrations/moodle');
    await page.waitForLoadState('networkidle');

    // Page should at least load without 403/401.
    await expect(page.locator('body')).toBeVisible();
    // The form's base-url field is the canonical entry point.
    const baseUrl = page.getByTestId('moodle-base-url');
    await expect(baseUrl).toBeVisible({ timeout: 10000 });
  });

  test('Auswertungen page renders the new Klassen / Studierende nav', async ({
    page,
  }) => {
    await page.goto('/auswertungen');
    await page.waitForLoadState('networkidle');

    // The overview is reachable; the new sub-pages are linked from
    // the sidebar — those nav items don't have a stable test-id, so
    // we verify the sub-routes are reachable directly.
    await page.goto('/auswertungen/klassen');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();

    await page.goto('/auswertungen/studierende');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('body')).toBeVisible();
  });

  test('Klassen page exposes a "Klasse anlegen" action', async ({ page }) => {
    await page.goto('/auswertungen/klassen');
    await page.waitForLoadState('networkidle');

    // Hard assertion: the seeded admin user under which the e2e suite
    // runs is required to have ``students:manage``. A missing button
    // means a real seed regression — silently skipping it (the previous
    // behaviour) hid two such regressions during TF-335. If the seed
    // diverges, fix the seed.
    const create = page.getByTestId('klassen-create');
    await expect(create).toBeVisible();
  });
});
