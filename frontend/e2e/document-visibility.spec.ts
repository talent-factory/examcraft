/**
 * E2E for the document visibility privacy fix (TF-354).
 *
 * API-driven (no fragile UI selectors): exercises the real backend + DB to
 * prove the privacy guarantee end-to-end:
 *
 *   1. User A uploads a PRIVATE document.
 *   2. User B (same institution) does NOT see it.
 *   3. User C (other institution) does NOT see it.
 *   4. User A switches it to INSTITUTION visibility.
 *   5. User B now sees it; User C still does not.
 *
 * Pre-requisites: dev stack running (`just dev-full`) and
 * `setup_e2e_test_data.py` has seeded the three users (A, B, C).
 *
 * To run: just e2e -- document-visibility.spec.ts
 */
import { test, expect, request as pwRequest, type APIRequestContext } from '@playwright/test';
import { E2E_TEST_USER, E2E_TEST_USER_B, E2E_TEST_USER_C, testLoginApi } from './fixtures/auth';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

// One API context per user: the session is a cookie (EXAMCRAFT-126), so each
// user needs a cookie jar of their own.
async function loginAs(creds: { email: string }): Promise<APIRequestContext> {
  const ctx = await pwRequest.newContext();
  await testLoginApi(ctx, creds.email);
  return ctx;
}

async function listDocumentIds(request: APIRequestContext): Promise<number[]> {
  const res = await request.get(`${API_URL}/api/v1/documents/`);
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return (body.documents as Array<{ id: number }>).map((d) => d.id);
}

test.describe('Document visibility privacy (TF-354)', () => {
  test('private upload is owner-only, sharing reveals it to the institution', async () => {
    const userA = await loginAs(E2E_TEST_USER);
    const userB = await loginAs(E2E_TEST_USER_B);
    const userC = await loginAs(E2E_TEST_USER_C);

    // 1. User A uploads a PRIVATE document.
    const uniqueName = `tf354-${Date.now()}.txt`;
    const uploadRes = await userA.post(`${API_URL}/api/v1/documents/upload`, {
      multipart: {
        visibility: 'private',
        file: {
          name: uniqueName,
          mimeType: 'text/plain',
          buffer: Buffer.from('Privacy test content for TF-354.'),
        },
      },
    });
    expect(uploadRes.ok(), `upload failed: ${uploadRes.status()}`).toBeTruthy();
    const docId = (await uploadRes.json()).document_id as number;

    try {
      // 2 + 3. Neither the colleague nor the outsider can see the private doc.
      expect(await listDocumentIds(userA)).toContain(docId);
      expect(await listDocumentIds(userB)).not.toContain(docId);
      expect(await listDocumentIds(userC)).not.toContain(docId);

      // 4. User A shares it institution-wide.
      const patchRes = await userA.patch(
        `${API_URL}/api/v1/documents/${docId}`,
        {
          data: { visibility: 'institution' },
        },
      );
      expect(patchRes.ok(), `patch failed: ${patchRes.status()}`).toBeTruthy();
      expect((await patchRes.json()).visibility).toBe('institution');

      // 5. The colleague now sees it; the outsider still does not.
      expect(await listDocumentIds(userB)).toContain(docId);
      expect(await listDocumentIds(userC)).not.toContain(docId);
    } finally {
      // Cleanup so reruns stay deterministic.
      await userA.delete(`${API_URL}/api/v1/documents/${docId}`);
    }
  });

  test('a colleague cannot change the visibility of a doc they do not own', async () => {
    const userA = await loginAs(E2E_TEST_USER);
    const userB = await loginAs(E2E_TEST_USER_B);

    const uniqueName = `tf354-owner-${Date.now()}.txt`;
    const uploadRes = await userA.post(`${API_URL}/api/v1/documents/upload`, {
      multipart: {
        visibility: 'institution',
        file: {
          name: uniqueName,
          mimeType: 'text/plain',
          buffer: Buffer.from('Owner-only visibility edit test.'),
        },
      },
    });
    expect(uploadRes.ok()).toBeTruthy();
    const docId = (await uploadRes.json()).document_id as number;

    try {
      // B can see the institution-shared doc but must NOT be able to change
      // its visibility — owner-only (403).
      const patchRes = await userB.patch(
        `${API_URL}/api/v1/documents/${docId}`,
        {
          data: { visibility: 'private' },
        },
      );
      expect(patchRes.status()).toBe(403);
    } finally {
      await userA.delete(`${API_URL}/api/v1/documents/${docId}`);
    }
  });
});
