/**
 * Client-seitiger rrweb-Wrapper für Session-Replay-Recording, meldet gebatchte Events an den
 * Backend-Proxy `POST /api/v1/monitoring/session-replay` (TF-867, ersetzt Sentrys
 * `replayIntegration()`).
 *
 * Bewusst LOKAL reimplementiert statt `@talent-factory/specula-client` (specula-client-js) zu
 * importieren, obwohl dessen `createSessionReplayRecorder()` (TF-855) genau diese Logik schon
 * hat: `core/frontend` wird unveraendert als Open-Source-Mirror veroeffentlicht
 * (`git subtree split --prefix=core`), und `bun install` laeuft dort ohne Zugriff auf private
 * GitHub-Pakete (`specula-client-js` ist nicht auf npm) -- exakt dieselbe Begruendung wie
 * `errorReporting.ts` (TF-866), siehe dessen Moduldoc fuer Details zum Build-Bruch-Risiko eines
 * statischen Imports aus einem nicht aufloesbaren Paket. `rrweb` selbst ist dagegen ein
 * oeffentliches npm-Paket (siehe `package.json`), deshalb bleibt DAS als echte Dependency
 * nutzbar -- nur der duenne Wrapper drumherum wird hier nachgebildet statt importiert.
 *
 * API-Form und Verhalten (Sampling, Batching, DSGVO-Defaults) wurden bewusst nach dem Vorbild von
 * specula-client-js' `sessionReplay.ts` modelliert (Stand TF-855/TF-867), damit ein spaeterer
 * Vergleich/Audit beider Implementierungen einfach bleibt -- es gibt aber keine CI-/Build-Kopplung
 * zwischen den beiden Repos, die diese Parität erzwingt oder prueft; sie kann bei kuenftigen
 * Aenderungen an einer der beiden Seiten stillschweigend auseinanderlaufen.
 */

import { record } from 'rrweb';
import { EventType, type eventWithTime } from '@rrweb/types';

export type SessionReplaySamplingMode = 'normal' | 'error';

export interface SessionReplayEventBatch {
  sessionId: string;
  correlationId?: string;
  samplingMode: SessionReplaySamplingMode;
  events: eventWithTime[];
}

export interface SessionReplayOptions {
  /** Pfad oder vollqualifizierte URL des Backend-Proxy-Endpoints (`/session-replay`). Pflicht. */
  endpoint: string;
  /** Anteil der Sessions, die von Anfang an regulaer aufgezeichnet werden (0-1, Default 0.1). */
  sampleRate?: number;
  /** Anteil, zu dem eine nicht regulaer gesampelte Session bei {@link
   * SessionReplayRecorder.notifyError} doch aufgezeichnet wird (0-1, Default 1). */
  errorSampleRate?: number;
  /** Liefert die aktuell aktive Session-/Trace-Korrelations-ID, pro Batch neu abgefragt. */
  getCorrelationId?: () => string | undefined;
  /** Intervall zwischen automatischen Batch-Uploads in ms (Default 10000). */
  batchIntervalMs?: number;
  /** Batch wird sofort geflushed, sobald diese Anzahl gepufferter Events erreicht ist
   * (Default 100). */
  batchMaxEvents?: number;
  /** Schaltet die DSGVO-Defaults (Text-Maskierung + Medien-Blocking) explizit ab. Bewusst kein
   * einfaches `false`-Flag, sondern ein separat benannter, unmissverstaendlich "gefaehrlicher"
   * Opt-out (Default `false`). */
  dangerouslyDisableDefaultPrivacy?: boolean;
}

export interface SessionReplayRecorder {
  readonly sessionId: string;
  /** Wuerfelt `sampleRate` und startet bei Erfolg `rrweb.record()`. Idempotent. */
  start(): void;
  /** Meldet einen erfassten Fehler; wuerfelt `errorSampleRate` und startet das Recording bei
   * Erfolg ab JETZT, falls noch nicht aufgezeichnet wird. */
  notifyError(): void;
  isRecording(): boolean;
  /** Sendet den aktuellen Event-Puffer sofort. Wirft nie. No-op bei leerem Puffer.
   * `keepalive` (Default `false`) NUR fuer einen abschliessenden Flush vor einem Unload setzen
   * (siehe `stop()`) -- der Browser lehnt jeden `keepalive`-Request ueber 64 KiB hart ab, ein
   * regulaerer Batch ist dafuer typischerweise zu gross. */
  flush(options?: { keepalive?: boolean }): Promise<void>;
  /** Stoppt `rrweb.record()`, raeumt den Timer ab und flusht ein letztes Mal. */
  stop(): Promise<void>;
}

const DEFAULT_SAMPLE_RATE = 0.1;
const DEFAULT_ERROR_SAMPLE_RATE = 1;
const DEFAULT_BATCH_INTERVAL_MS = 10_000;
const DEFAULT_BATCH_MAX_EVENTS = 100;

/** Medien-Elemente, die als Default per `blockSelector` geblockt werden -- rrweb kennt kein
 * eingebautes "block all media"-Flag (analog Sentrys `blockAllMedia`). Bewusst ohne `iframe`:
 * eingebettete Frames sind oft funktionale Widgets, deren Blockieren ueberraschende
 * Funktionsluecken im Replay erzeugen wuerde. */
const DEFAULT_BLOCKED_MEDIA_SELECTOR = 'img, image, video, object, embed, map, audio, picture, source';

function isValidRate(value: number): boolean {
  return Number.isFinite(value) && value >= 0 && value <= 1;
}

/** rrweb-Meta-Events tragen `data.href` mit der vollen Seiten-URL inkl. Query-String/Fragment --
 * kann wie in `errorReporting.ts`s {@link safeUrl} beschrieben ein Capability-Token tragen (z. B.
 * `/auth/reset-password/confirm?token=...`). Bewusst lokal statt `safeUrl()` aus
 * `errorReporting.ts` importiert: dieses Modul wird bereits von `errorReporting.ts` importiert
 * (fuer {@link notifySessionReplayError}), ein Import in die Gegenrichtung waere ein
 * Zirkularimport. Das Backend saniert `data.href` zusaetzlich selbst (Defense-in-Depth, siehe
 * `monitoring.py`s `_sanitized_event_body()`). */
function sanitizeMetaHref(event: eventWithTime): eventWithTime {
  if (event.type !== EventType.Meta) {
    return event;
  }
  try {
    const url = new URL(event.data.href);
    return { ...event, data: { ...event.data, href: `${url.origin}${url.pathname}` } };
  } catch {
    return event;
  }
}

export function createSessionReplayRecorder(options: SessionReplayOptions): SessionReplayRecorder {
  const {
    endpoint,
    sampleRate = DEFAULT_SAMPLE_RATE,
    errorSampleRate = DEFAULT_ERROR_SAMPLE_RATE,
    getCorrelationId,
    batchIntervalMs = DEFAULT_BATCH_INTERVAL_MS,
    batchMaxEvents = DEFAULT_BATCH_MAX_EVENTS,
    dangerouslyDisableDefaultPrivacy = false,
  } = options;

  if (endpoint.trim() === '') {
    throw new Error('createSessionReplayRecorder: `endpoint` ist Pflicht und darf nicht leer sein.');
  }
  if (!isValidRate(sampleRate)) {
    throw new Error(
      `createSessionReplayRecorder: \`sampleRate\` muss zwischen 0 und 1 liegen, erhalten: ${String(sampleRate)}.`
    );
  }
  if (!isValidRate(errorSampleRate)) {
    throw new Error(
      `createSessionReplayRecorder: \`errorSampleRate\` muss zwischen 0 und 1 liegen, erhalten: ${String(errorSampleRate)}.`
    );
  }

  const sessionId = crypto.randomUUID();
  let buffer: eventWithTime[] = [];
  let stopRecordingFn: (() => void) | undefined;
  let flushTimer: ReturnType<typeof setInterval> | undefined;
  let samplingMode: SessionReplaySamplingMode | undefined;
  let startRolled = false;
  let stopped = false;

  function handleEmit(event: eventWithTime): void {
    buffer.push(sanitizeMetaHref(event));
    if (buffer.length >= batchMaxEvents) {
      void flush();
    }
  }

  function beginRecording(mode: SessionReplaySamplingMode): void {
    // Vor record() gesetzt: rrweb kann emit() synchron innerhalb von record() feuern (initialer
    // Full-Snapshot), samplingMode muss also schon stehen, bevor handleEmit() erreichbar ist.
    samplingMode = mode;
    let stopFn: (() => void) | undefined;
    try {
      stopFn = record({
        emit: handleEmit,
        maskAllInputs: !dangerouslyDisableDefaultPrivacy,
        maskTextSelector: dangerouslyDisableDefaultPrivacy ? undefined : '*',
        blockSelector: dangerouslyDisableDefaultPrivacy ? undefined : DEFAULT_BLOCKED_MEDIA_SELECTOR,
      });
    } catch (err) {
      // Anders als der dokumentierte "liefert undefined statt zu werfen"-Fall unten: ein
      // tatsaechlicher Throw aus record() (z. B. unerwarteter Browser-API-Fehler) darf trotzdem
      // nicht durchschlagen -- beginRecording() wird auch aus notifyError() erreicht, das wiederum
      // direkt im Error-Handling-Hotpath (reportClientError() -> notifySessionReplayError())
      // haengt. Ein zweiter, unbehandelter Fehler dort waere schlimmer als der erste.
      console.error(`[sessionReplay] Recording (mode=${mode}) warf beim Start:`, err);
      return;
    }
    if (stopFn === undefined) {
      // rrweb.record() faengt Init-Fehler intern ab (z. B. CSP-Restriktion) und liefert dann
      // undefined statt zu werfen -- stopRecordingFn/flushTimer bewusst nicht setzen, sonst
      // wuerde isRecording() faelschlich false bleiben, waehrend trotzdem ein Timer liefe.
      console.error(
        `[sessionReplay] Recording (mode=${mode}) konnte nicht gestartet werden -- rrweb.record() lieferte keinen Stop-Handler zurueck.`
      );
      return;
    }
    stopRecordingFn = stopFn;
    flushTimer = setInterval(() => void flush(), batchIntervalMs);
  }

  function isRecording(): boolean {
    return stopRecordingFn !== undefined;
  }

  function start(): void {
    if (stopped || startRolled) {
      return;
    }
    // Vor dem Wuerfeln gesetzt (nicht erst bei Erfolg): macht start() auch nach einem verlorenen
    // Roll idempotent -- ein zweiter Aufruf (z. B. erneut feuernder React-Effect) wuerfelt sonst
    // ein zweites Mal und haette die effektive Sampling-Rate ueber den konfigurierten Wert hinaus
    // angehoben.
    startRolled = true;
    if (isRecording()) {
      // notifyError() ist bereits vor start() gelaufen und zeichnet schon auf (z. B. ein Fehler,
      // der vor dem regulaeren App-Mount-Aufruf von start() feuert) -- ohne diese Guard wuerde
      // hier ein zweites beginRecording('normal') stopRecordingFn/flushTimer der ersten,
      // error-getriggerten Aufzeichnung ueberschreiben, ohne sie aufzuraeumen (Listener-/Timer-Leak,
      // samplingMode faellt faelschlich auf 'normal' zurueck).
      return;
    }
    if (Math.random() < sampleRate) {
      beginRecording('normal');
    }
  }

  function notifyError(): void {
    if (stopped || isRecording()) {
      return;
    }
    if (Math.random() < errorSampleRate) {
      beginRecording('error');
    }
  }

  async function flush(options?: { keepalive?: boolean }): Promise<void> {
    if (buffer.length === 0) {
      return;
    }
    const events = buffer;
    buffer = [];
    try {
      const batch: SessionReplayEventBatch = {
        sessionId,
        // samplingMode ist hier nie undefined: buffer wird nur ueber handleEmit() befuellt, und
        // die ist erst nach beginRecording() (setzt samplingMode) als emit-Callback aktiv.
        samplingMode: samplingMode as SessionReplaySamplingMode,
        correlationId: getCorrelationId?.(),
        events,
      };
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(batch),
        // NUR fuer die abschliessende Flush aus stop() (siehe dort) -- bei einem regulaeren
        // Batch (insb. dem ersten mit dem rrweb-Full-Snapshot) waere `keepalive: true`
        // kontraproduktiv: der Browser lehnt jeden keepalive-Request ueber 64 KiB hart ab
        // (Fetch-Spec), waehrend ein regulaerer Batch typischerweise deutlich groesser ist
        // (_MAX_REPLAY_EVENT_BYTES in monitoring.py rechnet mit bis zu 300 KB fuer ein
        // Full-Snapshot-Event allein) -- der allererste Flush jeder Session wuerde damit
        // faktisch immer als Netzwerkfehler scheitern.
        keepalive: options?.keepalive ?? false,
      });
      if (!response.ok) {
        console.error(
          `[sessionReplay] Batch-Upload fehlgeschlagen (endpoint=${endpoint}): HTTP ${response.status}, ${events.length} Events verworfen.`
        );
      }
    } catch (err) {
      console.error(
        `[sessionReplay] Batch-Upload fehlgeschlagen (endpoint=${endpoint}), ${events.length} Events verworfen:`,
        err
      );
    }
  }

  async function stop(): Promise<void> {
    if (stopped) {
      return;
    }
    stopped = true;
    if (flushTimer !== undefined) {
      clearInterval(flushTimer);
      flushTimer = undefined;
    }
    if (stopRecordingFn !== undefined) {
      stopRecordingFn();
      stopRecordingFn = undefined;
    }
    // keepalive: true nur hier (siehe flush()) -- stop() wird u. a. aus dem pagehide-Handler in
    // initSessionReplay() aufgerufen, dessen abschliessender Flush den Seitenwechsel ueberleben
    // soll.
    await flush({ keepalive: true });
  }

  return { sessionId, start, notifyError, isRecording, flush, stop };
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const DEFAULT_ENDPOINT = `${API_BASE_URL}/api/v1/monitoring/session-replay`;

/** Gilt fuer {@link initSessionReplay} -- Paritaet zum bisherigen `initSentry()`/
 * `initErrorReporting()`, die beide nur ausserhalb von `development` recordeten. */
function isReplayReportingEnabled(): boolean {
  return (process.env.REACT_APP_ENVIRONMENT || 'development') !== 'development';
}

let defaultRecorder: SessionReplayRecorder | undefined;

/**
 * Erzeugt die app-weite Standard-Recorder-Instanz und startet sie -- No-op in `development`
 * (siehe {@link isReplayReportingEnabled}). Analog `initErrorReporting()`: einmal beim App-Mount
 * aufrufen, vor dem ersten Render.
 *
 * Faengt jeden Fehler ab (ADR-012, siehe `errorReporting.ts`s Moduldoc): `index.tsx` ruft dies
 * synchron VOR `ReactDOM.createRoot()` auf, ein unbehandelter Throw hier (z. B.
 * `createSessionReplayRecorder()`s Konstruktor-Validierung oder `crypto.randomUUID()` in einem
 * Kontext ohne Secure-Context-Support) wuerde also den kompletten App-Bootstrap verhindern statt
 * nur Session-Replay lahmzulegen.
 *
 * Registriert zusaetzlich einen `pagehide`-Listener (nicht `beforeunload`, bfcache-kompatibel),
 * der den Recorder stoppt/flusht -- ohne diesen gehen die letzten `batchIntervalMs` (Default
 * 10 s) Events bei jedem Tab-Close/Full-Page-Navigate verloren, oft genau die Sekunden nach
 * einem Fehler, wegen dem `notifyError()` das Recording ueberhaupt erst gestartet hat.
 */
export function initSessionReplay(): void {
  const environment = process.env.REACT_APP_ENVIRONMENT || 'development';
  if (!isReplayReportingEnabled()) {
    console.log('[sessionReplay] Disabled in', environment);
    return;
  }
  try {
    // Schuetzt vor einem doppelten initSessionReplay()-Aufruf (heute nur ein Call-Site in
    // index.tsx, aber billig abzusichern): ohne dies wuerde der alte Recorder samt Listener/Timer
    // weiterlaufen, unerreichbar ueber die neu zugewiesene defaultRecorder-Referenz.
    if (defaultRecorder !== undefined) {
      void defaultRecorder.stop();
    }
    defaultRecorder = createSessionReplayRecorder({ endpoint: DEFAULT_ENDPOINT });
    defaultRecorder.start();
    window.addEventListener('pagehide', () => {
      void defaultRecorder?.stop();
    });
    console.log('[sessionReplay] Initialized for', environment);
  } catch (err) {
    console.error('[sessionReplay] Initialisierung fehlgeschlagen:', err);
  }
}

/**
 * Meldet der app-weiten Standard-Instanz einen erfassten Fehler (siehe {@link
 * SessionReplayRecorder.notifyError}) -- koppelt das Sample-Rate-Upgrade an denselben
 * Fehler-Signal-Pfad wie `errorReporting.ts`s `reportClientError()` (TF-867 AC2). Sicheres No-op,
 * solange {@link initSessionReplay} noch nicht gelaufen ist (z. B. `development`, oder ein Fehler
 * vor dem App-Mount).
 */
export function notifySessionReplayError(): void {
  defaultRecorder?.notifyError();
}
