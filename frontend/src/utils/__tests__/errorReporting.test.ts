/**
 * Tests fuer die lokale Reimplementierung des `/client-errors`-Reportings
 * (TF-866). Nutzt ueberwiegend frische `createErrorReporter()`-Instanzen,
 * um sich nicht ueber den modulweiten `defaultReporter`-Drossel-Zustand
 * (`reportClientError`/`initErrorReporting`) hinweg gegenseitig zu
 * beeinflussen.
 */
import { createErrorReporter, safeUrl, type ClientErrorPayload } from '../errorReporting';

global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

const payload: ClientErrorPayload = {
  message: 'boom',
  stack: 'Error: boom\n  at x',
  url: 'https://app.example.com/dashboard?token=secret#frag',
  userAgent: 'jest-agent',
};

describe('errorReporting', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('safeUrl', () => {
    it('strippt Query-String und Fragment, behaelt Origin + Pfad', () => {
      expect(safeUrl('https://app.example.com/dashboard?token=secret#frag')).toBe(
        'https://app.example.com/dashboard'
      );
    });

    it('gibt bei unparsbarer URL einen leeren String zurueck und warnt', () => {
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      expect(safeUrl('not a url')).toBe('');
      expect(warnSpy).toHaveBeenCalledWith(expect.stringContaining('not a url'));
      warnSpy.mockRestore();
    });
  });

  describe('createErrorReporter', () => {
    it('wirft sofort bei leerem endpoint', () => {
      expect(() => createErrorReporter({ endpoint: '' })).toThrow(/endpoint.*Pflicht/);
      expect(() => createErrorReporter({ endpoint: '   ' })).toThrow(/endpoint.*Pflicht/);
    });

    it.each([-1, NaN, Infinity])('wirft sofort bei ungueltigem maxReports=%s', (maxReports) => {
      expect(() => createErrorReporter({ endpoint: '/client-errors', maxReports })).toThrow(
        /maxReports/
      );
    });

    it('sendet den Payload mit sanitizierter url per POST an den Endpoint', async () => {
      mockFetch.mockResolvedValueOnce({ ok: true } as Response);
      const reporter = createErrorReporter({ endpoint: '/api/v1/monitoring/client-errors' });

      await reporter.reportError(payload);

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/monitoring/client-errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, url: 'https://app.example.com/dashboard' }),
        keepalive: true,
      });
    });

    it('wirft nie und loggt stattdessen bei einem Netzwerkfehler', async () => {
      const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockFetch.mockRejectedValueOnce(new Error('network down'));
      const reporter = createErrorReporter({ endpoint: '/client-errors' });

      await expect(reporter.reportError(payload)).resolves.toBeUndefined();
      expect(errorSpy).toHaveBeenCalled();
      errorSpy.mockRestore();
    });

    it('wirft nie und loggt stattdessen bei einer Non-2xx-Antwort', async () => {
      const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
      mockFetch.mockResolvedValueOnce({ ok: false, status: 429 } as Response);
      const reporter = createErrorReporter({ endpoint: '/client-errors' });

      await reporter.reportError(payload);

      expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('HTTP 429'));
      errorSpy.mockRestore();
    });

    it('dedupliziert identische message+stack-Signaturen', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      const reporter = createErrorReporter({ endpoint: '/client-errors' });

      await reporter.reportError(payload);
      await reporter.reportError(payload);

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it('drosselt nach maxReports und warnt nur einmal', async () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      const warnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
      const reporter = createErrorReporter({ endpoint: '/client-errors', maxReports: 2 });

      await reporter.reportError({ ...payload, message: 'a' });
      await reporter.reportError({ ...payload, message: 'b' });
      await reporter.reportError({ ...payload, message: 'c' });
      await reporter.reportError({ ...payload, message: 'd' });

      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(warnSpy).toHaveBeenCalledTimes(1);
      warnSpy.mockRestore();
    });

    // Bewusst kein echtes `window.dispatchEvent(new Event('error'))`: jsdom
    // behandelt ein dispatchtes "error"-Event mit gesetzter `.error`-Property
    // wie eine echte uncaught exception und meldet sie ueber seine virtuelle
    // Konsole, was den Test unabhaengig vom eigentlichen Verhalten scheitern
    // laesst. Stattdessen wird der bei `addEventListener` registrierte
    // Handler abgefangen und direkt aufgerufen.
    it('attachGlobalHandlers meldet window "error"-Events und entfernt Listener beim Cleanup', () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      const reporter = createErrorReporter({ endpoint: '/client-errors' });
      const listeners: Record<string, EventListener> = {};
      const addSpy = jest
        .spyOn(window, 'addEventListener')
        .mockImplementation((type, listener) => {
          listeners[type] = listener as EventListener;
        });
      const removeSpy = jest.spyOn(window, 'removeEventListener').mockImplementation(() => {});

      const detach = reporter.attachGlobalHandlers();
      const error = new Error('render-free crash');
      listeners['error']({ error, message: error.message } as unknown as ErrorEvent);

      expect(mockFetch).toHaveBeenCalledWith(
        '/client-errors',
        expect.objectContaining({
          body: expect.stringContaining('"message":"render-free crash"'),
        })
      );

      detach();
      expect(removeSpy).toHaveBeenCalledWith('error', listeners['error']);
      expect(removeSpy).toHaveBeenCalledWith('unhandledrejection', listeners['unhandledrejection']);

      addSpy.mockRestore();
      removeSpy.mockRestore();
    });

    it('attachGlobalHandlers meldet unhandledrejection-Events', () => {
      mockFetch.mockResolvedValue({ ok: true } as Response);
      const reporter = createErrorReporter({ endpoint: '/client-errors' });
      const listeners: Record<string, EventListener> = {};
      const addSpy = jest
        .spyOn(window, 'addEventListener')
        .mockImplementation((type, listener) => {
          listeners[type] = listener as EventListener;
        });

      reporter.attachGlobalHandlers();
      listeners['unhandledrejection']({
        reason: new Error('promise blew up'),
      } as unknown as PromiseRejectionEvent);

      expect(mockFetch).toHaveBeenCalledWith(
        '/client-errors',
        expect.objectContaining({
          body: expect.stringContaining('"message":"promise blew up"'),
        })
      );

      addSpy.mockRestore();
    });
  });

  describe('initErrorReporting', () => {
    const originalEnv = process.env.REACT_APP_ENVIRONMENT;

    afterEach(() => {
      process.env.REACT_APP_ENVIRONMENT = originalEnv;
    });

    it('registriert keine globalen Handler in development', async () => {
      process.env.REACT_APP_ENVIRONMENT = 'development';
      jest.resetModules();
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const { initErrorReporting } = await import('../errorReporting');

      initErrorReporting();

      expect(addEventListenerSpy).not.toHaveBeenCalledWith('error', expect.anything());
      addEventListenerSpy.mockRestore();
    });

    it('registriert globale Handler ausserhalb von development', async () => {
      process.env.REACT_APP_ENVIRONMENT = 'production';
      jest.resetModules();
      const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
      const { initErrorReporting } = await import('../errorReporting');

      initErrorReporting();

      expect(addEventListenerSpy).toHaveBeenCalledWith('error', expect.any(Function));
      expect(addEventListenerSpy).toHaveBeenCalledWith('unhandledrejection', expect.any(Function));
      addEventListenerSpy.mockRestore();
    });
  });

  // Bewusst `jest.resetModules()` + dynamischer Import pro Test (wie oben bei
  // `initErrorReporting`): `reportClientError`/`reportHandledError` teilen sich
  // den modulweiten `defaultReporter`-Drossel-/Dedup-Zustand, ein frisches
  // Modul pro Test verhindert Bleed zwischen den Faellen.
  describe('reportClientError (Env-Gating)', () => {
    const originalEnv = process.env.REACT_APP_ENVIRONMENT;

    afterEach(() => {
      process.env.REACT_APP_ENVIRONMENT = originalEnv;
    });

    it('sendet keinen Request in development — Paritaet zum bisherigen initSentry(), das ohne REACT_APP_ENABLE_SENTRY nie initialisiert wurde', async () => {
      process.env.REACT_APP_ENVIRONMENT = 'development';
      jest.resetModules();
      const { reportClientError } = await import('../errorReporting');

      await reportClientError(payload);

      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('sendet ausserhalb von development', async () => {
      process.env.REACT_APP_ENVIRONMENT = 'production';
      jest.resetModules();
      mockFetch.mockResolvedValueOnce({ ok: true } as Response);
      const { reportClientError } = await import('../errorReporting');

      await reportClientError(payload);

      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('reportHandledError', () => {
    const originalEnv = process.env.REACT_APP_ENVIRONMENT;

    beforeEach(() => {
      // Reporting muss aktiv sein, um das gesendete Payload zu inspizieren.
      process.env.REACT_APP_ENVIRONMENT = 'production';
    });

    afterEach(() => {
      process.env.REACT_APP_ENVIRONMENT = originalEnv;
    });

    it('haengt den Kontext als "key=value"-Suffix an die message an, filtert undefined und JSON-serialisiert Nicht-Strings', async () => {
      jest.resetModules();
      mockFetch.mockResolvedValueOnce({ ok: true } as Response);
      const { reportHandledError } = await import('../errorReporting');

      reportHandledError(new Error('boom'), {
        feature: 'aktivitaeten',
        status: 404,
        detail: undefined,
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"message":"boom [feature=aktivitaeten status=404]"'),
        })
      );
    });

    it('haengt ohne context keinen Suffix an und wandelt einen Nicht-Error-Wert via String() in eine Error-message um', async () => {
      jest.resetModules();
      mockFetch.mockResolvedValueOnce({ ok: true } as Response);
      const { reportHandledError } = await import('../errorReporting');

      reportHandledError('plain string error');

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"message":"plain string error"'),
        })
      );
    });

    it('respektiert dasselbe Env-Gating wie reportClientError', async () => {
      process.env.REACT_APP_ENVIRONMENT = 'development';
      jest.resetModules();
      const { reportHandledError } = await import('../errorReporting');

      reportHandledError(new Error('boom'), { feature: 'aktivitaeten' });

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
