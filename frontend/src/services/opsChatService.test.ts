import { sendOpsChatMessage } from './opsChatService';
import { API_BASE_URL, ACCESS_TOKEN_KEY } from './httpClient';

describe('sendOpsChatMessage', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    localStorage.clear();
    jest.restoreAllMocks();
  });

  it('POSTs the message and history to /api/v1/ops/chat and returns the reply', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'test-token');
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ reply: 'Celery hat 2 aktive Worker.' }),
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    const history = [{ role: 'user' as const, content: 'Was ist Celery?' }];
    const result = await sendOpsChatMessage('Wie viele Worker?', history);

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/ops/chat`,
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        }),
        body: JSON.stringify({ message: 'Wie viele Worker?', history }),
      }),
    );
    expect(result).toBe('Celery hat 2 aktive Worker.');
  });

  it('propagates a non-2xx response as an ApiError', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      text: async () => '',
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(sendOpsChatMessage('hi', [])).rejects.toMatchObject({ status: 403 });
  });
});
