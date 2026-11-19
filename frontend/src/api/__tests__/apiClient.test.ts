/**
 * apiClient.test.ts (EXAMCRAFT-126)
 *
 * Cookie-Session: kein Token-Header, kein Refresh. Geprüft wird, dass
 * - der Axios-Client Cookies mitsendet (withCredentials),
 * - der fetch-Interceptor `credentials: 'include'` für API-Aufrufe setzt,
 * - ein 401 die lokale Session abbaut, ausser an den ausgenommenen Pfaden.
 */

jest.mock('axios', () => {
  const responseHandlers: Array<[(res: any) => any, (err: any) => any]> = [];
  const instance = jest.fn() as any;
  instance.interceptors = {
    request: { use: jest.fn() },
    response: {
      use: jest.fn((onFulfilled: (res: any) => any, onRejected: (err: any) => any) => {
        responseHandlers.push([onFulfilled, onRejected]);
      }),
    },
  };
  instance._responseHandlers = responseHandlers;
  return { __esModule: true, default: { create: jest.fn(() => instance) }, create: jest.fn(() => instance) };
});

describe('apiClient', () => {
  let apiModule: typeof import('../apiClient');
  let axiosMock: any;
  let originalFetch: typeof window.fetch;
  let fetchMock: jest.Mock;
  let logout: jest.Mock;

  beforeEach(async () => {
    jest.resetModules();
    originalFetch = window.fetch;
    fetchMock = jest.fn().mockResolvedValue({ status: 200 });
    window.fetch = fetchMock as never;
    axiosMock = (await import('axios')).default;
    apiModule = await import('../apiClient');
    logout = jest.fn().mockResolvedValue(undefined);
    apiModule.setLogoutCallback(logout);
  });

  afterEach(() => {
    window.fetch = originalFetch;
  });

  it('erzeugt den Axios-Client mit withCredentials und ohne Token-Interceptor', () => {
    expect(axiosMock.create).toHaveBeenCalledWith(expect.objectContaining({ withCredentials: true }));
    expect(apiModule.apiClient.interceptors.request.use).not.toHaveBeenCalled();
  });

  describe('Axios-401', () => {
    const run = async (url: string, status = 401) => {
      const [, onRejected] = (apiModule.apiClient as any)._responseHandlers[0];
      const error = { config: { url }, response: { status } };
      await expect(onRejected(error)).rejects.toBe(error);
    };

    it('baut bei 401 die lokale Session ab', async () => {
      await run('/api/v1/tags');
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it.each(['/api/auth/me', '/api/v1/auth/login', '/api/admin/impersonate/end'])(
      'lässt 401 an %s unberührt',
      async (url) => {
        await run(url);
        expect(logout).not.toHaveBeenCalled();
      },
    );

    it('ignoriert andere Fehlerstatus', async () => {
      await run('/api/v1/tags', 500);
      expect(logout).not.toHaveBeenCalled();
    });
  });

  describe('fetch-Interceptor', () => {
    beforeEach(() => {
      apiModule.setupFetchInterceptor();
    });

    it('sendet das Cookie bei API-Aufrufen', async () => {
      await window.fetch(`${apiModule.API_BASE_URL}/api/v1/exams`, { method: 'GET' });
      expect(fetchMock).toHaveBeenCalledWith(
        `${apiModule.API_BASE_URL}/api/v1/exams`,
        expect.objectContaining({ credentials: 'include', method: 'GET' }),
      );
    });

    it('lässt ein ausdrückliches credentials des Aufrufers gelten', async () => {
      await window.fetch('/api/v1/exams', { credentials: 'omit' });
      expect(fetchMock).toHaveBeenCalledWith('/api/v1/exams', { credentials: 'omit' });
    });

    it('fasst fremde URLs nicht an', async () => {
      await window.fetch('https://cdn.example.com/x.png');
      expect(fetchMock).toHaveBeenCalledWith('https://cdn.example.com/x.png', undefined);
    });

    it('baut bei 401 auf einer API-URL die Session ab', async () => {
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(`${apiModule.API_BASE_URL}/api/v1/exams`);
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('lässt 401 von /api/auth/me dem AuthContext', async () => {
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(`${apiModule.API_BASE_URL}/api/auth/me`);
      expect(logout).not.toHaveBeenCalled();
    });

    it('lässt 401 von /api/v1/auth/ und /api/admin/impersonate/end dem AuthContext', async () => {
      for (const path of ['/api/v1/auth/login', '/api/admin/impersonate/end']) {
        fetchMock.mockResolvedValueOnce({ status: 401 });
        await window.fetch(`${apiModule.API_BASE_URL}${path}`);
      }
      expect(logout).not.toHaveBeenCalled();
    });

    it('wertet ein Request-Objekt als Input über dessen URL aus', async () => {
      const request = new Request(`${apiModule.API_BASE_URL}/api/v1/exams`);
      await window.fetch(request);
      expect(fetchMock).toHaveBeenCalledWith(
        request,
        expect.objectContaining({ credentials: 'include' }),
      );

      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(request);
      expect(logout).toHaveBeenCalledTimes(1);

      const excluded = new Request(`${apiModule.API_BASE_URL}/api/auth/me`);
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(excluded);
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('fasst ein Request-Objekt einer fremden URL nicht an', async () => {
      const request = new Request('https://cdn.example.com/x.png');
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(request);
      expect(fetchMock).toHaveBeenCalledWith(request, undefined);
      expect(logout).not.toHaveBeenCalled();
    });

    it('behandelt Pfade mit /ws/-Präfix als API-Aufruf', async () => {
      await window.fetch('/ws/tasks/abc');
      expect(fetchMock).toHaveBeenCalledWith(
        '/ws/tasks/abc',
        expect.objectContaining({ credentials: 'include' }),
      );
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch('/ws/tasks/abc');
      expect(logout).toHaveBeenCalledTimes(1);
    });

    it('behandelt Pfade mit /api/-Präfix ohne Host als API-Aufruf', async () => {
      await window.fetch('/api/v1/exams');
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/v1/exams',
        expect.objectContaining({ credentials: 'include' }),
      );
    });

    it('gibt die Antwort unverändert zurück', async () => {
      const response = { status: 200, ok: true };
      fetchMock.mockResolvedValueOnce(response);
      await expect(window.fetch('/api/v1/exams')).resolves.toBe(response);
    });

    it('installiert sich nur einmal', async () => {
      apiModule.setupFetchInterceptor();
      fetchMock.mockResolvedValueOnce({ status: 401 });
      await window.fetch(`${apiModule.API_BASE_URL}/api/v1/exams`);
      expect(logout).toHaveBeenCalledTimes(1);
    });
  });
});
