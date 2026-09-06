import { fetchOpsHealth } from './opsHealthService';
import { API_BASE_URL, ACCESS_TOKEN_KEY } from './httpClient';

describe('fetchOpsHealth', () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    localStorage.clear();
    jest.restoreAllMocks();
  });

  it('GETs /api/v1/ops/health with the auth header and returns the parsed snapshot', async () => {
    localStorage.setItem(ACCESS_TOKEN_KEY, 'test-token');
    const snapshot = {
      generated_at: '2026-09-05T08:00:00+00:00',
      overall_status: 'green',
      components: {
        frontend: {
          status: 'green',
          metric_label: 'reachable_machines',
          metric_value: '1/1',
          timestamp: '2026-09-05T08:00:00+00:00',
          detail: null,
          deep_link: 'https://talent-factory.sentry.io/projects/talent-factory/examcraft-frontend/',
          sentry: { configured: false },
        },
        backend: {
          status: 'green',
          metric_label: 'reachable_machines',
          metric_value: '1/1',
          timestamp: '2026-09-05T08:00:00+00:00',
          detail: null,
          deep_link: null,
          sentry: { configured: false },
        },
        db: {
          status: 'yellow',
          metric_label: 'latency_ms',
          metric_value: 320,
          timestamp: '2026-09-05T08:00:00+00:00',
          detail: null,
          deep_link: null,
        },
        rabbitmq: {
          status: 'green',
          metric_label: 'queued_messages',
          metric_value: 0,
          timestamp: '2026-09-05T08:00:00+00:00',
          detail: null,
          deep_link: 'https://examcraft-rabbitmq.fly.dev',
        },
        celery: {
          status: 'red',
          metric_label: 'online_workers',
          metric_value: 0,
          timestamp: '2026-09-05T08:00:00+00:00',
          detail: 'no workers registered',
          deep_link: 'https://examcraft-flower.fly.dev',
        },
      },
    };
    const mockFetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => snapshot,
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    const result = await fetchOpsHealth();

    expect(mockFetch).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/ops/health`,
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({ Authorization: 'Bearer test-token' }),
      }),
    );
    expect(result).toEqual(snapshot);
    expect(result.components.celery.status).toBe('red');
  });

  it('propagates a non-2xx response as an ApiError', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 403,
      statusText: 'Forbidden',
      text: async () => '',
    });
    global.fetch = mockFetch as unknown as typeof fetch;

    await expect(fetchOpsHealth()).rejects.toMatchObject({ status: 403 });
  });
});
