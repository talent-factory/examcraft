import { fetchLiveActivity, sendActivityHeartbeat } from './liveActivityService';
import { API_BASE_URL, ACCESS_TOKEN_KEY } from './httpClient';

describe('fetchLiveActivity', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    localStorage.clear();
    jest.restoreAllMocks();
  });

  it('GETs /api/v1/ops/activity with the auth header and returns the parsed snapshot', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'test-token');
    const snapshot = {
      generated_at: '2026-09-16T08:00:00+00:00',
      buckets: {
        documents_upload: { value: 0, exact: true },
        questions_review: { value: 5, exact: false },
      },
    };
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => snapshot,
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await fetchLiveActivity();

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/ops/activity`,
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
      }),
    );
    expect(result).toEqual(snapshot);
  });

  it('propagates a non-2xx response as an ApiError', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      text: async () => '',
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(fetchLiveActivity()).rejects.toMatchObject({ status: 403 });
  });
});

describe('sendActivityHeartbeat', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    localStorage.clear();
    jest.restoreAllMocks();
  });

  it('POSTs the bucket_id to /api/v1/activity/heartbeat and resolves without parsing a body', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'test-token');
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 204,
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(sendActivityHeartbeat('questions_review')).resolves.toBeUndefined();

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/activity/heartbeat`,
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({ bucket_id: 'questions_review' }),
      }),
    );
  });

  it('propagates a non-2xx response as an ApiError', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      text: async () => '',
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(sendActivityHeartbeat('questions_review')).rejects.toMatchObject({ status: 422 });
  });

  it('does not go through the auth-retry/logout path on a 401 (PR #286 review: a background ping must not force-logout mid-workflow)', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      text: async () => '',
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(sendActivityHeartbeat('questions_review')).rejects.toMatchObject({ status: 401 });

    // withAuthRetry would attempt a token refresh and then re-call fetch a
    // second time — a single call proves the retry path was bypassed.
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
