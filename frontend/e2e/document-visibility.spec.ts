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
import { test, expect, type APIRequestContext } from '@playwright/test';
import { E2E_TEST_USER, E2E_TEST_USER_B, E2E_TEST_USER_C } from './fixtures/auth';

const API_URL = process.env.E2E_API_URL ?? 'http://localhost:8000';

async function login(
  request: APIRequestContext,
  creds: { email: string; password: string },
): Promise<string> {
  const res = await request.post(`${API_URL}/api/auth/login`, {
    data: { email: creds.email, password: creds.password },
  });
  expect(res.ok(), `login failed for ${creds.email}: ${res.status()}`).toBeTruthy();
  const body = await res.json();
  return body.access_token as string;
}

async function listDocumentIds(
  request: APIRequestContext,
  token: string,
): Promise<number[]> {
  const res = await request.get(`${API_URL}/api/v1/documents/`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return (body.documents as Array<{ id: number }>).map((d) => d.id);
}

test.describe('Document visibility privacy (TF-354)', () => {
  test('private upload is owner-only, sharing reveals it to the institution', async ({
    request,
  }) => {
    const tokenA = await login(request, E2E_TEST_USER);
    const tokenB = await login(request, E2E_TEST_USER_B);
    const tokenC = await login(request, E2E_TEST_USER_C);

    // 1. User A uploads a PRIVATE document.
    const uniqueName = `tf354-${Date.now()}.txt`;
    const uploadRes = await request.post(`${API_URL}/api/v1/documents/upload`, {
      headers: { Authorization: `Bearer ${tokenA}` },
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
      expect(await listDocumentIds(request, tokenA)).toContain(docId);
      expect(await listDocumentIds(request, tokenB)).not.toContain(docId);
      expect(await listDocumentIds(request, tokenC)).not.toContain(docId);

      // 4. User A shares it institution-wide.
      const patchRes = await request.patch(
        `${API_URL}/api/v1/documents/${docId}`,
        {
          headers: { Authorization: `Bearer ${tokenA}` },
          data: { visibility: 'institution' },
        },
      );
      expect(patchRes.ok(), `patch failed: ${patchRes.status()}`).toBeTruthy();
      expect((await patchRes.json()).visibility).toBe('institution');

      // 5. The colleague now sees it; the outsider still does not.
      expect(await listDocumentIds(request, tokenB)).toContain(docId);
      expect(await listDocumentIds(request, tokenC)).not.toContain(docId);
    } finally {
      // Cleanup so reruns stay deterministic.
      await request.delete(`${API_URL}/api/v1/documents/${docId}`, {
        headers: { Authorization: `Bearer ${tokenA}` },
      });
    }
  });

  test('a colleague cannot change the visibility of a doc they do not own', async ({
    request,
  }) => {
    const tokenA = await login(request, E2E_TEST_USER);
    const tokenB = await login(request, E2E_TEST_USER_B);

    const uniqueName = `tf354-owner-${Date.now()}.txt`;
    const uploadRes = await request.post(`${API_URL}/api/v1/documents/upload`, {
      headers: { Authorization: `Bearer ${tokenA}` },
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
      const patchRes = await request.patch(
        `${API_URL}/api/v1/documents/${docId}`,
        {
          headers: { Authorization: `Bearer ${tokenB}` },
          data: { visibility: 'private' },
        },
      );
      expect(patchRes.status()).toBe(403);
    } finally {
      await request.delete(`${API_URL}/api/v1/documents/${docId}`, {
        headers: { Authorization: `Bearer ${tokenA}` },
      });
    }
  });
});
