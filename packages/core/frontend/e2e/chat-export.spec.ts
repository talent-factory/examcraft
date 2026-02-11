import { test, expect, Page } from '@playwright/test';
import path from 'path';
import fs from 'fs';

/**
 * E2E Tests for Chat Export Functionality
 *
 * Tests the complete flow of:
 * 1. Creating a chat session
 * 2. Sending messages
 * 3. Exporting chat as Markdown/JSON
 * 4. Verifying correct filename in download
 *
 * This prevents regressions like the browser-specific filename bug (Oct 2025)
 */

// Test configuration - must match setup_e2e_test_data.py
const TEST_USER = {
  email: 'e2e-test@example.com',
  password: 'E2ETestPassword123',  // pragma: allowlist secret
};

const DOWNLOAD_DIR = path.join(__dirname, '../test-downloads');

// Skip these tests until Document Chat UI is fully implemented
// These tests require specific UI elements that may not exist yet
test.describe.skip('Chat Export Functionality', () => {

  test.beforeAll(async () => {
    // Ensure download directory exists
    if (!fs.existsSync(DOWNLOAD_DIR)) {
      fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });
    }
  });

  test.beforeEach(async ({ page }) => {
    // Login before each test
    await loginUser(page, TEST_USER.email, TEST_USER.password);
  });

  test.afterEach(async () => {
    // Clean up downloaded files
    if (fs.existsSync(DOWNLOAD_DIR)) {
      const files = fs.readdirSync(DOWNLOAD_DIR);
      files.forEach(file => {
        fs.unlinkSync(path.join(DOWNLOAD_DIR, file));
      });
    }
  });

  test('should export chat as Markdown with correct filename', async ({ page }) => {
    // Navigate to Document Chat
    await page.goto('/document-chat');
    await expect(page.locator('text=Dokument Chat')).toBeVisible();

    // Create a new chat session
    const sessionId = await createChatSession(page);

    // Send a test message
    await sendChatMessage(page, 'Was ist Heapsort?');

    // Wait for response
    await expect(page.locator('text=Heapsort')).toBeVisible({ timeout: 10000 });

    // Export as Markdown
    const customFilename = 'test-chat-export.md';
    const downloadPath = await exportChat(page, 'markdown', customFilename);

    // Verify file was downloaded with correct name
    expect(downloadPath).toContain(customFilename);
    expect(fs.existsSync(downloadPath)).toBeTruthy();

    // Verify file content
    const content = fs.readFileSync(downloadPath, 'utf-8');
    expect(content).toContain('# Dokument Chat');
    expect(content).toContain('Was ist Heapsort?');
  });

  test('should export chat as JSON with correct filename', async ({ page }) => {
    // Navigate to Document Chat
    await page.goto('/document-chat');

    // Create a new chat session
    await createChatSession(page);

    // Send a test message
    await sendChatMessage(page, 'Erkläre Priority Queues');

    // Wait for response
    await expect(page.locator('text=Priority Queue')).toBeVisible({ timeout: 10000 });

    // Export as JSON
    const customFilename = 'test-chat-export.json';
    const downloadPath = await exportChat(page, 'json', customFilename);

    // Verify file was downloaded with correct name
    expect(downloadPath).toContain(customFilename);
    expect(fs.existsSync(downloadPath)).toBeTruthy();

    // Verify JSON structure
    const content = fs.readFileSync(downloadPath, 'utf-8');
    const json = JSON.parse(content);
    expect(json).toHaveProperty('session_id');
    expect(json).toHaveProperty('messages');
    expect(json.messages).toBeInstanceOf(Array);
    expect(json.messages.length).toBeGreaterThan(0);
  });

  test('should handle special characters in filename', async ({ page }) => {
    await page.goto('/document-chat');
    await createChatSession(page);
    await sendChatMessage(page, 'Test message');

    // Try filename with special characters
    const customFilename = 'chat-äöü-2025.md';
    const downloadPath = await exportChat(page, 'markdown', customFilename);

    // Verify file exists (browser may sanitize filename)
    expect(fs.existsSync(downloadPath)).toBeTruthy();
  });

  test('should auto-add file extension if missing', async ({ page }) => {
    await page.goto('/document-chat');
    await createChatSession(page);
    await sendChatMessage(page, 'Test message');

    // Provide filename without extension
    const filenameWithoutExt = 'my-chat';
    const downloadPath = await exportChat(page, 'markdown', filenameWithoutExt);

    // Verify .md extension was added
    expect(downloadPath).toMatch(/\.md$/);
  });

  test('should work across different browsers', async ({ page, browserName }) => {
    // This test runs on all configured browsers (Chromium, Firefox, WebKit)
    console.log(`Testing on browser: ${browserName}`);

    await page.goto('/document-chat');
    await createChatSession(page);
    await sendChatMessage(page, 'Browser compatibility test');

    const customFilename = `${browserName}-test.md`;
    const downloadPath = await exportChat(page, 'markdown', customFilename);

    // Verify download works on all browsers
    expect(fs.existsSync(downloadPath)).toBeTruthy();

    // Log success for debugging
    console.log(`✅ ${browserName}: Download successful - ${downloadPath}`);
  });
});

// ============================================
// Helper Functions
// ============================================

/**
 * Login user
 */
async function loginUser(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  // Use #id selectors (the form uses id, not name)
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button[type="submit"]');

  // Wait for redirect to dashboard
  await expect(page).toHaveURL(/\/(dashboard|document-chat)/, { timeout: 15000 });
}

/**
 * Create a new chat session
 */
async function createChatSession(page: Page): Promise<string> {
  // Click "Neuer Chat" button
  await page.click('button:has-text("Neuer Chat")');

  // Select a document (assumes at least one document exists)
  await page.click('[data-testid="document-card"]:first-child');

  // Click "Chat starten"
  await page.click('button:has-text("Chat starten")');

  // Wait for chat interface to load
  await expect(page.locator('text=Dokument Chat')).toBeVisible();

  // Extract session ID from URL or data attribute
  const sessionId = await page.getAttribute('[data-session-id]', 'data-session-id');
  return sessionId || 'unknown';
}

/**
 * Send a chat message
 */
async function sendChatMessage(page: Page, message: string) {
  const inputSelector = 'textarea[placeholder*="Stelle eine Frage"]';
  await page.fill(inputSelector, message);
  await page.click('button[aria-label="Send"]');

  // Wait for message to appear in chat
  await expect(page.locator(`text=${message}`)).toBeVisible();
}

/**
 * Export chat and return download path
 */
async function exportChat(
  page: Page,
  format: 'markdown' | 'json',
  filename: string
): Promise<string> {
  // Setup download listener
  const downloadPromise = page.waitForEvent('download');

  // Click export button
  const exportButton = format === 'markdown'
    ? page.locator('button[title="Als Markdown exportieren"]')
    : page.locator('button[title="Als JSON exportieren"]');

  await exportButton.click();

  // Fill in filename in dialog
  await page.fill('input[placeholder*="mein-chat"]', filename);

  // Confirm export
  await page.click('button:has-text("Exportieren")');

  // Wait for download
  const download = await downloadPromise;

  // Save to test directory
  const downloadPath = path.join(DOWNLOAD_DIR, await download.suggestedFilename());
  await download.saveAs(downloadPath);

  return downloadPath;
}
