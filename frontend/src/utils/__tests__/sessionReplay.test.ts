/**
 * Tests fuer die lokale Reimplementierung des rrweb-Session-Replay-Wrappers (TF-867).
 * `rrweb.record()` wird gemockt (siehe unten) -- ein Unit-Test fuer Batching-/Sampling-Logik
 * braucht kein echtes DOM-Recording, nur den `emit`-Callback, den `record()` erhaelt.
 */
import { randomUUID } from 'crypto';
import type { eventWithTime } from '@rrweb/types';
import { createSessionReplayRecorder } from '../sessionReplay';

// jsdom (react-scripts' Jest-Testumgebung) stellt kein Web Crypto API global bereit -- anders als
// jeder echte Browser. Mit Node's `crypto.randomUUID` nachruesten, statt `sessionReplay.ts`s
// Produktionscode fuer eine reine Testumgebungs-Luecke anzupassen.
if (typeof globalThis.crypto === 'undefined' || typeof globalThis.crypto.randomUUID !== 'function') {
  Object.defineProperty(globalThis, 'crypto', {
    value: { randomUUID },
    configurable: true,
  });
}

// jest.mock()'s Hoisting erlaubt nur Out-of-Scope-Variablen mit "mock"-Praefix
// (babel-plugin-jest-hoist) -- und hebt diesen Aufruf automatisch ueber den obigen
// `../sessionReplay`-Import, unabhaengig von der Quelltext-Reihenfolge.
const mockRecord = jest.fn();
jest.mock('rrweb', () => ({
  record: (options: Record<string, unknown>) => mockRecord(options),
}));

const ENDPOINT = '/api/v1/monitoring/session-replay';

function makeEvent(overrides: Partial<eventWithTime> = {}): eventWithTime {
  return { type: 3, data: {}, timestamp: Date.now(), ...overrides } as eventWithTime;
}

/** Emittiert ein synthetisches rrweb-Event ueber den `emit`-Callback, mit dem `record()` zuletzt
 * aufgerufen wurde. */
function emitEvent(overrides: Partial<eventWithTime> = {}): void {
  const lastCall = mockRecord.mock.calls[mockRecord.mock.calls.length - 1] as
    | [{ emit: (event: eventWithTime) => void }]
    | undefined;
  if (!lastCall) {
    throw new Error('rrweb.record() wurde noch nicht aufgerufen -- recorder.start() vergessen?');
  }
  lastCall[0].emit(makeEvent(overrides));
}

let stopRecordingSpy: jest.Mock;
let mockFetch: jest.MockedFunction<typeof fetch>;

beforeEach(() => {
  jest.useFakeTimers();
  stopRecordingSpy = jest.fn();
  mockRecord.mockReset();
  mockRecord.mockReturnValue(stopRecordingSpy);
  mockFetch = jest.fn().mockResolvedValue({ ok: true } as Response);
  global.fetch = mockFetch;
});

afterEach(() => {
  jest.useRealTimers();
  jest.restoreAllMocks();
});

describe('createSessionReplayRecorder — Konstruktions-Validierung', () => {
  it('wirft sofort bei leerem endpoint', () => {
    expect(() => createSessionReplayRecorder({ endpoint: '' })).toThrow(/endpoint/);
    expect(() => createSessionReplayRecorder({ endpoint: '   ' })).toThrow(/endpoint/);
  });

  it('wirft bei einer sampleRate ausserhalb [0, 1]', () => {
    expect(() => createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: -0.1 })).toThrow(
      /sampleRate/
    );
    expect(() => createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: 1.1 })).toThrow(
      /sampleRate/
    );
  });

  it('wirft bei einer errorSampleRate ausserhalb [0, 1]', () => {
    expect(() =>
      createSessionReplayRecorder({ endpoint: ENDPOINT, errorSampleRate: -1 })
    ).toThrow(/errorSampleRate/);
  });

  it('vergibt jedem Recorder eine eigene, stabile sessionId', () => {
    const a = createSessionReplayRecorder({ endpoint: ENDPOINT });
    const b = createSessionReplayRecorder({ endpoint: ENDPOINT });

    expect(a.sessionId).not.toBe(b.sessionId);
  });
});

describe('createSessionReplayRecorder — DSGVO-Defaults', () => {
  it('startet rrweb.record() mit maskAllInputs/maskTextSelector/blockSelector als Default', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0); // < jede sampleRate > 0 -> sofort gesampelt
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });

    recorder.start();

    expect(mockRecord).toHaveBeenCalledWith(
      expect.objectContaining({
        maskAllInputs: true,
        maskTextSelector: '*',
        blockSelector: expect.stringContaining('img'),
      })
    );
  });

  it('deaktiviert Maskierung/Blocking nur ueber den expliziten dangerouslyDisableDefaultPrivacy-Opt-out', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({
      endpoint: ENDPOINT,
      dangerouslyDisableDefaultPrivacy: true,
    });

    recorder.start();

    expect(mockRecord).toHaveBeenCalledWith(
      expect.objectContaining({
        maskAllInputs: false,
        maskTextSelector: undefined,
        blockSelector: undefined,
      })
    );
  });
});

describe('createSessionReplayRecorder — Sampling', () => {
  it('startet sofort, wenn der sampleRate-Wurf erfolgreich ist', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0.05);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: 0.1 });

    recorder.start();

    expect(recorder.isRecording()).toBe(true);
    expect(mockRecord).toHaveBeenCalledTimes(1);
  });

  it('startet nicht, wenn der sampleRate-Wurf fehlschlaegt', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0.5);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: 0.1 });

    recorder.start();

    expect(recorder.isRecording()).toBe(false);
    expect(mockRecord).not.toHaveBeenCalled();
  });

  it('ist idempotent -- ein zweiter start()-Aufruf wuerfelt nicht erneut', () => {
    const randomSpy = jest.spyOn(Math, 'random').mockReturnValue(0.5);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: 0.1 });

    recorder.start();
    recorder.start();

    expect(randomSpy).toHaveBeenCalledTimes(1);
  });

  it('notifyError() startet eine ungesampelte Session bei erfolgreichem errorSampleRate-Wurf nachtraeglich', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0.5);
    const recorder = createSessionReplayRecorder({
      endpoint: ENDPOINT,
      sampleRate: 0.1,
      errorSampleRate: 1,
    });
    recorder.start();
    expect(recorder.isRecording()).toBe(false);

    recorder.notifyError();

    expect(recorder.isRecording()).toBe(true);
  });

  it('notifyError() ist ein No-op, wenn die Session bereits aufzeichnet', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();

    recorder.notifyError();

    expect(mockRecord).toHaveBeenCalledTimes(1);
  });

  it('start() nach vorherigem notifyError() rollt nicht erneut und startet kein zweites Recording', () => {
    // 0 wuerde bei einem erneuten Wurf garantiert (wieder) treffen -- beweist, dass start() nach
    // der isRecording()-Guard gar nicht erst nochmal wuerfelt.
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, errorSampleRate: 1 });

    recorder.notifyError();
    expect(recorder.isRecording()).toBe(true);
    expect(mockRecord).toHaveBeenCalledTimes(1);

    recorder.start();

    // Ohne die isRecording()-Guard in start() wuerde hier ein zweites beginRecording('normal')
    // feuern und stopRecordingFn/flushTimer der ersten (error-getriggerten) Aufzeichnung leaken.
    expect(mockRecord).toHaveBeenCalledTimes(1);
  });
});

describe('createSessionReplayRecorder — record()-Fehlerpfade', () => {
  it('loggt und bleibt isRecording()=false, wenn record() keinen Stop-Handler liefert', () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(Math, 'random').mockReturnValue(0);
    mockRecord.mockReturnValueOnce(undefined);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });

    recorder.start();

    expect(recorder.isRecording()).toBe(false);
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('loggt statt zu werfen, wenn record() selbst wirft (z. B. CSP-Restriktion)', () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(Math, 'random').mockReturnValue(0);
    mockRecord.mockImplementationOnce(() => {
      throw new Error('CSP blocked');
    });
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });

    expect(() => recorder.start()).not.toThrow();

    expect(recorder.isRecording()).toBe(false);
    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });
});

describe('createSessionReplayRecorder — Batching/Flush', () => {
  it('sendet gepufferte Events per POST an den endpoint, ohne keepalive fuer einen regulaeren Flush', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();

    emitEvent();
    await recorder.flush();

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, init] = mockFetch.mock.calls[0]!;
    expect(url).toBe(ENDPOINT);
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.sessionId).toBe(recorder.sessionId);
    expect(body.samplingMode).toBe('normal');
    expect(body.events).toHaveLength(1);
    // Ein regulaerer Batch (insb. der erste mit dem Full-Snapshot) ist typischerweise groesser
    // als die 64-KiB-Grenze, die der Browser fuer keepalive-Requests hart durchsetzt --
    // keepalive muss hier also false sein, sonst scheitert dieser Flush faktisch immer.
    expect((init as RequestInit).keepalive).toBe(false);
  });

  it('saniert die href eines rrweb-Meta-Events vor dem Puffern (strippt Query/Fragment)', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();

    emitEvent({
      type: 4,
      data: { href: 'https://example.com/auth/reset-password/confirm?token=super-secret' },
    } as Partial<eventWithTime>);
    await recorder.flush();

    const body = JSON.parse((mockFetch.mock.calls[0]![1] as RequestInit).body as string);
    expect(body.events[0].data.href).toBe('https://example.com/auth/reset-password/confirm');
    expect(JSON.stringify(body.events[0])).not.toContain('super-secret');
  });

  it('markiert Error-getriggerte Batches mit samplingMode "error"', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0.99);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, errorSampleRate: 1 });
    recorder.notifyError();

    emitEvent();
    await recorder.flush();

    const body = JSON.parse((mockFetch.mock.calls[0]![1] as RequestInit).body as string);
    expect(body.samplingMode).toBe('error');
  });

  it('haengt die von getCorrelationId() gelieferte ID an jeden Batch', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({
      endpoint: ENDPOINT,
      getCorrelationId: () => 'trace-xyz',
    });
    recorder.start();

    emitEvent();
    await recorder.flush();

    const body = JSON.parse((mockFetch.mock.calls[0]![1] as RequestInit).body as string);
    expect(body.correlationId).toBe('trace-xyz');
  });

  it('flusht automatisch, sobald batchMaxEvents erreicht ist', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, batchMaxEvents: 2 });
    recorder.start();

    emitEvent();
    expect(mockFetch).not.toHaveBeenCalled();
    emitEvent();

    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('flusht automatisch im batchIntervalMs-Takt', () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, batchIntervalMs: 5000 });
    recorder.start();
    emitEvent();

    jest.advanceTimersByTime(5000);

    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('flush() ist ein No-op bei leerem Puffer', async () => {
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });

    await recorder.flush();

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('wirft nie und loggt stattdessen bei einem Netzwerkfehler', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(Math, 'random').mockReturnValue(0);
    mockFetch.mockRejectedValueOnce(new Error('network down'));
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();
    emitEvent();

    await expect(recorder.flush()).resolves.toBeUndefined();

    expect(errorSpy).toHaveBeenCalled();
    errorSpy.mockRestore();
  });

  it('wirft nie und loggt stattdessen bei einer Non-2xx-Antwort', async () => {
    const errorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    jest.spyOn(Math, 'random').mockReturnValue(0);
    mockFetch.mockResolvedValueOnce({ ok: false, status: 500 } as Response);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();
    emitEvent();

    await expect(recorder.flush()).resolves.toBeUndefined();

    expect(errorSpy).toHaveBeenCalledWith(expect.stringContaining('HTTP 500'));
    errorSpy.mockRestore();
  });
});

describe('createSessionReplayRecorder — stop()', () => {
  it('stoppt rrweb.record(), raeumt den Timer ab und flusht ein letztes Mal mit keepalive', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();
    emitEvent();

    await recorder.stop();

    expect(stopRecordingSpy).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(recorder.isRecording()).toBe(false);
    // Anders als ein regulaerer Flush: der abschliessende Flush aus stop() soll einen
    // Seitenwechsel/Unload ueberleben, siehe flush()s Kommentar zur 64-KiB-Grenze.
    expect((mockFetch.mock.calls[0]![1] as RequestInit).keepalive).toBe(true);
  });

  it('ist idempotent -- ein zweiter stop()-Aufruf sendet keinen weiteren Flush', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT });
    recorder.start();
    emitEvent();

    await recorder.stop();
    await recorder.stop();

    expect(stopRecordingSpy).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it('start()/notifyError() sind nach stop() dauerhaft No-ops', async () => {
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const recorder = createSessionReplayRecorder({ endpoint: ENDPOINT, sampleRate: 0 });
    await recorder.stop();

    recorder.start();
    recorder.notifyError();

    expect(mockRecord).not.toHaveBeenCalled();
  });
});

// Bewusst `jest.resetModules()` + dynamischer Import pro Test (wie `errorReporting.test.ts`s
// `initErrorReporting`-Tests): `initSessionReplay`/`notifySessionReplayError` teilen sich den
// modulweiten Default-Recorder, ein frisches Modul pro Test verhindert Bleed zwischen den Faellen.
describe('initSessionReplay / notifySessionReplayError (Env-Gating)', () => {
  const originalEnv = process.env.REACT_APP_ENVIRONMENT;

  afterEach(() => {
    process.env.REACT_APP_ENVIRONMENT = originalEnv;
  });

  it('startet keinen Recorder in development', async () => {
    process.env.REACT_APP_ENVIRONMENT = 'development';
    jest.resetModules();
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const { initSessionReplay } = await import('../sessionReplay');

    initSessionReplay();

    expect(mockRecord).not.toHaveBeenCalled();
  });

  it('startet einen Recorder ausserhalb von development', async () => {
    process.env.REACT_APP_ENVIRONMENT = 'production';
    jest.resetModules();
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const { initSessionReplay } = await import('../sessionReplay');

    initSessionReplay();

    expect(mockRecord).toHaveBeenCalledTimes(1);
  });

  it('notifySessionReplayError() ist ein sicheres No-op ohne vorherigen initSessionReplay()-Aufruf', async () => {
    jest.resetModules();
    const { notifySessionReplayError } = await import('../sessionReplay');

    expect(() => notifySessionReplayError()).not.toThrow();
    expect(mockRecord).not.toHaveBeenCalled();
  });

  it('notifySessionReplayError() delegiert an den vom initSessionReplay() erzeugten Default-Recorder', async () => {
    process.env.REACT_APP_ENVIRONMENT = 'production';
    jest.resetModules();
    jest.spyOn(Math, 'random').mockReturnValue(0.99); // Normal-Sampling schlaegt fehl
    const { initSessionReplay, notifySessionReplayError } = await import('../sessionReplay');
    initSessionReplay();
    expect(mockRecord).not.toHaveBeenCalled();

    notifySessionReplayError();

    expect(mockRecord).toHaveBeenCalledTimes(1);
  });

  it('registriert einen pagehide-Listener, der den Default-Recorder stoppt/flusht', async () => {
    process.env.REACT_APP_ENVIRONMENT = 'production';
    jest.resetModules();
    jest.spyOn(Math, 'random').mockReturnValue(0);
    const addEventListenerSpy = jest.spyOn(window, 'addEventListener');
    const { initSessionReplay } = await import('../sessionReplay');

    initSessionReplay();
    emitEvent();

    const pagehideHandler = addEventListenerSpy.mock.calls.find(
      ([eventName]) => eventName === 'pagehide'
    )?.[1] as (() => void) | undefined;
    expect(pagehideHandler).toBeDefined();

    pagehideHandler?.();
    await Promise.resolve();

    expect(stopRecordingSpy).toHaveBeenCalledTimes(1);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    addEventListenerSpy.mockRestore();
  });
});
